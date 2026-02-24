#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Editor Module - Code-Editor Komponenten
"""

from .quick_editor import QuickEditorDialog, CodeEditor
from .syntax_highlighter import (
    BaseHighlighter,
    PythonHighlighter,
    JavaScriptHighlighter,
    HTMLHighlighter,
    CSSHighlighter,
    JSONHighlighter,
    SQLHighlighter,
    get_lexer_for_extension,
    HIGHLIGHTERS
)

__all__ = [
    'QuickEditorDialog',
    'CodeEditor',
    'BaseHighlighter',
    'PythonHighlighter',
    'JavaScriptHighlighter',
    'HTMLHighlighter',
    'CSSHighlighter',
    'JSONHighlighter',
    'SQLHighlighter',
    'get_lexer_for_extension',
    'HIGHLIGHTERS'
]
