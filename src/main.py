#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ExplorerPro - Ein intelligenter Datei-Explorer
Fusion aus ProFiler, PythonBox, ProSync, AmpelTool, SoftwareCenter, ProfiPrompt

"""

import sys
import os
from pathlib import Path

# Encoding für Windows
if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

# Pfad hinzufügen (src/ und Projektwurzel mit translator.py)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Frozen helpers must finish before importing Qt or constructing the application.
if __name__ == '__main__' and len(sys.argv) == 4 and sys.argv[1] == '--drive-capacity-query':
    from core.drive_usage import capacity_query_main
    sys.exit(capacity_query_main(sys.argv[2], sys.argv[3]))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QTranslator, QLibraryInfo
from PySide6.QtGui import QIcon

from app import ExplorerProApp
from core.crash_log import install_crash_logging
from version import __version__
from core.gui_gc import install_gui_gc
from gui.sidebar.drive_capacity import shutdown_capacity_executor


def load_app_icon() -> QIcon:
    base_dir = Path(__file__).resolve().parent.parent
    candidates = [
        Path(sys.executable).with_name("ExplorerPro.ico") if getattr(sys, "frozen", False) else None,
        base_dir / "ExplorerPro.ico",
        base_dir / "assets" / "ExplorerPro.ico",
        base_dir / "assets" / "icon.ico",
        base_dir / "DesktopIcon.ico",
        base_dir / "icon.ico",
        base_dir / "assets" / "icon.png",
        base_dir / "icon.png",
        Path(__file__).resolve().parent / "ExplorerPro.ico",
    ]
    for candidate in candidates:
        if candidate and candidate.exists():
            icon = QIcon(str(candidate))
            if not icon.isNull():
                return icon
    return QIcon()


def install_qt_translations(app: QApplication, lang: str):
    """Lädt Qts eigene Übersetzung (qtbase_<lang>.qm), damit Standard-Buttons
    wie Ja/Nein, Speichern/Verwerfen/Abbrechen in der UI-Sprache erscheinen.

    Ein zuvor installierter Qt-Übersetzer wird entfernt, damit ein
    Sprachwechsel zur Laufzeit nicht die alte Sprache weiter bevorzugt.
    """
    previous = getattr(app, "_ep_qt_translator", None)
    if previous is not None:
        app.removeTranslator(previous)
        app._ep_qt_translator = None
    translator = QTranslator(app)
    path = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    if translator.load(f"qtbase_{lang}", path):
        app.installTranslator(translator)
        app._ep_qt_translator = translator
        return translator
    return None


def install_runtime_translation(app: QApplication, translator) -> None:
    """Übersetzt alle Widgets zur Laufzeit und folgt Sprachwechseln live."""
    from core.ui_translator import install_ui_translator

    install_ui_translator(app)
    translator.add_language_listener(lambda lang: install_qt_translations(app, lang))


def set_application_version(app: QApplication) -> None:
    app.setApplicationVersion(__version__)


def configure_application_language():
    """Restore the saved UI language before constructing any translated widgets."""
    from core.settings_manager import SettingsManager
    from translator import get_translator, SUPPORTED_LANGUAGES

    language = SettingsManager.instance().get("general", "language", "de")
    if language not in SUPPORTED_LANGUAGES:
        language = "de"
    return get_translator(language)


def main():
    """Haupteinstiegspunkt für ExplorerPro"""
    # High DPI Support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    install_crash_logging()
    app = QApplication(sys.argv)
    collector = install_gui_gc(app)
    try:
        app.setApplicationName("ExplorerPro")
        app.setOrganizationName("ExplorerPro")
        translator = configure_application_language()
        install_qt_translations(app, translator.get_language())
        install_runtime_translation(app, translator)
        set_application_version(app)
        icon = load_app_icon()
        if not icon.isNull():
            app.setWindowIcon(icon)

        # Style
        app.setStyle("Fusion")

        # Dark Theme (optional)
        # from gui.themes import apply_dark_theme
        # apply_dark_theme(app)

        # Hauptfenster starten
        explorer = ExplorerProApp()
        if not icon.isNull():
            explorer.setWindowIcon(icon)
        explorer.show()
        exit_code = app.exec()
    finally:
        try:
            shutdown_capacity_executor()
        finally:
            collector.close()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
