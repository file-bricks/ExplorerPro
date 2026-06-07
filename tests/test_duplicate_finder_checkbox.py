"""
Bugfix-Test: duplicate_finder.py DuplicateFinderDialog –
Delete-Button muss aktiviert werden, wenn der User eine Checkbox
manuell anklickt (itemChanged-Signal war nicht verbunden).
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

from PySide6.QtCore import Qt
from modules.indexer.duplicate_finder import DuplicateFinderDialog


class TestDuplicateCheckboxFix:
    """Delete-Button muss auf manuelle Checkbox-Klicks reagieren."""

    def _make_dialog(self) -> DuplicateFinderDialog:
        return DuplicateFinderDialog.__new__(DuplicateFinderDialog)

    def _setup_dialog_with_duplicates(self) -> DuplicateFinderDialog:
        dialog = DuplicateFinderDialog(file_index=None)
        duplicates = {
            "abc123": ["/tmp/a.txt", "/tmp/b.txt"],
        }
        dialog._populate_tree(duplicates)
        dialog.duplicate_groups = duplicates
        dialog.delete_btn.setEnabled(False)
        return dialog

    def test_delete_btn_enabled_on_checkbox_check(self):
        """Checkbox manuell setzen → delete_btn wird aktiviert."""
        dialog = self._setup_dialog_with_duplicates()

        group = dialog.tree.topLevelItem(0)
        child = group.child(0)

        assert not dialog.delete_btn.isEnabled()

        # Checkbox programmatisch setzen (simuliert User-Klick)
        child.setCheckState(0, Qt.CheckState.Checked)

        assert dialog.delete_btn.isEnabled(), (
            "Delete-Button wurde nach Checkbox-Check NICHT aktiviert"
        )

    def test_delete_btn_disabled_when_all_unchecked(self):
        """Alle Checkboxen deaktivieren → delete_btn wird deaktiviert."""
        dialog = self._setup_dialog_with_duplicates()

        group = dialog.tree.topLevelItem(0)
        # Erst einschalten, dann ausschalten
        group.child(0).setCheckState(0, Qt.CheckState.Checked)
        assert dialog.delete_btn.isEnabled()

        group.child(0).setCheckState(0, Qt.CheckState.Unchecked)
        assert not dialog.delete_btn.isEnabled(), (
            "Delete-Button blieb aktiv obwohl alle Checkboxen deaktiviert wurden"
        )
