"""
TranslationSystem - Multi-Language Support für Anwendungen
============================================================
Version: 2.1.0 (Tier-2 6-Sprachen-Ausbau P-006)
Quelle: _LANG/translator.py v2.0 & ExplorerPro
Referenz: _LANG/LANGUAGE_CODES.md

Verwendung:
-----------
from translator import TranslationSystem, get_translator, t

translator = get_translator()
label.setText(t('Datei öffnen'))
translator.set_language('en')
"""

import json
import locale
import re
from pathlib import Path
from typing import Dict, List, Optional, Set

SUPPORTED_LANGUAGES = ("de", "en", "es", "zh", "ja", "ru")
DEFAULT_LANGUAGE = "de"
FALLBACK_CHAIN = ("en", "de")

LANGUAGE_NAMES: Dict[str, str] = {
    "de": "Deutsch",
    "en": "English",
    "es": "Español",
    "zh": "简体中文",
    "ja": "日本語",
    "ru": "Русский",
}

LANGUAGE_DISPLAY_NAMES: Dict[str, str] = {
    "de": "Deutsch (de)",
    "en": "English (en)",
    "es": "Español (es)",
    "zh": "简体中文 (zh)",
    "ja": "日本語 (ja)",
    "ru": "Русский (ru)",
}


# "📂 Öffnen", "⚠️ Hinweis", "• Eintrag": Symbolpräfix ohne Buchstaben/Ziffern.
_PREFIX_RE = re.compile(r"^([^\w(\[\"'„“]+\s+)(\S.*)$", re.S)
# "Name:", "Neue Datei...", "Zurück (Alt+Left)", "Suche …".
_SUFFIX_RE = re.compile(r"^(.*?)(\s*(?:\.\.\.|…|:|\([^()]*\))\s*)$", re.S)


def detect_system_language() -> str:
    """Ermittelt die Systemsprache, Fallback auf 'de'."""
    try:
        loc = locale.getlocale()[0]
        if loc:
            code = loc.split("_")[0].lower()
            if code in SUPPORTED_LANGUAGES:
                return code
    except Exception:
        pass
    return DEFAULT_LANGUAGE



class TranslationSystem:
    """Multi-Language Support System v2.1 mit deterministischer Fallback-Kette."""

    SUPPORTED_LANGUAGES = SUPPORTED_LANGUAGES
    FALLBACK_LANGUAGES = FALLBACK_CHAIN
    LANGUAGE_NAMES = LANGUAGE_NAMES
    LANGUAGE_DISPLAY_NAMES = LANGUAGE_DISPLAY_NAMES

    def __init__(self, default_lang: str = DEFAULT_LANGUAGE, app_dir: Optional[Path] = None):
        """
        Initialisiert Translation-System.

        Args:
            default_lang: Standard-Sprache ('de', 'en', 'es', 'zh', 'ja', 'ru')
            app_dir: Verzeichnis der Anwendung (default: Verzeichnis dieser Datei)
        """
        self.current_lang = default_lang if default_lang in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE

        if app_dir is None:
            self.app_dir = Path(__file__).resolve().parent
        else:
            self.app_dir = Path(app_dir)

        self.translations_file = self.app_dir / "locales" / "translations.json"

        self.string_patterns = [
            re.compile(r'setText\s*\(\s*["\']([^"\']+)["\']\s*\)'),
            re.compile(r'setWindowTitle\s*\(\s*["\']([^"\']+)["\']\s*\)'),
            re.compile(r'setToolTip\s*\(\s*["\']([^"\']+)["\']\s*\)'),
            re.compile(r'setPlaceholderText\s*\(\s*["\']([^"\']+)["\']\s*\)'),
            re.compile(r'QLabel\s*\(\s*["\']([^"\']+)["\']\s*\)'),
            re.compile(r'QPushButton\s*\(\s*["\']([^"\']+)["\']\s*\)'),
            re.compile(r'QCheckBox\s*\(\s*["\']([^"\']+)["\']\s*\)'),
            re.compile(r'addAction\s*\([^,]*["\']([^"\']+)["\']\s*\)'),
            re.compile(r'addTab\s*\([^,]+,\s*["\']([^"\']+)["\']\s*\)'),
            re.compile(r'text\s*=\s*"([^"]+)"'),
        ]

        self.german_hints = [
            "datei", "bearbeiten", "ansicht", "hilfe", "oeffnen", "speichern",
            "schliessen", "einstellungen", "abbrechen", "ok", "ja", "nein",
            "start", "stop", "pause", "fortsetzen", "laden", "aktualisieren",
            "filter", "fehler", "export", "import", "optionen", "anzeigen",
            "löschen", "duplikate", "vorschau", "suche", "ordner", "bereit",
        ]

        self.translations: Dict[str, Dict[str, str]] = {}
        self.missing_keys: Set[str] = set()
        self._reverse_index: Optional[Dict[str, Dict[str, str]]] = None
        self._listeners: list = []
        self._load_translations()

    def _load_translations(self):
        if self.translations_file.exists():
            try:
                with open(self.translations_file, "r", encoding="utf-8") as f:
                    self.translations = json.load(f)
                if not isinstance(self.translations, dict):
                    self.translations = {}
            except Exception:
                self.translations = {}
        else:
            self.translations = {}

    def _save_translations(self):
        self._reverse_index = None
        self.translations_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.translations_file, "w", encoding="utf-8") as f:
            json.dump(self.translations, f, indent=2, ensure_ascii=False)

    def t(self, key: str) -> str:
        """
        Übersetzt einen Key in die aktuelle Sprache.
        Fallback-Kette: aktuelle Sprache -> en -> de -> Key selbst.
        """
        if not key:
            return ""

        entry = self.translations.get(key)
        if isinstance(entry, dict):
            value = entry.get(self.current_lang)
            if isinstance(value, str) and value.strip():
                return value
            for fb in FALLBACK_CHAIN:
                value = entry.get(fb)
                if isinstance(value, str) and value.strip():
                    return value
            return key

        # Dekorierte Varianten ("🟢 Grün", "Name:", "Neue Datei...") über
        # den Kern-Schlüssel auflösen.
        decorated = self._translate_parts(key, 0, self.current_lang)
        if decorated is not None:
            return decorated

        # Fehlende Schlüssel nur im Speicher vormerken: Zur Laufzeit darf der
        # Katalog nicht geschrieben werden (im Store-/EXE-Paket schreibgeschützt,
        # ein PermissionError würde sonst die aufrufende GUI-Aktion abbrechen).
        # Neue Strings pflegt `python manage_translations.py`.
        if self._is_german(key):
            self.missing_keys.add(key)

        return key

    # ===== Übersetzung zusammengesetzter GUI-Texte =====

    def has_key(self, key: str) -> bool:
        """True, wenn *key* als Eintrag im Katalog existiert."""
        return isinstance(self.translations.get(key), dict)

    def _lookup(self, key: str) -> Optional[str]:
        """Übersetzt *key* ohne Seiteneffekte; None, wenn kein Katalogeintrag existiert."""
        entry = self.translations.get(key)
        if not isinstance(entry, dict):
            return None
        for lang in (self.current_lang, *FALLBACK_CHAIN):
            value = entry.get(lang)
            if isinstance(value, str) and value.strip():
                return value
        return key

    def _source_for(self, text: str, source_lang: Optional[str] = None) -> Optional[str]:
        """Findet den deutschen Schlüssel zu *text*.

        Akzeptiert den Schlüssel selbst oder seine Übersetzung in der *aktiven*
        Sprache (z. B. bereits per ``t()`` übersetzte Tooltips). Werte anderer
        Sprachen werden bewusst nicht zurückgeführt, damit Nutzerdaten wie
        Ordnernamen in der aktiven Sprache unverändert bleiben.
        """
        if self.has_key(text):
            return text
        lang = source_lang or self.current_lang
        if self._reverse_index is None:
            self._reverse_index = {}
        reverse = self._reverse_index.get(lang)
        if reverse is None:
            reverse = {}
            for key, entry in self.translations.items():
                if not isinstance(entry, dict):
                    continue
                value = entry.get(lang)
                if isinstance(value, str) and value.strip():
                    reverse.setdefault(value, key)
            self._reverse_index[lang] = reverse
        return reverse.get(text)

    def source_text(self, text: str) -> Optional[str]:
        """Öffentliche Variante von :meth:`_source_for` für den UI-Übersetzer."""
        return self._source_for(text) if text else None

    def translate_text(self, text: str) -> str:
        """Übersetzt einen GUI-Text tolerant gegenüber Präfixen und Suffixen.

        Neben exakten Katalogtreffern werden typische Dekorationen erkannt und
        beibehalten: Emoji-/Symbolpräfixe ("📂 Öffnen"), Doppelpunkte
        ("Name:"), Auslassungspunkte ("Neue Datei..."), Tastenkürzel in
        Klammern ("Zurück (Alt+Left)"), Mnemonics ("&Datei") und mehrzeilige
        Texte. Ohne Treffer wird *text* unverändert zurückgegeben.
        """
        return self.translate_text_from(text, self.current_lang)

    def translate_text_from(self, text: str, source_lang: str) -> str:
        """Wie :meth:`translate_text`, wobei *text* in *source_lang* vorliegen darf."""
        result = self._translate_parts(text, 0, source_lang)
        return text if result is None else result

    def _translate_parts(self, text: str, depth: int, source_lang: str) -> Optional[str]:
        if not text or not text.strip() or depth > 4:
            return None

        source = self._source_for(text, source_lang)
        if source is not None:
            return self._lookup(source)

        if "\n" in text:
            lines = text.split("\n")
            translated = [self._translate_parts(line, depth + 1, source_lang) for line in lines]
            if any(item is not None for item in translated):
                return "\n".join(
                    item if item is not None else line for line, item in zip(lines, translated)
                )
            return None

        stripped = text.strip()
        if stripped != text:
            inner = self._translate_parts(stripped, depth + 1, source_lang)
            if inner is None:
                return None
            start = text.index(stripped)
            return text[:start] + inner + text[start + len(stripped):]

        if "&" in text and "&&" not in text:
            plain = text.replace("&", "", 1)
            inner = self._translate_parts(plain, depth + 1, source_lang)
            if inner is not None:
                return "&" + inner if not inner.startswith("&") else inner

        match = _PREFIX_RE.match(text)
        if match:
            inner = self._translate_parts(match.group(2), depth + 1, source_lang)
            if inner is not None:
                return match.group(1) + inner

        match = _SUFFIX_RE.match(text)
        if match and match.group(1).strip():
            inner = self._translate_parts(match.group(1), depth + 1, source_lang)
            if inner is not None:
                return inner + match.group(2)

        return None

    def add_language_listener(self, callback) -> None:
        """Registriert einen Callback, der nach jedem Sprachwechsel aufgerufen wird."""
        if callback not in self._listeners:
            self._listeners.append(callback)

    def remove_language_listener(self, callback) -> None:
        if callback in self._listeners:
            self._listeners.remove(callback)

    def set_language(self, lang: str):
        """Setzt die aktive Zielsprache und benachrichtigt registrierte Listener."""
        if lang in SUPPORTED_LANGUAGES and lang != self.current_lang:
            self.current_lang = lang
            for callback in list(self._listeners):
                try:
                    callback(lang)
                except Exception:
                    # Ein defekter Listener darf den Sprachwechsel nicht blockieren.
                    pass

    def get_language(self) -> str:
        """Liefert die aktive Zielsprache zurück."""
        return self.current_lang

    @classmethod
    def get_supported_languages(cls) -> List[str]:
        """Liefert die Liste aller 6 unterstützten Sprachcodes."""
        return list(SUPPORTED_LANGUAGES)

    @classmethod
    def get_language_names(cls) -> Dict[str, str]:
        """Liefert Mapping von Sprachcode auf nativer Sprachname."""
        return dict(LANGUAGE_NAMES)

    @classmethod
    def get_language_display_names(cls) -> Dict[str, str]:
        """Liefert Mapping von Sprachcode auf UI-Display-Name."""
        return dict(LANGUAGE_DISPLAY_NAMES)

    @classmethod
    def _new_translation_entry(cls, de: str, en: str = "", **kwargs) -> Dict[str, str]:
        """Erzeugt einen neuen Eintrag mit vollständigem 6-Sprachen-Schema."""
        entry = {lang: "" for lang in SUPPORTED_LANGUAGES}
        entry["de"] = de
        entry["en"] = en
        for lang, val in kwargs.items():
            if lang in SUPPORTED_LANGUAGES:
                entry[lang] = val
        return entry

    def add_translation(self, key: str, **translations: str):
        """Fügt eine Übersetzung manuell hinzu oder aktualisiert sie."""
        if key not in self.translations:
            self.translations[key] = {lang: "" for lang in SUPPORTED_LANGUAGES}
        for lang, value in translations.items():
            if lang in SUPPORTED_LANGUAGES:
                self.translations[key][lang] = value
        self._save_translations()

    def scan_and_update(self, project_dir: Optional[Path] = None) -> Dict:
        """Scannt Projekt-Dateien nach deutschen Strings und aktualisiert translations.json."""
        if project_dir is None:
            project_dir = self.app_dir

        found_strings = self._find_german_strings(Path(project_dir))

        added = []
        for string in sorted(found_strings):
            if string not in self.translations:
                self.translations[string] = self._new_translation_entry(string, "")
                added.append(string)

        if added:
            self._save_translations()

        missing = {lang: [] for lang in SUPPORTED_LANGUAGES if lang != "de"}
        for k, v in self.translations.items():
            for lang in SUPPORTED_LANGUAGES:
                if lang != "de" and not v.get(lang):
                    missing[lang].append(k)

        return {"added": added, "missing": missing, "total": len(self.translations)}

    def _find_german_strings(self, directory: Path) -> Set[str]:
        german_strings = set()
        skip_dirs = {"build", "dist", "venv", ".venv", "__pycache__", "releases", ".git"}

        for py_file in directory.rglob("*.py"):
            if any(folder in py_file.parts for folder in skip_dirs):
                continue
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception:
                continue

            for pattern in self.string_patterns:
                for match in pattern.findall(content):
                    if match and self._is_german(match):
                        german_strings.add(match.strip())

        return german_strings

    def _is_german(self, text: str) -> bool:
        if any(ch in text for ch in "äöüÄÖÜß"):
            return True
        text_lower = text.lower()
        return any(hint in text_lower for hint in self.german_hints)

    def get_missing_translations(self, lang: Optional[str] = None) -> Dict[str, List[str]] | List[str]:
        """Gibt fehlende Übersetzungen zurück. Wenn lang gesetzt ist, nur für diese Sprache."""
        if lang:
            if lang not in SUPPORTED_LANGUAGES:
                raise ValueError(f"Unsupported language: {lang}")
            return [k for k, v in self.translations.items() if not v.get(lang)]

        missing = {}
        for lang_code in SUPPORTED_LANGUAGES:
            if lang_code == "de":
                continue
            m = [k for k, v in self.translations.items() if not v.get(lang_code)]
            if m:
                missing[lang_code] = m
        return missing


_default_translator: Optional[TranslationSystem] = None


def get_translator(default_lang: Optional[str] = None) -> TranslationSystem:
    """Gibt die anwendungsweite TranslationSystem-Instanz zurück (Singleton-Muster)."""
    global _default_translator
    if _default_translator is None:
        _default_translator = TranslationSystem(default_lang or DEFAULT_LANGUAGE)
    elif default_lang and default_lang in SUPPORTED_LANGUAGES:
        _default_translator.set_language(default_lang)
    return _default_translator


def t(key: str) -> str:
    """Übersetzt den angegebenen Schlüssel mit der Standard-Instanz."""
    return get_translator().t(key)


if __name__ == "__main__":
    tr = TranslationSystem()
    print(f"Sprache: {tr.get_language()}")
    print(f"Unterstützt: {', '.join(SUPPORTED_LANGUAGES)}")
    result = tr.scan_and_update()
    print(f"Scan: {result['total']} Strings, {len(result['added'])} neu")
    for lang_code, keys in result["missing"].items():
        print(f"  {lang_code}: {len(keys)} fehlend")
