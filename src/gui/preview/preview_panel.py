#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PreviewPanel - Vorschau-Panel für Dateien
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QLabel, QScrollArea, QGroupBox, QFormLayout, QLineEdit,
    QPlainTextEdit, QFrame,
    QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import (
    QPixmap, QImage, QImageReader, QFont, QSyntaxHighlighter, QTextCharFormat, QColor,
)
import logging
import os
from datetime import datetime
from pathlib import Path

from core.file_attributes import is_cloud_placeholder
from core.shortcut_utils import build_shortcut_preview_target, is_windows_shortcut
from core.ui_translator import NO_TRANSLATE
from translator import t

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.ico', '.tif', '.tiff'}
TEXT_EXTENSIONS = {
    '.txt', '.md', '.py', '.pyw', '.js', '.html', '.htm', '.css', '.json',
    '.xml', '.sql', '.c', '.cpp', '.h', '.hpp', '.java', '.ini', '.cfg', '.conf',
    '.log', '.yml', '.yaml', '.toml', '.sh', '.bat', '.cmd', '.ps1',
    '.csv', '.tsv', '.env', '.gitignore', '.editorconfig',
    '.rs', '.go', '.ts', '.tsx', '.jsx', '.vue', '.svelte', '.kt', '.cs', '.swift',
    '.r', '.rb', '.php', '.lua', '.tex', '.bib', '.cmake', '.rst', '.properties',
}
# Bilder werden höchstens in dieser Kantenlänge dekodiert (Speicher/Tempo).
MAX_IMAGE_EDGE = 2048
# PDF-Seiten werden höchstens in dieser Breite gerendert.
MAX_PDF_WIDTH = 1600


def _preview_setting(key: str, default):
    try:
        from core.settings_manager import SettingsManager

        return SettingsManager.instance().get("preview", key, default)
    except Exception:
        return default


def _looks_like_text(path: str) -> bool:
    """Erkennt Textdateien ohne bekannte Endung (README, Makefile, *.conf ...)."""
    try:
        with open(path, 'rb') as f:
            sample = f.read(4096)
    except OSError:
        return False
    if not sample:
        return True
    if sample.startswith((b'\xff\xfe', b'\xfe\xff', b'\xef\xbb\xbf')):
        return True
    if b'\x00' in sample:
        return False
    try:
        sample.decode('utf-8')
        return True
    except UnicodeDecodeError as exc:
        # Abgeschnittenes Mehrbyte-Zeichen am Ende des Ausschnitts ist ok.
        return exc.start >= len(sample) - 3

# Optionale Imports
try:
    import fitz  # PyMuPDF
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False


class PythonHighlighter(QSyntaxHighlighter):
    """Einfacher Python Syntax-Highlighter"""

    KEYWORDS = [
        'and', 'as', 'assert', 'async', 'await', 'break', 'class', 'continue',
        'def', 'del', 'elif', 'else', 'except', 'finally', 'for', 'from',
        'global', 'if', 'import', 'in', 'is', 'lambda', 'None', 'nonlocal',
        'not', 'or', 'pass', 'raise', 'return', 'True', 'False', 'try',
        'while', 'with', 'yield'
    ]

    def __init__(self, parent=None):
        super().__init__(parent)

        self.keyword_format = QTextCharFormat()
        self.keyword_format.setForeground(QColor("#569CD6"))
        self.keyword_format.setFontWeight(QFont.Weight.Bold)

        self.string_format = QTextCharFormat()
        self.string_format.setForeground(QColor("#CE9178"))

        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QColor("#6A9955"))

        self.function_format = QTextCharFormat()
        self.function_format.setForeground(QColor("#DCDCAA"))

    def highlightBlock(self, text):
        import re

        # Keywords
        for word in self.KEYWORDS:
            pattern = r'\b' + word + r'\b'
            for match in re.finditer(pattern, text):
                self.setFormat(match.start(), match.end() - match.start(), self.keyword_format)

        # Strings
        for pattern in [r'"[^"]*"', r"'[^']*'"]:
            for match in re.finditer(pattern, text):
                self.setFormat(match.start(), match.end() - match.start(), self.string_format)

        # Comments
        if '#' in text:
            idx = text.index('#')
            self.setFormat(idx, len(text) - idx, self.comment_format)

        # Functions
        for match in re.finditer(r'\bdef\s+(\w+)', text):
            start = match.start(1)
            length = len(match.group(1))
            self.setFormat(start, length, self.function_format)


class ImagePreview(QLabel):
    """Bild-Vorschau"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(200, 200)
        self._original_pixmap = None

    def load_image(self, path: str):
        """Lädt und zeigt ein Bild (verkleinert dekodiert, EXIF-Drehung beachtet)"""
        self._original_pixmap = None
        self.clear()
        try:
            reader = QImageReader(path)
            reader.setAutoTransform(True)
            size = reader.size()
            if size.isValid() and max(size.width(), size.height()) > MAX_IMAGE_EDGE:
                reader.setScaledSize(size.scaled(
                    QSize(MAX_IMAGE_EDGE, MAX_IMAGE_EDGE), Qt.AspectRatioMode.KeepAspectRatio
                ))
            image = reader.read()
            pixmap = QPixmap.fromImage(image) if not image.isNull() else QPixmap(path)
            if pixmap.isNull():
                self.setText(t("Bild konnte nicht geladen werden"))
                return

            self._original_pixmap = pixmap
            self._scale_to_fit()
        except Exception as e:
            self._original_pixmap = None
            self.setText(t("Fehler: {error}").format(error=e))

    def _scale_to_fit(self):
        if self._original_pixmap and not self._original_pixmap.isNull():
            sz = self.size()
            if sz.width() > 0 and sz.height() > 0:
                scaled = self._original_pixmap.scaled(
                    sz,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.setPixmap(scaled)

    def resizeEvent(self, event):
        self._scale_to_fit()
        super().resizeEvent(event)


class TextPreview(QPlainTextEdit):
    """Text/Code-Vorschau"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        font = QFont("Consolas", 10)
        self.setFont(font)

        self._highlighter = None

    def load_file(self, path: str):
        """Lädt eine Textdatei"""
        # Altes Highlighting sicher lösen
        if self._highlighter is not None:
            self._highlighter.setDocument(None)
            self._highlighter = None

        try:
            with open(path, 'rb') as f:
                raw = f.read(100000)  # Max 100KB

            # Robuste Erkennung verschiedener Text-Encodings (BOMs & Fallbacks)
            if raw.startswith(b'\xff\xfe'):
                content = raw.decode('utf-16-le', errors='replace')
            elif raw.startswith(b'\xfe\xff'):
                content = raw.decode('utf-16-be', errors='replace')
            elif raw.startswith(b'\xef\xbb\xbf'):
                content = raw.decode('utf-8-sig', errors='replace')
            elif b'\x00' in raw:
                try:
                    content = raw.decode('utf-16-le')
                except UnicodeDecodeError:
                    try:
                        content = raw.decode('utf-16-be')
                    except UnicodeDecodeError:
                        content = raw.decode('utf-8', errors='replace')
            else:
                try:
                    content = raw.decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        content = raw.decode('cp1252')
                    except UnicodeDecodeError:
                        content = raw.decode('utf-8', errors='replace')

            self.setPlainText(content)

            # Syntax-Highlighting
            ext = os.path.splitext(path)[1].lower()
            try:
                from modules.editor.syntax_highlighter import get_lexer_for_extension
                lexer_cls = get_lexer_for_extension(ext)
                if lexer_cls:
                    self._highlighter = lexer_cls(self.document())
                elif ext == '.py':
                    self._highlighter = PythonHighlighter(self.document())
                else:
                    self._highlighter = None
            except Exception:
                if ext == '.py':
                    self._highlighter = PythonHighlighter(self.document())
                else:
                    self._highlighter = None

        except Exception as e:
            if self._highlighter is not None:
                self._highlighter.setDocument(None)
                self._highlighter = None
            self.setPlainText(t("Fehler beim Laden: {error}").format(error=e))


class DirectoryPreview(QPlainTextEdit):
    """Read-only preview for folders and resolved shortcut targets."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setFont(QFont("Consolas", 10))

    def load_directory(self, path: str, heading: str | None = None):
        folder = Path(path)
        lines = [heading or t("Ordner: {path}").format(path=folder), ""]

        try:
            entries = sorted(
                folder.iterdir(),
                key=lambda item: (not item.is_dir(), item.name.lower()),
            )
        except OSError as exc:
            self.setPlainText(
                t("Ordner konnte nicht gelesen werden:") + f"\n{folder}\n\n{exc}"
            )
            return

        if not entries:
            lines.append(t("(leer)"))
        else:
            for entry in entries[:200]:
                marker = "[DIR]" if entry.is_dir() else "     "
                lines.append(f"{marker} {entry.name}")
            if len(entries) > 200:
                lines.append(t("... {count} weitere Einträge").format(count=len(entries) - 200))

        self.setPlainText("\n".join(lines))


class PdfPreview(QScrollArea):
    """PDF-Vorschau (erste Seite)"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)

        self.content = QLabel()
        self.content.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self.setWidget(self.content)

    def load_pdf(self, path: str):
        """Lädt ein PDF und zeigt die erste Seite"""
        self.content.clear()
        if not HAS_FITZ:
            self.content.setText(t("PyMuPDF nicht installiert.\nPDF-Vorschau nicht verfügbar."))
            return

        try:
            doc = fitz.open(path)
            try:
                if len(doc) > 0:
                    page = doc[0]
                    zoom = 1.5
                    try:
                        width = float(page.rect.width)
                        if width > 0:
                            zoom = max(0.2, min(1.5, MAX_PDF_WIDTH / width))
                    except (AttributeError, TypeError, ValueError):
                        pass
                    mat = fitz.Matrix(zoom, zoom)
                    pix = page.get_pixmap(matrix=mat, alpha=False)

                    # Puffer explizit halten und das Bild kopieren: QImage
                    # referenziert sonst Speicher, den PyMuPDF wieder freigibt.
                    samples = pix.samples
                    img = QImage(
                        samples,
                        pix.width,
                        pix.height,
                        pix.stride,
                        QImage.Format.Format_RGB888
                    ).copy()

                    pixmap = QPixmap.fromImage(img)
                    self.content.setPixmap(pixmap)
                else:
                    self.content.setText(t("Leeres PDF"))
            finally:
                doc.close()
        except Exception as e:
            self.content.setText(t("Fehler beim Laden: {error}").format(error=e))


class MetadataPanel(QWidget):
    """Metadaten-Anzeige"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_path = None
        self._file_index = None
        self._loaded_user_data = ("", "")
        self._setup_ui()

    def set_file_index(self, file_index):
        """Verbindet das Panel mit dem Index, in dem Tags und Notizen gespeichert werden."""
        self._file_index = file_index

    def _user_data(self) -> tuple:
        return (self.tags_edit.text().strip(), self.notes_edit.toPlainText())

    def save_user_data(self):
        """Speichert geänderte Tags/Notizen der angezeigten Datei im Index."""
        if not self._file_index or not self._current_path:
            return
        tags, notes = self._user_data()
        if (tags, notes) == self._loaded_user_data:
            return
        try:
            self._file_index.set_tags(self._current_path, tags.split(","))
            self._file_index.set_note(self._current_path, notes)
        except Exception as exc:  # z. B. "database is locked" während einer Indizierung
            logging.warning("Tags/Notizen konnten nicht gespeichert werden: %s", exc)
            return
        self._loaded_user_data = (tags, notes)

    def _load_user_data(self, path: str):
        tags, notes = "", ""
        if self._file_index:
            try:
                tags = ", ".join(self._file_index.get_tags(path))
                notes = self._file_index.get_note(path)
            except Exception as exc:
                logging.warning("Tags/Notizen konnten nicht gelesen werden: %s", exc)
        self.tags_edit.setText(tags)
        self.notes_edit.setPlainText(notes)
        self._loaded_user_data = self._user_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Datei-Info
        info_group = QGroupBox("📊 Datei-Information")
        info_layout = QFormLayout(info_group)

        self.name_label = QLabel("-")
        self.name_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.name_label.setWordWrap(True)
        info_layout.addRow("Name:", self.name_label)

        self.type_label = QLabel("-")
        info_layout.addRow("Typ:", self.type_label)

        self.size_label = QLabel("-")
        info_layout.addRow("Größe:", self.size_label)

        self.modified_label = QLabel("-")
        info_layout.addRow("Geändert:", self.modified_label)

        self.created_label = QLabel("-")
        info_layout.addRow("Erstellt:", self.created_label)

        # Werte sind Nutzerdaten (Dateinamen); nie automatisch übersetzen.
        for label in (self.name_label, self.type_label, self.size_label,
                      self.modified_label, self.created_label):
            label.setProperty(NO_TRANSLATE, True)

        self.checksum_btn = QPushButton("🔑 Berechnen...")
        self.checksum_btn.setAccessibleName("Prüfsummen berechnen")
        self.checksum_btn.setAccessibleDescription("Öffnet den Dialog zur Berechnung und Verifizierung von Hash-Prüfsummen.")
        self.checksum_btn.setToolTip("Prüfsummen (MD5, SHA-1, SHA-256) anzeigen und verifizieren")
        self.checksum_btn.clicked.connect(self._open_checksums)
        info_layout.addRow("Prüfsummen:", self.checksum_btn)

        layout.addWidget(info_group)

        # Tags
        tags_group = QGroupBox("🏷️ Tags")
        tags_layout = QVBoxLayout(tags_group)

        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("Tags hinzufügen (kommagetrennt)")
        self.tags_edit.setAccessibleName("Metadaten-Tags")
        self.tags_edit.setToolTip(t("Kommagetrennte Tags für die Datei eingeben"))
        self.tags_edit.editingFinished.connect(self.save_user_data)
        tags_layout.addWidget(self.tags_edit)

        layout.addWidget(tags_group)

        # Notizen
        notes_group = QGroupBox("📝 Notizen")
        notes_layout = QVBoxLayout(notes_group)

        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setMaximumHeight(100)
        self.notes_edit.setPlaceholderText("Notizen zur Datei...")
        self.notes_edit.setAccessibleName("Datei-Notizen")
        self.notes_edit.setToolTip(t("Freitextnotizen zur Datei eingeben"))
        notes_layout.addWidget(self.notes_edit)

        layout.addWidget(notes_group)

        layout.addStretch()

    def clear_metadata(self):
        """Setzt die Metadaten-Anzeige vollständig zurück."""
        self.save_user_data()
        self.name_label.setText("-")
        self.type_label.setText("-")
        self.size_label.setText("-")
        self.modified_label.setText("-")
        self.created_label.setText("-")
        self.tags_edit.clear()
        self.notes_edit.clear()
        self._current_path = None
        if hasattr(self, "checksum_btn"):
            self.checksum_btn.setEnabled(False)

    def show_metadata(self, path: str):
        """Zeigt Metadaten einer Datei"""
        self.save_user_data()
        if not path or not os.path.exists(path):
            self.clear_metadata()
            return

        try:
            stat = os.stat(path)
        except OSError:
            self.clear_metadata()
            self.name_label.setText(os.path.basename(path))
            self.type_label.setText(t("Nicht lesbar"))
            return

        name = os.path.basename(path)
        ext = os.path.splitext(name)[1].lower()

        self.name_label.setText(name)
        if os.path.isdir(path):
            type_text = t("Ordner")
        else:
            type_text = ext or t("Unbekannt")
            if is_cloud_placeholder(path):
                type_text += " · ☁️ " + t("nur online")
        self.type_label.setText(type_text)

        # Größe formatieren
        size = stat.st_size
        if size < 1024:
            size_str = f"{size} B"
        elif size < 1024 * 1024:
            size_str = f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            size_str = f"{size / (1024*1024):.2f} MB"
        else:
            size_str = f"{size / (1024*1024*1024):.2f} GB"
        self.size_label.setText(size_str)

        # Zeitstempel sicher formatieren (resistent gegen negative Zeitstempel auf Windows)
        try:
            if stat.st_mtime >= 0:
                modified = datetime.fromtimestamp(stat.st_mtime)
                self.modified_label.setText(modified.strftime("%d.%m.%Y %H:%M"))
            else:
                self.modified_label.setText("-")
        except (OSError, ValueError, OverflowError):
            self.modified_label.setText("-")

        try:
            if stat.st_ctime >= 0:
                created = datetime.fromtimestamp(stat.st_ctime)
                self.created_label.setText(created.strftime("%d.%m.%Y %H:%M"))
            else:
                self.created_label.setText("-")
        except (OSError, ValueError, OverflowError):
            self.created_label.setText("-")

        self._current_path = path
        self._load_user_data(path)
        if hasattr(self, "checksum_btn"):
            self.checksum_btn.setEnabled(os.path.isfile(path))

    def _open_checksums(self):
        """Öffnet den Prüfsummen-Dialog für die aktuell angezeigte Datei."""
        if hasattr(self, "_current_path") and self._current_path and os.path.isfile(self._current_path):
            from gui.checksum_dialog import ChecksumDialog

            dlg = ChecksumDialog(self._current_path, self.window())
            dlg.exec()


class ExcelPreview(QWidget):
    """Read-only-Vorschau für .xlsx- und .xls-Dateien.

    Zeigt eine Arbeitsblatt-Auswahl (Dropdown) und die ersten Zeilen/Spalten
    in einer Tabelle. Bei fehlender Bibliothek oder Lesefehler erscheint
    ein klar beschrifteter Fallback mit „Extern öffnen"-Schaltfläche.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._path: str | None = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Kopfzeile: Arbeitsblatt-Auswahl
        header = QHBoxLayout()
        header.addWidget(QLabel("Arbeitsblatt:"))

        self.sheet_combo = QComboBox()
        self.sheet_combo.setProperty(NO_TRANSLATE, True)  # Blattnamen sind Nutzerdaten
        self.sheet_combo.setMinimumWidth(120)
        self.sheet_combo.setAccessibleName("Excel-Arbeitsblatt")
        self.sheet_combo.setToolTip(t("Arbeitsblatt der Excel-Arbeitsmappe auswählen"))
        self.sheet_combo.currentTextChanged.connect(self._on_sheet_changed)
        header.addWidget(self.sheet_combo, 1)

        self.open_extern_btn = QPushButton("Extern öffnen")
        self.open_extern_btn.setAccessibleName("In externer Anwendung öffnen")
        self.open_extern_btn.setToolTip(t("Öffnet die Excel-Datei im Standardprogramm"))
        self.open_extern_btn.setVisible(False)
        self.open_extern_btn.clicked.connect(self._open_extern)
        header.addWidget(self.open_extern_btn)

        layout.addLayout(header)

        # Statuszeile (Fehler / Fallback-Hinweis)
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.status_label.setAccessibleName("Vorschau-Hinweis")
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)

        # Datentabelle
        self.table = QTableWidget()
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setAccessibleName("Tabellenvorschau")
        self.table.setAccessibleDescription("Vorschautabelle der Excel-Zellendaten.")
        layout.addWidget(self.table, 1)

    def load_file(self, path: str):
        """Lädt eine Excel-Datei und zeigt das erste Arbeitsblatt an."""
        from core.xlsx_reader import read_workbook_meta

        self._path = path
        self.sheet_combo.blockSignals(True)
        self.sheet_combo.clear()

        meta = read_workbook_meta(path)
        if meta.error:
            self._show_fallback(meta.error)
            self.sheet_combo.blockSignals(False)
            return

        self.sheet_combo.addItems(meta.sheets)
        self.sheet_combo.blockSignals(False)
        self.status_label.setVisible(False)
        self.open_extern_btn.setVisible(False)

        if meta.active_sheet:
            self._load_sheet(meta.active_sheet)

    def _on_sheet_changed(self, sheet_name: str):
        if sheet_name:
            self._load_sheet(sheet_name)

    def _load_sheet(self, sheet_name: str):
        """Füllt die Tabelle mit den Zellinhalten des gewählten Arbeitsblatts."""
        from core.xlsx_reader import read_workbook_sheet, XlsxReadError

        if not self._path:
            return

        try:
            rows = read_workbook_sheet(self._path, sheet_name)
        except XlsxReadError as exc:
            self._show_fallback(str(exc))
            return

        if not rows:
            self.table.setRowCount(0)
            self.table.setColumnCount(0)
            return

        col_count = max(len(r) for r in rows)
        self.table.setRowCount(len(rows))
        self.table.setColumnCount(col_count)

        # Erste Zeile als Spaltenköpfe
        header_row = rows[0]
        self.table.setHorizontalHeaderLabels(
            [str(v) if v is not None else "" for v in header_row]
        )

        for r_idx, row in enumerate(rows):
            for c_idx, val in enumerate(row):
                item = QTableWidgetItem(str(val) if val is not None else "")
                self.table.setItem(r_idx, c_idx, item)

    def _show_fallback(self, reason: str):
        self.table.setRowCount(0)
        self.table.setColumnCount(0)
        self.status_label.setText(
            t("Vorschau nicht verfügbar: {reason}").format(reason=reason)
            + "\n→ " + t("Datei extern öffnen")
        )
        self.status_label.setVisible(True)
        self.open_extern_btn.setVisible(True)

    def _open_extern(self):
        """Öffnet die Datei mit der systemseitig zugeordneten Anwendung."""
        if not self._path:
            return
        import subprocess
        import sys as _sys

        try:
            if _sys.platform == "win32":
                os.startfile(self._path)  # type: ignore[attr-defined]
            elif _sys.platform == "darwin":
                subprocess.Popen(["open", self._path])
            else:
                subprocess.Popen(["xdg-open", self._path])
        except Exception as exc:
            self.status_label.setText(t("Externes Öffnen fehlgeschlagen: {error}").format(error=exc))
            self.status_label.setVisible(True)


class ArchivePreview(QWidget):
    """Vorschau-Widget für ZIP-Archive (.zip)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._path: str | None = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Header-Box
        header_group = QGroupBox("📦 ZIP-Archiv")
        header_layout = QFormLayout(header_group)

        self.name_label = QLabel("-")
        self.name_label.setWordWrap(True)
        header_layout.addRow("Name:", self.name_label)

        self.count_label = QLabel("-")
        header_layout.addRow("Inhalt:", self.count_label)

        self.size_label = QLabel("-")
        header_layout.addRow("Größe:", self.size_label)

        self.ratio_label = QLabel("-")
        header_layout.addRow("Kompression:", self.ratio_label)

        layout.addWidget(header_group)

        # Tabelle der enthaltenen Dateien
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Name / Pfad", "Größe", "Komprimiert"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setAccessibleName("Archiv-Vorschautabelle")
        layout.addWidget(self.table, 1)

        # Aktions-Buttons
        btn_layout = QHBoxLayout()
        self.explore_btn = QPushButton("🔍 Durchsuchen...")
        self.explore_btn.setAccessibleName("Archiv detailliert durchsuchen")
        self.explore_btn.setToolTip("Öffnet den vollen Archiv-Inspektor mit Filterung und Tests")
        self.explore_btn.clicked.connect(self._open_viewer)
        btn_layout.addWidget(self.explore_btn)

        self.extract_btn = QPushButton("📦 Entpacken...")
        self.extract_btn.setAccessibleName("Archiv entpacken")
        self.extract_btn.setToolTip("Öffnet den Dialog zum Entpacken des Archivs")
        self.extract_btn.clicked.connect(self._open_extract)
        btn_layout.addWidget(self.extract_btn)

        layout.addLayout(btn_layout)

        # Status-/Fehler-Label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #d32f2f;")
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)

    def load_archive(self, path: str):
        self._path = path
        self.status_label.setVisible(False)
        self.name_label.setText(os.path.basename(path))

        try:
            from core.archive_service import inspect_zip
            summary, entries = inspect_zip(path)

            self.count_label.setText(f"{summary.total_files} Dateien, {summary.total_folders} Ordner")
            self.size_label.setText(
                f"{summary.formatted_uncompressed_size} (gepackt: {summary.formatted_compressed_size})"
            )
            self.ratio_label.setText(f"{summary.overall_ratio:.1f}% Ersparnis")

            show_entries = entries[:100]
            self.table.setRowCount(len(show_entries))
            for row, entry in enumerate(show_entries):
                prefix = "📁 " if entry.is_dir else "📄 "
                self.table.setItem(row, 0, QTableWidgetItem(f"{prefix}{entry.filename}"))
                self.table.setItem(row, 1, QTableWidgetItem(entry.formatted_size if not entry.is_dir else "-"))
                self.table.setItem(row, 2, QTableWidgetItem(entry.formatted_compressed_size if not entry.is_dir else "-"))

            self.explore_btn.setEnabled(True)
            self.extract_btn.setEnabled(True)

        except Exception as exc:
            self.table.setRowCount(0)
            self.count_label.setText("-")
            self.size_label.setText("-")
            self.ratio_label.setText("-")
            self.status_label.setText(f"Archiv konnte nicht gelesen werden: {exc}")
            self.status_label.setVisible(True)
            self.explore_btn.setEnabled(False)
            self.extract_btn.setEnabled(False)

    def _open_viewer(self):
        if self._path and os.path.exists(self._path):
            from gui.archive_dialog import ArchiveViewerDialog
            dlg = ArchiveViewerDialog(self._path, self.window())
            dlg.exec()

    def _open_extract(self):
        if self._path and os.path.exists(self._path):
            from gui.archive_dialog import ArchiveExtractDialog
            dlg = ArchiveExtractDialog(self._path, parent=self.window())
            dlg.exec()


class PreviewPanel(QWidget):
    """
    Haupt-Vorschau-Panel mit:
    - Datei-Vorschau (Bild, Text, PDF, Archiv)
    - Metadaten
    - Tags & Notizen
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(300)
        self._current_path = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Vorschau-Stack
        self.preview_stack = QStackedWidget()

        # Platzhalter
        placeholder = QLabel("Keine Datei ausgewählt")
        placeholder.setWordWrap(True)
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_stack.addWidget(placeholder)

        # Bild-Vorschau
        self.image_preview = ImagePreview()
        self.preview_stack.addWidget(self.image_preview)

        # Text-Vorschau
        self.text_preview = TextPreview()
        self.preview_stack.addWidget(self.text_preview)

        # PDF-Vorschau
        self.pdf_preview = PdfPreview()
        self.preview_stack.addWidget(self.pdf_preview)

        # Ordner-Vorschau
        self.directory_preview = DirectoryPreview()
        self.preview_stack.addWidget(self.directory_preview)

        # Nicht unterstützt
        self.unsupported_label = QLabel(t("Vorschau nicht verfügbar\nfür diesen Dateityp"))
        self.unsupported_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.unsupported_label.setWordWrap(True)
        self.preview_stack.addWidget(self.unsupported_label)

        # Excel-Vorschau (.xlsx / .xls) — Index 6
        self.excel_preview = ExcelPreview()
        self.preview_stack.addWidget(self.excel_preview)

        # ZIP-Archiv-Vorschau (.zip) — Index 7
        self.archive_preview = ArchivePreview()
        self.preview_stack.addWidget(self.archive_preview)

        layout.addWidget(self.preview_stack, 2)

        # Trennlinie
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)

        # Metadaten
        self.metadata_panel = MetadataPanel()
        layout.addWidget(self.metadata_panel, 1)

    def clear_preview(self):
        """Setzt die Vorschau und Metadaten zurück."""
        self._current_path = None
        self.preview_stack.setCurrentIndex(0)
        self.metadata_panel.clear_metadata()

    def show_preview(self, path: str):
        """Zeigt Vorschau für eine Datei.

        Fehler beim Erzeugen der Vorschau dürfen niemals die Anwendung
        beenden; sie werden protokolliert und als Hinweis angezeigt.
        """
        try:
            self._show_preview(path)
        except Exception as exc:
            logging.exception("Vorschau fehlgeschlagen für %s", path)
            self._show_message(t("Vorschau nicht verfügbar: {reason}").format(reason=exc))
            try:
                self.metadata_panel.show_metadata(path)
            except Exception:
                pass

    def _show_message(self, text: str):
        self.unsupported_label.setText(text)
        self.preview_stack.setCurrentWidget(self.unsupported_label)

    def _show_preview(self, path: str):
        if not path or not os.path.exists(path):
            self.clear_preview()
            return

        self._current_path = path
        preview_path = path
        heading = None

        if is_windows_shortcut(path):
            shortcut_target = build_shortcut_preview_target(path)
            if shortcut_target is None:
                self._show_message(
                    t("Verknüpfung konnte nicht aufgelöst werden\noder das Ziel existiert nicht.")
                )
                self.metadata_panel.show_metadata(path)
                return

            preview_path = shortcut_target.preview_path
            heading = (
                t("Verknüpfung: {name}").format(name=os.path.basename(path)) + "\n"
                + t("Ziel: {path}").format(path=shortcut_target.target_path) + "\n"
                + t("Vorschau: {path}").format(path=shortcut_target.preview_path)
            )

        self._show_preview_for_path(preview_path, heading)
        self.metadata_panel.show_metadata(preview_path)

    def _show_preview_for_path(self, path: str, heading: str | None = None):
        ext = os.path.splitext(path)[1].lower()
        self.unsupported_label.setText(t("Vorschau nicht verfügbar\nfür diesen Dateityp"))

        if os.path.isdir(path):
            self.directory_preview.load_directory(path, heading)
            self.preview_stack.setCurrentIndex(4)
            return

        # Cloud-Platzhalter ("Nur online verfügbar") nicht öffnen: Das Lesen
        # würde einen Download auslösen und die Oberfläche blockieren.
        if is_cloud_placeholder(path):
            self._show_message(
                "☁️ " + t("Diese Datei ist nur online verfügbar.") + "\n"
                + t("Zum Öffnen doppelklicken – die Datei wird dabei heruntergeladen.")
            )
            return

        try:
            size = os.path.getsize(path)
        except OSError:
            size = 0
        try:
            limit_mb = float(_preview_setting("max_preview_size_mb", 50))
        except (TypeError, ValueError):
            limit_mb = 50.0
        too_large = limit_mb > 0 and size > limit_mb * 1024 * 1024

        def show_too_large():
            self._show_message(
                t("Datei zu groß für die Vorschau ({size} MB, Grenze {limit} MB).").format(
                    size=f"{size / (1024 * 1024):.1f}", limit=f"{limit_mb:g}"
                )
            )

        # Bild-Vorschau
        if ext in IMAGE_EXTENSIONS:
            if not _preview_setting("preview_images", True):
                self._show_message(t("Bildvorschau ist in den Einstellungen deaktiviert."))
            elif too_large:
                show_too_large()
            else:
                self.image_preview.load_image(path)
                self.preview_stack.setCurrentIndex(1)

        # Text/Code-Vorschau (liest höchstens 100 KB)
        elif ext in TEXT_EXTENSIONS:
            if not _preview_setting("preview_code", True):
                self._show_message(t("Textvorschau ist in den Einstellungen deaktiviert."))
            else:
                self.text_preview.load_file(path)
                self.preview_stack.setCurrentIndex(2)

        # PDF-Vorschau
        elif ext == '.pdf':
            if not _preview_setting("preview_pdfs", True):
                self._show_message(t("PDF-Vorschau ist in den Einstellungen deaktiviert."))
            elif too_large:
                show_too_large()
            else:
                self.pdf_preview.load_pdf(path)
                self.preview_stack.setCurrentIndex(3)

        # Excel-Vorschau
        elif ext in ['.xlsx', '.xls']:
            if too_large:
                show_too_large()
            else:
                self.excel_preview.load_file(path)
                self.preview_stack.setCurrentIndex(6)

        # Unbekannte Endung, aber offensichtlich Text (README, Makefile, ...)
        elif _preview_setting("preview_code", True) and _looks_like_text(path):
            self.text_preview.load_file(path)
            self.preview_stack.setCurrentIndex(2)

        # ZIP-Archiv-Vorschau
        elif ext == '.zip':
            self.archive_preview.load_archive(path)
            self.preview_stack.setCurrentIndex(7)

        # Nicht unterstützt
        else:
            self.preview_stack.setCurrentIndex(5)
