# ExplorerPro – Store-Fehler und Versionsstand

Stand: 08.10.2026. Der Status wurde nach dem Upload im Partner Center unabhängig zurückgelesen.

## Veröffentlichte Store-Version: 1.0.7.0

Die veröffentlichte Submission ist `1152921505701989667`. Das neu eingereichte Update ersetzt diese Version erst nach erfolgreicher Zertifizierung und Veröffentlichung durch Microsoft. Eine Installation des neuen Store-Updates ist noch nicht bestätigt.

## Eingereichtes Update: 1.0.8.0

- Submission: `1152921505702068603`.
- Status: **Certification**, keine Fehler beim Zurücklesen.
- Paket: `releases/windowsstore/v1.0.8/ExplorerPro.msix`, Architektur x64.
- SHA-256: `6f0d862f17776a433527e3c6b957b32178ed8fe6d498af1b6bd301ffda73339e`.
- GitHub-Release: [v1.0.8](https://github.com/file-bricks/ExplorerPro/releases/tag/v1.0.8), Quellcommit `affe7387a0f81622a9db321979d95140720c7c4d`.
- Die deutschen und englischen Änderungshinweise wurden im Store-Feld „Neuigkeiten in dieser Version“ gespeichert und nach dem Upload zurückgelesen.

## Enthaltene Fehlerbehebungen

Die folgenden Fehlerbehebungen sind im eingereichten Paket enthalten. „GEFIXT (GitHub)“ bleibt bis zur Veröffentlichung des neuen Store-Pakets der Status dieses Release-Protokolls.

| Ticket | Schwere | Beschreibung | Fundort | Status |
|---|---|---|---|---|
| T-20260928-288887892 | P1 | Sidebar und Vorschau können nach einem Neustart trotz aktivierter Ansicht auf Breite null bleiben. | `src/app.py`, `src/gui/main_window.py` | GEFIXT (GitHub); in 1.0.8.0 enthalten, Zertifizierung läuft |
| T-20260928-288887892 | P1 | Ein Ordnerwechsel aktualisiert den Pfad, lädt aber keine Dateizeilen; dadurch bleiben Vorschau, Umbenennen und Dateiaktionen unerreichbar. | `src/gui/browser/file_browser.py` | GEFIXT (GitHub); in 1.0.8.0 enthalten, Zertifizierung läuft |
| T-20260928-288887892 | P1 | Umbenennen und Kontextmenü-Aktionen benötigen einen Test an der gepackten Anwendung. | `src/gui/browser/file_browser.py`, Paketversion | GEFIXT (GitHub); in 1.0.8.0 enthalten, Zertifizierung läuft |
| T-20260928-288887892 | P1 | „Python-Skript ausführen“ startet im gefrorenen Build erneut ExplorerPro statt eines Python-Interpreters. | `src/modules/editor/quick_editor.py` | GEFIXT (GitHub); in 1.0.8.0 enthalten, Zertifizierung läuft |
| T-20260928-288887892 | P1 | Desktop- und EXE-Icon weichen vom neuen Store-Motiv ab; im Paket fehlt `resources.pri`. | `scripts/gen_store_icons.py`, `scripts/build_store_msix.ps1`, `store_assets/` | GEFIXT (GitHub); Paket-Gate bestanden, Zertifizierung läuft |

Zusätzlich behebt 1.0.8 das automatische Lesen von Dateiinhalten und Cloud-Dateien beim Öffnen der Eigenschaften. Prüfsummen starten ausdrücklich auf Anforderung und lassen sich sicher schließen. Text- und Ordnerstatistiken laufen mit Zeitbegrenzung. Selbst eingegebene Kategorien bleiben beim Sprachwechsel erhalten. Der Excel-Export behandelt Werte mit führendem Gleichheitszeichen als Text.

## Prüfung des eingereichten Builds

- Gesamte Python-Testsuite: **536 bestanden, 7 übersprungen**, Prozessende erfolgreich. Die übersprungenen Fälle betreffen fehlende Rechte für symbolische Links und einen Screenshot auf der Offscreen-Plattform.
- Die EXE aus dem entpackten MSIX wurde unter Windows nativ gestartet; Kernfunktionen und vier Screenshots wurden geprüft.
- Alle sechs Pre-Submit-Gates sind bestanden: Testsuite, Icons im Paket, Start und Kernfunktionen der entpackten EXE, Laufzeitabhängigkeiten, Nutzer-Sicht-OK und Versionskonsistenz. Der Receipt ist an die obige Paket-SHA-256 gebunden.
- Das Sicht-OK für die endgültigen Icon-Übersichten von ExplorerPro und ProfiPrompt wurde am 07.10.2026 erteilt.
- WACK wurde ohne Adminrechte gemäß zentraler Store-Policy übersprungen. Die Microsoft-Zertifizierung läuft.

## Versionsverlauf

### 1.0.8.0 – eingereicht am 07.10.2026 (UTC)

Bugfix-Release mit den oben dokumentierten Prüfungen und zweisprachigen Änderungshinweisen. GitHub v1.0.8 ist veröffentlicht; die Store-Veröffentlichung steht aus.

### 1.0.7.0 – veröffentlichter Store-Stand beim Release-Abschluss

Dieser Paketstand wurde vor dem Upload und danach über die Submission-API bestätigt.

### Historischer lokaler Befund vom 28.09.2026

Damals war lokal `Geiger.ExplorerPro_1.0.0.0_neutral__9jp3kxz2tnb3w` installiert; die EXE stammte vom 30.08.2026. Das damalige lokale Paket `releases/ExplorerPro.msix` hatte die Identity 1.0.6.0. Zu diesem Zeitpunkt war die spätere Einreichung noch nicht beauftragt. Dieser Befund beschreibt den damaligen Rechnerzustand.
