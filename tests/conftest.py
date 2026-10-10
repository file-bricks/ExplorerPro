"""Exercise the application's GUI-thread cyclic collection policy."""

import os

import pytest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication
from core.gui_gc import install_gui_gc
from gui.sidebar.drive_capacity import shutdown_capacity_executor

_application = QApplication.instance() or QApplication([])
_collector = install_gui_gc(_application)


# Windows: pytest's dead-symlink cleanup can raise PermissionError at session
# teardown (WinError 5 on `pytest-current`), which aborts CPython with
# STATUS_STACK_BUFFER_OVERRUN. Suppress OSError in those cleanup helpers.
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


@pytest.fixture(autouse=True)
def collect_gui_cycles():
    yield
    _collector.collect()


@pytest.fixture(autouse=True)
def isolated_drive_usage_cache(tmp_path, monkeypatch):
    """Tests never read or write the user's real ~/.explorerpro capacity cache."""
    monkeypatch.setattr('core.drive_usage.cache_path', lambda: tmp_path / 'drive_usage_cache.json')


@pytest.fixture(scope='session', autouse=True)
def gui_runtime():
    yield
    try:
        shutdown_capacity_executor()
    finally:
        _collector.close()
