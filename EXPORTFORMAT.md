# Austauschformat ExplorerPro

Stand: 2026-05-29

Dieses Dokument beschreibt das geplante, noch nicht implementierte Austauschformat für spätere Plattformwechsel und einen möglichen Web/PWA-Companion. Es ist kein Cloud-Sync-Protokoll.

## Format

Name: `explorerpro-workspace-v1.json`

Zweck:

- Einstellungen und redigierte Arbeitskontexte zwischen ExplorerPro-Installationen übertragen.
- Such-, Duplikat- und Datenschutzberichte in einem späteren Companion lesbar machen.
- Keine Dateien, keine Binärdaten und keine vollständigen privaten Indizes transportieren.

## Datenschutzgrenze

Ein Export darf standardmäßig keine Datei-Inhalte enthalten. Absolute Pfade sollen nur nach bewusster Nutzerentscheidung exportiert werden; der Standard ist eine gekürzte oder relative Referenz.

Nicht exportieren:

- Dokumentinhalte, PDF-Text, Bilder oder Quellcodeinhalte.
- Private Datenbanken wie `fileindex.db`.
- Vollständige Clipboard-Inhalte.
- Passwörter, Tokens, `.env`-Dateien, private Schlüssel oder lokale Secrets.
- Automatische Cloud-Ziele oder Server-Zugangsdaten.

## Strukturentwurf

```json
{
  "schema": "explorerpro-workspace-v1",
  "created_at": "2026-05-29T00:00:00+02:00",
  "app": {
    "name": "ExplorerPro",
    "version": "1.0.0",
    "platform": "windows"
  },
  "export_options": {
    "include_absolute_paths": false,
    "include_hashes": true,
    "include_reports": true,
    "redaction": "default"
  },
  "settings": {
    "appearance": {},
    "preview": {},
    "index": {}
  },
  "apps": [
    {
      "name": "VS Code",
      "category": "Entwicklung",
      "path_ref": "app-1",
      "arguments": ""
    }
  ],
  "prompts": [],
  "sync_profiles": [
    {
      "name": "Projekt-Backup",
      "direction": "source_to_target",
      "source_ref": "path-1",
      "target_ref": "path-2",
      "exclude_patterns": ["*.tmp", "*.bak"],
      "last_sync": null
    }
  ],
  "privacy": {
    "enabled_patterns": ["iban", "email"],
    "custom_terms_count": 0,
    "custom_terms_exported": false
  },
  "reports": {
    "searches": [],
    "duplicates": [],
    "privacy_alerts": []
  },
  "path_refs": [
    {
      "id": "path-1",
      "kind": "folder",
      "display": "Projektordner",
      "relative_hint": "project",
      "absolute_path": null
    }
  ]
}
```

## Companion-Usecase

Ein Web/PWA-Companion darf dieses Format nur lokal im Browser öffnen und anzeigen. Er soll redigierte Berichte, Prompt-Listen, Sync-Profile und App-Listen lesbar machen, aber keine Desktop-Dateien synchronisieren und keine Dateisystem-Aktionen ausführen.

## Kompatibilität

- Neue Felder müssen optional bleiben.
- Unbekannte Felder werden ignoriert.
- `schema` bleibt stabil für Version 1.
- Exportdateien werden UTF-8 ohne BOM geschrieben.

