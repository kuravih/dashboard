import time

from pykato.log import setup_logger
from PySide6.QtCore import Signal, Slot

from ..device import SinkSample
from ..device.modulator import Modulator
from ..worker import Worker, WorkerSignals

logger = setup_logger("modulator_sampling_worker", terminator="\n")


class ProcessWorkerSignals(WorkerSignals):
    sampled = Signal(SinkSample)


class ProcessWorker(Worker):
    def __init__(self, modulator: Modulator):
        super().__init__()
        self.signals = ProcessWorkerSignals()
        self._modulator = modulator

    @property
    def wid(self):
        return f"{self._modulator.name}_sampling_worker"

    @Slot()
    def run(self):
        super().run()
        while self._running:
            time.sleep(0.1)
            self.signals.sampled.emit(self._modulator.sample)

        logger.info("modulator_worker.py - ProcessWorker() finished")
        self.stop()
        self.signals.finished.emit()
