"""Run blocking filesystem calls off the GUI thread.

A hung network/cloud drive can block a call forever and Python threads cannot
be killed, so each request gets a daemon thread: an abandoned one never keeps
the app from exiting. Results come back as a queued Qt signal; callers drop
answers they no longer want (timeout, node collapsed, other path).
"""

import os
import threading
from itertools import chain, islice

from PySide6.QtCore import QObject, Signal


class AsyncFs(QObject):
    finished = Signal(object, object, object)  # token, result, exception
    preview = Signal(object, object)          # token, first bounded entries

    def submit_preview(self, token, fn, *args):
        """Emit one early page, then a complete sorted snapshot; no signal flood."""
        def collect():
            remaining = iter(fn(*args))
            first = list(islice(remaining, 128))
            first.sort(key=lambda entry: entry[0].lower())
            if first:
                self.preview.emit(token, first)
            return sorted(chain(first, remaining), key=lambda entry: entry[0].lower())
        self.submit(token, collect)

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


def iter_subfolders(path):
    """Stream visible subfolders; metadata stays in the filesystem worker."""
    with os.scandir(path) as entries:
        for entry in entries:
            if entry.name.startswith('.'):
                continue
            try:
                if entry.is_dir():
                    yield entry.name, entry.path
            except OSError:
                continue
