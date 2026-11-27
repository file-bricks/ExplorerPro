#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
atomic_io.py - Gehärtete, atomare Dateispeicherungs-Engine für ExplorerPro.

Gewährleistet Datenintegrität bei Stromausfall, Prozessabbruch und I/O-Fehlern:
1. Temporäres Staging im selben Verzeichnis (Same-Filesystem Invariant).
2. Explizites Flush und os.fsync() vor Schließen des File-Deskriptors.
3. Erhalt von Dateiattributen / Berechtigungen (stat.S_IMODE).
4. Atomare Publikation via os.replace().
5. Garantierte Aufräumung temporärer Staging-Dateien bei Fehlern.
"""

from __future__ import annotations

import json
import os
import stat
import uuid
from pathlib import Path
from typing import Any


def atomic_write_bytes(
    filepath: str | Path,
    data: bytes,
    preserve_mode: bool = True,
) -> Path:
    """
    Schreibt Bytes atomar und crash-sicher in die Zieldatei.

    Args:
        filepath: Zielpfad für die Datei
        data: Zu schreibende Rohbytes
        preserve_mode: Vorhandene POSIX/Windows-Dateirechte erhalten

    Returns:
        Path-Objekt der geschriebenen Zieldatei
    """
    target = Path(filepath).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)

    mode: int | None = None
    if preserve_mode and target.exists():
        try:
            mode = stat.S_IMODE(target.stat().st_mode)
        except OSError:
            mode = None

    temp_name = f".{target.name}.tmp.{os.getpid()}_{uuid.uuid4().hex}"
    temp_path = target.parent / temp_name

    try:
        with open(temp_path, "wb") as fh:
            fh.write(data)
            fh.flush()
            try:
                os.fsync(fh.fileno())
            except OSError:
                pass

        if mode is not None:
            try:
                os.chmod(temp_path, mode)
            except OSError:
                pass

        os.replace(temp_path, target)
        return target
    finally:
        if temp_path.exists():
            try:
                temp_path.chmod(stat.S_IRUSR | stat.S_IWUSR)
            except OSError:
                pass
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass


def atomic_write_text(
    filepath: str | Path,
    content: str,
    encoding: str = "utf-8",
    errors: str = "strict",
    preserve_mode: bool = True,
    newline: str | None = None,
) -> Path:
    """
    Schreibt Text atomar und crash-sicher in die Zieldatei.

    Args:
        filepath: Zielpfad für die Datei
        content: Zu schreibender Text
        encoding: Zeichensatzkodierung (Standard: utf-8)
        errors: Fehlerbehandlungsstrategie bei Kodierung
        preserve_mode: Vorhandene POSIX/Windows-Dateirechte erhalten
        newline: Spezifische Zeilenumbruchskonvention

    Returns:
        Path-Objekt der geschriebenen Zieldatei
    """
    target = Path(filepath).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)

    mode: int | None = None
    if preserve_mode and target.exists():
        try:
            mode = stat.S_IMODE(target.stat().st_mode)
        except OSError:
            mode = None

    temp_name = f".{target.name}.tmp.{os.getpid()}_{uuid.uuid4().hex}"
    temp_path = target.parent / temp_name

    try:
        with open(temp_path, "w", encoding=encoding, errors=errors, newline=newline) as fh:
            fh.write(content)
            fh.flush()
            try:
                os.fsync(fh.fileno())
            except OSError:
                pass

        if mode is not None:
            try:
                os.chmod(temp_path, mode)
            except OSError:
                pass

        os.replace(temp_path, target)
        return target
    finally:
        if temp_path.exists():
            try:
                temp_path.chmod(stat.S_IRUSR | stat.S_IWUSR)
            except OSError:
                pass
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass


def atomic_write_json(
    filepath: str | Path,
    data: Any,
    indent: int = 2,
    ensure_ascii: bool = False,
    encoding: str = "utf-8",
    preserve_mode: bool = True,
) -> Path:
    """
    Serialisiert Daten strukturiert als JSON und speichert sie atomar ab.

    Args:
        filepath: Zielpfad für die JSON-Datei
        data: Zu serialisierende Python-Datenstruktur
        indent: Einrückungstiefe für Lesbarkeit
        ensure_ascii: Ob Nicht-ASCII-Zeichen als Unicode-Escapes kodiert werden sollen
        encoding: Zeichensatzkodierung (Standard: utf-8)
        preserve_mode: Vorhandene POSIX/Windows-Dateirechte erhalten

    Returns:
        Path-Objekt der geschriebenen Zieldatei
    """
    serialized = json.dumps(data, indent=indent, ensure_ascii=ensure_ascii) + "\n"
    return atomic_write_text(
        filepath=filepath,
        content=serialized,
        encoding=encoding,
        preserve_mode=preserve_mode,
    )
