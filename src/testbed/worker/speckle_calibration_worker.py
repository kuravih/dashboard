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

_PROCESS_ = testbed.SPECKLE_CALIBRATION

logger = setup_logger(f"{_PROCESS_}_worker", terminator="\n")


class ProcessWorkerSignals(WorkerSignals):
    srcSampled = Signal(SourceSample)
    snkSampled = Signal(SinkSample)
    specklesLocated = Signal(np.ndarray)


class ProcessWorker(Worker):
    def __init__(self, source: Camera, sink: Modulator, amplitude: float, freq_array: np.ndarray, ang_array: np.ndarray, phs_array: np.ndarray):
        self.signals = ProcessWorkerSignals()
        self.source = source
        self.sink = sink
        self.amplitude = amplitude
        self.freq_array = freq_array
        self.ang_array = ang_array  # degrees
        self.phs_array = phs_array  # degrees
        super().__init__(1 + freq_array.size * ang_array.size * (phs_array.size + 1))  # blanks for subtraction

    def speckle_phase_sweep(self, current_cmd: np.ndarray, current_cap: np.ndarray, speckle_amplitude: float, speckle_frequency: float, speckle_angle: float, speckle_phase_array: np.ndarray) -> list[tuple[float, float]]:

        # ---- blank --------------------------------------------------------------------------------------------------
        current_sink_sample = self.sink.push_command(current_cmd)
        self.signals.snkSampled.emit(current_sink_sample)
        time.sleep(0.1)

        current_source_sample = self.source.pull_capture()
        current_cap[:] = current_source_sample.capture[:]
        self.signals.srcSampled.emit(current_source_sample)
        time.sleep(0.2)

        self.i_tick = self.i_tick + 1
        self.signals.progressTicked.emit(self.i_tick, time.time() - self.t_start)
        # ---- blank --------------------------------------------------------------------------------------------------

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

        delta_probes = np.clip(sum_probe_capture / speckle_phase_array.size - current_cap.astype(float), min=0)

        speckles, speckle_stencil = find_speckles(delta_probes, 2, 5, 50)

        return speckles

    def speckle_frequency_angle_sweep(self, current_cmd: np.ndarray, current_cap: np.ndarray, speckle_amplitude: float, speckle_frequency_array: np.ndarray, speckle_angle_array: np.ndarray, speckle_phase_array: np.ndarray) -> np.ndarray:
        speckles = np.full((speckle_frequency_array.size, speckle_angle_array.size, 2, 2), np.nan)
        i_freq = 0
        while (speckle_frequency_array.size > i_freq) and self._running:
            i_ang = 0
            while (speckle_angle_array.size > i_ang) and self._running:
                speckles[i_freq, i_ang] = self.speckle_phase_sweep(current_cmd, current_cap, speckle_amplitude, speckle_frequency_array[i_freq], speckle_angle_array[i_ang], speckle_phase_array)
                self.signals.specklesLocated.emit(speckles)
                i_ang = i_ang + 1
            i_freq = i_freq + 1
        return speckles

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

        self.speckle_frequency_angle_sweep(zero_sink_sample.command, zero_source_sample.capture, self.amplitude, self.freq_array, np.deg2rad(self.ang_array), np.deg2rad(self.phs_array))

        logger.info("speckle_calibration_worker.py - ProcessWorker() finished")
        self.stop()
        self.signals.finished.emit()
