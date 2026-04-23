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

logger = setup_logger(f"{testbed.RECENTER}_worker", terminator="\n")


class ProcessWorkerSignals(WorkerSignals):
    srcSampled = Signal(SourceSample)
    snkSampled = Signal(SinkSample)
    specklesLocated = Signal(np.ndarray)
    centerLocated = Signal(float, float)


class ProcessWorker(Worker):

    wid = f"{testbed.RECENTER}_worker"

    def __init__(self, source: Camera, sink: Modulator, amplitude: float, n_steps: int):
        self.signals = ProcessWorkerSignals()
        self.source = source
        self.sink = sink
        self.amplitude = amplitude
        self.frequency = 0.035
        self.ang_array = np.linspace(0.0, 180.0, n_steps, endpoint=False) + (180.0 / n_steps) / 2  # degrees
        self.phs_array = np.array([0.0, 90.0, 180.0, 270.0])  # degrees
        super().__init__(self.ang_array.size * (self.phs_array.size + 1) + 1)  # blank

    def speckle_phase_sweep(self, speckle_amplitude: float, speckle_frequency: float, speckle_angle: float, speckle_phase_array: np.ndarray) -> list[tuple[float, float]]:

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

        i_phs = 0
        sum_probe_capture = np.zeros_like(self.source.blank, dtype=float)
        while (speckle_phase_array.size > i_phs) and self._running:

            probe = speckle_amplitude * sinusoid(self.sink.shape, 1.0 / speckle_frequency, angle=speckle_angle, phase=speckle_phase_array[i_phs])
            probe_cmd = zero_cmd + probe

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

        delta_probes = np.clip(sum_probe_capture / speckle_phase_array.size - zero_source_sample.capture.astype(float), min=0)

        speckles, _ = find_speckles(delta_probes, 2, 5, 50)

        return speckles

    def speckle_angle_sweep(self, speckle_amplitude: float, speckle_frequency: float, speckle_angle_array: np.ndarray, speckle_phase_array: np.ndarray):
        speckles = np.full((speckle_angle_array.size, 2, 2), np.nan)
        i_ang = 0
        while (speckle_angle_array.size > i_ang) and self._running:
            speckles[i_ang] = self.speckle_phase_sweep(speckle_amplitude, speckle_frequency, speckle_angle_array[i_ang], speckle_phase_array)
            i_ang = i_ang + 1
            self.signals.specklesLocated.emit(speckles)
        return speckles

    def find_center(self) -> tuple[float, float]:
        speckles = self.speckle_angle_sweep(self.amplitude, self.frequency, np.deg2rad(self.ang_array), np.deg2rad(self.phs_array))
        return np.mean(speckles, axis=(0, 1))

    @Slot()
    def run(self):
        super().run()

        try:
            center = self.find_center()
        except AssertionError as e:
            self.signals.error.emit(str(e))
        else:
            self.signals.centerLocated.emit(*center)

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

        logger.info("recenter_worker.py - ProcessWorker() finished")
        self.stop()
        self.signals.finished.emit()
