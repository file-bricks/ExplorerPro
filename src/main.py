#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ExplorerPro - Ein intelligenter Datei-Explorer
Fusion aus ProFiler, PythonBox, ProSync, AmpelTool, SoftwareCenter, ProfiPrompt

Version: 0.1.0
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

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QTranslator, QLibraryInfo
from PySide6.QtGui import QIcon

from app import ExplorerProApp


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
    wie Ja/Nein, Speichern/Verwerfen/Abbrechen in der UI-Sprache erscheinen."""
    translator = QTranslator(app)
    path = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    if translator.load(f"qtbase_{lang}", path):
        app.installTranslator(translator)
        return translator
    return None


def main():
    """Haupteinstiegspunkt für ExplorerPro"""
    # High DPI Support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("ExplorerPro")
    app.setOrganizationName("ExplorerPro")
    from translator import get_translator
    install_qt_translations(app, get_translator().get_language())
    app.setApplicationVersion("0.1.0")
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

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
