# CROSSCHECK — Externe Dependencies

> Quelle: aktueller pyproject.toml-Vertrag und Source-Importscan
> Pfad: _sources/CROSSCHECK.md
> Stand: 2026-07-22

## Runtime-Abhängigkeiten mit Major-Version-Pinning

| Paket | Gepinnte Version | Lokal geprüft | Letzte Prüfung |
|---|---|---|---|
| PySide6 | >=6.5.0,<7.0.0 | 6.11.1 | 2026-07-22 |
| PyMuPDF | >=1.21.0,<2.0.0 | 1.27.2.3 | 2026-07-22 |
| pandas | >=2.0.0,<4.0.0 | 3.0.3 | 2026-07-22 |
| openpyxl | >=3.1.0,<4.0.0 | 3.1.5 | 2026-07-22 |

## Optionale Extras

| Extra | Paket | Gepinnte Version | Zweck |
|---|---|---|---|
| build | PyInstaller | >=6.0.0,<7.0.0 | Windows-EXE-Build |
| legacy-pdf | PyPDF2 | >=3.0.0,<4.0.0 | PDF-Fallback, wenn PyMuPDF fehlt |
| legacy-excel | xlrd | >=2.0.0,<3.0.0 | Vorschau historischer .xls-Dateien |
| windows-shortcuts | pywin32 | >=306 (Windows) | Auflösung von Windows-Verknüpfungen |

Nicht Teil des Release-Vertrags: QScintilla, Pygments und watchdog.

Aktuelle Versionen prüfen: python -m pip list --outdated

---

## P0 — Sicherheit / CVEs (blockiert Release)

| # | Paket | Problem | Status | Behoben in |
|---|---|---|---|---|
| — | — | — | — | — |

Quellen: PyPI, CVE MITRE und aktuelle Paketmetadaten.

---

## P1 — Breaking Changes bei Major-Update (dokumentieren vor Update)

| # | Paket | Von | Nach | Breaking Change | Aufwand |
|---|---|---|---|---|---|
| — | — | — | — | — | — |

---

## P2 — Deprecation-Warnings

| # | Paket | Warnung | Deadline | Maßnahme |
|---|---|---|---|---|
| 1 | PyPDF2 | Projekt ist bei 3.0.x eingefroren; Nachfolger ist pypdf | Vor Aktivierung des Extras | Fallback bewusst testen oder auf pypdf migrieren |

---

## P3 — Nice-to-have Features / Performance

| # | Paket | Neue Funktion | Nützlich für | Priorität |
|---|---|---|---|---|
| — | — | — | — | niedrig |

---

## Workflow

1. Vor jedem Release: Runtime- und tatsächlich gewählte Extras gegen
   THIRD_PARTY_LICENSES.txt und die Projekt-LICENSE abgleichen.
2. Quartalsmäßig: python -m pip list --outdated laufen lassen und die
   Tabelle aktualisieren.
3. Neue Deps: Runtime oder Extra im pyproject.toml deklarieren, Lizenz- und
   CVE-Status hier dokumentieren und den Build/Smoke passend erweitern.
