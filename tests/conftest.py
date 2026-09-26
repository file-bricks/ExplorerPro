"""Shared pytest setup for ExplorerPro's Qt-based test suite.

A single QApplication instance is created here, before any test module is
collected/imported, so the many `QApplication.instance() or QApplication([])`
calls scattered across individual test files (28 as of this writing) all
retrieve the SAME instance instead of racing to create their own.

Without this, widgets created across many test modules get garbage-collected
by Python in an unpredictable order relative to Qt's own C++ object
lifetime at interpreter shutdown -- observed as
"QObject: shared QObject was deleted directly" followed by a segfault
(exit 139) on Linux/macOS.

Note on the Windows crash (PYTEST_EXIT=-1073740791, STATUS_STACK_BUFFER_OVERRUN,
a few seconds after "365 passed" prints): reproduced this locally BOTH with
and without this conftest.py, so it is not caused by (or fixed by) the
QApplication-sharing/teardown-order issue this file addresses. Forcing an
early process exit (os._exit() / Win32 TerminateProcess) from
pytest_unconfigure was tried and did not prevent it either -- the crash
moved earlier but a native stack-corruption fault (Windows GS-cookie check
failure) still triggered. That points to a genuine memory-safety bug in a
native dependency (fitz/PyMuPDF and openpyxl are the two C-extension-heavy
libraries this suite exercises) rather than a Qt teardown-order problem,
and needs bisection across the 58 test files to localize -- out of scope
for this fix. Tracked separately; does not block release.
"""
from __future__ import annotations

import gc
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication([])


def pytest_sessionfinish(session, exitstatus):
    """Let Qt's event loop actually destroy widgets scheduled via
    deleteLater() before Python starts tearing down objects at interpreter
    exit. This is what prevents the shared-QObject-deleted warning on
    Linux/macOS; see module docstring for the separate, still-open Windows
    native crash."""
    app = QApplication.instance()
    if app is None:
        return
    for _ in range(5):
        app.processEvents()
    gc.collect()
    for _ in range(5):
        app.processEvents()
