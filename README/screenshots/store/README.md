# Store-Screenshots

Stand: 2026-07-18

## Reproduzierbare Erzeugung

```powershell
python generate_store_screenshots.py
```

Der Generator verwendet bewusst redigierte Demo-Daten in einem temporären
Arbeitsbereich. So bleiben private Dateinamen, echte Pfade und lokale Inhalte
aus dem finalen Store-Set heraus.

## Enthaltenes Screenshot-Set

1. `main-window.png` - Hauptfenster mit Dateibrowser, Breadcrumbs und Vorschau
2. `search.png` - Suchansicht mit aktiven Ergebnissen
3. `duplicates.png` - Duplikatsuche mit gefundener Gruppe
4. `sync.png` - Sync-Ansicht mit vorbereiteten Paaren

## Qualitätsregeln

- Keine privaten Dateinamen, Pfade oder Dokumentinhalte im finalen Screenshot-Set
- Möglichst konsistente Fenstergröße und helle, gut lesbare Oberfläche
- Keine temporären Testordner oder Build-Artefakte sichtbar
