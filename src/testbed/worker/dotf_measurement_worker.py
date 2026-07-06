import time

import numpy as np
from numpy.typing import NDArray
from pykato.function import psf_to_otf
from pykato.log import setup_logger
from PySide6.QtCore import Signal, Slot

import testbed

from ..device import SinkSample, SourceSample
from ..device.camera import Camera
from ..device.modulator import Modulator
from ..function import DOTFProbeDirection, dotf_probe, image_shift, locate_single_airy, locate_single_airy_with_radius
from . import Worker, WorkerSignals

logger = setup_logger(f"{testbed.DOTF_MEASUREMENT}_worker", terminator="\n")


class ProcessWorkerSignals(WorkerSignals):
    srcSampled = Signal(SourceSample)
    snkSampled = Signal(SinkSample)
    dotfMeasured = Signal(DOTFProbeDirection, np.ndarray)


class ProcessWorker(Worker):
    wid = f"{testbed.DOTF_MEASUREMENT}_worker"

    def __init__(self, source: Camera, sink: Modulator, probe_amplitude_perc: float, probe_size: tuple[int, int], probe_directions: list[DOTFProbeDirection], n_reps: int = 0):
        self.signals = ProcessWorkerSignals()
        self.source = source
        self.sink = sink
        self.probe_amplitude_perc = probe_amplitude_perc
        self.probe_size = probe_size
        self.probe_directions = probe_directions
        self.dotf_measurements = {}
        for direction in self.probe_directions:
            self.dotf_measurements[direction] = np.zeros(self.source.shape, dtype=np.complex64)
        self.n_reps = n_reps
        if self.n_reps:
            super().__init__(1 + self.n_reps * (2 * len(self.probe_directions)) + 1)  # blanks at the beginning and end
        else:
            super().__init__(0)

    def measure_dotf(self, probe_amplitude: float, probe_size: tuple[int, int], direction: DOTFProbeDirection, airy_center: tuple[float, float], airy_radius: float) -> NDArray[np.complex64]:
        zero_cmd = np.zeros(self.sink.shape)
        probe_command = probe_amplitude * dotf_probe(self.sink.shape, probe_size, direction)

        # -------------------------------------------------------------------------------------------------------------
        command_incl_probe = zero_cmd + probe_command

        incl_probe_sink_sample = self.sink.push_command(command_incl_probe)
        self.signals.snkSampled.emit(incl_probe_sink_sample)
        time.sleep(0.1)

        incl_probe_source_sample = self.source.pull_capture()
        self.signals.srcSampled.emit(incl_probe_source_sample)
        time.sleep(0.2)

        self.i_tick = self.i_tick + 1
        self.signals.progressTicked.emit(self.i_tick, time.time() - self.t_start)

        fit_center, fit_height = locate_single_airy_with_radius(incl_probe_source_sample.capture, airy_radius)
        # incl_probe_source_sample_capture = image_shift(incl_probe_source_sample.capture, shift=(airy_center[0] - fit_center[0], airy_center[1] - fit_center[1]))
        incl_probe_source_sample_capture = image_shift(incl_probe_source_sample.capture, shift=(airy_center[1] - fit_center[1], airy_center[0] - fit_center[0]))  # good
        # incl_probe_source_sample_capture = image_shift(incl_probe_source_sample.capture, shift=(fit_center[0] - airy_center[0], fit_center[1] - airy_center[1]))
        # incl_probe_source_sample_capture = image_shift(incl_probe_source_sample.capture, shift=(fit_center[1] - airy_center[1], fit_center[0] - airy_center[0]))
        # -------------------------------------------------------------------------------------------------------------

        # -------------------------------------------------------------------------------------------------------------
        command_excl_probe = zero_cmd[:]

        excl_probe_sink_sample = self.sink.push_command(command_excl_probe)
        self.signals.snkSampled.emit(excl_probe_sink_sample)
        time.sleep(0.1)

        excl_probe_source_sample = self.source.pull_capture()
        self.signals.srcSampled.emit(excl_probe_source_sample)
        time.sleep(0.2)

        self.i_tick = self.i_tick + 1
        self.signals.progressTicked.emit(self.i_tick, time.time() - self.t_start)

        fit_center, fit_height = locate_single_airy_with_radius(excl_probe_source_sample.capture, airy_radius)
        # excl_probe_source_sample_capture = image_shift(excl_probe_source_sample.capture, shift=(airy_center[0] - fit_center[0], airy_center[1] - fit_center[1]))
        excl_probe_source_sample_capture = image_shift(excl_probe_source_sample.capture, shift=(airy_center[1] - fit_center[1], airy_center[0] - fit_center[0]))  # good
        # excl_probe_source_sample_capture = image_shift(excl_probe_source_sample.capture, shift=(fit_center[0] - airy_center[0], fit_center[1] - airy_center[1]))
        # excl_probe_source_sample_capture = image_shift(excl_probe_source_sample.capture, shift=(fit_center[1] - airy_center[1], fit_center[0] - airy_center[0]))
        # -------------------------------------------------------------------------------------------------------------

        return psf_to_otf(incl_probe_source_sample_capture) - psf_to_otf(excl_probe_source_sample_capture)

    def measure_dotfs(self, probe_amplitude: float, probe_size: tuple[int, int], directions: list[DOTFProbeDirection], airy_center: tuple[float, float], airy_radius: float, n_reps: int):
        i_rep = 0
        while ((n_reps == 0) or (n_reps > i_rep)) and self._running:
            for direction in directions:
                self.dotf_measurements[direction] = self.dotf_measurements[direction] + self.measure_dotf(probe_amplitude, probe_size, direction, airy_center, airy_radius)
                self.signals.dotfMeasured.emit(direction, self.dotf_measurements[direction] / (i_rep + 1))

            i_rep = i_rep + 1

    @Slot()
    def run(self):
        super().run()

        # ---- blank --------------------------------------------------------------------------------------------------
        zero_cmd = np.zeros(self.sink.shape)

        zero_sink_sample = self.sink.push_command(zero_cmd)
        self.signals.snkSampled.emit(zero_sink_sample)
        time.sleep(0.1)

        zero_source_sample = self.source.pull_capture()
        self.signals.srcSampled.emit(zero_source_sample)
        time.sleep(0.2)

        self.i_tick: int = self.i_tick + 1
        self.signals.progressTicked.emit(self.i_tick, time.time() - self.t_start)

        guess_radius = 0.5
        fit_center, _fit_radius, _fit_height = locate_single_airy(zero_source_sample.capture, guess_radius)
        # ---- blank --------------------------------------------------------------------------------------------------

        try:
            probe_amplitude = self.sink.vrange * self.probe_amplitude_perc
            self.measure_dotfs(probe_amplitude, self.probe_size, self.probe_directions, fit_center, _fit_radius, self.n_reps)
        except AssertionError as e:
            self.signals.error.emit(str(e))

        # ---- blank --------------------------------------------------------------------------------------------------
        zero_cmd = np.zeros(self.sink.shape)

        zero_sink_sample = self.sink.push_command(zero_cmd)
        self.signals.snkSampled.emit(zero_sink_sample)
        time.sleep(0.1)

        zero_source_sample = self.source.pull_capture()
        self.signals.srcSampled.emit(zero_source_sample)
        time.sleep(0.2)

        self.i_tick = self.i_tick + 1
        self.signals.progressTicked.emit(self.i_tick, time.time() - self.t_start)
        # ---- blank --------------------------------------------------------------------------------------------------

        logger.info("dotf_measurement_worker.py - ProcessWorker() finished")
        self.stop()
        self.signals.finished.emit()
