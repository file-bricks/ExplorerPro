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
    return b


def test_switch_to_slow_drive_does_not_block_event_loop(browser, slow_drive):
    meter = TickMeter()
    browser.navigate_to(SLOW)
    assert pump(lambda: browser.current_path == SLOW)
    meter.stop()
    print(f"MEASURED drive switch worst tick gap: {meter.worst:.3f}s (stat takes {DELAY}s)")
    assert meter.worst < 1.0, f"GUI blocked for {meter.worst:.2f}s"


def test_busy_hint_while_waiting(browser, slow_drive):
    start = browser.current_path
    browser.navigate_to(SLOW)
    assert not browser._busy.isHidden()  # "wird geladen …" instead of a hang
    assert browser.current_path == start  # old view stays usable meanwhile
    assert pump(lambda: browser.current_path == SLOW)


def test_hanging_drive_times_out_with_hint_and_late_answer_is_ignored(browser, slow_drive):
    browser.NAV_TIMEOUT_MS = 100
    start = browser.current_path
    browser.navigate_to(SLOW)
    assert pump(lambda: "Keine Antwort" in browser._busy.text(), timeout=2)
    pump(lambda: False, timeout=DELAY + 0.5)
    assert browser.current_path == start


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
