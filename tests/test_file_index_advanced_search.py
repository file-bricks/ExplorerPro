"""
Regressionstests: FileIndex.advanced_search()
Prüft:
1. Regex-Suche (use_regex=True) mit korrekter Filterung
2. Case-Sensitivity (case_sensitive=True/False) sowohl für Regex als auch Substring-Suche
3. Fehlerbehandlung bei ungültigen Regex-Mustern (ValueError)
4. Datumsbereich-Grenzwerte (date_to schließt den gesamten Tag ein, inklusive Nachmittags-/Abend-Timestamps)
"""
from __future__ import annotations

import os
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from core.file_index import FileIndex


class TestFileIndexAdvancedSearch:
    """Tests für die erweiterte Suche im Datei-Index."""

    def _make_index(self) -> tuple[FileIndex, str]:
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        idx = FileIndex(tmp.name)
        return idx, tmp.name

    def _insert_file(
        self,
        idx: FileIndex,
        path: str,
        filename: str,
        content: str = "",
        modified: str | None = None,
        size: int = 100,
        category: str = "Dokumente",
    ):
        import sqlite3
        conn = sqlite3.connect(idx.db_path)
        try:
            cursor = conn.cursor()
            mod_str = modified or datetime.now().isoformat()
            cursor.execute(
                """
                INSERT OR REPLACE INTO files
                (path, filename, extension, size, modified, created,
                 hash, category, text_content, indexed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    path,
                    filename,
                    Path(filename).suffix.lower(),
                    size,
                    mod_str,
                    mod_str,
                    None,
                    category,
                    content,
                    mod_str,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def test_regex_search_matches_pattern(self):
        """Regex-Suche muss reguläre Ausdrücke korrekt auswerten."""
        idx, db = self._make_index()
        try:
            self._insert_file(idx, "/docs/report_2026.txt", "report_2026.txt", "Inhalt A")
            self._insert_file(idx, "/docs/report_abc.txt", "report_abc.txt", "Inhalt B")
            self._insert_file(idx, "/docs/notes.txt", "notes.txt", "Rechnungsnummer: INV-9942")

            # Regex auf Dateiname: nur Ziffern nach Unterstrich
            results = idx.advanced_search(query=r"^report_\d+\.txt$", use_regex=True, search_name=True, search_content=False)
            paths = [r["path"] for r in results]
            assert "/docs/report_2026.txt" in paths
            assert "/docs/report_abc.txt" not in paths

            # Regex auf Inhalt
            results_content = idx.advanced_search(query=r"INV-\d{4}", use_regex=True, search_name=False, search_content=True)
            paths_content = [r["path"] for r in results_content]
            assert "/docs/notes.txt" in paths_content
        finally:
            os.unlink(db)

    def test_regex_case_sensitivity(self):
        """Regex-Suche muss case_sensitive respektieren."""
        idx, db = self._make_index()
        try:
            self._insert_file(idx, "/docs/report.txt", "report.txt")
            self._insert_file(idx, "/docs/REPORT.LOG", "REPORT.LOG")

            # case_sensitive=False (Standard für Regex)
            res_ci = idx.advanced_search(query=r"^REPORT", use_regex=True, case_sensitive=False)
            assert len(res_ci) == 2

            # case_sensitive=True
            res_cs = idx.advanced_search(query=r"^REPORT", use_regex=True, case_sensitive=True)
            assert len(res_cs) == 1
            assert res_cs[0]["path"] == "/docs/REPORT.LOG"
        finally:
            os.unlink(db)

    def test_invalid_regex_raises_value_error(self):
        """Ungültige reguläre Ausdrücke müssen einen informativen ValueError werfen."""
        idx, db = self._make_index()
        try:
            with pytest.raises(ValueError, match="Ungültiger regulärer Ausdruck"):
                idx.advanced_search(query=r"[unclosed-bracket", use_regex=True)
        finally:
            os.unlink(db)

    def test_case_sensitive_non_regex_search(self):
        """Nicht-Regex-Suche mit case_sensitive=True unterscheidet Groß-/Kleinschreibung exakt."""
        idx, db = self._make_index()
        try:
            self._insert_file(idx, "/files/Data.csv", "Data.csv", "Wichtige Daten")
            self._insert_file(idx, "/files/data.csv", "data.csv", "andere daten")

            # Case-insensitiv: beide finden
            res_ci = idx.advanced_search(query="Data", case_sensitive=False)
            assert len(res_ci) == 2

            # Case-sensitiv: nur Data.csv finden
            res_cs = idx.advanced_search(query="Data", case_sensitive=True)
            assert len(res_cs) == 1
            assert res_cs[0]["filename"] == "Data.csv"
        finally:
            os.unlink(db)

    def test_date_to_includes_full_day(self):
        """date_to muss Dateien einschließen, die im Laufe des Tages (z.B. Nachmittags) modifiziert wurden."""
        idx, db = self._make_index()
        try:
            # Datei modifiziert am 2026-09-08 um 15:30 Uhr
            self._insert_file(idx, "/files/today.txt", "today.txt", modified="2026-09-08T15:30:00")
            # Datei modifiziert am 2026-09-09 um 09:00 Uhr
            self._insert_file(idx, "/files/tomorrow.txt", "tomorrow.txt", modified="2026-09-09T09:00:00")
            # Datei modifiziert am 2026-09-07 um 12:00 Uhr
            self._insert_file(idx, "/files/yesterday.txt", "yesterday.txt", modified="2026-09-07T12:00:00")

            # date_to als date-Objekt für den 2026-09-08
            target_date = date(2026, 9, 8)
            res = idx.advanced_search(date_to=target_date)
            paths = [r["path"] for r in res]

            # today.txt (15:30 Uhr) MUSS enthalten sein
            assert "/files/today.txt" in paths, "today.txt muss trotz Uhrzeit 15:30 im Tagesfilter date_to liegen"
            assert "/files/yesterday.txt" in paths
            assert "/files/tomorrow.txt" not in paths

            # Genau derselbe Tag: date_from=target_date und date_to=target_date
            res_single_day = idx.advanced_search(date_from=target_date, date_to=target_date)
            single_paths = [r["path"] for r in res_single_day]
            assert single_paths == ["/files/today.txt"]

            # date_to als String '2026-09-08'
            res_str = idx.advanced_search(date_to="2026-09-08")
            paths_str = [r["path"] for r in res_str]
            assert "/files/today.txt" in paths_str
        finally:
            os.unlink(db)
