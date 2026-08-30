"""
Job functions for the worker tests.

These live in an importable file rather than in the test module because the worker
is started with "spawn": it reaches a job by importing the file that defines it, so
a function written inside a test could not be found.

WORKER_ID is generated once when this file is imported. Two jobs reporting the same
value therefore ran in the same worker, which is how the tests tell a reused worker
from a replaced one.
"""

import os
import signal
import subprocess
import sys
import time
import uuid

import gradio as gr


WORKER_ID = uuid.uuid4().hex


class Unsendable:
    """Cannot cross a process boundary, to stand in for an accidental return value."""

    def __reduce__(self):
        raise TypeError("Unsendable cannot be pickled")


def identify(_=None):
    """Reports which process and which worker ran the job."""
    return {"pid": os.getpid(), "worker_id": WORKER_ID}


def sleep_interruptibly(seconds):
    """Spends its time in Python, so an interrupt unwinds it immediately."""
    deadline = time.monotonic() + seconds

    while time.monotonic() < deadline:
        time.sleep(0.05)

    return "finished"


def sleep_ignoring_interrupts(seconds):
    """Refuses to be interrupted, so stopping it needs the worker to be killed."""
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    return sleep_interruptibly(seconds)


def spawn_child_then_sleep(marker_path, seconds):
    """
    Starts a grandchild process and waits on it, as a dual-environment app does.

    The grandchild writes its own pid to marker_path so the test can check whether
    it outlived the worker.
    """
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    script = (
        "import os, sys, time\n"
        "open(sys.argv[1], 'w').write(str(os.getpid()))\n"
        f"time.sleep({seconds})\n"
    )

    subprocess.run([sys.executable, "-c", script, marker_path], timeout=seconds + 30)

    return "finished"


def report_progress(steps):
    for step in range(steps):
        gr.Progress()((step + 1) / steps, desc=f"step {step + 1}")

    return "finished"


def report_messages():
    gr.Info("an informational message", title="Notice")
    gr.Warning("a warning message")

    return "finished"


def raise_gradio_error():
    raise gr.Error("something the user should see", title="Bad Input", duration=7)


def raise_plain_error():
    raise ValueError("an unexpected failure")


def return_unsendable():
    return Unsendable()


def exit_abruptly():
    """Stands in for an out-of-memory kill: the process dies without reporting."""
    os._exit(1)
