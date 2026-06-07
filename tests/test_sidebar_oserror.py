"""
Bugfix-Test: sidebar_main.py TreePanel._on_item_expanded() –
Nur PermissionError wurde abgefangen; andere OSError-Varianten
(z.B. [WinError 21] Gerät nicht bereit) propagierten unkontrolliert.
Behoben durch Fangen von OSError (Oberklasse, schließt PermissionError ein).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PySide6.QtWidgets import QApplication
_app = QApplication.instance() or QApplication([])

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTreeWidgetItem

from gui.sidebar.sidebar_main import TreePanel


class TestTreePanelOsErrorFix:
    """_on_item_expanded muss alle OSError-Varianten abfangen."""

    def _make_tree(self) -> TreePanel:
        return TreePanel()

    def test_permission_error_handled(self):
        """PermissionError (OSError-Subklasse) darf keinen Crash verursachen."""
        panel = self._make_tree()

        item = QTreeWidgetItem(["/fake/path"])
        item.setData(0, Qt.ItemDataRole.UserRole, "/fake/path")
        panel.tree.addTopLevelItem(item)

        with patch("os.listdir", side_effect=PermissionError("Zugriff verweigert")):
            panel._on_item_expanded(item)  # darf nicht crashen

    def test_generic_oserror_handled(self):
        """Generische OSError (z.B. Gerät nicht bereit) darf keinen Crash verursachen."""
        panel = self._make_tree()

        item = QTreeWidgetItem(["/fake/drive"])
        item.setData(0, Qt.ItemDataRole.UserRole, "/fake/drive")
        panel.tree.addTopLevelItem(item)

        with patch("os.listdir", side_effect=OSError(21, "Das Gerät ist nicht bereit")):
            panel._on_item_expanded(item)  # darf nicht crashen
