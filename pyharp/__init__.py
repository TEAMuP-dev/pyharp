# Held before anything else is imported, because until the worker installs its own
# handler (see worker.py) SIGINT is still Python's default, which ends the process.
# That window covers every import below, gradio included, and in an app it covers the
# model loaded on the way to process_fn, so it is seconds long at best. Cancelling
# inside it would otherwise kill the worker outright and be reported as a crash
# rather than as the cancellation it is. Holding the signal leaves stopping the
# worker to the supervisor, which already does that for a job that will not yield.
#
# multiprocessing sets _inheriting for exactly the span of a worker's imports, so
# nothing is held in the app's own process.
import multiprocessing as _mp
import signal as _signal

if getattr(_mp.current_process(), "_inheriting", False):
    try:
        _signal.signal(_signal.SIGINT, lambda *_: None)
    except ValueError:
        # A handler can only be set from the main thread. An import from another
        # one leaves SIGINT at its default, where cancelling kills the worker, but
        # that is better than refusing to import at all.
        pass

from .core import *
from .media import *
from .labels import *
