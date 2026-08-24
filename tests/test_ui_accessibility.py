from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication([])

from gui.status_bar import PrivacyIndicator, StatusBarWidget
from gui.browser.file_browser import FileBrowser
from gui.sidebar.sidebar_main import TreePanel, FavoritesPanel
from modules.editor.quick_editor import QuickEditorDialog
from modules.indexer.duplicate_finder import DuplicateFinderDialog
from modules.sync.sync_manager import SyncPair, SyncPairDialog, SyncPanel


def test_privacy_indicator_accessibility_and_keyboard():
    indicator = PrivacyIndicator()
    assert indicator.accessibleName() == "Datenschutz-Status"
    assert "Sicher" in indicator.toolTip() or "sicher" in indicator.accessibleDescription()
    assert indicator.focusPolicy() == Qt.FocusPolicy.StrongFocus

    indicator.set_status("yellow")
    assert "Gelb" in indicator.accessibleDescription() or "Warnung" in indicator.accessibleDescription()

    indicator.set_status("red")
    assert "Rot" in indicator.accessibleDescription() or "blockiert" in indicator.accessibleDescription()

    # Keyboard activation via Space / Enter
    clicked = []
    indicator.clicked.connect(lambda: clicked.append(True))

    event_space = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Space, Qt.KeyboardModifier.NoModifier)
    indicator.keyPressEvent(event_space)
    assert len(clicked) == 1

    event_enter = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier)
    indicator.keyPressEvent(event_enter)
    assert len(clicked) == 2


def test_status_bar_widget_accessibility():
    status_bar = StatusBarWidget()
    assert status_bar.path_label.accessibleName() == "Aktueller Ordnerpfad"
    assert status_bar.file_count_label.accessibleName() == "Elementanzahl"
    assert status_bar.space_label.accessibleName() == "Speicherplatzanzeige"
    assert status_bar.sync_label.accessibleName() == "Synchronisationsstatus"

    status_bar.update_path("/test/path/folder")
    assert "/test/path/folder" in status_bar.path_label.accessibleDescription()

    status_bar.update_file_count(42, selected=5)
    assert "5 von 42 ausgewählt" in status_bar.file_count_label.accessibleDescription()

    status_bar.update_space(1024 * 1024 * 50)
    assert "MB" in status_bar.space_label.accessibleDescription()

    status_bar.set_sync_status(True)
    assert "Synchronisation" in status_bar.sync_label.accessibleDescription()


def test_file_browser_table_accessibility():
    browser = FileBrowser()
    assert browser.table.accessibleName() == "Dateiliste"
    assert "Tabelle der Dateien und Ordner" in browser.table.accessibleDescription()
    assert browser.table.toolTip() == "Dateien und Ordner im aktuellen Verzeichnis"


def test_sidebar_tree_and_favorites_accessibility():
    tree_panel = TreePanel()
    assert tree_panel.tree.accessibleName() == "Ordnerbaum"
    assert "Laufwerke" in tree_panel.tree.accessibleDescription()

    fav_panel = FavoritesPanel()
    assert fav_panel.add_btn.accessibleName() == "Zu Favoriten hinzufügen"
    assert fav_panel.list.accessibleName() == "Favoritenliste"


def test_quick_editor_accessibility():
    dialog = QuickEditorDialog()
    try:
        assert dialog.btn_save.accessibleName() == "Datei speichern"
        assert dialog.btn_validate.accessibleName() == "Syntax validieren"
        assert dialog.btn_run.accessibleName() == "Code ausführen"
        assert dialog.btn_stop.accessibleName() == "Ausführung stoppen"

        assert dialog.editor.accessibleName() == "Code-Editor"
        assert dialog.output.accessibleName() == "Programmausgabe"

        assert dialog.line_label.accessibleName() == "Cursor-Position"
        assert dialog.encoding_label.accessibleName() == "Zeichenkodierung"
        assert dialog.modified_label.accessibleName() == "Änderungsstatus"
    finally:
        dialog.close()


def test_duplicate_finder_accessibility():
    dialog = DuplicateFinderDialog()
    try:
        assert dialog.source_combo.accessibleName() == "Scan-Quelle"
        assert dialog.folder_btn.accessibleName() == "Ordner auswählen"
        assert dialog.min_size_spin.accessibleName() == "Minimale Dateigröße"
        assert dialog.scan_btn.accessibleName() == "Scan starten"
        assert dialog.cancel_btn.accessibleName() == "Scan abbrechen"
        assert dialog.tree.accessibleName() == "Duplikate-Ergebnisliste"
        assert dialog.select_all_btn.accessibleName() == "Alle Duplikate auswählen"
        assert dialog.select_newest_btn.accessibleName() == "Neueste behalten"
        assert dialog.select_oldest_btn.accessibleName() == "Älteste behalten"
        assert dialog.delete_btn.accessibleName() == "Ausgewählte Duplikate löschen"
    finally:
        dialog.close()


def test_sync_controls_accessibility(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    dialog = SyncPairDialog()
    panel = SyncPanel()
    try:
        assert dialog.name_edit.accessibleName() == "Name des Synchronisationspaars"
        assert dialog.source_edit.accessibleName() == "Quellordner"
        assert dialog.source_btn.accessibleName() == "Quellordner auswählen"
        assert dialog.target_edit.accessibleName() == "Zielordner"
        assert dialog.target_btn.accessibleName() == "Zielordner auswählen"
        assert dialog.direction_combo.accessibleName() == "Synchronisationsrichtung"
        assert dialog.conflict_combo.accessibleName() == "Konfliktlösung"
        assert dialog.exclude_edit.accessibleName() == "Ausgeschlossene Dateimuster"

        assert panel.add_btn.accessibleName() == "Neues Synchronisationspaar erstellen"
        assert panel.pair_list.accessibleName() == "Synchronisationspaare"
        assert panel.sync_btn.accessibleName() == "Synchronisation starten"
        assert panel.preview_btn.accessibleName() == "Synchronisationsvorschau öffnen"

        panel.sync_pairs = [
            SyncPair(id="sync-1", name="Dokumente", source="/source", target="/target", direction="target_to_source")
        ]
        panel._refresh_list()
        assert "Ziel zu Quelle" in panel.pair_list.item(0).toolTip()
    finally:
        dialog.close()
        panel.close()
