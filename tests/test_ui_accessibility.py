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


def test_checksum_dialog_accessibility(tmp_path):
    from gui.checksum_dialog import ChecksumDialog

    test_file = tmp_path / "sample.txt"
    test_file.write_text("ExplorerPro A11y Verification", encoding="utf-8")

    dialog = ChecksumDialog(str(test_file))
    try:
        assert dialog.accessibleName() == "Prüfsummen-Dialog"
        assert "md5" in dialog.hash_edits
        assert "sha256" in dialog.hash_edits
        assert dialog.hash_edits["md5"].accessibleName() == "MD5 Prüfsumme"
        assert dialog.hash_edits["sha256"].accessibleName() == "SHA256 Prüfsumme"
        assert dialog.verify_edit.accessibleName() == "Erwartete Prüfsumme zur Verifikation"
        assert dialog.close_btn.accessibleName() == "Dialog schließen"
        assert dialog.close_btn.shortcut().toString() == "Esc"
    finally:
        dialog.close()


def test_diff_dialog_accessibility():
    from gui.diff_dialog import DiffDialog

    dialog = DiffDialog()
    try:
        assert dialog.accessibleName() == "Datei-Vergleichs-Dialog"
        assert dialog.file1_edit.accessibleName() == "Pfad zu Datei 1 (Basis)"
        assert dialog.file2_edit.accessibleName() == "Pfad zu Datei 2 (Vergleich)"
        assert dialog.table.accessibleName() == "Diff-Ergebnistabelle"
        assert dialog.compare_btn.accessibleName() == "Dateien vergleichen"
        assert dialog.compare_btn.shortcut().toString() == "Ctrl+Return"
        assert dialog.close_btn.accessibleName() == "Dialog schließen"
        assert dialog.close_btn.shortcut().toString() == "Esc"
    finally:
        dialog.close()


def test_batch_rename_dialog_accessibility(tmp_path):
    from gui.batch_rename_dialog import BatchRenameDialog

    f1 = tmp_path / "file1.txt"
    f2 = tmp_path / "file2.txt"
    f1.write_text("a", encoding="utf-8")
    f2.write_text("b", encoding="utf-8")

    dialog = BatchRenameDialog([str(f1), str(f2)])
    try:
        assert dialog.accessibleName() == "Mehrfachumbenennung"
        assert dialog.search_edit.accessibleName() == "Suchbegriff für Umbenennung"
        assert dialog.replace_edit.accessibleName() == "Ersetzungstext"
        assert dialog.table.accessibleName() == "Umbenennungs-Vorschautabelle"
        assert dialog.rename_btn.accessibleName() == "Dateien jetzt umbenennen"
        assert dialog.close_btn.accessibleName() == "Dialog schließen"
        assert dialog.close_btn.shortcut().toString() == "Esc"
    finally:
        dialog.close()


def test_advanced_search_dialog_accessibility_and_keyboard():
    from gui.sidebar.advanced_search_dialog import AdvancedSearchDialog

    dialog = AdvancedSearchDialog()
    try:
        assert dialog.accessibleName() == "Erweiterte Dateisuche"
        assert dialog.query_input.accessibleName() == "Suchbegriff"
        assert dialog.results_table.accessibleName() == "Suchergebnisse"
        assert dialog.search_btn.accessibleName() == "Suche ausführen"
        assert dialog.clear_btn.accessibleName() == "Suchfilter zurücksetzen"
        assert dialog.open_btn.accessibleName() == "Ausgewählte Datei öffnen"
        assert dialog.open_folder_btn.accessibleName() == "Enthaltenden Ordner öffnen"

        # KeyPressEvent test on results table
        dialog.open_btn.setEnabled(True)
        opened = []
        dialog._open_selected = lambda: opened.append(True)
        enter_event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier)
        dialog.results_table.keyPressEvent(enter_event)
        assert len(opened) == 1
    finally:
        dialog.close()


def test_settings_dialog_accessibility(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    from gui.settings_dialog import SettingsDialog

    dialog = SettingsDialog()
    try:
        assert dialog.accessibleName() == "Einstellungen"
        assert dialog.show_hidden_cb.accessibleName() == "Versteckte Dateien anzeigen"
        assert dialog.confirm_delete_cb.accessibleName() == "Vor dem Löschen nachfragen"
        assert dialog.remember_size_cb.accessibleName() == "Fenstergröße merken"
        assert dialog.auto_index_cb.accessibleName() == "Ordner automatisch indizieren"
        assert dialog.show_preview_cb.accessibleName() == "Vorschaufenster anzeigen"
        assert dialog.clipboard_monitor_cb.accessibleName() == "Zwischenablage überwachen"
        assert dialog.theme_combo.accessibleName() == "Farbschema"
        assert "Versteckte Dateien" in dialog.show_hidden_cb.toolTip()
    finally:
        dialog.close()


def test_privacy_settings_dialog_accessibility():
    from gui.main_window import PrivacySettingsDialog
    from modules.privacy.privacy_monitor import PrivacyMonitor

    monitor = PrivacyMonitor()
    dialog = PrivacySettingsDialog(monitor)
    try:
        assert dialog.accessibleName() == "Datenschutz-Einstellungen"
        assert dialog.case_sensitive_cb.accessibleName() == "Groß- und Kleinschreibung beachten"
        assert dialog.whole_words_cb.accessibleName() == "Nur ganze Wörter"
        assert dialog.auto_clear_cb.accessibleName() == "Clipboard bei Alarm automatisch leeren"
        assert len(dialog.pattern_checks) > 0
        first_key = list(dialog.pattern_checks.keys())[0]
        assert "Erkennungsmuster" in dialog.pattern_checks[first_key].accessibleName()
    finally:
        dialog.close()


def test_apps_launcher_accessibility(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    from modules.launcher.apps_panel import AppButton, AppEditDialog, AppEntry, AppsPanel

    app = AppEntry(name="TestApp", path="C:/test/app.exe", category="System")
    btn = AppButton(app)
    assert btn.accessibleName() == "App TestApp"
    assert "C:/test/app.exe" in btn.accessibleDescription()
    assert btn.focusPolicy() == Qt.FocusPolicy.StrongFocus

    edit_dialog = AppEditDialog(app)
    try:
        assert edit_dialog.accessibleName() == "App bearbeiten"
        assert edit_dialog.name_edit.accessibleName() == "Anwendungsname"
        assert edit_dialog.path_edit.accessibleName() == "Programmpfad"
        assert edit_dialog.category_combo.accessibleName() == "Kategorie"
    finally:
        edit_dialog.close()

    panel = AppsPanel()
    try:
        assert panel.search_edit.accessibleName() == "Apps durchsuchen"
        assert panel.tabs.accessibleName() == "App-Kategorien"
    finally:
        panel.close()


def test_prompts_panel_accessibility(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    from modules.prompts.prompts_panel import Prompt, PromptEditDialog, PromptsPanel

    prompt = Prompt(id="p1", title="Code Review", content="Review: {{code}}", category="Code")
    edit_dialog = PromptEditDialog(prompt)
    try:
        assert edit_dialog.accessibleName() == "Prompt bearbeiten"
        assert edit_dialog.title_edit.accessibleName() == "Prompt-Titel"
        assert edit_dialog.category_combo.accessibleName() == "Prompt-Kategorie"
        assert edit_dialog.content_edit.accessibleName() == "Prompt-Inhaltstext"
    finally:
        edit_dialog.close()

    panel = PromptsPanel()
    try:
        assert panel.search_edit.accessibleName() == "Prompts durchsuchen"
        assert panel.category_tabs.accessibleName() == "Prompt-Kategorien"
        assert panel.prompt_list.accessibleName() == "Prompt-Liste"
        assert panel.preview_text.accessibleName() == "Prompt-Vorschautext"
        assert panel.copy_btn.accessibleName() == "Ausgewählten Prompt kopieren"
        assert panel.edit_btn.accessibleName() == "Ausgewählten Prompt bearbeiten"
    finally:
        panel.close()


def test_metadata_and_excel_preview_accessibility():
    from gui.preview.preview_panel import MetadataPanel, ExcelPreview

    meta_panel = MetadataPanel()
    try:
        assert meta_panel.checksum_btn.accessibleName() == "Prüfsummen berechnen"
        assert meta_panel.tags_edit.accessibleName() == "Metadaten-Tags"
        assert meta_panel.notes_edit.accessibleName() == "Datei-Notizen"
    finally:
        meta_panel.close()

    excel_preview = ExcelPreview()
    try:
        assert excel_preview.sheet_combo.accessibleName() == "Excel-Arbeitsblatt"
        assert excel_preview.open_extern_btn.accessibleName() == "In externer Anwendung öffnen"
        assert excel_preview.table.accessibleName() == "Tabellenvorschau"
    finally:
        excel_preview.close()
