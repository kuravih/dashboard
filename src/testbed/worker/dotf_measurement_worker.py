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
    def __init__(self, source: Camera, sink: Modulator, probe_amplitude: float, probe_size: tuple[int, int], probe_directions: list[DOTFProbeDirection], n_reps: int):
        super().__init__()
        self.signals = ProcessWorkerSignals()
        self.source = source
        self.sink = sink
        self.probe_amplitude = probe_amplitude
        self.probe_size = probe_size
        self.probe_directions = probe_directions
        self.n_reps = n_reps
        self.dotf_measurements = {}
        for direction in self.probe_directions:
            self.dotf_measurements[direction] = np.zeros(self.source.shape, dtype=np.complex64)

    def measure_dotf(self, current_cmd: np.ndarray, probe_amplitude: float, probe_size: tuple[int, int], direction: DOTFProbeDirection) -> NDArray[np.complex64]:

        probe_command = probe_amplitude * dotf_probe(self.sink.shape, probe_size, direction)

        # -------------------------------------------------------------------------------------------------------------

        command_incl_probe = current_cmd + probe_command

        _incl_probe_sink_sample = self.sink.push_command(command_incl_probe)
        self.signals.snkSampled.emit(_incl_probe_sink_sample)
        time.sleep(0.1)

        _incl_probe_source_sample = self.source.pull_capture()
        self.signals.srcSampled.emit(_incl_probe_source_sample)
        time.sleep(0.2)

        # -------------------------------------------------------------------------------------------------------------

        command_excl_probe = current_cmd[:]

        _excl_probe_sink_sample = self.sink.push_command(command_excl_probe)
        self.signals.snkSampled.emit(_excl_probe_sink_sample)
        time.sleep(0.1)

        _excl_probe_source_sample = self.source.pull_capture()
        self.signals.srcSampled.emit(_excl_probe_source_sample)
        time.sleep(0.2)

        # -------------------------------------------------------------------------------------------------------------

        return psf_to_otf(_incl_probe_source_sample.capture) - psf_to_otf(_excl_probe_source_sample.capture)

    @Slot()
    def run(self):
        super().run()
        t_start = time.time()

        # ---- blank --------------------------------------------------------------------------------------------------
        current_cmd = np.zeros(self.sink.shape)

        _current_sink_sample = self.sink.push_command(current_cmd)
        self.signals.snkSampled.emit(_current_sink_sample)
        time.sleep(0.1)

        _current_source_sample = self.source.pull_capture()
        self.signals.srcSampled.emit(_current_source_sample)
        time.sleep(0.2)

        i_rep = 0
        self.signals.progressTicked.emit(i_rep, time.time() - t_start)
        # ---- blank --------------------------------------------------------------------------------------------------

        logger.info("%s and %s ProcessWorker.run : step %i of %i", self.source.name, self.sink.name, i_rep, self.n_reps)

        while ((self.n_reps is None) or (self.n_reps > i_rep)) and self._running:
            for direction in self.probe_directions:
                self.dotf_measurements[direction] = self.dotf_measurements[direction] + self.measure_dotf(current_cmd, self.probe_amplitude, self.probe_size, direction)
                self.signals.dotfMeasured.emit(direction, self.dotf_measurements[direction] / (i_rep + 1))
                logger.info("%s and %s ProcessWorker.run : step %i of %i, %i", self.source.name, self.sink.name, i_rep, self.n_reps, direction)

            i_rep = i_rep + 1
            self.signals.progressTicked.emit(i_rep, time.time() - t_start)

        logger.info("dotf_measurement_worker.py - ProcessWorker() finished")
        self.stop()
        self.signals.finished.emit()
