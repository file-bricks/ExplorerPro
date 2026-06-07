"""
Bugfix-Test: file_index.py extract_text() – fitz.Document wird nun
in einem try/finally-Block geschlossen, auch wenn page.get_text() wirft.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# QApplication zuerst, damit PySide6-Imports in file_index funktionieren
from PySide6.QtWidgets import QApplication
_app = QApplication.instance() or QApplication([])

import core.file_index as fi_mod


class TestFitzResourceLeak:
    """fitz.Document.close() muss auch bei Ausnahmen aufgerufen werden."""

    def _make_idx(self):
        idx = fi_mod.FileIndex.__new__(fi_mod.FileIndex)
        return idx

    def test_close_called_on_success(self, tmp_path):
        fake_pdf = tmp_path / "test.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4")

        page = MagicMock()
        page.get_text.return_value = "Hallo Welt"

        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([page]))
        mock_doc.close = MagicMock()

        mock_fitz = MagicMock()
        mock_fitz.open.return_value = mock_doc

        idx = self._make_idx()
        with patch.object(fi_mod, "fitz", mock_fitz), \
             patch.object(fi_mod, "HAS_FITZ", True), \
             patch.object(fi_mod, "HAS_PDF", False):
            result = idx.extract_text(str(fake_pdf))

        mock_doc.close.assert_called_once()
        assert result is not None

    def test_close_called_on_exception(self, tmp_path):
        """RESOURCE LEAK: close() muss aufgerufen werden, auch wenn page.get_text() wirft."""
        fake_pdf = tmp_path / "boom.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4")

        page = MagicMock()
        page.get_text.side_effect = RuntimeError("Seiten-Fehler")

        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([page]))
        mock_doc.close = MagicMock()

        mock_fitz = MagicMock()
        mock_fitz.open.return_value = mock_doc

        idx = self._make_idx()
        with patch.object(fi_mod, "fitz", mock_fitz), \
             patch.object(fi_mod, "HAS_FITZ", True), \
             patch.object(fi_mod, "HAS_PDF", False):
            result = idx.extract_text(str(fake_pdf))

        mock_doc.close.assert_called_once(), (
            "RESOURCE LEAK: close() wurde bei Ausnahme in page.get_text() nicht aufgerufen"
        )
        assert result is None
