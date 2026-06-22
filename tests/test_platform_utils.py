from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import Mock


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from core import platform_utils


def test_get_system_open_command_uses_open_on_macos(monkeypatch) -> None:
    monkeypatch.setattr(platform_utils.sys, "platform", "darwin", raising=False)

    assert platform_utils.get_system_open_command("/tmp/datei.txt") == ["open", "/tmp/datei.txt"]


def test_get_system_open_command_uses_xdg_open_on_linux(monkeypatch) -> None:
    monkeypatch.setattr(platform_utils.sys, "platform", "linux", raising=False)

    assert platform_utils.get_system_open_command("/tmp/datei.txt") == ["xdg-open", "/tmp/datei.txt"]


def test_open_path_with_system_uses_startfile_on_windows(monkeypatch, tmp_path) -> None:
    path = str(tmp_path / "Datei.txt")
    (tmp_path / "Datei.txt").write_text("Hallo", encoding="utf-8")
    startfile = Mock()
    run = Mock()

    monkeypatch.setattr(platform_utils.sys, "platform", "win32", raising=False)
    monkeypatch.setattr(platform_utils.os, "startfile", startfile, raising=False)
    monkeypatch.setattr(platform_utils.subprocess, "run", run)

    platform_utils.open_path_with_system(path)

    startfile.assert_called_once_with(path)
    run.assert_not_called()


def test_open_path_with_system_uses_platform_command_on_unix(monkeypatch) -> None:
    run = Mock()

    monkeypatch.setattr(platform_utils.sys, "platform", "darwin", raising=False)
    monkeypatch.setattr(platform_utils.subprocess, "run", run)

    platform_utils.open_path_with_system("/tmp/datei.txt")

    # D4: timeout muss übergeben werden, damit ein hängender Shell-Opener
    # den Prozess nicht unbegrenzt blockiert.
    run.assert_called_once_with(["open", "/tmp/datei.txt"], check=True, timeout=10)
