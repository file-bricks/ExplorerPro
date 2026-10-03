"""Exercise the application's GUI-thread cyclic collection policy."""

import os

import pytest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication
from core.gui_gc import install_gui_gc

_application = QApplication.instance() or QApplication([])
_collector = install_gui_gc(_application)


@pytest.fixture(autouse=True)
def collect_gui_cycles():
    yield
    _collector.collect()


@pytest.fixture(scope='session', autouse=True)
def gui_runtime():
    yield
    _collector.close()
