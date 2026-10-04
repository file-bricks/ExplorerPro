import os
import threading
import time
from concurrent.futures import Future
from types import SimpleNamespace

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest
from PySide6.QtCore import QDir, Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest

from core.drive_usage import DriveUsage, format_capacity, read_drive_usage
from gui.sidebar.drive_capacity import DriveCapacityWidget
from gui.sidebar.sidebar_main import TreePanel
from translator import get_translator

app = QApplication.instance() or QApplication([])


def wait_until(predicate):
    deadline = time.monotonic() + 4
    while not predicate():
        assert time.monotonic() < deadline, 'Background result did not arrive'
        app.processEvents()
        QTest.qWait(5)


@pytest.fixture(autouse=True)
def german():
    tr = get_translator()
    old = tr.get_language()
    tr.set_language('de')
    yield
    tr.set_language(old)


@pytest.mark.parametrize('used,free,percent', [(0, 1000, 0), (1, 999, .1), (500, 500, 50), (1000, 0, 100)])
def test_usage_values_and_bar(used, free, percent):
    widget = DriveCapacityWidget('X:/')
    widget.set_usage(DriveUsage(1000, used, free))
    assert widget.bar.value() == round(percent * 10)
    assert widget.bar.format() == f'{percent:.1f}% belegt'
    assert f'{free} B frei' in widget.details.text()
    assert f'{used} B belegt' in widget.details.text()
    assert '1000 B gesamt' in widget.details.text()
    assert not widget.bar.isHidden()
    assert widget.bar.format() in widget.accessibleDescription()


@pytest.mark.parametrize('values', [(0, 0, 0), (100, -1, 20), (100, 101, 0), (100, 30, 101)])
def test_invalid_capacity_not_shown_as_real_data(values):
    with pytest.raises(ValueError):
        DriveUsage(*values)


def test_unavailable_discards_previous_measurement():
    widget = DriveCapacityWidget('X:/')
    widget.set_usage(DriveUsage(100, 80, 20))
    widget.set_usage(None)
    assert widget.details.text() == 'Speicherbelegung nicht verfügbar'
    assert widget.bar.isHidden()
    assert '80' not in widget.accessibleDescription()


def test_real_operating_system_capacity(tmp_path):
    import shutil
    expected = shutil.disk_usage(tmp_path)
    actual = read_drive_usage(str(tmp_path))
    assert actual.total == expected.total
    # Free space can change between OS calls; compare accounting and valid range.
    assert actual.used + actual.free == actual.total if os.name == 'nt' else actual.used + actual.free <= actual.total
    assert 0 <= actual.used_percent <= 100


def test_binary_units():
    assert format_capacity(1024) == '1.0 KiB'
    assert format_capacity(1024 ** 3) == '1.0 GiB'


def make_panel(monkeypatch, read):
    monkeypatch.setattr(QDir, 'drives', lambda: [SimpleNamespace(absolutePath=lambda: 'X:/')])
    monkeypatch.setattr('gui.sidebar.sidebar_main.read_drive_usage', read)
    return TreePanel()


def test_cancelled_drive_query_is_reported_as_unavailable(monkeypatch):
    panel = make_panel(monkeypatch, lambda _: DriveUsage(100, 20, 80))
    try:
        wait_until(lambda: not panel._usage_requests)
        cancelled = Future()
        cancelled.cancel()
        panel._usage_requests['X:/'] = cancelled

        panel._collect_drive_usage()

        assert not panel._usage_requests
        assert panel._drive_rows['X:/'][1].details.text() == 'Speicherbelegung nicht verfügbar'
    finally:
        panel.close()


def test_slow_query_keeps_gui_responsive_and_deduplicates(monkeypatch):
    entered, release = threading.Event(), threading.Event()
    threads = []
    main_thread = threading.get_ident()

    def read(path):
        threads.append(threading.get_ident())
        entered.set()
        assert release.wait(4)
        return DriveUsage(1000, 250, 750)

    panel = make_panel(monkeypatch, read)
    try:
        wait_until(entered.is_set)
        for _ in range(5):
            panel.refresh_drive_usage()
        app.processEvents()
        assert len(threads) == 1
        assert threads[0] != main_thread
        assert panel._drive_rows['X:/'][1].bar.isHidden()
        release.set()
        wait_until(lambda: not panel._usage_requests)
        assert panel._drive_rows['X:/'][1].bar.value() == 250
        panel.refresh_drives_button.click()
        wait_until(lambda: not panel._usage_requests)
        assert len(threads) == 2
    finally:
        release.set()
        for future in panel._usage_requests.values():
            future.result(timeout=4)
        panel.close()


def test_failed_query_and_recovery(monkeypatch):
    def unavailable(path):
        raise OSError('Device not ready')

    panel = make_panel(monkeypatch, unavailable)
    wait_until(lambda: not panel._usage_requests)
    item, widget = panel._drive_rows['X:/']
    assert item.text(0) == ''  # embedded title must not overlap tree text
    assert item.data(0, Qt.ItemDataRole.AccessibleTextRole) == 'X:/'
    assert 'nicht verfügbar' in widget.details.text()
    monkeypatch.setattr('gui.sidebar.sidebar_main.read_drive_usage', lambda path: DriveUsage(100, 100, 0))
    panel.refresh_drive_usage()
    wait_until(lambda: not panel._usage_requests)
    assert widget.bar.value() == 1000
    assert item.data(0, Qt.ItemDataRole.UserRole) == 'X:/'
    selected = []
    panel.folder_selected.connect(selected.append)
    panel._on_item_clicked(item, 0)
    assert selected == ['X:/']
    panel.close()


def test_panel_destroyed_while_query_is_running(monkeypatch):
    from PySide6.QtCore import QCoreApplication, QEvent, QObject
    from shiboken6 import isValid
    entered, release = threading.Event(), threading.Event()

    def read(path):
        entered.set()
        assert release.wait(4)
        return DriveUsage(100, 20, 80)

    panel = make_panel(monkeypatch, read)
    futures = list(panel._usage_requests.values())
    unrelated = None
    try:
        wait_until(entered.is_set)
        unrelated = QObject()
        unrelated.deleteLater()
        panel.deleteLater()
        QCoreApplication.sendPostedEvents(panel, QEvent.Type.DeferredDelete)
        assert isValid(unrelated), 'Panel cleanup must not delete unrelated Qt objects'
    finally:
        release.set()
        for future in futures:
            future.result(timeout=4)
        if unrelated is not None and isValid(unrelated):
            QCoreApplication.sendPostedEvents(unrelated, QEvent.Type.DeferredDelete)
        app.processEvents()


def test_capacity_text_placeholders_in_every_language():
    tr = get_translator()
    for lang in tr.get_supported_languages():
        tr.set_language(lang)
        widget = DriveCapacityWidget('X:/')
        widget.set_usage(DriveUsage(1000, 500, 500))
        assert '500 B' in widget.details.text() and '1000 B' in widget.details.text()
        assert '{' not in widget.details.text()
        assert '50.0' in widget.bar.format()


def test_narrow_sidebar_preserves_wrapped_capacity_text(monkeypatch):
    panel = make_panel(monkeypatch, lambda path: DriveUsage(1024 ** 4, 1024 ** 3, 1024 ** 4 - 1024 ** 3))
    panel.resize(200, 600)
    panel.show()
    wait_until(lambda: not panel._usage_requests)
    app.processEvents()
    item, widget = panel._drive_rows['X:/']
    required = widget.layout().totalHeightForWidth(widget.width())
    assert item.sizeHint(0).height() >= required
    assert widget.height() >= required
    panel.close()


def test_pending_capacity_job_finishes_before_interpreter_exit():
    import subprocess
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    script = '''
import sys, time
sys.path.insert(0, 'src')
from PySide6.QtWidgets import QApplication
from core.drive_usage import DriveUsage
from gui.sidebar import drive_capacity
app = QApplication([])
def slow_read(path):
    time.sleep(.2)
    print('capacity-job-finished', flush=True)
    return DriveUsage(100, 20, 80)
drive_capacity.capacity_executor().submit(slow_read, 'X:/')
'''
    result = subprocess.run([sys.executable, '-c', script], cwd=root, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert 'capacity-job-finished' in result.stdout


def test_destroyed_panel_cancels_queued_layout_refresh(monkeypatch, capsys):
    from PySide6.QtCore import QCoreApplication, QEvent
    from shiboken6 import isValid
    panel = make_panel(monkeypatch, lambda path: DriveUsage(100, 20, 80))
    wait_until(lambda: not panel._usage_requests)
    panel.resize(200, 600)
    panel.show()
    timer = panel._resize_timer
    timer.start(0)
    assert timer.isActive()
    panel.deleteLater()
    QCoreApplication.sendPostedEvents(panel, QEvent.Type.DeferredDelete)
    assert not isValid(timer)
    app.processEvents()
    assert 'RuntimeError' not in capsys.readouterr().err
