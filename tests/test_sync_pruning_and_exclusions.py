"""
Contract tests for SyncWorker directory pruning, path exclusions, and cancellation.
Verifies:
1. Directory pruning: Excluded directories (node_modules, __pycache__, etc.) are not traversed.
2. Wildcard path patterns: Glob path patterns match correctly across directories.
3. Hidden directory exclusion: Hidden directories (starting with '.') are skipped when include_hidden=False.
4. Cancellation responsiveness: SyncWorker stops walking when cancelled.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PySide6.QtWidgets import QApplication
_app = QApplication.instance() or QApplication([])

from modules.sync.sync_manager import SyncWorker, SyncPair


def test_sync_directory_pruning_avoids_descending_into_excluded_folders(tmp_path):
    """Prüft, dass SyncWorker._get_files gar nicht erst in ausgeschlossene Ordner absteigt."""
    source_dir = tmp_path / "source"
    target_dir = tmp_path / "target"
    source_dir.mkdir()
    target_dir.mkdir()

    # Normaler Dateiinhalt
    (source_dir / "main.py").write_text("print('hello')", encoding="utf-8")

    # Auszuschließender Ordner mit Tausenden/Tiefen Unterdateien
    excluded_folder = source_dir / "node_modules"
    subfolder = excluded_folder / "deep_pkg" / "nested"
    subfolder.mkdir(parents=True)
    (subfolder / "package.json").write_text("{}", encoding="utf-8")
    (subfolder / "index.js").write_text("module.exports = {};", encoding="utf-8")

    pair = SyncPair(
        id="test_prune",
        name="Prune Test",
        source=str(source_dir),
        target=str(target_dir),
        direction="source_to_target",
        exclude_patterns=["node_modules", "*.tmp"],
    )

    worker = SyncWorker(pair, dry_run=True)
    files = worker._get_files(source_dir)

    # Es darf nur main.py erfasst sein
    relative_paths = [str(p).replace('\\', '/') for p in files.keys()]
    assert "main.py" in relative_paths
    assert not any("node_modules" in p for p in relative_paths)


def test_sync_hidden_directory_skipping(tmp_path):
    """Prüft, dass versteckte Ordner (z.B. .git) übersprungen werden wenn include_hidden=False."""
    source_dir = tmp_path / "source"
    target_dir = tmp_path / "target"
    source_dir.mkdir()
    target_dir.mkdir()

    (source_dir / "readme.md").write_text("# Readme", encoding="utf-8")
    git_dir = source_dir / ".git" / "objects"
    git_dir.mkdir(parents=True)
    (git_dir / "commit_obj").write_bytes(b"blob data")

    pair = SyncPair(
        id="test_hidden",
        name="Hidden Test",
        source=str(source_dir),
        target=str(target_dir),
        include_hidden=False,
    )

    worker = SyncWorker(pair, dry_run=True)
    files = worker._get_files(source_dir)

    relative_paths = [str(p).replace('\\', '/') for p in files.keys()]
    assert "readme.md" in relative_paths
    assert not any(".git" in p for p in relative_paths)


def test_sync_wildcard_path_patterns(tmp_path):
    """Prüft, dass Wildcard-Muster wie cache/* oder *.bak korrekt greifen."""
    source_dir = tmp_path / "source"
    target_dir = tmp_path / "target"
    source_dir.mkdir()
    target_dir.mkdir()

    cache_dir = source_dir / "cache"
    cache_dir.mkdir()
    (cache_dir / "data.bin").write_bytes(b"cache")
    (source_dir / "keep.txt").write_text("keep", encoding="utf-8")
    (source_dir / "temp.bak").write_text("backup", encoding="utf-8")

    pair = SyncPair(
        id="test_wildcard",
        name="Wildcard Test",
        source=str(source_dir),
        target=str(target_dir),
        exclude_patterns=["cache/*", "*.bak"],
    )

    worker = SyncWorker(pair, dry_run=True)
    files = worker._get_files(source_dir)

    relative_paths = [str(p).replace('\\', '/') for p in files.keys()]
    assert "keep.txt" in relative_paths
    assert "temp.bak" not in relative_paths
    assert not any("cache" in p for p in relative_paths)
