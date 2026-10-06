#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ui_translator — übersetzt sichtbare Qt-Texte zentral zur Laufzeit.

Viele GUI-Texte sind als deutsche Literale im Code hinterlegt. Statt jede
Stelle einzeln in ``t()`` zu kapseln, übersetzt ein anwendungsweiter
Event-Filter beim Anzeigen eines Widgets dessen statische Texte über den
Katalog ``locales/translations.json``:

* Fenstertitel, Tooltips, Status-/WhatsThis-Texte, Barrierefreiheitsnamen
* Beschriftungen von Labels, Buttons, Gruppen, Tabs und Toolboxen
* Platzhaltertexte von Eingabefeldern
* Spaltenköpfe von QTreeWidget/QTableWidget
* Einträge von Comboboxen (nur exakte Katalogschlüssel)
* Menüs, Menüleisten und Toolbars samt ihrer QActions

Bei einem Sprachwechsel werden alle bereits übersetzten Texte live neu
übersetzt, sofern der Code sie zwischenzeitlich nicht geändert hat.
Nutzerdaten (Dateinamen, Pfade, Editorinhalte) werden nie angefasst;
bei Widgets mit Nutzerdaten im Text (Labels, Listen, Comboboxen) schließt
``widget.setProperty(NO_TRANSLATE, True)`` den angezeigten Inhalt aus –
Tooltips und Barrierefreiheitstexte werden weiterhin übersetzt.
"""
from __future__ import annotations

from typing import Callable, Iterable

from PySide6.QtCore import QEvent, QObject
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QAbstractButton, QApplication, QComboBox, QGroupBox, QLabel, QLineEdit,
    QMenu, QMenuBar, QPlainTextEdit, QTabWidget, QTableWidget, QTextEdit,
    QToolBar, QToolBox, QTreeWidget, QWidget,
)

from translator import get_translator

NO_TRANSLATE = "ep_no_translate"
_RECORD = "_ep_i18n"

# Attribut -> (Getter, Setter) für alle QWidgets.
_WIDGET_ATTRS = (
    ("windowTitle", QWidget.windowTitle, QWidget.setWindowTitle),
    ("toolTip", QWidget.toolTip, QWidget.setToolTip),
    ("statusTip", QWidget.statusTip, QWidget.setStatusTip),
    ("whatsThis", QWidget.whatsThis, QWidget.setWhatsThis),
    ("accessibleName", QWidget.accessibleName, QWidget.setAccessibleName),
    ("accessibleDescription", QWidget.accessibleDescription, QWidget.setAccessibleDescription),
)

_ACTION_ATTRS = (
    ("text", QAction.text, QAction.setText),
    ("statusTip", QAction.statusTip, QAction.setStatusTip),
    ("whatsThis", QAction.whatsThis, QAction.setWhatsThis),
)


def _stripped_action_text(text: str) -> str:
    """Nachbildung von Qts Tooltip-Ableitung aus dem Aktionstext."""
    text = text.replace("&&", "\0").replace("&", "").replace("\0", "&")
    if text.endswith("..."):
        text = text[:-3]
    elif text.endswith("…"):
        text = text[:-1]
    return text


class UiTranslator(QObject):
    """Anwendungsweiter Event-Filter für die Laufzeitübersetzung."""

    def __init__(self, app: QApplication):
        super().__init__(app)
        self._app = app
        self._translator = get_translator()
        self._last_language = self._translator.get_language()
        self._translator.add_language_listener(self._on_language_changed)
        app.installEventFilter(self)

    def shutdown(self) -> None:
        self._app.removeEventFilter(self)
        self._translator.remove_language_listener(self._on_language_changed)

    # ------------------------------------------------------------------ #
    # Event-Filter                                                         #
    # ------------------------------------------------------------------ #

    def eventFilter(self, watched, event):  # noqa: N802 (Qt-API)
        try:
            if event.type() == QEvent.Type.Show and isinstance(watched, QWidget):
                self.translate_widget(watched)
        except Exception:
            # Übersetzung ist Komfort; sie darf niemals ein Fenster blockieren.
            pass
        return False

    # ------------------------------------------------------------------ #
    # Übersetzung einzelner Objekte                                       #
    # ------------------------------------------------------------------ #

    def translate_widget(self, widget: QWidget) -> None:
        """Übersetzt die statischen Texte eines Widgets (nicht rekursiv)."""
        record = self._record(widget)
        changed = False

        for name, getter, setter in _WIDGET_ATTRS:
            changed |= self._apply(widget, record, name, getter, setter)

        if widget.property(NO_TRANSLATE):
            # Inhalt sind Nutzerdaten: nur Hilfetexte (oben) übersetzen.
            pass
        elif isinstance(widget, QAbstractButton):
            changed |= self._apply(widget, record, "text", QAbstractButton.text, QAbstractButton.setText)
        elif isinstance(widget, QLabel):
            changed |= self._apply(widget, record, "text", QLabel.text, QLabel.setText)
        elif isinstance(widget, QGroupBox):
            changed |= self._apply(widget, record, "title", QGroupBox.title, QGroupBox.setTitle)
        elif isinstance(widget, QLineEdit):
            changed |= self._apply(
                widget, record, "placeholderText", QLineEdit.placeholderText, QLineEdit.setPlaceholderText
            )
        elif isinstance(widget, QPlainTextEdit):
            changed |= self._apply(
                widget, record, "placeholderText",
                QPlainTextEdit.placeholderText, QPlainTextEdit.setPlaceholderText,
            )
        elif isinstance(widget, QTextEdit):
            changed |= self._apply(
                widget, record, "placeholderText", QTextEdit.placeholderText, QTextEdit.setPlaceholderText
            )
        elif isinstance(widget, QMenu):
            changed |= self._apply(widget, record, "title", QMenu.title, QMenu.setTitle)
        elif isinstance(widget, QTabWidget):
            for i in range(widget.count()):
                changed |= self._apply_indexed(widget, record, "tab", i, widget.tabText, widget.setTabText)
                changed |= self._apply_indexed(
                    widget, record, "tabtip", i, widget.tabToolTip, widget.setTabToolTip
                )
        elif isinstance(widget, QToolBox):
            for i in range(widget.count()):
                changed |= self._apply_indexed(widget, record, "item", i, widget.itemText, widget.setItemText)
        elif isinstance(widget, QComboBox):
            changed |= self._translate_combo(widget, record)
        elif isinstance(widget, QTreeWidget):
            header = widget.headerItem()
            if header is not None:
                for i in range(header.columnCount()):
                    changed |= self._apply_indexed(
                        widget, record, "header", i,
                        lambda col, h=header: h.text(col),
                        lambda col, value, h=header: h.setText(col, value),
                    )
        elif isinstance(widget, QTableWidget):
            for i in range(widget.columnCount()):
                item = widget.horizontalHeaderItem(i)
                if item is not None:
                    changed |= self._apply_indexed(
                        widget, record, "hheader", i,
                        lambda col, it=item: it.text(),
                        lambda col, value, it=item: it.setText(value),
                    )

        if changed:
            widget.setProperty(_RECORD, record)

        if isinstance(widget, (QMenu, QMenuBar, QToolBar)) and not widget.property(NO_TRANSLATE):
            for action in widget.actions():
                self.translate_action(action)

    def translate_action(self, action: QAction) -> None:
        if action.isSeparator() or action.property(NO_TRANSLATE):
            return
        record = self._record(action)
        original_text = action.text()
        changed = False
        for name, getter, setter in _ACTION_ATTRS:
            changed |= self._apply(action, record, name, getter, setter)
        # Nur explizit gesetzte Tooltips übersetzen; abgeleitete folgen dem Text.
        tooltip = action.toolTip()
        if "toolTip" in record or tooltip != _stripped_action_text(original_text):
            changed |= self._apply(action, record, "toolTip", QAction.toolTip, QAction.setToolTip)
        if changed:
            action.setProperty(_RECORD, record)

    def _translate_combo(self, combo: QComboBox, record: dict) -> bool:
        changed = False
        blocked = combo.blockSignals(True)
        try:
            for i in range(combo.count()):
                key = f"combo:{i}"
                current = combo.itemText(i)
                if key not in record and not self._translator.has_key(current.strip()):
                    # Comboboxen enthalten oft Nutzerdaten (Blattnamen, Pfade):
                    # nur exakte Katalogschlüssel werden übersetzt.
                    continue
                changed |= self._apply_indexed(combo, record, "combo", i, combo.itemText, combo.setItemText)
        finally:
            combo.blockSignals(blocked)
        return changed

    # ------------------------------------------------------------------ #
    # Kernlogik                                                            #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _record(obj: QObject) -> dict:
        value = obj.property(_RECORD)
        return dict(value) if isinstance(value, dict) else {}

    def _apply(self, obj, record: dict, name: str, getter: Callable, setter: Callable) -> bool:
        return self._apply_value(
            record, name, lambda: getter(obj), lambda value: setter(obj, value)
        )

    def _apply_indexed(self, obj, record: dict, prefix: str, index: int,
                       getter: Callable, setter: Callable) -> bool:
        return self._apply_value(
            record, f"{prefix}:{index}", lambda: getter(index), lambda value: setter(index, value)
        )

    def _apply_value(self, record: dict, name: str, get: Callable, set_: Callable) -> bool:
        current = get()
        if not current:
            return False
        language = self._translator.get_language()
        entry = record.get(name)
        if entry is not None and list(entry)[2] == current and list(entry)[1] == language:
            return False  # bereits in der aktiven Sprache übersetzt
        translated = self._translator.translate_text(current)
        if translated == current and self._translator.source_text(current.strip()) is None:
            if entry is not None:
                record.pop(name, None)
                return True
            return False
        if translated != current:
            set_(translated)
        record[name] = [current, language, translated]
        return True

    def _retranslate_value(self, record: dict, name: str, get: Callable, set_: Callable,
                           old_language: str) -> bool:
        entry = record.get(name)
        if entry is None:
            return False
        raw, raw_language, last = list(entry)
        current = get()
        if current != last:
            # Der Code hat den Text inzwischen selbst gesetzt (typisch per t()
            # in der bisherigen Sprache); als neue Quelle übernehmen.
            raw, raw_language = current, old_language
        translated = self._translator.translate_text_from(raw, raw_language)
        if translated != current:
            set_(translated)
        record[name] = [raw, raw_language, translated]
        return True

    # ------------------------------------------------------------------ #
    # Live-Sprachwechsel                                                   #
    # ------------------------------------------------------------------ #

    def _on_language_changed(self, language: str) -> None:
        old_language, self._last_language = self._last_language, language
        try:
            self.retranslate_all(old_language)
        except Exception:
            pass

    def retranslate_all(self, old_language: str) -> None:
        seen_actions: set[int] = set()
        for widget in QApplication.allWidgets():
            self._retranslate_object(widget, old_language)
            for action in widget.actions():
                if id(action) in seen_actions:
                    continue
                seen_actions.add(id(action))
                self._retranslate_object(action, old_language)

    def _retranslate_object(self, obj: QObject, old_language: str) -> None:
        record = self._record(obj)
        if not record:
            return
        changed = False
        for name in list(record):
            getter_setter = self._accessor(obj, name)
            if getter_setter is None:
                record.pop(name, None)
                changed = True
                continue
            changed |= self._retranslate_value(record, name, *getter_setter, old_language)
        if changed:
            obj.setProperty(_RECORD, record)

    @staticmethod
    def _accessor(obj: QObject, name: str):
        """Liefert (get, set) für einen aufgezeichneten Attributnamen."""
        prefix, _, index_text = name.partition(":")
        if index_text:
            index = int(index_text)
            if prefix == "tab" and isinstance(obj, QTabWidget) and index < obj.count():
                return (lambda: obj.tabText(index), lambda v: obj.setTabText(index, v))
            if prefix == "tabtip" and isinstance(obj, QTabWidget) and index < obj.count():
                return (lambda: obj.tabToolTip(index), lambda v: obj.setTabToolTip(index, v))
            if prefix == "item" and isinstance(obj, QToolBox) and index < obj.count():
                return (lambda: obj.itemText(index), lambda v: obj.setItemText(index, v))
            if prefix == "combo" and isinstance(obj, QComboBox) and index < obj.count():
                def set_combo(value):
                    blocked = obj.blockSignals(True)
                    try:
                        obj.setItemText(index, value)
                    finally:
                        obj.blockSignals(blocked)
                return (lambda: obj.itemText(index), set_combo)
            if prefix == "header" and isinstance(obj, QTreeWidget):
                header = obj.headerItem()
                if header is not None and index < header.columnCount():
                    return (lambda: header.text(index), lambda v: header.setText(index, v))
            if prefix == "hheader" and isinstance(obj, QTableWidget):
                item = obj.horizontalHeaderItem(index) if index < obj.columnCount() else None
                if item is not None:
                    return (item.text, item.setText)
            return None

        candidates: Iterable = ()
        if isinstance(obj, QAction):
            candidates = _ACTION_ATTRS + (("toolTip", QAction.toolTip, QAction.setToolTip),)
        else:
            extra = []
            if isinstance(obj, QAbstractButton):
                extra.append(("text", QAbstractButton.text, QAbstractButton.setText))
            elif isinstance(obj, QLabel):
                extra.append(("text", QLabel.text, QLabel.setText))
            elif isinstance(obj, QGroupBox):
                extra.append(("title", QGroupBox.title, QGroupBox.setTitle))
            elif isinstance(obj, QMenu):
                extra.append(("title", QMenu.title, QMenu.setTitle))
            elif isinstance(obj, QLineEdit):
                extra.append(("placeholderText", QLineEdit.placeholderText, QLineEdit.setPlaceholderText))
            elif isinstance(obj, QPlainTextEdit):
                extra.append(("placeholderText", QPlainTextEdit.placeholderText,
                              QPlainTextEdit.setPlaceholderText))
            elif isinstance(obj, QTextEdit):
                extra.append(("placeholderText", QTextEdit.placeholderText, QTextEdit.setPlaceholderText))
            candidates = tuple(_WIDGET_ATTRS) + tuple(extra)
        for attr, getter, setter in candidates:
            if attr == name:
                return (lambda: getter(obj), lambda v: setter(obj, v))
        return None


def uninstall_ui_translator(app: QApplication) -> None:
    """Entfernt Filter und Sprach-Listener vor dem Abbau der QApplication.

    Ein Python-Eventfilter, der während der Zerstörung der Anwendung noch
    Ereignisse erhält, kann beim Beenden zu nativen Abstürzen führen.
    """
    existing = getattr(app, "_ep_ui_translator", None)
    if existing is None:
        return
    app._ep_ui_translator = None
    existing.shutdown()


def install_ui_translator(app: QApplication) -> UiTranslator:
    """Installiert den Übersetzer einmalig am QApplication-Objekt."""
    existing = getattr(app, "_ep_ui_translator", None)
    if existing is None:
        existing = UiTranslator(app)
        app._ep_ui_translator = existing
    return existing
