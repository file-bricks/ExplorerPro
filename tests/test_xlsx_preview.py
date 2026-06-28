"""
Tests für den Excel-Vorschau-Reader (Pure Logic) und die GUI-Integration.

Pure-Logic-Tests (TestXlsxReader) benötigen kein Qt.
GUI-Tests (TestExcelPreviewWidget, TestPreviewPanelExcel) laufen im Offscreen-Modus.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import pytest
import openpyxl
from PySide6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication([])


# ── Fixture-Hilfsfunktion ────────────────────────────────────────────────────

def _make_xlsx(path: Path, sheets: dict[str, list[list]]) -> None:
    """Erzeugt eine .xlsx-Datei programmatisch via openpyxl."""
    wb = openpyxl.Workbook()
    first = True
    for sheet_name, data in sheets.items():
        if first:
            ws = wb.active
            ws.title = sheet_name
            first = False
        else:
            ws = wb.create_sheet(title=sheet_name)
        for row in data:
            ws.append(row)
    wb.save(str(path))


# ── Pure-Logic-Tests ─────────────────────────────────────────────────────────

class TestXlsxReader:
    def test_sheet_list_single(self, tmp_path):
        from core.xlsx_reader import read_workbook_meta

        f = tmp_path / "single.xlsx"
        _make_xlsx(f, {"Tabelle1": [["A", "B"], [1, 2]]})
        meta = read_workbook_meta(str(f))

        assert meta.error is None
        assert meta.sheets == ["Tabelle1"]
        assert meta.active_sheet == "Tabelle1"

    def test_sheet_list_multi(self, tmp_path):
        from core.xlsx_reader import read_workbook_meta

        f = tmp_path / "multi.xlsx"
        _make_xlsx(f, {"Alpha": [[1]], "Beta": [[2]], "Gamma": [[3]]})
        meta = read_workbook_meta(str(f))

        assert meta.error is None
        assert meta.sheets == ["Alpha", "Beta", "Gamma"]
        assert meta.active_sheet == "Alpha"

    def test_first_rows_and_cols(self, tmp_path):
        from core.xlsx_reader import read_workbook_sheet

        f = tmp_path / "data.xlsx"
        _make_xlsx(f, {"Daten": [["Name", "Wert"], ["Alice", 42], ["Bob", 7]]})
        rows = read_workbook_sheet(str(f), "Daten")

        assert rows[0][:2] == ["Name", "Wert"]
        assert rows[1][:2] == ["Alice", 42]
        assert rows[2][:2] == ["Bob", 7]

    def test_empty_sheet(self, tmp_path):
        from core.xlsx_reader import read_workbook_sheet

        f = tmp_path / "empty.xlsx"
        _make_xlsx(f, {"Leer": []})
        rows = read_workbook_sheet(str(f), "Leer")

        # Leeres Blatt liefert entweder [] oder Zeilen mit ausschließlich None
        assert rows == [] or all(all(c is None for c in r) for r in rows)

    def test_max_rows_limit(self, tmp_path):
        from core.xlsx_reader import read_workbook_sheet, MAX_ROWS

        f = tmp_path / "big.xlsx"
        data = [[i] for i in range(MAX_ROWS + 20)]
        _make_xlsx(f, {"Groß": data})
        rows = read_workbook_sheet(str(f), "Groß")

        assert len(rows) <= MAX_ROWS

    def test_fallback_corrupt_file(self, tmp_path):
        """Eine Nicht-Excel-Datei mit .xlsx-Endung liefert einen Fehler im meta.error."""
        from core.xlsx_reader import read_workbook_meta

        f = tmp_path / "fake.xlsx"
        f.write_bytes(b"das ist kein Excel")
        meta = read_workbook_meta(str(f))

        assert meta.error is not None

    def test_fallback_missing_openpyxl(self, tmp_path, monkeypatch):
        """Fehlendes openpyxl wird sauber als Fehlertext zurückgegeben (kein Crash)."""
        import core.xlsx_reader as reader_mod

        monkeypatch.setattr(reader_mod, "HAS_OPENPYXL", False)
        monkeypatch.setattr(reader_mod, "openpyxl", None)

        f = tmp_path / "x.xlsx"
        _make_xlsx(f, {"A": [[1]]})
        meta = reader_mod.read_workbook_meta(str(f))

        assert meta.error is not None
        assert "openpyxl" in meta.error.lower()

    def test_read_sheet_raises_on_missing_openpyxl(self, tmp_path, monkeypatch):
        """read_workbook_sheet wirft XlsxReadError wenn openpyxl fehlt."""
        import core.xlsx_reader as reader_mod
        from core.xlsx_reader import XlsxReadError

        monkeypatch.setattr(reader_mod, "HAS_OPENPYXL", False)
        monkeypatch.setattr(reader_mod, "openpyxl", None)

        f = tmp_path / "y.xlsx"
        _make_xlsx(f, {"A": [[1]]})

        with pytest.raises(XlsxReadError):
            reader_mod.read_workbook_sheet(str(f), "A")


# ── Widget-Tests (mit Qt) ────────────────────────────────────────────────────

class TestExcelPreviewWidget:
    def test_loads_sheet_names_into_combo(self, tmp_path):
        from gui.preview.preview_panel import ExcelPreview

        f = tmp_path / "m.xlsx"
        _make_xlsx(f, {"Blatt1": [[1, 2]], "Blatt2": [[3, 4]]})
        widget = ExcelPreview()
        widget.load_file(str(f))

        items = [widget.sheet_combo.itemText(i) for i in range(widget.sheet_combo.count())]
        assert "Blatt1" in items
        assert "Blatt2" in items

    def test_table_filled_with_data(self, tmp_path):
        from gui.preview.preview_panel import ExcelPreview

        f = tmp_path / "data.xlsx"
        _make_xlsx(f, {"Sheet": [["X", "Y"], [10, 20]]})
        widget = ExcelPreview()
        widget.load_file(str(f))

        assert widget.table.rowCount() >= 2
        assert widget.table.columnCount() >= 2

    def test_fallback_shown_on_corrupt_file(self, tmp_path):
        from gui.preview.preview_panel import ExcelPreview

        f = tmp_path / "bad.xlsx"
        f.write_bytes(b"kein Excel")
        widget = ExcelPreview()
        widget.load_file(str(f))

        # isHidden() prüft den Widget-eigenen Sichtbarkeits-Flag unabhängig vom
        # Parent; isVisible() wäre im Offscreen-Modus ohne show() immer False.
        assert not widget.status_label.isHidden()
        assert not widget.open_extern_btn.isHidden()

    def test_status_hidden_on_valid_file(self, tmp_path):
        from gui.preview.preview_panel import ExcelPreview

        f = tmp_path / "ok.xlsx"
        _make_xlsx(f, {"Tabelle": [["A", "B"]]})
        widget = ExcelPreview()
        widget.load_file(str(f))

        assert widget.status_label.isHidden()
        assert widget.open_extern_btn.isHidden()


# ── PreviewPanel-Integrationstests ──────────────────────────────────────────

class TestPreviewPanelExcel:
    def test_shows_excel_widget_for_xlsx(self, tmp_path):
        from gui.preview.preview_panel import PreviewPanel

        f = tmp_path / "test.xlsx"
        _make_xlsx(f, {"Sheet": [["A", "B"], [1, 2]]})
        panel = PreviewPanel()
        panel.show_preview(str(f))

        assert panel.preview_stack.currentWidget() is panel.excel_preview

    def test_shows_excel_widget_for_corrupt_xlsx(self, tmp_path):
        """Auch bei korrupter .xlsx landet man im excel_preview (Fallback-Anzeige)."""
        from gui.preview.preview_panel import PreviewPanel

        f = tmp_path / "corrupt.xlsx"
        f.write_bytes(b"no excel")
        panel = PreviewPanel()
        panel.show_preview(str(f))

        assert panel.preview_stack.currentWidget() is panel.excel_preview

    def test_metadata_shown_for_xlsx(self, tmp_path):
        from gui.preview.preview_panel import PreviewPanel

        f = tmp_path / "meta.xlsx"
        _make_xlsx(f, {"Sheet": [["A"]]})
        panel = PreviewPanel()
        panel.show_preview(str(f))

        assert panel.metadata_panel.name_label.text() == "meta.xlsx"
