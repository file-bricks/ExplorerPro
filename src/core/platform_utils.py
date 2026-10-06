from __future__ import annotations

import os
import shutil
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


def get_terminal_command(directory: str) -> list[str]:
    """Return the platform-native terminal launcher command for a directory."""
    if sys.platform.startswith("win"):
        if shutil.which("wt"):
            # Windows Terminal treats semicolons as command separators. Use
            # the Popen working directory instead of passing an untrusted path.
            return ["wt", "-d", "."]
        if shutil.which("powershell"):
            # open_terminal_in_directory passes cwd to Popen; never interpolate
            # a path into a shell-interpreted command.
            return ["powershell", "-NoExit"]
        return ["cmd", "/K"]
    if sys.platform == "darwin":
        return ["open", "-a", "Terminal", directory]
    # Linux / BSD
    for term in ["xdg-terminal-exec", "gnome-terminal", "konsole", "xfce4-terminal", "xterm"]:
        if shutil.which(term):
            if term == "gnome-terminal":
                return ["gnome-terminal", f"--working-directory={directory}"]
            if term == "konsole":
                return ["konsole", "--workdir", directory]
            if term == "xfce4-terminal":
                return ["xfce4-terminal", f"--working-directory={directory}"]
            return [term]
    return ["xterm"]


def open_terminal_in_directory(path: str) -> subprocess.Popen:
    """Launch a terminal emulator session located in the given directory or file parent."""
    target_dir = path if os.path.isdir(path) else os.path.dirname(path)
    if not target_dir or not os.path.exists(target_dir):
        target_dir = os.getcwd()
    cmd = get_terminal_command(os.path.abspath(target_dir))
    flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0) if sys.platform.startswith("win") else 0
    return subprocess.Popen(cmd, cwd=target_dir, creationflags=flags)


def normalize_user_path(path: str) -> str:
    """Bereinigt einen vom Nutzer eingegebenen oder eingefügten Pfad.

    Entfernt umschließende Anführungszeichen (Windows "Als Pfad kopieren"),
    wandelt ``file://``-URLs um und expandiert ``~`` sowie Umgebungsvariablen
    wie ``%OneDrive%`` oder ``$HOME``.
    """
    if not path:
        return path
    text = str(path).strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        text = text[1:-1].strip()
    if text.lower().startswith("file:"):
        from urllib.parse import unquote, urlparse

        parsed = urlparse(text)
        local = unquote(parsed.path)
        if sys.platform.startswith("win") and len(local) > 2 and local[0] == "/" and local[2] == ":":
            local = local[1:]
        if parsed.netloc and parsed.netloc.lower() != "localhost":
            local = f"//{parsed.netloc}{local}"
        text = os.path.normpath(local)
    return os.path.expandvars(os.path.expanduser(text))
