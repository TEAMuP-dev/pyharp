# PyHARP runs process_fn in a separate worker process, so that pressing Cancel in HARP
# can stop work that has already started (see worker.py). Canceling sends the worker an
# interrupt, the same signal Ctrl-C sends.
#
# The worker starts by importing this package and the app's module, which can take
# seconds once gradio and a model are involved. worker.py installs a handler that turns
# the interrupt into a clean stop, but only once it is running, so Python's default
# handler is still in place during those imports. That one ends the process on the spot,
# which would make a cancellation look like the model had crashed.
#
# Ignoring the interrupt until the imports finish avoids that. worker.py takes over from
# there, and PyHARP ends the worker outright if a job refuses to stop.
#
# multiprocessing sets _inheriting only while a new process is importing, so this leaves
# the app's own process untouched.
import multiprocessing as _mp
import signal as _signal

if getattr(_mp.current_process(), "_inheriting", False):
    try:
        _signal.signal(_signal.SIGINT, lambda *_: None)
    except ValueError:
        # Only the main thread can install a signal handler. If this import is not on
        # it, the interrupt keeps its default behavior and canceling kills the worker,
        # which is still better than refusing to import at all.
        pass

from .core import *
from .tags import *
from .media import *
from .labels import *
