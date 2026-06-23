from __future__ import annotations

import os
import ntpath
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
    return _read_shortcut_target_with_powershell(path)


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
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None

    target = result.stdout.strip()
    return target or None
