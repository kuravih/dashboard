import time

import numpy as np
from pykato.function import sinusoid
from pykato.log import setup_logger
from PySide6.QtCore import Signal, Slot

import testbed

from ..device import SinkSample, SourceSample
from ..device.camera import Camera
from ..device.modulator import Modulator
from ..function import find_speckles
from . import Worker, WorkerSignals

logger = setup_logger(f"{testbed.RECENTER}_worker", terminator="\n")


class ProcessWorkerSignals(WorkerSignals):
    srcSampled = Signal(SourceSample)
    snkSampled = Signal(SinkSample)
    specklesLocated = Signal(np.ndarray)
    centerLocated = Signal(float, float)


class ProcessWorker(Worker):
    wid = f"{testbed.RECENTER}_worker"

    def __init__(self, source: Camera, sink: Modulator, amplitude_perc: float):
        self.signals = ProcessWorkerSignals()
        self.source = source
        self.sink = sink
        self.amplitude_perc = amplitude_perc
        self.frequency = 0.035
        self.speckle_angle_rad_array = np.array([0, 1]) * np.pi / 2 + np.pi / 4
        self.speckle_phase_rad_array = np.array([0, 1]) * np.pi / 2
        super().__init__(3)  # blank + positive + negative

    def speckle_phase_sweep(self, speckle_amplitude: float, speckle_frequency: float, speckle_angle_rad_array: np.ndarray, speckle_phase_rad_array: np.ndarray) -> list[tuple[float, float]]:

        probe_zero = np.zeros(self.sink.shape)

        probe_zero_sink_sample = self.sink.push_command(probe_zero)
        self.signals.snkSampled.emit(probe_zero_sink_sample)
        time.sleep(0.1)

        probe_zero_source_sample = self.source.pull_capture()
        self.signals.srcSampled.emit(probe_zero_source_sample)
        time.sleep(0.2)

        self.i_tick = self.i_tick + 1
        self.signals.progressTicked.emit(self.i_tick, time.time() - self.t_start)

        probe_positive = speckle_amplitude * (sinusoid(self.sink.shape, 1.0 / speckle_frequency, angle=speckle_angle_rad_array[0], phase=speckle_phase_rad_array[0]) + sinusoid(self.sink.shape, 1.0 / speckle_frequency, angle=speckle_angle_rad_array[1], phase=speckle_phase_rad_array[0]))

        probe_positive_sink_sample = self.sink.push_command(probe_positive)
        self.signals.snkSampled.emit(probe_positive_sink_sample)
        time.sleep(0.1)

        probe_positive_source_sample = self.source.pull_capture()
        self.signals.srcSampled.emit(probe_positive_source_sample)
        time.sleep(0.2)

        self.i_tick = self.i_tick + 1
        self.signals.progressTicked.emit(self.i_tick, time.time() - self.t_start)

        probe_negative = speckle_amplitude * (sinusoid(self.sink.shape, 1.0 / speckle_frequency, angle=speckle_angle_rad_array[0], phase=speckle_phase_rad_array[1]) + sinusoid(self.sink.shape, 1.0 / speckle_frequency, angle=speckle_angle_rad_array[1], phase=speckle_phase_rad_array[1]))

        probe_negative_sink_sample = self.sink.push_command(probe_negative)
        self.signals.snkSampled.emit(probe_negative_sink_sample)
        time.sleep(0.1)

        probe_negative_source_sample = self.source.pull_capture()
        self.signals.srcSampled.emit(probe_negative_source_sample)
        time.sleep(0.2)

        self.i_tick = self.i_tick + 1
        self.signals.progressTicked.emit(self.i_tick, time.time() - self.t_start)

        speckles_image = np.clip((probe_positive_source_sample.capture + probe_negative_source_sample.capture) / 2 - probe_zero_source_sample.capture, min=0)

        speckles, _ = find_speckles(speckles_image, 4, 5, 50)

        self.signals.specklesLocated.emit(np.array(speckles))

        return speckles

    def find_center(self, speckle_amplitude: float, speckle_frequency: float, speckle_angle_rad_array: np.ndarray, speckle_phase_rad_array: np.ndarray) -> tuple[float, float]:
        speckles = self.speckle_phase_sweep(speckle_amplitude, speckle_frequency, speckle_angle_rad_array, speckle_phase_rad_array)
        return np.mean(speckles, axis=(0))

    @Slot()
    def run(self):
        super().run()

        try:
            amplitude = self.sink.vrange * self.amplitude_perc
            center = self.find_center(amplitude, self.frequency, self.speckle_angle_rad_array, self.speckle_phase_rad_array)
        except AssertionError as e:
            self.signals.error.emit(str(e))
        else:
            self.signals.centerLocated.emit(*center)

        logger.info("recenter_worker.py - ProcessWorker() finished")
        self.stop()
        self.signals.finished.emit()
