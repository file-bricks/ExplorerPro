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
    if not cleaned or cleaned == ".":
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

    final_name = new_stem + (new_ext or "")

    # 6. Validierung
    if not final_name or final_name.strip() in ("", ".", ".."):
        return original_name, "Dateiname darf nicht leer sein"

    if final_name.endswith(".") or final_name.endswith(" "):
        return final_name, "Dateiname darf nicht mit einem Punkt oder Leerzeichen enden"

    for ch in final_name:
        if ch in INVALID_FILENAME_CHARS or ord(ch) < 32:
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

    # 1. Erster Durchlauf: Namen berechnen und identische Pfade (unchanged) bestimmen
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
        elif os.path.normpath(path) == os.path.normpath(new_path):
            item.status = "unchanged"
        else:
            item.status = "ok"

        items.append(item)

    # 2. Zweiter Durchlauf: Kollisionsanalyse
    # Jedes Element belegt am Ende einen Pfad:
    # - 'ok': will new_path belegen
    # - 'unchanged' oder 'invalid': belegt weiterhin original_path
    target_usage: Dict[str, List[int]] = {}
    for idx, item in enumerate(items):
        target = item.new_path if item.status == "ok" else item.original_path
        norm_t = os.path.normcase(os.path.abspath(target))
        target_usage.setdefault(norm_t, []).append(idx)

    norm_original_inputs = {os.path.normcase(os.path.abspath(p)) for p in file_paths}

    for idx, item in enumerate(items):
        if item.status != "ok":
            continue

        norm_target = os.path.normcase(os.path.abspath(item.new_path))
        norm_src = os.path.normcase(os.path.abspath(item.original_path))

        # Prüfung 1: Kollision innerhalb des aktuellen Batches
        users = target_usage.get(norm_target, [])
        if len(users) > 1:
            item.status = "collision"
            if any(items[u].status in ("unchanged", "invalid") for u in users if u != idx):
                item.error_message = "Kollision: Zieldatei bleibt im selben Ordner unverändert bestehen"
            else:
                item.error_message = "Kollision: Mehrere Dateien erhalten denselben Namen"
            continue

        # Prüfung 2: Kollision mit einer existierenden Datei auf der Festplatte
        # Wenn norm_target == norm_src handelt es sich um einen Case-Only Rename der eigenen Datei.
        if norm_target != norm_src:
            if os.path.exists(item.new_path):
                if norm_target not in norm_original_inputs:
                    item.status = "collision"
                    item.error_message = "Kollision: Datei existiert bereits im Zielverzeichnis"
                    continue
                # Gehört zu einer anderen Datei im Batch. Zieht diese Datei sicher weg?
                other_idx = next(
                    (i for i, it in enumerate(items) if os.path.normcase(os.path.abspath(it.original_path)) == norm_target),
                    None
                )
                if other_idx is not None:
                    other_item = items[other_idx]
                    if other_item.status != "ok":
                        item.status = "collision"
                        item.error_message = "Kollision: Datei existiert bereits im Zielverzeichnis"
                        continue

    return items


def execute_rename(
    items: List[RenameItem],
    dry_run: bool = False
) -> Tuple[int, List[str], List[Tuple[str, str]]]:
    """
    Führt die Umbenennungen aus.
    Verwendet ein atomares Zwei-Phasen-Verfahren über temporäre Zwischenpfade,
    um Kettungs- und Zyklus-Kollisionen sowie Windows Case-Only-Renames
    garantiert kollisionsfrei und ohne Datenverlust abzuwickeln.
    Gibt (anzahl_erfolgreich, fehlerliste, rollback_verlauf) zurück.
    """
    import uuid

    success_count = 0
    errors: List[str] = []
    history: List[Tuple[str, str]] = []  # [(neuer_pfad, alter_pfad), ...]

    actionable = [it for it in items if it.status == "ok"]

    if dry_run:
        return len(actionable), [], []

    # Phase 1: Jede Quelldatei in einen eindeutigen temporären Pfad im selben Verzeichnis umbenennen
    temp_stage: List[Tuple[str, str, str, RenameItem]] = []
    phase1_done: List[Tuple[str, str]] = []  # [(temp_path, original_path)]

    for item in actionable:
        src = item.original_path
        dst = item.new_path

        if not os.path.exists(src):
            errors.append(f"Quelle nicht gefunden: {src}")
            continue

        parent_dir = os.path.dirname(src)
        temp_name = f".__ep_tmp_{uuid.uuid4().hex}__"
        temp_path = os.path.join(parent_dir, temp_name)

        try:
            os.rename(src, temp_path)
            phase1_done.append((temp_path, src))
            temp_stage.append((temp_path, src, dst, item))
        except OSError as exc:
            errors.append(f"Fehler beim Vorbereiten von {item.original_name}: {exc}")
            break

    # Falls Phase 1 fehlschlägt: Alle bisherigen temp_path zurück auf original_path
    if errors:
        for t_path, orig_path in reversed(phase1_done):
            try:
                if os.path.exists(t_path):
                    os.rename(t_path, orig_path)
            except OSError as rb_exc:
                errors.append(f"Rollback-Fehler bei Phase-1-Bereinigung von {orig_path}: {rb_exc}")
        return 0, errors, []

    # Phase 2: Von temp_path zum endgültigen dst umbenennen
    phase2_done: List[Tuple[str, str]] = []  # [(dst, original_path)]

    for temp_path, orig_path, dst, item in temp_stage:
        try:
            os.rename(temp_path, dst)
            phase2_done.append((dst, orig_path))
            history.append((dst, orig_path))
            success_count += 1
        except OSError as exc:
            errors.append(f"Fehler bei {item.original_name} -> {item.new_name}: {exc}")
            break

    if errors:
        # Rückabwicklung bei Abbruch in Phase 2
        for final_dst, original_path in reversed(phase2_done):
            try:
                if os.path.exists(final_dst):
                    os.rename(final_dst, original_path)
            except OSError as rb_exc:
                errors.append(f"Rollback-Fehler bei {final_dst}: {rb_exc}")

        for temp_path, orig_path, dst, item in temp_stage[len(phase2_done):]:
            try:
                if os.path.exists(temp_path):
                    os.rename(temp_path, orig_path)
            except OSError as rb_exc:
                errors.append(f"Rollback-Fehler bei Phase-1-Rest {orig_path}: {rb_exc}")

        return 0, errors, []

    return success_count, errors, history


def rollback_rename(history: List[Tuple[str, str]]) -> Tuple[int, List[str]]:
    """
    Macht einen Batch-Rename-Vorgang anhand der Historie rückgängig.
    Nutzt ebenfalls ein temporäres Zwischenverfahren, damit auch Ketten,
    Swaps und Case-Changes im Rollback kollisionsfrei zurückgesetzt werden.
    Gibt (anzahl_rueckgaengig, fehlerliste) zurück.
    """
    import uuid

    restored = 0
    errors: List[str] = []

    # Phase 1: current_path -> temp_path
    temp_stage: List[Tuple[str, str]] = []  # [(temp_path, original_path)]
    for current_path, original_path in reversed(history):
        if not os.path.exists(current_path):
            errors.append(f"Datei für Rollback nicht gefunden: {current_path}")
            continue
        parent_dir = os.path.dirname(current_path)
        temp_path = os.path.join(parent_dir, f".__ep_rb_tmp_{uuid.uuid4().hex}__")
        try:
            os.rename(current_path, temp_path)
            temp_stage.append((temp_path, original_path))
        except OSError as exc:
            errors.append(f"Fehler bei Rollback-Vorbereitung für {current_path}: {exc}")

    # Phase 2: temp_path -> original_path
    for temp_path, original_path in temp_stage:
        try:
            os.rename(temp_path, original_path)
            restored += 1
        except OSError as exc:
            errors.append(f"Rollback fehlgeschlagen für {original_path}: {exc}")

    return restored, errors
