# Changelog / Änderungsprotokoll

Alle wesentlichen Änderungen an diesem Projekt werden hier dokumentiert.
Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).

## [Unreleased]

## [1.0.2] - 2026-08-21

### Hinzugefügt / Added
- **AI Agent Governance & Bootstrap-Standard** (`CLAUDE.md`, `AGENTS.md`, `tests/test_metadata_contract.py`):
  - Erstanlage von `CLAUDE.md` mit YAML-Frontmatter nach `project-docs`-Standard, Dokumentation von Quick Commands, Architektur, Hard Rules (Zero-Egress, Non-Elevation, Plan D), Domain-Kontext und Schlüsseldateien.
  - Erstanlage von `AGENTS.md` als universeller Multi-Agent-Redirect auf `CLAUDE.md`.
  - Vervollständigung aller 36 GUI-Strings in `locales/translations.json` (100% Deckung über 6 Zielsprachen: DE, EN, ES, ZH, JA, RU), verifiziert via `manage_translations.py`.
  - Validierung von `scripts/check_store_readiness.py` (0 Findings, Store Readiness OK).
  - 9 automatisierte Metadaten- und Governance-Vertragstests in `tests/test_metadata_contract.py`.
- **Kontextmenü & Datei-Operationen in `FileBrowser`** (`src/gui/browser/file_browser.py`):
  - Vollständige Implementierung aller Datei- und Verzeichnisoperationen im Kontextmenü des Datei-Browsers:
    - **Löschen** (`delete_selection`): Mit Sicherheits-Bestätigungsdialog (`QMessageBox.question`), Löschung von Dateien (`os.remove`) und Verzeichnissen (`shutil.rmtree`), Fehlerbehandlung und Aktualisierung. Tastenkürzel `Delete`.
    - **Umbenennen** (`rename_selection`): Dialog mit Vorbelegung des aktuellen Namens (`QInputDialog.getText`), Kollisionsprüfung und Warnung bei vorhandenem Zieldateinamen, `os.rename` mit Fehlerbehandlung. Tastenkürzel `F2`.
    - **Neuer Ordner** (`create_new_folder`): Erstellung im aktuellen Verzeichnis via `QInputDialog.getText` und `os.makedirs`, Duplikat- und Fehlerbehandlung.
    - **Kopieren & Einfügen** (`copy_selection`, `paste_from_clipboard`): Synchronisation mit der System-Zwischenablage (`QMimeData` mit file URLs und Pfad-Text), Einfügen mit kollisionsfreiem Auto-Suffix (`_copy`, `_copy_2`) ohne Überschreiben. Tastenkürzel `Ctrl+C` und `Ctrl+V`.
    - **In Index suchen** (`_search_in_index`): Übergibt Dateinamen an die Toolbar-Suche und startet Volltext-Recherche.
    - **Pfad als Prompt speichern** (`_save_path_as_prompt`): Legt Dateipfad-Prompt in der Prompt-Bibliothek ab oder kopiert Analyse-Template in die Zwischenablage.
    - **Zur Blacklist hinzufügen** (`_add_to_blacklist`): Trägt Dateinamen in den Datenschutz-Monitor (`PrivacyMonitor`) ein.
    - **Synchronisieren** (`_sync_path`): Öffnet das Synchronisations-Panel für den ausgewählten Pfad.
  - Erweiterte Tastatur-Events in `_DnDTableView` (`keyPressEvent`) für Delete, F2, Copy und Paste.
- **Menü-Verdrahtung in `MainWindow`** (`src/gui/main_window.py`):
  - Datei -> „Neues Fenster" (`_open_new_window`, Ctrl+N) öffnet neue Instanz und registriert sie in `_child_windows`.
  - Bearbeiten -> „Kopieren" (Ctrl+C), „Einfügen" (Ctrl+V) und „Neuer Ordner" (Ctrl+Shift+N) vollständig mit `FileBrowser` verdrahtet.
  - Tools -> „Einstellungen…" (Ctrl+,) mit Einstellungsdialog (`SettingsDialog`) verdrahtet.
- **Automatisierte Testsuiten** (`tests/test_file_browser.py`, `tests/test_menu_actions_wired.py`):
  - 11 neue Tests für Datei-Browser-Operationen (Ordnererstellung, Umbenennen mit Kollision, Löschen mit Bestätigung/Abbruch, Copy/Paste, Prompt/Blacklist-Aktionen).
  - Umfassende Testsuite `tests/test_menu_actions_wired.py` für Menü-Verdrahtung, Einstellungs-Roundtrip, Ansichtsmenü und Tastatur-Shortcuts.

### Behoben / Fixed
- **Kontextmenü-Aktionen im Dateibrowser verdrahtet** (`src/gui/browser/file_browser.py`):
  Die Kontextmenü-Aktionen „Löschen", „Umbenennen" und „Neuer Ordner" waren im Kontextmenü vorhanden, aber nicht mit Aktionen verbunden. Die Methoden `delete_selection()`, `rename_selection()` und `create_new_folder()` wurden implementiert und mit Sicherheitsabfragen/Dialogen versehen.
- **Index-Synchronisation & Verbindungs-Handling im DuplicateFinder** (`src/modules/indexer/duplicate_finder.py`):
  `DuplicateScanWorker` nutzt nun eine saubere, per-Thread SQLite-Verbindung über `file_index.db_path` statt eines potenziell verwaisten `conn`-Objekts. Beim Löschen gefundener Duplikate wird der `FileIndex` via `file_index.remove_file()` synchronisiert.
- **Python 3.12+ SQLite Datetime Adapter & Index-Methoden** (`src/core/file_index.py`):
  Explizite Registrierung von `sqlite3.register_adapter(datetime, ...)` verhindert DeprecationWarnings in Python 3.12+. `FileIndex` um `remove_file()` und `get_file()` ergänzt.
- **Erkennung versteckter Verzeichnisse im SyncManager** (`src/modules/sync/sync_manager.py`):
  `SyncWorker._get_files` prüft nun alle Pfadsegmente des relativen Pfads, sodass Dateien innerhalb versteckter Unterverzeichnisse bei `include_hidden=False` zuverlässig ignoriert werden.
- **SyntaxHighlighter Lifecycle in TextPreview** (`src/gui/preview/preview_panel.py`):
  Bestehende `QSyntaxHighlighter`-Instanzen werden vor dem Erzeugen eines neuen Highlighters per `setDocument(None)` explizit getrennt, um Überlappungen und Leaks zu verhindern.
- **Menuepunkt „Einstellungen…" oeffnete kein Fenster** (Usertest Welle 1, 2026-08-14):
  Die QAction in `src/gui/main_window.py` war dem Tools-Menue hinzugefuegt, aber nie
  mit `triggered.connect` verbunden; als lokale Variable konnte die Verbindung auch
  nirgends nachgeholt werden. Ein Einstellungsdialog existierte ueberhaupt nicht.
  Neu: `src/gui/settings_dialog.py` mit den fuenf Sektionen des `SettingsManager`
  (Allgemein, Index, Vorschau, Datenschutz, Darstellung). `_show_settings` haelt eine
  Referenz am Fenster; `_apply_settings` wendet Vorschau-Sichtbarkeit und versteckte
  Dateien sofort an. `FileBrowser.set_show_hidden_files` ergaenzt.
- **Toolbar-Schalter „Ansicht" war funktionslos**: Der `QToolButton` im Modus
  `InstantPopup` hatte nie ein Menue per `setMenu` erhalten und reagierte daher
  prinzipbedingt nicht auf Klicks. Das gleichnamige Menue der Menueleiste war intakt.
  Neu: `view_toolbutton_menu` wird als Attribut gehalten und teilt sich die Aktionen
  mit der Menueleiste, sodass die Haekchen in beiden Menues synchron bleiben.
- **Weitere unverbundene Menuepunkte**: „Neues Fenster", „Kopieren" und „Einfuegen"
  im Hauptmenue sowie dieselben Eintraege im Kontextmenue des Dateibrowsers.
  `FileBrowser` erhaelt `copy_selection` und `paste_from_clipboard`; Einfuegen nutzt
  die bestehende Kollisionsbehandlung aus `_do_file_drop` und ueberschreibt nichts.
  Neue Fenster werden in `_child_windows` referenziert.

### Gewartet / Maintenance
- **Release-Build in sauberer virtueller Umgebung**: Der Build erfolgt jetzt gegen
  eine venv mit ausschliesslich den Abhaengigkeiten aus `requirements.txt` plus
  PyInstaller und pywin32. Ein Build gegen die globale Python-Installation hatte
  projektfremde Pakete eingesammelt (aiohttp, botocore, paramiko, cryptography,
  pydantic u. a.) und das Bundle auf 20,3 MB / 118 Dateien aufgeblaeht. Der saubere
  Build liegt bei 11,5 MB / 89 Dateien und damit unter dem Stand vom 27.06.2026
  (12,9 MB / 96 Dateien).

## [1.0.1] - 2026-07-27

### Gewartet / Maintenance
- **Technische Hygiene & Doku-Wartung (Pfad A)**:
  - Datum der letzten Wartungs- und Dokumentationsprüfung in `llms.txt`, `README.md` und `README_de.md` auf 2026-07-27 aktualisiert.
  - Testsuite verifiziert (160 passed, 1 skipped) und Quelltext-Kompilierung (`compileall`) erfolgreich ausgeführt.

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
- `llms.txt`: Header `Last-checked` Datum auf `2026-07-25` aktualisiert.
- `pytest.ini` & `pyproject.toml`: `pythonpath = . src` bzw. `pythonpath = [".", "src"]` hinzugefügt für nahtlose Testausführung; Metadaten um Keywords & `[project.urls]` erweitert.
- `README.md` & `README_de.md`: Pytest (160 passed), PySide6, Local-First Privacy & LLM-Ready Badges sowie KI-Agenten-Hinweis (`> [!NOTE]`) eingebunden; Wartungsdatum auf 2026-07-25 aktualisiert.
- `ROADMAP.md` ist seit 2026-07-19 eine versionierte, kanonische
  Planungsübersicht statt einer untracked Arbeitsnotiz. Erledigte Punkte zu
  Release-Start-Smoke, Drag-and-drop, Excel-Vorschau, Syntaxformaten und
  Originalicons sind als historisch abgeschlossen markiert; offen bleiben nur
  die in `AUFGABEN.txt` und `PORTIERUNGSPLAN.md` geführten MSIX-/WACK-,
  Lizenzprovenienz-, Release-Hygiene- und Export-/Privacy-/Viewer-Gates.
- README, Contributing Guide und Code of Conduct auf das aktuelle Repository `file-bricks/ExplorerPro` aktualisiert.
- Öffentliche private Kontaktadresse aus dem Code of Conduct entfernt.
- `.gitignore` um Test-, Coverage- und Cache-Artefakte erweitert.
- Community-Workflows und Testworkflow auf aktuelle GitHub-Actions-Major-Versionen aktualisiert.
- README mit Plattformplan, Exportformat und aktuellem Wartungsstand abgeglichen.
- Windows-Store-Doku nennt das dedizierte Screenshot-Set jetzt als erledigten Bestandteil der lokalen Store-Basis.
- Portierungsplan markiert die Windows-Store-Basis jetzt als erledigten P0-Schritt.
- Desktop-Öffnen nutzt jetzt plattformgerecht `open` auf macOS und `xdg-open` auf Linux.

### Behoben / Fixed
- Drag-and-drop überschreibt bei Namenskollisionen keine vorhandenen Dateien mehr und blockiert Ordner-Drops in sich selbst oder eigene Nachfahren.
- Der Standardexport lässt App-Argumente und Prompt-Inhalte aus; sensitive Inhalte benötigen ein separates Opt-in. Aktive Privacy-Muster folgen der gültigen lokalen Konfiguration.
- Der LIKE-Fallback der Volltextsuche respektiert weiterhin den Filter „Nur im Inhalt suchen“.
- Runtime-, optionale Extra-, Build- und Lizenzverträge sind synchron; veraltete PyQt6-/QScintilla-/Pygments-/watchdog-Behauptungen wurden entfernt.
- Locks, lokale Backups und unreferenzierte Mobile/PWA-Assets sind explizit vom Git-/Release-Scope ausgeschlossen.
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
