import json
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

APP_VERSION = "1.0.0"
SCHEMA = "explorerpro-workspace-v1"

# Nur Muster die standardmäßig aktiv sind (default=True in privacy_monitor.py)
BUILTIN_DEFAULT_PATTERNS = ["iban", "email"]
PRIVACY_PATTERN_KEYS = (
    "iban",
    "email",
    "phone_de",
    "creditcard",
    "ssn_de",
    "password_hint",
)



class WorkspaceExporter:
    """Exportiert den ExplorerPro-Arbeitsbereich als portables JSON."""

    CONFIG_DIR = Path.home() / ".explorerpro"

    def __init__(self, config_dir: Path | None = None, settings: dict | None = None):
        self._dir = config_dir or self.CONFIG_DIR
        # Settings werden aus dem GUI injiziert (SettingsManager.instance()._settings),
        # weil settings.json an einem anderen Ort liegt als ~/.explorerpro/
        self._settings = settings or {}

    def build_export(
        self,
        include_absolute_paths: bool = False,
        include_sensitive_content: bool = False,
    ) -> dict:
        path_refs: list[dict] = []
        apps = self._read_apps(
            path_refs, include_absolute_paths, include_sensitive_content
        )
        sync_profiles = self._read_sync_profiles(path_refs, include_absolute_paths)
        return {
            "schema": SCHEMA,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "app": {
                "name": "ExplorerPro",
                "version": APP_VERSION,
                "platform": platform.system().lower(),
            },
            "export_options": {
                "include_absolute_paths": include_absolute_paths,
                "include_sensitive_content": include_sensitive_content,
                "include_hashes": False,
                "include_reports": False,
                "redaction": "default",
            },
            "settings": self._extract_safe_settings(),
            "apps": apps,
            "prompts": self._read_prompts(include_sensitive_content),
            "sync_profiles": sync_profiles,
            "privacy": self._read_privacy(),
            "reports": {"searches": [], "duplicates": [], "privacy_alerts": []},
            "path_refs": path_refs,
        }

    def save_export(
        self,
        output_path: Path,
        include_absolute_paths: bool = False,
        include_sensitive_content: bool = False,
    ) -> None:
        data = self.build_export(
            include_absolute_paths=include_absolute_paths,
            include_sensitive_content=include_sensitive_content,
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)

    # --- private helpers ---

    def _load_json(self, filename: str) -> Any:
        path = self._dir / filename
        if not path.exists():
            return []
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, json.JSONDecodeError):
            return []

    def _make_ref(self, refs: list, path_str: str, kind: str, display: str) -> str:
        ref_id = f"path-{len(refs) + 1}"
        refs.append({
            "id": ref_id,
            "kind": kind,
            "display": display,
            "relative_hint": kind,
            "absolute_path": None,
        })
        return ref_id

    def _extract_safe_settings(self) -> dict:
        return {
            "appearance": self._settings.get("appearance", {}),
            "preview": self._settings.get("preview", {}),
            "index": {
                k: v
                for k, v in self._settings.get("index", {}).items()
                if k not in ("watched_folders",)
            },
        }

    def _read_apps(
        self,
        path_refs: list,
        include_absolute_paths: bool,
        include_sensitive_content: bool,
    ) -> list:
        raw = self._load_json("apps.json")
        if not isinstance(raw, list):
            return []

        result = []
        for app in raw:
            if not isinstance(app, dict):
                continue
            name = app.get("name", "")
            path_str = app.get("path", "")
            entry: dict = {
                "name": name,
                "category": app.get("category", ""),
            }
            if include_sensitive_content:
                entry["arguments"] = app.get("arguments", "")
            if include_absolute_paths:
                entry["path"] = path_str
            elif path_str:
                entry["path_ref"] = self._make_ref(
                    path_refs, path_str, "app", name or Path(path_str).name
                )
            result.append(entry)
        return result

    def _read_prompts(self, include_sensitive_content: bool) -> list:
        raw = self._load_json("prompts.json")
        if not isinstance(raw, list):
            return []

        result = []
        for prompt in raw:
            if not isinstance(prompt, dict):
                continue
            entry = {
                "id": prompt.get("id", ""),
                "title": prompt.get("title", ""),
                "category": prompt.get("category", ""),
                "tags": prompt.get("tags", []),
                "favorite": prompt.get("favorite", False),
            }
            if include_sensitive_content:
                entry["content"] = prompt.get("content", "")
            result.append(entry)
        return result

    def _read_sync_profiles(self, path_refs: list, include_absolute_paths: bool) -> list:
        raw = self._load_json("sync.json")
        if not isinstance(raw, list):
            return []
        result = []
        for s in raw:
            if not isinstance(s, dict):
                continue
            name = s.get("name", "")
            entry: dict = {
                "name": name,
                "direction": s.get("direction", "source_to_target"),
                "exclude_patterns": s.get("exclude_patterns", []),
                "last_sync": s.get("last_sync", None),
            }
            if include_absolute_paths:
                entry["source"] = s.get("source", "")
                entry["target"] = s.get("target", "")
            else:
                src = s.get("source", "")
                tgt = s.get("target", "")
                if src:
                    entry["source_ref"] = self._make_ref(
                        path_refs, src, "folder", f"{name} (Quelle)"
                    )
                if tgt:
                    entry["target_ref"] = self._make_ref(
                        path_refs, tgt, "folder", f"{name} (Ziel)"
                    )
            result.append(entry)
        return result

    def _read_privacy(self) -> dict:
        blacklist_path = self._dir / "blacklist.json"
        custom_count = 0
        if blacklist_path.exists():
            try:
                bl = json.loads(blacklist_path.read_text(encoding="utf-8"))
                if isinstance(bl, list):
                    custom_count = len(bl)
                elif isinstance(bl, dict):
                    custom_count = len(bl.get("blacklist", []))
            except (OSError, json.JSONDecodeError):
                custom_count = 0

        enabled_patterns = BUILTIN_DEFAULT_PATTERNS
        privacy_config = self._load_json("privacy_config.json")
        if isinstance(privacy_config, dict):
            patterns = privacy_config.get("patterns")
            if isinstance(patterns, dict):
                enabled_patterns = [
                    key
                    for key in PRIVACY_PATTERN_KEYS
                    if patterns.get(key) is True
                ]

        return {
            "enabled_patterns": enabled_patterns,
            "custom_terms_count": custom_count,
            "custom_terms_exported": False,
        }
