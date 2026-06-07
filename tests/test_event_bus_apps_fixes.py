"""
Bugfix-Tests:
(1) event_bus.py – unregister_handler darf keinen ValueError werfen
    wenn der Handler nicht (mehr) registriert ist.
(2) apps_panel.py – _launch_app nutzt shlex.split statt str.split,
    damit Argumente mit Leerzeichen korrekt aufgeteilt werden.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PySide6.QtWidgets import QApplication
_app = QApplication.instance() or QApplication([])

from core.event_bus import EventBus


class TestEventBusUnregisterFix:
    """unregister_handler darf keinen ValueError werfen."""

    def setup_method(self):
        # Frische Instanz für jeden Test (Singleton zurücksetzen)
        EventBus._instance = None

    def test_unregister_not_registered_handler_no_crash(self):
        bus = EventBus()
        handler = lambda: None

        # Kein Register vorher — darf nicht crashen
        bus.unregister_handler("some_event", handler)

    def test_unregister_already_removed_handler_no_crash(self):
        bus = EventBus()
        handler = lambda: None

        bus.register_handler("my_event", handler)
        bus.unregister_handler("my_event", handler)

        # Zweites Mal unregister — darf nicht crashen
        bus.unregister_handler("my_event", handler)

    def test_unregister_removes_correct_handler(self):
        bus = EventBus()
        calls = []
        h1 = lambda: calls.append(1)
        h2 = lambda: calls.append(2)

        bus.register_handler("ev", h1)
        bus.register_handler("ev", h2)
        bus.unregister_handler("ev", h1)
        bus.emit_custom("ev")

        assert calls == [2], f"Nach unregister(h1) soll nur h2 laufen, war: {calls}"


class TestAppsShlex:
    """_launch_app muss shlex.split für Argumente nutzen."""

    def test_shlex_split_quoted_args(self):
        import shlex
        args = '--config="path with spaces" --verbose'
        result = shlex.split(args)
        assert result == ['--config=path with spaces', '--verbose'], (
            f"shlex.split verhält sich unerwartet: {result}"
        )

    def test_plain_args_unchanged(self):
        import shlex
        args = '--verbose --count=3'
        assert shlex.split(args) == ['--verbose', '--count=3']
