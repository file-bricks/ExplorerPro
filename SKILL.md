---
name: explorerpro
version: "1.0.9"
license: AGPL-3.0-or-later
description: |
  Product usage guide for ExplorerPro Suite (PySide6 desktop file manager,
  SQLite FTS5 full-text search, duplicate finder, archive suite, quick editor,
  folder sync, and sanitized workspace export).
---

# ExplorerPro Suite — Product Skill (`SKILL.md`)

> **Scope:** Product usage, verification, and safe machine-assisted workflows for **ExplorerPro Suite v1.0.9** (`file-bricks/ExplorerPro`).
> For repository development conventions, see `AGENTS.md` / `CLAUDE.md`.

## Capabilities & When to Use

ExplorerPro is a 100% local-first, offline desktop file manager and power-user utility suite (Python `3.10–3.12`, PySide6 / Qt 6, SQLite FTS5, PyMuPDF):

- **Multi-Tab File Browsing & Preview:** Directory navigation, inline preview (PDF, images, spreadsheets, syntax-highlighted code, Markdown), and file properties.
- **SQLite FTS5 Indexing & Search (`src/modules/indexer/`):** Fast filename and content search using embedded SQLite FTS5 in WAL mode.
- **Byte-Exact Duplicate Detection:** Two-phase size + MD5/SHA-256 chunk hashing with Recycle Bin deletion.
- **Safe Archive Suite (`src/core/archive_service.py`):** Create, inspect, verify, and extract `.zip`, `.tar`, `.tar.gz`/`.tgz`, `.tar.bz2`/`.tbz2`, `.tar.xz`/`.txz`, and standalone `.gz`/`.bz2`/`.xz` single-file streams with Zip-Slip/Tar-Slip path-traversal protection and atomic writes.
- **Atomic Persistence & File Diff (`src/core/atomic_io.py`, `src/core/diff_service.py`):** Crash-safe `os.replace` + `fsync` writes and fast size/prefix-filtered file comparisons.
- **Batch Rename & Folder Sync:** Rule-based batch renaming with collision detection and one-way/mirror directory sync with dry-run previews.
- **Sanitized Workspace Export (`EXPORTFORMAT.md`):** `explorerpro-workspace-v1` redacted workspace interchange format.

## Boundaries & Limitations

- **100% Local-First / Zero-Egress:** Never makes remote network calls, telemetry pings, or cloud API requests.
- **Non-Elevation (`RunAsInvoker`):** Runs strictly under user-level permissions; never requests UAC or root elevation.
- **No Cloud-Drive Sync Client:** ExplorerPro manages local/mounted paths; it does not replace cloud-provider sync daemons.
- **Destructive Safety:** File deletions/overwrites require confirmation or safe staging; automated callers must never bypass `sanitize_archive_member_path`.

## Setup & Prerequisites

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

## Human & Machine Entry Points

### 1. Desktop Application Launch

```bash
python src/main.py
# Windows launcher:
START_ExplorerPro.bat
```

### 2. Automated Verification & Smoke Entry Points

| Task | Command | Expected Output / Exit Code |
|---|---|---|
| Offscreen Desktop Smoke | `QT_QPA_PLATFORM=offscreen python tests/source_platform_smoke.py` | Prints `source_platform_smoke: OK`, exit `0` |
| Release Binary Smoke | `python src/main.py --release-smoke <path-to-bundle>` | Exits `0` on valid bundle |
| Store Readiness Preflight | `python scripts/check_store_readiness.py` | Prints readiness report, exit `0` when staged |
| 6-Language Translation Check | `python manage_translations.py --check` | Exit `0` when all 6 locales (`de/en/es/zh/ja/ru`) are 100% complete |
| Full Test Suite | `QT_QPA_PLATFORM=offscreen python -m pytest -ra -v` | All non-skipped tests pass, exit `0` |

### 3. Safe Programmatic Core APIs

When delegating deterministic file, archive, or diff tasks in Python:

- **Archive Operations (`src/core/archive_service.py`):**
  - `inspect_archive(path)` -> `(ArchiveSummary, List[ArchiveEntry])`
  - `create_archive(sources, dest_path)` -> `(added_files, total_bytes)`
  - `extract_archive(archive_path, target_dir, members=None, overwrite=True)` -> `(extracted_files, extracted_bytes)`
  - `check_archive_integrity(archive_path)` -> `(is_valid: bool, error: Optional[str])`
  - `sanitize_archive_member_path(member_name, target_dir)` -> resolved `Path` inside `target_dir` or raises `ZipSlipSecurityError`
- **Atomic File Writes (`src/core/atomic_io.py`):**
  - `atomic_write_bytes(path, data)`, `atomic_write_text(path, text)`, `atomic_write_json(path, payload)`
- **Fast Byte/Diff Comparison (`src/core/diff_service.py`):**
  - `compute_sha256(filepath, chunk_size=262144)`, `compare_files(path_a, path_b)`

## Verification & Output Contract

- Always verify tool/CLI results by checking exit codes (`0` = success) and expected output artifacts before claiming completion.
- For archive extraction, confirm all extracted paths remain strictly inside `target_dir` (`Path.is_relative_to`).

## References

- [llms.txt](llms.txt) — Machine-readable repository summary and verification entry points
- [README.md](README.md) / [README_de.md](README_de.md) / [README_es.md](README_es.md) — User documentation
- [EXPORTFORMAT.md](EXPORTFORMAT.md) — `explorerpro-workspace-v1` schema specification
- [SECURITY.md](SECURITY.md) — Security policy, non-elevation, and 48h response SLA
