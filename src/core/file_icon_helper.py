#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
file_icon_helper — liefert das System-Icon zu einem Pfad mit Fallback.

QFileIconProvider gibt auf Windows die echten Shell-Icons zurück (Dateityp,
Programm-Icons für .exe, zugewiesene Programm-Icons für .docx usw.).
Bei fehlendem, leerem oder unbekanntem Pfad wird auf ein generisches
System-Icon zurückgefallen, damit kein ``QIcon.isNull()`` in der Ansicht
erscheint.

Nutzung:
    from core.file_icon_helper import get_file_icon
    icon = get_file_icon("/pfad/zur/datei.txt")
"""
from __future__ import annotations

import os

from PySide6.QtCore import QFileInfo
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QFileIconProvider

# Einmaliger Provider – QFileIconProvider ist thread-sicher für Lesezugriffe.
_provider: QFileIconProvider = QFileIconProvider()


def get_file_icon(path: str) -> QIcon:
    """Gibt das System-Icon für *path* zurück; liefert nie ``QIcon.isNull()``.

    Fallback-Reihenfolge:
      1. ``QFileIconProvider.icon(QFileInfo(path))`` — echtes Shell-/Typ-Icon
      2. ``QFileIconProvider.IconType.Folder`` — falls *path* ein Ordner ist
         und der Provider kein spezifisches Icon liefert
      3. ``QFileIconProvider.IconType.File`` — für alle übrigen Fälle
    """
    if not path:
        return _provider.icon(QFileIconProvider.IconType.File)

    icon = _provider.icon(QFileInfo(path))
    if not icon.isNull():
        return icon

    # Fallback: Ordner vs. Datei
    if os.path.isdir(path):
        return _provider.icon(QFileIconProvider.IconType.Folder)
    return _provider.icon(QFileIconProvider.IconType.File)
