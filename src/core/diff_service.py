#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diff_service.py - Robuster Datei-Vergleichsdienst (Diff Service)

Ermöglicht den präzisen Vergleich zweier Dateien:
- Textdateien: Detaillierter Zeilenvergleich mit difflib (Hinzugefügt, Entfernt, Modifiziert, Identisch)
- Binärdateien: Erkennung binärer Inhalte, Größen- und SHA-256-Prüfsummen-Vergleich
- Export als Standard Unified-Diff
"""

import difflib
import hashlib
import os
from dataclasses import dataclass, field
from typing import List, Optional, Dict


@dataclass
class DiffLine:
    """Repräsentiert eine Zeile im Vergleichsergebnis."""
    tag: str  # 'equal', 'insert', 'delete', 'header', 'info'
    line_num_left: Optional[int]
    line_num_right: Optional[int]
    content: str


@dataclass
class DiffResult:
    """Gesamtergebnis eines Dateivergleichs."""
    file1_path: str
    file2_path: str
    file1_name: str
    file2_name: str
    file1_size: int
    file2_size: int
    file1_hash: str
    file2_hash: str
    is_binary: bool
    is_identical: bool
    lines: List[DiffLine] = field(default_factory=list)
    stats: Dict[str, int] = field(default_factory=lambda: {
        "added": 0,
        "deleted": 0,
        "identical": 0,
        "total_lines_left": 0,
        "total_lines_right": 0,
    })


def is_binary_file(filepath: str, sample_size: int = 8192) -> bool:
    """
    Prüft heuristisch, ob eine Datei binär ist (Präsenz von Null-Bytes).
    """
    if not os.path.isfile(filepath):
        return False
    try:
        with open(filepath, "rb") as f:
            chunk = f.read(sample_size)
            if b"\x00" in chunk:
                return True
            # Versuche als UTF-8 zu decodieren
            try:
                chunk.decode("utf-8")
                return False
            except UnicodeDecodeError:
                # Prüfe lateinische Encodings
                try:
                    chunk.decode("latin-1")
                    return False
                except UnicodeDecodeError:
                    return True
    except OSError:
        return True


def compute_sha256(filepath: str) -> str:
    """Berechnet die SHA-256-Prüfsumme einer Datei."""
    if not os.path.isfile(filepath):
        return ""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def compare_files(file1: str, file2: str, max_lines: int = 15000) -> DiffResult:
    """
    Vergleicht zwei Dateien und liefert ein detailliertes DiffResult zurück.
    """
    if not os.path.exists(file1):
        raise FileNotFoundError(f"Datei nicht gefunden: {file1}")
    if not os.path.exists(file2):
        raise FileNotFoundError(f"Datei nicht gefunden: {file2}")

    size1 = os.path.getsize(file1)
    size2 = os.path.getsize(file2)
    hash1 = compute_sha256(file1)
    hash2 = compute_sha256(file2)

    is_identical = (hash1 == hash2) if (hash1 and hash2) else False
    bin1 = is_binary_file(file1)
    bin2 = is_binary_file(file2)
    is_binary = bin1 or bin2

    result = DiffResult(
        file1_path=file1,
        file2_path=file2,
        file1_name=os.path.basename(file1),
        file2_name=os.path.basename(file2),
        file1_size=size1,
        file2_size=size2,
        file1_hash=hash1,
        file2_hash=hash2,
        is_binary=is_binary,
        is_identical=is_identical,
    )

    # Bei Binärdateien Zeilenvergleich überspringen
    if is_binary:
        status_msg = "Binärdateien sind identisch." if is_identical else "Binärdateien weichen voneinander ab."
        result.lines.append(DiffLine(tag="info", line_num_left=None, line_num_right=None, content=status_msg))
        return result

    # Textdateien zeilenweise vergleichen
    try:
        with open(file1, "r", encoding="utf-8", errors="replace") as f1:
            lines1 = f1.read().splitlines()
        with open(file2, "r", encoding="utf-8", errors="replace") as f2:
            lines2 = f2.read().splitlines()
    except OSError as exc:
        result.lines.append(DiffLine(tag="info", line_num_left=None, line_num_right=None, content=f"Lesefehler: {exc}"))
        return result

    result.stats["total_lines_left"] = len(lines1)
    result.stats["total_lines_right"] = len(lines2)

    # Diff-Matching durchführen
    matcher = difflib.SequenceMatcher(None, lines1, lines2)
    diff_lines: List[DiffLine] = []

    added = 0
    deleted = 0
    identical = 0

    left_idx = 0
    right_idx = 0

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for k in range(i1, i2):
                left_idx += 1
                right_idx += 1
                diff_lines.append(DiffLine(
                    tag="equal",
                    line_num_left=left_idx,
                    line_num_right=right_idx,
                    content=lines1[k]
                ))
                identical += 1
        elif tag == "replace":
            for k in range(i1, i2):
                left_idx += 1
                diff_lines.append(DiffLine(
                    tag="delete",
                    line_num_left=left_idx,
                    line_num_right=None,
                    content=lines1[k]
                ))
                deleted += 1
            for k in range(j1, j2):
                right_idx += 1
                diff_lines.append(DiffLine(
                    tag="insert",
                    line_num_left=None,
                    line_num_right=right_idx,
                    content=lines2[k]
                ))
                added += 1
        elif tag == "delete":
            for k in range(i1, i2):
                left_idx += 1
                diff_lines.append(DiffLine(
                    tag="delete",
                    line_num_left=left_idx,
                    line_num_right=None,
                    content=lines1[k]
                ))
                deleted += 1
        elif tag == "insert":
            for k in range(j1, j2):
                right_idx += 1
                diff_lines.append(DiffLine(
                    tag="insert",
                    line_num_left=None,
                    line_num_right=right_idx,
                    content=lines2[k]
                ))
                added += 1

        if len(diff_lines) >= max_lines:
            diff_lines.append(DiffLine(
                tag="info",
                line_num_left=None,
                line_num_right=None,
                content=f"... Ausgabe bei {max_lines} Zeilen begrenzt ..."
            ))
            break

    result.lines = diff_lines
    result.stats["added"] = added
    result.stats["deleted"] = deleted
    result.stats["identical"] = identical

    return result


def generate_unified_diff_text(file1: str, file2: str) -> str:
    """
    Erzeugt einen standardisierten Unified-Diff-String.
    """
    if not os.path.isfile(file1) or not os.path.isfile(file2):
        return ""

    if is_binary_file(file1) or is_binary_file(file2):
        h1 = compute_sha256(file1)
        h2 = compute_sha256(file2)
        if h1 == h2:
            return "Binary files are identical."
        return f"Binary files differ:\n  {file1} (SHA256: {h1})\n  {file2} (SHA256: {h2})"

    with open(file1, "r", encoding="utf-8", errors="replace") as f1:
        lines1 = f1.readlines()
    with open(file2, "r", encoding="utf-8", errors="replace") as f2:
        lines2 = f2.readlines()

    diff = difflib.unified_diff(
        lines1,
        lines2,
        fromfile=file1,
        tofile=file2,
        lineterm=""
    )
    return "\n".join(diff)
