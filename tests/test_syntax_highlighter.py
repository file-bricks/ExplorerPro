"""
Tests für TOMLHighlighter und JSON/TOML-Validierungsfunktionen.
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
    HIGHLIGHTERS,
    get_lexer_for_extension,
)
from modules.editor.quick_editor import _validate_json, _validate_toml


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
