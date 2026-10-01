"""Native process regressions for collection and worker shutdown."""

import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize("automatic_before", [True, False])
@pytest.mark.parametrize("use_timer", [True, False])
def test_qt_cycles_are_destroyed_on_gui_thread(automatic_before, use_timer):
    script = f'''
import gc, sys, threading
sys.path.insert(0, 'src')
from PySide6.QtCore import QObject
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from core.gui_gc import install_gui_gc
app = QApplication([])
gc.enable() if {automatic_before!r} else gc.disable()
collector = install_gui_gc(app)
assert collector is install_gui_gc(app)
assert not gc.isenabled()
gui_thread = threading.get_ident()
deleted = []
qt_deleted = []
errors = []
class Probe(QObject):
    def __init__(self):
        super().__init__()
        self.cycle = self
        self.destroyed.connect(lambda: qt_deleted.append(threading.get_ident()))
    def __del__(self):
        deleted.append(threading.get_ident())
probe = Probe()
del probe
def allocate():
    for _ in range(10000):
        cycle = []
        cycle.append(cycle)
    for operation in (collector.collect, lambda: install_gui_gc(QApplication.instance()).close()):
        try:
            operation()
        except RuntimeError:
            errors.append('wrong-thread-rejected')
thread = threading.Thread(target=allocate)
thread.start()
thread.join(timeout=10)
assert not thread.is_alive()
assert errors == ['wrong-thread-rejected', 'wrong-thread-rejected']
assert deleted == [] and qt_deleted == [], (deleted, qt_deleted)
if {use_timer!r}:
    collector.timer.setInterval(1)
    collector.timer.start()
    QTest.qWait(100)
else:
    collector.collect()
assert deleted == [gui_thread], deleted
assert qt_deleted == [gui_thread], qt_deleted
collector.close()
collector.close()
assert gc.isenabled() is {automatic_before!r}
assert not collector.timer.isActive()
print('gui-collection-ok')
'''
    result = subprocess.run(
        [sys.executable, "-c", script], cwd=Path(__file__).resolve().parents[1],
        capture_output=True, text=True, timeout=25,
    )
    assert result.returncode == 0, result.stderr
    assert "gui-collection-ok" in result.stdout


def test_capacity_shutdown_drains_workers_before_restoring_gc():
    script = '''
import gc, sys, threading, time
sys.path.insert(0, 'src')
from PySide6.QtWidgets import QApplication
from core.gui_gc import install_gui_gc
from gui.sidebar.drive_capacity import capacity_executor, shutdown_capacity_executor
app = QApplication([])
collector = install_gui_gc(app)
entered = threading.Event()
def worker():
    entered.set()
    time.sleep(.1)
    assert not gc.isenabled()
    return 'finished'
future = capacity_executor().submit(worker)
assert entered.wait(5)
shutdown_capacity_executor()
assert future.done() and future.result() == 'finished'
collector.close()
assert gc.isenabled()
print('shutdown-ok')
'''
    result = subprocess.run(
        [sys.executable, "-c", script], cwd=Path(__file__).resolve().parents[1],
        capture_output=True, text=True, timeout=25,
    )
    assert result.returncode == 0, result.stderr
    assert "shutdown-ok" in result.stdout
