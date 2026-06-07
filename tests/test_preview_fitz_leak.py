"""
Bugfix-Test: preview_panel.py PdfPreview.load_pdf() – fitz.Document wird nun
in einem try/finally-Block geschlossen, auch wenn get_pixmap() wirft.
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

from PySide6.QtWidgets import QApplication
_app = QApplication.instance() or QApplication([])

import gui.preview.preview_panel as pp_mod


class TestPdfPreviewFitzLeak:
    """fitz.Document.close() muss auch bei Ausnahmen in get_pixmap() aufgerufen werden."""

    def _make_preview(self):
        preview = pp_mod.PdfPreview.__new__(pp_mod.PdfPreview)
        preview.content = MagicMock()
        return preview

    def test_close_called_on_success(self, tmp_path):
        fake_pdf = tmp_path / "ok.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4")

        pix = MagicMock()
        pix.samples = b"\x00" * (10 * 10 * 3)
        pix.width = 10
        pix.height = 10
        pix.stride = 30

        page = MagicMock()
        page.get_pixmap.return_value = pix

        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=1)
        mock_doc.__getitem__ = MagicMock(return_value=page)
        mock_doc.close = MagicMock()

        mock_fitz = MagicMock()
        mock_fitz.open.return_value = mock_doc
        mock_fitz.Matrix = MagicMock(return_value=MagicMock())

        preview = self._make_preview()
        with patch.object(pp_mod, "fitz", mock_fitz), \
             patch.object(pp_mod, "HAS_FITZ", True):
            preview.load_pdf(str(fake_pdf))

        mock_doc.close.assert_called_once()

    def test_close_called_on_exception(self, tmp_path):
        """RESOURCE LEAK: close() muss aufgerufen werden, auch wenn get_pixmap() wirft."""
        fake_pdf = tmp_path / "boom.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4")

        page = MagicMock()
        page.get_pixmap.side_effect = RuntimeError("Render-Fehler")

        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=1)
        mock_doc.__getitem__ = MagicMock(return_value=page)
        mock_doc.close = MagicMock()

        mock_fitz = MagicMock()
        mock_fitz.open.return_value = mock_doc
        mock_fitz.Matrix = MagicMock(return_value=MagicMock())

        preview = self._make_preview()
        with patch.object(pp_mod, "fitz", mock_fitz), \
             patch.object(pp_mod, "HAS_FITZ", True):
            preview.load_pdf(str(fake_pdf))

        mock_doc.close.assert_called_once(), (
            "RESOURCE LEAK: close() wurde bei Ausnahme in get_pixmap() nicht aufgerufen"
        )
        preview.content.setText.assert_called()
