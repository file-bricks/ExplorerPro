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

from gui.sidebar.sidebar_main import Sidebar


def test_sidebar_tab_buttons_expose_accessible_context() -> None:
    sidebar = Sidebar()

    expected = {
        0: ("Ordner", "Laufwerken und Schnellzugriff"),
        1: ("Favoriten", "gespeicherten Favoritenordnern"),
        2: ("Suche", "Volltext- und Dateisuche"),
        3: ("Apps", "häufig genutzten Programmen"),
        4: ("Prompts", "lokalen Prompt-Vorlagen"),
        5: ("Sync", "Ordnerabgleich"),
    }

    for idx, (name, description_fragment) in expected.items():
        button = sidebar.btn_group.button(idx)
        assert button is not None
        assert button.objectName() == f"sidebar_tab_{idx}"
        assert button.accessibleName() == name
        assert description_fragment in button.accessibleDescription()
        assert button.toolTip() == name
        assert button.statusTip() == button.accessibleDescription()
