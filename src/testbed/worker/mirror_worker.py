import time
import numpy as np
from PySide6.QtCore import Signal, Slot

from pykato.function import preroll
from pykato.log import setup_logger

from ..device import SinkSample
from ..device.mirror import Mirror
from ..worker import Worker, WorkerSignals

logger = setup_logger("mirror_worker", terminator="\n")


class UpdateWorkerSignals(WorkerSignals):
    new_sample = Signal(SinkSample)


class UpdateWorker(Worker):

    def __init__(self, mirror: Mirror):
        super().__init__()
        self.signals = UpdateWorkerSignals()
        self._mirror = mirror

    @Slot()
    def run(self):
        super().run()
        while self._running:
            time.sleep(0.1)
            # logger.info("%s UpdateWorker.run", self._mirror.name)
            count = time.time() % 60.0
            self._mirror.push_command(((2**16 - 1) * preroll(self._modulator.shape, int(count), count / 60.0, 100)).astype(np.uint16))
            self.signals.new_sample.emit(self._modulator.pull_sample())

        logger.info("mirror_worker.py - ProcessWorker() finished")
        self.stop()
        self.signals.finished.emit()
