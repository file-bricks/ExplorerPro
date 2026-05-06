# Beitragsrichtlinie / Contributing Guide

## Deutsch

Vielen Dank für Ihr Interesse, zu ExplorerPro beizutragen.

### Wie Sie beitragen können

1. **Bug melden:** Erstellen Sie ein Issue mit dem Label `bug`.
2. **Feature vorschlagen:** Erstellen Sie ein Issue mit dem Label `enhancement`.
3. **Code beitragen:** Erstellen Sie einen Pull Request.

### Pull Requests

1. Forken Sie das Repository.
2. Erstellen Sie einen Feature-Branch: `git checkout -b feature/mein-feature`.
3. Committen Sie Ihre Änderungen: `git commit -m "Beschreibung der Änderung"`.
4. Pushen Sie den Branch: `git push origin feature/mein-feature`.
5. Erstellen Sie einen Pull Request gegen `file-bricks/ExplorerPro`.

### Developer Certificate of Origin (DCO)

Dieses Projekt verwendet den [Developer Certificate of Origin (DCO)](https://developercertificate.org/).
Bitte signieren Sie jeden Commit mit `--signoff`:

```bash
git commit --signoff -m "Beschreibung der Änderung"
```

Damit bestätigen Sie, dass Sie das Recht haben, den Code unter der Projektlizenz einzureichen.

### Code-Richtlinien

- Python: PEP 8 Stil.
- Encoding: UTF-8 für alle Textdateien.
- GUI-Framework: PySide6.
- Keine hardcoded Pfade, lokalen Benutzerdaten, API-Keys, Tokens oder Logdateien committen.
- Tests und Dokumentation aktualisieren, wenn sich Verhalten oder Bedienung ändern.

### Erste Schritte

```bash
git clone https://github.com/file-bricks/ExplorerPro.git
cd ExplorerPro
python -m pip install -r requirements.txt
python -m pytest -q
python src/main.py
```

---

## English

Thank you for your interest in contributing to ExplorerPro.

### How to Contribute

1. **Report bugs:** Create an issue with the `bug` label.
2. **Suggest features:** Create an issue with the `enhancement` label.
3. **Contribute code:** Open a pull request.

### Pull Requests

1. Fork the repository.
2. Create a feature branch: `git checkout -b feature/my-feature`.
3. Commit your changes: `git commit -m "Description of change"`.
4. Push the branch: `git push origin feature/my-feature`.
5. Open a pull request against `file-bricks/ExplorerPro`.

### Developer Certificate of Origin (DCO)

This project uses the [Developer Certificate of Origin (DCO)](https://developercertificate.org/).
Please sign off every commit:

```bash
git commit --signoff -m "Description of change"
```

This certifies that you have the right to submit the code under the project license.

### Code Guidelines

- Python: PEP 8 style.
- Encoding: UTF-8 for all text files.
- GUI framework: PySide6.
- Do not commit hardcoded paths, local user data, API keys, tokens, or log files.
- Update tests and documentation when behavior or usage changes.

### Getting Started

```bash
git clone https://github.com/file-bricks/ExplorerPro.git
cd ExplorerPro
python -m pip install -r requirements.txt
python -m pytest -q
python src/main.py
```
