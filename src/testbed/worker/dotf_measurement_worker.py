import time
import numpy as np
from PySide6.QtCore import Slot, Signal

from numpy.typing import NDArray
from pykato.log import setup_logger

import testbed

from ..function import dotf_probe, DOTFProbeDirection
from ..device import SourceSample, SinkSample
from ..device.camera import Camera
from ..device.modulator import Modulator
from . import Worker, WorkerSignals
from pykato.function import psf_to_otf

_PROCESS_ = testbed.DOTF_MEASUREMENT

logger = setup_logger(f"{_PROCESS_}_worker", terminator="\n")


class ProcessWorkerSignals(WorkerSignals):
    srcSampled = Signal(SourceSample)
    snkSampled = Signal(SinkSample)
    dotfMeasured = Signal(DOTFProbeDirection, np.ndarray)


class ProcessWorker(Worker):
    def __init__(self, source: Camera, sink: Modulator, probe_amplitude: float, probe_size: tuple[int, int], probe_directions: list[DOTFProbeDirection], n_reps: int = 0):
        self.signals = ProcessWorkerSignals()
        self.source = source
        self.sink = sink
        self.probe_amplitude = probe_amplitude
        self.probe_size = probe_size
        self.probe_directions = probe_directions
        self.dotf_measurements = {}
        for direction in self.probe_directions:
            self.dotf_measurements[direction] = np.zeros(self.source.shape, dtype=np.complex64)
        self.n_reps = n_reps
        if self.n_reps:
            super().__init__(self.n_reps * len(self.probe_directions) + 1)  # blank at the end
        else:
            super().__init__(0)

    def measure_dotf(self, probe_amplitude: float, probe_size: tuple[int, int], direction: DOTFProbeDirection) -> NDArray[np.complex64]:
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
        # -------------------------------------------------------------------------------------------------------------

        # -------------------------------------------------------------------------------------------------------------
        command_excl_probe = zero_cmd[:]

        excl_probe_sink_sample = self.sink.push_command(command_excl_probe)
        self.signals.snkSampled.emit(excl_probe_sink_sample)
        time.sleep(0.1)

        excl_probe_source_sample = self.source.pull_capture()
        self.signals.srcSampled.emit(excl_probe_source_sample)
        time.sleep(0.2)
        # -------------------------------------------------------------------------------------------------------------

        return psf_to_otf(incl_probe_source_sample.capture) - psf_to_otf(excl_probe_source_sample.capture)

    def measure_dotfs(self, amplitude: float, probe_size: tuple[int, int], directions:list[DOTFProbeDirection], n_reps: int):
        i_rep = 0
        while ((n_reps is 0) or (n_reps > i_rep)) and self._running:
            for direction in directions:
                self.dotf_measurements[direction] = self.dotf_measurements[direction] + self.measure_dotf(amplitude, probe_size, direction)
                self.signals.dotfMeasured.emit(direction, self.dotf_measurements[direction] / (i_rep + 1))

            i_rep = i_rep + 1

            self.i_tick = self.i_tick + 1
            self.signals.progressTicked.emit(self.i_tick, time.time() - self.t_start)

    @Slot()
    def run(self):
        super().run()

        try:
            self.measure_dotfs(self.probe_amplitude, self.probe_size, self.probe_directions, self.n_reps)
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
