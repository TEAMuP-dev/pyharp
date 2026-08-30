"""
Runs process_fn in a worker process, so that a job can be stopped once it has started.

Gradio has no way to interrupt a running event handler, and a Python thread cannot be
killed, so cancelling one in place is not possible: the work would carry on holding the
GPU whatever the caller did. Running it in a separate process makes it stoppable, and
reusing that process across requests keeps whatever the app loaded on the way to
process_fn from being paid for again on every job.

Only JobSupervisor is used elsewhere; everything else here supports it.
"""

import multiprocessing as mp
import os
import queue
import signal
import threading
import time

import gradio as gr


# "spawn" avoids deadlocks that "fork" can cause with CUDA/PyTorch on Linux (Hugging Face
# Spaces). A private context is used rather than mp.set_start_method(force=True), which
# would change the start method for the whole process and override whatever the app or
# any other library had chosen.
_MP = mp.get_context("spawn")

# Grace period for a result already in flight when the worker exits. The queue is fed by
# a background thread in the worker, so a result put just before exit can arrive slightly
# after the process is gone.
_RESULT_GRACE_S = 10

# How often the supervisor wakes to re-check the worker while waiting for messages
_POLL_S = 0.1

# How long a cancelled job is given to unwind before the worker is killed outright
_INTERRUPT_GRACE_S = 2

# "spawn" re-imports the app module in the worker to reach process_fn, which for an app
# whose Gradio code is not behind an "if __name__" guard means launch() runs there too.
# Suppressing it keeps such an app working, at the cost of building its interface in the
# worker as well.
#
# multiprocessing sets _inheriting for exactly the span of that re-import - it is the flag
# behind its own "if __name__ == '__main__'" guidance - so it identifies a worker without
# any global state having to be set. Read defensively: if it ever goes away, nothing is
# suppressed and an unguarded app is back to needing the guard.
if getattr(mp.current_process(), "_inheriting", False):

    def _suppress_launch(self, *args, **kwargs):
        import warnings

        warnings.warn(
            "PyHARP suppressed a launch() call in a processing worker. Put the Gradio "
            "code behind 'if __name__ == \"__main__\":', with process_fn defined above "
            "it, to avoid rebuilding the interface in every worker.",
            stacklevel=2,
        )

        return None, None, None

    gr.Blocks.launch = _suppress_launch

def _redirect_context_calls(result_q, job_id):
    """
    Points Gradio's progress and message helpers at the result queue.

    These normally reach the browser through the Gradio request context, which only
    exists in the server process. Called from the worker they would find no context
    and quietly print to the server log instead, so they are redirected here and
    replayed by the supervisor, which does have that context.

    Both are patched at their single definition in gradio.helpers rather than at
    gr.Info / gr.Progress, so that an app which imported the names directly is
    redirected too.
    """
    import gradio.helpers as helpers

    def forward_log(message, title, level="info", duration=10, visible=True):
        result_q.put((job_id[0], "log", (str(message), str(title), level, duration, visible)))

    def forward_progress(self, progress, desc=None, total=None, unit="steps", _tqdm=None):
        result_q.put((job_id[0], "progress", (progress, desc, total, unit)))

    # gr.Info, gr.Warning and gr.Success all funnel through log_message
    helpers.log_message = forward_log
    helpers.Progress.__call__ = forward_progress


def _worker_loop(jobs_q, results_q, job_done):
    """
    Runs jobs one after another until the supervisor stops sending them.

    The worker outlives individual jobs, so a model loaded on the way to process_fn
    is loaded once rather than once per request. A cancelled job arrives as
    SIGINT, which unwinds Python-level work and leaves the worker - and everything it
    has loaded - intact for the next job.
    """
    import pickle
    import traceback

    try:
        # Leads its own process group, so that killing an uninterruptible job takes
        # whatever it started with it. A model invoked as a subprocess - the layout the
        # dual-environment Docker Spaces use - would otherwise be reparented and keep
        # running after its worker is gone.
        os.setsid()
    except (AttributeError, OSError):
        # Not available on this platform; the fallback in _end_process still applies
        pass

    current_id = [None]

    _redirect_context_calls(results_q, current_id)

    running = threading.Event()

    def on_interrupt(signum, frame):
        # Between jobs there is nothing to unwind, and raising would end the worker
        if running.is_set():
            raise KeyboardInterrupt

    signal.signal(signal.SIGINT, on_interrupt)

    while True:
        try:
            job = jobs_q.get()
        except KeyboardInterrupt:
            # Arrived with no job to stop, so there is nothing to do but keep waiting
            continue
        except (EOFError, OSError):
            # The queue is gone, so no further job can arrive
            return

        job_id, fn, args = job
        current_id[0] = job_id

        try:
            # Set inside the try, so an interrupt landing here is caught below rather
            # than unwinding out of the loop and ending the worker
            running.set()

            result = fn(*args)

            # Pickling happens on a feeder thread once queued, where a failure would be
            # invisible and the job would look like it never finished. Failing here
            # instead reports it as the error it is.
            pickle.dumps(result)

            results_q.put((job_id, "ok", result))
        except KeyboardInterrupt:
            results_q.put((job_id, "gr_error", ("Job cancelled.", 10, True, "Cancelled")))
        except gr.Error as e:
            traceback.print_exc()
            results_q.put((job_id, "gr_error", (e.message, e.duration, e.visible, e.title)))
        except Exception as e:
            results_q.put((job_id, "err", (str(e), traceback.format_exc())))
        finally:
            running.clear()
            job_done.set()


class JobSupervisor:
    """
    Runs process_fn in a worker process that can be cancelled or timed out, rather
    than running to completion server-side.

    The worker is reused across requests so that whatever the app loads at import
    time - model weights above all - is paid for once rather than per job. Cancelling
    interrupts the job in place and keeps the worker; only a job stuck in a native
    call that will not yield costs a restart, and the replacement is started
    immediately so it is usually warm again before the next request.

    One supervisor is shared by every caller of an endpoint, so a Process or Cancel
    from one visitor stops whatever job is running. Gradio serialises queued events
    by default, which keeps that to a single job at a time; raising an event's
    concurrency_limit above 1 would let visitors cancel each other.
    """

    def __init__(self, timeout_s=900):
        self.timeout_s = timeout_s
        self._worker = None
        self._jobs_q = None
        self._results_q = None
        self._job_done = None
        self._job_id = 0
        self._busy = False
        self._lock = threading.Lock()

    def run(self, fn, *args, progress=None):
        # Single-flight: a new request stops whatever was running, rather than queueing
        # behind it, so that Process always starts the job the user just asked for
        self.cancel()

        with self._lock:
            worker, jobs_q, results_q, job_done = self._ensure_worker()
            job_done.clear()
            self._job_id += 1
            job_id = self._job_id
            self._busy = True

        jobs_q.put((job_id, fn, args))

        try:
            status, payload = self._collect(worker, results_q, job_done, job_id, progress)
        finally:
            with self._lock:
                self._busy = False

        if status == "gr_error":
            message, duration, visible, title = payload
            raise gr.Error(message, duration=duration, visible=visible, title=title)
        if status == "err":
            short_msg, tb = payload
            raise RuntimeError(f"{short_msg}\n\n{tb}")
        if status == "died":
            raise gr.Error(
                f"Processing stopped unexpectedly (exit code {payload}). This usually "
                f"means the model ran out of memory or crashed.",
                title="Processing failed",
            )
        return payload

    def cancel(self):
        with self._lock:
            if not self._busy or self._worker is None or not self._worker.is_alive():
                return

            worker, results_q, job_done = self._worker, self._results_q, self._job_done
            job_id = self._job_id

            try:
                os.kill(worker.pid, signal.SIGINT)
            except (ProcessLookupError, PermissionError, OSError):
                pass

        # Released before waiting, so the job's own thread can finish collecting
        if job_done.wait(timeout=_INTERRUPT_GRACE_S):
            # The job unwound and the worker kept everything it had loaded
            return

        with self._lock:
            if self._worker is not worker or not worker.is_alive():
                return

            # Stuck somewhere that will not accept an interrupt, so nothing short of
            # ending the process will stop it
            self._discard_worker("cancelled", results_q, job_id)

        # Reload while the user decides what to do next, rather than on their next request
        threading.Thread(target=self._warm_up, daemon=True).start()

    def _ensure_worker(self):
        """Returns a live worker, starting one if needed. Called with the lock held."""
        if self._worker is not None and self._worker.is_alive():
            return self._worker, self._jobs_q, self._results_q, self._job_done

        self._jobs_q = _MP.Queue()
        self._results_q = _MP.Queue()
        self._job_done = _MP.Event()
        self._worker = _MP.Process(
            target=_worker_loop,
            args=(self._jobs_q, self._results_q, self._job_done),
            daemon=True,
        )

        self._worker.start()

        return self._worker, self._jobs_q, self._results_q, self._job_done

    def _discard_worker(self, reason, results_q, job_id):
        """Ends the worker and leaves an outcome behind. Called with the lock held."""
        if self._worker is not None:
            self._end_process(self._worker)

        if results_q is not None:
            # Frees whichever request is waiting on this worker's queue
            results_q.put(
                (job_id, "gr_error", (f"Job {reason}.", 10, True, reason.capitalize()))
            )

        self._worker = None
        self._jobs_q = None
        self._results_q = None
        self._job_done = None

    @staticmethod
    def _end_process(worker):
        """Ends a worker and everything it started."""
        try:
            group = os.getpgid(worker.pid)
        except (AttributeError, ProcessLookupError, OSError):
            group = None

        # Only when the worker leads its own group, or this would signal the server too
        if group is not None and group == worker.pid:
            try:
                os.killpg(group, signal.SIGKILL)
            except (AttributeError, ProcessLookupError, PermissionError, OSError):
                worker.kill()
        else:
            worker.kill()

        worker.join(timeout=5)

    def _warm_up(self):
        with self._lock:
            if self._worker is None:
                self._ensure_worker()

    def _collect(self, worker, results_q, job_done, job_id, progress):
        """
        Waits for the job's outcome, replaying progress and messages as they arrive.

        This runs in the server's request context, so the calls the worker could not
        make itself are made here on its behalf.
        """
        import gradio.helpers as helpers

        deadline = time.monotonic() + self.timeout_s
        exited_at = None
        finished_at = None
        timed_out = False

        while True:
            try:
                message_id, kind, payload = results_q.get(timeout=_POLL_S)
            except queue.Empty:
                if time.monotonic() >= deadline:
                    timed_out = True
                    self._time_out(worker, results_q, job_id)
                    deadline = time.monotonic() + _RESULT_GRACE_S
                    continue

                if worker.is_alive():
                    exited_at = None

                    # The worker has moved on but nothing arrived for this job, which
                    # is what an unsendable return value looks like
                    if job_done.is_set():
                        if finished_at is None:
                            finished_at = time.monotonic()
                        elif time.monotonic() - finished_at >= _RESULT_GRACE_S:
                            return "err", (
                                "The job finished but sent nothing back. Check that "
                                "everything process_fn returns can be pickled.",
                                "",
                            )

                    continue

                # The worker is gone. Its result may still be in flight, since the
                # queue is fed by a background thread, so allow a grace period before
                # concluding that it stopped without posting one - which is what a
                # segfault or an out-of-memory kill looks like. Waiting forever here
                # would block this thread, and the queue behind it, for good.
                if exited_at is None:
                    exited_at = time.monotonic()
                elif time.monotonic() - exited_at >= _RESULT_GRACE_S:
                    return "died", worker.exitcode

                continue

            exited_at = None

            # A message from an earlier job, left behind when it was stopped
            if message_id != job_id:
                continue

            if kind == "progress":
                if progress is not None:
                    value, desc, total, unit = payload
                    progress(value, desc=desc, total=total, unit=unit)
                continue

            if kind == "log":
                message, title, level, duration, visible = payload
                helpers.log_message(
                    message, title=title, level=level, duration=duration, visible=visible
                )
                continue

            if timed_out and kind == "gr_error":
                # The worker reports an interrupt as a cancellation, since it cannot
                # tell who asked for one. Here it is known to have been the clock.
                _, duration, visible, _ = payload
                return kind, ("Job timed out.", duration, visible, "Timed out")

            return kind, payload

    def _time_out(self, worker, results_q, job_id):
        """Stops an overrunning job, interrupting first and ending the worker if that fails."""
        if not worker.is_alive():
            return

        try:
            os.kill(worker.pid, signal.SIGINT)
        except (ProcessLookupError, PermissionError, OSError):
            pass

        with self._lock:
            job_done = self._job_done

        if job_done is not None and job_done.wait(timeout=_INTERRUPT_GRACE_S):
            return

        with self._lock:
            if self._worker is worker:
                self._discard_worker("timed out", results_q, job_id)

        threading.Thread(target=self._warm_up, daemon=True).start()
