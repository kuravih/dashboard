import time

from PySide6.QtCore import QObject, QRunnable, Signal, Slot


class WorkerSignals(QObject):
    progressTicked = Signal(int, float)  # step, elapsed_time
    finished = Signal()
    error = Signal(str)


class Worker(QRunnable):
    _allowed_slots_ = {"n_ticks", "i_tick", "t_start", "_running"}

    def __setattr__(self, name, value):
        is_property = isinstance(getattr(type(self), name, None), property)
        if not is_property and name not in self._allowed_slots_ and not name.startswith("_"):
            raise AttributeError(f"Cannot set undeclared attribute '{name}'")
        super().__setattr__(name, value)

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
