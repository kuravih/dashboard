import time
import numpy as np
from PySide6.QtCore import Slot, Signal

from numpy.typing import NDArray
from pykato.log import setup_logger

import testbed

from ..function import pairwise_probe, PairwiseProbeDirection
from ..device import SourceSample, SinkSample
from ..device.camera import Camera
from ..device.modulator import Modulator
from . import Worker, WorkerSignals

_PROCESS_ = testbed.PAIRWISE_FPWFS

logger = setup_logger(f"{_PROCESS_}_worker", terminator="\n")


class ProcessWorkerSignals(WorkerSignals):
    srcSampled = Signal(SourceSample)
    snkSampled = Signal(SinkSample)
    wfSensed = Signal(PairwiseProbeDirection, np.ndarray)


class ProcessWorker(Worker):
    def __init__(self, source: Camera, sink: Modulator, probe_amplitude: float, probe_dξ: float, probe_dη: float, probe_ξc: float, probe_directions: list[PairwiseProbeDirection], n_reps: int):
        super().__init__()
        self.signals = ProcessWorkerSignals()
        self.source = source
        self.sink = sink
        self.probe_amplitude = probe_amplitude
        self.probe_dξ = probe_dξ
        self.probe_dη = probe_dη
        self.probe_ξc = probe_ξc
        self.probe_directions = probe_directions
        self.n_reps = n_reps
        self.wavefront = np.zeros(self.source.shape, dtype=np.complex64)

    def sense_wavefront(self, current_cmd: np.ndarray, probe_amplitude: float, dξ: float, dη: float, ξc: float, θ: float, direction: PairwiseProbeDirection) -> NDArray[np.complex64]:

        probe_command = probe_amplitude * self.sink.pxmax * pairwise_probe(self.sink.shape, dξ, dη, ξc, θ, direction)

        # -------------------------------------------------------------------------------------------------------------

        command_inc_probe = current_cmd + probe_command
        command_inc_probe = np.clip(command_inc_probe, 0, self.sink.pxmax)

        _inc_probe_sink_sample = self.sink.push_command(command_inc_probe.astype(np.uint16))
        self.signals.snkSampled.emit(_inc_probe_sink_sample)
        time.sleep(0.1)

        _inc_probe_source_sample = self.source.pull_capture()
        self.signals.srcSampled.emit(_inc_probe_source_sample)
        time.sleep(0.2)

        # -------------------------------------------------------------------------------------------------------------

        command_exc_probe = current_cmd[:]
        command_exc_probe = np.clip(command_exc_probe, 0, self.sink.pxmax)

        _exc_probe_sink_sample = self.sink.push_command(command_exc_probe.astype(np.uint16))
        self.signals.snkSampled.emit(_exc_probe_sink_sample)
        time.sleep(0.1)

        _exc_probe_source_sample = self.source.pull_capture()
        self.signals.srcSampled.emit(_exc_probe_source_sample)
        time.sleep(0.2)

        # -------------------------------------------------------------------------------------------------------------

        return psf_to_otf(_inc_probe_source_sample.capture) - psf_to_otf(_exc_probe_source_sample.capture)

    @Slot()
    def run(self):
        super().run()
        t_start = time.time()

        # ---- blank --------------------------------------------------------------------------------------------------
        current_cmd = self.sink.pxmax * (np.zeros(self.sink.shape) + 0.5)

        command = current_cmd
        command = np.clip(command, 0, self.sink.pxmax)

        _current_sink_sample = self.sink.push_command(command.astype(np.uint16))
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
            for i_dir, direction in enumerate(self.probe_directions):
                self.dotf_measurements[direction] = self.dotf_measurements[direction] + self.sense_wavefront(current_cmd, self.probe_amplitude, self.probe_size, direction)
                self.signals.wfSensed.emit(direction, self.dotf_measurements[direction] / i_rep)

            logger.info("%s and %s ProcessWorker.run : step %i of %i", self.source.name, self.sink.name, i_rep, self.n_reps)

            i_rep = i_rep + 1
            self.signals.progressTicked.emit(i_rep, time.time() - t_start)

        self.signals.finished.emit()
