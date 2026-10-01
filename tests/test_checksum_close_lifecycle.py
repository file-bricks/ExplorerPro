"""A dialog must retain its native QThread until the worker actually exits."""

import threading
import time
import subprocess
import sys
from pathlib import Path

import pytest
from PySide6.QtWidgets import QDialog

from core.checksum_service import ChecksumWorker
from gui.checksum_dialog import ChecksumDialog


@pytest.mark.parametrize('action,result', [
    ('accept', QDialog.DialogCode.Accepted),
    ('reject', QDialog.DialogCode.Rejected),
    ('close', QDialog.DialogCode.Rejected),
])
def test_close_remains_responsive_and_keeps_running_worker(qtbot, monkeypatch, tmp_path, action, result):
    entered, release = threading.Event(), threading.Event()

    def blocked_read(worker):
        entered.set()
        release.wait(5)

    monkeypatch.setattr(ChecksumWorker, 'run', blocked_read)
    sample = tmp_path / 'sample.txt'
    sample.write_text('slow storage', encoding='utf-8')
    dialog = ChecksumDialog(str(sample))
    dialog.show()
    completed = []
    dialog.finished.connect(completed.append)
    try:
        assert entered.wait(2)
        started = time.monotonic()
        getattr(dialog, action)()
        assert time.monotonic() - started < .3
        qtbot.wait(40)
        assert dialog.isVisible()
        assert dialog.worker.isRunning()
        assert dialog.worker.is_cancelled()
        assert completed == []
        # Repeated close requests must not emit duplicate completion signals.
        getattr(dialog, action)()
        release.set()
        qtbot.waitUntil(lambda: completed == [int(result)], timeout=3000)
        assert not dialog.isVisible()
        assert not dialog.worker.isRunning()
    finally:
        release.set()
        dialog.worker.wait(2000)
        dialog.close()


def test_finished_cleanup_does_not_destroy_running_native_thread(tmp_path):
    script = '''
import sys, threading
from pathlib import Path
sys.path.insert(0, 'src')
from PySide6.QtCore import QCoreApplication, QEvent, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from core.checksum_service import ChecksumWorker
from gui.checksum_dialog import ChecksumDialog
app = QApplication([])
app.setQuitOnLastWindowClosed(False)
entered, release = threading.Event(), threading.Event()
def read(worker):
    entered.set()
    release.wait(5)
ChecksumWorker.run = read
dialog = ChecksumDialog(sys.argv[1])
dialog.show()
dialog.finished.connect(dialog.deleteLater)
assert entered.wait(2)
QTimer.singleShot(1500, release.set)
dialog.accept()
for _ in range(200):
    QTest.qWait(10)
QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
print('native-close-ok')
'''
    sample = tmp_path / 'slow.txt'
    sample.write_text('sample', encoding='utf-8')
    result = subprocess.run([sys.executable, '-X', 'faulthandler', '-c', script, str(sample)],
                            cwd=Path(__file__).resolve().parents[1], capture_output=True,
                            text=True, timeout=15)
    assert result.returncode == 0, (result.returncode, result.stderr)
    assert 'native-close-ok' in result.stdout
