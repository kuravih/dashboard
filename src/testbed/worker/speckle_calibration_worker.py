import time
import numpy as np
from PySide6.QtCore import Slot, Signal

from pykato.function import sinusoid
from pykato.log import setup_logger

import testbed
from ..device import SourceSample, SinkSample
from ..device.camera import Camera
from ..device.modulator import Modulator
from . import Worker, WorkerSignals

_PROCESS_ = testbed.SPECKLE_CALIBRATION

logger = setup_logger(f"{_PROCESS_}_worker", terminator="\n")


class ProcessWorkerSignals(WorkerSignals):
    srcSampled = Signal(SourceSample)
    snkSampled = Signal(SinkSample)


class ProcessWorker(Worker):
    def __init__(self, source: Camera, sink: Modulator, amplitude: float, freq_array: np.ndarray, ang_array: np.ndarray, phs_array: np.ndarray):
        super().__init__()
        self.signals = ProcessWorkerSignals()
        self.source = source
        self.sink = sink
        self.amplitude = amplitude
        self.freq_array = freq_array
        self.ang_array = ang_array
        self.phs_array = phs_array
        self.n_steps = freq_array.size * ang_array.size * phs_array.size

    @Slot()
    def run(self):
        super().run()
        i_step = 0
        t_start = time.time()

        # ---- blank --------------------------------------------------------------------------------------------------
        current_cmd = np.zeros(self.sink.shape)

        self.signals.snkSampled.emit(self.sink.push_command(current_cmd))
        time.sleep(0.1)

        self.signals.srcSampled.emit(self.source.pull_capture())
        time.sleep(0.2)

        self.signals.progressTicked.emit(i_step, time.time() - t_start)
        # ---- blank --------------------------------------------------------------------------------------------------

        logger.info("%s and %s ProcessWorker.run : step %i of %i", self.source.name, self.sink.name, i_step, self.n_steps)

        i_freq = 0
        while (self.freq_array.size > i_freq) and self._running:
            i_ang = 0
            while (self.ang_array.size > i_ang) and self._running:
                i_phs = 0
                while (self.phs_array.size > i_phs) and self._running:

                    probe_command = self.amplitude * sinusoid(self.sink.shape, 1.0 / self.freq_array[i_freq], np.deg2rad(self.phs_array[i_phs]), np.deg2rad(self.ang_array[i_ang]))

                    command = current_cmd + probe_command

                    _current_sink_sample = self.sink.push_command(command)
                    self.signals.snkSampled.emit(_current_sink_sample)
                    time.sleep(0.1)

                    _current_source_sample = self.source.pull_capture()
                    self.signals.srcSampled.emit(_current_source_sample)
                    time.sleep(0.2)

                    i_step = i_step + 1
                    self.signals.progressTicked.emit(i_step, time.time() - t_start)

                    logger.info("%s and %s ProcessWorker.run : step %i of %i", self.source.name, self.sink.name, i_step, self.n_steps)

                    i_phs = i_phs + 1

                i_ang = i_ang + 1

            i_freq = i_freq + 1

        logger.info("speckle_calibration_worker.py - ProcessWorker() finished")
        self.stop()
        self.signals.finished.emit()
