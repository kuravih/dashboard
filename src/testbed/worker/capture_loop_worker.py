import time
from PySide6.QtCore import Slot, Signal

from pykato.log import setup_logger

import testbed
from ..device import SourceSample, SinkSample
from ..device.camera import Camera
from . import Worker, WorkerSignals

logger = setup_logger(f"{testbed.CAPTURE_LOOP}_worker", terminator="\n")


class ProcessWorkerSignals(WorkerSignals):
    srcSampled = Signal(SourceSample)
    snkSampled = Signal(SinkSample)


class ProcessWorker(Worker):

    wid = f"{testbed.CAPTURE_LOOP}_worker"

    def __init__(self, source: Camera, n_steps: int = 0):
        self.signals = ProcessWorkerSignals()
        self.source = source
        self.n_steps = n_steps
        super().__init__(self.n_steps + 1)  # blank at the end

    def count_sweep(self, n_steps: int = 0):
        i_step = 0
        while ((n_steps is 0) or (n_steps > i_step)) and self._running:

            count_source_sample = self.source.pull_capture()
            self.signals.srcSampled.emit(count_source_sample)
            time.sleep(0.2)

            i_step = i_step + 1

            self.i_tick = self.i_tick + 1
            self.signals.progressTicked.emit(self.i_tick, time.time() - self.t_start)

    @Slot()
    def run(self):
        super().run()

        try:
            self.count_sweep(self.n_steps)
        except AssertionError as e:
            self.signals.error.emit(str(e))

        # ---- zero ---------------------------------------------------------------------------------------------------
        zero_source_sample = self.source.pull_capture()
        self.signals.srcSampled.emit(zero_source_sample)
        time.sleep(0.1)

        self.i_tick = self.i_tick + 1
        self.signals.progressTicked.emit(self.i_tick, time.time() - self.t_start)
        # ---- zero ---------------------------------------------------------------------------------------------------

        logger.info("capture_loop_worker.py - ProcessWorker() finished")
        self.stop()
        self.signals.finished.emit()
