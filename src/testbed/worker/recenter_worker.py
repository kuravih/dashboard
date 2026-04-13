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
from ..function import find_speckles

_PROCESS_ = testbed.RECENTER

logger = setup_logger(f"{_PROCESS_}_worker", terminator="\n")


class ProcessWorkerSignals(WorkerSignals):
    srcSampled = Signal(SourceSample)
    snkSampled = Signal(SinkSample)
    specklesLocated = Signal(np.ndarray)
    centerLocated = Signal(float, float)


class ProcessWorker(Worker):
    def __init__(self, source: Camera, sink: Modulator, amplitude: float, n_steps: int):
        super().__init__()
        self.signals = ProcessWorkerSignals()
        self.source = source
        self.sink = sink
        self.amplitude = amplitude
        self.n_steps = n_steps

    def find_center(self, current_cmd: np.ndarray, current_cap: np.ndarray, n_steps: int) -> tuple[float, float]:
        speckle_frequency = 0.035
        phs_array = np.array([0, 90])
        self.ang_array = np.linspace(0, 180, n_steps, endpoint=False) + (180.0 / n_steps) / 2
        i_ang = 0
        all_speckles = np.full((self.ang_array.size, 2, 2), np.nan)
        t_start = time.time()

        while (self.ang_array.size > i_ang) and self._running:
            i_phs = 0
            mean_cap = np.zeros_like(current_cap, dtype=float)
            while (phs_array.size > i_phs) and self._running:

                probe_command = self.amplitude * sinusoid(self.sink.shape, 1.0 / speckle_frequency, np.deg2rad(phs_array[i_phs]), np.deg2rad(self.ang_array[i_ang]))

                command = current_cmd + probe_command

                _current_sink_sample = self.sink.push_command(command)
                self.signals.snkSampled.emit(_current_sink_sample)
                time.sleep(0.1)

                _current_source_sample = self.source.pull_capture()
                self.signals.srcSampled.emit(_current_source_sample)
                time.sleep(0.2)

                mean_cap = mean_cap + _current_source_sample.capture

                i_phs = i_phs + 1

            all_speckles[i_ang], speckle_stencil = find_speckles(mean_cap / 2 - current_cap.astype(float), 2, 5, 50)

            i_ang = i_ang + 1

            self.signals.specklesLocated.emit(all_speckles)
            self.signals.progressTicked.emit(i_ang, time.time() - t_start)

        return np.mean(all_speckles, axis=(0, 1))

    def recenter(self, current_cmd: np.ndarray, current_cap: np.ndarray, n_steps: int):
        center = self.find_center(current_cmd, current_cap, n_steps)
        self.signals.centerLocated.emit(*center)

    @Slot()
    def run(self):
        super().run()
        t_start = time.time()

        # ---- blank --------------------------------------------------------------------------------------------------
        current_cmd = np.zeros(self.sink.shape)

        command = current_cmd
        command = np.clip(command, 0, self.sink.pxmax)

        _current_sink_sample = self.sink.push_command(command)
        self.signals.snkSampled.emit(_current_sink_sample)
        time.sleep(0.1)

        _current_source_sample = self.source.pull_capture()
        self.signals.srcSampled.emit(_current_source_sample)
        time.sleep(0.2)

        i_step = 0
        self.signals.progressTicked.emit(i_step, time.time() - t_start)
        # ---- blank --------------------------------------------------------------------------------------------------

        logger.info("%s and %s ProcessWorker.run : step %i of %i", self.source.name, self.sink.name, i_step, self.n_steps)

        self.recenter(_current_sink_sample.command, _current_source_sample.capture, self.n_steps)

        time.sleep(0.2)

        self.stop()
        self.signals.finished.emit()
