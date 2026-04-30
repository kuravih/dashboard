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

logger = setup_logger(f"{testbed.PAIRWISE_FPWFS}_worker", terminator="\n")


class ProcessWorkerSignals(WorkerSignals):
    srcSampled = Signal(SourceSample)
    snkSampled = Signal(SinkSample)
    wfSensed = Signal(PairwiseProbeDirection, np.ndarray)


class ProcessWorker(Worker):

    wid = f"{testbed.PAIRWISE_FPWFS}_worker"

    def __init__(self, source: Camera, sink: Modulator, dark_hole_mask: NDArray[np.bool], pairwise_calibration: dict[int, NDArray[np.float64]], probe_amplitude_nm: float, probe_dξ: float, probe_dη: float, probe_ξc: float, probe_directions: list[PairwiseProbeDirection], n_reps: int):
        self.signals = ProcessWorkerSignals()
        self.source = source
        self.sink = sink
        self.dark_hole_mask = dark_hole_mask
        self.pairwise_calibration = pairwise_calibration
        self.probe_amplitude_nm = probe_amplitude_nm
        self.probe_dξ = probe_dξ
        self.probe_dη = probe_dη
        self.probe_ξc = probe_ξc
        self.probe_directions = probe_directions
        self.wavefront = {}
        for direction in self.probe_directions:
            self.wavefront[direction] = np.zeros(self.source.shape, dtype=np.complex64)
        self.n_reps = n_reps
        if self.n_reps:
            super().__init__(self.n_reps * (5 * len(self.probe_directions)) + 1)  # blank at the end
        else:
            super().__init__(0)

    def sense_wavefront(self, probe_amplitude_nm: float, dξ: float, dη: float, ξc: float, direction: PairwiseProbeDirection) -> NDArray[np.complex64]:
        # -------------------------------------------------------------------------------------------------------------
        zero_cmd = np.zeros(self.sink.shape)

        zero_sink_sample = self.sink.push_command(zero_cmd)
        self.signals.snkSampled.emit(zero_sink_sample)
        time.sleep(0.1)

        zero_source_sample = self.source.pull_capture()
        self.signals.srcSampled.emit(zero_source_sample)
        time.sleep(0.2)

        self.i_tick = self.i_tick + 1
        self.signals.progressTicked.emit(self.i_tick, time.time() - self.t_start)
        # -------------------------------------------------------------------------------------------------------------

        # -------------------------------------------------------------------------------------------------------------
        k = 1
        probe_p_h_1 = +probe_amplitude_nm * pairwise_probe(self.sink.shape, dξ, dη, ξc, k * np.pi / 2, direction)
        probe_m_h_1 = -probe_amplitude_nm * pairwise_probe(self.sink.shape, dξ, dη, ξc, k * np.pi / 2, direction)

        k = 2
        probe_p_h_2 = +probe_amplitude_nm * pairwise_probe(self.sink.shape, dξ, dη, ξc, k * np.pi / 2, direction)
        probe_m_h_2 = -probe_amplitude_nm * pairwise_probe(self.sink.shape, dξ, dη, ξc, k * np.pi / 2, direction)
        # -------------------------------------------------------------------------------------------------------------

        # ---- probe_p_h_1 --------------------------------------------------------------------------------------------
        probe_p_h_1_sink_sample = self.sink.push_command(probe_p_h_1)
        self.signals.snkSampled.emit(probe_p_h_1_sink_sample)
        time.sleep(0.1)

        probe_p_h_1_source_sample = self.source.pull_capture()
        self.signals.srcSampled.emit(probe_p_h_1_source_sample)
        time.sleep(0.2)

        self.i_tick = self.i_tick + 1
        self.signals.progressTicked.emit(self.i_tick, time.time() - self.t_start)
        # ---- probe_p_h_1 --------------------------------------------------------------------------------------------

        # ---- probe_m_h_1 --------------------------------------------------------------------------------------------
        probe_m_h_1_sink_sample = self.sink.push_command(probe_m_h_1)
        self.signals.snkSampled.emit(probe_m_h_1_sink_sample)
        time.sleep(0.1)

        probe_m_h_1_source_sample = self.source.pull_capture()
        self.signals.srcSampled.emit(probe_m_h_1_source_sample)
        time.sleep(0.2)

        self.i_tick = self.i_tick + 1
        self.signals.progressTicked.emit(self.i_tick, time.time() - self.t_start)
        # ---- probe_m_h_1 --------------------------------------------------------------------------------------------

        # ---- probe_p_h_2 --------------------------------------------------------------------------------------------
        probe_p_h_2_sink_sample = self.sink.push_command(probe_p_h_2)
        self.signals.snkSampled.emit(probe_p_h_2_sink_sample)
        time.sleep(0.1)

        probe_p_h_2_source_sample = self.source.pull_capture()
        self.signals.srcSampled.emit(probe_p_h_2_source_sample)
        time.sleep(0.2)

        self.i_tick = self.i_tick + 1
        self.signals.progressTicked.emit(self.i_tick, time.time() - self.t_start)
        # ---- probe_p_h_2 --------------------------------------------------------------------------------------------

        # ---- probe_m_h_2 --------------------------------------------------------------------------------------------
        probe_m_h_2_sink_sample = self.sink.push_command(probe_m_h_2)
        self.signals.snkSampled.emit(probe_m_h_2_sink_sample)
        time.sleep(0.1)

        probe_m_h_2_source_sample = self.source.pull_capture()
        self.signals.srcSampled.emit(probe_m_h_2_source_sample)
        time.sleep(0.2)

        self.i_tick = self.i_tick + 1
        self.signals.progressTicked.emit(self.i_tick, time.time() - self.t_start)
        # ---- probe_m_h_2 --------------------------------------------------------------------------------------------

        Δp_h_1_mag = np.sqrt(np.clip((probe_p_h_1_source_sample.capture + probe_m_h_1_source_sample.capture) / 2 - zero_source_sample.capture, min=0))
        Δp_h_1 = Δp_h_1_mag * np.exp(1j * self.pairwise_calibration[1])

        Δp_h_2_mag = np.sqrt(np.clip((probe_p_h_2_source_sample.capture + probe_m_h_2_source_sample.capture) / 2 - zero_source_sample.capture, min=0))
        Δp_h_2 = Δp_h_2_mag * np.exp(1j * self.pairwise_calibration[2])

        electric_field_h = np.zeros_like(zero_source_sample.capture, dtype=np.complex64)

        electric_field_h[self.dark_hole_mask] = pairwise_estimate(probe_p_h_1_source_sample.capture[self.dark_hole_mask], probe_m_h_1_source_sample.capture[self.dark_hole_mask], probe_p_h_2_source_sample.capture[self.dark_hole_mask], probe_m_h_2_source_sample.capture[self.dark_hole_mask], pairwise_estimation_matrices(Δp_h_1[self.dark_hole_mask], Δp_h_2[self.dark_hole_mask]))

        electric_field_h[self.dark_hole_mask] = zero_source_sample.capture[self.dark_hole_mask] * np.exp(1j * np.angle(electric_field_h[self.dark_hole_mask]))

        return electric_field_h

    def sense_wavefronts(self, probe_amplitude_nm: float, dξ: float, dη: float, ξc: float, directions: list[PairwiseProbeDirection], n_reps: int):
        i_rep = 0
        while ((n_reps is 0) or (n_reps > i_rep)) and self._running:
            for direction in directions:
                self.wavefront[direction] = self.wavefront[direction] + self.sense_wavefront(probe_amplitude_nm, dξ, dη, ξc, direction)
                self.signals.wfSensed.emit(direction, self.wavefront[direction] / (i_rep + 1))

            i_rep = i_rep + 1

    @Slot()
    def run(self):
        super().run()

        try:
            self.sense_wavefronts(self.probe_amplitude_nm, self.probe_dξ, self.probe_dη, self.probe_ξc, self.probe_directions, self.n_reps)
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

        logger.info("pairwise_fpwfs_worker.py - ProcessWorker() finished")
        self.stop()
        self.signals.finished.emit()
