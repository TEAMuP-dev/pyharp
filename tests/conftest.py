import os
import sys
import threading

import gradio as gr
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyharp.worker import JobSupervisor  # noqa: E402


@pytest.fixture
def supervisor():
    """A supervisor whose worker is always torn down, so tests leak no processes."""
    made = []

    def build(timeout_s=30):
        instance = JobSupervisor(timeout_s=timeout_s)
        made.append(instance)

        return instance

    yield build

    for instance in made:
        worker = instance._worker

        if worker is not None and worker.is_alive():
            JobSupervisor._end_process(worker)


@pytest.fixture
def collected_messages(monkeypatch):
    """
    Captures what the supervisor replays on the worker's behalf.

    gr.Info, gr.Warning and gr.Success all reach the browser through log_message,
    which needs a live request context. Replacing it records the calls instead.
    """
    messages = []

    def record(message, title, level="info", duration=10, visible=True):
        messages.append({"message": message, "title": title, "level": level})

    monkeypatch.setattr("gradio.helpers.log_message", record)

    return messages


@pytest.fixture
def serving_request():
    """
    Stands in for the request context Gradio establishes around a handler.

    The request lives in a contextvar, so it is set and reset rather than patched.
    """
    from gradio.context import LocalContext

    tokens = []

    def serve(headers, session_hash=None):
        request = (
            gr.Request(headers=headers, session_hash=session_hash)
            if headers is not None
            else None
        )
        tokens.append(LocalContext.request.set(request))

        return request

    yield serve

    for token in reversed(tokens):
        LocalContext.request.reset(token)


class RecordingProgress:
    """Stands in for the progress tracker Gradio injects into a request."""

    def __init__(self):
        self.updates = []

    def __call__(self, value, desc=None, total=None, unit="steps"):
        self.updates.append((round(value, 3), desc))


@pytest.fixture
def progress():
    return RecordingProgress()


def cancel_after(supervisor, seconds):
    """Cancels from another thread, as the Cancel endpoint does mid-request."""
    timer = threading.Timer(seconds, supervisor.cancel)
    timer.daemon = True
    timer.start()

    return timer
