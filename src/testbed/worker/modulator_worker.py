import time
from PySide6.QtCore import Signal, Slot

from pykato.log import setup_logger

from ..device import SinkSample
from ..device.modulator import Modulator
from ..worker import Worker, WorkerSignals

logger = setup_logger("modulator_worker", terminator="\n")


class UpdateWorkerSignals(WorkerSignals):
    sampled = Signal(SinkSample)


class UpdateWorker(Worker):
    def __init__(self, modulator: Modulator):
        super().__init__()
        self.signals = UpdateWorkerSignals()
        self._modulator = modulator

    @Slot()
    def run(self):
        super().run()
        while self._running:
            time.sleep(0.1)
            self.signals.sampled.emit(self._modulator.sample)
