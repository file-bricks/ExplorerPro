"""Shared pytest setup and teardown for ExplorerPro.

1. Safe Symlink & Numbered Dir Cleanup (Windows):
   On Windows, pytest's `cleanup_dead_symlinks` in `_pytest.pathlib` checks
   `left_dir.resolve().exists()` on `pytest-current` (a directory symlink).
   Without Developer Mode or when symlink permissions differ, `exists()` raises
   `PermissionError: [WinError 5] Zugriff verweigert: '...\\pytest-current'`.
   When raised inside `tmp_path_factory._exit_stack.close()` at sessionfinish,
   CPython aborts with `Fatal Python error: Aborted` / `STATUS_STACK_BUFFER_OVERRUN`
   (exit code 1). Suppressing OSError in `cleanup_dead_symlinks` and `cleanup_numbered_dir`
   guards against this Windows-specific teardown failure.

2. Clean Qt Top-Level Widget Teardown:
   Closes and schedules `deleteLater()` for remaining top-level Qt widgets
   and processes pending events, preventing dangling QObject destructors
   at interpreter exit.
"""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    import _pytest.pathlib as _pytest_pathlib

    _orig_cleanup_dead_symlinks = _pytest_pathlib.cleanup_dead_symlinks
    _orig_cleanup_numbered_dir = _pytest_pathlib.cleanup_numbered_dir

    def _safe_cleanup_dead_symlinks(root):
        try:
            _orig_cleanup_dead_symlinks(root)
        except OSError:
            pass

    def _safe_cleanup_numbered_dir(root, prefix, keep, consider_lock_dead_if_created_before):
        try:
            _orig_cleanup_numbered_dir(root, prefix, keep, consider_lock_dead_if_created_before)
        except OSError:
            pass

    _pytest_pathlib.cleanup_dead_symlinks = _safe_cleanup_dead_symlinks
    _pytest_pathlib.cleanup_numbered_dir = _safe_cleanup_numbered_dir
except (ImportError, AttributeError):
    pass

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(autouse=True)
def _cleanup_qt_widgets():
    """Ensure top-level Qt widgets created during a test are closed and drained."""
    yield
    app = QApplication.instance()
    if app is not None:
        for widget in app.topLevelWidgets():
            try:
                widget.close()
                widget.deleteLater()
            except Exception:
                pass
        app.processEvents()


def pytest_sessionfinish(session, exitstatus):
    """Drain any remaining events before interpreter shutdown."""
    app = QApplication.instance()
    if app is not None:
        try:
            for widget in app.topLevelWidgets():
                try:
                    widget.close()
                    widget.deleteLater()
                except Exception:
                    pass
            for _ in range(5):
                app.processEvents()
        except Exception:
            pass
