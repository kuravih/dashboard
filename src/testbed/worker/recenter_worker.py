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
        self.signals = ProcessWorkerSignals()
        self.source = source
        self.sink = sink
        self.amplitude = amplitude
        self.n_steps = n_steps
        super().__init__(1 + 2 * self.n_steps) # blank for subtraction

    def speckle_phase_sweep(self, current_cmd: np.ndarray, current_cap: np.ndarray, speckle_amplitude: float, speckle_frequency: float, speckle_angle: float, speckle_phase_array: np.ndarray) -> list[tuple[float, float]]:
        i_phs = 0
        sum_probe_capture = np.zeros_like(current_cap, dtype=float)
        while (speckle_phase_array.size > i_phs) and self._running:

            probe = speckle_amplitude * sinusoid(self.sink.shape, 1.0 / speckle_frequency, angle=speckle_angle, phase=speckle_phase_array[i_phs])
            probe_cmd = current_cmd + probe

            probe_sink_sample = self.sink.push_command(probe_cmd)
            self.signals.snkSampled.emit(probe_sink_sample)
            time.sleep(0.1)

            probe_source_sample = self.source.pull_capture()
            self.signals.srcSampled.emit(probe_source_sample)
            time.sleep(0.2)

            sum_probe_capture = sum_probe_capture + probe_source_sample.capture

            i_phs = i_phs + 1

            self.i_tick = self.i_tick + 1
            self.signals.progressTicked.emit(self.i_tick, time.time() - self.t_start)

        speckles, speckle_stencil = find_speckles(sum_probe_capture / speckle_phase_array.size - current_cap.astype(float), 2, 5, 50)

        return speckles

    def speckle_angle_sweep(self, current_cmd: np.ndarray, current_cap: np.ndarray, speckle_amplitude: float, speckle_frequency: float, speckle_angle_array: np.ndarray, speckle_phase_array: np.ndarray):
        speckles = np.full((speckle_angle_array.size, 2, 2), np.nan)
        i_ang = 0
        while (speckle_angle_array.size > i_ang) and self._running:
            speckles[i_ang] = self.speckle_phase_sweep(current_cmd, current_cap, speckle_amplitude, speckle_frequency, speckle_angle_array[i_ang], speckle_phase_array)
            i_ang = i_ang + 1
            self.signals.specklesLocated.emit(speckles)

        return speckles

    def find_center(self, current_cmd: np.ndarray, current_cap: np.ndarray, n_steps: int) -> tuple[float, float]:
        speckle_frequency = 0.035
        speckle_angle_array = np.linspace(0, 180, n_steps, endpoint=False) + (180.0 / n_steps) / 2 # degrees
        speckle_phase_array = np.array([0, 90, 180, 270])  # degrees
        speckles = self.speckle_angle_sweep(current_cmd, current_cap, self.amplitude, speckle_frequency, np.deg2rad(speckle_angle_array), np.deg2rad(speckle_phase_array))
        return np.mean(speckles, axis=(0, 1))

    @Slot()
    def run(self):
        super().run()

        # ---- zero ---------------------------------------------------------------------------------------------------
        zero_cmd = np.zeros(self.sink.shape)

        zero_sink_sample = self.sink.push_command(zero_cmd)
        self.signals.snkSampled.emit(zero_sink_sample)
        time.sleep(0.1)

        zero_source_sample = self.source.pull_capture()
        self.signals.srcSampled.emit(zero_source_sample)
        time.sleep(0.2)

        self.signals.progressTicked.emit(self.i_tick, time.time() - self.t_start)
        # ---- zero ---------------------------------------------------------------------------------------------------

        center = self.find_center(zero_sink_sample.command, zero_source_sample.capture, self.n_steps)
        self.signals.centerLocated.emit(*center)

        logger.info("recenter_worker.py - ProcessWorker() finished")
        self.stop()
        self.signals.finished.emit()
