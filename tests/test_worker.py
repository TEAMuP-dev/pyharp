"""
Tests for running process_fn in a worker process.

The behavior under test is mostly about what happens when things go wrong -
cancellation, timeouts, crashes - so most of these drive a failure deliberately and
assert on how it is reported. Each one keeps its own timings short; nothing here
should take more than a few seconds.
"""

import contextvars
import os
import threading
import time

import gradio as gr
import pytest

from conftest import cancel_after

import jobs


def is_running(pid):
    try:
        os.kill(pid, 0)
    except OSError:
        return False

    return True


# --------------------------------------------------------------------------------
# Where the job runs
# --------------------------------------------------------------------------------


def test_job_runs_outside_the_server_process(supervisor, progress):
    result = supervisor().run(jobs.identify, progress=progress)

    assert result["pid"] != os.getpid()


def test_worker_is_reused_between_jobs(supervisor, progress):
    sup = supervisor()

    first = sup.run(jobs.identify, progress=progress)
    second = sup.run(jobs.identify, progress=progress)

    assert first["pid"] == second["pid"]

    # The same import, so anything loaded on the way to process_fn was loaded once
    assert first["worker_id"] == second["worker_id"]


# --------------------------------------------------------------------------------
# Results and failures
# --------------------------------------------------------------------------------


def test_gradio_error_keeps_its_fields(supervisor, progress):
    with pytest.raises(gr.Error) as raised:
        supervisor().run(jobs.raise_gradio_error, progress=progress)

    assert raised.value.message == "something the user should see"
    assert raised.value.title == "Bad Input"
    assert raised.value.duration == 7


def test_plain_exception_reaches_the_user_without_its_traceback(supervisor, progress, capfd):
    """
    A traceback in a HARP dialog buries the one line a user can act on, so it is
    logged where whoever runs the app can read it instead. capfd rather than capsys,
    since the worker is a separate process writing to the inherited stderr.
    """
    with pytest.raises(RuntimeError) as raised:
        supervisor().run(jobs.raise_plain_error, progress=progress)

    assert "an unexpected failure" in str(raised.value)
    assert "Traceback" not in str(raised.value)

    assert "raise_plain_error" in capfd.readouterr().err


def test_unsendable_result_is_reported_rather_than_hanging(supervisor, progress):
    started = time.monotonic()

    with pytest.raises((RuntimeError, gr.Error)):
        supervisor(timeout_s=30).run(jobs.return_unsendable, progress=progress)

    # The point is that it does not wait for the timeout to notice
    assert time.monotonic() - started < 15


def test_worker_dying_without_reporting_is_not_a_hang(supervisor, progress):
    with pytest.raises(gr.Error) as raised:
        supervisor(timeout_s=60).run(jobs.exit_abruptly, progress=progress)

    assert "stopped unexpectedly" in raised.value.message


def test_supervisor_recovers_after_a_crash(supervisor, progress):
    sup = supervisor(timeout_s=60)

    with pytest.raises(gr.Error):
        sup.run(jobs.exit_abruptly, progress=progress)

    assert sup.run(jobs.identify, progress=progress)["pid"] != os.getpid()


# --------------------------------------------------------------------------------
# Calls that need the request context, made from a process that does not have one
# --------------------------------------------------------------------------------


def test_progress_updates_reach_the_request(supervisor, progress):
    supervisor().run(jobs.report_progress, 3, progress=progress)

    assert progress.updates == [(0.333, "step 1"), (0.667, "step 2"), (1.0, "step 3")]


def test_info_and_warning_reach_the_request(supervisor, progress, collected_messages):
    supervisor().run(jobs.report_messages, progress=progress)

    assert collected_messages == [
        {"message": "an informational message", "title": "Notice", "level": "info"},
        {"message": "a warning message", "title": "Warning", "level": "warning"},
    ]


def test_progress_is_optional(supervisor):
    """A handler Gradio gave no tracker to must not fail when the job reports."""
    assert supervisor().run(jobs.report_progress, 2) == "finished"


# --------------------------------------------------------------------------------
# Cancellation
# --------------------------------------------------------------------------------


def test_cancel_stops_the_job_and_keeps_the_worker(supervisor, progress):
    sup = supervisor()

    warm = sup.run(jobs.identify, progress=progress)

    cancel_after(sup, 1)
    started = time.monotonic()

    with pytest.raises(gr.Error) as raised:
        sup.run(jobs.sleep_interruptibly, 60, progress=progress)

    assert raised.value.message == "Job canceled."
    assert time.monotonic() - started < 10

    # Interrupted in place, so whatever the worker had loaded is still loaded
    assert sup.run(jobs.identify, progress=progress)["worker_id"] == warm["worker_id"]


def test_cancel_replaces_a_worker_that_ignores_interrupts(supervisor, progress):
    sup = supervisor()

    warm = sup.run(jobs.identify, progress=progress)

    cancel_after(sup, 1)

    with pytest.raises(gr.Error) as raised:
        sup.run(jobs.sleep_ignoring_interrupts, 60, progress=progress)

    assert raised.value.message == "Job canceled."

    # Killing it is the only way to stop it, so the next job gets a fresh worker
    assert sup.run(jobs.identify, progress=progress)["worker_id"] != warm["worker_id"]


def test_cancel_while_idle_does_nothing(supervisor, progress):
    sup = supervisor()

    warm = sup.run(jobs.identify, progress=progress)
    sup.cancel()

    assert sup.run(jobs.identify, progress=progress)["worker_id"] == warm["worker_id"]


def test_starting_a_job_stops_the_previous_one(supervisor, progress):
    """Single-flight: Process runs what was just asked for, not what is queued."""
    sup = supervisor()

    outcome = {}

    def run_slow():
        try:
            outcome["result"] = sup.run(jobs.sleep_interruptibly, 60, progress=progress)
        except gr.Error as error:
            outcome["error"] = error.message

    import threading

    slow = threading.Thread(target=run_slow, daemon=True)
    slow.start()
    time.sleep(2)

    assert sup.run(jobs.identify, progress=progress)["pid"] != os.getpid()

    slow.join(timeout=15)
    assert outcome.get("error") == "Job canceled."


def test_a_stopped_job_does_not_report_into_the_next_one(supervisor, progress):
    """The sentinel left by a canceled job must not be read as the next result."""
    sup = supervisor()

    cancel_after(sup, 1)

    with pytest.raises(gr.Error):
        sup.run(jobs.sleep_interruptibly, 60, progress=progress)

    assert sup.run(jobs.identify, progress=progress)["pid"] != os.getpid()


def test_processes_the_job_started_are_stopped_with_it(supervisor, progress, tmp_path):
    """A model invoked as a subprocess must not outlive the worker that ran it."""
    marker = tmp_path / "grandchild.pid"

    sup = supervisor()
    cancel_after(sup, 3)

    with pytest.raises(gr.Error):
        sup.run(jobs.spawn_child_then_sleep, str(marker), 60, progress=progress)

    assert marker.exists(), "the job never started its subprocess"

    grandchild = int(marker.read_text())

    for _ in range(50):
        if not is_running(grandchild):
            break
        time.sleep(0.1)

    assert not is_running(grandchild), f"process {grandchild} outlived its worker"


# --------------------------------------------------------------------------------
# Timeouts
# --------------------------------------------------------------------------------


def test_overrunning_job_is_stopped_at_the_limit(supervisor, progress):
    started = time.monotonic()

    with pytest.raises(gr.Error) as raised:
        supervisor(timeout_s=2).run(jobs.sleep_interruptibly, 60, progress=progress)

    elapsed = time.monotonic() - started

    # Reported as a timeout, not as the cancellation the worker sees
    assert raised.value.message == "Job timed out."
    assert raised.value.title == "Timed out"
    assert 2 <= elapsed < 15


def test_a_job_within_its_limit_is_left_alone(supervisor, progress):
    assert supervisor(timeout_s=30).run(jobs.sleep_interruptibly, 1, progress=progress)


def test_request_headers_reach_the_worker(supervisor, progress, serving_request):
    """
    ZeroGPU decides whose GPU quota a job spends from the caller's token, which it
    reads off these headers. They reach it through a contextvar, which does not
    survive the jump into the worker unless it is carried there.
    """
    headers = {"x-ip-token": "a-caller-token", "x-gradio-user": "app"}

    serving_request(headers)

    assert supervisor().run(jobs.report_request_headers, progress=progress) == headers


def test_a_job_without_a_request_sees_none(supervisor, progress):
    """An app driven outside a request, such as from a script, still runs."""
    assert supervisor().run(jobs.report_request_headers, progress=progress) is None


def test_a_request_does_not_leak_into_the_next_job(supervisor, progress, serving_request):
    """
    The worker outlives the job, so a contextvar set for one caller would otherwise
    still be set for whoever is served next.
    """
    instance = supervisor()

    serving_request({"x-ip-token": "first-caller"})

    assert instance.run(jobs.report_request_headers, progress=progress) == {
        "x-ip-token": "first-caller"
    }

    serving_request(None)

    assert instance.run(jobs.report_request_headers, progress=progress) is None

# --------------------------------------------------------------------------------
# Whose job a cancel belongs to
# --------------------------------------------------------------------------------


def _run_in_background(sup, outcome, progress, seconds=14):
    """
    Starts a job on another thread, carrying this thread's request context with it.

    A new thread gets an empty context, so the headers the test set would not reach
    run() without copying it over.
    """
    def job():
        try:
            outcome["result"] = sup.run(jobs.sleep_interruptibly, seconds, progress=progress)
        except gr.Error as error:
            outcome["error"] = error.message

    thread = threading.Thread(target=contextvars.copy_context().run, args=(job,), daemon=True)
    thread.start()

    return thread


def test_a_cancel_from_another_client_is_ignored(supervisor, progress, serving_request):
    """One visitor pressing Cancel must not stop a job another visitor started."""
    sup = supervisor()
    outcome = {}

    serving_request({"x-harp-client": "tab-1"})
    thread = _run_in_background(sup, outcome, progress)

    time.sleep(7)

    serving_request({"x-harp-client": "tab-2"})
    sup.cancel()

    thread.join(timeout=40)

    assert outcome.get("result") == "finished", outcome


def test_a_cancel_from_the_same_client_stops_the_job(supervisor, progress, serving_request):
    sup = supervisor()
    outcome = {}

    serving_request({"x-harp-client": "tab-1"})
    thread = _run_in_background(sup, outcome, progress)

    time.sleep(7)

    serving_request({"x-harp-client": "tab-1"})
    sup.cancel()

    thread.join(timeout=40)

    assert outcome.get("error") == "Job canceled.", outcome


def test_an_unidentified_cancel_cannot_stop_an_identified_job(supervisor, progress, serving_request):
    """The Gradio page in a browser must not stop a job HARP started."""
    sup = supervisor()
    outcome = {}

    serving_request({"x-harp-client": "tab-1"})
    thread = _run_in_background(sup, outcome, progress)

    time.sleep(7)

    serving_request({"user-agent": "a browser"})
    sup.cancel()

    thread.join(timeout=40)

    assert outcome.get("result") == "finished", outcome


def test_an_unidentified_cancel_stops_nothing(supervisor, progress, serving_request):
    """
    Two callers that send no id cannot be told apart, so neither stops the other and
    the job finishes in the background. This is what cancelling did before the worker,
    so an older HARP is no worse off than it was before.
    """
    sup = supervisor()
    outcome = {}

    serving_request({"user-agent": "an older HARP"})
    thread = _run_in_background(sup, outcome, progress)

    time.sleep(7)

    serving_request({"user-agent": "a different older HARP"})
    sup.cancel()

    thread.join(timeout=40)

    assert outcome.get("result") == "finished", outcome
