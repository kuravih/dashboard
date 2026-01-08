from PySide6.QtCore import QRunnable, Slot, QObject, Signal


class WorkerSignals(QObject):
    progress = Signal(int, float)  # step, elapsed_time
    finished = Signal()


class Worker(QRunnable):

    def stop(self):
        self._running = False

    @Slot()
    def run(self):
        self._running = True
