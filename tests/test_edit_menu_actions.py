"""
Bugfix-Test (Folgebefund zum Usertest Welle 1, 2026-08-14):

Bei der Untersuchung der beiden gemeldeten Menuepunkte fielen drei weitere
QActions derselben Defektklasse auf, die nie mit triggered.connect verbunden
waren und deshalb garantiert nichts ausloesten:

  * Datei -> "Neues Fenster" (main_window.py)
  * Bearbeiten -> "Kopieren" und "Einfuegen" (main_window.py)
  * dieselben Eintraege im Kontextmenue des Dateibrowsers

Die Tests halten die Verdrahtung sowie den Zwischenablage-Rundlauf fest.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PySide6.QtWidgets import QApplication  # noqa: E402

_app = QApplication.instance() or QApplication([])

from gui.browser.file_browser import FileBrowser  # noqa: E402
from gui.main_window import MainWindow  # noqa: E402


@pytest.fixture
def clean_clipboard():
    """Entfernt temporäre Datei-URLs vor QApplication-Finalisierung."""
    yield
    QApplication.clipboard().clear()
    QApplication.processEvents()


class TestClipboardOperations:
    """Kopieren und Einfuegen muessen echte Dateien bewegen."""

    def test_copy_selection_without_selection_returns_false(self):
        browser = FileBrowser()
        assert browser.copy_selection() is False

    def test_paste_without_clipboard_content_returns_false(self):
        QApplication.clipboard().clear()
        browser = FileBrowser()
        assert browser.paste_from_clipboard() is False

    def test_copy_then_paste_duplicates_file(self, tmp_path, monkeypatch, clean_clipboard):
        quelle = tmp_path / "quelle"
        ziel = tmp_path / "ziel"
        quelle.mkdir()
        ziel.mkdir()
        datei = quelle / "beispiel.txt"
        datei.write_text("Grüße mit Umlauten", encoding="utf-8")

        browser = FileBrowser()
        monkeypatch.setattr(browser, "get_selected_files", lambda: [str(datei)])

        assert browser.copy_selection() is True

        browser._current_path = str(ziel)
        assert browser.paste_from_clipboard() is True
        assert (ziel / "beispiel.txt").exists()
        assert (ziel / "beispiel.txt").read_text(encoding="utf-8") == "Grüße mit Umlauten"


class TestEditMenuWiring:
    """Die Menuepunkte muessen die Browser-Methoden aufrufen."""

    def test_copy_menu_action_calls_browser(self, monkeypatch):
        win = MainWindow()
        aufrufe = []
        monkeypatch.setattr(
            win.file_browser, "copy_selection", lambda: aufrufe.append("copy") or True
        )
        win._copy_selection()
        win.close()
        assert aufrufe == ["copy"]

    def test_paste_menu_action_calls_browser(self, monkeypatch):
        win = MainWindow()
        aufrufe = []
        monkeypatch.setattr(
            win.file_browser,
            "paste_from_clipboard",
            lambda: aufrufe.append("paste") or True,
        )
        win._paste_clipboard()
        win.close()
        assert aufrufe == ["paste"]

    def test_new_window_is_created_and_referenced(self):
        win = MainWindow()
        neu = win._open_new_window()

        assert isinstance(neu, MainWindow)
        assert neu in win._child_windows
        neu.close()
        win.close()
