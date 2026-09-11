#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_batch_renamer.py - Umfassende Tests für den Batch-Rename-Service (TW-EP-10)
"""

from pathlib import Path

from core.batch_rename_service import (
    RenameRules,
    apply_case_mode,
    sanitize_extension,
    compute_new_name,
    generate_preview,
    execute_rename,
    rollback_rename,
)


def test_apply_case_mode():
    text = "hALLO wELT"
    assert apply_case_mode(text, None) == "hALLO wELT"
    assert apply_case_mode(text, "lower") == "hallo welt"
    assert apply_case_mode(text, "upper") == "HALLO WELT"
    assert apply_case_mode(text, "title") == "Hallo Welt"
    assert apply_case_mode(text, "sentence") == "Hallo welt"


def test_sanitize_extension():
    assert sanitize_extension(None) is None
    assert sanitize_extension("txt") == ".txt"
    assert sanitize_extension(".md") == ".md"
    assert sanitize_extension("   .pdf  ") == ".pdf"
    assert sanitize_extension("") == ""


def test_compute_new_name_search_replace():
    rules = RenameRules(search_str="DOC", replace_str="REPORT", regex_case_sensitive=True)
    new_name, err = compute_new_name("my_DOC_final.txt", rules)
    assert err is None
    assert new_name == "my_REPORT_final.txt"

    # Case insensitive
    rules_ci = RenameRules(search_str="doc", replace_str="REPORT", regex_case_sensitive=False)
    new_name_ci, err = compute_new_name("my_DOC_final.txt", rules_ci)
    assert err is None
    assert new_name_ci == "my_REPORT_final.txt"


def test_compute_new_name_regex():
    rules = RenameRules(search_str=r"\d+", replace_str="X", use_regex=True)
    new_name, err = compute_new_name("invoice_2026_09.pdf", rules)
    assert err is None
    assert new_name == "invoice_X_X.pdf"

    # Invalid regex
    bad_rules = RenameRules(search_str=r"[unclosed", replace_str="X", use_regex=True)
    bad_name, err = compute_new_name("test.txt", bad_rules)
    assert err is not None
    assert "Ungültiger Regex" in err


def test_compute_new_name_prefix_suffix_case():
    rules = RenameRules(prefix="pre_", suffix="_post", case_mode="upper", change_extension=".dat")
    new_name, err = compute_new_name("sample.txt", rules)
    assert err is None
    assert new_name == "pre_SAMPLE_post.dat"


def test_compute_new_name_numbering():
    # Suffix numbering
    rules_suffix = RenameRules(numbering_enabled=True, start_num=10, step_num=5, padding=3, number_position="suffix")
    name0, err0 = compute_new_name("item.png", rules_suffix, index=0)
    name1, err1 = compute_new_name("item.png", rules_suffix, index=1)
    assert name0 == "item_010.png"
    assert name1 == "item_015.png"

    # Prefix numbering
    rules_prefix = RenameRules(numbering_enabled=True, start_num=1, padding=2, number_position="prefix")
    pname, _ = compute_new_name("photo.jpg", rules_prefix, index=2)
    assert pname == "03_photo.jpg"

    # Replace numbering
    rules_replace = RenameRules(numbering_enabled=True, start_num=1, padding=4, number_position="replace")
    rname, _ = compute_new_name("photo.jpg", rules_replace, index=0)
    assert rname == "0001.jpg"


def test_compute_new_name_invalid_chars():
    rules = RenameRules(prefix="bad:char*")
    new_name, err = compute_new_name("doc.txt", rules)
    assert err is not None
    assert "Ungültiges Zeichen" in err


def test_generate_preview_and_collision_detection(tmp_path: Path):
    file1 = tmp_path / "file1.txt"
    file2 = tmp_path / "file2.txt"
    file3 = tmp_path / "existing_target.txt"

    file1.write_text("1")
    file2.write_text("2")
    file3.write_text("3")

    # Unchanged
    rules_no_change = RenameRules()
    preview1 = generate_preview([str(file1), str(file2)], rules_no_change)
    assert all(it.status == "unchanged" for it in preview1)

    # Batch internal collision (both want to be 'renamed.txt')
    rules_collision = RenameRules(prefix="fixed_name", search_str="file1", replace_str="fixed_name")
    # Let's test with replace numbering disabled and fixed name
    rules_collision.search_str = r".*"
    rules_collision.replace_str = "target"
    rules_collision.use_regex = True
    preview_col = generate_preview([str(file1), str(file2)], rules_collision)
    assert any(it.status == "collision" for it in preview_col)

    # Disk collision (file1 wants to be 'existing_target.txt')
    rules_disk_col = RenameRules(search_str="file1", replace_str="existing_target")
    preview_disk = generate_preview([str(file1)], rules_disk_col)
    assert preview_disk[0].status == "collision"
    assert "existiert bereits" in preview_disk[0].error_message


def test_execute_rename_and_rollback(tmp_path: Path):
    f1 = tmp_path / "test_a.txt"
    f2 = tmp_path / "test_b.txt"
    f1.write_text("alpha")
    f2.write_text("beta")

    rules = RenameRules(prefix="new_")
    preview = generate_preview([str(f1), str(f2)], rules)
    assert all(it.status == "ok" for it in preview)

    # Dry run
    success, errors, history = execute_rename(preview, dry_run=True)
    assert success == 2
    assert f1.exists() and f2.exists()
    assert not (tmp_path / "new_test_a.txt").exists()

    # Actual run
    success, errors, history = execute_rename(preview, dry_run=False)
    assert success == 2
    assert len(errors) == 0
    assert not f1.exists()
    assert (tmp_path / "new_test_a.txt").exists()
    assert (tmp_path / "new_test_b.txt").exists()

    # Rollback
    restored, r_errors = rollback_rename(history)
    assert restored == 2
    assert len(r_errors) == 0
    assert f1.exists() and f2.exists()
    assert not (tmp_path / "new_test_a.txt").exists()
    assert not (tmp_path / "new_test_b.txt").exists()
