# Austauschformat ExplorerPro

Stand: 2026-07-22

Dieses Dokument beschreibt den implementierten Austauschvertrag `explorerpro-workspace-v1` für den bewussten, lokalen Datenaustausch. Es ist kein Cloud-Sync-Protokoll.

## Format

Name: `explorerpro-workspace-v1.json`

Zweck:

- Einstellungen und redigierte Arbeitskontexte zwischen ExplorerPro-Installationen übertragen.
- Redigierte Such-, Duplikat- und Datenschutzberichte in einem späteren Werkzeug lesbar halten.
- Keine Dateien, Binärdaten oder vollständigen privaten Indizes transportieren.

## Datenschutzgrenze

Der Standardexport enthält keine Datei-Inhalte, Hashes, absoluten Pfade, App-Argumente oder Prompt-Inhalte. App-Argumente können Tokens oder andere Geheimnisse enthalten; Prompt-Inhalte können private Daten enthalten. Beide Felder werden deshalb nur über das separate, programmgesteuerte Opt-in `include_sensitive_content=True` exportiert. Absolute Pfade benötigen unabhängig davon `include_absolute_paths=True`.

Die aktuelle GUI nutzt ausschließlich den sicheren Standard. Für die sensiblen Opt-ins gibt es bewusst keinen GUI-Schalter. Nutzerdefinierte Bezeichnungen wie App-, Prompt- oder Sync-Profilnamen bleiben als Metadaten enthalten und müssen vor einer Weitergabe geprüft werden.

Nicht exportieren:

- Dokumentinhalte, PDF-Text, Bilder oder Quellcodeinhalte.
- Private Datenbanken wie `explorer.db`.
- Vollständige Clipboard-Inhalte.
- Passwörter, Tokens, `.env`-Dateien, private Schlüssel oder lokale Secrets.
- Automatische Cloud-Ziele oder Server-Zugangsdaten.

## Struktur (Implementierungsvertrag)

```json
{
  "schema": "explorerpro-workspace-v1",
  "created_at": "2026-07-22T00:00:00+00:00",
  "app": {
    "name": "ExplorerPro",
    "version": "1.0.0",
    "platform": "windows"
  },
  "export_options": {
    "include_absolute_paths": false,
    "include_sensitive_content": false,
    "include_hashes": false,
    "include_reports": false,
    "redaction": "default"
  },
  "settings": {
    "appearance": {},
    "preview": {},
    "index": {}
  },
  "apps": [
    {
      "name": "Editor",
      "category": "Entwicklung",
      "path_ref": "path-1"
    }
  ],
  "prompts": [
    {
      "id": "prompt-1",
      "title": "Beispiel",
      "category": "Allgemein",
      "tags": [],
      "favorite": false
    }
  ],
  "sync_profiles": [
    {
      "name": "Projekt-Backup",
      "direction": "source_to_target",
      "source_ref": "path-2",
      "target_ref": "path-3",
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
      "kind": "app",
      "display": "Editor",
      "relative_hint": "app",
      "absolute_path": null
    }
  ]
}
```

## Companion-Entscheidung

Am 2026-07-22 wurde für eine separate Web/PWA-Anwendung ein **No-Go** beschlossen: Es ist kein eigenständiger, belegter Usecase vorhanden, der den zusätzlichen Browser-Code und seine Privacy-Angriffsfläche rechtfertigt. Der JSON-Vertrag bleibt für lokale, manuell gewählte Werkzeuge und spätere Neubewertung erhalten. Weiterhin ausgeschlossen sind Upload, Server, Dateisystemaktionen und automatische Cloud-Synchronisierung.

## Kompatibilität

- Neue Felder müssen optional bleiben.
- Unbekannte Felder werden ignoriert.
- `schema` bleibt für Version 1 stabil.
- Exportdateien werden als UTF-8 ohne BOM geschrieben.
- `include_sensitive_content` und `include_absolute_paths` sind voneinander unabhängige Opt-ins.
