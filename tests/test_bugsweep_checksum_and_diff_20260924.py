#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_bugsweep_checksum_and_diff_20260924.py
Regressionstests für Bugsweep 2026-09-24:
Bereich: Datei-Integritäts- & Prüfsummen-Dienst, Verifikations-Parsing und Datei-Vergleich
(core/checksum_service.py + gui/checksum_dialog.py + core/diff_service.py + gui/diff_dialog.py)
"""

import os
import sys
from pathlib import Path

# Sicherstellen, dass src im Pfad liegt
SRC_PATH = Path(__file__).resolve().parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

import pytest
from PySide6.QtWidgets import QApplication

from core.checksum_service import verify_hash
from core.diff_service import (
    compare_files,
    generate_unified_diff_text,
    is_binary_file,
)
from gui.checksum_dialog import ChecksumDialog


def _ensure_app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


SAMPLE_HASHES = {
    "md5": "098f6bcd4621d373cade4e832627b4f6",
    "sha1": "a94a8fe5ccb19ba61c4c0873d391e987982fbbd3",
    "sha256": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
    "sha512": "ee26b0dd4af7e749aa1a8ee3c10ae9923f618980772e473f8819a5d4e07ad56281a4b0e2330f4f53b5550c30292d125240ee00bc62ba4e10065c9ecd2f33d5ff",
}


def test_verify_hash_gnu_coreutils_format():
    """Prüft Erkennung von Standard sha256sum / md5sum Text- und Binärzeilen."""
    # Text-Modus (zwei Leerzeichen)
    res1 = verify_hash(SAMPLE_HASHES, "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08  archive.zip")
    assert res1 == ("sha256", SAMPLE_HASHES["sha256"])

    # Binär-Modus (Leerzeichen + Stern)
    res2 = verify_hash(SAMPLE_HASHES, "098f6bcd4621d373cade4e832627b4f6 *test.iso")
    assert res2 == ("md5", SAMPLE_HASHES["md5"])


def test_verify_hash_bsd_format():
    """Prüft Erkennung von BSD-Checksummen (z. B. SHA256 (datei) = hash)."""
    res1 = verify_hash(SAMPLE_HASHES, "SHA256 (ExplorerPro-Setup.exe) = 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08")
    assert res1 == ("sha256", SAMPLE_HASHES["sha256"])

    res2 = verify_hash(SAMPLE_HASHES, "MD5(image.iso)= 098f6bcd4621d373cade4e832627b4f6")
    assert res2 == ("md5", SAMPLE_HASHES["md5"])


def test_verify_hash_key_value_equals_and_spaces():
    """Prüft Erkennung mit '=' oder Leerzeichen als Trenner."""
    res1 = verify_hash(SAMPLE_HASHES, "SHA256 = 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08")
    assert res1 == ("sha256", SAMPLE_HASHES["sha256"])

    res2 = verify_hash(SAMPLE_HASHES, "sha1 a94a8fe5ccb19ba61c4c0873d391e987982fbbd3")
    assert res2 == ("sha1", SAMPLE_HASHES["sha1"])


def test_verify_hash_formatted_hex_delimiters():
    """Prüft Erkennung von formatiertem Hex mit Bindestrichen oder Leerzeichen (z. B. Windows CertUtil / PowerShell)."""
    # CertUtil Format: XX-XX-XX-...
    certutil_sha256 = "9F-86-D0-81-88-4C-7D-65-9A-2F-EA-A0-C5-5A-D0-15-A3-BF-4F-1B-2B-0B-82-2C-D1-5D-6C-15-B0-F0-0A-08"
    assert verify_hash(SAMPLE_HASHES, certutil_sha256) == ("sha256", SAMPLE_HASHES["sha256"])

    # Byte-Gruppiert mit Leerzeichen
    spaced_md5 = "09 8f 6b cd 46 21 d3 73 ca de 4e 83 26 27 b4 f6"
    assert verify_hash(SAMPLE_HASHES, spaced_md5) == ("md5", SAMPLE_HASHES["md5"])


def test_verify_hash_quoted_and_multiline():
    """Prüft Erkennung bei gequoteten Werten und mehrzeiligen Checksummen-Dateien."""
    quoted = '"9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"'
    assert verify_hash(SAMPLE_HASHES, quoted) == ("sha256", SAMPLE_HASHES["sha256"])

    multiline = """
    # SHA256 Checksums
    # Generated on 2026-09-24
    e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  empty.txt
    9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08  target_payload.bin
    """
    assert verify_hash(SAMPLE_HASHES, multiline) == ("sha256", SAMPLE_HASHES["sha256"])


def test_unified_diff_no_double_newlines(tmp_path: Path):
    """Prüft, dass der generierte Unified Diff keine korrupten Leerzeilen zwischen Diff-Zeilen enthält."""
    f1 = tmp_path / "file1.txt"
    f2 = tmp_path / "file2.txt"
    f1.write_text("Row 1\nRow 2\nRow 3\n", encoding="utf-8")
    f2.write_text("Row 1\nRow 2 Modified\nRow 3\nRow 4\n", encoding="utf-8")

    diff_text = generate_unified_diff_text(str(f1), str(f2))
    lines = diff_text.splitlines()

    # Es darf keine leeren Zeilen mitten im Diff-Hunk geben
    for line in lines:
        if line.startswith("@@"):
            continue
        # Jede Diff-Zeile im Body muss mit ' ', '+', '-' beginnen
        if line.startswith("---") or line.startswith("+++"):
            continue
        assert line != "", "Unerwartete Leerzeile im Unified Diff (Doppel-Newline-Bug)!"
        assert line[0] in (" ", "+", "-"), f"Ungültiges erstes Zeichen in Diff-Zeile: {repr(line)}"


def test_compare_files_rejects_directory(tmp_path: Path):
    """Prüft, dass compare_files Verzeichnisse sauber abweist statt mit PermissionError abzustürzen."""
    f1 = tmp_path / "regular.txt"
    f1.write_text("content", encoding="utf-8")
    d1 = tmp_path / "subfolder"
    d1.mkdir()

    with pytest.raises(ValueError) as exc1:
        compare_files(str(d1), str(f1))
    assert "Pfad ist keine reguläre Datei" in str(exc1.value)

    with pytest.raises(ValueError) as exc2:
        compare_files(str(f1), str(d1))
    assert "Pfad ist keine reguläre Datei" in str(exc2.value)


def test_is_binary_file_heuristic_control_chars(tmp_path: Path):
    """Prüft Erkennung von Binärdaten auch ohne Null-Bytes via Kontrollzeichen-Dichte."""
    # Binärdatei ohne 0x00, aber mit vielen Kontrollzeichen (z. B. 0x01..0x1F)
    raw_binary = bytes([i % 31 + 1 for i in range(1000)])
    bin_file = tmp_path / "control_bytes.dat"
    bin_file.write_bytes(raw_binary)

    assert is_binary_file(str(bin_file)) is True


def test_checksum_dialog_done_cancels_worker(tmp_path: Path):
    """Prüft, dass ChecksumDialog.done() (via accept/reject/Schließen) den Worker abbricht."""
    _ensure_app()
    sample = tmp_path / "big_sample.bin"
    sample.write_bytes(b"Z" * (1024 * 1024))

    dlg = ChecksumDialog(str(sample))
    worker = dlg.worker
    assert worker is not None

    # Simuliere Schließen via accept (Button "Schließen")
    dlg.accept()
    assert worker.is_cancelled() is True
    assert not worker.isRunning()


def test_checksum_dialog_directory_handling(tmp_path: Path):
    """Prüft, dass ChecksumDialog bei einem Verzeichnis nicht abstürzt und klare Meldung liefert."""
    _ensure_app()
    sub_dir = tmp_path / "some_directory"
    sub_dir.mkdir()

    dlg = ChecksumDialog(str(sub_dir))
    assert dlg.worker is None
    assert "Verzeichnis" in dlg.verify_result_label.text()
    dlg.close()
