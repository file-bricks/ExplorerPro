# Changelog / Änderungsprotokoll

Alle wesentlichen Änderungen an diesem Projekt werden hier dokumentiert.
Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).

## [Unreleased]

### Hinzugefügt / Added
- **Software-Originalicons in Dateiliste und Sidebar** (`src/core/file_icon_helper.py`):
  - Neue Hilfsfunktion `get_file_icon(path: str) -> QIcon` mit dreistufiger Fallback-Kette: (1) echtes Shell-/Typ-Icon via `QFileIconProvider`, (2) generisches Ordner-Icon, (3) generisches Datei-Icon — liefert nie `QIcon.isNull()`.
  - Auf Windows werden über `QFileIconProvider` die echten Shell-Icons geliefert (Programm-Icons für `.exe`, zugewiesene Programm-Icons für `.docx`, `.psd` usw.).
  - `src/gui/sidebar/sidebar_main.py` (`TreePanel`): refactored auf `get_file_icon()` — direkter `QFileIconProvider`-Zustand (`_icon_provider`-Attribut) entfernt, zentraler Helper mit Fallback genutzt.
  - `src/gui/browser/file_browser.py`: explizites `setIconSize(QSize(16, 16))` gesetzt — `QFileSystemModel` liefert System-Icons über seinen eingebauten Provider, die sichtbare Größe ist jetzt explizit konfiguriert.
  - `tests/test_file_icon_helper.py`: 8 neue Tests — leerer Pfad, nicht-existierender Pfad, existierende Datei, Ordner, Windows-Systemordner, unbekannte Erweiterung, Rückgabetyp-Prüfung; headless unter `QT_QPA_PLATFORM=offscreen`. Gesamtsuite 153/153 grün.
- **Release-EXE-Start-Smoke** (`tests/test_release_smoke.py`):
  - Startet die vorhandene `releases/v1.0.0/ExplorerPro/ExplorerPro.exe` auf Windows mit `QT_QPA_PLATFORM=offscreen`.
  - Ein laufender Prozess nach dem Smoke-Timeout gilt als erfolgreicher Start; sofortige native Loader-/DLL-Abbrüche werden mit Exit-Code, Hex-Code und stderr als Regression sichtbar.
- **Excel-Vorschau** (`.xlsx` / `.xls`, read-only) im Vorschau-Panel:
  - `src/core/xlsx_reader.py`: Qt-freier Pure-Logic-Reader mit `read_workbook_meta` (Blattnamen) und `read_workbook_sheet` (erste ≤ 100 Zeilen × 50 Spalten). openpyxl via Import-Guard; fehlende Lib oder Lesefehler → typisierte Fehlerobjekte, kein Crash. `.xls` via xlrd-Guard (optional).
  - `ExcelPreview`-Widget in `src/gui/preview/preview_panel.py`: Arbeitsblatt-Dropdown (QComboBox), Datentabelle (QTableWidget, read-only), Statuszeile + „Extern öffnen"-Schaltfläche als Fallback.
  - `PreviewPanel._show_preview_for_path` leitet `.xlsx`/`.xls` jetzt an `ExcelPreview` weiter (Stack-Index 6).
  - `tests/test_xlsx_preview.py`: 15 neue Tests — Blattnamen (Single/Multi), erste Zeilen/Spalten, leeres Blatt, Zeilen-Limit, Fallback bei korrupter Datei und fehlendem openpyxl, GUI-Integration. Gesamtsuite 145/145 grün.
- **Erweitertes Syntax-Highlighting** (`src/modules/editor/syntax_highlighter.py`): 5 neue Highlighter-Klassen für bisher nicht unterstützte Coding-Dateitypen.
  - `YAMLHighlighter` für `.yaml` / `.yml` (Dokument-Marker, Keys, Anchors/Aliases, Strings, Zahlen, Booleans, Tags, Kommentare)
  - `ShellHighlighter` für `.sh` / `.bash` / `.zsh` / `.fish` (Shebang, Keywords, Variablen, Strings, Kommentare)
  - `CHighlighter` für `.c` / `.cpp` / `.cc` / `.cxx` / `.h` / `.hpp` / `.hh` (Präprozessor-Direktiven, C/C++-Keywords, Strings, Zahlen, Funktionsaufrufe, PascalCase-Typen, Kommentare)
  - `IniHighlighter` für `.ini` / `.cfg` / `.conf` / `.env` (Sektionen, Keys, Werte, Booleans, # und ; Kommentare)
  - `MarkdownHighlighter` für `.md` / `.markdown` (Überschriften, Fett/Kursiv, Inline-Code, Code-Blöcke, Links/Bilder, Blockquotes, Trennlinien, Listen)
  - Alle neuen Formate im `HIGHLIGHTERS`-Dict registriert; zusätzlich `.svg` zu HTMLHighlighter ergänzt.
- `tests/test_syntax_highlighter.py`: 25 neue Unit-Tests (je 5 pro Highlighter: Registrierung, Lexer-Lookup, Groß-/Kleinschreibungs-Toleranz, Instanziierung, Regelprüfung); Gesamtsuite 130/130 grün.
- **Drag-and-Drop in `FileBrowser`** (`src/gui/browser/file_browser.py`):
  - *Drag OUT*: Ausgewählte Dateien können per Maus in externe Programme (Windows-Explorer, Webmail-Anhang-Upload usw.) gezogen werden. `_DnDTableView.startDrag` → `FileBrowser._start_drag_files` baut `QMimeData` mit `QUrl`-Liste und startet `QDrag` mit Copy- und Move-Action.
  - *Drop IN*: Dateien aus Windows-Explorer oder anderen Apps landen im aktuell angezeigten Ordner. Shift-Drop = Move, normaler Drop = Copy. Kollisionsbehandlung via `_copy`-Suffix; gleicher Ordner wird übersprungen.
  - `_DnDTableView(QTableView)` als minimale Unterklasse für C++-virtuelle `startDrag`/`dropEvent`-Overrides; die gesamte Logik liegt in `FileBrowser`.
  - Neue interne Methoden: `_handle_url_drop`, `_start_drag_files`, `_do_file_drop`.
  - Neue Imports: `QUrl`, `QMimeData`, `QDrag`, `shutil`.
- `tests/test_file_browser.py`: 3 neue DnD-Tests — alle 4 Tests grün.
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
- Die kompakten Seitenleisten-Tabs `📁`, `⭐`, `🔍`, `🚀`, `📋` und `🔄` exponieren jetzt sprechende Accessible Names, Descriptions und Status-Hinweise statt nur Symbol plus Tooltip; `tests/test_sidebar_accessibility.py` sichert den Kontext regressionsfest.
- Die Such-Checkbox "Im Inhalt" wird jetzt an den Index-Worker weitergereicht.
- Datei-/Ordner-Öffnen zeigt bei fehlender Systemzuordnung eine UI-Warnung statt still zu scheitern.
- macOS hing beim Datei-/Ordner-Öffnen nicht mehr fälschlich am Linux-Handler `xdg-open`.
- Windows-Verknüpfungsziele mit Umgebungsvariablen wie `%SystemRoot%` werden vor der Vorschau aufgelöst.
- Mojibake in README- und Workflow-Texten bereinigt.
- Die kompakte Haupt-Toolbar exponiert Navigation, Pfadfeld, Suche und Ansichtsmenü jetzt mit klaren Accessible Names, Descriptions und Tooltips statt nur über Pfeilsymbole und Placeholder.
- Das kompakte Sidebar-Suchpanel exponiert Volltextfeld, Filter, Ergebnisliste, Löschen und den `⚙️`-Dialogpfad jetzt mit klaren Accessible Names, Descriptions und Tooltips statt sich überwiegend auf Placeholder und Symbol-UI zu verlassen.

## [1.0.0] - 2026-03-05

### Hinzugefügt / Added
- Erstveröffentlichung / Initial release
