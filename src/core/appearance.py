#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
appearance — wendet Farbschema und Schriftgröße auf die QApplication an.

* ``system``: folgt dem Hell/Dunkel-Modus des Betriebssystems
* ``light`` / ``dark``: erzwingt das jeweilige Schema
* Schriftgröße ``0`` bedeutet Systemstandard
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

THEMES = ("system", "light", "dark")


def _dark_palette() -> QPalette:
    palette = QPalette()
    window = QColor(45, 45, 48)
    base = QColor(30, 30, 30)
    text = QColor(230, 230, 230)
    disabled = QColor(130, 130, 130)
    highlight = QColor(0, 120, 215)
    palette.setColor(QPalette.ColorRole.Window, window)
    palette.setColor(QPalette.ColorRole.WindowText, text)
    palette.setColor(QPalette.ColorRole.Base, base)
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(40, 40, 42))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(60, 60, 64))
    palette.setColor(QPalette.ColorRole.ToolTipText, text)
    palette.setColor(QPalette.ColorRole.Text, text)
    palette.setColor(QPalette.ColorRole.Button, window)
    palette.setColor(QPalette.ColorRole.ButtonText, text)
    palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 80, 80))
    palette.setColor(QPalette.ColorRole.Link, QColor(80, 160, 255))
    palette.setColor(QPalette.ColorRole.Highlight, highlight)
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.PlaceholderText, disabled)
    for role in (QPalette.ColorRole.WindowText, QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText):
        palette.setColor(QPalette.ColorGroup.Disabled, role, disabled)
    return palette


def apply_theme(app: QApplication, theme: str) -> None:
    """Setzt das Farbschema; unbekannte Werte gelten als ``system``."""
    theme = theme if theme in THEMES else "system"
    hints = app.styleHints()
    if hasattr(hints, "setColorScheme"):  # Qt >= 6.8
        scheme = {
            "system": Qt.ColorScheme.Unknown,
            "light": Qt.ColorScheme.Light,
            "dark": Qt.ColorScheme.Dark,
        }[theme]
        hints.setColorScheme(scheme)
        app.setPalette(app.style().standardPalette())
        return
    if theme == "dark":
        app.setPalette(_dark_palette())
    else:
        app.setPalette(app.style().standardPalette())


def apply_font_size(app: QApplication, point_size: int) -> None:
    """Setzt die Basisschriftgröße; 0 stellt die ursprüngliche Größe wieder her."""
    original = getattr(app, "_ep_original_point_size", None)
    font = app.font()
    if original is None:
        original = font.pointSizeF()
        app._ep_original_point_size = original
    try:
        size = float(point_size)
    except (TypeError, ValueError):
        size = 0
    target = size if 6 <= size <= 32 else original
    if target > 0 and abs(font.pointSizeF() - target) > 0.01:
        font.setPointSizeF(target)
        app.setFont(font)
