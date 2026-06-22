from __future__ import annotations

import os
import subprocess
import sys


def get_system_open_command(path: str) -> list[str] | None:
    """Return the native desktop opener command for the current platform."""
    if sys.platform.startswith("win"):
        return None
    if sys.platform == "darwin":
        return ["open", path]
    return ["xdg-open", path]


def open_path_with_system(path: str) -> None:
    """Open a file or folder with the platform-native shell handler."""
    command = get_system_open_command(path)
    if command is None:
        os.startfile(path)
        return
    # D4: timeout verhindert, dass ein haengender Shell-Opener den Prozess blockiert.
    subprocess.run(command, check=True, timeout=10)
