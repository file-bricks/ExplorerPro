#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_file_index_expanded_text.py - Prüft die erweiterte Volltext-Extraktion für Code, Config und strukturierte Daten
"""

from pathlib import Path
from core.file_index import FileIndex


def test_extract_text_code_and_configs(tmp_path: Path):
    """Prüft, dass Python-, JSON-, SQL-, YAML-, CSV- und Logdateien textuell extrahiert werden."""
    db_file = tmp_path / "test_idx.db"
    idx = FileIndex(str(db_file))

    samples = {
        "script.py": "def hello_world():\n    print('ExplorerPro')",
        "config.json": '{"app": "ExplorerPro", "version": "2.0"}',
        "schema.sql": "CREATE TABLE test_table (id INTEGER PRIMARY KEY);",
        "settings.yaml": "server:\n  port: 8080\n  debug: false",
        "data.csv": "id,name,score\n1,Alice,100\n2,Bob,95",
        "audit.log": "2026-09-10 [INFO] ExplorerPro started successfully",
    }

    for fname, text in samples.items():
        fpath = tmp_path / fname
        fpath.write_text(text, encoding="utf-8")
        extracted = idx.extract_text(str(fpath))
        assert extracted is not None, f"Extraktion fehlgeschlagen für {fname}"
        assert text in extracted


def test_fts5_search_on_code_file(tmp_path: Path):
    """Prüft, dass FTS5-Suche in Quellcodedateien funktioniert."""
    db_file = tmp_path / "test_fts.db"
    idx = FileIndex(str(db_file))

    py_file = tmp_path / "algorithm.py"
    py_file.write_text("def unique_search_keyword_alpha_123():\n    pass", encoding="utf-8")

    idx.index_file(str(py_file), calculate_hash=True)

    results = idx.search("unique_search_keyword_alpha_123")
    assert len(results) == 1
    assert results[0]["filename"] == "algorithm.py"
