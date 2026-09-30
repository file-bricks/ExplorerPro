"""Capacity widgets and independent background requests for drive rows."""

import atexit

from PySide6.QtCore import QObject, QRunnable, Qt, Signal, QThreadPool
from PySide6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget

from core.drive_usage import format_capacity, read_drive_usage
from translator import t

_shutdown_registered = False


def capacity_pool():
    """Finish Python runnables before interpreter/Qt teardown destroys them."""
    global _shutdown_registered
    pool = QThreadPool.globalInstance()
    if not _shutdown_registered:
        atexit.register(pool.waitForDone)
        _shutdown_registered = True
    return pool


class UsageSignals(QObject):
    ready = Signal(str, object)


class UsageRequest(QRunnable):
    def __init__(self, path):
        super().__init__()
        self.path = path
        self.signals = UsageSignals()

    def run(self):
        try:
            usage = read_drive_usage(self.path)
        except (OSError, ValueError):
            usage = None
        self.signals.ready.emit(self.path, usage)


class DriveCapacityWidget(QWidget):
    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.path = path
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
