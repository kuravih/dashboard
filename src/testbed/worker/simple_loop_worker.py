import time

import numpy as np
from pykato.function import text
from pykato.log import setup_logger
from PySide6.QtCore import Signal, Slot

import testbed

from ..device import SinkSample, SourceSample
from ..device.camera import Camera
from ..device.modulator import Modulator
from . import Worker, WorkerSignals

logger = setup_logger(f"{testbed.SIMPLE_LOOP}_worker", terminator="\n")


class ProcessWorkerSignals(WorkerSignals):
    srcSampled = Signal(SourceSample)
    snkSampled = Signal(SinkSample)


class ProcessWorker(Worker):
    wid = f"{testbed.SIMPLE_LOOP}_worker"

    def __init__(self, source: Camera, sink: Modulator, amplitude_perc: float, n_steps: int = 0):
        self.signals = ProcessWorkerSignals()
        self.source = source
        self.sink = sink
        self.amplitude_perc = amplitude_perc
        self.n_steps = n_steps
        if self.n_steps:
            super().__init__(self.n_steps + 1)  # blank at the end
        else:
            super().__init__(0)

    def count_sweep(self, amplitude_perc: float, n_steps: int = 0):
        zero_cmd = np.zeros(self.sink.shape)
        i_step = 0
        while ((n_steps == 0) or (n_steps > i_step)) and self._running:
            count = amplitude_perc * text(self.sink.shape, f"{i_step:02d}", font_size=150)
            count_cmd = zero_cmd + count

            count_sink_sample = self.sink.push_command(count_cmd)
            self.signals.snkSampled.emit(count_sink_sample)
            time.sleep(0.1)

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
            amplitude = self.sink.vrange * self.amplitude_perc
            self.count_sweep(amplitude, self.n_steps)
        except AssertionError as e:
            self.signals.error.emit(str(e))

        # ---- zero ---------------------------------------------------------------------------------------------------
        zero_cmd = np.zeros(self.sink.shape)

        zero_sink_sample = self.sink.push_command(zero_cmd)
        self.signals.snkSampled.emit(zero_sink_sample)
        time.sleep(0.1)

        zero_source_sample = self.source.pull_capture()
        self.signals.srcSampled.emit(zero_source_sample)
        time.sleep(0.2)

        self.i_tick = self.i_tick + 1
        self.signals.progressTicked.emit(self.i_tick, time.time() - self.t_start)
        # ---- zero ---------------------------------------------------------------------------------------------------

        logger.info("simple_loop_worker.py - ProcessWorker() finished")
        self.stop()
        self.signals.finished.emit()
