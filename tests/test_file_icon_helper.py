#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests für src/core/file_icon_helper.py

Getestet wird die Logik von get_file_icon():
  - nicht-null QIcon für bekannte Pfade
  - Fallback (nicht-null) für leere / unbekannte / nicht-existierende Pfade
  - Fallback für Ordner-Pfad ohne Provider-Ergebnis

Kein Pixel-Inhalt wird geprüft — QFileIconProvider liefert unter
QT_QPA_PLATFORM=offscreen generische Icons ohne Shell-Zugriff.
"""
import os
import sys
import tempfile

import pytest

# Sicherstellen, dass src/ im Suchpfad liegt
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

# QApplication ist Pflicht, bevor Qt-Klassen instanziiert werden.
_app = QApplication.instance() or QApplication(sys.argv)

from core.file_icon_helper import get_file_icon


class TestGetFileIcon:
    """Einheitstests für get_file_icon()."""

    def test_empty_string_returns_non_null_icon(self):
        """Leerer Pfad → generisches File-Icon, kein Crash, kein null."""
        icon = get_file_icon("")
        assert isinstance(icon, QIcon)
        assert not icon.isNull()

    def test_none_like_empty_returns_non_null_icon(self):
        """Falsy-Eingabe (leerer String) → non-null Icon."""
        icon = get_file_icon("")
        assert not icon.isNull()

    def test_nonexistent_path_returns_non_null_icon(self):
        """Pfad der nicht existiert → Fallback-Icon (kein Crash)."""
        icon = get_file_icon(r"C:\kein\solcher\pfad\datei.xyz")
        assert isinstance(icon, QIcon)
        assert not icon.isNull()

    def test_existing_file_returns_non_null_icon(self):
        """Existierende Datei → nicht-null Icon."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            tmp_path = f.name
        try:
            icon = get_file_icon(tmp_path)
            assert isinstance(icon, QIcon)
            assert not icon.isNull()
        finally:
            os.unlink(tmp_path)

    def test_existing_directory_returns_non_null_icon(self):
        """Existierender Ordner → nicht-null Icon."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            icon = get_file_icon(tmp_dir)
            assert isinstance(icon, QIcon)
            assert not icon.isNull()

    def test_system_dir_returns_non_null_icon(self):
        """Windows-Systemordner → nicht-null Icon."""
        sys_dir = os.environ.get("SystemRoot", r"C:\Windows")
        if os.path.isdir(sys_dir):
            icon = get_file_icon(sys_dir)
            assert isinstance(icon, QIcon)
            assert not icon.isNull()

    def test_unknown_extension_nonexistent_returns_non_null_icon(self):
        """Unbekannte Erweiterung + nicht-existierend → Fallback, kein null."""
        icon = get_file_icon(r"C:\x\y\z.zzz999")
        assert isinstance(icon, QIcon)
        assert not icon.isNull()

    def test_return_type_is_qicon(self):
        """Rückgabetyp ist immer QIcon."""
        for path in ("", r"C:\kein\pfad", os.path.dirname(__file__)):
            assert isinstance(get_file_icon(path), QIcon)
