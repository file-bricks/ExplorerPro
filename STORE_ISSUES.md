# ExplorerPro – Store-Fehler und Versionsstand

## Installierte Store-Version: 1.0.0.0

Lokaler Paketbefund vom 28.09.2026: `Geiger.ExplorerPro_1.0.0.0_neutral__9jp3kxz2tnb3w`; die enthaltene `ExplorerPro.exe` stammt vom 30.08.2026. Das lokal gebaute Paket `releases/ExplorerPro.msix` hat dagegen die Identity `1.0.6.0` und eine andere EXE. Ein neuer Store-Release ist mit diesem Befund nicht belegt.

## Offene Fehler

| Ticket | Schwere | Beschreibung | Fundort | Status |
|---|---|---|---|---|
| T-20260928-288887892 | P1 | Sidebar und Vorschau können nach einem Neustart trotz aktivierter Ansicht auf Breite null bleiben. | `src/app.py`, `src/gui/main_window.py` | IN ARBEIT |
| T-20260928-288887892 | P1 | Ein Ordnerwechsel aktualisiert den Pfad, lädt aber keine Dateizeilen; dadurch bleiben Vorschau, Umbenennen und Dateiaktionen unerreichbar. | `src/gui/browser/file_browser.py` | IN ARBEIT |
| T-20260928-288887892 | P1 | Umbenennen und Kontextmenü-Aktionen müssen am installierten Paket und am neuen Build tatsächlich ausgelöst werden; der installierte Binärstand enthält den Fix vom 26.09.2026 nicht. | `src/gui/browser/file_browser.py`, Paketversion | IN ARBEIT |
| T-20260928-288887892 | P1 | „Python-Skript ausführen“ startet im gefrorenen Build erneut ExplorerPro statt eines Python-Interpreters. | `src/modules/editor/quick_editor.py` | IN ARBEIT |

## Geplanter nächster Build: 1.0.7.0

Der lokale Build und der Test der entpackten Anwendung gehören zum Ticket. Eine Store-Einreichung ist nicht beauftragt. Vor einer späteren Einreichung sind die Icon-Collage und das Sicht-OK des Nutzers erforderlich.
