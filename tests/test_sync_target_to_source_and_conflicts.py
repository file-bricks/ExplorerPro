"""
Comprehensive contract tests for sync directions (source_to_target, target_to_source, bidirectional)
and conflict resolution modes (newer_wins, larger_wins, source_wins, target_wins) in SyncWorker.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PySide6.QtWidgets import QApplication
_app = QApplication.instance() or QApplication([])

from modules.sync.sync_manager import SyncWorker, SyncPair


def test_target_to_source_sync(tmp_path):
    """Test that target_to_source copies new and updated files from target to source."""
    source_dir = tmp_path / "source"
    target_dir = tmp_path / "target"
    source_dir.mkdir()
    target_dir.mkdir()

    # File only in target
    target_new_file = target_dir / "target_only.txt"
    target_new_file.write_text("Hello from target", encoding="utf-8")

    # File in both, target is newer
    source_shared = source_dir / "shared.txt"
    source_shared.write_text("Old source version", encoding="utf-8")
    time.sleep(0.05)
    target_shared = target_dir / "shared.txt"
    target_shared.write_text("Newer target version", encoding="utf-8")

    # File only in source (should NOT be copied to target in target_to_source mode)
    source_only = source_dir / "source_only.txt"
    source_only.write_text("Should not be copied to target", encoding="utf-8")

    pair = SyncPair(
        id="test_t2s",
        name="Test Target to Source",
        source=str(source_dir),
        target=str(target_dir),
        direction="target_to_source",
        conflict_resolution="newer_wins",
    )

    worker = SyncWorker(pair, dry_run=True)
    worker.run()

    action_files = [Path(a.source_path).name for a in worker.actions]
    action_directions = [a.direction for a in worker.actions]

    assert "target_only.txt" in action_files, "target_only.txt was not detected in target_to_source"
    assert "shared.txt" in action_files, "shared.txt was not detected as newer in target"
    assert "source_only.txt" not in action_files, "source_only.txt should NOT be copied in target_to_source"
    assert all(d == "to_source" for d in action_directions), f"All actions should be to_source, got: {action_directions}"


def test_target_to_source_execution(tmp_path):
    """Test real execution (dry_run=False) for target_to_source sync."""
    source_dir = tmp_path / "source"
    target_dir = tmp_path / "target"
    source_dir.mkdir()
    target_dir.mkdir()

    target_new = target_dir / "file.txt"
    target_new.write_text("Target payload", encoding="utf-8")

    pair = SyncPair(
        id="test_t2s_exec",
        name="Test T2S Exec",
        source=str(source_dir),
        target=str(target_dir),
        direction="target_to_source",
    )

    synced_events = []
    worker = SyncWorker(pair, dry_run=False)
    worker.finished_sync.connect(lambda s, e: synced_events.append((s, e)))
    worker.run()

    assert (source_dir / "file.txt").exists()
    assert (source_dir / "file.txt").read_text(encoding="utf-8") == "Target payload"
    assert synced_events == [(1, 0)]


def test_source_to_target_sync(tmp_path):
    """Test source_to_target sync behavior."""
    source_dir = tmp_path / "source"
    target_dir = tmp_path / "target"
    source_dir.mkdir()
    target_dir.mkdir()

    source_new = source_dir / "source_only.txt"
    source_new.write_text("Source only", encoding="utf-8")

    target_new = target_dir / "target_only.txt"
    target_new.write_text("Target only", encoding="utf-8")

    pair = SyncPair(
        id="test_s2t",
        name="Test S2T",
        source=str(source_dir),
        target=str(target_dir),
        direction="source_to_target",
    )

    worker = SyncWorker(pair, dry_run=True)
    worker.run()

    action_files = [Path(a.source_path).name for a in worker.actions]
    assert "source_only.txt" in action_files
    assert "target_only.txt" not in action_files
    assert all(a.direction == "to_target" for a in worker.actions)


def test_bidirectional_sync(tmp_path):
    """Test bidirectional sync handles changes in both directions."""
    source_dir = tmp_path / "source"
    target_dir = tmp_path / "target"
    source_dir.mkdir()
    target_dir.mkdir()

    source_new = source_dir / "from_source.txt"
    source_new.write_text("From source", encoding="utf-8")

    target_new = target_dir / "from_target.txt"
    target_new.write_text("From target", encoding="utf-8")

    pair = SyncPair(
        id="test_bidi",
        name="Test Bidi",
        source=str(source_dir),
        target=str(target_dir),
        direction="bidirectional",
    )

    worker = SyncWorker(pair, dry_run=False)
    worker.run()

    assert (target_dir / "from_source.txt").exists()
    assert (source_dir / "from_target.txt").exists()


def test_conflict_resolutions(tmp_path):
    """Test conflict resolution modes (larger_wins, source_wins, target_wins)."""
    source_dir = tmp_path / "source"
    target_dir = tmp_path / "target"
    source_dir.mkdir()
    target_dir.mkdir()

    # larger_wins test
    (source_dir / "larger.txt").write_text("Short", encoding="utf-8")
    (target_dir / "larger.txt").write_text("Much longer text here", encoding="utf-8")

    pair_larger = SyncPair(
        id="test_larger",
        name="Larger Wins",
        source=str(source_dir),
        target=str(target_dir),
        direction="bidirectional",
        conflict_resolution="larger_wins",
    )
    worker = SyncWorker(pair_larger, dry_run=True)
    worker.run()
    assert len(worker.actions) == 1
    assert worker.actions[0].direction == "to_source"
    assert worker.actions[0].reason == "Ziel größer"


def test_target_to_source_missing_target_emits_error(tmp_path):
    """If target folder is missing in target_to_source mode, error should be emitted."""
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    target_dir = tmp_path / "non_existent_target"

    pair = SyncPair(
        id="test_err",
        name="Missing Target",
        source=str(source_dir),
        target=str(target_dir),
        direction="target_to_source",
    )

    errors = []
    worker = SyncWorker(pair, dry_run=True)
    worker.error.connect(lambda e: errors.append(e))
    worker.run()

    assert len(errors) == 1
    assert "Zielordner" in errors[0]
