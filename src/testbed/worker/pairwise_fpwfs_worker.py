import time

import numpy as np
from numpy.typing import NDArray
from pykato.log import setup_logger
from PySide6.QtCore import Signal, Slot

import testbed

from ..device import SinkSample, SourceSample
from ..device.camera import Camera
from ..device.modulator import Modulator
from ..function import PairwiseProbeDirection, calculate_quantum_efficiency, capture_to_intensity, pairwise_estimate, pairwise_estimation_matrices, pairwise_probe
from . import Worker, WorkerSignals

logger = setup_logger(f"{testbed.PAIRWISE_FPWFS}_worker", terminator="\n")


class ProcessWorkerSignals(WorkerSignals):
    srcSampled = Signal(SourceSample)
    snkSampled = Signal(SinkSample)
    wfSensed = Signal(PairwiseProbeDirection, np.ndarray)


class ProcessWorker(Worker):
    wid = f"{testbed.PAIRWISE_FPWFS}_worker"

    _allowed_slots_ = Worker._allowed_slots_ | {"signals", "source", "sink", "camera_calibration", "star_brightness_model", "star_brightness_experiment", "qe_perc", "probe_amplitude_perc", "dark_hole_mask", "iCAψ", "probe_dξ", "probe_dη", "probe_ξc", "probe_directions", "wavefront", "n_reps"}

    def __init__(self, source: Camera, sink: Modulator, dark_hole_mask: NDArray[np.bool], star_brightness_model: float, star_brightness_experiment: dict[str, float], camera_calibration: dict[str, np.ndarray | float | int], pairwise_calibration: tuple[NDArray[np.complex128], dict[int, NDArray[np.complex128]], float, float, float, float], probe_amplitude_perc: float, probe_dξ: float, probe_dη: float, probe_ξc: float, probe_directions: list[PairwiseProbeDirection], n_reps: int):
        self.signals = ProcessWorkerSignals()
        self.source = source
        self.sink = sink
        self.star_brightness_model = star_brightness_model
        self.star_brightness_experiment = star_brightness_experiment
        self.camera_calibration = camera_calibration
        self.qe_perc = calculate_quantum_efficiency(633.0, *self.camera_calibration["quantum_efficiency"])
        self.probe_amplitude_perc = probe_amplitude_perc
        self.dark_hole_mask = dark_hole_mask
        self.iCAψ = pairwise_calibration
        self.probe_dξ = probe_dξ
        self.probe_dη = probe_dη
        self.probe_ξc = probe_ξc
        self.probe_directions = probe_directions
        self.wavefront = {}
        for direction in self.probe_directions:
            self.wavefront[direction] = np.zeros(self.source.shape, dtype=np.complex128)
        self.n_reps = n_reps
        if self.n_reps:
            super().__init__(self.n_reps * (5 * len(self.probe_directions)) + 1)  # blank at the end
        else:
            super().__init__(0)

    def sense_wavefront(self, iCAψ: dict[int, NDArray[np.complex128]], probe_amplitude: float, dξ: float, dη: float, ξc: float, direction: PairwiseProbeDirection) -> NDArray[np.complex128]:
        iCAψ1, iCAψ2 = iCAψ[1], iCAψ[2]

        # -------------------------------------------------------------------------------------------------------------
        zero_cmd = np.zeros(self.sink.shape)

        k = 1
        probe_p1 = zero_cmd + probe_amplitude * pairwise_probe(self.sink.shape, dξ, dη, ξc, k * np.pi / 2, direction)
        probe_m1 = zero_cmd - probe_amplitude * pairwise_probe(self.sink.shape, dξ, dη, ξc, k * np.pi / 2, direction)

        k = 2
        probe_p2 = zero_cmd + probe_amplitude * pairwise_probe(self.sink.shape, dξ, dη, ξc, k * np.pi / 2, direction)
        probe_m2 = zero_cmd - probe_amplitude * pairwise_probe(self.sink.shape, dξ, dη, ξc, k * np.pi / 2, direction)
        # -------------------------------------------------------------------------------------------------------------

        # ---- probe_p1 -----------------------------------------------------------------------------------------------
        probe_p1_sink_sample = self.sink.push_command(probe_p1)
        self.signals.snkSampled.emit(probe_p1_sink_sample)
        time.sleep(0.1)

        probe_p1_source_sample = self.source.pull_capture()
        self.signals.srcSampled.emit(probe_p1_source_sample)
        time.sleep(0.2)

        probe_p1_intensity = capture_to_intensity(probe_p1_source_sample.capture, probe_p1_source_sample.exposure_time_s, dark_rate=self.camera_calibration["dark_rate"], bias=self.camera_calibration["bias"], qe=self.qe_perc / 100.0, gain=self.camera_calibration["gain"])

        self.i_tick = self.i_tick + 1
        self.signals.progressTicked.emit(self.i_tick, time.time() - self.t_start)
        # ---- probe_p1 -----------------------------------------------------------------------------------------------

        # ---- probe_m1 -----------------------------------------------------------------------------------------------
        probe_m1_sink_sample = self.sink.push_command(probe_m1)
        self.signals.snkSampled.emit(probe_m1_sink_sample)
        time.sleep(0.1)

        probe_m1_source_sample = self.source.pull_capture()
        self.signals.srcSampled.emit(probe_m1_source_sample)
        time.sleep(0.2)

        probe_m1_intensity = capture_to_intensity(probe_m1_source_sample.capture, probe_m1_source_sample.exposure_time_s, dark_rate=self.camera_calibration["dark_rate"], bias=self.camera_calibration["bias"], qe=self.qe_perc / 100.0, gain=self.camera_calibration["gain"])

        self.i_tick = self.i_tick + 1
        self.signals.progressTicked.emit(self.i_tick, time.time() - self.t_start)
        # ---- probe_m1 -----------------------------------------------------------------------------------------------

        # ---- probe_p2 -----------------------------------------------------------------------------------------------
        probe_p2_sink_sample = self.sink.push_command(probe_p2)
        self.signals.snkSampled.emit(probe_p2_sink_sample)
        time.sleep(0.1)

        probe_p2_source_sample = self.source.pull_capture()
        self.signals.srcSampled.emit(probe_p2_source_sample)
        time.sleep(0.2)

        probe_p2_intensity = capture_to_intensity(probe_p2_source_sample.capture, probe_p2_source_sample.exposure_time_s, dark_rate=self.camera_calibration["dark_rate"], bias=self.camera_calibration["bias"], qe=self.qe_perc / 100.0, gain=self.camera_calibration["gain"])

        self.i_tick = self.i_tick + 1
        self.signals.progressTicked.emit(self.i_tick, time.time() - self.t_start)
        # ---- probe_p2 -----------------------------------------------------------------------------------------------

        # ---- probe_m2 -----------------------------------------------------------------------------------------------
        probe_m2_sink_sample = self.sink.push_command(probe_m2)
        self.signals.snkSampled.emit(probe_m2_sink_sample)
        time.sleep(0.1)

        probe_m2_source_sample = self.source.pull_capture()
        self.signals.srcSampled.emit(probe_m2_source_sample)
        time.sleep(0.2)

        probe_m2_intensity = capture_to_intensity(probe_m2_source_sample.capture, probe_m2_source_sample.exposure_time_s, dark_rate=self.camera_calibration["dark_rate"], bias=self.camera_calibration["bias"], qe=self.qe_perc / 100.0, gain=self.camera_calibration["gain"])

        self.i_tick = self.i_tick + 1
        self.signals.progressTicked.emit(self.i_tick, time.time() - self.t_start)
        # ---- probe_m2 -----------------------------------------------------------------------------------------------

        electric_field = np.zeros_like(probe_p1_source_sample.capture, dtype=np.complex128)

        electric_field[self.dark_hole_mask] = np.sqrt(self.star_brightness_model / self.star_brightness_experiment) * pairwise_estimate(probe_p1_intensity[self.dark_hole_mask], probe_m1_intensity[self.dark_hole_mask], probe_p2_intensity[self.dark_hole_mask], probe_m2_intensity[self.dark_hole_mask], pairwise_estimation_matrices(iCAψ1[self.dark_hole_mask], iCAψ2[self.dark_hole_mask]))

        return electric_field

    def sense_wavefronts(self, iCAψ: dict[int, NDArray[np.complex128]], probe_amplitude: float, dξ: float, dη: float, ξc: float, directions: list[PairwiseProbeDirection], n_reps: int):
        i_rep = 0
        while ((n_reps == 0) or (n_reps > i_rep)) and self._running:
            for direction in directions:
                self.wavefront[direction] = self.wavefront[direction] + self.sense_wavefront(iCAψ, probe_amplitude, dξ, dη, ξc, direction)
                self.signals.wfSensed.emit(direction, self.wavefront[direction] / (i_rep + 1))

            i_rep = i_rep + 1

    @Slot()
    def run(self):
        super().run()

        try:
            probe_amplitude = self.sink.vrange * self.probe_amplitude_perc
            self.sense_wavefronts(self.iCAψ, probe_amplitude, self.probe_dξ, self.probe_dη, self.probe_ξc, self.probe_directions, self.n_reps)
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
