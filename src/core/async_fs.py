"""Run blocking filesystem calls off the GUI thread.

A hung network/cloud drive can block a call forever and Python threads cannot
be killed, so each request gets a daemon thread: an abandoned one never keeps
the app from exiting. Results come back as a queued Qt signal; callers drop
answers they no longer want (timeout, node collapsed, other path).
"""

import os
import threading

from PySide6.QtCore import QObject, Signal


class AsyncFs(QObject):
    finished = Signal(object, object, object)  # token, result, exception

    def submit(self, token, fn, *args):
        # ponytail: one thread per request; a pool if request storms appear
        threading.Thread(target=self._run, args=(token, fn, args), daemon=True,
                         name="explorerpro-fs").start()

    def _run(self, token, fn, args):
        try:
            result, error = fn(*args), None
        except Exception as exc:  # delivered to the GUI, never raised in the thread
            result, error = None, exc
        try:
            self.finished.emit(token, result, error)
        except RuntimeError:  # owner already destroyed (app shutdown)
            pass


def list_subfolders(path):
    """Sorted visible subfolders as (name, full_path); may block on slow drives."""
    entries = []
    for name in sorted(os.listdir(path), key=str.lower):
        if name.startswith('.'):
            continue
        full = os.path.join(path, name)
        try:
            # Cloud placeholders are reparse points; isdir() reads metadata only.
            if os.path.isdir(full):
                entries.append((name, full))
        except OSError:
            continue
    return entries
