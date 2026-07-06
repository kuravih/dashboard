import time

from PySide6.QtCore import QObject, QRunnable, Signal, Slot


class WorkerSignals(QObject):
    progressTicked = Signal(int, float)  # step, elapsed_time
    finished = Signal()
    error = Signal(str)


class Worker(QRunnable):
    def __init__(self, n_ticks: int | None = None) -> None:
        self.n_ticks = n_ticks
        super().__init__()

    def stop(self):
        self._running = False

    @Slot()
    def run(self):
        self.i_tick = 0
        self.t_start = time.time()
        self._running = True
