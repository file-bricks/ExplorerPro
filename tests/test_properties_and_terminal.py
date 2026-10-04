#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_properties_and_terminal.py - Vertragstests für Eigenschaften-Dialog,
Pfad-Kopier-Funktionen und Terminal-Integration (TW-EP-11).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication([])

from core.platform_utils import get_terminal_command, open_terminal_in_directory
from gui.browser.file_browser import FileBrowser, _DnDTableView
from gui.main_window import MainWindow
from gui.properties_dialog import FilePropertiesDialog, calculate_folder_stats, format_size


@pytest.fixture
def clean_clipboard():
    yield
    QApplication.clipboard().clear()
    QApplication.processEvents()


class TestFormatSizeAndFolderStats:
    """Formatierungs- und Ordnerstatistik-Tests."""

    def test_format_size_units(self):
        assert format_size(-5) == "0 Bytes"
        assert format_size(500) == "500 Bytes"
        assert "KB" in format_size(2048)
        assert "MB" in format_size(5 * 1024 * 1024)
        assert "GB" in format_size(3 * 1024 * 1024 * 1024)

    def test_calculate_folder_stats(self, tmp_path):
        sub1 = tmp_path / "sub1"
        sub1.mkdir()
        sub2 = tmp_path / "sub2"
        sub2.mkdir()
        f1 = sub1 / "test1.txt"
        f1.write_text("Hello World", encoding="utf-8")
        f2 = sub2 / "test2.txt"
        f2.write_text("Testing 123", encoding="utf-8")

        file_count, dir_count, total_bytes = calculate_folder_stats(str(tmp_path))
        assert file_count == 2
        assert dir_count == 2
        assert total_bytes == len("Hello World") + len("Testing 123")

    def test_calculate_folder_stats_nonexistent(self, tmp_path):
        assert calculate_folder_stats(str(tmp_path / "ghost")) == (0, 0, 0)


class TestPlatformTerminal:
    """Plattformspezifische Terminal-Befehle und Start-Logik."""

    def test_get_terminal_command_windows(self):
        with patch("sys.platform", "win32"), patch("shutil.which", return_value="C:\\Windows\\System32\\cmd.exe"):
            cmd = get_terminal_command("C:\\Test")
            assert isinstance(cmd, list)
            assert any("cmd" in c or "powershell" in c or "wt" in c for c in cmd)

    def test_windows_terminal_does_not_receive_directory_as_command_text(self):
        directory = r"C:\Users\test\a; new-tab -p PowerShell"
        with patch("sys.platform", "win32"), patch(
            "shutil.which",
            side_effect=lambda executable: "wt.exe" if executable == "wt" else None,
        ):
            assert get_terminal_command(directory) == ["wt", "-d", "."]

    def test_windows_powershell_fallback_does_not_interpolate_directory(self):
        directory = r"C:\Users\test\x'; Start-Process calc; '"
        with patch("sys.platform", "win32"), patch(
            "shutil.which",
            side_effect=lambda executable: "powershell.exe" if executable == "powershell" else None,
        ):
            assert get_terminal_command(directory) == ["powershell", "-NoExit"]

    def test_windows_cmd_fallback_does_not_interpolate_directory(self):
        directory = r"C:\Users\test\a&calc"
        with patch("sys.platform", "win32"), patch("shutil.which", return_value=None):
            assert get_terminal_command(directory) == ["cmd", "/K"]

    def test_get_terminal_command_darwin(self):
        with patch("sys.platform", "darwin"):
            cmd = get_terminal_command("/Users/test")
            assert cmd == ["open", "-a", "Terminal", "/Users/test"]

    def test_get_terminal_command_linux(self):
        with patch("sys.platform", "linux"), patch("shutil.which", lambda t: "/usr/bin/xterm" if t == "xterm" else None):
            cmd = get_terminal_command("/home/user")
            assert cmd == ["xterm"]

    def test_open_terminal_in_directory_launches_process(self, tmp_path):
        target = tmp_path / "somedir"
        target.mkdir()
        with patch("subprocess.Popen") as mock_popen:
            open_terminal_in_directory(str(target))
            assert mock_popen.called
            args, kwargs = mock_popen.call_args
            assert kwargs.get("cwd") == str(target)

    def test_open_terminal_uses_cwd_for_windows_metacharacter_path(self, tmp_path):
        target = tmp_path / "x'&calc"
        target.mkdir()
        with (
            patch("sys.platform", "win32"),
            patch("shutil.which", return_value=None),
            patch("subprocess.Popen") as mock_popen,
        ):
            open_terminal_in_directory(str(target))

        args, kwargs = mock_popen.call_args
        assert args[0] == ["cmd", "/K"]
        assert kwargs["cwd"] == str(target)

    def test_open_terminal_uses_cwd_with_windows_terminal(self, tmp_path):
        target = tmp_path / "a; new-tab -p PowerShell"
        target.mkdir()
        with (
            patch("sys.platform", "win32"),
            patch("shutil.which", side_effect=lambda executable: "wt.exe" if executable == "wt" else None),
            patch("subprocess.Popen") as mock_popen,
        ):
            open_terminal_in_directory(str(target))

        args, kwargs = mock_popen.call_args
        assert args[0] == ["wt", "-d", "."]
        assert kwargs["cwd"] == str(target)


class TestCopyPathOperations:
    """Pfad-Kopier-Funktionen in FileBrowser."""

    def test_copy_single_path_to_clipboard(self, tmp_path, monkeypatch, clean_clipboard):
        f = tmp_path / "datei.txt"
        f.write_text("Inhalt", encoding="utf-8")

        browser = FileBrowser()
        monkeypatch.setattr(browser, "get_selected_files", lambda: [str(f)])

        res = browser.copy_path_to_clipboard()
        assert res == str(f)
        assert QApplication.clipboard().text() == str(f)

    def test_copy_multiple_paths_to_clipboard(self, tmp_path, monkeypatch, clean_clipboard):
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"

        browser = FileBrowser()
        monkeypatch.setattr(browser, "get_selected_files", lambda: [str(f1), str(f2)])

        res = browser.copy_path_to_clipboard()
        expected = f"{f1}\n{f2}"
        assert res == expected
        assert QApplication.clipboard().text() == expected

    def test_copy_name_only_to_clipboard(self, tmp_path, monkeypatch, clean_clipboard):
        f = tmp_path / "meine_datei.pdf"

        browser = FileBrowser()
        monkeypatch.setattr(browser, "get_selected_files", lambda: [str(f)])

        res = browser.copy_path_to_clipboard(name_only=True)
        assert res == "meine_datei.pdf"
        assert QApplication.clipboard().text() == "meine_datei.pdf"

    def test_copy_relative_path_to_clipboard(self, tmp_path, monkeypatch, clean_clipboard):
        sub = tmp_path / "sub"
        f = sub / "doc.txt"

        browser = FileBrowser()
        browser._current_path = str(tmp_path)
        monkeypatch.setattr(browser, "get_selected_files", lambda: [str(f)])

        res = browser.copy_path_to_clipboard(relative=True)
        assert res == os.path.join("sub", "doc.txt")

    def test_copy_path_fallback_current_path(self, tmp_path, monkeypatch, clean_clipboard):
        browser = FileBrowser()
        browser._current_path = str(tmp_path)
        monkeypatch.setattr(browser, "get_selected_files", lambda: [])

        res = browser.copy_path_to_clipboard()
        assert res == str(tmp_path)
        assert QApplication.clipboard().text() == str(tmp_path)


class TestFilePropertiesDialog:
    """Initialisierung und Datenintegrität des Eigenschaften-Dialogs."""

    def test_dialog_for_file(self, tmp_path):
        f = tmp_path / "notiz.txt"
        f.write_text("Zeile 1\nZeile 2\nZeile 3 mit Worten\n", encoding="utf-8")

        dlg = FilePropertiesDialog(str(f))
        assert dlg.name_edit.text() == "notiz.txt"
        assert dlg.tabs.count() == 2
        assert dlg.sha256_edit.text() != ""
        assert dlg.md5_edit.text() != ""
        dlg.close()

    def test_dialog_for_directory(self, tmp_path):
        sub = tmp_path / "projekt_ordner"
        sub.mkdir()
        (sub / "datei.txt").write_text("Hello", encoding="utf-8")

        dlg = FilePropertiesDialog(str(sub))
        assert dlg.name_edit.text() == "projekt_ordner"
        assert dlg.is_dir is True
        dlg.close()

    def test_dialog_copy_path_button(self, tmp_path, clean_clipboard):
        f = tmp_path / "test.txt"
        f.write_text("abc", encoding="utf-8")
        dlg = FilePropertiesDialog(str(f))
        with patch("PySide6.QtWidgets.QMessageBox.information"):
            dlg.copy_path_btn.click()
        assert QApplication.clipboard().text() == str(f)
        dlg.close()


class TestMainWindowAndKeyboardShortcuts:
    """Verdrahtung in Menüleiste und Tastenkürzeln."""

    def test_main_window_wiring(self, monkeypatch):
        win = MainWindow()
        calls = []

        monkeypatch.setattr(win.file_browser, "show_properties", lambda: calls.append("prop") or True)
        monkeypatch.setattr(win.file_browser, "copy_path_to_clipboard", lambda: calls.append("copy_path") or "ok")
        monkeypatch.setattr(win.file_browser, "open_terminal", lambda: calls.append("term") or True)

        win._show_properties()
        win._copy_path()
        win._open_terminal()
        win.close()

        assert "prop" in calls
        assert "copy_path" in calls
        assert "term" in calls

    def test_dnd_table_view_shortcuts(self, tmp_path, monkeypatch):
        browser = FileBrowser()
        table = _DnDTableView(browser)
        calls = []

        monkeypatch.setattr(browser, "show_properties", lambda: calls.append("prop") or True)
        monkeypatch.setattr(browser, "copy_path_to_clipboard", lambda: calls.append("copy_path") or "ok")

        # Alt+Enter -> show_properties
        event_alt_enter = QKeyEvent(
            QKeyEvent.Type.KeyPress,
            Qt.Key.Key_Return,
            Qt.KeyboardModifier.AltModifier
        )
        table.keyPressEvent(event_alt_enter)
        assert "prop" in calls

        # Ctrl+Shift+C -> copy_path_to_clipboard
        event_ctrl_shift_c = QKeyEvent(
            QKeyEvent.Type.KeyPress,
            Qt.Key.Key_C,
            Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier
        )
        table.keyPressEvent(event_ctrl_shift_c)
        assert "copy_path" in calls
