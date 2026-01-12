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


class MainWorkerSignals(WorkerSignals):
    new_source_sample = Signal(SourceSample)
    new_sink_sample = Signal(SinkSample)


class MainWorker(Worker):
    def __init__(self, _source: Camera, _sink: Modulator, _ampl: float, _freqs: np.ndarray, _angles: np.ndarray, _phases: np.ndarray):
        super().__init__()
        self.signals = MainWorkerSignals()
        self._source = _source
        self._sink = _sink
        self._ampl = _ampl
        self._freqs = _freqs
        self._angles = _angles
        self._phases = _phases
        self._n_steps = _freqs.size * _angles.size * _phases.size

    @Slot()
    def run(self):
        super().run()
        i_step = 0
        t_start = time.time()

        # ---- blank --------------------------------------------------------------------------------------------------
        command = self._sink.pxmax * np.clip(np.zeros(self._sink.shape) + 0.5, 0, 1)

        self.signals.new_sink_sample.emit(self._sink.push_command(command.astype(np.uint16)))
        time.sleep(0.1)

        self.signals.new_source_sample.emit(self._source.pull_capture())
        time.sleep(0.2)

        self.signals.progress.emit(i_step, time.time() - t_start)
        # ---- blank --------------------------------------------------------------------------------------------------

        logger.info("%s and %s MainWorker.run : step %s of %s", self._source.name, self._sink.name, i_step, self._n_steps)

        i_freq = 0
        while (self._freqs.size > i_freq) and self._running:
            i_angle = 0
            while (self._angles.size > i_angle) and self._running:
                i_phase = 0
                while (self._phases.size > i_phase) and self._running:

                    command = self._sink.pxmax * np.clip(self._ampl * sinusoid(self._sink.shape, 1.0 / self._freqs[i_freq], np.deg2rad(self._phases[i_phase]), np.deg2rad(self._angles[i_angle])) + 0.5, 0, 1)

                    self.signals.new_sink_sample.emit(self._sink.push_command(command.astype(np.uint16)))
                    time.sleep(0.1)

                    self.signals.new_source_sample.emit(self._source.pull_capture())
                    time.sleep(0.2)

                    i_step = i_step + 1
                    self.signals.progress.emit(i_step, time.time() - t_start)

                    logger.info("%s and %s MainWorker.run : step %s of %s", self._source.name, self._sink.name, i_step, self._n_steps)

                    i_phase = i_phase + 1

                i_angle = i_angle + 1

            i_freq = i_freq + 1

        self.signals.finished.emit()

        # self._sink.push_command(_current_sink_sample.command.astype(np.uint16))
