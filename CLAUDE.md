---
name: ExplorerPro
type: project-docs
profile: STANDARD
version: 1.0.3
created: 2026-07-22
updated: 2026-08-24
reason_last_change: "Path B Marketing & Discoverability: Dual Mermaid Diagrams, Showcase Gallery, Capability & Sibling Matrix, Contract Tests"
last_verified: 2026-08-24
author: Lukas Geiger
anthropic_compatible: true
description: |
  Projektspezifische Leitlinien und Instruktionen für AI-Coding-Agenten in ExplorerPro.
  Primäre Zielgruppe: Claude Code, Antigravity/Gemini und Codex. Weiterleitung via AGENTS.md.
---

# CLAUDE.md — Instructions für AI Coding Agents

> **Für LLM-Agenten (Claude Code, Gemini/Antigravity, Codex, Cursor, Cline, Aider, Copilot).**
> Diese Datei wird von Claude Code und kompatiblen Agenten **automatisch** geladen.
> Andere Agenten lesen zuerst `AGENTS.md` → Weiterleitung hierher.
>
> **YAML-Header oben** ist maschinenlesbar und validierbar.
> Bei Änderungen an der Doku: `updated` und `last_verified` nachziehen.

---

## Projekt

**ExplorerPro Suite** — Lokaler, datenschutzorientierter Multi-Tab-Dateimanager und Power-User-Explorer mit integrierter FTS5-Suche, Duplikaterkennung, Datei-Vorschau, Prompt-Manager und Ordnersynchronisation.

**Pfad:** `C:\_Local_DEV\repos\ExplorerPro`
**OneDrive-Spiegel:** `C:\Users\lukas\OneDrive\.TOPICS\.SOFTWARE\DATA\REL-PUB_ExplorerPro_SUITE`
**Repository:** `https://github.com/file-bricks/ExplorerPro` (Branch: `master`)
**Sprache/Stack:** Python 3.10–3.12, PySide6 (Qt 6), SQLite (FTS5), PyMuPDF (fitz)
**Lizenz:** AGPL-3.0
**Store-Status:** Live im Microsoft Store (Store-ID: `9P0X52WSHZ3Q`, Identity: `Geiger.ExplorerPro`)

## Rolle & Stil

Arbeite als **Senior Python/Qt-Entwickler und Desktop-Architekt** mit Fokus auf Robustheit, Offline-First-Sicherheit, Thread-Safety und Barrierefreiheit.

**Kommunikation:**
- Sprache: Deutsch (Code, Docstrings und Identifier bleiben englisch)
- End-User-Texte: Echte deutsche Umlaute (`ä`, `ö`, `ü`, `ß`), keine Umschreibungen
- Stil: präzise, faktenbasiert, direkt

## Einstieg (Quick Commands)

```bash
# Tests ausführen
python -m pytest -q

# Syntax- und Bytecode-Kompilierung
python -m compileall -q src tests manage_translations.py translator.py

# Übersetzungs-Scanner und Status
python manage_translations.py .

# Store-Readiness-Preflight prüfen
python scripts/check_store_readiness.py

# Anwendung starten
python src/main.py
```

## Hard Rules (non-negotiable)

- **100% Offline & Zero-Egress:** Keine Netzwerkzugriffe, Telemetrie oder externe Cloud-Uploads in der Laufzeitlogik.
- **Plan-D-Repository-Disziplin:** Quellcode, Tests und Git-Operationen ausschließlich in `C:\_Local_DEV\repos\ExplorerPro`. Keine isolierten Codeänderungen im OneDrive-Spiegel ohne Synchronisation.
- **Non-Elevation:** Die Anwendung läuft strikt im User-Mode und verlangt niemals Administrator-Rechte.
- **Destructive Safety:** Dateioperationen (Löschen, Verschieben, Umbenennen) erfordern Bestätigungsdialoge oder sicheres Recycling; kein blindes `shutil.rmtree` ohne Nutzerbestätigung.
- **Thread-Safety in Qt:** Schwere Operationen (Dateisuche, Hashing für Duplikate, Ordnerscan, PDF-Rendering) laufen in dedizierten `QThread`-Workern und kommunizieren ausschließlich per Qt Signals/Slots mit der GUI.
- **IMMER vor Push:** `git status`, Pytest-Gesamtsuite und `manage_translations.py` prüfen.

## Projekt-Struktur

```
ExplorerPro/
├── src/
│   ├── main.py                  # Anwendungs-Einstiegspunkt, Theme-Initialisierung
│   ├── app.py                   # App-Lifecycle und Komponentenverdrahtung
│   ├── core/                    # Konfiguration, SettingsManager, ThemeEngine, AppPaths
│   ├── gui/                     # PySide6 GUI-Komponenten
│   │   ├── main_window.py       # Hauptfenster, Toolbar, Menüleiste, View-Umschaltung
│   │   ├── file_browser.py      # Multi-Tab QTableView mit _DnDTableView und Kontextmenüs
│   │   ├── settings_dialog.py   # Einstellungsdialog (5 Tabs)
│   │   ├── preview/             # Multi-Format-Vorschaupanel (Text, PDF, Bilder, Markdown)
│   │   ├── prompt_panel.py      # Prompt-Manager mit Variablen-Interpolation
│   │   ├── privacy_panel.py     # Datenschutz-Monitor und Blacklist-Verwaltung
│   │   ├── sync_panel.py        # Ordnersynchronisations-Panel
│   │   └── editor_panel.py      # Integrierter Quelltext-Editor
│   └── modules/
│       ├── indexer/             # SQLite/FTS5-Suchindex und Duplikaterkennung
│       └── sync/                # Synchronisations-Engine und Datei-Worker
├── locales/
│   └── translations.json        # 6-Sprachen-Übersetzungskatalog (DE, EN, ES, ZH, JA, RU)
├── scripts/
│   └── check_store_readiness.py # Store-Preflight-Prüfung
├── store_assets/                # MSIX-Icons (Square44, Square150, Wide310, Square310, StoreLogo)
├── tests/                       # Pytest-Testsuite (Unit-, UI-, A11y- und Smoke-Tests)
├── translator.py                # TranslationSystem v1/v2 mit Fallback-Kette
├── manage_translations.py       # Auto-Scanner für GUI-Strings
├── pyproject.toml               # Projekt- und Tooling-Konfiguration
├── store_package.json           # Microsoft Store Metadaten
├── README.md / README_de.md     # Zweisprachige Dokumentation
└── llms.txt                     # LLM-Einstiegspunkt
```

## Wichtige Dateien

| Datei | Zweck |
|---|---|
| [`CLAUDE.md`](./CLAUDE.md) | Kanonische Instruktionen für AI-Coding-Agenten |
| [`AGENTS.md`](./AGENTS.md) | Universal-Redirect für Multi-Agent-Systeme |
| [`ROADMAP.md`](./ROADMAP.md) | Architektur- und Feature-Roadmap |
| [`AUFGABEN.txt`](./AUFGABEN.txt) | Aufgabenliste und Statusverfolgung |
| [`CHANGELOG.md`](./CHANGELOG.md) | Versionschronik |
| [`EXPORTFORMAT.md`](./EXPORTFORMAT.md) | Spezifikation `explorerpro-workspace-v1` |
| [`STORE_LISTING.md`](./STORE_LISTING.md) | Microsoft Store Beschreibungstexte (DE/EN) |
| [`store_package.json`](./store_package.json) | Store-Manifest und Paketkonfiguration |
| [`SECURITY.md`](./SECURITY.md) | Sicherheitsrichtlinie und Offline-Garantien |
| [`llms.txt`](./llms.txt) | LLM-Übersicht und Kurzbeschreibung |

## Domain-Kontext

- **ExplorerPro** richtet sich an Power-User, die eine schnelle, datenschutzkonforme Desktop-Alternative zu Standard-Dateimanagern suchen.
- **FTS5-Indexierung:** Verwendet SQLite mit FTS5 für Volltext- und Metadatensuche auf lokalen Verzeichnissen.
- **Duplikaterkennung:** Schneller 2-Phasen-Algorithmus (Größen-Gruppierung gefolgt von partiellem und vollständigem Hash-Vergleich) mit konfigurierbarem Auto-Select.
- **Vorschau-Engine:** Fallback-geschützt — PyMuPDF (`fitz`) für PDFs, Pillow/Qt für Bilder, SyntaxHighlighter für Text/Code, Hex-Dump für Binärdateien.
- **Lokalisierung:** 6 Zielsprachen (Deutsch, Englisch, Spanisch, Chinesisch, Japanisch, Russisch). Neue GUI-Strings werden über `manage_translations.py` synchronisiert.

---

<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä ß -->
