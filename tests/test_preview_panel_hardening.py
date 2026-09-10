"""
Regression tests for preview_panel.py hardening (BS-20260910):
- TextPreview syntax highlighter dispatch (fixing TypeError in get_lexer_for_extension)
- Multi-format text encoding detection (UTF-8, UTF-16, CP1252)
- ImagePreview stale pixmap clearing and resize safety
- MetadataPanel reset on empty/nonexistent path and negative timestamp resilience
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
from PySide6.QtGui import QImage, QColor

_app = QApplication.instance() or QApplication([])

from gui.preview.preview_panel import TextPreview, ImagePreview, MetadataPanel, PreviewPanel


class TestTextPreviewHighlighter:
    def test_json_syntax_highlighter_attached(self, tmp_path):
        json_file = tmp_path / "test.json"
        json_file.write_text('{"key": "value", "number": 42}', encoding="utf-8")

        preview = TextPreview()
        preview.load_file(str(json_file))

        assert preview._highlighter is not None
        assert type(preview._highlighter).__name__ == "JSONHighlighter"

    def test_markdown_syntax_highlighter_attached(self, tmp_path):
        md_file = tmp_path / "doc.md"
        md_file.write_text("# Title\n\n**Bold text**", encoding="utf-8")

        preview = TextPreview()
        preview.load_file(str(md_file))

        assert preview._highlighter is not None
        assert type(preview._highlighter).__name__ == "MarkdownHighlighter"

    def test_python_syntax_highlighter_attached(self, tmp_path):
        py_file = tmp_path / "script.py"
        py_file.write_text("def hello():\n    print('world')\n", encoding="utf-8")

        preview = TextPreview()
        preview.load_file(str(py_file))

        assert preview._highlighter is not None
        # Should use the rich PythonHighlighter from modules.editor.syntax_highlighter
        assert type(preview._highlighter).__name__ == "PythonHighlighter"

    def test_utf16_text_file_decoded_cleanly(self, tmp_path):
        txt_file = tmp_path / "utf16.txt"
        content = "Übersicht: Häuser und Bäume — 100% Ökologie"
        txt_file.write_bytes(content.encode("utf-16-le"))

        preview = TextPreview()
        preview.load_file(str(txt_file))

        result = preview.toPlainText()
        assert "Häuser und Bäume" in result
        assert "\x00" not in result


class TestImagePreviewStalePixmap:
    def test_corrupt_image_resets_original_pixmap_and_survives_resize(self, tmp_path):
        # 1. First load a valid image
        valid_img_path = tmp_path / "valid.png"
        img = QImage(64, 64, QImage.Format.Format_RGB32)
        img.fill(QColor("blue"))
        img.save(str(valid_img_path))

        preview = ImagePreview()
        preview.resize(150, 150)
        preview.load_image(str(valid_img_path))

        assert preview._original_pixmap is not None
        assert not preview._original_pixmap.isNull()

        # 2. Now load a corrupt image file
        corrupt_img_path = tmp_path / "corrupt.png"
        corrupt_img_path.write_bytes(b"not an image file content")

        preview.load_image(str(corrupt_img_path))

        # Stale pixmap MUST be cleared!
        assert preview._original_pixmap is None
        assert preview.text() == "Bild konnte nicht geladen werden"

        # 3. Simulate window resize / layout change
        preview._scale_to_fit()

        # Error text must persist, not be overwritten by stale previous pixmap
        assert preview.text() == "Bild konnte nicht geladen werden"
        assert preview.pixmap().isNull()


class TestMetadataPanelAndPreviewReset:
    def test_empty_or_nonexistent_path_resets_metadata_panel(self, tmp_path):
        sample_file = tmp_path / "sample.txt"
        sample_file.write_text("hello", encoding="utf-8")

        panel = PreviewPanel()
        panel.show_preview(str(sample_file))

        assert panel.metadata_panel.name_label.text() == "sample.txt"
        assert panel._current_path == str(sample_file)

        # Clear preview by passing empty path
        panel.show_preview("")

        assert panel.preview_stack.currentIndex() == 0
        assert panel.metadata_panel.name_label.text() == "-"
        assert panel.metadata_panel.type_label.text() == "-"
        assert panel.metadata_panel.size_label.text() == "-"
        assert panel._current_path is None

    def test_metadata_handles_negative_or_invalid_timestamp_gracefully(self, tmp_path):
        f = tmp_path / "old.txt"
        f.write_text("timestamp test", encoding="utf-8")

        fake_stat = os.stat(str(f))
        mock_stat_res = MagicMock(
            st_size=100,
            st_mtime=-3600,  # Negative timestamp triggers OSError on Windows
            st_ctime=-3600,
            st_mode=fake_stat.st_mode,
        )

        metadata = MetadataPanel()
        with patch("os.stat", return_value=mock_stat_res):
            # Must not crash!
            metadata.show_metadata(str(f))

        assert metadata.name_label.text() == "old.txt"
        assert metadata.modified_label.text() in ("-", "Unbekannt", "01.01.1970 00:00")


class TestExcelPreviewExternalLaunch:
    def test_open_extern_handles_os_error_gracefully(self, tmp_path):
        from gui.preview.preview_panel import ExcelPreview

        widget = ExcelPreview()
        widget._path = str(tmp_path / "fake.xlsx")

        with patch("os.startfile", side_effect=OSError("No application associated")):
            widget._open_extern()

        assert not widget.status_label.isHidden()
        assert "Externes Öffnen fehlgeschlagen" in widget.status_label.text()
