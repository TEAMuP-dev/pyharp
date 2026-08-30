"""
Tests for running process_fn in a worker process.

The behaviour under test is mostly about what happens when things go wrong -
cancellation, timeouts, crashes - so most of these drive a failure deliberately and
assert on how it is reported. Each one keeps its own timings short; nothing here
should take more than a few seconds.
"""

import os
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


def test_plain_exception_arrives_with_its_traceback(supervisor, progress):
    with pytest.raises(RuntimeError) as raised:
        supervisor().run(jobs.raise_plain_error, progress=progress)

    assert "an unexpected failure" in str(raised.value)
    assert "raise_plain_error" in str(raised.value)


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

    assert raised.value.message == "Job cancelled."
    assert time.monotonic() - started < 10

    # Interrupted in place, so whatever the worker had loaded is still loaded
    assert sup.run(jobs.identify, progress=progress)["worker_id"] == warm["worker_id"]


def test_cancel_replaces_a_worker_that_ignores_interrupts(supervisor, progress):
    sup = supervisor()

    warm = sup.run(jobs.identify, progress=progress)

    cancel_after(sup, 1)

    with pytest.raises(gr.Error) as raised:
        sup.run(jobs.sleep_ignoring_interrupts, 60, progress=progress)

    assert raised.value.message == "Job cancelled."

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
    assert outcome.get("error") == "Job cancelled."


def test_a_stopped_job_does_not_report_into_the_next_one(supervisor, progress):
    """The sentinel left by a cancelled job must not be read as the next result."""
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
