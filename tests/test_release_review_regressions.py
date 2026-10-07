"""Properties must not read data on opening; translations preserve user data."""
from unittest.mock import Mock
from PySide6.QtWidgets import QComboBox, QApplication
from core.ui_translator import UiTranslator
from translator import get_translator
from gui import properties_dialog
from modules.privacy.term_io import read_terms, write_terms

def test_properties_do_not_read_cloud_contents(tmp_path, monkeypatch):
    path = tmp_path / "nur online.txt"
    path.write_text("Fixture", encoding="utf-8")
    monkeypatch.setattr(properties_dialog, "is_cloud_placeholder", lambda p: True)
    checksum = Mock(side_effect=AssertionError("must not read cloud contents"))
    monkeypatch.setattr(properties_dialog, "ChecksumDialog", checksum)
    dialog = properties_dialog.FilePropertiesDialog(str(path))
    assert not dialog.calc_btn.isEnabled()
    assert not dialog.text_stats_btn.isEnabled()
    dialog._compute_large_hashes()
    checksum.assert_not_called()
    dialog.close()

def test_properties_folder_query_is_explicit_and_async(tmp_path, monkeypatch, qtbot):
    path = tmp_path / "folder"
    path.mkdir()
    (path / "file.txt").write_bytes(b"abc")
    dialog = properties_dialog.FilePropertiesDialog(str(path))
    qtbot.addWidget(dialog)
    assert dialog.folder_size_label.text() == "—"
    dialog.folder_stats_btn.click()
    assert dialog._details_process is not None
    qtbot.waitUntil(lambda: dialog._details_process is None, timeout=15_000)
    assert "3 Bytes" in dialog.folder_size_label.text()
    assert "1" in dialog.folder_count_label.text()
    dialog.close()

def test_properties_close_stops_owned_query(tmp_path, qtbot):
    dialog = properties_dialog.FilePropertiesDialog(str(tmp_path))
    dialog.folder_stats_btn.click()
    process = dialog._details_process
    dialog.close()
    assert dialog._details_process is None
    assert process.state() == process.ProcessState.NotRunning

def test_editable_categories_survive_translation():
    translator = get_translator("en")
    bridge = UiTranslator(QApplication.instance())
    combo = QComboBox()
    combo.setEditable(True)
    combo.addItems(["Allgemein", "Datei", "Meine Kategorie"])
    combo.setCurrentText("Allgemein")
    try:
        bridge.translate_widget(combo)
        assert combo.currentText() == "Allgemein"
        assert [combo.itemText(i) for i in range(combo.count())] == ["Allgemein", "Datei", "Meine Kategorie"]
        translator.set_language("de")
        assert combo.currentText() == "Allgemein"
    finally:
        bridge.shutdown()
        combo.deleteLater()

def test_xlsx_terms_are_literal_not_formulas(tmp_path):
    import openpyxl
    target = tmp_path / "terms.xlsx"
    terms = ["=ProjectX", "=1+2", "+Äpfel", "Grüße"]
    write_terms(target, terms)
    assert set(read_terms(target)) == set(terms)
    book = openpyxl.load_workbook(target)
    try:
        assert all(cell.data_type == "s" for row in book.active for cell in row)
    finally:
        book.close()

def test_skipped_cloud_subtree_reports_partial_statistics(tmp_path, monkeypatch):
    from core import properties_details
    cloud = tmp_path / "online"
    cloud.mkdir()
    (cloud / "unavailable.txt").write_bytes(b"hidden fixture content")
    monkeypatch.setattr(properties_details, "is_cloud_placeholder", lambda p: str(p) == str(cloud))
    result = properties_details.query_details("folder", str(tmp_path))
    assert result["partial"] is True
    assert result["files"] == 0
