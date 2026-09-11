#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
batch_rename_service.py - Leistungsfähiger Service für Mehrfachumbenennungen (Batch Rename)

Unterstützt:
- Suchen & Ersetzen (mit Regex-Support)
- Präfix- und Suffix-Ergänzung
- Flexible Nummerierung (Start, Schritt, Führende Nullen / Padding)
- Groß-/Kleinschreibungs-Transformationen (lower, upper, title, sentence)
- Erweiterungs-Änderung
- Kollisionserkennung (Dateisystem & chargenintern)
- Transaktionale Ausführung mit Rollback-Protokoll
"""

import os
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict


# Ungültige Dateinamenzeichen auf gängigen Betriebssystemen
INVALID_FILENAME_CHARS = set(r'<>:"/\|?*')


@dataclass
class RenameRules:
    """Konfiguration der Umbenennungsregeln."""
    search_str: str = ""
    replace_str: str = ""
    use_regex: bool = False
    regex_case_sensitive: bool = True
    prefix: str = ""
    suffix: str = ""
    case_mode: Optional[str] = None  # None, "lower", "upper", "title", "sentence"
    numbering_enabled: bool = False
    start_num: int = 1
    step_num: int = 1
    padding: int = 2
    number_position: str = "suffix"  # "prefix", "suffix", "replace"
    change_extension: Optional[str] = None  # None = beibehalten, sonst z. B. ".txt" or "txt"


@dataclass
class RenameItem:
    """Ein einzelnes Umbenennungselement mit Status und Validierung."""
    original_path: str
    original_name: str
    new_name: str
    new_path: str
    status: str = "ok"  # "ok", "unchanged", "collision", "invalid"
    error_message: Optional[str] = None


def apply_case_mode(text: str, mode: Optional[str]) -> str:
    """Wendet die gewünschte Groß-/Kleinschreibung auf einen Text an."""
    if not mode:
        return text
    mode_lower = mode.lower()
    if mode_lower == "lower":
        return text.lower()
    if mode_lower == "upper":
        return text.upper()
    if mode_lower == "title":
        return text.title()
    if mode_lower == "sentence":
        return text.capitalize()
    return text


def sanitize_extension(ext: Optional[str]) -> Optional[str]:
    """Bereinigt eine Dateiendung, sodass sie mit '.' beginnt."""
    if ext is None:
        return None
    cleaned = ext.strip()
    if not cleaned:
        return ""
    if not cleaned.startswith("."):
        cleaned = "." + cleaned
    return cleaned


def compute_new_name(
    original_name: str,
    rules: RenameRules,
    index: int = 0
) -> Tuple[str, Optional[str]]:
    """
    Berechnet den neuen Dateinamen anhand der definierten Regeln.
    Gibt (neuer_name, fehler_nachricht) zurück.
    """
    stem, ext = os.path.splitext(original_name)

    # 1. Suchen und Ersetzen auf dem Stamm
    new_stem = stem
    if rules.search_str:
        if rules.use_regex:
            try:
                flags = 0 if rules.regex_case_sensitive else re.IGNORECASE
                new_stem = re.sub(rules.search_str, rules.replace_str, new_stem, flags=flags)
            except re.error as err:
                return original_name, f"Ungültiger Regex: {err}"
        else:
            if rules.regex_case_sensitive:
                new_stem = new_stem.replace(rules.search_str, rules.replace_str)
            else:
                pattern = re.compile(re.escape(rules.search_str), re.IGNORECASE)
                new_stem = pattern.sub(rules.replace_str, new_stem)

    # 2. Groß-/Kleinschreibung
    new_stem = apply_case_mode(new_stem, rules.case_mode)

    # 3. Präfix und Suffix
    if rules.prefix:
        new_stem = rules.prefix + new_stem
    if rules.suffix:
        new_stem = new_stem + rules.suffix

    # 4. Nummerierung
    if rules.numbering_enabled:
        num_val = rules.start_num + (index * rules.step_num)
        formatted_num = str(num_val).zfill(max(1, rules.padding))
        if rules.number_position == "prefix":
            new_stem = f"{formatted_num}_{new_stem}"
        elif rules.number_position == "replace":
            new_stem = formatted_num
        else:  # "suffix"
            new_stem = f"{new_stem}_{formatted_num}"

    # 5. Dateiendung
    if rules.change_extension is not None:
        new_ext = sanitize_extension(rules.change_extension)
    else:
        new_ext = ext

    final_name = new_stem + new_ext

    # 6. Validierung
    if not final_name or final_name.strip() in ("", ".", ".."):
        return original_name, "Dateiname darf nicht leer sein"

    for ch in INVALID_FILENAME_CHARS:
        if ch in final_name:
            return final_name, f"Ungültiges Zeichen im Dateinamen: '{ch}'"

    return final_name, None


def generate_preview(
    file_paths: List[str],
    rules: RenameRules
) -> List[RenameItem]:
    """
    Erstellt eine vollständige Vorschau der Umbenennungen inklusive
    Kollisions- und Gültigkeitsprüfung.
    """
    items: List[RenameItem] = []
    seen_target_paths: Dict[str, int] = {}

    for idx, path in enumerate(file_paths):
        orig_name = os.path.basename(path)
        parent_dir = os.path.dirname(path)
        new_name, error = compute_new_name(orig_name, rules, index=idx)
        new_path = os.path.join(parent_dir, new_name)

        item = RenameItem(
            original_path=path,
            original_name=orig_name,
            new_name=new_name,
            new_path=new_path,
        )

        if error:
            item.status = "invalid"
            item.error_message = error
        elif os.path.normcase(path) == os.path.normcase(new_path):
            item.status = "unchanged"
        else:
            norm_target = os.path.normcase(new_path)
            # Kollision innerhalb des aktuellen Batches
            if norm_target in seen_target_paths:
                item.status = "collision"
                item.error_message = "Kollision: Mehrere Dateien erhalten denselben Namen"
            # Kollision mit einer existierenden Datei auf der Festplatte
            elif os.path.exists(new_path) and os.path.normcase(new_path) not in [os.path.normcase(p) for p in file_paths]:
                item.status = "collision"
                item.error_message = "Kollision: Datei existiert bereits im Zielverzeichnis"
            else:
                item.status = "ok"

            seen_target_paths[norm_target] = idx

        items.append(item)

    return items


def execute_rename(
    items: List[RenameItem],
    dry_run: bool = False
) -> Tuple[int, List[str], List[Tuple[str, str]]]:
    """
    Führt die Umbenennungen aus.
    Überspringt unveränderte und fehlerhafte Elemente.
    Gibt (anzahl_erfolgreich, fehlerliste, rollback_verlauf) zurück.
    """
    success_count = 0
    errors: List[str] = []
    history: List[Tuple[str, str]] = []  # [(neuer_pfad, alter_pfad), ...]

    actionable = [it for it in items if it.status == "ok"]

    if dry_run:
        return len(actionable), [], []

    for item in actionable:
        src = item.original_path
        dst = item.new_path

        if not os.path.exists(src):
            errors.append(f"Quelle nicht gefunden: {src}")
            continue

        try:
            os.rename(src, dst)
            history.append((dst, src))
            success_count += 1
        except OSError as exc:
            errors.append(f"Fehler bei {item.original_name} -> {item.new_name}: {exc}")

    return success_count, errors, history


def rollback_rename(history: List[Tuple[str, str]]) -> Tuple[int, List[str]]:
    """
    Macht einen Batch-Rename-Vorgang anhand der Historie rückgängig.
    Gibt (anzahl_rueckgaengig, fehlerliste) zurück.
    """
    restored = 0
    errors: List[str] = []

    # In umgekehrter Reihenfolge zurückrollen
    for current_path, original_path in reversed(history):
        if not os.path.exists(current_path):
            errors.append(f"Datei für Rollback nicht gefunden: {current_path}")
            continue
        try:
            os.rename(current_path, original_path)
            restored += 1
        except OSError as exc:
            errors.append(f"Rollback fehlgeschlagen für {current_path}: {exc}")

    return restored, errors
