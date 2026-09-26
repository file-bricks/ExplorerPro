#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_batch_renamer_regressions.py - Regressionstests für Batch-Renamer (Bugsweep 2026-09-21)

Prüft:
1. Case-only Renames (z. B. test.txt -> TEST.TXT) auf Windows werden nicht fälschlich als 'unchanged' markiert.
2. Kollisionserkennung: Umbenennung auf den Namen einer im Batch unverändert bleibenden Datei wird als Kollision erkannt.
3. Kettungs-Umbenennungen (file1 -> file2 -> file3) werden dank Zwei-Phasen-Ausführung kollisionsfrei ausgeführt.
4. Tausch-Umbenennungen (a -> b, b -> a) funktionieren ohne WinError 183.
5. Ungültige Dateinamen mit nachgestelltem Punkt oder Leerzeichen werden abgefangen.
"""

from pathlib import Path

from core.batch_rename_service import (
    RenameRules,
    compute_new_name,
    generate_preview,
    execute_rename,
    rollback_rename,
)


def test_case_only_rename_is_actionable_not_unchanged(tmp_path: Path):
    """Case-only Renames dürfen nicht als 'unchanged' markiert und ignoriert werden."""
    f1 = tmp_path / "sample.txt"
    f1.write_text("content", encoding="utf-8")

    rules = RenameRules(case_mode="upper")
    preview = generate_preview([str(f1)], rules)

    assert len(preview) == 1
    assert preview[0].new_name == "SAMPLE.txt"
    assert preview[0].status == "ok", f"Status sollte 'ok' sein, war aber '{preview[0].status}'"

    # Ausführung muss die Datei tatsächlich umbenennen
    success, errors, history = execute_rename(preview)
    assert success == 1
    assert len(errors) == 0
    assert len(history) == 1


def test_collision_with_unchanged_file_in_batch(tmp_path: Path):
    """Eine Umbenennung auf den Namen einer im selben Batch unverändert bleibenden Datei muss als Kollision erkannt werden."""
    f1 = tmp_path / "file1.txt"
    f2 = tmp_path / "file2.txt"
    f1.write_text("1", encoding="utf-8")
    f2.write_text("2", encoding="utf-8")

    # Regel: Ersetze '1' durch '2' -> f1 will 'file2.txt' werden, f2 bleibt 'file2.txt'
    rules = RenameRules(search_str="1", replace_str="2")
    preview = generate_preview([str(f1), str(f2)], rules)

    assert len(preview) == 2
    f1_item = next(it for it in preview if it.original_name == "file1.txt")
    f2_item = next(it for it in preview if it.original_name == "file2.txt")

    assert f2_item.status == "unchanged"
    assert f1_item.status == "collision", f"f1 sollte als Kollision erkannt werden, war aber '{f1_item.status}'"
    assert "Kollision" in (f1_item.error_message or "")


def test_chain_rename_execution(tmp_path: Path):
    """Kettenumbenennung: file1 -> file2 und file2 -> file3 muss ohne FileExistsError gelingen."""
    f1 = tmp_path / "file1.txt"
    f2 = tmp_path / "file2.txt"
    f1.write_text("content1", encoding="utf-8")
    f2.write_text("content2", encoding="utf-8")

    # Manuell konstruierter Preview für Kette f1->f2, f2->f3
    f3_path = str(tmp_path / "file3.txt")
    from core.batch_rename_service import RenameItem
    items = [
        RenameItem(original_path=str(f1), original_name="file1.txt", new_name="file2.txt", new_path=str(f2), status="ok"),
        RenameItem(original_path=str(f2), original_name="file2.txt", new_name="file3.txt", new_path=f3_path, status="ok"),
    ]

    success, errors, history = execute_rename(items)
    assert len(errors) == 0, f"Fehler bei Ketten-Ausführung: {errors}"
    assert success == 2
    assert not f1.exists()
    assert (tmp_path / "file2.txt").read_text(encoding="utf-8") == "content1"
    assert (tmp_path / "file3.txt").read_text(encoding="utf-8") == "content2"

    # Rollback der Kette
    restored, r_errors = rollback_rename(history)
    assert len(r_errors) == 0
    assert restored == 2
    assert f1.read_text(encoding="utf-8") == "content1"
    assert f2.read_text(encoding="utf-8") == "content2"
    assert not (tmp_path / "file3.txt").exists()


def test_swap_rename_execution(tmp_path: Path):
    """Zyklische Umbenennung (Swap): a -> b und b -> a muss dank Zwei-Phasen-Rename gelingen."""
    f_a = tmp_path / "a.txt"
    f_b = tmp_path / "b.txt"
    f_a.write_text("content_A", encoding="utf-8")
    f_b.write_text("content_B", encoding="utf-8")

    from core.batch_rename_service import RenameItem
    items = [
        RenameItem(original_path=str(f_a), original_name="a.txt", new_name="b.txt", new_path=str(f_b), status="ok"),
        RenameItem(original_path=str(f_b), original_name="b.txt", new_name="a.txt", new_path=str(f_a), status="ok"),
    ]

    success, errors, history = execute_rename(items)
    assert len(errors) == 0, f"Fehler bei Swap-Ausführung: {errors}"
    assert success == 2
    assert f_a.read_text(encoding="utf-8") == "content_B"
    assert f_b.read_text(encoding="utf-8") == "content_A"

    # Rollback des Swaps
    restored, r_errors = rollback_rename(history)
    assert len(r_errors) == 0
    assert restored == 2
    assert f_a.read_text(encoding="utf-8") == "content_A"
    assert f_b.read_text(encoding="utf-8") == "content_B"


def test_trailing_dot_and_space_rejected():
    """Dateinamen mit nachgestelltem Punkt oder Leerzeichen sind auf Windows unzulässig."""
    rules_dot = RenameRules(suffix=".")
    _, err_dot = compute_new_name("test", rules_dot)
    assert err_dot is not None
    assert "Punkt" in err_dot or "Ungültig" in err_dot

    rules_space = RenameRules(suffix=" ")
    _, err_space = compute_new_name("test", rules_space)
    assert err_space is not None
    assert "Leerzeichen" in err_space or "Ungültig" in err_space

    rules_ext_dot = RenameRules(change_extension="txt.")
    _, err_ext_dot = compute_new_name("test.txt", rules_ext_dot)
    assert err_ext_dot is not None
    assert "Punkt" in err_ext_dot or "Ungültig" in err_ext_dot


def test_cascading_collision_detection_in_preview_and_execute(tmp_path: Path):
    """
    Kaskadierende Kollisionserkennung:
    Wenn doc_1 -> doc_2 und doc_2 -> doc_3 umbenannt werden soll, doc_3 aber
    bereits auf der Festplatte existiert und nicht im Batch ist, kollidiert doc_2.
    Da doc_2 nicht verschoben werden kann, muss auch doc_1 als Kollision erkannt werden
    und darf keinesfalls als 'ok' markiert werden.
    """
    f1 = tmp_path / "doc_1.txt"
    f2 = tmp_path / "doc_2.txt"
    f3 = tmp_path / "doc_3.txt"
    f1.write_text("content 1", encoding="utf-8")
    f2.write_text("content 2", encoding="utf-8")
    f3.write_text("content 3", encoding="utf-8")

    rules = RenameRules(
        search_str=r"_[0-9]+",
        replace_str="",
        use_regex=True,
        numbering_enabled=True,
        number_position="suffix",
        start_num=2,
        step_num=1,
        padding=1,
    )
    preview = generate_preview([str(f1), str(f2)], rules)
    assert len(preview) == 2

    item_f1 = next(it for it in preview if it.original_name == "doc_1.txt")
    item_f2 = next(it for it in preview if it.original_name == "doc_2.txt")

    assert item_f2.status == "collision", f"doc_2 sollte collision sein, war {item_f2.status}"
    assert item_f1.status == "collision", (
        f"Kaskade fehlgeschlagen: doc_1 wurde fälschlich als '{item_f1.status}' markiert, "
        "obwohl Zieldatei doc_2 nicht verschoben werden kann!"
    )
    assert "Kollision" in (item_f1.error_message or "")

    # Ausführung darf keine Datei verändern oder crashen
    success, errors, history = execute_rename(preview)
    assert success == 0
    assert f1.read_text(encoding="utf-8") == "content 1"
    assert f2.read_text(encoding="utf-8") == "content 2"
    assert f3.read_text(encoding="utf-8") == "content 3"


def test_replace_numbering_preserves_prefix_and_suffix():
    """
    Bei 'Name ersetzen' (number_position='replace') muss die Nummer den Stamm ersetzen,
    aber konfigurierte Präfixe und Suffixe müssen erhalten bleiben.
    """
    rules = RenameRules(
        prefix="IMG_",
        suffix="_RAW",
        numbering_enabled=True,
        number_position="replace",
        start_num=1,
        padding=3,
    )
    new_name, err = compute_new_name("photo.jpg", rules, index=0)
    assert err is None
    assert new_name == "IMG_001_RAW.jpg", f"Erwartet 'IMG_001_RAW.jpg', erhalten '{new_name}'"


def test_windows_reserved_device_names_rejected():
    """Windows-reservierte Gerätenamen (CON, PRN, AUX, NUL, COM1-9, LPT1-9) müssen abgefangen werden."""
    for bad_stem in ["CON", "prn", "aux", "Nul", "com1", "COM9", "lpt1", "LPT9"]:
        rules = RenameRules(search_str="sample", replace_str=bad_stem)
        name, err = compute_new_name("sample.txt", rules)
        assert err is not None, f"Reservierter Name '{bad_stem}' wurde nicht als Fehler erkannt!"
        assert "reserviert" in err or "Ungültig" in err


def test_execute_rename_early_break_on_missing_source(tmp_path: Path):
    """Fehlt eine Quelldatei in Phase 1, muss sofort abgebrochen werden, ohne Folge-Dateien anzufassen."""
    from core.batch_rename_service import RenameItem
    missing_src = str(tmp_path / "does_not_exist.txt")
    valid_file = tmp_path / "valid.txt"
    valid_file.write_text("keep_intact", encoding="utf-8")

    items = [
        RenameItem(original_path=missing_src, original_name="does_not_exist.txt", new_name="x.txt", new_path=str(tmp_path / "x.txt"), status="ok"),
        RenameItem(original_path=str(valid_file), original_name="valid.txt", new_name="valid_renamed.txt", new_path=str(tmp_path / "valid_renamed.txt"), status="ok"),
    ]

    success, errors, history = execute_rename(items)
    assert success == 0
    assert any("nicht gefunden" in e for e in errors)
    assert valid_file.exists()
    assert valid_file.read_text(encoding="utf-8") == "keep_intact"
    assert not (tmp_path / "valid_renamed.txt").exists()


def test_execute_rename_guards_against_existing_destination(tmp_path: Path):
    """Phase 2 muss prüfen, ob der Zielpfad unerwartet belegt ist (Schutz vor stillem Überschreiben)."""
    from core.batch_rename_service import RenameItem
    f1 = tmp_path / "f1.txt"
    f2 = tmp_path / "already_here.txt"
    f1.write_text("one", encoding="utf-8")
    f2.write_text("precious", encoding="utf-8")

    # Item will auf den Pfad von f2 umbenennen, f2 ist aber vorhanden
    items = [
        RenameItem(original_path=str(f1), original_name="f1.txt", new_name="already_here.txt", new_path=str(f2), status="ok"),
    ]

    success, errors, history = execute_rename(items)
    assert success == 0
    assert len(errors) > 0
    assert f1.read_text(encoding="utf-8") == "one"
    assert f2.read_text(encoding="utf-8") == "precious"
