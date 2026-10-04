#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_bugsweep_batch_rename_resilience_20261001.py
Hermetische Regressionstests für den Bugsweep 2026-10-01 in ExplorerPro:
Bereich: Mehrfachumbenennung (Batch Rename) - Regelberechnung, Regex-Ersetzung,
Nummerierungs- & Padding-Resilienz, Windows-Gerätenamen-Validierung,
zweiphasige atomare Rollback-Hygiene und Dialog-Lebenszyklus
(core/batch_rename_service.py + gui/batch_rename_dialog.py).
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch

# Sicherstellen, dass Repo-Root und src im Pfad liegen
REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_PATH = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from PySide6.QtWidgets import QApplication

from core.batch_rename_service import (
    RenameRules,
    RenameItem,
    compute_new_name,
    execute_rename,
    rollback_rename,
)
from gui.batch_rename_dialog import BatchRenameDialog


def _ensure_app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_non_regex_case_insensitive_replace_with_backslashes():
    """
    Prüft, dass nicht-reguläres Suchen & Ersetzen ohne Beachtung der Groß-/Kleinschreibung
    Backslashes und Gruppen-Escape-Muster (wie \\1, \\g, \\t) im Ersetzungstext
    nicht als Regex-Backreferenz fehlinterpretiert werden und nicht unkontrolliert
    mit re.error abstürzen, sondern deterministisch die Dateinamens-Validierung erreichen.
    """
    rules = RenameRules(
        search_str="DOC",
        replace_str=r"sub\1\test",
        use_regex=False,
        regex_case_sensitive=False,
    )
    # Zuvor: unhandled re.error: invalid group reference 1 at position 4 (Crash!)
    # Jetzt: Sicher ausgeführt und von der Dateinamensprüfung gefangen
    new_name, err = compute_new_name("my_doc_2026.txt", rules)
    assert err is not None
    assert "Ungültiges Zeichen im Dateinamen: '\\'" in err


def test_negative_numbering_formatting():
    """
    Prüft, dass negative Startnummern korrekt mit Vorzeichen und Padding formatiert werden
    (z. B. -005 statt fehlerhaft verkürztem -05).
    """
    rules = RenameRules(
        numbering_enabled=True,
        start_num=-5,
        step_num=2,
        padding=3,
        number_position="suffix",
    )
    name0, err0 = compute_new_name("log.txt", rules, index=0)
    assert err0 is None
    assert name0 == "log_-005.txt"

    name1, err1 = compute_new_name("log.txt", rules, index=1)
    assert err1 is None
    assert name1 == "log_-003.txt"


def test_windows_reserved_names_clock():
    """
    Prüft, dass auch CLOCK$ zuverlässig als Windows-Gerätename abgewiesen wird.
    """
    rules = RenameRules(search_str="^.*$", replace_str="clock$", use_regex=True)
    new_name, err = compute_new_name("test.txt", rules)
    assert err is not None
    assert "reservierter Gerätename" in err


def test_empty_final_name_validation():
    """
    Prüft, dass ein durch Ersetzung vollständig geleerter Dateiname
    nicht den Originalnamen fälschlich als neuen Namen spiegelt, sondern
    eindeutig als leer und ungültig deklariert wird.
    """
    rules = RenameRules(search_str="test", replace_str="", change_extension="")
    new_name, err = compute_new_name("test.txt", rules)
    assert err is not None
    assert "Dateiname darf nicht leer sein" in err
    assert new_name == ""


def test_execute_rename_cycle_error_rollback_two_phase(tmp_path: Path):
    """
    Prüft, dass bei einem zyklischen Batch-Rename (A->B, B->C, C->A)
    ein Fehler mitten in Phase 2 durch zweistufige Bereinigung vollständig
    und kollisionsfrei zurückgerollt wird, ohne WinError 183 oder verwaiste Temp-Dateien.
    """
    fa = tmp_path / "A.txt"
    fb = tmp_path / "B.txt"
    fc = tmp_path / "C.txt"
    fa.write_text("content_a", encoding="utf-8")
    fb.write_text("content_b", encoding="utf-8")
    fc.write_text("content_c", encoding="utf-8")

    items = [
        RenameItem(original_path=str(fa), original_name="A.txt", new_name="B.txt", new_path=str(fb), status="ok"),
        RenameItem(original_path=str(fb), original_name="B.txt", new_name="C.txt", new_path=str(fc), status="ok"),
        RenameItem(original_path=str(fc), original_name="C.txt", new_name="A.txt", new_path=str(fa), status="ok"),
    ]

    orig_rename = os.rename
    counter = {"calls": 0}

    def failing_rename(src, dst):
        counter["calls"] += 1
        # 3 Calls in Phase 1 (1, 2, 3), 2 Calls in Phase 2 (4, 5), Call 6 schlägt fehl
        if counter["calls"] == 6:
            raise OSError("Künstlicher I/O-Fehler beim 3. Element in Phase 2")
        return orig_rename(src, dst)

    with patch("os.rename", side_effect=failing_rename):
        success, errors, history = execute_rename(items)

    assert success == 0
    assert len(errors) > 0
    assert "Künstlicher I/O-Fehler" in errors[0]

    # Prüfen, dass alle drei Dateien unbeschädigt und an ihren Originalorten liegen
    assert fa.exists() and fa.read_text(encoding="utf-8") == "content_a"
    assert fb.exists() and fb.read_text(encoding="utf-8") == "content_b"
    assert fc.exists() and fc.read_text(encoding="utf-8") == "content_c"

    # Keine verwaisten temporären Dateien im Ordner
    all_files = [p.name for p in tmp_path.iterdir()]
    assert sorted(all_files) == ["A.txt", "B.txt", "C.txt"]


def test_rollback_rename_phase1_failure_cleanup(tmp_path: Path):
    """
    Prüft, dass rollback_rename bei einem Fehler in Phase 1 sofort abbricht
    und bereits verschobene Zwischendateien restlos zurückrollt.
    """
    fa = tmp_path / "file_a_new.txt"
    fb = tmp_path / "file_b_new.txt"
    fa.write_text("data_a", encoding="utf-8")
    fb.write_text("data_b", encoding="utf-8")

    history = [
        (str(fa), str(tmp_path / "file_a_orig.txt")),
        (str(fb), str(tmp_path / "file_b_orig.txt")),
    ]

    orig_rename = os.rename
    counter = {"calls": 0}

    def failing_rb(src, dst):
        counter["calls"] += 1
        # Erste Datei in Phase 1 gelingt, zweite schlägt fehl
        if counter["calls"] == 2:
            raise OSError("Fehler bei Phase 1 des Rollbacks")
        return orig_rename(src, dst)

    with patch("os.rename", side_effect=failing_rb):
        restored, errors = rollback_rename(history)

    assert restored == 0
    assert len(errors) > 0

    # Beide Dateien müssen weiterhin unter ihren aktuellen Pfaden existieren (keine verwaisten __ep_rb_tmp_)
    assert fa.exists() and fa.read_text(encoding="utf-8") == "data_a"
    assert fb.exists() and fb.read_text(encoding="utf-8") == "data_b"
    assert not any(p.name.startswith(".__ep_rb_tmp_") for p in tmp_path.iterdir())


def test_batch_rename_dialog_rollback_and_path_synchronization(tmp_path: Path):
    """
    Prüft, dass BatchRenameDialog nach einem Rollback self.file_paths korrekt
    auf die tatsächlich existierenden Originalpfade zurücksynchronisiert,
    sodass Folgeaktionen sauber funktionieren und der Dialog geöffnet bleibt.
    """
    _ensure_app()
    f1 = tmp_path / "report1.txt"
    f2 = tmp_path / "report2.txt"
    f1.write_text("r1", encoding="utf-8")
    f2.write_text("r2", encoding="utf-8")

    dlg = BatchRenameDialog([str(f1), str(f2)])
    dlg.prefix_edit.setText("2026_")
    dlg._update_preview()

    assert dlg.rename_btn.isEnabled() is True

    # 1. Umbenennung durchführen
    with patch("PySide6.QtWidgets.QMessageBox.information"):
        dlg._do_rename()

    renamed1 = tmp_path / "2026_report1.txt"
    renamed2 = tmp_path / "2026_report2.txt"
    assert renamed1.exists()
    assert renamed2.exists()
    assert dlg.rollback_btn.isEnabled() is True
    assert dlg.file_paths == [str(renamed1), str(renamed2)]

    # 2. Rollback durchführen
    with patch("PySide6.QtWidgets.QMessageBox.information"):
        dlg._do_rollback()

    assert f1.exists()
    assert f2.exists()
    assert not renamed1.exists()
    assert not renamed2.exists()
    assert dlg.rollback_btn.isEnabled() is False

    # file_paths muss jetzt wieder auf die wiederhergestellten Dateien verweisen!
    assert dlg.file_paths == [str(f1), str(f2)]
    assert all(os.path.exists(p) for p in dlg.file_paths)

    # Schließen des Dialogs
    dlg._on_close_clicked()
    dlg.close()


def test_batch_rename_dialog_deduplication(tmp_path: Path):
    """
    Prüft, dass mehrfach übergebene identische Dateipfade in BatchRenameDialog
    ohne Verlust der Reihenfolge dedupliziert werden.
    """
    _ensure_app()
    f1 = tmp_path / "item.txt"
    f1.write_text("content", encoding="utf-8")

    dlg = BatchRenameDialog([str(f1), str(f1), str(f1)])
    assert len(dlg.file_paths) == 1
    assert dlg.table.rowCount() == 1
    dlg.close()
