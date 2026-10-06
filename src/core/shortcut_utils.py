from __future__ import annotations

import os
import ntpath
import struct
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ShortcutPreviewTarget:
    target_path: str
    preview_path: str
    target_kind: str


def is_windows_shortcut(path: str) -> bool:
    return Path(path).suffix.lower() == ".lnk"


def resolve_windows_shortcut_target(path: str) -> str | None:
    """Resolve a Windows .lnk target path without adding a runtime dependency."""
    if not is_windows_shortcut(path) or not sys.platform.startswith("win"):
        return None

    target = _read_shortcut_target_with_win32com(path)
    if target:
        return target
    # Reiner Python-Parser: kein Kindprozess, kein Konsolenfenster, keine
    # Wartezeit im GUI-Thread. PowerShell bleibt nur letzter Ausweg.
    target = read_shortcut_target_native(path)
    if target:
        return target
    return _read_shortcut_target_with_powershell(path)


# MS-SHLLINK Konstanten
_LNK_HEADER_SIZE = 0x4C
_LNK_CLSID = bytes.fromhex("0114020000000000c000000000000046")
_HAS_LINK_TARGET_ID_LIST = 0x01
_HAS_LINK_INFO = 0x02
_HAS_NAME = 0x04
_HAS_RELATIVE_PATH = 0x08
_HAS_WORKING_DIR = 0x10
_HAS_ARGUMENTS = 0x20
_HAS_ICON_LOCATION = 0x40
_IS_UNICODE = 0x80
_HAS_EXP_STRING = 0x200
_ENVIRONMENT_BLOCK_SIGNATURE = 0xA0000001
_MAX_LNK_BYTES = 1024 * 1024


def _c_string(data: bytes, offset: int, unicode: bool) -> str:
    if offset <= 0 or offset >= len(data):
        return ""
    if unicode:
        end = offset
        while end + 1 < len(data) and data[end:end + 2] != b"\x00\x00":
            end += 2
        return data[offset:end].decode("utf-16-le", errors="replace")
    end = data.find(b"\x00", offset)
    if end < 0:
        end = len(data)
    raw = data[offset:end]
    try:
        return raw.decode("mbcs", errors="replace")  # ANSI-Codepage (nur Windows)
    except LookupError:
        return raw.decode("cp1252", errors="replace")


def parse_shortcut_target(data: bytes) -> str | None:
    """Liest das Ziel einer Windows-Verknüpfung (MS-SHLLINK) aus Rohdaten."""
    if len(data) < _LNK_HEADER_SIZE or struct.unpack_from("<I", data, 0)[0] != _LNK_HEADER_SIZE:
        return None
    if data[4:20] != _LNK_CLSID:
        return None
    flags = struct.unpack_from("<I", data, 0x14)[0]
    offset = _LNK_HEADER_SIZE

    if flags & _HAS_LINK_TARGET_ID_LIST:
        if offset + 2 > len(data):
            return None
        offset += 2 + struct.unpack_from("<H", data, offset)[0]

    target = ""
    if flags & _HAS_LINK_INFO and offset + 28 <= len(data):
        info = data[offset:]
        info_size, header_size, info_flags, _volume, local_base, _network, suffix = struct.unpack_from(
            "<7I", info, 0
        )
        info = info[:info_size]
        local_base_unicode = suffix_unicode = 0
        if header_size >= 0x24 and len(info) >= 0x24:
            local_base_unicode, suffix_unicode = struct.unpack_from("<2I", info, 0x1C)
        if info_flags & 0x01:  # VolumeIDAndLocalBasePath
            base = (_c_string(info, local_base_unicode, True) if local_base_unicode
                    else _c_string(info, local_base, False))
            tail = (_c_string(info, suffix_unicode, True) if suffix_unicode
                    else _c_string(info, suffix, False))
            target = base + tail  # MS-SHLLINK: einfache Verkettung
        offset += info_size

    # Optionale StringData-Blöcke überspringen, um ExtraData zu erreichen.
    unicode = bool(flags & _IS_UNICODE)
    for flag in (_HAS_NAME, _HAS_RELATIVE_PATH, _HAS_WORKING_DIR, _HAS_ARGUMENTS, _HAS_ICON_LOCATION):
        if not flags & flag:
            continue
        if offset + 2 > len(data):
            break
        count = struct.unpack_from("<H", data, offset)[0]
        offset += 2 + count * (2 if unicode else 1)

    if not target and flags & _HAS_EXP_STRING:
        while offset + 8 <= len(data):
            size, signature = struct.unpack_from("<2I", data, offset)
            if size < 8:
                break
            if signature == _ENVIRONMENT_BLOCK_SIGNATURE and size >= 0x314:
                block = data[offset:offset + size]
                target = _c_string(block, 0x10C, True) or _c_string(block, 8, False)
                break
            offset += size

    return target.strip() or None


def read_shortcut_target_native(path: str) -> str | None:
    try:
        with open(path, "rb") as handle:
            data = handle.read(_MAX_LNK_BYTES)
    except OSError:
        return None
    try:
        return parse_shortcut_target(data)
    except (struct.error, ValueError, LookupError):
        return None


def build_shortcut_preview_target(path: str) -> ShortcutPreviewTarget | None:
    target = resolve_windows_shortcut_target(path)
    if not target:
        return None

    target_path = Path(os.path.expandvars(ntpath.expandvars(target))).expanduser()
    if target_path.is_dir():
        return ShortcutPreviewTarget(
            target_path=str(target_path),
            preview_path=str(target_path),
            target_kind="directory",
        )

    if target_path.is_file() and target_path.suffix.lower() == ".exe":
        return ShortcutPreviewTarget(
            target_path=str(target_path),
            preview_path=str(target_path.parent),
            target_kind="executable_parent",
        )

    if target_path.exists():
        return ShortcutPreviewTarget(
            target_path=str(target_path),
            preview_path=str(target_path),
            target_kind="file",
        )

    return None


def _read_shortcut_target_with_win32com(path: str) -> str | None:
    try:
        import win32com.client  # type: ignore[import-untyped]
    except ImportError:
        return None

    try:
        shortcut = win32com.client.Dispatch("WScript.Shell").CreateShortcut(str(path))
        target = getattr(shortcut, "TargetPath", "") or getattr(shortcut, "Targetpath", "")
    except Exception:
        return None
    return str(target).strip() or None


def _read_shortcut_target_with_powershell(path: str) -> str | None:
    script = (
        "$s=(New-Object -ComObject WScript.Shell).CreateShortcut($args[0]);"
        "[Console]::OutputEncoding=[Text.UTF8Encoding]::new();"
        "Write-Output $s.TargetPath"
    )
    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                script,
                str(path),
            ],
            capture_output=True,
            check=True,
            encoding="utf-8",
            errors="replace",
            text=True,
            timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None

    target = result.stdout.strip()
    return target or None
