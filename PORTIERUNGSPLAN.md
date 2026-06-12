# Portierungsplan ExplorerPro Suite

Stand: 2026-05-29

## Ergebnis der Bedingungsprüfung

Ein eigener Portierungsplan war nicht vorhanden. Dieser Lauf folgt daher Pfad B und legt den ersten usecase-basierten Plan an. Es wurden keine Codeänderungen vorgenommen.

## Features der besten Version

ExplorerPro bündelt eine lokale Power-User-Dateiverwaltung:

- Mehrtab-Dateibrowser mit Breadcrumbs, Kontextmenüs und Vorschau.
- Vorschau für PDFs, Bilder, Quellcode und Textdateien.
- Volltext- und Metadatenindex mit Suche, Filterung und Dateiüberwachung.
- Duplikat-Finder auf Hash-Basis.
- Datenschutzmonitor für Zwischenablage, Blacklist, Whitelist und sensible Muster.
- Schnell-Editor mit Syntaxhervorhebung.
- App-Launcher, Prompt-Sammlung und lokale Ordner-Synchronisation.
- Nutzerkonfigurationen in lokalen JSON-Dateien unter `.explorerpro`.

## Abgeleitete Usecases

### Usecase-Setting 1: Desktop-Arbeitsplatz

Nutzer: Power User, Entwickler, Wissensarbeiter und Projektbetreuer mit vielen lokalen Dateien.

Usecases:

- Lokale Projekt-, Dokument- und Download-Ordner schnell durchsuchen.
- PDFs, Bilder, Text und Code prüfen, ohne ständig externe Programme zu wechseln.
- Duplikate und große lokale Datenbestände bereinigen.
- Sensible Inhalte vor Copy-Paste, Veröffentlichung oder KI-Nutzung erkennen.
- Häufige Apps, Prompts und Sync-Paare als Arbeitsumgebung bündeln.

Dieses Setting braucht echten Dateisystemzugriff, native Dateidialoge, lokale Indizes, Desktop-Clipboard und externe Programme. Es ist daher ein Voll-App-Usecase für Desktop-Betriebssysteme.

### Usecase-Setting 2: Mobile oder Web-Review

Nutzer: dieselbe Person, aber unterwegs oder auf einem Zweitgerät.

Usecases:

- Redigierte Such-, Datenschutz- oder Duplikatberichte lesen.
- Prompts, App-Listen oder Sync-Profile ansehen.
- Kleine Planungsnotizen zu einem Export ergänzen.

Dieses Setting erfüllt nur einen Teil des Haupt-Usecases. Mobile und Web sind daher kein Ersatz für ExplorerPro als Dateimanager, sondern höchstens ein Companion für redigierte Berichte und Einstellungen.

### Usecase-Setting 3: Release und Store-Vertrieb

Nutzer: Maintainer, Tester und Store-Nutzer.

Usecases:

- Windows-Build zuverlässig starten, testen und verpacken.
- Lizenz-, Datenschutz- und Store-Anforderungen transparent erfüllen.
- macOS- und Linux-Tauglichkeit realistisch prüfen, ohne sofort drei voll gepflegte Release-Linien zu versprechen.

## Plattformentscheidung

| Plattform | Entscheidung | Begründung |
|---|---|---|
| Windows | Hauptplattform und Store-Kandidat | Beste Passung für Explorer-, Clipboard-, App-Launcher- und lokale Sync-Workflows. Windows Store bleibt sinnvoll, aber erst nach Store-Artefakten, Drittanbieter-Lizenzdatei und AGPL-/PyMuPDF-Transparenz. |
| macOS | P1 Source-/Build-Smoke | Der Desktop-Usecase ist ähnlich, aber Packaging, Dateidialoge, QScintilla, PyMuPDF und App-Startpfade müssen separat geprüft werden. |
| Linux | P1 Source-/Build-Smoke | Der Desktop-Usecase ist ähnlich; AppImage oder Tarball erst nach sauberem PySide6-/QScintilla-/PyMuPDF-Smoke. |
| Web/PWA | P2 Companion, kein Dateimanager-Klon | Browser-Sandbox verhindert den Kernnutzen. Sinnvoll ist nur ein redigierter Report-/Profil-Viewer für `explorerpro-workspace-v1.json`. |
| Android | P3 über Web/PWA-Companion, keine native Voll-App | Lokale Dateimanager-, Clipboard- und App-Launcher-Usecases passen nicht ausreichend. Native App nur bei neuem, belegtem Mobile-Usecase. |
| iOS | P3 über Web/PWA-Companion, keine native Voll-App | iOS-Sandbox und App-Store-Regeln passen schlecht zu ExplorerPro als lokaler Datei- und Launcher-Suite. |

## Synchronisationsentscheidung

Die bestehende Ordner-Synchronisation bleibt ein Desktop-Feature für lokal gewählte Quell- und Zielordner. Eine direkte Cloud- oder Server-Synchronisierung ist aktuell kein Ziel, weil ExplorerPro private Dateipfade, Dateinamen, Indizes, Prompts und Datenschutzmuster berührt.

Für Plattformwechsel und einen späteren Companion ist ausschließlich ein bewusst ausgelöster, dateibasierter Export geplant. Das vorgesehene Format steht in `EXPORTFORMAT.md`.

## Nicht-Ziele

- Native Android- oder iOS-Voll-App als Dateimanager-Klon.
- Öffentliche Upload-Webapp für lokale Dateien, Indizes oder private Dokumente.
- Automatische Cloud-Synchronisierung von Indexdaten, Dateilisten, Prompts, Datenschutzmustern oder Sync-Profilen.
- Store-Einreichung ohne `THIRD_PARTY_LICENSES.txt`, Datenschutz-/Support-URL, Store-Screenshots, MSIX und WACK-Protokoll.

## Roadmap

| Priorität | Schritt | Ergebnis |
|---|---|---|
| P0 | Drittanbieter-Lizenzen und bestehende Security-Notizen abschließen | `THIRD_PARTY_LICENSES.txt` vorhanden; QScintilla/PyMuPDF/Pygments/PySide6 sauber dokumentiert. |
| P0 | Windows-Store-Basis vorbereiten | DONE 2026-06-04: `store_package.json`, Privacy-/Support-URL, `STORE_LISTING.md`, Screenshot-Inventar und `WINDOWS_STORE_PREP.md` angelegt. |
| P0 | Dediziertes Store-Screenshot-Set erzeugen | DONE 2026-06-12: `generate_store_screenshots.py` erzeugt reproduzierbar `README/screenshots/store/main-window.png`, `search.png`, `duplicates.png` und `sync.png` aus redigierten Demo-Daten. |
| P1 | macOS-/Linux-Smokes definieren | DONE 2026-06-05: `tests/source_platform_smoke.py` prüft Offscreen-Start, Suche, Vorschau, Duplikat-Scan und Konfigurationspfade; CI läuft auf `ubuntu-latest` und `macos-latest`. |
| P1 | Exportformat implementierbar machen | DONE 2026-06-07: `src/core/export_service.py` mit `WorkspaceExporter`; Datei-Menü-Aktion Ctrl+E; 11 Unit-Tests grün. |
| P2 | Web/PWA-Companion entscheiden | Nur starten, wenn der Export real existiert und ein redigierter Review-Workflow belegbar ist. |
| P3 | Mobile erneut bewerten | Android/iOS erst prüfen, wenn ein eigenständiger mobiler Usecase dokumentiert ist. |

## Erledigter Plattformschritt 2026-06-05

- `src/core/platform_utils.py` bündelt das Desktop-Öffnen jetzt plattformgerecht:
  Windows via `os.startfile`, macOS via `open`, Linux via `xdg-open`.
- `file_browser.py`, `duplicate_finder.py` und `apps_panel.py` nutzen denselben Pfad, damit Dateifenster und Ordner-Launcher auf macOS nicht mehr am Linux-Handler hängen.
- `tests/source_platform_smoke.py` deckt auf echter Desktop-Codebasis den Start, Textvorschau mit echten Umlauten, Suchergebnis-Anzeige, Duplikat-Scan und den Konfigurationspfad ab.

## Erledigter Plattformschritt 2026-06-12

- `generate_store_screenshots.py` erzeugt reproduzierbar vier redigierte Windows-Store-Screenshots aus temporären Demo-Daten.
- Das Store-Set liegt jetzt unter `README/screenshots/store/` als `main-window.png`, `search.png`, `duplicates.png` und `sync.png`.
- `tests/test_store_screenshots.py` prüft den Generator als PNG-Smoke; `tests/test_store_materials.py` verankert die Artefakte zusätzlich in der Store-Doku.
