#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cloud_locations — findet lokale Synchronisationsordner von Cloud-Diensten.

Es werden ausschließlich lokale Quellen gelesen (Umgebungsvariablen,
Benutzerverzeichnis, unter Windows die Registry nur lesend); es findet
kein Netzwerkzugriff statt.

Quellen:
* Windows: ``%OneDrive%``, ``%OneDriveConsumer%``, ``%OneDriveCommercial%``
  sowie die von Windows verwalteten Sync-Roots
  (``HKLM\\...\\Explorer\\SyncRootManager``), über die sich OneDrive,
  Dropbox, iCloud, Nextcloud, Box usw. beim Explorer anmelden.
* macOS: ``~/Library/CloudStorage/*`` und iCloud Drive.
* Alle Plattformen: bekannte Ordnernamen direkt im Benutzerverzeichnis.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CloudLocation:
    label: str
    path: str


# Präfixe bekannter Sync-Ordner im Benutzerverzeichnis (Vergleich ohne
# Groß-/Kleinschreibung). "OneDrive - Firma" und "Dropbox (Team)" werden
# über den Präfix erkannt.
_HOME_PREFIXES = (
    "onedrive",
    "dropbox",
    "google drive",
    "googledrive",
    "my drive",
    "icloud drive",
    "iclouddrive",
    "nextcloud",
    "owncloud",
    "pcloud drive",
    "pclouddrive",
    "mega",
    "megasync",
    "box",
    "box sync",
    "tresorit",
    "proton drive",
    "seafile",
    "yandex.disk",
    "synologydrive",
    "magentacloud",
    "ionos hidrive",
    "hidrive",
)


def _matches_known_name(name: str) -> bool:
    lower = name.lower()
    for prefix in _HOME_PREFIXES:
        if lower == prefix:
            return True
        if lower.startswith(prefix) and len(lower) > len(prefix) and lower[len(prefix)] in " -_(":
            return True
    return False


def _label_for(path: str) -> str:
    name = os.path.basename(os.path.normpath(path)) or path
    lower = name.lower()
    if lower.startswith("onedrive-"):
        # macOS: ~/Library/CloudStorage/OneDrive-Persönlich
        return "OneDrive - " + name.split("-", 1)[1]
    if lower.startswith("googledrive-"):
        return "Google Drive (" + name.split("-", 1)[1] + ")"
    if lower == "com~apple~clouddocs":
        return "iCloud Drive"
    return name


def _windows_sync_roots() -> list[str]:
    """Liest die beim Explorer registrierten Cloud-Sync-Roots (nur lesend)."""
    try:
        import winreg  # type: ignore[import-not-found]
    except ImportError:
        return []

    roots: list[str] = []
    base = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\SyncRootManager"
    try:
        manager = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base, 0, winreg.KEY_READ)
    except OSError:
        return []
    try:
        index = 0
        while True:
            try:
                provider = winreg.EnumKey(manager, index)
            except OSError:
                break
            index += 1
            try:
                user_roots = winreg.OpenKey(manager, provider + r"\UserSyncRoots", 0, winreg.KEY_READ)
            except OSError:
                continue
            try:
                value_index = 0
                while True:
                    try:
                        _, data, _ = winreg.EnumValue(user_roots, value_index)
                    except OSError:
                        break
                    value_index += 1
                    if isinstance(data, str) and data.strip():
                        roots.append(data.strip())
            finally:
                winreg.CloseKey(user_roots)
    finally:
        winreg.CloseKey(manager)
    return roots


def find_cloud_locations(home: str | None = None, environ: dict | None = None,
                         platform: str | None = None) -> list[CloudLocation]:
    """Liefert vorhandene Cloud-Sync-Ordner ohne Duplikate, sortiert nach Name."""
    home = home or str(Path.home())
    environ = os.environ if environ is None else environ
    platform = platform or sys.platform

    candidates: list[str] = []

    for var in ("OneDriveConsumer", "OneDriveCommercial", "OneDrive"):
        value = environ.get(var)
        if value:
            candidates.append(value)

    if platform.startswith("win"):
        candidates.extend(_windows_sync_roots())

    if platform == "darwin":
        cloud_storage = os.path.join(home, "Library", "CloudStorage")
        try:
            for entry in sorted(os.listdir(cloud_storage)):
                candidates.append(os.path.join(cloud_storage, entry))
        except OSError:
            pass
        candidates.append(os.path.join(home, "Library", "Mobile Documents", "com~apple~CloudDocs"))

    try:
        for entry in sorted(os.listdir(home)):
            if _matches_known_name(entry):
                candidates.append(os.path.join(home, entry))
    except OSError:
        pass

    seen: set[str] = set()
    result: list[CloudLocation] = []
    for candidate in candidates:
        try:
            if not os.path.isdir(candidate):
                continue
            key = os.path.normcase(os.path.realpath(candidate))
        except (OSError, ValueError):
            continue
        if key in seen:
            continue
        seen.add(key)
        result.append(CloudLocation(label=_label_for(candidate), path=candidate))

    result.sort(key=lambda loc: loc.label.lower())
    return result
