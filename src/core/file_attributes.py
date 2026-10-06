#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
file_attributes — erkennt Cloud-Platzhalter ohne sie herunterzuladen.

OneDrive, Dropbox, iCloud & Co. legen bei "Dateien bei Bedarf" lokale
Platzhalter an. Das Lesen des Inhalts löst einen Download aus, der bei
langsamer oder fehlender Verbindung die Oberfläche blockiert. Die Prüfung
nutzt ausschließlich Metadaten (``lstat``) und greift nie auf Inhalte zu.
"""
from __future__ import annotations

import os
import stat
import sys

# Windows-Dateiattribute (winnt.h)
FILE_ATTRIBUTE_OFFLINE = 0x00001000
FILE_ATTRIBUTE_RECALL_ON_OPEN = 0x00040000
FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS = 0x00400000
_WINDOWS_CLOUD_ATTRIBUTES = (
    FILE_ATTRIBUTE_OFFLINE | FILE_ATTRIBUTE_RECALL_ON_OPEN | FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS
)

# macOS: SF_DATALESS (sys/stat.h) markiert iCloud-/File-Provider-Platzhalter.
SF_DATALESS = 0x40000000


def is_cloud_placeholder(path: str, stat_result=None, platform: str | None = None) -> bool:
    """True, wenn *path* ein nicht lokal vorhandener Cloud-Platzhalter ist."""
    platform = platform or sys.platform
    try:
        st = stat_result if stat_result is not None else os.lstat(path)
    except (OSError, ValueError):
        return False

    if platform.startswith("win"):
        attributes = getattr(st, "st_file_attributes", 0) or 0
        return bool(attributes & _WINDOWS_CLOUD_ATTRIBUTES)

    if platform == "darwin":
        flags = getattr(st, "st_flags", 0) or 0
        return bool(flags & SF_DATALESS) and stat.S_ISREG(st.st_mode)

    return False
