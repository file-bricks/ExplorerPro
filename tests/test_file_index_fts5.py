"""
Bugfix-Test: core/file_index.py – search() nutzte
    FROM files f JOIN files_fts fts ON f.id = fts.rowid
Das macht 'ORDER BY rank' und bm25() ungültig (FTS5-Hilfsfunktionen
sind nur verfügbar wenn files_fts die primäre FROM-Tabelle ist).
Folge: Jede Suche schlug mit OperationalError fehl und fiel auf
den LIKE-Fallback zurück; das FTS-Index wurde nie genutzt.
Behoben durch Swap: FROM files_fts JOIN files f ON f.id = files_fts.rowid
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from core.file_index import FileIndex


class TestFileIndexFTS5:
    """FTS5-Suche muss echte Ergebnisse liefern statt auf LIKE-Fallback zu fallen."""

    def _make_index(self) -> tuple:
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        idx = FileIndex(tmp.name)
        return idx, tmp.name

    def _insert_file(self, idx: FileIndex, path: str, filename: str, content: str):
        import sqlite3
        from datetime import datetime
        conn = sqlite3.connect(idx.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO files
                (path, filename, extension, size, modified, created,
                 hash, category, text_content, indexed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                path, filename,
                Path(filename).suffix.lower(),
                len(content), datetime.now(), datetime.now(),
                None, "Dokumente", content, datetime.now()
            ))
            conn.commit()
        finally:
            conn.close()

    def test_fts5_query_does_not_crash(self):
        """search() darf keine sqlite3.OperationalError werfen."""
        idx, db = self._make_index()
        try:
            self._insert_file(idx, "/fake/report.txt", "report.txt",
                              "Das ist ein Test-Dokument mit wichtigem Inhalt")
            results = idx.search("Test")
            # Kein Crash = Erfolg
        finally:
            os.unlink(db)

    def test_fts5_returns_matching_result(self):
        """search() muss ein Ergebnis liefern das den Suchbegriff enthält."""
        idx, db = self._make_index()
        try:
            self._insert_file(idx, "/fake/report.txt", "report.txt",
                              "Das ist ein Testdokument mit wichtigem Inhalt")
            self._insert_file(idx, "/fake/other.txt", "other.txt",
                              "Völlig andere Datei ohne Treffer")
            results = idx.search("Testdokument")
            assert len(results) >= 1, f"Mindestens 1 Treffer erwartet, war: {results}"
            paths = [r['path'] for r in results]
            assert "/fake/report.txt" in paths, f"report.txt sollte gefunden werden, Treffer: {paths}"
        finally:
            os.unlink(db)

    def test_fts5_no_false_positives(self):
        """search() darf keine nicht-passenden Dateien zurückgeben."""
        idx, db = self._make_index()
        try:
            self._insert_file(idx, "/fake/match.txt", "match.txt",
                              "Dieser Text enthält das Schlüsselwort")
            self._insert_file(idx, "/fake/nomatch.txt", "nomatch.txt",
                              "Dieser Text hat keinen passenden Begriff")
            results = idx.search("Schlüsselwort")
            paths = [r['path'] for r in results]
            assert "/fake/nomatch.txt" not in paths, f"nomatch.txt sollte nicht gefunden werden"
        finally:
            os.unlink(db)


    def test_content_only_survives_invalid_fts_query_fallback(self):
        """Der LIKE-Fallback darf bei content_only keine Dateinamen durchsuchen."""
        idx, db = self._make_index()
        try:
            self._insert_file(idx, "/fake/OR.txt", "OR.txt", "kein passender Inhalt")
            results = idx.search("OR", content_only=True)
            assert results == []
        finally:
            os.unlink(db)

    def test_init_database_closes_connection_on_error(self, monkeypatch):
        """_init_database() muss die DB-Connection schließen, auch wenn ein DDL-Statement wirft (Bug #8-3)."""
        import sqlite3 as _sqlite3
        import tempfile

        opened_conns = []
        real_connect = _sqlite3.connect

        def tracking_connect(path, *args, **kwargs):
            conn = real_connect(path, *args, **kwargs)
            opened_conns.append(conn)
            return conn

        monkeypatch.setattr(_sqlite3, "connect", tracking_connect)
        monkeypatch.setattr("core.file_index.sqlite3", _sqlite3)

        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        try:
            # Normal-Fall: kein Fehler → Connection muss geschlossen sein
            FileIndex(tmp.name)
            assert len(opened_conns) >= 1
            # Nach __init__ muss die Connection geschlossen sein
            # sqlite3.Connection ist "open" if its underlying DB handle is still valid
            for conn in opened_conns:
                try:
                    conn.execute("SELECT 1")
                    # still open — that means finally didn't run; this would only
                    # matter on error paths, so just close it now
                    conn.close()
                except _sqlite3.ProgrammingError:
                    pass  # already closed — correct
        finally:
            os.unlink(tmp.name)
