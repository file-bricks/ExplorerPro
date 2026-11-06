#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_atomic_io_suite.py - Hermetische Test-Suite für atomic_io und Persistenzhärtung in ExplorerPro.
"""

from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

from core.atomic_io import (
    atomic_write_bytes,
    atomic_write_json,
    atomic_write_text,
)
from core.export_service import WorkspaceExporter
from core.settings_manager import SettingsManager


def test_atomic_write_bytes_success(tmp_path: Path):
    target = tmp_path / "data.bin"
    payload = b"\x00\x01\x02\xfe\xff" * 1024
    result = atomic_write_bytes(target, payload)

    assert result == target.resolve()
    assert target.is_file()
    assert target.read_bytes() == payload
    # Sicherstellen, dass keine temporären Staging-Dateien zurückgeblieben sind
    assert not list(tmp_path.glob(".*.tmp.*"))


def test_atomic_write_text_success(tmp_path: Path):
    target = tmp_path / "notes.txt"
    sample_content = "ExplorerPro High-End Durability Test\nLine 2 mit Umlauten: äöüß\n"
    result = atomic_write_text(target, sample_content, encoding="utf-8")

    assert result == target.resolve()
    assert target.is_file()
    assert target.read_text(encoding="utf-8") == sample_content
    assert not list(tmp_path.glob(".*.tmp.*"))


def test_atomic_write_json_success(tmp_path: Path):
    target = tmp_path / "config.json"
    data = {
        "version": "1.8.0",
        "active": True,
        "features": ["archive", "diff", "atomic_io"],
        "count": 42,
    }
    result = atomic_write_json(target, data, indent=2, ensure_ascii=False)

    assert result == target.resolve()
    assert target.is_file()
    loaded = json.loads(target.read_text(encoding="utf-8"))
    assert loaded == data
    assert not list(tmp_path.glob(".*.tmp.*"))


def test_atomic_write_creates_parent_directories(tmp_path: Path):
    nested_target = tmp_path / "sub" / "deep" / "folder" / "atomic.txt"
    content = "Auto-creation of parents verified"
    result = atomic_write_text(nested_target, content)

    assert result.is_file()
    assert nested_target.read_text(encoding="utf-8") == content


def test_atomic_write_preserves_mode(tmp_path: Path):
    target = tmp_path / "script.sh"
    target.write_text("#!/bin/sh\necho hello\n", encoding="utf-8")
    original_mode = stat.S_IMODE(target.stat().st_mode)

    updated_content = "#!/bin/sh\necho updated\n"
    atomic_write_text(target, updated_content, preserve_mode=True)

    assert target.read_text(encoding="utf-8") == updated_content
    assert stat.S_IMODE(target.stat().st_mode) == original_mode


def test_atomic_write_failure_cleans_up_temp_and_preserves_original(tmp_path: Path, monkeypatch):
    target = tmp_path / "critical_data.txt"
    original_content = "Original uncorrupted content"
    target.write_text(original_content, encoding="utf-8")

    def fail_replace(src, dst):
        raise OSError("Simulated atomic replace failure")

    monkeypatch.setattr("core.atomic_io.os.replace", fail_replace)

    with pytest.raises(OSError, match="Simulated atomic replace failure"):
        atomic_write_text(target, "New corrupting content")

    # Original muss unberührt sein
    assert target.read_text(encoding="utf-8") == original_content
    # Keine verwaisten Temp-Dateien
    assert not list(tmp_path.glob(".*.tmp.*"))


def test_atomic_write_json_invalid_serialization_cleans_up(tmp_path: Path):
    target = tmp_path / "bad.json"
    target.write_text("{\"keep\": true}", encoding="utf-8")

    class Unserializable:
        pass

    bad_data = {"key": Unserializable()}

    with pytest.raises(TypeError):
        atomic_write_json(target, bad_data)

    assert target.read_text(encoding="utf-8") == "{\"keep\": true}"
    assert not list(tmp_path.glob(".*.tmp.*"))


def test_settings_manager_atomic_save(tmp_path: Path):
    cfg_file = tmp_path / "settings.json"
    sm = SettingsManager()
    sm._config_path = str(cfg_file)
    sm.set("general", "theme", "dark_pro")
    sm.save()

    assert cfg_file.is_file()
    loaded = json.loads(cfg_file.read_text(encoding="utf-8"))
    assert loaded["general"]["theme"] == "dark_pro"
    assert not list(tmp_path.glob(".*.tmp.*"))


def test_workspace_exporter_atomic_save(tmp_path: Path):
    exporter = WorkspaceExporter(config_dir=tmp_path)
    out_file = tmp_path / "exports" / "workspace.json"
    exporter.save_export(out_file)

    assert out_file.is_file()
    loaded = json.loads(out_file.read_text(encoding="utf-8"))
    assert loaded["schema"] == "explorerpro-workspace-v1"
    assert loaded["app"]["name"] == "ExplorerPro"
    assert not list((tmp_path / "exports").glob(".*.tmp.*"))
