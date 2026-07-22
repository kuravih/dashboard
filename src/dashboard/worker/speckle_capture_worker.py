import time

import numpy as np
from pykato.function import sinusoid
from pykato.log import setup_logger
from PySide6.QtCore import Signal, Slot
from pytestbed import SinkSample, SourceSample

import dashboard

from pytestbed.device.camera import Camera
from pytestbed.device.modulator import Modulator
from pytestbed.function import find_speckles
from . import Worker, WorkerSignals

logger = setup_logger(f"{dashboard.SPECKLE_CAPTURE}_worker", terminator="\n")


class ProcessWorkerSignals(WorkerSignals):
    srcSampled = Signal(SourceSample)
    snkSampled = Signal(SinkSample)
    specklesLocated = Signal(np.ndarray)


class ProcessWorker(Worker):
    wid = f"{dashboard.SPECKLE_CAPTURE}_worker"

    _allowed_slots_ = Worker._allowed_slots_ | {"signals", "source", "sink", "amplitude_perc", "frequency_array", "angle_rad_array", "phase_rad_array", "n_reps"}

    def __init__(self, source: Camera, sink: Modulator, amplitude_perc: float, frequency_array: np.ndarray, angle_rad_array: np.ndarray, phase_rad_array: np.ndarray, n_reps: int):
        self.signals = ProcessWorkerSignals()
        self.source = source
        self.sink = sink
        self.amplitude_perc = amplitude_perc
        self.frequency_array = frequency_array
        self.angle_rad_array = angle_rad_array
        self.phase_rad_array = phase_rad_array
        self.n_reps = n_reps
        super().__init__(self.n_reps * self.frequency_array.size * self.angle_rad_array.size * (self.phase_rad_array.size + 1))  # blanks for subtraction

    def speckle_phase_sweep(self, speckle_amplitude: float, speckle_frequency: float, speckle_angle_rad: float, speckle_phase_rad_array: np.ndarray) -> list[tuple[float, float]]:

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
        while (speckle_phase_rad_array.size > i_phs) and self._running:
            probe = speckle_amplitude * sinusoid(self.sink.shape, 1.0 / speckle_frequency, angle=speckle_angle_rad, phase=speckle_phase_rad_array[i_phs])
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

        delta_probes = np.clip(sum_probe_capture / speckle_phase_rad_array.size - zero_source_sample.capture.astype(float), min=0)

        speckles, _ = find_speckles(delta_probes, 2, 5, 25)

        return speckles

    def speckle_frequency_angle_sweep(self, speckle_amplitude: float, n_reps: int, speckle_frequency_array: np.ndarray, speckle_angle_rad_array: np.ndarray, speckle_phase_rad_array: np.ndarray) -> np.ndarray:
        speckles = np.full((speckle_frequency_array.size, speckle_angle_rad_array.size, 2, 2), np.nan)
        i_rep = 0
        while n_reps > i_rep:
            i_freq = 0
            while (speckle_frequency_array.size > i_freq) and self._running:
                i_ang = 0
                while (speckle_angle_rad_array.size > i_ang) and self._running:
                    speckles[i_freq, i_ang] = self.speckle_phase_sweep(speckle_amplitude, speckle_frequency_array[i_freq], speckle_angle_rad_array[i_ang], speckle_phase_rad_array)
                    self.signals.specklesLocated.emit(speckles)
                    i_ang = i_ang + 1
                i_freq = i_freq + 1
            i_rep = i_rep + 1

        return speckles

    @Slot()
    def run(self):
        super().run()

        try:
            amplitude = self.sink.vrange * self.amplitude_perc
            self.speckle_frequency_angle_sweep(amplitude, self.n_reps, self.frequency_array, self.angle_rad_array, self.phase_rad_array)
        except AssertionError as e:
            self.signals.error.emit(str(e))

        logger.info("speckle_calibration_worker.py - ProcessWorker() finished")
        self.stop()
        self.signals.finished.emit()
