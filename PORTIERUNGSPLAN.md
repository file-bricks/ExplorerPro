# Portierungsplan ExplorerPro Suite

Stand: 2026-07-22

## Ergebnis der Bedingungsprüfung

Der Plan wurde aus dem damaligen Bestandscheck abgeleitet. Die folgenden Roadmap-Zeilen sind durch die aktuellen Status- und Changelog-Einträge zu lesen; offene Release-Gates bleiben ausdrücklich offen.

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

Dieses Setting erfüllt nur einen Teil des Haupt-Usecases. Mobile und Web sind kein Ersatz für ExplorerPro als Dateimanager; ohne eigenständigen belegten Workflow bleibt eine separate Companion-Anwendung No-Go.

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
| macOS | P1 Source-/Build-Smoke | Der Desktop-Usecase ist ähnlich, aber Packaging, Dateidialoge, PySide6, PyMuPDF und App-Startpfade müssen separat geprüft werden. |
| Linux | P1 Source-/Build-Smoke | Der Desktop-Usecase ist ähnlich; AppImage oder Tarball erst nach sauberem PySide6-/PyMuPDF-Smoke. |
| Web/PWA | No-Go 2026-07-22 | Browser-Sandbox verhindert den Kernnutzen; ohne eigenständigen belegten Review-Usecase wird kein separater Viewer gebaut. Der lokale JSON-Vertrag bleibt offen für spätere Neubewertung. |
| Android | Keine native Voll-App | Lokale Dateimanager-, Clipboard- und App-Launcher-Usecases passen nicht ausreichend; Neubewertung nur bei neuem, belegtem Mobile-Usecase. |
| iOS | Keine native Voll-App | iOS-Sandbox und App-Store-Regeln passen schlecht zu ExplorerPro als lokaler Datei- und Launcher-Suite. |

## Synchronisationsentscheidung

Die bestehende Ordner-Synchronisation bleibt ein Desktop-Feature für lokal gewählte Quell- und Zielordner. Eine direkte Cloud- oder Server-Synchronisierung ist aktuell kein Ziel, weil ExplorerPro private Dateipfade, Dateinamen, Indizes, Prompts und Datenschutzmuster berührt.

Für Plattformwechsel existiert ein bewusst ausgelöster, dateibasierter Export. Das implementierte Format und seine Datenschutzgrenze stehen in `EXPORTFORMAT.md`.

## Companion-Entscheidung 2026-07-22

Für eine separate Web/PWA-Anwendung gilt **No-Go**. Ein eigenständiger mobiler oder browserbasierter Review-Usecase ist nicht belegt; eine zusätzliche Anwendung würde den Wartungs- und Privacy-Scope ohne ausreichenden Nutzen vergrößern. Der lokale JSON-Vertrag bleibt als offener Austauschpunkt erhalten. Eine Neubewertung braucht einen konkreten Nutzerworkflow und bleibt auf lokalen Import ohne Upload, Server, Dateisystemaktion oder Cloud-Synchronisierung begrenzt.

## Nicht-Ziele

- Native Android- oder iOS-Voll-App als Dateimanager-Klon.
- Öffentliche Upload-Webapp für lokale Dateien, Indizes oder private Dokumente.
- Automatische Cloud-Synchronisierung von Indexdaten, Dateilisten, Prompts, Datenschutzmustern oder Sync-Profilen.
- Store-Einreichung ohne `THIRD_PARTY_LICENSES.txt`, Datenschutz-/Support-URL, Store-Screenshots, MSIX und WACK-Protokoll.

## Roadmap

| Priorität | Schritt | Ergebnis |
|---|---|---|
| P0 | Drittanbieter-Lizenzen und bestehende Security-Notizen abschließen | DONE 2026-07-22: Runtime, optionale Extras und Build-Abhängigkeit sind in `pyproject.toml`, `requirements.txt`, `THIRD_PARTY_LICENSES.txt` und `_sources/CROSSCHECK.md` konsistent; der tatsächliche Bundle-Readback bleibt Teil jedes Release-Builds. |
| P0 | Windows-Store-Basis vorbereiten | DONE 2026-06-04: `store_package.json`, Privacy-/Support-URL, `STORE_LISTING.md`, Screenshot-Inventar und `WINDOWS_STORE_PREP.md` angelegt. |
| P0 | Dediziertes Store-Screenshot-Set erzeugen | DONE 2026-06-12: `generate_store_screenshots.py` erzeugt reproduzierbar `README/screenshots/store/main-window.png`, `search.png`, `duplicates.png` und `sync.png` aus redigierten Demo-Daten. |
| P0 | Eigenes ExplorerPro-MSIX bauen und WACK-Protokoll ablegen | Offen: lokale Build-/MSIX-Prüfung, WACK-Readback und danach externe Store-Freigabe. |
| P1 | macOS-/Linux-Smokes definieren | DONE 2026-06-05: `tests/source_platform_smoke.py` prüft Offscreen-Start, Suche, Vorschau, Duplikat-Scan und Konfigurationspfade; CI läuft auf `ubuntu-latest` und `macos-latest`. |
| P1 | Exportformat implementierbar machen | DONE 2026-06-07: `src/core/export_service.py` mit `WorkspaceExporter`; Datei-Menü-Aktion Ctrl+E; 11 Unit-Tests grün. |
| P2 | Redigierten Web/PWA-Companion bewerten | DONE 2026-07-22, No-Go: kein eigenständiger belegter Usecase; der sichere JSON-Vertrag bleibt für lokalen manuellen Austausch erhalten. |
| P3 | Mobile erneut bewerten | Native Android-/iOS-Vollapps bleiben bestätigt Nicht-Ziel; nur ein separat belegter redigierter Export-Viewer wäre prüfbar. |

## Erledigter Plattformschritt 2026-06-05

- `src/core/platform_utils.py` bündelt das Desktop-Öffnen jetzt plattformgerecht:
  Windows via `os.startfile`, macOS via `open`, Linux via `xdg-open`.
- `file_browser.py`, `duplicate_finder.py` und `apps_panel.py` nutzen denselben Pfad, damit Dateifenster und Ordner-Launcher auf macOS nicht mehr am Linux-Handler hängen.
- `tests/source_platform_smoke.py` deckt auf echter Desktop-Codebasis den Start, Textvorschau mit echten Umlauten, Suchergebnis-Anzeige, Duplikat-Scan und den Konfigurationspfad ab.

## Erledigter Plattformschritt 2026-06-12

- `generate_store_screenshots.py` erzeugt reproduzierbar vier redigierte Windows-Store-Screenshots aus temporären Demo-Daten.
- Das Store-Set liegt jetzt unter `README/screenshots/store/` als `main-window.png`, `search.png`, `duplicates.png` und `sync.png`.
- `tests/test_store_screenshots.py` prüft den Generator als PNG-Smoke; `tests/test_store_materials.py` verankert die Artefakte zusätzlich in der Store-Doku.
