import time
import numpy as np
from PySide6.QtCore import Slot, Signal

from pykato.log import setup_logger

import testbed
from ..device import SourceSample, SinkSample
from ..device.camera import Camera
from . import Worker, WorkerSignals

_PROCESS_ = testbed.CAMERA_CALIBRATION

logger = setup_logger(f"{_PROCESS_}_worker", terminator="\n")


class ProcessWorkerSignals(WorkerSignals):
    srcSampled = Signal(SourceSample)
    snkSampled = Signal(SinkSample)


class ProcessWorker(Worker):
    def __init__(self, source: Camera, exp_array: np.ndarray):
        super().__init__()
        self.signals = ProcessWorkerSignals()
        self.source = source
        self.exp_array = exp_array

    @Slot()
    def run(self):
        super().run()
        i_exp = 0
        t_start = time.time()

        # ---- blank --------------------------------------------------------------------------------------------------
        self.signals.srcSampled.emit(self.source.pull_capture())
        time.sleep(0.2)

        self.signals.progressTicked.emit(i_exp, time.time() - t_start)
        # ---- blank --------------------------------------------------------------------------------------------------

        logger.info("%s ProcessWorker.run : step %i of %i", self.source.name, i_exp, self.exp_array.size)

        i_exp = 0
        while (self.exp_array.size > i_exp) and self._running:

            self.source.set_exposure_time_us(int(self.exp_array[i_exp]))

            _current_source_sample = self.source.pull_capture()
            self.signals.srcSampled.emit(_current_source_sample)
            time.sleep(0.2)

            i_exp = i_exp + 1
            self.signals.progressTicked.emit(i_exp, time.time() - t_start)

            logger.info("%s ProcessWorker.run : step %i of %i", self.source.name, i_exp, self.exp_array.size)
            
        self.signals.finished.emit()