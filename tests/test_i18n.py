#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_i18n.py - Vertragstests für die Tier-2 6-Sprachen-Lokalisierung (P-006)
"""

import json
from pathlib import Path

import pytest

import manage_translations
from core.settings_manager import SettingsManager
from translator import (
    DEFAULT_LANGUAGE,
    LANGUAGE_DISPLAY_NAMES,
    LANGUAGE_NAMES,
    SUPPORTED_LANGUAGES,
    TranslationSystem,
    detect_system_language,
    get_translator,
    t,
)


def _custom_translator(tmp_path: Path, translations: dict) -> TranslationSystem:
    locales = tmp_path / "locales"
    locales.mkdir(exist_ok=True)
    (locales / "translations.json").write_text(
        json.dumps(translations, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return TranslationSystem(app_dir=tmp_path)


def test_supported_languages_are_complete_and_ordered():
    """Prüft, dass alle 6 P-006 Tier-2 Sprachen vollständig und geordnet definiert sind."""
    assert TranslationSystem.get_supported_languages() == ["de", "en", "es", "zh", "ja", "ru"]
    assert len(TranslationSystem.get_supported_languages()) == 6


def test_language_names_and_display_mappings():
    """Prüft native Namen und GUI-Display-Namen für alle Sprachen."""
    names = TranslationSystem.get_language_names()
    display = TranslationSystem.get_language_display_names()
    for lang in TranslationSystem.get_supported_languages():
        assert lang in names
        assert lang in display
        assert f"({lang})" in display[lang]


def test_invalid_default_language_falls_back_to_german(tmp_path):
    """Ungültige Spracheinstellungen müssen deterministisch auf Deutsch fallen."""
    assert TranslationSystem("fr", app_dir=tmp_path).get_language() == "de"
    assert TranslationSystem("invalid_code", app_dir=tmp_path).get_language() == "de"


def test_fallback_chain_target_en_de_key(tmp_path):
    """Prüft 4-stufige Fallback-Kette: Zielsprache -> en -> de -> key."""
    translations = {
        "Speichern": {"de": "Speichern", "en": "Save", "es": "Guardar", "zh": "", "ja": "", "ru": ""},
        "Nur_DE_EN": {"de": "Schließen", "en": "Close", "es": "", "zh": "", "ja": "", "ru": ""},
        "Nur_DE": {"de": "Spezialfall", "en": "", "es": "", "zh": "", "ja": "", "ru": ""},
    }
    ts = _custom_translator(tmp_path, translations)

    # 1. Zielsprache vorhanden
    ts.set_language("es")
    assert ts.t("Speichern") == "Guardar"

    # 2. Zielsprache fehlt -> Fallback auf Englisch
    ts.set_language("zh")
    assert ts.t("Nur_DE_EN") == "Close"

    # 3. Zielsprache und Englisch fehlen -> Fallback auf Deutsch
    ts.set_language("ja")
    assert ts.t("Nur_DE") == "Spezialfall"

    # 4. Völlig unübersetzter Key -> Key selbst
    ts.set_language("ru")
    assert ts.t("Nonexistent_Key") == "Nonexistent_Key"


def test_new_translation_entry_schema():
    """Prüft, dass neu erzeugte Einträge alle 6 Zielsprachen umfassen."""
    entry = TranslationSystem._new_translation_entry("Neu", "New", es="Nuevo")
    assert set(entry.keys()) == set(TranslationSystem.get_supported_languages())
    assert entry["de"] == "Neu"
    assert entry["en"] == "New"
    assert entry["es"] == "Nuevo"
    assert entry["zh"] == ""


def test_system_language_detection():
    """Prüft, dass die Systemsprachenerkennung einen gültigen Tier-2 Code liefert."""
    detected = detect_system_language()
    assert detected in TranslationSystem.get_supported_languages()


def test_singleton_get_translator():
    """Prüft die globale Singleton-Funktion get_translator und Kurzform t()."""
    tr1 = get_translator()
    tr2 = get_translator()
    assert tr1 is tr2
    assert isinstance(t("Abbrechen"), str)


def test_manage_translations_scanner(tmp_path):
    """Prüft die Scanner-Funktion von manage_translations."""
    py_sample = tmp_path / "sample.py"
    py_sample.write_text('button.setText("Löschen")\nlabel.setToolTip("Bereit")', encoding="utf-8")

    code = manage_translations.manage_translations(str(tmp_path), check_mode=False)
    assert code == 0

    trans_file = tmp_path / "locales" / "translations.json"
    assert trans_file.exists()
    data = json.loads(trans_file.read_text(encoding="utf-8"))
    assert "Löschen" in data
    assert set(data["Löschen"].keys()) == set(TranslationSystem.get_supported_languages())


def test_repository_translation_catalog_parity():
    """Prüft, dass alle Einträge im Produktivkatalog alle 6 Sprachen vollständig besitzen."""
    ts = TranslationSystem()
    assert ts.translations_file.exists()
    data = ts.translations
    assert len(data) >= 80, f"Erwartet mindestens 80 Strings, erhalten: {len(data)}"

    supported = TranslationSystem.get_supported_languages()
    for key, entry in data.items():
        assert isinstance(entry, dict), f"Eintrag für {key} ist kein Dictionary"
        for lang in supported:
            val = entry.get(lang)
            assert isinstance(val, str) and val.strip(), (
                f"Key '{key}' fehlt Übersetzung für Sprache '{lang}'"
            )


def test_settings_manager_language_integration():
    """Prüft, dass SettingsManager die Spracheinstellung speichert und lädt."""
    sm = SettingsManager.instance()
    assert "language" in sm.DEFAULTS["general"]
    assert sm.get("general", "language") in TranslationSystem.get_supported_languages()


def test_settings_dialog_language_dropdown():
    """Prüft, dass SettingsDialog die Sprachauswahl mit allen 6 Sprachen anbietet."""
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from gui.settings_dialog import SettingsDialog
    dlg = SettingsDialog()
    assert hasattr(dlg, "language_cb")
    assert dlg.language_cb.count() == 6
    codes = [dlg.language_cb.itemData(i) for i in range(dlg.language_cb.count())]
    assert codes == ["de", "en", "es", "zh", "ja", "ru"]
