"""Tests für WorkspaceExporter (src/core/export_service.py)"""
import json
import sys
from pathlib import Path

import pytest

# Damit der Import ohne installiertes Paket funktioniert
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.export_service import WorkspaceExporter, SCHEMA, BUILTIN_DEFAULT_PATTERNS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def empty_dir(tmp_path):
    """Leeres config-Verzeichnis — keine Konfig-Dateien vorhanden."""
    return tmp_path


@pytest.fixture()
def populated_dir(tmp_path):
    """Config-Verzeichnis mit apps, prompts, sync, blacklist."""
    apps = [
        {"name": "VS Code", "path": "/usr/bin/code", "category": "Dev", "arguments": "--token top-secret"},
        {"name": "Browser", "path": "/usr/bin/firefox", "category": "Web", "arguments": ""},
    ]
    prompts = [
        {
            "id": "p1", "title": "Refactor", "content": "Refactoriere den Code",
            "category": "Dev", "tags": ["python"], "favorite": True, "use_count": 3,
        }
    ]
    sync = [
        {
            "id": "s1", "name": "Backup", "source": "/home/user/docs",
            "target": "/mnt/backup", "direction": "source_to_target",
            "exclude_patterns": ["*.tmp"], "last_sync": "2026-01-01T00:00:00+00:00",
            "enabled": True,
        }
    ]
    blacklist = ["secret123", "password456"]

    (tmp_path / "apps.json").write_text(json.dumps(apps), encoding="utf-8")
    (tmp_path / "prompts.json").write_text(json.dumps(prompts), encoding="utf-8")
    (tmp_path / "sync.json").write_text(json.dumps(sync), encoding="utf-8")
    (tmp_path / "blacklist.json").write_text(json.dumps(blacklist), encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_schema_field(empty_dir):
    exp = WorkspaceExporter(config_dir=empty_dir)
    data = exp.build_export()
    assert data["schema"] == SCHEMA


def test_empty_config_dir(empty_dir):
    """Fehlende JSON-Dateien dürfen keinen Fehler auslösen."""
    exp = WorkspaceExporter(config_dir=empty_dir)
    data = exp.build_export()
    assert data["apps"] == []
    assert data["prompts"] == []
    assert data["sync_profiles"] == []
    assert data["path_refs"] == []


def test_no_absolute_paths_by_default(populated_dir):
    """Standardexport enthält keine absoluten Pfade in apps/sync."""
    exp = WorkspaceExporter(config_dir=populated_dir)
    data = exp.build_export()

    for app in data["apps"]:
        assert "path" not in app, f"App enthält absoluten Pfad: {app}"

    for profile in data["sync_profiles"]:
        assert "source" not in profile
        assert "target" not in profile


def test_path_refs_populated(populated_dir):
    """Ohne absolute Pfade müssen path_refs befüllt sein."""
    exp = WorkspaceExporter(config_dir=populated_dir)
    data = exp.build_export()
    # 2 Apps + 1 Sync (source + target) = 4 Refs
    assert len(data["path_refs"]) == 4
    for ref in data["path_refs"]:
        assert ref["id"].startswith("path-")
        assert ref["absolute_path"] is None  # privacy-safe


def test_absolute_paths_opt_in(populated_dir):
    """Mit include_absolute_paths=True erscheinen echte Pfade."""
    exp = WorkspaceExporter(config_dir=populated_dir)
    data = exp.build_export(include_absolute_paths=True)

    paths = [a["path"] for a in data["apps"]]
    assert "/usr/bin/code" in paths
    assert "/usr/bin/firefox" in paths

    sources = [s["source"] for s in data["sync_profiles"]]
    assert "/home/user/docs" in sources

    assert data["path_refs"] == []


def test_watched_folders_not_exported(populated_dir):
    """watched_folders aus den Settings dürfen nicht im Export erscheinen."""
    settings = {
        "index": {
            "max_file_size": 10,
            "watched_folders": ["/home/user"],
        },
        "appearance": {"theme": "dark"},
    }
    exp = WorkspaceExporter(config_dir=populated_dir, settings=settings)
    data = exp.build_export()
    assert "watched_folders" not in data["settings"]["index"]
    assert data["settings"]["index"]["max_file_size"] == 10


def test_sensitive_content_is_omitted_by_default(populated_dir):
    """Standardexport darf keine App-Argumente oder Prompt-Inhalte enthalten."""
    exp = WorkspaceExporter(config_dir=populated_dir)
    data = exp.build_export()
    app = data["apps"][0]
    prompt = data["prompts"][0]

    assert app["name"] == "VS Code"
    assert "arguments" not in app
    assert prompt["title"] == "Refactor"
    assert "content" not in prompt
    assert data["export_options"]["include_sensitive_content"] is False


def test_sensitive_content_requires_explicit_opt_in(populated_dir):
    exp = WorkspaceExporter(config_dir=populated_dir)
    data = exp.build_export(include_sensitive_content=True)

    assert data["apps"][0]["arguments"] == "--token top-secret"
    assert data["prompts"][0]["content"] == "Refactoriere den Code"
    assert data["export_options"]["include_sensitive_content"] is True


def test_save_export_writes_valid_json(populated_dir, tmp_path):
    """save_export schreibt eine gültige, parsbare JSON-Datei."""
    out = tmp_path / "workspace.json"
    exp = WorkspaceExporter(config_dir=populated_dir)
    exp.save_export(out)
    assert out.exists()
    parsed = json.loads(out.read_text(encoding="utf-8"))
    assert parsed["schema"] == SCHEMA


def test_settings_source_decoupled(populated_dir):
    """Settings kommen aus dem injizierten dict, nicht aus config_dir."""
    injected = {
        "appearance": {"theme": "light"},
        "preview": {"max_size_mb": 5},
        "index": {"extensions": [".py"]},
    }
    exp = WorkspaceExporter(config_dir=populated_dir, settings=injected)
    data = exp.build_export()
    assert data["settings"]["appearance"]["theme"] == "light"
    assert data["settings"]["preview"]["max_size_mb"] == 5
    assert data["settings"]["index"]["extensions"] == [".py"]


def test_blacklist_count_only(populated_dir):
    """Blacklist-Inhalte werden NICHT exportiert, nur die Anzahl."""
    exp = WorkspaceExporter(config_dir=populated_dir)
    data = exp.build_export()
    privacy = data["privacy"]
    assert privacy["custom_terms_count"] == 2
    assert privacy["custom_terms_exported"] is False
    assert "custom_terms" not in privacy


def test_privacy_patterns_follow_valid_config_and_ignore_unknown_keys(populated_dir):
    (populated_dir / "privacy_config.json").write_text(
        json.dumps({"patterns": {"email": False, "creditcard": True, "unknown": True}}),
        encoding="utf-8",
    )

    data = WorkspaceExporter(config_dir=populated_dir).build_export()

    assert data["privacy"]["enabled_patterns"] == ["creditcard"]


def test_invalid_privacy_config_uses_defaults(populated_dir):
    (populated_dir / "privacy_config.json").write_text("{ungültig", encoding="utf-8")

    data = WorkspaceExporter(config_dir=populated_dir).build_export()

    assert data["privacy"]["enabled_patterns"] == BUILTIN_DEFAULT_PATTERNS


def test_builtin_default_patterns():
    """Nur iban und email sind standardmäßig aktiv."""
    assert set(BUILTIN_DEFAULT_PATTERNS) == {"iban", "email"}
