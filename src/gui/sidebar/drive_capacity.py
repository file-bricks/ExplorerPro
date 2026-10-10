"""Capacity widgets and independent background requests for drive rows."""

from concurrent.futures import ThreadPoolExecutor

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget

from core.drive_usage import format_capacity, start_drive_queries, stop_drive_queries
from translator import t

_executor = None


def capacity_executor():
    """Workers only return Python data; no Qt objects cross thread boundaries.

    OS reads run in bounded helpers, so failed drives release worker slots.
    """
    global _executor
    if _executor is None:
        start_drive_queries()
        _executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="drive-capacity")
    return _executor


def shutdown_capacity_executor():
    """Stop capacity helpers, then drain Python workers before Qt teardown."""
    global _executor
    if _executor is not None:
        stop_drive_queries()
        _executor.shutdown(wait=True, cancel_futures=True)
        _executor = None


class DriveCapacityWidget(QWidget):
    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.path = path
        self.has_usage = False  # a shown value (even stale) stays until a new one arrives
        # Tree selection and double-click navigation still receive mouse events.
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 3, 2, 3)
        layout.setSpacing(2)
        self.title = QLabel(path)
        self.details = QLabel()
        self.details.setWordWrap(True)
        self.bar = QProgressBar()
        self.bar.setRange(0, 1000)
        self.bar.setFixedHeight(18)
        self.bar.setAccessibleName(t("Speicherbelegung"))
        layout.addWidget(self.title)
        layout.addWidget(self.details)
        layout.addWidget(self.bar)
        self.set_loading()

    def set_loading(self):
        self.details.setText(t("Speicherbelegung wird ermittelt …"))
        self.bar.hide()
        self.setAccessibleName(self.path)
        self.setAccessibleDescription(self.details.text())

    def set_usage(self, usage):
        self.has_usage = usage is not None
        if usage is None:
            self.details.setText(t("Speicherbelegung nicht verfügbar"))
            self.bar.hide()
            self.bar.setValue(0)
        else:
            self.details.setText(t("{free} frei · {used} belegt · {total} gesamt").format(
                free=format_capacity(usage.free), used=format_capacity(usage.used),
                total=format_capacity(usage.total)))
            self.bar.setValue(round(usage.used_percent * 10))
            self.bar.setFormat(t("{percent}% belegt").format(percent=f"{usage.used_percent:.1f}"))
            self.bar.show()
        description = self.details.text()
        if usage is not None:
            description += " · " + self.bar.format()
        self.setToolTip(self.path + "\n" + description)
        self.setAccessibleDescription(description)
        self.bar.setAccessibleDescription(description)
