"""The packaged and displayed versions follow pyproject.toml."""

import json
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox

from src import __version__
from src.gui.main_window import MainWindow
from src.main import set_application_version


ROOT = Path(__file__).resolve().parents[1]


def test_runtime_about_and_package_versions_match(monkeypatch):
    app = QApplication.instance() or QApplication([])
    set_application_version(app)

    captured = {}
    monkeypatch.setattr(QMessageBox, "about", lambda _parent, _title, body: captured.setdefault("body", body))
    MainWindow._show_about(None)

    package_version = json.loads((ROOT / "store_package.json").read_text(encoding="utf-8"))["version"]
    assert app.applicationVersion() == __version__ == package_version.removesuffix(".0")
    assert f"Version {__version__}" in captured["body"]
