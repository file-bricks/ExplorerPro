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
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QImage, QFont, QSyntaxHighlighter, QTextCharFormat, QColor
import os
from datetime import datetime
from pathlib import Path

from core.shortcut_utils import build_shortcut_preview_target, is_windows_shortcut

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
        """Lädt und zeigt ein Bild"""
        try:
            pixmap = QPixmap(path)
            if pixmap.isNull():
                self.setText("Bild konnte nicht geladen werden")
                return
            
            self._original_pixmap = pixmap
            self._scale_to_fit()
        except Exception as e:
            self.setText(f"Fehler: {e}")
    
    def _scale_to_fit(self):
        if self._original_pixmap:
            scaled = self._original_pixmap.scaled(
                self.size(),
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
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(100000)  # Max 100KB
            
            self.setPlainText(content)
            
            # Syntax-Highlighting für Python
            ext = os.path.splitext(path)[1].lower()
            if ext == '.py':
                self._highlighter = PythonHighlighter(self.document())
            else:
                self._highlighter = None
                
        except Exception as e:
            self.setPlainText(f"Fehler beim Laden: {e}")


class DirectoryPreview(QPlainTextEdit):
    """Read-only preview for folders and resolved shortcut targets."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setFont(QFont("Consolas", 10))

    def load_directory(self, path: str, heading: str | None = None):
        folder = Path(path)
        lines = [heading or f"Ordner: {folder}", ""]

        try:
            entries = sorted(
                folder.iterdir(),
                key=lambda item: (not item.is_dir(), item.name.lower()),
            )
        except OSError as exc:
            self.setPlainText(f"Ordner konnte nicht gelesen werden:\n{folder}\n\n{exc}")
            return

        if not entries:
            lines.append("(leer)")
        else:
            for entry in entries[:200]:
                marker = "[DIR]" if entry.is_dir() else "     "
                lines.append(f"{marker} {entry.name}")
            if len(entries) > 200:
                lines.append(f"... {len(entries) - 200} weitere Einträge")

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
        if not HAS_FITZ:
            self.content.setText("PyMuPDF nicht installiert.\nPDF-Vorschau nicht verfügbar.")
            return
        
        try:
            doc = fitz.open(path)
            try:
                if len(doc) > 0:
                    page = doc[0]
                    mat = fitz.Matrix(1.5, 1.5)  # Zoom
                    pix = page.get_pixmap(matrix=mat)

                    img = QImage(
                        pix.samples,
                        pix.width,
                        pix.height,
                        pix.stride,
                        QImage.Format.Format_RGB888
                    )

                    pixmap = QPixmap.fromImage(img)
                    self.content.setPixmap(pixmap)
                else:
                    self.content.setText("Leeres PDF")
            finally:
                doc.close()
        except Exception as e:
            self.content.setText(f"Fehler beim Laden: {e}")


class MetadataPanel(QWidget):
    """Metadaten-Anzeige"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Datei-Info
        info_group = QGroupBox("📊 Datei-Information")
        info_layout = QFormLayout(info_group)
        
        self.name_label = QLabel("-")
        info_layout.addRow("Name:", self.name_label)
        
        self.type_label = QLabel("-")
        info_layout.addRow("Typ:", self.type_label)
        
        self.size_label = QLabel("-")
        info_layout.addRow("Größe:", self.size_label)
        
        self.modified_label = QLabel("-")
        info_layout.addRow("Geändert:", self.modified_label)
        
        self.created_label = QLabel("-")
        info_layout.addRow("Erstellt:", self.created_label)
        
        layout.addWidget(info_group)
        
        # Tags
        tags_group = QGroupBox("🏷️ Tags")
        tags_layout = QVBoxLayout(tags_group)
        
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("Tags hinzufügen (kommagetrennt)")
        tags_layout.addWidget(self.tags_edit)
        
        layout.addWidget(tags_group)
        
        # Notizen
        notes_group = QGroupBox("📝 Notizen")
        notes_layout = QVBoxLayout(notes_group)
        
        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setMaximumHeight(100)
        self.notes_edit.setPlaceholderText("Notizen zur Datei...")
        notes_layout.addWidget(self.notes_edit)
        
        layout.addWidget(notes_group)
        
        layout.addStretch()
    
    def show_metadata(self, path: str):
        """Zeigt Metadaten einer Datei"""
        if not os.path.exists(path):
            return
        
        stat = os.stat(path)
        name = os.path.basename(path)
        ext = os.path.splitext(name)[1].lower()
        
        self.name_label.setText(name)
        self.type_label.setText("Ordner" if os.path.isdir(path) else (ext or "Unbekannt"))
        
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
        
        # Zeitstempel
        modified = datetime.fromtimestamp(stat.st_mtime)
        created = datetime.fromtimestamp(stat.st_ctime)
        
        self.modified_label.setText(modified.strftime("%d.%m.%Y %H:%M"))
        self.created_label.setText(created.strftime("%d.%m.%Y %H:%M"))


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
        self.sheet_combo.setMinimumWidth(120)
        self.sheet_combo.currentTextChanged.connect(self._on_sheet_changed)
        header.addWidget(self.sheet_combo, 1)

        self.open_extern_btn = QPushButton("Extern öffnen")
        self.open_extern_btn.setVisible(False)
        self.open_extern_btn.clicked.connect(self._open_extern)
        header.addWidget(self.open_extern_btn)

        layout.addLayout(header)

        # Statuszeile (Fehler / Fallback-Hinweis)
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)

        # Datentabelle
        self.table = QTableWidget()
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
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
            f"Vorschau nicht verfügbar: {reason}\n→ Datei extern öffnen"
        )
        self.status_label.setVisible(True)
        self.open_extern_btn.setVisible(True)

    def _open_extern(self):
        """Öffnet die Datei mit der systemseitig zugeordneten Anwendung."""
        if not self._path:
            return
        import subprocess
        import sys as _sys

        if _sys.platform == "win32":
            os.startfile(self._path)  # type: ignore[attr-defined]
        elif _sys.platform == "darwin":
            subprocess.Popen(["open", self._path])
        else:
            subprocess.Popen(["xdg-open", self._path])


class PreviewPanel(QWidget):
    """
    Haupt-Vorschau-Panel mit:
    - Datei-Vorschau (Bild, Text, PDF)
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
        self.unsupported_label = QLabel("Vorschau nicht verfügbar\nfür diesen Dateityp")
        self.unsupported_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_stack.addWidget(self.unsupported_label)

        # Excel-Vorschau (.xlsx / .xls) — Index 6
        self.excel_preview = ExcelPreview()
        self.preview_stack.addWidget(self.excel_preview)
        
        layout.addWidget(self.preview_stack, 2)
        
        # Trennlinie
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)
        
        # Metadaten
        self.metadata_panel = MetadataPanel()
        layout.addWidget(self.metadata_panel, 1)
    
    def show_preview(self, path: str):
        """Zeigt Vorschau für eine Datei"""
        if not os.path.exists(path):
            self.preview_stack.setCurrentIndex(0)
            return
        
        self._current_path = path
        preview_path = path
        heading = None

        if is_windows_shortcut(path):
            shortcut_target = build_shortcut_preview_target(path)
            if shortcut_target is None:
                self.unsupported_label.setText(
                    "Verknüpfung konnte nicht aufgelöst werden\noder das Ziel existiert nicht."
                )
                self.preview_stack.setCurrentIndex(5)
                self.metadata_panel.show_metadata(path)
                return

            preview_path = shortcut_target.preview_path
            heading = (
                f"Verknüpfung: {os.path.basename(path)}\n"
                f"Ziel: {shortcut_target.target_path}\n"
                f"Vorschau: {shortcut_target.preview_path}"
            )

        self._show_preview_for_path(preview_path, heading)
        self.metadata_panel.show_metadata(preview_path)

    def _show_preview_for_path(self, path: str, heading: str | None = None):
        ext = os.path.splitext(path)[1].lower()
        self.unsupported_label.setText("Vorschau nicht verfügbar\nfür diesen Dateityp")

        if os.path.isdir(path):
            self.directory_preview.load_directory(path, heading)
            self.preview_stack.setCurrentIndex(4)
            return
        
        # Bild-Vorschau
        if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg']:
            self.image_preview.load_image(path)
            self.preview_stack.setCurrentIndex(1)
        
        # Text/Code-Vorschau
        elif ext in ['.txt', '.md', '.py', '.js', '.html', '.css', '.json',
                     '.xml', '.sql', '.c', '.cpp', '.h', '.java', '.ini', '.cfg',
                     '.log', '.yml', '.yaml', '.toml', '.sh', '.bat', '.ps1',
                     '.csv', '.tsv', '.env', '.gitignore', '.editorconfig',
                     '.rs', '.go', '.ts', '.tsx', '.jsx', '.vue', '.svelte',
                     '.r', '.rb', '.php', '.lua', '.tex', '.bib', '.cmake']:
            self.text_preview.load_file(path)
            self.preview_stack.setCurrentIndex(2)
        
        # PDF-Vorschau
        elif ext == '.pdf':
            self.pdf_preview.load_pdf(path)
            self.preview_stack.setCurrentIndex(3)

        # Excel-Vorschau
        elif ext in ['.xlsx', '.xls']:
            self.excel_preview.load_file(path)
            self.preview_stack.setCurrentIndex(6)

        # Nicht unterstützt
        else:
            self.preview_stack.setCurrentIndex(5)
