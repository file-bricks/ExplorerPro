"""GUI must stay responsive on slow drives; the last known state stays visible.

Slow drives are simulated by delaying os.listdir / Path.iterdir /
read_drive_usage for a marker path (seconds) and measuring how late a 20 ms
QTimer tick fires while the GUI handles the request.
"""
import os
import time
from pathlib import Path

import pytest
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QTreeWidgetItem

from core.drive_usage import DriveUsage
from gui.preview.preview_panel import DirectoryPreview
from gui.sidebar.sidebar_main import TreePanel

SLOW = os.path.join(os.path.abspath(os.sep), "ep_slow_drive_marker")
DELAY = 2.0
_real_listdir = os.listdir
_real_isdir = os.path.isdir


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    monkeypatch.setattr("core.drive_usage.cache_path", lambda: tmp_path / "usage.json", raising=False)
    getattr(TreePanel, "_dir_cache", {}).clear()


def pump(predicate, timeout=6.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        QApplication.processEvents()
        if predicate():
            return True
        time.sleep(0.005)
    return predicate()


class TickMeter:
    """Largest delay of a 20 ms timer = how long the event loop was blocked."""

    def __init__(self):
        self.last = time.monotonic()
        self.worst = 0.0
        self.timer = QTimer()
        self.timer.setInterval(20)
        self.timer.timeout.connect(self._tick)
        self.timer.start()

    def _tick(self):
        now = time.monotonic()
        self.worst = max(self.worst, now - self.last)
        self.last = now

    def stop(self):
        self.timer.stop()
        self.worst = max(self.worst, time.monotonic() - self.last)


@pytest.fixture
def slow_listdir(monkeypatch):
    def fake_listdir(path="."):
        if os.fspath(path) == SLOW:
            time.sleep(DELAY)
            return ["alpha", "beta"]
        return _real_listdir(path)

    def fake_isdir(path):
        return os.fspath(path).startswith(SLOW) or _real_isdir(path)

    monkeypatch.setattr(os, "listdir", fake_listdir)
    monkeypatch.setattr(os.path, "isdir", fake_isdir)


@pytest.fixture
def panel(monkeypatch):
    monkeypatch.setattr("gui.sidebar.sidebar_main.read_drive_usage",
                        lambda p: DriveUsage(1000, 400, 600))
    p = TreePanel()
    p.resize(300, 500)
    p.show()
    pump(lambda: not p._usage_requests)
    return p


def slow_node(panel):
    item = QTreeWidgetItem(["slow"])
    item.setData(0, Qt.ItemDataRole.UserRole, SLOW)
    item.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
    panel.tree.addTopLevelItem(item)
    return item


def names(item):
    return [item.child(i).text(0) for i in range(item.childCount())]


def test_expanding_slow_folder_does_not_block_event_loop(panel, slow_listdir):
    item = slow_node(panel)
    meter = TickMeter()
    item.setExpanded(True)
    assert pump(lambda: names(item) == ["alpha", "beta"])
    meter.stop()
    print(f"MEASURED expand worst tick gap: {meter.worst:.3f}s (listing takes {DELAY}s)")
    assert meter.worst < 1.0, f"GUI blocked for {meter.worst:.2f}s"


def test_placeholder_instead_of_freeze_on_first_load(panel, slow_listdir):
    item = slow_node(panel)
    item.setExpanded(True)
    assert item.childCount() == 1
    assert not item.child(0).data(0, Qt.ItemDataRole.UserRole)  # placeholder, not a folder
    assert pump(lambda: names(item) == ["alpha", "beta"])


def test_last_known_children_shown_until_fresh_state_arrives(panel, slow_listdir):
    TreePanel._dir_cache = {SLOW: [("old", os.path.join(SLOW, "old"))]}
    item = slow_node(panel)
    item.setExpanded(True)
    assert names(item) == ["old"]  # immediately, while the slow listing still runs
    assert pump(lambda: names(item) == ["alpha", "beta"])


def test_answer_for_collapsed_node_is_dropped(panel, slow_listdir):
    item = slow_node(panel)
    item.setExpanded(True)
    item.setExpanded(False)
    pump(lambda: not panel._pending)
    assert names(item) != ["alpha", "beta"]


def test_hanging_listing_times_out_and_late_answer_is_ignored(panel, slow_listdir):
    panel.LIST_TIMEOUT_MS = 100
    item = slow_node(panel)
    item.setExpanded(True)
    assert pump(lambda: "Keine Antwort" in item.child(0).text(0), timeout=2)
    time.sleep(DELAY)
    pump(lambda: False, timeout=0.2)
    assert "Keine Antwort" in item.child(0).text(0)  # late result did not overwrite


def test_failed_capacity_read_releases_request_and_shows_unavailable(monkeypatch):
    def boom(path):
        raise RuntimeError("helper failed")  # not an OSError: used to leave the row stuck

    monkeypatch.setattr("gui.sidebar.sidebar_main.read_drive_usage", boom)
    p = TreePanel()
    assert pump(lambda: not p._usage_requests)
    _, cap = next(iter(p._drive_rows.values()))
    assert not cap.has_usage
    assert "nicht verfügbar" in cap.details.text() or "unavailable" in cap.details.text()


def test_refresh_keeps_old_capacity_visible_and_is_throttled(monkeypatch):
    calls = []

    def slow(path):
        calls.append(path)
        time.sleep(0.5)
        return DriveUsage(1000, 500, 500)

    monkeypatch.setattr("gui.sidebar.sidebar_main.read_drive_usage", slow)
    p = TreePanel()
    assert pump(lambda: not p._usage_requests)
    n = len(calls)
    assert n == len(p._drive_rows)
    shown = {k: cap.details.text() for k, (_, cap) in p._drive_rows.items()}
    p.refresh_drive_usage()  # automatic call right after a read: throttled
    assert len(calls) == n
    p.refresh_drive_usage(force=True)  # button: reads again, old value stays visible
    assert pump(lambda: len(p._usage_requests) == n, timeout=1)
    assert {k: cap.details.text() for k, (_, cap) in p._drive_rows.items()} == shown
    assert pump(lambda: not p._usage_requests)


def test_last_capacity_is_persisted_and_shown_at_start(monkeypatch):
    monkeypatch.setattr("gui.sidebar.sidebar_main.read_drive_usage",
                        lambda p: DriveUsage(2000, 500, 1500))
    first = TreePanel()
    assert pump(lambda: not first._usage_requests)

    def never(path):
        time.sleep(1)
        raise OSError

    monkeypatch.setattr("gui.sidebar.sidebar_main.read_drive_usage", never)
    second = TreePanel()
    _, cap = next(iter(second._drive_rows.values()))
    assert cap.has_usage  # old state is there before any read finished
    pump(lambda: not second._usage_requests)


def test_directory_preview_does_not_block_and_shows_placeholder(monkeypatch, tmp_path):
    real = Path.iterdir

    def slow_iterdir(self):
        if self == tmp_path:
            time.sleep(DELAY)
        return real(self)

    monkeypatch.setattr(Path, "iterdir", slow_iterdir)
    (tmp_path / "f.txt").write_text("x")
    preview = DirectoryPreview()
    meter = TickMeter()
    preview.load_directory(str(tmp_path))
    assert "f.txt" not in preview.toPlainText()  # placeholder first
    assert pump(lambda: "f.txt" in preview.toPlainText())
    meter.stop()
    print(f"MEASURED preview worst tick gap: {meter.worst:.3f}s (iterdir takes {DELAY}s)")
    assert meter.worst < 1.0, f"GUI blocked for {meter.worst:.2f}s"


def test_directory_preview_drops_answer_for_other_folder(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir()
    b.mkdir()
    (a / "only_a.txt").write_text("x")
    (b / "only_b.txt").write_text("x")
    preview = DirectoryPreview()
    preview.load_directory(str(a))
    preview.load_directory(str(b))
    assert pump(lambda: "only_b.txt" in preview.toPlainText())
    pump(lambda: False, timeout=0.2)
    assert "only_a.txt" not in preview.toPlainText()
