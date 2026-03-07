# ExplorerPro Suite

An advanced file explorer with privacy monitor, preview panel, sync manager, and integrated code editor.

## Features

- **File Browser** with multi-tab support and breadcrumb navigation
- **Preview Panel** for PDF, images, code, and text
- **Privacy Monitor** -- detection and management of sensitive files
- **Advanced Search** with filters (type, size, date)
- **Duplicate Finder** via file hashes
- **Quick Editor** with syntax highlighting (QScintilla + Pygments)
- **Prompt Launcher** for AI prompts
- **Sync Manager** for folder synchronization
- **App Launcher** for quick access
- **Status Bar** with file statistics and privacy status

## Architecture

```
ExplorerPro Suite v1.0
├── src/
│   ├── core/           Event bus, file index, settings
│   ├── gui/
│   │   ├── browser/    File browser with table view
│   │   ├── preview/    Preview panel (PDF, images, code)
│   │   └── sidebar/    Sidebar with search and navigation
│   └── modules/
│       ├── editor/     Quick editor with syntax highlighting
│       ├── indexer/    Duplicate finder
│       ├── launcher/   App launcher
│       ├── privacy/    Privacy monitor and blacklist
│       ├── prompts/    Prompt management
│       └── sync/       Sync manager
```

Full architecture: [ARCHITEKTUR.md](ARCHITEKTUR.md)

## Installation

### Prerequisites

- Python >= 3.8
- PyQt6

### Setup

```bash
pip install -r requirements.txt
```

## Usage

```bash
python src/main.py
```

Or via the batch file:

```bash
START_ExplorerPro.bat
```

## Dependencies

| Package | Purpose |
|---------|---------|
| PyQt6 | GUI framework |
| PyQt6-QScintilla | Code editor |
| PyMuPDF | PDF preview |
| watchdog | File monitoring |
| Pygments | Syntax highlighting |
| pandas | Table import |

## License

AGPL v3 - See [LICENSE](LICENSE)

This project uses PyQt6 (GPL) and PyMuPDF (AGPL).

---

**Version:** 1.0.0
**Autor:** Lukas Geiger
**Letzte Aktualisierung:** Maerz 2026

---

## English

An advanced file explorer with preview, duplicate finder, privacy monitor, and integrated editor.

### Features

- Multi-tab file browsing
- File preview (images, text, PDF)
- Duplicate finder
- Privacy monitor
- Integrated text editor

### Installation

```bash
git clone https://github.com/lukisch/REL-PUB_ExplorerPro_SUITE.git
cd REL-PUB_ExplorerPro_SUITE
pip install -r requirements.txt
python "src/main.py"
```

### License

See [LICENSE](LICENSE) for details.
