"""
Tests für Syntax-Highlighter und JSON/TOML-Validierungsfunktionen.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PySide6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication([])

from modules.editor.syntax_highlighter import (
    TOMLHighlighter,
    YAMLHighlighter,
    ShellHighlighter,
    CHighlighter,
    IniHighlighter,
    MarkdownHighlighter,
    HIGHLIGHTERS,
    get_lexer_for_extension,
)
from modules.editor.quick_editor import _validate_json, _validate_toml


def _make_highlighter(cls):
    """Hilfsfunktion: Highlighter-Instanz mit frischem QTextDocument."""
    from PySide6.QtGui import QTextDocument
    return cls(QTextDocument())


class TestTOMLHighlighter:
    def test_toml_in_highlighters(self):
        assert ".toml" in HIGHLIGHTERS
        assert HIGHLIGHTERS[".toml"] is TOMLHighlighter

    def test_get_lexer_returns_toml(self):
        assert get_lexer_for_extension(".toml") is TOMLHighlighter

    def test_get_lexer_case_insensitive(self):
        assert get_lexer_for_extension(".TOML") is TOMLHighlighter

    def test_toml_highlighter_instantiates(self):
        from PySide6.QtGui import QTextDocument

        doc = QTextDocument()
        h = TOMLHighlighter(doc)
        assert h is not None

    def test_toml_highlighter_has_rules(self):
        from PySide6.QtGui import QTextDocument

        doc = QTextDocument()
        h = TOMLHighlighter(doc)
        assert len(h.rules) > 0


class TestValidateJSON:
    def test_valid_object_passes(self):
        ok, msg = _validate_json('{"key": 1}')
        assert ok is True
        assert "Gültiges JSON" in msg

    def test_empty_object_passes(self):
        ok, msg = _validate_json("{}")
        assert ok is True

    def test_valid_array_passes(self):
        ok, msg = _validate_json("[1, 2, 3]")
        assert ok is True

    def test_invalid_json_fails(self):
        ok, msg = _validate_json("{invalid}")
        assert ok is False
        assert "Ungültiges JSON" in msg

    def test_truncated_json_fails(self):
        ok, msg = _validate_json('{"key":')
        assert ok is False

    def test_empty_string_fails(self):
        ok, msg = _validate_json("")
        assert ok is False


class TestValidateTOML:
    def _toml_available(self) -> bool:
        try:
            import tomllib  # noqa: F401
            return True
        except ImportError:
            pass
        try:
            import tomli  # noqa: F401
            return True
        except ImportError:
            return False

    def test_valid_toml_passes(self):
        ok, msg = _validate_toml('[section]\nkey = "value"')
        if not self._toml_available():
            assert "erfordert Python" in msg
            return
        assert ok is True
        assert "Gültiges TOML" in msg

    def test_empty_toml_passes(self):
        ok, msg = _validate_toml("")
        if not self._toml_available():
            return
        assert ok is True

    def test_invalid_toml_fails(self):
        ok, msg = _validate_toml("[section\nkey = missing bracket")
        if not self._toml_available():
            return
        assert ok is False
        assert "Ungültiges TOML" in msg

    def test_fallback_message_when_unavailable(self):
        """Wenn tomllib/tomli nicht verfügbar, wird eine klare Fehlermeldung zurückgegeben."""
        if self._toml_available():
            return  # nichts zu testen — lib ist verfügbar
        ok, msg = _validate_toml("key = 1")
        assert ok is False
        assert "erfordert Python" in msg


# ===== Neue Highlighter (2026-06-27) =====


class TestYAMLHighlighter:
    def test_yaml_extensions_in_highlighters(self):
        assert ".yaml" in HIGHLIGHTERS
        assert ".yml" in HIGHLIGHTERS
        assert HIGHLIGHTERS[".yaml"] is YAMLHighlighter
        assert HIGHLIGHTERS[".yml"] is YAMLHighlighter

    def test_get_lexer_returns_yaml(self):
        assert get_lexer_for_extension(".yaml") is YAMLHighlighter
        assert get_lexer_for_extension(".yml") is YAMLHighlighter

    def test_get_lexer_case_insensitive(self):
        assert get_lexer_for_extension(".YAML") is YAMLHighlighter
        assert get_lexer_for_extension(".YML") is YAMLHighlighter

    def test_yaml_highlighter_instantiates(self):
        h = _make_highlighter(YAMLHighlighter)
        assert h is not None

    def test_yaml_highlighter_has_rules(self):
        h = _make_highlighter(YAMLHighlighter)
        assert len(h.rules) > 0


class TestShellHighlighter:
    def test_shell_extensions_in_highlighters(self):
        for ext in ('.sh', '.bash', '.zsh', '.fish'):
            assert ext in HIGHLIGHTERS
            assert HIGHLIGHTERS[ext] is ShellHighlighter

    def test_get_lexer_returns_shell(self):
        assert get_lexer_for_extension(".sh") is ShellHighlighter
        assert get_lexer_for_extension(".bash") is ShellHighlighter

    def test_get_lexer_case_insensitive(self):
        assert get_lexer_for_extension(".SH") is ShellHighlighter

    def test_shell_highlighter_instantiates(self):
        h = _make_highlighter(ShellHighlighter)
        assert h is not None

    def test_shell_highlighter_has_rules(self):
        h = _make_highlighter(ShellHighlighter)
        assert len(h.rules) > 0


class TestCHighlighter:
    def test_c_extensions_in_highlighters(self):
        for ext in ('.c', '.cpp', '.cc', '.cxx', '.h', '.hpp', '.hh'):
            assert ext in HIGHLIGHTERS
            assert HIGHLIGHTERS[ext] is CHighlighter

    def test_get_lexer_returns_c(self):
        assert get_lexer_for_extension(".c") is CHighlighter
        assert get_lexer_for_extension(".cpp") is CHighlighter
        assert get_lexer_for_extension(".h") is CHighlighter

    def test_get_lexer_case_insensitive(self):
        assert get_lexer_for_extension(".CPP") is CHighlighter

    def test_c_highlighter_instantiates(self):
        h = _make_highlighter(CHighlighter)
        assert h is not None

    def test_c_highlighter_has_rules(self):
        h = _make_highlighter(CHighlighter)
        assert len(h.rules) > 0


class TestIniHighlighter:
    def test_ini_extensions_in_highlighters(self):
        for ext in ('.ini', '.cfg', '.conf', '.env'):
            assert ext in HIGHLIGHTERS
            assert HIGHLIGHTERS[ext] is IniHighlighter

    def test_get_lexer_returns_ini(self):
        assert get_lexer_for_extension(".ini") is IniHighlighter
        assert get_lexer_for_extension(".env") is IniHighlighter

    def test_get_lexer_case_insensitive(self):
        assert get_lexer_for_extension(".INI") is IniHighlighter

    def test_ini_highlighter_instantiates(self):
        h = _make_highlighter(IniHighlighter)
        assert h is not None

    def test_ini_highlighter_has_rules(self):
        h = _make_highlighter(IniHighlighter)
        assert len(h.rules) > 0


class TestMarkdownHighlighter:
    def test_markdown_extensions_in_highlighters(self):
        assert ".md" in HIGHLIGHTERS
        assert ".markdown" in HIGHLIGHTERS
        assert HIGHLIGHTERS[".md"] is MarkdownHighlighter
        assert HIGHLIGHTERS[".markdown"] is MarkdownHighlighter

    def test_get_lexer_returns_markdown(self):
        assert get_lexer_for_extension(".md") is MarkdownHighlighter
        assert get_lexer_for_extension(".markdown") is MarkdownHighlighter

    def test_get_lexer_case_insensitive(self):
        assert get_lexer_for_extension(".MD") is MarkdownHighlighter

    def test_markdown_highlighter_instantiates(self):
        h = _make_highlighter(MarkdownHighlighter)
        assert h is not None

    def test_markdown_highlighter_has_rules(self):
        h = _make_highlighter(MarkdownHighlighter)
        assert len(h.rules) > 0
