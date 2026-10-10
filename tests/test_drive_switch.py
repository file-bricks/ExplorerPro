"""Switching drives must not hang the main area; drive start pages are preloaded.

A slow/dead drive is simulated by delaying os.path.isdir/isfile/os.listdir for a
marker path; a 20 ms QTimer measures how long the event loop was blocked.
"""
import os
import time

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from gui.browser import file_browser as fb_mod
from gui.browser.file_browser import FileBrowser

SLOW = os.path.join(os.path.abspath(os.sep), "ep_slow_drive_marker")
DELAY = 2.0
_isdir, _isfile, _listdir = os.path.isdir, os.path.isfile, os.listdir


def pump(predicate, timeout=6.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        QApplication.processEvents()
        if predicate():
            return True
        time.sleep(0.005)
    return predicate()


class TickMeter:
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


@pytest.fixture(autouse=True)
def async_navigation(monkeypatch):
    monkeypatch.setattr(FileBrowser, "ASYNC_VALIDATE", True, raising=False)


@pytest.fixture
def slow_drive(monkeypatch):
    calls = {"stat": 0}

    def slow(real):
        def wrapper(path):
            if os.fspath(path).startswith(SLOW):
                calls["stat"] += 1
                time.sleep(DELAY)
                return True
            return real(path)
        return wrapper

    monkeypatch.setattr(os.path, "isdir", slow(_isdir))
    monkeypatch.setattr(os.path, "isfile", lambda p: False if os.fspath(p).startswith(SLOW) else _isfile(p))
    monkeypatch.setattr(os, "listdir", lambda p=".": [] if os.fspath(p) == SLOW else _listdir(p))
    return calls


@pytest.fixture
def browser():
    b = FileBrowser()
    b.resize(800, 500)
    b.show()
    pump(lambda: False, timeout=1.5)  # let the initial real folder settle first
    yield b
    b.close()
    b.deleteLater()
    QApplication.processEvents()


def test_switch_to_slow_drive_does_not_block_event_loop(browser, slow_drive):
    meter = TickMeter()
    browser.navigate_to(SLOW)
    assert pump(lambda: browser.current_path == SLOW)
    meter.stop()
    print(f"MEASURED drive switch worst tick gap: {meter.worst:.3f}s (stat takes {DELAY}s)")
    assert meter.worst < 1.0, f"GUI blocked for {meter.worst:.2f}s"


def test_busy_hint_while_waiting(browser, slow_drive):
    browser.navigate_to(SLOW)
    assert not browser._busy.isHidden()  # "wird geladen …" instead of a hang
    assert browser.current_path == SLOW and browser.table.isHidden()  # target shown, empty page
    assert pump(lambda: not browser.table.isHidden())  # confirmed: the page opens


def test_hanging_drive_times_out_with_hint_and_late_answer_is_ignored(browser, slow_drive):
    browser.NAV_TIMEOUT_MS = 100
    browser.navigate_to(SLOW)
    assert pump(lambda: "Keine Antwort" in browser._busy.text(), timeout=2)
    pump(lambda: False, timeout=DELAY + 0.5)
    assert browser.current_path == SLOW and browser.table.isHidden()  # empty page stays, late answer ignored


def test_newer_navigation_wins_over_slow_one(browser, slow_drive, tmp_path):
    browser.navigate_to(SLOW)
    browser.navigate_to(str(tmp_path))
    assert pump(lambda: browser.current_path == str(tmp_path))
    pump(lambda: False, timeout=DELAY + 0.5)
    assert browser.current_path == str(tmp_path)


def test_preloaded_drive_is_shown_at_once_without_any_stat(browser, slow_drive):
    browser.PRELOAD_GAP_MS = 1
    browser.preload_roots([SLOW])
    assert pump(lambda: fb_mod._norm(SLOW) in browser._known_dirs)
    slow_drive["stat"] = 0
    began = time.monotonic()
    browser.navigate_to(SLOW)
    assert browser.current_path == SLOW  # immediately, no pumping
    assert time.monotonic() - began < 0.5
    assert slow_drive["stat"] == 0


def test_preload_order_local_first_one_at_a_time_and_hanging_drive_does_not_stall(browser, monkeypatch):
    kinds = {"J:\\": 2, "H:\\": 0, "K:\\": 1, "I:\\": 0}
    seen = []

    def probe(path):
        seen.append(path)
        if path == "H:\\":
            time.sleep(0.6)  # hangs past the timeout
        return True

    monkeypatch.setattr(fb_mod, "drive_kind", lambda p: kinds[p])
    monkeypatch.setattr(fb_mod, "_probe", probe)
    browser.PRELOAD_GAP_MS = 1
    browser.PRELOAD_TIMEOUT_MS = 100
    browser.preload_roots(list(kinds))
    pump(lambda: len(seen) == 4, timeout=4)
    assert len(seen) == 4
    assert seen == ["H:\\", "I:\\", "K:\\", "J:\\"]  # local disks first, then removable, then network
    assert fb_mod._norm("H:\\") not in browser._known_dirs  # timed out: not trusted
    assert fb_mod._norm("I:\\") in browser._known_dirs


# ---- unreachable targets show an empty page, never the old entries --------------------

UNREACHABLE = os.path.join(os.path.abspath(os.sep), "ep_unreachable_drive_marker")


def rows(browser):
    return browser.proxy.rowCount(browser.table.rootIndex())


@pytest.fixture
def filled(browser, tmp_path):
    for name in ("a.txt", "b.txt", "c.txt"):
        (tmp_path / name).write_text("x")
    browser.navigate_to(str(tmp_path))
    assert pump(lambda: browser.current_path == str(tmp_path) and rows(browser) >= 3, timeout=12), (browser.current_path, browser.table.isHidden(), browser.model.rootPath(), browser.model.rowCount(browser.model.index(str(tmp_path))), browser.model.canFetchMore(browser.model.index(str(tmp_path))), browser._tokens, browser.table.rootIndex().isValid())
    return browser


@pytest.mark.parametrize("failure", ["none", "error"])
def test_unreachable_target_shows_empty_page_with_status_not_old_entries(filled, monkeypatch, failure):
    def classify(path):
        if failure == "error":
            raise OSError("drive not ready")
        return None

    monkeypatch.setattr(fb_mod, "_classify", classify)
    filled.navigate_to(UNREACHABLE)
    assert filled.current_path == UNREACHABLE  # address bar shows the target at once
    assert filled.table.isHidden()  # empty page at once: the old entries are gone
    assert pump(lambda: "nicht erreichbar" in filled._busy.text() or "not reachable" in filled._busy.text())
    assert filled.table.isHidden() and not filled._busy.isHidden()  # status only on the empty page


def test_back_and_retry_work_after_unreachable(filled, monkeypatch, tmp_path):
    answers = [None]
    real = fb_mod._classify
    monkeypatch.setattr(fb_mod, "_classify", lambda p: answers[0] if p == UNREACHABLE else real(p))
    filled.navigate_to(UNREACHABLE)
    assert pump(lambda: "nicht erreichbar" in filled._busy.text() or "not reachable" in filled._busy.text())
    filled.go_back()
    assert filled.current_path == str(tmp_path)
    assert pump(lambda: rows(filled) >= 3)
    assert filled._busy.isHidden()
    answers[0] = "dir"  # drive is back: a new click checks again
    filled.navigate_to(UNREACHABLE)
    assert pump(lambda: not filled.table.isHidden())
    assert filled.current_path == UNREACHABLE


def test_timeout_keeps_empty_page(filled, monkeypatch):
    monkeypatch.setattr(fb_mod, "_classify", lambda p: (time.sleep(DELAY), "dir")[1])
    filled.NAV_TIMEOUT_MS = 100
    filled.navigate_to(UNREACHABLE)
    assert filled.table.isHidden() and filled.current_path == UNREACHABLE
    assert pump(lambda: "Keine Antwort" in filled._busy.text() or "No response" in filled._busy.text(), timeout=2)
    pump(lambda: False, timeout=DELAY + 0.5)  # the late answer is ignored
    assert filled.table.isHidden()


def test_known_network_path_is_rechecked_and_dropped_when_gone(filled, monkeypatch, tmp_path):
    target = tmp_path / "net"
    target.mkdir()
    (target / "f.txt").write_text("x")
    monkeypatch.setattr(fb_mod, "drive_kind", lambda p: 2)  # pretend: network drive
    filled._known_dirs.add(fb_mod._norm(str(target)))
    monkeypatch.setattr(fb_mod, "_classify", lambda p: None)  # it went away
    filled.navigate_to(str(target))
    assert filled.current_path == str(target) and not filled.table.isHidden()  # last state at once
    assert pump(lambda: filled.table.isHidden())  # re-check failed: empty page
    assert fb_mod._norm(str(target)) not in filled._known_dirs
