# Changelog / Änderungsprotokoll

Alle wesentlichen Änderungen an diesem Projekt werden hier dokumentiert.
Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).

## [Unreleased]

## [1.0.7] - 2026-09-26

### Behoben / Fixed (Store-Icon weißer Rand — T-20260820-729932431)
- **Store-Kachel-Icons mit sichtbarem weißen Rand (`store_assets/Square44x44Logo.png`, `Square150x150Logo.png`, `Square310x310Logo.png`, `StoreLogo.png`, `Wide310x150Logo.png`)**: Diese Dateien hatten trotz RGBA-Modus einen opaken (nicht transparenten) Canvas-Hintergrund gebacken (Alpha 255 statt 0 rund um das Motiv, bei `Wide310x150Logo.png` im eingebetteten 150px-Mittelfeld) — sichtbar als weißer Kasten/Halo um das Icon-Motiv in Kachel, Startmenü, Taskleiste und Store-Listing.
  - **Nachreview (merge-reviewer, claude-opus, Commit `aee6401`) fand einen Mangel** in einem ersten, per Direkt-Push auf `master` eingespielten Versuch (in 1.0.6 nicht mehr zurückgenommen, siehe unten): Die dort verwendeten Ersatzdateien (`icon_44x44.png` u. a.) zeigen eine ANDERE Gestaltung (gerahmte Variante mit cyanfarbenem Rahmen und weißer Sichel am Rand, kleineres Motiv) statt des ursprünglichen Vollflächen-Motivs — und `Wide310x150Logo.png` blieb dabei unentdeckt defekt.
  - **Erster Korrekturversuch (PR #3, `edcb8fa`) noch nicht sauber:** Ursprüngliches Vollflächen-Motiv per Flood-Fill-Matting freigestellt, aber mit zu kleinem Farbdistanz-Schwellwert (60) — die eigentliche Antialiasing-Übergangszone am Rand der abgerundeten Ecke war nur 1 Pixel breit, hatte aber eine Farbdistanz von ~97 zum Hintergrund und blieb dadurch unverarbeitet: ein 1px heller Saum auf dunklem Grund (gemessen: bis zu 204 Randpixel mit Alpha ≥ 192 und Luminanz auf Schwarz bis 216, je nach Kachelgröße).
  - **Korrigierter Fix (dieser Release):** Farbdistanz-Schwellwert auf 150 angehoben (deutlich über der gemessenen Übergangsdistanz von ~97, deutlich unter der Distanz zur soliden Motivfarbe von >300) — damit erfasst das Un-Premultiply die komplette Antialiasing-Übergangszone, kein Fransensaum mehr. Motiv unverändert (keine Neugestaltung). `icon_310x150.png` ist ein separates Marketing-Banner (nicht vom AppxManifest referenziert) und bleibt unverändert. Regressionstest `test_store_tiles_have_transparent_corners` um eine Luminanz-Prüfung auf Schwarz-Komposit erweitert, damit dieser Fehler künftig auffällt. Verifiziert per Kontaktbogen (5 Größen × Weiß/Schwarz/Grau/Akzentgrün) und Vergrößerung der abgerundeten Ecke: kein Halo, kein Fransensaum, keine hellen Randflächen. Per Pull Request gegen `master` (kein Direkt-Push).

## [1.0.6] - 2026-09-26

### Behoben / Fixed (Kontextmenü, Editor-Dirty-Flag, Qt-Übersetzung — T-20260926-912169808)
- **Kontextmenü-Aktionen "Metadaten anzeigen"/"Tags bearbeiten" (`src/gui/browser/file_browser.py`, `src/gui/main_window.py`)**: Beide Aktionen aktualisierten nur das ggf. ausgeblendete Vorschaupanel und zeigten dadurch scheinbar keine Wirkung. `MainWindow.show_file_metadata()` blendet das Panel jetzt ein und fokussiert bei "Tags bearbeiten" direkt das Tag-Feld.
- **Tags/Notizen ohne dauerhafte Wirkung (`src/core/file_index.py`, `src/gui/preview/preview_panel.py`)**: Tag- und Notizfelder wurden nirgends gespeichert. `FileIndex.get_tags`/`set_tags`/`get_note`/`set_note` ergänzt, `MetadataPanel` lädt/speichert beim Anzeigen, Wechseln und Schließen. `index_file` von `INSERT OR REPLACE` auf echtes UPSERT (`ON CONFLICT DO UPDATE`) umgestellt, damit ein Reindex die `files.id` erhält und bestehende Tags/Notizen (referenziert über `ON DELETE CASCADE`) nicht verwaist.
- **Editor meldet Änderungen nach bloßem Öffnen (`src/modules/editor/quick_editor.py`)**: Verzögertes Syntax-Rehighlighting löste `textChanged` aus und markierte frisch geöffnete Dateien fälschlich als ungespeichert. Dirty-Flag jetzt über `QTextDocument.modificationChanged` statt `textChanged`.
- **Speichern/Verwerfen-Dialog auf Englisch in der deutschen Version (`src/main.py`)**: Kein Qt-eigener Übersetzer installiert. `QTranslator` mit `qtbase_<lang>.qm` ergänzt (unabhängig von der App-eigenen `TranslationSystem`, kein Overwrite).
- **Mehrfach-Umbenennen/Diff/Einstellungen stürzen im Quellstart ab (`src/main.py`, `ExplorerPro.spec`)**: `translator.py` (Projektwurzel) fehlte auf `sys.path`; Spec um `pathex`/`datas` für Projektwurzel und `locales/` ergänzt.
- **9 neue automatisierte Regressionstests** (`tests/test_context_menu_actions.py`), Vollsuite 359 passed / 2 skipped. Review/Merge als zweites Modell: Repo `file-bricks/ExplorerPro#1`, Squash `264aa6eae60055f1ffb4ff041025920738c6ead2`.
- **Bekannter Mangel dieses Releases:** Der ebenfalls in 1.0.6 enthaltene Icon-Fix-Versuch (direkt gepusht, `aee6401`) hatte das falsche Motiv und einen unentdeckt gebliebenen Defekt in `Wide310x150Logo.png` — die Store-Submission dieser Version läuft dennoch durch, weil die Kontextmenü-Fixes ankommen sollen; der korrigierte Icon-Fix folgt in 1.0.7.

### Behoben / Fixed (Bugsearch 2026-09-26)
- **Batch-Renamer, Kaskadierende Kollisionserkennung, Windows-Gerätenamens-Schutz und Nummerierungs-Affix-Integrität (`src/core/batch_rename_service.py`)**:
  - **Kaskadierende Kollisionserkennung (`generate_preview`)**: Fixpunkt-Iteration implementiert, die Abhängigkeitsketten und Kaskaden (Datei A will Dateiname B übernehmen, Datei B kann wegen eines externen oder internen Konflikts nicht verschoben werden) vollständig und deterministisch auflöst; verhindert, dass blockierte Zieldateien fälschlich als "Bereit" (`status="ok"`) markiert werden und schützt vor `WinError 183` auf Windows sowie stillem Datenverlust durch Überschreiben auf POSIX.
  - **Präfix- & Suffix-Erhalt bei Namensersetzung (`compute_new_name`)**: Nummerierung wird nun vor dem Hinzufügen von Präfix und Suffix auf den Stamm angewendet, sodass bei `number_position="replace"` die Nummer den Basisstamm ersetzt, konfigurierte Präfixe und Suffixe (z. B. `IMG_001_RAW.jpg`) jedoch vollständig erhalten bleiben.
  - **Windows-reservierte Gerätenamen (`compute_new_name`)**: Ungültige Windows-Gerätenamen (`CON`, `PRN`, `AUX`, `NUL`, `COM1-9`, `LPT1-9`) werden sowohl als Stamm als auch als Gesamtname mit klarer Fehlermeldung defensiv abgewiesen.
  - **Ressourcen- und I/O-Schutz bei fehlender Quelle (`execute_rename`)**: Phase 1 bricht bei fehlender Quelldatei sofort per `break` ab und rollt bereinigt zurück, statt unnötige Temp-Dateien für nachfolgende Dateien auf die Festplatte zu schreiben.
  - **Zielbelegungs-Schutz (`execute_rename`)**: Phase 2 prüft vor jedem `os.rename(temp_path, dst)` defensiv auf bereits belegte Zielpfade (`if os.path.exists(dst): raise OSError(...)`).
  - **5 neue automatisierte Regressionstests**: Vollständige Testabdeckung in `tests/test_batch_renamer_regressions.py` hinzugefügt (Vollsuite auf 357 Tests ausgebaut).

### Wartung & CI-Matrix-Härtung / Maintenance & CI Hardening (2026-09-26, Pfad A)
- **Repository-Hygiene, CI-Lifecycle-Härtung & PEP 621 Metadaten-Parität (Pfad A)**:
  - **CI-Workflow-Härtung (.github/workflows/ci.yml)**: Bytecode-Kompilierungsgate auf python -m compileall -q . für das gesamte Projektverzeichnis erweitert; Concurrency mit cancel-in-progress: true und Timeouts auf Multi-OS-Matrix verifiziert.
  - **Multi-Host Defense (.gitignore)**: Ergänzung um Flotten-Muster *-MacBook*, *-IDEAPAD*, .automation-lock, .pytest_temp/, .pytest_tmp*/.
  - **NOTICE Root-Attribution**: Formelle NOTICE-Datei für Lukas Geiger, file-bricks Familie und open-bricks Umbrella angelegt.
  - **PEP 621 Standardisierung (pyproject.toml)**: license-files Whitelist (LICENSE, NOTICE, THIRD_PARTY_LICENSES.md, THIRD_PARTY_LICENSES.txt), project.urls.Notice und 20 gesättigte Keywords abgestimmt auf GitHub Topics eingetragen; [tool.pytest.ini_options] um zusätzliche norecursedirs ergänzt.
  - **Level 1 SBOM (THIRD_PARTY_LICENSES.md)**: Stand auf 2026-09-26 mit NOTICE-Querverweis, RunAsInvoker und Zero-Egress Invarianten aktualisiert.
  - **Dokumentations- & Kontext-Synchronisation**: README.md und README_de.md Badges (350+ passed, Stand 2026-09-26, Attribution) und llms.txt (Last-checked 2026-09-26, 350+ Tests, NOTICE-Referenz) synchronisiert; 18-Punkte Navigations-Parität beibehalten.
  - **Automatisierte Vertragstests (tests/test_metadata_contract.py, tests/test_security_license_contract.py)**: Um Testfälle für NOTICE, 20 gesättigte Keywords, license-files, CI Compileall Gate und Multi-Host Gitignore-Muster erweitert.


### Behoben / Fixed (Bugsearch 2026-09-24)
- **Datei-Integritäts- & Prüfsummen-Dienst, Verifikations-Parsing und Datei-Vergleich (`src/core/checksum_service.py`, `src/gui/checksum_dialog.py`, `src/core/diff_service.py`, `src/gui/diff_dialog.py`)**:
  - **Multi-Format Hash-Verifikation (`core/checksum_service.py: verify_hash`)**: Unterstützung für GNU coreutils Prüfsummen (`sha256sum`/`md5sum` mit Dateinamen und Asterisk), BSD-Formate (`SHA256 (file) = hash`), Key-Value-Paare mit Gleichheitszeichen (`SHA256 = hash`), formatiertes Hex mit Trennzeichen (`XX-XX-XX...`, `XX XX XX...` aus Windows CertUtil und PowerShell), Anführungszeichen sowie mehrzeilige Prüfsummen-Dateien implementiert.
  - **Doppel-Newline-Bug im Unified Diff (`core/diff_service.py: generate_unified_diff_text`)**: `readlines()` durch `read().splitlines()` ersetzt; verhindert das Einfügen störender Leerzeilen nach jeder Diff-Zeile und erzeugt strikt standardkonforme Unified Diffs für `patch` und Zwischenablage.
  - **Verzeichnis-Validierung (`core/diff_service.py: compare_files`, `gui/diff_dialog.py`)**: Verzeichnispfade werden vor Leseversuchen defensiv mit `os.path.isfile` geprüft und mit klarer Fehlermeldung abgewiesen, statt mit ungefangenem `PermissionError: [Errno 13]` abzustürzen.
  - **Heuristik für Binärdateien (`core/diff_service.py: is_binary_file`)**: Erkennung von Binärdateien ohne Nullbytes über Kontrollzeichen-Dichte (>5%) implementiert und toten Ausnahme-Code in `latin-1`-Decodierung beseitigt.
  - **Worker-Thread-Lebenszyklus (`gui/checksum_dialog.py`)**: `done()` überschrieben, sodass beim Schließen via "Schließen"-Button oder `Esc` (`accept()`) der Hintergrund-Worker `ChecksumWorker` zuverlässig abgebrochen und gewartet wird, statt im Hintergrund weiterzulaufen.
  - **Resiliente Größenanzeige (`gui/checksum_dialog.py: _copy_all_hashes`)**: Wiederverwendung der bereits ermittelten Dateigröße statt fehleranfälligem Re-Read via `os.path.getsize`.
  - **10 neue automatisierte Regressionstests**: Vollständige Testabdeckung in `tests/test_bugsweep_checksum_and_diff_20260924.py` (Vollsuite auf 350 Tests ausgebaut, 100% grün).

### Marketing & Visuelle Architektur / Marketing & Visual Architecture (2026-09-18)
- **Pfad B: Discoverability, visuelle Architektur & Metadaten-Vertrag**:
  - **18-Punkte Schnellnavigations-Parität (`README.md` & `README_de.md`)**: Vollständige zweisprachige Parität über alle 18 Abschnitte mit dualen reziproken HTML-Ankern (`<a id="..."></a>`) für lückenlose Verlinkbarkeit.
  - **Zielgruppen- & Intent-Modellierung**: 4 dedizierte Personas (`[PERSONA-01]` bis `[PERSONA-04]`) sowie zweisprachige High-Intent-Suchbegriffkataloge für maximale Auffindbarkeit.
  - **Vergleichsmatrix gegenüber Alternativen**: 10-dimensionale Matrix gegen Windows File Explorer, Total Commander, Directory Opus, OneCommander und Cloud SaaS Viewer, kartiert auf die 10 Invarianten (`INV-LOCAL-01` bis `INV-SLA-10`).
  - **Duale Mermaid-Diagramme**: Ausbau der Architektur-Topologie (`flowchart TD`) und des End-to-End Verarbeitungs- und Such-Lebenszyklus (`sequenceDiagram` mit `autonumber` und null Semikolons).
  - **Rechtlicher Hinweis (§ 521 BGB Gefälligkeitsrecht)** in `README_de.md` verbindlich verankert.
  - **Metadaten- & Kontext-Aktualisierung**: `THIRD_PARTY_LICENSES.md` und `MARKETING-LOG.txt` (Abschnitt 8) auf Stand 2026-09-18 gehärtet; `llms.txt` auf Stand 2026-09-18 mit 323+ Tests und 18-Punkte-Index synchronisiert.
  - **Automatisierte Vertragstests**: `tests/test_metadata_contract.py` um 18-Punkte Schnellnavigationsprüfung und reziproke HTML-Anker-Validierung erweitert.


### Wartung & CI/CD-Härtung / Maintenance & CI Hardening (2026-09-16)
- **Repository-Hygiene & CI/CD-Automationshärtung (Pfad A)**:
  - CI-Workflow-Härtung (`.github/workflows/ci.yml`): `timeout-minutes: 15` für Testmatrix, Concurrency-Gruppe mit `cancel-in-progress: true` zur Vermeidung hängender Build-Queues.
  - Stale-Issues-Workflow (`.github/workflows/stale.yml`): `timeout-minutes: 10` und Concurrency-Gruppe hinzugefügt.
  - Welcome-Workflow (`.github/workflows/welcome.yml`): `timeout-minutes: 5` und Concurrency-Gruppe hinzugefügt.
  - Multi-Host Cloud-Sync- und Lock-Härtung in `.gitignore`: Ausschluss von `LOCK`, `uv.lock`, `!package-lock.json`, `* (copy)*`, `* (Copy)*`, `* (kopie)*`, `* (Kopie)*`, `*conflicted copy*`, `*-WORKSTATION*`, `*-ASUS*`, `*-LAPTOP*`, `*-Mac Studio*`, `*.sync-temp-*`, `*.orig`, `*.rej`, `.hypothesis/`, `.turbo/`, `wheelhouse/`, `.wheel-smoke/`, `.coverage.*`.
  - PEP 621 Standardisierung in `pyproject.toml`: `project.urls` um `"LLM Ready"` ergänzt, `[tool.pytest.ini_options]` um `minversion = "7.0"` und `addopts = "-ra -v"` ergänzt.
  - Lokales Marketing- und Audit-Register `MARKETING-LOG.txt`: Um Abschnitt 7 (Repository Hygiene & CI Contract Audit Stand 2026-09-16) erweitert.
  - Dokumentations- & Badge-Synchronisation (`README.md`, `README_de.md`, `llms.txt`): Test-Badges auf aktuellen Stand (320+ Tests / 100% grün) und `llms.txt` Last-checked Datum auf 2026-09-16 synchronisiert.
  - Erweiterung der automatisierten Vertragstestsuite in `tests/test_security_license_contract.py` und `tests/test_metadata_contract.py` um Prüfungen für CI-Guardrails (Timeouts & Concurrency), erweiterte Gitignore-Multi-Host-Muster, PEP 621 URLs und Hygiene-Log-Aktualität.

### Sicherheit & Governance / Security & Governance (2026-09-13)
- **Sicherheits- & Lizenz-Audit (Turnusgemäßer Audit-Lauf)**:
  - Härtung der Abhängigkeits-Untergrenzen in `pyproject.toml` (`pytest>=9.1.1` gegen CVE-2025-7117 / GHSA-6w46-j5rx-g56g, `ruff>=0.9.0`, `PyInstaller>=6.10.0`, `altgraph>=0.17.4`).
  - Standardisierung des Dritte-Partei-Lizenzinventars `THIRD_PARTY_LICENSES.txt` mit SPDX-Identifikatoren, Lizenztypen, Paket-URLs und detaillierten Verwendungsnachweisen für alle 21 direkten und transitiven Laufzeit-, Test- und Build-Pakete.
  - Zweisprachige Härtung der `SECURITY.md` (DE/EN) um verbindliche Reaktions-SLAs (48 Stunden Erstbestätigung, 5 Werktage Triage) sowie formelle Local-First / Zero-Egress und Non-Elevation-Garantien.
  - Multi-Host- und Geheimnis-Härtung der `.gitignore` (`secrets.*`, `*.pfx`, `*.p12`, `*.cer`, `*.crt`, `*-WORKSTATION-LG*`, `*-ASUS-GEI*`, `*.sync-conflict-*`, `*.conflict`, `LOCK.*`, `*.lock`, `node_modules/`).
  - Neue automatisierte Vertragstestsuite `tests/test_security_license_contract.py` mit 6 Prüfungen zur dauerhaften Einhaltung von Schwachstellenuntergrenzen, Lizenzschema, Dateisystem-Ausschlüssen, Hardcoded-Path-Freiheit, SLA-Vorgaben und Zero-Egress-Invarianten.
  - Gesamter Testbestand auf 317 Tests ausgebaut (100% grün, 0 Fehler).

## [1.0.5] - 2026-09-12

### Hinzugefügt / Added
- **Batch-Renamer Suite (`src/core/batch_rename_service.py`, `src/gui/batch_rename_dialog.py`) (TW-EP-10)**:
  - Vollwertige Datei-Umbenennungs-Engine mit regulären Ausdrücken (Regex) und Literal-Ersetzung (`search_str`, `replace_str`).
  - Text-Transformationen: Groß-/Kleinschreibung (`lower`, `upper`, `title`, `sentence`), Präfix- und Suffix-Steuerung.
  - Intelligente Nummerierung: Startindex, Schrittweite, konfigurierbare Nullauffüllung (Padding) und variable Positionierung (`prefix`, `suffix`, `replace`).
  - Robuste Kollisionserkennung: Zweistufige Erkennung von internen Kollisionen innerhalb des aktuellen Batches sowie Konflikten mit bestehenden Dateien auf dem Dateisystem mit Farbcodierung (grün = bereit, rot = Kollision, grau = unverändert).
  - Transaktionale Ausführung mit atomarem 1-Klick-Rollback (`rollback_rename`).
  - Interaktiver PySide6-Dialog mit Echtzeit-Live-Vorschautabelle, Validierung und Bestätigungsdialogen.
- **Side-by-Side Datei-Vergleich (Diff Viewer) (`src/core/diff_service.py`, `src/gui/diff_dialog.py`) (TW-EP-10)**:
  - Hochperformante Textvergleichs-Engine auf Basis von `difflib.SequenceMatcher` mit vollständiger Zeilen- und Status-Aufschlüsselung (`equal`, `insert`, `delete`).
  - Automatische Binärdateien-Erkennung über Nullbyte-Inspektion mit Fallback auf SHA-256 Checksummenvergleich.
  - Statistiken zu Änderungen: Anzahl hinzugefügter, gelöschter und identischer Zeilen.
  - Generierung standardkonformer Unified-Diff-Texte (`generate_unified_diff_text`) mit 1-Klick-Export in die Zwischenablage.
  - Visualisierender PySide6-Dialog mit Monospace-Schriftart, farblicher Syntaxhervorhebung (grün für Einfügungen, rot für Löschungen) und Dateipfadauswahl.
- **Dateibrowser-Erweiterungen & Schnellaktionen (`src/gui/browser/file_browser.py`, `src/gui/main_window.py`) (TW-EP-10)**:
  - "Neue Datei erstellen..." (`create_new_file`): Kollisionssichere Erstellung neuer Textdateien im aktuellen Ordner via atomarem Modus `'x'` mit Direktselektion im Browser.
  - Kontextmenü-Integration: "Mehrfach umbenennen..." (bei Auswahl > 1), "Dateien vergleichen (Diff)..." (bei Auswahl von genau 2 Dateien) sowie "Neue Datei..." im Hintergrund.
  - Menü-Verdrahtung in der Hauptmenüleiste: "Neue Datei..." (Ctrl+Shift+T) und "Mehrfach umbenennen..." (Ctrl+M) unter *Bearbeiten*; "Dateien vergleichen (Diff)..." und "Mehrfach umbenennen..." unter *Tools*.
- **Lokalisierung (Tier-2 P-006)**:
  - 71 neue UI- und Dialogschlüssel lückenlos über alle 6 Sprachen (DE, EN, ES, ZH, JA, RU) in `locales/translations.json` gepflegt (Gesamtkatalog auf 233 Einträge ausgebaut, 100% Parität bestätigt mit `manage_translations.py --check`).
- **Multi-Resolution Desktop-, Web- und Mobile-Icon-Suite (TW-EP-11)**:
  - 1024x1024 RGBA Master-Icons (`DesktopIcon.png`, `icon.png`, `assets/icon.png`, `assets/ExplorerPro.png`, `assets/DesktopIcon.png`).
  - Standardisierte 7-Layer Windows-ICOs (16x16, 24x24, 32x32, 48x48, 64x64, 128x128, 256x256, 32bpp) für Root (`ExplorerPro.ico`, `DesktopIcon.ico`, `icon.ico`) und `assets/`.
  - Vollständige Web- und Mobile/PWA-Icon-Suite in `mobile_icons/` (192x192, 512x512, maskierbar mit 80% Safe-Zone auf Slate-Theme `#0b0f19`, Apple-Touch-Icon 180x180, Favicons) und W3C-Manifest `manifest.json`.
  - Microsoft Store-Asset-Kacheln in `store_assets/` um standardisierte Pipeline-Icons (`icon_44x44.png`, `icon_50x50.png`, `icon_150x150.png`, `icon_310x150.png`, `icon_310x310.png`) erweitert bei vollständigem Erhalt der MSIX-Kacheln (`Square*Logo.png`).
  - Härtung von `src/main.py`: `load_app_icon()` mit robustem Fallback-Pfad über Root-, Assets- und Desktop-Icons.
  - PyInstaller-Spec (`ExplorerPro.spec`): Bündelung des `assets/`-Verzeichnisses in `datas`.
- **Test-Erweiterung**:
  - 25 neue automatisierte Tests (inkl. 5 Vertragstests in `tests/test_assets_and_icons.py` für 7-Layer-ICOs, Master-PNGs, PWA-Suite, Store-Tiles und Icon-Loader).
  - Gesamter Testbestand auf 311 Tests erweitert (100% grün, 0 Fehler).

## [1.0.4] - 2026-09-10

### Hinzugefügt / Added
- **Multi-Hash Checksummen-Generator & Live-Verifikation (`src/core/checksum_service.py`, `src/gui/checksum_dialog.py`)**:
  - Parallele Single-Pass-Stream-Berechnung für MD5, SHA-1, SHA-256 und SHA-512 über 64 KB Chunks mit bis zu 4-facher Geschwindigkeitssteigerung gegenüber sequenzieller Berechnung.
  - Asynchroner Hintergrund-Worker `ChecksumWorker(QThread)` mit Signalverbindung, Fortschrittsanzeige und kooperativer Thread-Stornierung bei Abbruch oder Dialogschließung.
  - Dialog zur Live-Berechnung und Integritätsprüfung: Monospace-Anzeige, Einzel- und Gesamtkopierfunktion ("Alle Prüfsummen kopieren") sowie Eingabefeld zur Verifikation von Hashes mit Toleranz ggü. Formatierungsunterschieden, Algorithmus-Präfixen und Groß-/Kleinschreibung.
  - Vollständige GUI-Verdrahtung im Kontextmenü des Dateibrowsers (`🔑 Prüfsummen berechnen...`), in der Hauptmenüleiste unter Tools und als Aktionsbutton im `MetadataPanel` der Dateidetailansicht.
- **Performance-Optimierung Duplikat-Finder (`src/modules/indexer/duplicate_finder.py`)**:
  - Zweistufige Chunk-Filterung: Vorprüfung mit 64 KB Prefix-Hash (`_compute_quick_hash`) für gleichgroße Dateien > 64 KB. Dateien mit abweichenden Datei-Headern werden ohne teures vollständiges Datei-Hashing sofort verworfen.
- **Volltextsuche & Modernisierung Indexer (`src/core/file_index.py`)**:
  - Erweiterte Volltext-Extraktion in `extract_text()` für über 30 Programmier-, Markup- und Konfigurationsformate (`.py`, `.js`, `.ts`, `.html`, `.css`, `.json`, `.yaml`, `.yml`, `.toml`, `.xml`, `.sql`, `.ini`, `.cfg`, `.sh`, `.bat`, `.ps1`, `.c`, `.cpp`, `.h`, `.log`, `.csv`, etc.).
  - Behebung von Deprecation-Warnungen durch Priorisierung von modernem `pypdf` vor `PyPDF2`.
- **Lokalisierung (Tier-2 P-006)**:
  - 100% lückenlose Übersetzung aller 8 neuen Strings in allen 6 Zielsprachen (DE, EN, ES, ZH, JA, RU) in `locales/translations.json` (Gesamt: 162 Strings, verifiziert mit `manage_translations.py --check`).
- **Test-Erweiterung**:
  - 12 neue Tests in `tests/test_checksum_service.py`, `tests/test_checksum_dialog.py`, `tests/test_duplicate_quick_hash.py` und `tests/test_file_index_expanded_text.py` (Gesamtbestand: 251 Tests, 100% bestanden).
- **Discoverability, Visual Architecture, 15-Punkte-Schnellnavigation & Metadatenvertrag (Pfad B)**:
  - **Zweisprachige README-Architektur (`README.md`, `README_de.md`)**: Ausbau auf 15-Punkte-Schnellnavigation mit 100% wechselseitiger Anker-Parität (#1-overview--value-proposition bis #15-privacy-security--license bzw. #1-ueberblick--werteversprechen bis #15-datenschutz-sicherheit--lizenz).
  - **Tabelle der 10 Governance- & Laufzeit-Invarianten**: Kanonische Dokumentation der Invarianten `INV-LOCAL-01` (100% Offline Zero-Egress) bis `INV-SLA-10` (48h Security Response & 5d Triage SLA) in beiden Dokumenten.
  - **Dritte-Partei-Lizenzinventar (`THIRD_PARTY_LICENSES.md`)**: Umfassendes Lizenzinventar für alle direkten Laufzeit- und optionalen Abhängigkeiten (PySide6 LGPL-3.0, PyMuPDF AGPL-3.0, pandas BSD-3-Clause, openpyxl MIT, PyInstaller GPL-2.0+, PyPDF2 BSD-3-Clause, xlrd BSD-3-Clause, pywin32 PSFL-2.0, pytest MIT, ruff MIT/Apache-2.0, setuptools MIT) mit Zero-Egress und unprivilegierter RunAsInvoker Non-Elevation.
  - **Lokales Marketing- & Auffindbarkeits-Log (`MARKETING-LOG.txt`)**: 4 Ziel-Personas (Desktop Power Users, Privacy & Compliance Officers, Software Developers & Researchers, Automation Engineers), High-Intent Suchbegriffe (DE/EN), tabellarische Wettbewerbsmatrix vs. Windows Explorer / Total Commander / Directory Opus / Cloud SaaS und Ökosystem-Synergien.
  - **Status-Badges & Metadaten**: Shields.io Badges für Version 1.0.4, 230+ bestandene Tests, Python 3.10-3.12, Plattformen, UI PySide6, 100% Local-First, RunAsInvoker Security, 48h SLA / 5d Triage, Third-Party Audited, Marketing Log, AGPL-3.0 Lizenz, Microsoft Store Live, LLM-Ready.
  - **Geschwister-Ökosystem-Matrix**: Ausbau auf 16 vernetzte Partner-Repositories über `file-bricks`, `doc-bricks`, `dev-bricks`, `ellmos-ai` und `open-bricks`.
  - **PEP 621 Metadaten (`pyproject.toml`)**: URLs für "Third-Party Licenses", "Marketing Log", "Parent Organization" und "Umbrella Ecosystem" integriert.
  - **Automatisierte Vertragstestsuite (`tests/test_metadata_contract.py`)**: Neue Contract-Tests für 15-Punkte-Schnellnavigation, 10 Invarianten, Third-Party Lizenzinventar, Marketing-Log und Versionsparität 1.0.4.
- **Tier-2 6-Sprachen-Ausbau & Lokalisierungsarchitektur (P-006)**:
  - **Lokalisierungskatalog (`locales/translations.json`)**: Ausbau von 36 auf 154 Schlüssel mit 100% lückenloser Übersetzung über alle 6 Zielsprachen (Deutsch, Englisch, Spanisch, Chinesisch, Japanisch, Russisch).
  - **Multi-Language-Engine (`translator.py`)**: Robuste relative Pfadauflösung (`Path(__file__).resolve().parent`), Systemsprachenerkennung ohne veraltete APIs, deterministische 4-stufige Fallback-Kette (`target -> en -> de -> key`), Klassenmethoden für UI-Display-Namen und Singleton-Zugriff `get_translator()` / `t()`.
  - **Auto-Scanner & CI-Auditing (`manage_translations.py`)**: Erweiterte Erkennung aller GUI-Muster (`setText`, `setToolTip`, `setPlaceholderText`, `QCheckBox`, `addAction`, `addTab`), vollständige 6-Sprachen-Initialisierung neuer Schlüssel, UTF-8-Terminal-Encoding-Schutz und `--check`-Prüfmodus für CI/Dev-Pipelines.
  - **Sprachauswahl im Einstellungsdialog (`src/core/settings_manager.py`, `src/gui/settings_dialog.py`)**: Speicherung der Sprachpräferenz in den Anwendungseinstellungen und ComboBox-Auswahl mit nativen Display-Namen im Reiter *Allgemein*.
  - **Automatisierte I18N-Vertragstests (`tests/test_i18n.py`)**: 11 Unittests zur Verifikation von Sprachdefinitionen, Fallback-Ketten, Systemsprachenerkennung, Katalogparität, Scanner und Einstellungsdialog.

### Behoben / Fixed
- **Erweiterte Suche & Dateiindex (`src/core/file_index.py`, `src/gui/sidebar/advanced_search_dialog.py`)**:
  - **Regex-Suche (`use_regex=True`)**: Vollständige Unterstützung für reguläre Ausdrücke über eine SQLite-Benutzerfunktion `REGEXP`. Ermöglicht komplexe Musterabfragen auf Dateinamen, Textinhalte und Pfade bei defensiver Validierung (`ValueError` bei Syntaxfehlern).
  - **Exakte Groß-/Kleinschreibung (`case_sensitive=True`)**: Respektierung der Case-Sensitivity via `INSTR(...) > 0` für Teilstrings bzw. Regex-Flags.
  - **Datumsbereichs-Grenzwerte (`date_to`)**: Schließt den vollen Tag (bis 23:59:59.999999) ein, sodass an einem gewählten Zieldatum nachmittags oder abends modifizierte Dateien nicht mehr durch ISO-Stringvergleiche (`YYYY-MM-DDTHH:MM:SS <= YYYY-MM-DD`) fälschlicherweise ausgeschlossen werden.
  - **Automatisierte Regressionstests (`tests/test_file_index_advanced_search.py`)**: 5 neue Unittests für Regex-Muster, Case-Sensitivity, Fehlerbehandlung und Datumsbereich-Grenzwerte.
- **Datenschutz & Privatsphäre (`src/modules/privacy/privacy_monitor.py`, `src/modules/privacy/blacklist_manager.py`)**:
  - **Span-basierte Redaktion & Substring-Schutz**: Ersetzung von fehleranfälligem `str.replace` durch atomare, interval-gemergte Zeichenspannen-Redaktion. Verhindert, dass Blacklist-Wörter (z. B. "anna" bei `whole_words=True`) innerhalb unbeteiligter Wörter (z. B. "johanna") fälschlicherweise ersetzt werden und sensible Treffer unmaskiert bleiben.
  - **Überlappende Muster-Erkennung**: Überlappende Treffer (z. B. E-Mail-Adresse und darin enthaltene Blacklist-Domain) werden sauber zu einem einzigen Platzhalter `[***]` konsolidiert.
  - **Whitelist-Durchsetzung in `anonymize()`**: Die Methode `anonymize()` respektiert nun ausnahmslos alle Whitelist-Einträge identisch zu `check_text()`.
  - **Strikte Groß-/Kleinschreibung**: Bei `case_sensitive=True` wird die Whitelist nun exakt unter Berücksichtigung von Groß-/Kleinschreibung ausgewertet.
  - **Robuste Datei-Exporte & Datenbereinigung**: `BlacklistManager.export_to_file()` erstellt fehlende Elternordner automatisch (`mkdir(parents=True, exist_ok=True)`). Deserialisierte leere/Whitespace-Begriffe werden in `PrivacyMonitor` und `BlacklistManager` gefiltert.
  - **Automatisierte Regressionstests (`tests/test_privacy_monitor_anonymization.py`)**: 7 neue Tests verifizieren alle behobenen Fehlerfälle.

## [1.0.3] - 2026-08-24

### Hinzugefügt / Added
- **Discoverability, README-Architektur & Dual-Mermaid-Diagramme (`README.md`, `README_de.md`)**:
  - Vollständige zweisprachige README-Architektur (Englisch & Deutsch) mit strukturierter Schnellnavigation (12 Sprungmarken) und detailliertem Werteversprechen für Power-User.
  - **Interaktive Dual-Mermaid-Diagramme**:
    - `flowchart TD`: 5-Schichten-Architekturmodell (`PySide6 UI Layer`, `Core Application Services`, `Background Indexing & Analysis Engines`, `File Operations & Safety Layer`, `Platform & Privacy Invariants`).
    - `sequenceDiagram`: End-to-End Verarbeitungs-Lebenszyklus für asynchrone Ordnernavigation & Vorschaugenerierung (PyMuPDF), FTS5-Volltextsuche und 2-Phasen Duplikatanalyse & sicheres Recycling.
  - **Visuelle Showcase-Galerie & Store-Assets**:
    - Einbindung von 4 hochauflösenden Bildschirmfotos (`main-window.png`, `search.png`, `duplicates.png`, `sync.png`) aus `README/screenshots/store/`.
  - **Tabelle der Kernfähigkeiten & Sicherheitsinvarianten**:
    - Detaillierte Matrix für 100% Offline-Betrieb (Zero-Egress), unprivilegierten User-Mode (Non-Elevation), Mehrtab-Browser, FTS5-Suche, Duplikat-Finder, Datenschutz-Monitor, Schnell-Editor, Ordnersynchronisation und 6-Sprachen-i18n.
  - **Tastaturkürzel-Matrix**:
    - Vollständige Referenztabelle aller globalen und browser-spezifischen Tastaturkürzel (Ctrl+N, Ctrl+T, Ctrl+W, Ctrl+Tab, Ctrl+F, F2, Delete, Ctrl+C, Ctrl+V, Ctrl+Shift+N, F5, Alt+Left/Right/Up, Ctrl+,, Ctrl+Q).
  - **Geschwisterwerkzeuge- & Ökosystem-Matrix**:
    - Vernetzung von ExplorerPro mit verwandten Repositories der `file-bricks`, `doc-bricks`, `dev-bricks`, `ellmos-ai` und `open-bricks` Produktfamilien.
  - **Shields.io Badges**:
    - Synchronisation aller Status-Badges (CI, Tests: 221 bestanden, Python 3.10-3.12, Plattformen: Windows | Linux | macOS, UI: PySide6 (Qt6), Datenschutz: 100% Local-First, Sicherheit: Zweisprachige Policy, Lizenz: AGPLv3, Microsoft Store: Live, LLM-Ready: llms.txt, Version: 1.0.3).
- **Erweiterte Metadaten-, Discoverability- & Offline-Vertragstests (`tests/test_metadata_contract.py`)**:
  - Neue automatisierte Contract-Tests für zweisprachige README-Parität (`test_readme_bilingual_structure_and_quick_nav`), Mermaid-Diagramm-Syntax (`test_mermaid_diagrams_syntax`), Showcase-Bilder-Integrität (`test_showcase_gallery_and_assets`), Geschwister-Ökosystem (`test_sibling_ecosystem_and_urls`), Tastaturkürzel & Fähigkeiten (`test_keyboard_shortcuts_and_capabilities_table`) und statischen Ausschluss unerlaubter Netzwerk-Imports (`test_offline_zero_egress_and_privacy_invariants`).
- **Maschinenlesbarer KI-Kontext (`llms.txt`)**:
  - Aktualisierung auf Stand 2026-08-24 mit Dokumentation der 5-Schichten-Architektur, 221+ bestandenen Tests und Microsoft Store Identität (`Geiger.ExplorerPro` / `9P0X52WSHZ3Q`).
- **Multi-OS CI Matrix Workflow (`.github/workflows/ci.yml`)**:
  - Implementierung eines vollständigen GitHub Actions CI-Workflows mit Multi-OS Matrix (`ubuntu-latest`, `windows-latest`, `macos-latest`) und Python Matrix (`['3.10', '3.11', '3.12']`).
  - Standardisierte offizielle Actions `actions/checkout@v4` und `actions/setup-python@v5` mit Pip-Caching.
  - Automatisierte Installation der Linux Qt-Laufzeitbibliotheken (`libegl1`, `libgl1`, `libxkbcommon-x11-0`, `libxcb-cursor0`), Bytecode-Kompilierung (`compileall`), Ruff-Linting und Pytest-Vollsuite mit `QT_QPA_PLATFORM: offscreen`.
- **PEP 621 Standard Classifiers & Projekt-URLs (`pyproject.toml`)**:
  - Vollständige PEP 621 Standard Classifiers (`Development Status :: 5 - Production/Stable`, `Python 3.10-3.12`, `OS Independent`, `Microsoft Windows`, `POSIX Linux`, `MacOS`, `Qt6 Desktop-Environment`, `AGPLv3`).
  - Standardisierte Projekt-URLs (`Homepage`, `Repository`, `Issues`, `Bug Tracker`, `Documentation`, `Changelog`, `Security`, `Umbrella`).
  - Erweiterte Suchbegriffe (Keywords) für Portfolio- und Paketmanager-Auffindbarkeit.
- **Zweisprachige Sicherheitsrichtlinie (`SECURITY.md`)**:
  - Vollständige zweisprachige Sicherheitsrichtlinie (Deutsch & Englisch) mit verbindlichen Garantien für Local-First & Zero-Egress (100% Offline-Betrieb, 0 Telemetrie, keine Cloud-Abhängigkeit), unprivilegierten User-Mode (Non-Elevation), destruktive Dateisicherheit (Bestätigungsdialoge, Papierkorb-Integration), isolierte SQLite/FTS5-Datenbanken und host-lokale Datenisolation.
  - Dokumentierte direkte Sicherheitskontakte (`security@file-bricks.org`, `security@ellmos.ai`, `support@lukasgeiger.com`, `lukas@open-bricks.org`) sowie GitHub Private Vulnerability Reporting Link.
- **Erweiterte Metadaten- & Governance-Vertragstests (`tests/test_metadata_contract.py`)**:
  - Neue automatisierte Contract-Tests für CI-Workflow-Integrität (`test_ci_workflow_integrity`), PEP 621 Classifiers & Projekt-URLs (`test_pyproject_pep621_classifiers_and_urls`), zweisprachige Sicherheitsrichtlinie (`test_security_policy`) und Versionsparität (`test_version_parity`).
- **Barrierefreiheit (A11y) & UX-Verbesserungen (`src/gui/`, `src/modules/`, `tests/test_ui_accessibility.py`)**:
  - **Datenschutz-Ampel & Statusleiste** (`src/gui/status_bar.py`): `PrivacyIndicator` mit `accessibleName`, `accessibleDescription`, Tastaturfokus (`StrongFocus`) und Tastaturbedienung (`Enter`/`Leertaste`); `StatusBarWidget` mit barrierefreien Attributen und dynamischer Tooltip-Synchronisation.
  - **Dateibrowser & Navigation** (`src/gui/browser/file_browser.py`): Tabellenansicht (`self.table`) mit `accessibleName`, Bedienungsanleitung für Screen-Reader und informativen Tooltips versehen.
  - **Sidebar-Komponenten** (`src/gui/sidebar/sidebar_main.py`): `TreePanel` und `FavoritesPanel` mit `accessibleName` und Strukturbeschreibungen versehen.
  - **Schnell-Editor** (`src/modules/editor/quick_editor.py`): Werkzeugleisten-Aktionen und Statusanzeigen mit barrierefreien Namen, Beschreibungen und Tooltips versehen.
  - **Duplikat-Finder** (`src/modules/indexer/duplicate_finder.py`): Alle Scan-Optionen, Ergebnisbaum und Aktionsschaltflächen mit barrierefreien Attributen versehen.
  - **Automatisierte Testsuite** (`tests/test_ui_accessibility.py`): 6 Integrationstests zur Verifikation aller A11y-Attribute und Tastatur-Interaktionen.

### Behoben / Fixed
- **Code-Hygiene & Linting (`translator.py`, `tests/`)**:
  - Unbenutzte Imports und uneindeutige Variablennamen (`l` -> `lang_code`) bereinigt. Ruff-Prüfung läuft mit 0 Fehlern über die gesamte Codebasis.

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
