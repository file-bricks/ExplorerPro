"""Native acceptance of the built app using only isolated fixture data."""
import json
import os
import sys
import time
from pathlib import Path

def run_release_smoke(output):
    root = Path(output).resolve()
    root.mkdir(parents=True, exist_ok=True)
    profile = root / "profile"
    profile.mkdir(exist_ok=True)
    for name, value in (("USERPROFILE", profile), ("HOME", profile),
                        ("APPDATA", profile / "AppData/Roaming"),
                        ("LOCALAPPDATA", profile / "AppData/Local")):
        os.environ[name] = str(value)
    os.environ.pop("QT_QPA_PLATFORM", None)
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication
    QSettings.setDefaultFormat(QSettings.IniFormat)
    for scope in (QSettings.UserScope, QSettings.SystemScope):
        QSettings.setPath(QSettings.IniFormat, scope, str(root / "qsettings"))
    from core.settings_manager import SettingsManager
    SettingsManager._instance = None
    SettingsManager._get_config_path = lambda self: root / "settings.json"
    fixtures = root / "fixtures"
    fixtures.mkdir(exist_ok=True)
    txt = fixtures / "Überblick äöü.txt"
    txt.write_text("Projektüberblick\nÄpfel, Öl und Grüße bleiben lokal.\n", encoding="utf-8")
    (root / "settings.json").write_text(json.dumps({
        "general": {"start_folder": str(fixtures), "language": "de"},
        "privacy": {"enable_clipboard_monitor": False},
        "index": {"auto_index": False, "index_on_startup": False},
    }), encoding="utf-8")
    from main import (load_app_icon, install_qt_translations, install_runtime_translation,
                      configure_application_language, set_application_version)
    from core.gui_gc import install_gui_gc
    from core.ui_translator import uninstall_ui_translator
    from gui.sidebar.drive_capacity import shutdown_capacity_executor
    from app import ExplorerProApp
    from version import __version__
    app = QApplication.instance() or QApplication([])
    if app.platformName() != "windows":
        raise RuntimeError("Native Windows Qt required.")
    app.setApplicationName("ExplorerPro")
    app.setOrganizationName("ExplorerPro")
    set_application_version(app)
    translator = configure_application_language()
    install_qt_translations(app, "de")
    install_runtime_translation(app, translator)
    collector = install_gui_gc(app)
    icon = load_app_icon()
    if icon.isNull():
        raise RuntimeError("Runtime icon missing.")
    app.setWindowIcon(icon)
    window = None
    checks, screenshots = [], []
    def events(seconds=0.1):
        until = time.monotonic() + seconds
        while time.monotonic() < until:
            app.processEvents()
            time.sleep(0.005)
    def shot(name):
        target = root / (name + ".png")
        if not window.grab().save(str(target)):
            raise RuntimeError("Screenshot could not be saved.")
        screenshots.append(str(target))
    try:
        window = ExplorerProApp()
        window.setWindowIcon(icon)
        window.show()
        events(1)
        window.file_browser.navigate_to(str(fixtures))
        events(1)
        window.preview_panel.show_preview(str(txt))
        events()
        if not window.sidebar.isVisible() or window.sidebar.width() == 0:
            raise RuntimeError("Sidebar is collapsed.")
        if not window.preview_panel.isVisible() or window.preview_panel.width() == 0:
            raise RuntimeError("Preview is collapsed.")
        if "Äpfel" not in window.preview_panel.text_preview.toPlainText():
            raise RuntimeError("Text preview lost Unicode content.")
        checks += ["sidebar", "text-preview", "umlauts"]
        shot("text-preview")
        import fitz
        pdf = fixtures / "Übersicht.pdf"
        with fitz.open() as doc:
            page = doc.new_page()
            page.insert_text((72, 72), "ExplorerPro PDF smoke")
            doc.save(pdf)
        window.preview_panel.show_preview(str(pdf))
        events()
        if window.preview_panel.pdf_preview.content.pixmap().isNull():
            raise RuntimeError("PDF preview is empty.")
        checks.append("pdf-preview")
        shot("pdf-preview")
        from openpyxl import Workbook
        xlsx = fixtures / "Äpfel.xlsx"
        book = Workbook()
        book.active.append(["Grüße", 42])
        book.save(xlsx)
        window.preview_panel.show_preview(str(xlsx))
        events()
        excel = window.preview_panel.excel_preview
        if window.preview_panel.preview_stack.currentWidget() is not excel:
            raise RuntimeError("XLSX preview fell back instead of rendering.")
        if excel.table.rowCount() != 1 or excel.table.item(0, 0).text() != "Grüße" or excel.table.item(0, 1).text() != "42":
            raise RuntimeError("XLSX preview lost fixture cell contents.")
        checks.append("xlsx-preview")
        shot("xlsx-preview")
        translator.set_language("en")
        events()
        shot("language-en")
        translator.set_language("de")
        from gui.privacy_dialog import PrivacySettingsDialog
        dialog = PrivacySettingsDialog(window.privacy_monitor, window, SettingsManager.instance())
        dialog.blacklist_editor.set_terms(["=ProjektX", "Äpfel"])
        dialog.whitelist_editor.set_terms(["Öffentlich"])
        dialog.apply_settings()
        if set(window.privacy_monitor.blacklist) != {"=ProjektX", "Äpfel"}:
            raise RuntimeError("Blacklist did not persist.")
        dialog.close()
        checks.append("privacy-lists")
        from gui.properties_dialog import FilePropertiesDialog
        props = FilePropertiesDialog(str(fixtures), window)
        props.folder_stats_btn.click()
        until = time.monotonic() + 15
        while props._details_process is not None and time.monotonic() < until:
            events()
        if props._details_process is not None or "—" in props.folder_size_label.text():
            raise RuntimeError("Properties subprocess did not return statistics.")
        props.close()
        checks.append("properties-helper")
        summary = {"version": __version__, "qt_platform": app.platformName(),
                   "frozen": bool(getattr(sys, "frozen", False)),
                   "checks": checks, "screenshots": screenshots}
        (root / "release-smoke.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        return summary
    finally:
        if window is not None:
            window.close()
            app.processEvents()
        uninstall_ui_translator(app)
        shutdown_capacity_executor()
        collector.close()
