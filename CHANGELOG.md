# Changelog / Änderungsprotokoll

Alle wesentlichen Änderungen an diesem Projekt werden hier dokumentiert.
Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).

## [Unreleased]

### Hinzugefügt / Added
- `TOMLHighlighter` in `src/modules/editor/syntax_highlighter.py`: Syntax-Highlighting für TOML-Dateien (Sections `[table]`/`[[array]]`, Keys, Strings, Zahlen, Booleans, Kommentare). `.toml` ist jetzt in `HIGHLIGHTERS` registriert.
- Schaltfläche „✔ Validieren" (F6) im Quick Editor: validiert JSON- und TOML-Dateien direkt aus dem Editor-Buffer (unsaved) und zeigt das Ergebnis im Output-Panel. Validierungslogik als testbare Pure Functions `_validate_json` / `_validate_toml` ohne Qt-Abhängigkeit.
- `tests/test_syntax_highlighter.py`: 15 Unit-Tests für TOMLHighlighter, JSON-Validierung und TOML-Validierung (inklusive graceful Fallback für Python <3.11 ohne tomli).
- `generate_store_screenshots.py` erzeugt reproduzierbar ein redigiertes Windows-Store-Screenshot-Set (`main-window.png`, `search.png`, `duplicates.png`, `sync.png`) aus Demo-Daten in temporären Verzeichnissen.
- `tests/test_store_screenshots.py` prüft den Screenshot-Generator als echten PNG-Smoke.
- `src/core/export_service.py`: `WorkspaceExporter`-Klasse exportiert den Arbeitsbereich als `explorerpro-workspace-v1.json`; absolute Pfade werden standardmäßig durch Referenz-IDs (`path_refs`) ersetzt; Settings werden aus dem GUI injiziert, nicht von der Festplatte gelesen.
- `tests/test_export_service.py`: 11 Unit-Tests für den Export-Service (leeres Verzeichnis, Pfad-Redaktion, Opt-in für absolute Pfade, Settings-Quellen-Trennung, Blacklist-Zählung, JSON-Schreibtest).
- Datei-Menü in `MainWindow`: Aktion „Arbeitsbereich exportieren…" (Ctrl+E) ruft `_export_workspace` auf.
- GitHub Actions Smoke-Test-Workflow für Python 3.10, 3.11 und 3.12.
- Repository-Privacy-Policy.
- `README_de.md` und `llms.txt` als deutschsprachige und maschinenlesbare Projektkontexte.
- PyInstaller-Spec und Build-Launcher für reproduzierbarere Windows-Builds.
- Windows-Store-Basis mit `store_package.json`, `STORE_LISTING.md`, `SUPPORT.md`,
  `WINDOWS_STORE_PREP.md`, Screenshot-Inventar und Store-Material-Test.
- Reproduzierbarer Desktop-Plattform-Smoke `tests/source_platform_smoke.py` für Linux und macOS.
- Das Vorschaufenster löst Windows-Verknüpfungen (`.lnk`) auf: Ordner-Links zeigen den Zielordnerinhalt, EXE-Links zeigen den Zielordner der Anwendung.

### Geändert / Changed
- README, Contributing Guide und Code of Conduct auf das aktuelle Repository `file-bricks/ExplorerPro` aktualisiert.
- Öffentliche private Kontaktadresse aus dem Code of Conduct entfernt.
- `.gitignore` um Test-, Coverage- und Cache-Artefakte erweitert.
- Community-Workflows und Testworkflow auf aktuelle GitHub-Actions-Major-Versionen aktualisiert.
- README mit Plattformplan, Exportformat und aktuellem Wartungsstand abgeglichen.
- Windows-Store-Doku nennt das dedizierte Screenshot-Set jetzt als erledigten Bestandteil der lokalen Store-Basis.
- Portierungsplan markiert die Windows-Store-Basis jetzt als erledigten P0-Schritt.
- Desktop-Öffnen nutzt jetzt plattformgerecht `open` auf macOS und `xdg-open` auf Linux.

### Behoben / Fixed
- Die Such-Checkbox "Im Inhalt" wird jetzt an den Index-Worker weitergereicht.
- Datei-/Ordner-Öffnen zeigt bei fehlender Systemzuordnung eine UI-Warnung statt still zu scheitern.
- macOS hing beim Datei-/Ordner-Öffnen nicht mehr fälschlich am Linux-Handler `xdg-open`.
- Windows-Verknüpfungsziele mit Umgebungsvariablen wie `%SystemRoot%` werden vor der Vorschau aufgelöst.
- Mojibake in README- und Workflow-Texten bereinigt.
- Die kompakte Haupt-Toolbar exponiert Navigation, Pfadfeld, Suche und Ansichtsmenü jetzt mit klaren Accessible Names, Descriptions und Tooltips statt nur über Pfeilsymbole und Placeholder.

## [1.0.0] - 2026-03-05

### Hinzugefügt / Added
- Erstveröffentlichung / Initial release
