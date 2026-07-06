import time

import numpy as np
from pykato.log import setup_logger
from PySide6.QtCore import Signal, Slot

import testbed

from ..device import SinkSample, SourceSample
from ..device.camera import Camera
from . import Worker, WorkerSignals

logger = setup_logger(f"{testbed.CAMERA_CALIBRATION}_worker", terminator="\n")


class ProcessWorkerSignals(WorkerSignals):
    srcSampled = Signal(SourceSample)
    snkSampled = Signal(SinkSample)


class ProcessWorker(Worker):
    wid = f"{testbed.CAMERA_CALIBRATION}_worker"

    def __init__(self, source: Camera, exp_array: np.ndarray):
        self.signals = ProcessWorkerSignals()
        self.source = source
        self.exp_array = exp_array
        super().__init__(self.exp_array.size + 1)

    def exptime_sweep(self, exp_array: np.ndarray):
        i_exp = 0
        while (exp_array.size > i_exp) and self._running:
            self.source.set_exposure_time_s(float(exp_array[i_exp]))

            # ---- zero -----------------------------------------------------------------------------------------------
            source_sample = self.source.pull_capture()
            self.signals.srcSampled.emit(source_sample)
            time.sleep(0.1)

            i_exp = i_exp + 1

            self.i_tick = self.i_tick + 1
            self.signals.progressTicked.emit(self.i_tick, time.time() - self.t_start)
            # ---- zero -----------------------------------------------------------------------------------------------

    @Slot()
    def run(self):
        super().run()

        try:
            self.exptime_sweep(self.exp_array)
        except AssertionError as e:
            self.signals.error.emit(str(e))

        # ---- zero ---------------------------------------------------------------------------------------------------
        self.source.set_exposure_time_s(float(self.exp_array[0]))

        source_sample = self.source.pull_capture()
        self.signals.srcSampled.emit(source_sample)
        time.sleep(0.2)

        self.i_tick = self.i_tick + 1
        self.signals.progressTicked.emit(self.i_tick, time.time() - self.t_start)
        # ---- zero ---------------------------------------------------------------------------------------------------

        logger.info("camera_calibration_worker.py - ProcessWorker() finished")
        self.stop()
        self.signals.finished.emit()
