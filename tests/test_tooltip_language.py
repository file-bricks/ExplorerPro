"""Language selection survives a restart and changes real Qt help text."""

import json
from pathlib import Path

import pytest
import shiboken6
from PySide6.QtWidgets import QApplication

import manage_translations
import translator
from core.settings_manager import SettingsManager
from gui.settings_dialog import SettingsDialog
from src.main import configure_application_language


@pytest.fixture
def isolated_settings(monkeypatch, tmp_path):
    # Use real JSON persistence without touching the user's settings or singleton.
    monkeypatch.setattr(SettingsManager, "_instance", None)
    monkeypatch.setattr(SettingsManager, "_get_config_path", lambda self: tmp_path / "settings.json")
    monkeypatch.setattr(translator, "_default_translator", translator.TranslationSystem())
    return SettingsManager.instance()


@pytest.mark.parametrize("language", translator.SUPPORTED_LANGUAGES)
def test_language_survives_dialog_save_and_restart(isolated_settings, monkeypatch, language):
    app = QApplication.instance() or QApplication([])
    settings = isolated_settings
    dialog = SettingsDialog(settings=settings)
    try:
        dialog.language_cb.setCurrentIndex(dialog.language_cb.findData(language))
        dialog.apply_to_settings()
        saved = json.loads(settings._config_path.read_text(encoding="utf-8"))
        assert saved["general"]["language"] == language
    finally:
        shiboken6.delete(dialog)

    # Recreate the manager and restore the translator as at application startup.
    monkeypatch.setattr(SettingsManager, "_instance", None)
    restored = SettingsManager.instance()
    tr = configure_application_language()
    assert tr.get_language() == language
    reopened = SettingsDialog(settings=restored)
    try:
        assert reopened.language_cb.currentData() == language
        assert reopened.start_folder_edit.toolTip() == tr.translations["Standardverzeichnis beim Programmstart"][language]
        assert reopened.language_cb.toolTip().splitlines()[1] == tr.translations["Sprachänderungen werden sofort übernommen; einzelne Texte erst nach einem Neustart."][language]
        assert app is QApplication.instance()
    finally:
        shiboken6.delete(reopened)


@pytest.mark.parametrize("invalid", ["fr", None, ["en"], {"language": "en"}])
def test_invalid_saved_language_falls_back_to_german(isolated_settings, invalid):
    app = QApplication.instance() or QApplication([])
    isolated_settings.set("general", "language", invalid)
    assert configure_application_language().get_language() == "de"
    dialog = SettingsDialog(settings=isolated_settings)
    try:
        assert dialog.language_cb.currentData() == "de"
        assert dialog.start_folder_edit.toolTip() == "Standardverzeichnis beim Programmstart"
        assert app is QApplication.instance()
    finally:
        shiboken6.delete(dialog)


def test_auditor_checks_translated_calls_without_modifying_catalog(tmp_path):
    (tmp_path / "sample.py").write_text(
        'from translator import t\nbutton.setToolTip(t("Neue Hilfe"))\n'
        'button.setText(t("Status"))\n'
        '# t("Nicht vorhandene Hilfe")\n', encoding="utf-8"
    )
    locales = tmp_path / "locales"
    locales.mkdir()
    catalog = locales / "translations.json"
    catalog.write_text("{}\n", encoding="utf-8")
    assert manage_translations.find_german_strings(str(tmp_path)) == {"Neue Hilfe", "Status"}
    assert manage_translations.manage_translations(str(tmp_path), check_mode=True) == 1
    assert catalog.read_text(encoding="utf-8") == "{}\n"


def test_repository_auditor_has_no_untranslated_help_text():
    root = Path(__file__).resolve().parents[1]
    assert manage_translations.manage_translations(str(root), check_mode=True) == 0
