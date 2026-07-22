# 🏗️ ExplOrer Pro - Architektur-Skizze (Final)

## Version 1.0.0 - Phase 5 Complete

## Komponenten-Diagramm

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            ExplOrer Pro v1.0                                │
│                         (PySide6 Desktop App)                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                        MAIN WINDOW                                    │ │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │ │
│  │  │                      TOOLBAR                                    │ │ │
│  │  │  [◀][▶][↑] [📁 C:\Users\...           ] [🔍 Suchen...  ] [⚙️] │ │ │
│  │  └─────────────────────────────────────────────────────────────────┘ │ │
│  │                                                                       │ │
│  │  ┌─────────┬──────────────────────────────┬──────────────────────┐  │ │
│  │  │ SIDEBAR │        FILE BROWSER          │    PREVIEW PANEL     │  │ │
│  │  │         │                              │                      │  │ │
│  │  │ [📁][⭐]│  ┌────────────────────────┐  │  ┌────────────────┐  │  │ │
│  │  │ [🔍][🚀]│  │ Name    │ Size │ Date │  │  │   PDF/Image/   │  │  │ │
│  │  │ [📋][🔄]│  ├─────────┼──────┼──────┤  │  │   Code Preview │  │  │ │
│  │  │         │  │ doc.pdf │ 2MB  │ 01/03│  │  │                │  │  │ │
│  │  │ ┌─────┐ │  │ code.py │ 12KB │ 01/02│  │  └────────────────┘  │  │ │
│  │  │ │📁Tree│ │  │ img.png │ 500KB│ 12/28│  │                      │  │ │
│  │  │ │ ├─C:│ │  └────────────────────────┘  │  ┌────────────────┐  │  │ │
│  │  │ │ ├─D:│ │                              │  │   METADATA     │  │  │ │
│  │  │ │ └─..│ │                              │  │  ├─ Hash       │  │  │ │
│  │  │ └─────┘ │                              │  │  ├─ Tags       │  │  │ │
│  │  │ ┌─────┐ │                              │  │  └─ Notes      │  │  │ │
│  │  │ │⭐Favs│ │                              │  └────────────────┘  │  │ │
│  │  │ │🔍Srch│ │                              │                      │  │ │
│  │  │ │🚀Apps│ │                              │  ┌────────────────┐  │  │ │
│  │  │ │📋Prmt│ │                              │  │  QUICK EDIT    │  │  │ │
│  │  │ │🔄Sync│ │                              │  │  (PythonBox)   │  │  │ │
│  │  │ └─────┘ │                              │  └────────────────┘  │  │ │
│  │  └─────────┴──────────────────────────────┴──────────────────────┘  │ │
│  │                                                                       │ │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │ │
│  │  │  STATUS BAR                                                     │ │ │
│  │  │  📁 1.234 Dateien │ 💾 2.3 GB │ 🟢 Datenschutz OK │ Sync: ✓    │ │ │
│  │  └─────────────────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Projekt-Struktur (Final)

```
ExplorerPro/
├── src/
│   ├── main.py                          # Entry Point (58 Zeilen)
│   ├── app.py                           # Haupt-App-Klasse (239 Zeilen)
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── file_index.py                # SQLite Index + FTS5 (580 Zeilen)
│   │   ├── settings_manager.py          # Einstellungen (JSON)
│   │   └── event_bus.py                 # Signal-Bus
│   │
│   ├── gui/
│   │   ├── __init__.py
│   │   ├── main_window.py               # Hauptfenster + Menüs (530 Zeilen)
│   │   ├── sidebar.py                   # 6-Tab Sidebar (301 Zeilen)
│   │   ├── status_bar.py                # Statusleiste mit Ampel (167 Zeilen)
│   │   │
│   │   ├── sidebar/
│   │   │   ├── __init__.py
│   │   │   ├── search_panel.py          # Erweiterte Suche (387 Zeilen)
│   │   │   └── advanced_search_dialog.py # Such-Dialog (489 Zeilen)
│   │   │
│   │   ├── browser/
│   │   │   ├── __init__.py
│   │   │   └── file_browser.py          # Dateiliste (395 Zeilen)
│   │   │
│   │   └── preview/
│   │       ├── __init__.py
│   │       └── preview_panel.py         # Vorschau-Panel (367 Zeilen)
│   │
│   └── modules/
│       ├── __init__.py
│       │
│       ├── privacy/                      # AmpelTool-Integration
│       │   ├── __init__.py
│       │   ├── privacy_monitor.py       # Clipboard-Überwachung (437 Zeilen)
│       │   └── blacklist_manager.py     # Blacklist-Verwaltung (244 Zeilen)
│       │
│       ├── editor/                       # PythonBox-Integration
│       │   ├── __init__.py
│       │   ├── quick_editor.py          # Code-Editor (545 Zeilen)
│       │   └── syntax_highlighter.py    # Syntax-Highlighting (294 Zeilen)
│       │
│       ├── indexer/                      # Index-Tools
│       │   ├── __init__.py
│       │   └── duplicate_finder.py      # Duplikate-Finder (676 Zeilen)
│       │
│       ├── launcher/                     # SoftwareCenter-Integration
│       │   ├── __init__.py
│       │   └── apps_panel.py            # App-Launcher (382 Zeilen)
│       │
│       ├── prompts/                      # ProfiPrompt-Integration
│       │   ├── __init__.py
│       │   └── prompts_panel.py         # Prompt-Bibliothek (500 Zeilen)
│       │
│       └── sync/                         # ProSync-Integration
│           ├── __init__.py
│           └── sync_manager.py          # Ordner-Sync (709 Zeilen)
│
├── requirements.txt                      # Abhängigkeiten
└── README.md

GESAMT: ~7.500 Zeilen Python-Code
```

## System-Architektur

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           ExplOrer Pro v1.0                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                        GUI LAYER                                 │   │
│  │                                                                  │   │
│  │   MainWindow ──┬── Sidebar ────┬── TreePanel                    │   │
│  │                │               ├── FavoritesPanel               │   │
│  │                │               ├── SearchPanel (Advanced)       │   │
│  │                │               ├── AppsPanel (SoftwareCenter)   │   │
│  │                │               ├── PromptsPanel (ProfiPrompt)   │   │
│  │                │               └── SyncPanel (ProSync)          │   │
│  │                │                                                 │   │
│  │                ├── FileBrowser ─── QTableView + FileModel       │   │
│  │                │                                                 │   │
│  │                └── PreviewPanel ─┬── PDFPreview (PyMuPDF)       │   │
│  │                                  ├── ImagePreview (Qt QPixmap)  │   │
│  │                                  ├── CodePreview (PythonBox)    │   │
│  │                                  └── MetadataPanel              │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                      │                                  │
│  ┌───────────────────────────────────┴──────────────────────────────┐   │
│  │                       CORE LAYER                                 │   │
│  │                                                                  │   │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────────┐    │   │
│  │  │   FileIndex   │  │  MetaStore    │  │  PrivacyMonitor   │    │   │
│  │  │  (ProFiler)   │  │   (Tags,      │  │   (AmpelTool)     │    │   │
│  │  │               │  │   Notes)      │  │                   │    │   │
│  │  │ • SQLite+FTS5 │  │               │  │ • Clipboard Watch │    │   │
│  │  │ • Hash Index  │  │ • JSON Store  │  │ • Blacklist       │    │   │
│  │  │ • Text-Extraktion│ │ • Categories  │  │ • Ampel-Status    │    │   │
│  │  └───────────────┘  └───────────────┘  └───────────────────┘    │   │
│  │                                                                  │   │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────────┐    │   │
│  │  │  SyncManager  │  │  AppsPanel    │  │   PromptsPanel    │    │   │
│  │  │  (ProSync)    │  │ (SoftwareCtr) │  │  (ProfiPrompt)    │    │   │
│  │  │               │  │               │  │                   │    │   │
│  │  │ • Bidirekt.   │  │ • Categories  │  │ • Variablen       │    │   │
│  │  │ • Konflikt-   │  │ • Favorites   │  │ • Tags            │    │   │
│  │  │   Lösung      │  │ • Launch      │  │ • Quick-Copy      │    │   │
│  │  └───────────────┘  └───────────────┘  └───────────────────┘    │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                      │                                  │
│  ┌───────────────────────────────────┴──────────────────────────────┐   │
│  │                       DATA LAYER                                 │   │
│  │                                                                  │   │
│  │   ┌─────────────┐   ┌─────────────┐   ┌─────────────────────┐   │   │
│  │   │fileindex.db │   │  apps.json  │   │   File System       │   │   │
│  │   │  (Index)    │   │prompts.json │   │   (watched dirs)    │   │   │
│  │   │             │   │  sync.json  │   │                     │   │   │
│  │   └─────────────┘   └─────────────┘   └─────────────────────┘   │   │
│  │                                                                  │   │
│  │   Speicherort: ~/.explorerpro/                                  │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

## Integrierte Tool-Fusion

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     INTEGRIERTE TOOLS                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────┐                                                   │
│  │   ProFiler V14  │ ──▶ FileIndex (SQLite + FTS5)                     │
│  │   (File Index)  │     • Datei-Hash (SHA-256)                        │
│  └─────────────────┘     • Text-Extraktion (PDF, DOCX)                 │
│                          • Erweiterte Suche mit Filtern                │
│                                                                         │
│  ┌─────────────────┐                                                   │
│  │   PythonBox V8  │ ──▶ QuickEditor + SyntaxHighlighter               │
│  │   (Code Editor) │     • Multi-Tab Editor                            │
│  └─────────────────┘     • Python, HTML, CSS, JS Syntax                │
│                          • Code-Completion                              │
│                                                                         │
│  ┌─────────────────┐                                                   │
│  │   AmpelTool V5  │ ──▶ PrivacyMonitor + BlacklistManager             │
│  │   (Privacy)     │     • Clipboard-Überwachung                       │
│  └─────────────────┘     • Pattern-Erkennung (Regex)                   │
│                          • 🟢🟡🔴 Ampel-Status                          │
│                                                                         │
│  ┌─────────────────┐                                                   │
│  │ SoftwareCenter  │ ──▶ AppsPanel                                     │
│  │   (Launcher)    │     • Kategorien & Favoriten                      │
│  └─────────────────┘     • Custom Apps mit Argumenten                  │
│                          • Quick-Launch via Sidebar                     │
│                                                                         │
│  ┌─────────────────┐                                                   │
│  │  ProfiPrompt    │ ──▶ PromptsPanel                                  │
│  │   (Prompts)     │     • Prompt-Bibliothek                           │
│  └─────────────────┘     • {{Variable}} Ersetzung                      │
│                          • Kategorien & Tags                            │
│                                                                         │
│  ┌─────────────────┐                                                   │
│  │   ProSync V3.1  │ ──▶ SyncPanel + SyncManager                       │
│  │   (Backup)      │     • Bidirektionale Sync                         │
│  └─────────────────┘     • Konflikt-Lösung                             │
│                          • Exclude-Patterns                             │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Keyboard Shortcuts

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    TASTENKÜRZEL                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Navigation:                                                            │
│    Alt+Left      Zurück                                                │
│    Alt+Right     Vorwärts                                              │
│    Alt+Up        Übergeordneter Ordner                                 │
│    Alt+Home      Home-Verzeichnis                                      │
│                                                                         │
│  Ansicht:                                                               │
│    Ctrl+B        Sidebar ein/aus                                       │
│    Ctrl+P        Vorschau ein/aus                                      │
│    F5            Aktualisieren                                         │
│                                                                         │
│  Tools (Sidebar-Tabs):                                                  │
│    Ctrl+1        Apps-Panel öffnen                                     │
│    Ctrl+2        Prompts-Panel öffnen                                  │
│    Ctrl+3        Sync-Panel öffnen                                     │
│                                                                         │
│  Bearbeitung:                                                           │
│    F4            Editor öffnen                                         │
│    Ctrl+N        Neues Fenster                                         │
│    Ctrl+O        Ordner öffnen                                         │
│    Ctrl+Shift+N  Neuer Ordner                                          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Technologie-Stack

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    TECHNOLOGIE-STACK                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  GUI:        PySide6 (QMainWindow, QSplitter, QTableView, QTreeWidget) │
│                                                                         │
│  Editor:     Eigener QSyntaxHighlighter (Syntax-Highlighting)           │
│                                                                         │
│  Preview:    PyMuPDF (PDF), Qt QPixmap (Bilder), eigener Highlighter    │
│                                                                         │
│  Datenbank:  SQLite3 + FTS5 (Volltext-Suche)                           │
│                                                                         │
│  Dateizugriff: Qt- und Standardbibliotheks-APIs für lokale Dateien       │
│                                                                         │
│  Sync:       shutil, hashlib (SHA-256), filecmp                        │
│                                                                         │
│  Config:     JSON (~/.explorerpro/), QSettings                         │
│                                                                         │
│  Python:     3.10+                                                      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Build und Tests

- Runtime installieren: python -m pip install -r requirements.txt
- Windows-EXE bauen: python -m pip install ".[build]" und anschließend build_exe.bat.
- Regressionen: python -m pytest -q
- Syntax- und Bytecode-Check: python -m compileall -q src tests generate_store_screenshots.py



## Phasen-Übersicht

| Phase | Beschreibung | Zeilen | Status |
|-------|--------------|--------|--------|
| 1 | Explorer-Grundgerüst | ~2.000 | ✅ |
| 2 | Index & Suche | ~1.500 | ✅ |
| 3 | Editor & Preview | ~1.200 | ✅ |
| 4 | Datenschutz (AmpelTool) | ~700 | ✅ |
| 5 | Apps, Prompts, Sync | ~1.600 | ✅ |
| **Gesamt** | | **~7.500** | **100%** |
