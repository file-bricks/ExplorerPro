"""Keep cyclic Python garbage collection on the Qt application thread.

PySide wrappers can be part of Python reference cycles. Automatic collection
may run in whichever thread happens to allocate, including a hashing worker;
destroying a GUI QObject there is unsafe. Reference counting is unaffected.
"""

import gc

from PySide6.QtCore import QObject, QThread, QTimer, Slot


class GuiGarbageCollector(QObject):
    def __init__(self, application):
        if QThread.currentThread() != application.thread():
            raise RuntimeError("Install the collector on the application thread")
        super().__init__(application)
        self._previously_enabled = gc.isenabled()
        self._closed = False
        self._ticks = 0
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.collect_if_needed)
        if self._previously_enabled:
            self.timer.start()
        gc.disable()

    def _assert_gui_thread(self):
        if QThread.currentThread() != self.thread():
            raise RuntimeError("Collect Qt reference cycles on the application thread")

    @Slot()
    def collect_if_needed(self):
        self._assert_gui_thread()
        if self._closed:
            return
        self._ticks += 1
        counts = gc.get_count()
        thresholds = gc.get_threshold()
        # Periodically revisit older cycles even if allocation has subsided.
        if self._ticks >= 30 or counts[2] >= thresholds[2]:
            self.collect()
        elif counts[1] >= thresholds[1]:
            gc.collect(1)
        elif counts[0] >= thresholds[0]:
            gc.collect(0)

    def collect(self):
        self._assert_gui_thread()
        if not self._closed:
            self._ticks = 0
            return gc.collect()
        return 0

    def close(self):
        """Restore GC policy after application workers have stopped."""
        self._assert_gui_thread()
        if self._closed:
            return
        try:
            self.timer.stop()
            self.collect()
        finally:
            self._closed = True
            if self._previously_enabled:
                gc.enable()
            else:
                gc.disable()


def install_gui_gc(application):
    """Install once; the application retains the Python wrapper and Qt owner."""
    existing = getattr(application, "_gui_garbage_collector", None)
    if existing is None or existing._closed:
        existing = GuiGarbageCollector(application)
        application._gui_garbage_collector = existing
    return existing
