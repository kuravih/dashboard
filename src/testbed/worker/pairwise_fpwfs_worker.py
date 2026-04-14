import time
import numpy as np
from PySide6.QtCore import Slot, Signal

from numpy.typing import NDArray
from pykato.log import setup_logger

import testbed

from ..function import pairwise_probe, PairwiseProbeDirection, pairwise_estimation_matrices, pairwise_estimate
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
    def __init__(self, source: Camera, sink: Modulator, dark_hole_mask: NDArray[np.bool], pairwise_calibration: dict[int, NDArray[np.float64]], probe_amplitude: float, probe_dξ: float, probe_dη: float, probe_ξc: float, probe_directions: list[PairwiseProbeDirection], n_reps: int):
        """
        Pairwise FPWFS Process Worker

        Parameters:
            source: Camera
                Data source

            sink: Modulator
                Data sink

            dark_hole_mask: NDArray[np.bool]
                Dark hole mask

            pairwise_calibration: dict[int, NDArray[np.float64]]
                Pairwise FPWFS Calibration

            probe_amplitude: float
                Probe amplitude

            probe_dξ: float
                Probe dξ

            probe_dη: float
                Probe dη

            probe_ξc: float
                Probe ξc

            probe_directions: list[PairwiseProbeDirection]
                Probe Direction (PairwiseProbeDirection.HORIZONTAL or PairwiseProbeDirection.VERTICAL)

            n_reps: int
                Number of reps
        """

        super().__init__()
        self.signals = ProcessWorkerSignals()
        self.source = source
        self.sink = sink
        self.dark_hole_mask = dark_hole_mask
        self.pairwise_calibration = pairwise_calibration
        self.probe_amplitude = probe_amplitude
        self.probe_dξ = probe_dξ
        self.probe_dη = probe_dη
        self.probe_ξc = probe_ξc
        self.probe_directions = probe_directions
        self.n_reps = n_reps
        self.wavefront = {}
        for direction in self.probe_directions:
            self.wavefront[direction] = np.zeros(self.source.shape, dtype=np.complex64)

    def sense_wavefront(self, current_cmd: np.ndarray, probe_amplitude: float, dξ: float, dη: float, ξc: float, direction: PairwiseProbeDirection) -> NDArray[np.complex64]:

        command_0 = np.zeros(self.sink.shape)

        _inc_probe_sink_sample = self.sink.push_command(command_0)
        self.signals.snkSampled.emit(_inc_probe_sink_sample)
        time.sleep(0.1)

        sample_0 = self.source.pull_capture()
        self.signals.srcSampled.emit(sample_0)
        time.sleep(0.2)

        # -------------------------------------------------------------------------------------------------------------
        k = 1
        command_p_h_1 = +probe_amplitude * pairwise_probe(self.sink.shape, dξ, dη, ξc, k * np.pi / 2, direction)
        command_m_h_1 = -probe_amplitude * pairwise_probe(self.sink.shape, dξ, dη, ξc, k * np.pi / 2, direction)

        k = 2
        command_p_h_2 = +probe_amplitude * pairwise_probe(self.sink.shape, dξ, dη, ξc, k * np.pi / 2, direction)
        command_m_h_2 = -probe_amplitude * pairwise_probe(self.sink.shape, dξ, dη, ξc, k * np.pi / 2, direction)
        # -------------------------------------------------------------------------------------------------------------

        _inc_probe_sink_sample = self.sink.push_command(command_p_h_1)
        self.signals.snkSampled.emit(_inc_probe_sink_sample)
        time.sleep(0.1)

        sample_p_h_1 = self.source.pull_capture()
        self.signals.srcSampled.emit(sample_p_h_1)
        time.sleep(0.2)

        _inc_probe_sink_sample = self.sink.push_command(command_m_h_1)
        self.signals.snkSampled.emit(_inc_probe_sink_sample)
        time.sleep(0.1)

        sample_m_h_1 = self.source.pull_capture()
        self.signals.srcSampled.emit(sample_m_h_1)
        time.sleep(0.2)

        _inc_probe_sink_sample = self.sink.push_command(command_p_h_2)
        self.signals.snkSampled.emit(_inc_probe_sink_sample)
        time.sleep(0.1)

        sample_p_h_2 = self.source.pull_capture()
        self.signals.srcSampled.emit(sample_p_h_2)
        time.sleep(0.2)

        _inc_probe_sink_sample = self.sink.push_command(command_m_h_2)
        self.signals.snkSampled.emit(_inc_probe_sink_sample)
        time.sleep(0.1)

        sample_m_h_2 = self.source.pull_capture()
        self.signals.srcSampled.emit(sample_m_h_2)
        time.sleep(0.2)

        Δp_h_1_mag = np.sqrt((sample_p_h_1.capture + sample_m_h_1.capture) / 2 - sample_0.capture)
        Δp_h_1 = Δp_h_1_mag * np.exp(1j * self.pairwise_calibration[1])

        Δp_h_2_mag = np.sqrt((sample_p_h_2.capture + sample_m_h_2.capture) / 2 - sample_0.capture)
        Δp_h_2 = Δp_h_2_mag * np.exp(1j * self.pairwise_calibration[2])

        electric_field_h = np.zeros_like(sample_0.capture, dtype=np.complex64)

        electric_field_h[self.dark_hole_mask] = pairwise_estimate(sample_p_h_1.capture[self.dark_hole_mask], sample_m_h_1.capture[self.dark_hole_mask], sample_p_h_2.capture[self.dark_hole_mask], sample_m_h_2.capture[self.dark_hole_mask], pairwise_estimation_matrices(Δp_h_1[self.dark_hole_mask], Δp_h_2[self.dark_hole_mask]))

        electric_field_h[self.dark_hole_mask] = sample_0.capture[self.dark_hole_mask] * np.exp(1j * np.angle(electric_field_h[self.dark_hole_mask]))

        return electric_field_h

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
                self.wavefront[direction] = self.wavefront[direction] + self.sense_wavefront(current_cmd, self.probe_amplitude, self.probe_dξ, self.probe_dη, self.probe_ξc, direction)
                self.signals.wfSensed.emit(direction, self.wavefront[direction] / (i_rep + 1))
                logger.info("%s and %s ProcessWorker.run : step %i of %i", self.source.name, self.sink.name, i_rep, self.n_reps)

            i_rep = i_rep + 1
            self.signals.progressTicked.emit(i_rep, time.time() - t_start)

        logger.info("pairwise_fpwfs_worker.py - ProcessWorker() finished")
        self.stop()
        self.signals.finished.emit()
