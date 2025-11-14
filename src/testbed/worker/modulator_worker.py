import time
import numpy as np
from PySide6.QtCore import Signal, Slot

from pykato.function import preroll
from pykato.log import setup_logger

from ..device import SinkSample
from ..device.modulator import Modulator
from ..worker import Worker, WorkerSignals

logger = setup_logger("modulator_worker", terminator="\n")


class UpdateWorkerSignals(WorkerSignals):
    new_sample = Signal(SinkSample)


class UpdateWorker(Worker):
    def __init__(self, _modulator: Modulator):
        super().__init__()
        self.signals = UpdateWorkerSignals()
        self._modulator = _modulator

    @Slot()
    def run(self):
        super().run()
        while self._running:
            time.sleep(0.1)
            # logger.info("%s UpdateWorker.run", self._modulator.name)
            count = time.time() % 60.0
            command = (2**16 - 1) * preroll(self._modulator.shape, int(count), count / 60.0, 100)
            self._modulator.push_command(command.astype(np.uint16))
            self.signals.new_sample.emit(self._modulator.pull_sample())
