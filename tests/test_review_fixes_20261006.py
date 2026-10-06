"""Regressionstests für das Review vom 2026-10-06.

Abgedeckt:
* Cloud-Ordner (OneDrive & Co.) werden erkannt und im Browser nicht ausgefiltert
* Namensspalte der Dateiliste bleibt sichtbar
* Vorschau stürzt nicht ab und lädt keine Cloud-Platzhalter
* Black-/Whitelist sind in der GUI editierbar, Ampel ist bedienbar
* Spracheinstellung wirkt zur Laufzeit auf alle Widgets
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import shiboken6
from PySide6.QtCore import QDir
from PySide6.QtWidgets import QApplication, QCheckBox, QLabel, QMenu, QPushButton, QWidget

import translator
from core import cloud_locations, file_attributes
from core.platform_utils import normalize_user_path
from core.settings_manager import SettingsManager


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def isolated_settings(monkeypatch, tmp_path):
    monkeypatch.setattr(SettingsManager, "_instance", None)
    monkeypatch.setattr(SettingsManager, "_get_config_path", lambda self: tmp_path / "settings.json")
    return SettingsManager.instance()


@pytest.fixture
def fresh_translator(monkeypatch):
    ts = translator.TranslationSystem("de")
    monkeypatch.setattr(translator, "_default_translator", ts)
    return ts


# --------------------------------------------------------------------------- #
# Cloud-Ordner                                                                  #
# --------------------------------------------------------------------------- #

def test_cloud_locations_from_environment_and_home(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    (home / "OneDrive - Contoso").mkdir()
    (home / "Dropbox").mkdir()
    (home / "Dokumente").mkdir()
    (home / "Boxen").mkdir()  # kein Cloud-Ordner trotz Präfix "box"
    personal = home / "OneDrive"
    personal.mkdir()

    found = cloud_locations.find_cloud_locations(
        home=str(home), environ={"OneDrive": str(personal), "OneDriveConsumer": str(personal)},
        platform="linux",
    )
    labels = [loc.label for loc in found]
    assert labels == ["Dropbox", "OneDrive", "OneDrive - Contoso"]
    assert len({os.path.realpath(loc.path) for loc in found}) == len(found)


def test_cloud_locations_macos_cloudstorage(tmp_path):
    home = tmp_path
    storage = home / "Library" / "CloudStorage"
    (storage / "OneDrive-Persönlich").mkdir(parents=True)
    (storage / "GoogleDrive-user@example.com").mkdir()
    icloud = home / "Library" / "Mobile Documents" / "com~apple~CloudDocs"
    icloud.mkdir(parents=True)

    labels = {loc.label for loc in cloud_locations.find_cloud_locations(
        home=str(home), environ={}, platform="darwin")}
    assert {"OneDrive - Persönlich", "Google Drive (user@example.com)", "iCloud Drive"} <= labels


def test_cloud_placeholder_detection_uses_metadata_only():
    windows_online = SimpleNamespace(st_file_attributes=file_attributes.FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS)
    windows_local = SimpleNamespace(st_file_attributes=0x20)
    assert file_attributes.is_cloud_placeholder("x", windows_online, platform="win32")
    assert not file_attributes.is_cloud_placeholder("x", windows_local, platform="win32")

    import stat as stat_mod
    mac = SimpleNamespace(st_flags=file_attributes.SF_DATALESS, st_mode=stat_mod.S_IFREG)
    assert file_attributes.is_cloud_placeholder("x", mac, platform="darwin")
    assert not file_attributes.is_cloud_placeholder("/does/not/exist")


def test_browser_shows_windows_system_entries(monkeypatch):
    from gui.browser import file_browser

    monkeypatch.setattr(file_browser.sys, "platform", "win32")
    assert file_browser.base_entry_filters() & QDir.Filter.System
    monkeypatch.setattr(file_browser.sys, "platform", "linux")
    assert not file_browser.base_entry_filters() & QDir.Filter.System


def test_sidebar_lists_cloud_storage(app, monkeypatch, tmp_path):
    from gui.sidebar import sidebar_main

    cloud = tmp_path / "OneDrive"
    cloud.mkdir()
    (cloud / "Projekte").mkdir()
    monkeypatch.setattr(
        sidebar_main, "find_cloud_locations",
        lambda: [cloud_locations.CloudLocation("OneDrive", str(cloud))],
    )
    panel = sidebar_main.TreePanel()
    try:
        assert panel.cloud_item is not None
        child = panel.cloud_item.child(0)
        assert child.text(0) == "OneDrive"
        panel._on_item_expanded(child)
        assert [child.child(i).text(0) for i in range(child.childCount())] == ["Projekte"]
    finally:
        shiboken6.delete(panel)


# --------------------------------------------------------------------------- #
# Dateiliste                                                                    #
# --------------------------------------------------------------------------- #

def test_name_column_keeps_space_when_narrow(app, isolated_settings, tmp_path):
    from gui.browser.file_browser import FileBrowser

    browser = FileBrowser()
    try:
        browser.resize(420, 300)
        browser.show()
        app.processEvents()
        header = browser.table.horizontalHeader()
        assert header.sectionSize(0) >= FileBrowser.MIN_NAME_WIDTH - 2
        for column in FileBrowser.COLUMN_WIDTHS:
            assert header.sectionResizeMode(column).name == "Interactive"
    finally:
        browser.close()
        shiboken6.delete(browser)


def test_browser_uses_configured_start_folder(app, isolated_settings, tmp_path):
    from gui.browser.file_browser import FileBrowser

    start = tmp_path / "Start Ordner"
    start.mkdir()
    isolated_settings.set("general", "start_folder", f'"{start}"')
    browser = FileBrowser()
    try:
        assert browser.current_path == str(start)
    finally:
        shiboken6.delete(browser)


def test_navigate_to_file_opens_parent_and_selects(app, isolated_settings, tmp_path):
    from gui.browser.file_browser import FileBrowser

    target = tmp_path / "notiz.txt"
    target.write_text("x", encoding="utf-8")
    browser = FileBrowser()
    selected = []
    browser.file_selected.connect(selected.append)
    try:
        browser.navigate_to(str(target))
        assert browser.current_path == str(tmp_path)
        assert selected == [str(target)]
    finally:
        shiboken6.delete(browser)


def test_normalize_user_path(monkeypatch, tmp_path):
    monkeypatch.setenv("EP_TEST_DIR", str(tmp_path))
    assert normalize_user_path(f'"{tmp_path}"') == str(tmp_path)
    assert normalize_user_path("$EP_TEST_DIR") == str(tmp_path)
    assert normalize_user_path(tmp_path.as_uri()) == str(tmp_path)
    assert normalize_user_path("  ") == ""


# --------------------------------------------------------------------------- #
# Vorschau                                                                      #
# --------------------------------------------------------------------------- #

def test_preview_never_raises(app, isolated_settings, monkeypatch, tmp_path):
    from gui.preview import preview_panel

    target = tmp_path / "bild.png"
    target.write_bytes(b"not really a png")
    panel = preview_panel.PreviewPanel()
    try:
        def boom(*_args, **_kwargs):
            raise RuntimeError("Render kaputt")

        monkeypatch.setattr(panel.image_preview, "load_image", boom)
        panel.show_preview(str(target))  # darf nicht werfen
        assert panel.preview_stack.currentWidget() is panel.unsupported_label
        assert "Render kaputt" in panel.unsupported_label.text()
        assert panel.metadata_panel.name_label.text() == "bild.png"
    finally:
        shiboken6.delete(panel)


def test_preview_skips_cloud_placeholders(app, isolated_settings, monkeypatch, tmp_path):
    from gui.preview import preview_panel

    target = tmp_path / "online.txt"
    target.write_text("Inhalt", encoding="utf-8")
    monkeypatch.setattr(preview_panel, "is_cloud_placeholder", lambda path: True)
    panel = preview_panel.PreviewPanel()
    try:
        monkeypatch.setattr(panel.text_preview, "load_file",
                            lambda path: pytest.fail("Platzhalter darf nicht gelesen werden"))
        panel.show_preview(str(target))
        assert "nur online verfügbar" in panel.unsupported_label.text()
    finally:
        shiboken6.delete(panel)


def test_preview_respects_size_limit_and_toggles(app, isolated_settings, tmp_path):
    from gui.preview import preview_panel

    big = tmp_path / "gross.pdf"
    big.write_bytes(b"%PDF-1.4" + b"0" * (2 * 1024 * 1024))
    isolated_settings.set("preview", "max_preview_size_mb", 1)
    panel = preview_panel.PreviewPanel()
    try:
        panel.show_preview(str(big))
        assert "zu groß" in panel.unsupported_label.text()

        isolated_settings.set("preview", "preview_images", False)
        image = tmp_path / "klein.png"
        image.write_bytes(b"\x89PNG")
        panel.show_preview(str(image))
        assert "deaktiviert" in panel.unsupported_label.text()
    finally:
        shiboken6.delete(panel)


def test_preview_detects_text_without_extension(app, isolated_settings, tmp_path):
    from gui.preview import preview_panel

    readme = tmp_path / "README"
    readme.write_text("Hallo Welt\n", encoding="utf-8")
    panel = preview_panel.PreviewPanel()
    try:
        panel.show_preview(str(readme))
        assert panel.preview_stack.currentWidget() is panel.text_preview
        assert "Hallo Welt" in panel.text_preview.toPlainText()
    finally:
        shiboken6.delete(panel)


def test_image_preview_downscales_large_images(app, tmp_path):
    from PySide6.QtGui import QImage, QColor
    from gui.preview.preview_panel import ImagePreview, MAX_IMAGE_EDGE

    path = tmp_path / "riesig.png"
    image = QImage(MAX_IMAGE_EDGE * 2, 100, QImage.Format.Format_RGB32)
    image.fill(QColor("red"))
    assert image.save(str(path))
    preview = ImagePreview()
    try:
        preview.load_image(str(path))
        assert preview._original_pixmap.width() <= MAX_IMAGE_EDGE
    finally:
        shiboken6.delete(preview)


# --------------------------------------------------------------------------- #
# Datenschutz                                                                   #
# --------------------------------------------------------------------------- #

@pytest.fixture
def monitor(tmp_path):
    from modules.privacy.privacy_monitor import PrivacyMonitor

    return PrivacyMonitor(tmp_path / "privacy")


def test_privacy_dialog_edits_black_and_whitelist(app, isolated_settings, monitor):
    from gui.privacy_dialog import PrivacySettingsDialog

    monitor.add_to_blacklist("Altbegriff")
    dialog = PrivacySettingsDialog(monitor, settings=isolated_settings)
    try:
        assert dialog.blacklist_editor.terms() == ["Altbegriff"]
        dialog.blacklist_editor.term_edit.setText("Projekt Phoenix; Kunde 4711")
        dialog.blacklist_editor.add_from_input()
        dialog.whitelist_editor.add_terms(["info@firma.de"])
        dialog.blacklist_editor.list_widget.setCurrentRow(0)  # sortiert: Altbegriff
        dialog.blacklist_editor.remove_selected()
        dialog.apply_settings()
    finally:
        shiboken6.delete(dialog)

    assert monitor.blacklist == {"Projekt Phoenix", "Kunde 4711"}
    assert monitor.whitelist == {"info@firma.de"}
    saved = json.loads(monitor.config_path.read_text(encoding="utf-8"))
    assert set(saved["blacklist"]) == {"Projekt Phoenix", "Kunde 4711"}
    assert monitor.check_text("Treffen zu Projekt Phoenix").detected_patterns
    assert not monitor.check_text("Mail an info@firma.de").detected_patterns


def test_privacy_dialog_test_tab_uses_unsaved_lists(app, isolated_settings, monitor):
    from gui.privacy_dialog import PrivacySettingsDialog

    dialog = PrivacySettingsDialog(monitor, settings=isolated_settings)
    try:
        dialog.blacklist_editor.add_terms(["Geheimprojekt"])
        dialog.test_input.setPlainText("Status Geheimprojekt")
        dialog.run_test()
        assert "Geheimprojekt" in dialog.test_result.toPlainText()
        # Ohne Speichern bleibt der Monitor unverändert.
        assert monitor.blacklist == set()
        assert not monitor.check_text("Status Geheimprojekt").detected_patterns
    finally:
        shiboken6.delete(dialog)


def test_privacy_dialog_toggles_monitoring(app, isolated_settings, monitor):
    from gui.privacy_dialog import PrivacySettingsDialog

    monitor.start()
    dialog = PrivacySettingsDialog(monitor, settings=isolated_settings)
    try:
        dialog.monitor_enabled_cb.setChecked(False)
        dialog.apply_settings()
        assert monitor.status == "gray" and not monitor.enabled
        assert isolated_settings.get("privacy", "enable_clipboard_monitor") is False
        dialog.monitor_enabled_cb.setChecked(True)
        dialog.apply_settings()
        assert monitor.enabled and monitor.status == "green"
    finally:
        monitor.stop()
        shiboken6.delete(dialog)


def test_monitor_restart_reconnects_clipboard(app, monitor):
    monitor.start()
    monitor.stop()
    monitor.start()
    assert monitor.enabled and monitor._connected
    monitor.add_to_blacklist("Codename")
    QApplication.clipboard().setText("Codename Falke")
    app.processEvents()
    assert monitor.status in ("yellow", "red")
    monitor.reset_status()
    assert monitor.status == "green"
    monitor.stop()


def test_term_io_roundtrip(tmp_path):
    from modules.privacy.term_io import read_terms, write_terms

    terms = ["Müller", "Projekt X", "Müller", " ", "nan"]
    for suffix in (".txt", ".csv", ".xlsx"):
        path = tmp_path / f"liste{suffix}"
        write_terms(str(path), terms)
        assert sorted(read_terms(str(path))) == ["Müller", "Projekt X"]

    semicolon = tmp_path / "excel_export.csv"
    semicolon.write_bytes("Begriff;Kommentar\nÄrger;x\n".encode("cp1252"))
    assert read_terms(str(semicolon)) == ["Begriff", "Ärger"]


def test_status_bar_privacy_menu_emits_actions(app):
    from gui.status_bar import StatusBarWidget

    bar = StatusBarWidget()
    events = []
    bar.privacy_settings_requested.connect(lambda: events.append("settings"))
    bar.privacy_reset_requested.connect(lambda: events.append("reset"))
    bar.privacy_monitoring_toggled.connect(lambda on: events.append(("toggle", on)))
    try:
        bar.privacy_indicator.clicked.emit()
        bar.set_privacy_status("red")
        menu = bar.build_privacy_menu()
        actions = {a.text(): a for a in menu.actions() if a.text()}
        actions["Ampel zurücksetzen"].trigger()
        actions["Zwischenablage überwachen"].trigger()
        assert events == ["settings", "reset", ("toggle", False)]
    finally:
        shiboken6.delete(bar)


# --------------------------------------------------------------------------- #
# Sprache                                                                       #
# --------------------------------------------------------------------------- #

def test_translator_never_writes_catalog_at_runtime(tmp_path):
    locales = tmp_path / "locales"
    locales.mkdir()
    catalog = locales / "translations.json"
    catalog.write_text("{}", encoding="utf-8")
    catalog.chmod(0o444)
    try:
        ts = translator.TranslationSystem("en", app_dir=tmp_path)
        assert ts.t("Völlig neuer Text") == "Völlig neuer Text"
        assert "Völlig neuer Text" in ts.missing_keys
        assert catalog.read_text(encoding="utf-8") == "{}"
    finally:
        catalog.chmod(0o644)


def test_translate_text_handles_decorations(fresh_translator):
    ts = fresh_translator
    ts.set_language("en")
    assert ts.translate_text("📂 Öffnen") == "📂 Open"
    assert ts.translate_text("Neue Datei...") == "New File..."
    assert ts.translate_text("Startordner:") == "Start folder:"
    assert ts.translate_text("&Datei") == "&File"
    assert ts.translate_text("Abbrechen\nAbbrechen") == "Cancel\nCancel"
    assert ts.translate_text("Ein Ordnername ohne Eintrag") == "Ein Ordnername ohne Eintrag"
    # Werte der aktiven Sprache bleiben unverändert (keine Doppelübersetzung)
    assert ts.translate_text("Cancel") == "Cancel"
    assert ts.translate_text_from("Cancel", "en") == "Cancel"
    ts.set_language("es")
    assert ts.translate_text_from("Cancel", "en") == ts.translations["Abbrechen"]["es"]


def test_ui_translator_translates_and_switches_live(app, fresh_translator):
    from core.ui_translator import NO_TRANSLATE, UiTranslator

    ui = UiTranslator(app)
    window = QWidget()
    try:
        label = QLabel("Startordner:", window)
        button = QPushButton("Abbrechen", window)
        data = QLabel("Abbrechen", window)
        data.setProperty(NO_TRANSLATE, True)
        check = QCheckBox("Versteckte Dateien anzeigen", window)
        menu = QMenu("&Datei", window)
        action = menu.addAction("Neue Datei...")

        fresh_translator.set_language("en")
        window.show()
        app.processEvents()
        ui.translate_widget(menu)
        assert label.text() == "Start folder:"
        assert button.text() == "Cancel"
        assert data.text() == "Abbrechen"
        assert check.text() == fresh_translator.translations["Versteckte Dateien anzeigen"]["en"]
        assert action.text() == "New File..."

        fresh_translator.set_language("es")  # Live-Wechsel
        assert button.text() == fresh_translator.translations["Abbrechen"]["es"]
        assert label.text() == fresh_translator.translations["Startordner:"]["es"]
        assert action.text() == fresh_translator.translations["Neue Datei"]["es"] + "..."

        fresh_translator.set_language("de")
        assert button.text() == "Abbrechen"
        assert action.text() == "Neue Datei..."
    finally:
        fresh_translator.remove_language_listener(ui._on_language_changed)
        app.removeEventFilter(ui)
        shiboken6.delete(window)


def test_settings_language_change_applies_live(app, isolated_settings, fresh_translator, monkeypatch):
    from gui.main_window import MainWindow

    window = MainWindow()
    try:
        isolated_settings.set("general", "language", "en")
        window._apply_settings()
        assert fresh_translator.get_language() == "en"
    finally:
        fresh_translator.set_language("de")
        window.close()
        shiboken6.delete(window)


# --------------------------------------------------------------------------- #
# Indexer & Crash-Log                                                           #
# --------------------------------------------------------------------------- #

def test_index_worker_respects_excludes_and_placeholders(app, tmp_path, monkeypatch):
    from core import file_attributes as fa
    from core.file_index import FileIndex, IndexWorker

    folder = tmp_path / "daten"
    folder.mkdir()
    (folder / "behalten.txt").write_text("hallo", encoding="utf-8")
    (folder / "weg.tmp").write_text("x", encoding="utf-8")
    (folder / "online.txt").write_text("cloud", encoding="utf-8")
    index = FileIndex(str(tmp_path / "index.db"))

    monkeypatch.setattr(fa, "is_cloud_placeholder", lambda path: path.endswith("online.txt"))
    read = []
    original = FileIndex.calculate_hash
    monkeypatch.setattr(FileIndex, "calculate_hash", lambda self, p: read.append(p) or original(self, p))

    worker = IndexWorker(index, str(folder), max_file_size_mb=1, excluded_patterns=["*.tmp"])
    worker.run()

    assert index.get_file(str(folder / "weg.tmp")) is None
    assert index.get_file(str(folder / "online.txt")) is not None
    assert not any(p.endswith("online.txt") for p in read)


def test_crash_log_records_unhandled_exceptions(tmp_path, monkeypatch):
    from core import crash_log

    previous = sys.excepthook
    # pytest-qt meldet weitergereichte Ausnahmen als Testfehler: Kette kappen.
    monkeypatch.setattr(sys, "excepthook", lambda *args: None)
    path = crash_log.install_crash_logging(tmp_path)
    try:
        try:
            raise ValueError("Testfehler 42")
        except ValueError:
            sys.excepthook(*sys.exc_info())
        assert "Testfehler 42" in Path(path).read_text(encoding="utf-8")
    finally:
        crash_log.uninstall_crash_logging()
        sys.excepthook = previous
