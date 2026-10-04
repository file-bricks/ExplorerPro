"""Native process regressions for collection and worker shutdown."""

import os
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


def _isolated_qt_env(tmp_path):
    profile = tmp_path / 'profile'
    directories = {
        'USERPROFILE': profile,
        'HOME': profile,
        'APPDATA': profile / 'AppData' / 'Roaming',
        'LOCALAPPDATA': profile / 'AppData' / 'Local',
        'XDG_CONFIG_HOME': profile / '.config',
        'XDG_CACHE_HOME': profile / '.cache',
    }
    for directory in directories.values():
        directory.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update({key: str(value) for key, value in directories.items()})
    env['QT_QPA_PLATFORM'] = 'offscreen'
    return env


@pytest.mark.parametrize('automatic_before', [True, False])
def test_close_restores_gc_policy_when_collection_fails(tmp_path, automatic_before):
    script = f'''
import gc, sys
sys.path.insert(0, 'src')
from PySide6.QtWidgets import QApplication
from core.gui_gc import install_gui_gc
app = QApplication([])
gc.enable() if {automatic_before!r} else gc.disable()
collector = install_gui_gc(app)
def fail_collect():
    raise RuntimeError('collect-failed')
collector.collect = fail_collect
try:
    collector.close()
except RuntimeError as error:
    assert str(error) == 'collect-failed'
else:
    raise AssertionError('collection failure was swallowed')
assert collector._closed
assert gc.isenabled() is {automatic_before!r}
collector.close()
assert gc.isenabled() is {automatic_before!r}
print('gc-close-error-restored')
'''
    result = subprocess.run(
        [sys.executable, '-c', script],
        cwd=Path(__file__).resolve().parents[1],
        env=_isolated_qt_env(tmp_path),
        capture_output=True,
        text=True,
        timeout=25,
    )
    assert result.returncode == 0, result.stderr
    assert 'gc-close-error-restored' in result.stdout


def test_install_start_failure_keeps_existing_gc_policy(tmp_path):
    script = '''
import gc, sys
sys.path.insert(0, 'src')
from PySide6.QtWidgets import QApplication
import core.gui_gc as gui_gc
app = QApplication([])
class Signal:
    def connect(self, callback):
        self.callback = callback
class FailingTimer:
    def __init__(self, parent):
        self.timeout = Signal()
    def setInterval(self, interval):
        self.interval = interval
    def start(self):
        raise RuntimeError('timer-start-failed')
gui_gc.QTimer = FailingTimer
gc.enable()
try:
    gui_gc.install_gui_gc(app)
except RuntimeError as error:
    assert str(error) == 'timer-start-failed'
else:
    raise AssertionError('timer start failure was swallowed')
assert gc.isenabled(), 'GC policy changed before timer start succeeded'
print('gc-install-start-error-restored')
'''
    result = subprocess.run(
        [sys.executable, '-c', script],
        cwd=Path(__file__).resolve().parents[1],
        env=_isolated_qt_env(tmp_path),
        capture_output=True,
        text=True,
        timeout=25,
    )
    assert result.returncode == 0, result.stderr
    assert 'gc-install-start-error-restored' in result.stdout


def test_main_closes_gc_collector_when_application_setup_fails(tmp_path):
    script = '''
import sys, types
sys.path.insert(0, 'src')
import main
sys.argv = []
closed = []
class Collector:
    def close(self):
        closed.append(True)
collector = Collector()
main.install_gui_gc = lambda app: collector
class Translator:
    def get_language(self):
        return 'en'
module = types.ModuleType('translator')
module.get_translator = lambda: Translator()
sys.modules['translator'] = module
def fail_setup(app, language):
    raise RuntimeError('application-setup-failed')
main.install_qt_translations = fail_setup
try:
    main.main()
except RuntimeError as error:
    assert str(error) == 'application-setup-failed'
else:
    raise AssertionError('setup failure was swallowed')
assert closed == [True], closed
print('main-setup-close-restored')
'''
    result = subprocess.run(
        [sys.executable, '-c', script],
        cwd=Path(__file__).resolve().parents[1],
        env=_isolated_qt_env(tmp_path),
        capture_output=True,
        text=True,
        timeout=25,
    )
    assert result.returncode == 0, result.stderr
    assert 'main-setup-close-restored' in result.stdout


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
