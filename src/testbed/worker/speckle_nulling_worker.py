import time
import numpy as np
from PySide6.QtCore import Slot, Signal

from pykato.function import sinusoid, least_squares_fit
from pykato.log import setup_logger

import testbed
from ..device import SourceSample, SinkSample
from ..device.camera import Camera
from ..device.modulator import Modulator
from . import Worker, WorkerSignals
from ..function import find_speckles, speckle_parameters, constrained_sin_fit_fn, quadratic_fit_fn

logger = setup_logger(f"{testbed.SPECKLE_NULLING}_worker", terminator="\n")


class ProcessWorkerSignals(WorkerSignals):
    srcSampled = Signal(SourceSample)
    snkSampled = Signal(SinkSample)

    speckleLocated = Signal(float, float, float, float)

    phaseSwept = Signal(np.ndarray)
    phaseFitted = Signal(float, float, float)
    phaseSolved = Signal(float)

    amplitudeSwept = Signal(np.ndarray)
    amplitudeFitted = Signal(float, float, float)
    amplitudeSolved = Signal(float)

    contrastMeasured = Signal(np.ndarray, np.ndarray)


class ProcessWorker(Worker):

    wid = f"{testbed.SPECKLE_NULLING}_worker"

    def __init__(self, source: Camera, sink: Modulator, dark_hole_mask: np.ndarray, speckle_calibration: dict[str, dict[str, float]], phase_rad_array: np.ndarray, amplitude_perc_array: np.ndarray, n_iterations: int | None = None):
        self.signals = ProcessWorkerSignals()
        self.source = source
        self.sink = sink
        self.dark_hole_mask = dark_hole_mask
        self.speckle_calibration = speckle_calibration
        self.phase_rad_array = phase_rad_array
        self.amplitude_perc_array = amplitude_perc_array
        self.n_iterations = n_iterations
        if self.n_iterations is None:
            super().__init__(None)
        else:
            super().__init__(self.n_iterations * self.phase_rad_array.size * self.amplitude_perc_array.size + 1)  # blank

    def speckle_phase_search(self, current_cmd: np.ndarray, speckle_frequency: float, phase_rad_array: np.ndarray, speckle_angle_rad: float, speckle_stencil: np.ndarray):
        speckle_intensity_array = np.zeros_like(phase_rad_array) * np.nan
        amplitude_perc = np.mean(self.amplitude_perc_array)
        amplitude = self.sink.vrange * amplitude_perc
        logger.info("speckle_phs_search : amplitude = %s", amplitude)
        i_phs = 0
        while i_phs < phase_rad_array.size:

            probe_command = amplitude * sinusoid(self.sink.shape, 1.0 / speckle_frequency, angle=speckle_angle_rad, phase=phase_rad_array[i_phs])
            # logger.info("speckle_phs_search : np.deg2rad(phs_array[%s]) = %s", i_phs, np.deg2rad(phs_array[i_phs]))
            command = current_cmd + probe_command

            _current_sink_sample = self.sink.push_command(command)
            self.signals.snkSampled.emit(_current_sink_sample)
            time.sleep(0.1)

            _current_source_sample = self.source.pull_capture()
            self.signals.srcSampled.emit(_current_source_sample)
            time.sleep(0.2)

            self.i_tick = self.i_tick + 1
            self.signals.progressTicked.emit(self.i_tick, time.time() - self.t_start)

            speckle_intensity_array[i_phs] = np.mean(_current_source_sample.capture[speckle_stencil])
            logger.info("speckle_phs_search : np.rad2deg(phs_array[%s]) = %s, speckle_intensity_array[%s] = %s", i_phs, np.rad2deg(phase_rad_array[i_phs]), i_phs, speckle_intensity_array[i_phs])
            i_phs = i_phs + 1

            self.signals.phaseSwept.emit(speckle_intensity_array)

        try:
            logger.info("speckle_phs_search: np.rad2deg(phase_rad_array) = %s", np.rad2deg(phase_rad_array))
            logger.info("speckle_phs_search: speckle_intensity_array = %s", speckle_intensity_array)

            guess_offset = np.mean(speckle_intensity_array)
            offset_min, offset_max = guess_offset * 0.5, guess_offset * 1.5
            guess_amplitude_perc = (np.max(speckle_intensity_array) - np.min(speckle_intensity_array)) / 2
            amplitude_perc_min, amplitude_perc_max = guess_amplitude_perc * 0.5, guess_amplitude_perc * 1.5
            guess_phase_rad = np.pi
            phase_rad_min, phase_rad_max = 0, 2 * np.pi
            (fit_amplitude_perc, fit_phase_rad, fit_offset), _ = least_squares_fit(speckle_intensity_array, constrained_sin_fit_fn, x_coord=phase_rad_array, guess_prms=(guess_amplitude_perc, guess_phase_rad, guess_offset), bounds=([amplitude_perc_min, phase_rad_min, offset_min], [amplitude_perc_max, phase_rad_max, offset_max]))  # pylint: disable=unbalanced-tuple-unpacking
            self.signals.phaseFitted.emit(fit_amplitude_perc, fit_phase_rad, fit_offset)
        except RuntimeError:
            logger.info("speckle_phs_search: least_squares_fit failed")
            speckle_phase_rad = 0
        else:
            speckle_phase_rad = (-np.pi / 2 - fit_phase_rad) % (2 * np.pi)

        logger.info("speckle_phs_search: np.rad2deg(speckle_phase_rad) = %f", np.rad2deg(speckle_phase_rad))

        self.signals.phaseSolved.emit(speckle_phase_rad)

        return speckle_phase_rad

    def speckle_amplitude_search(self, current_cmd: np.ndarray, speckle_frequency: float, speckle_phase_rad: float, speckle_angle_rad: float, amplitude_perc_array: np.ndarray, speckle_stencil: np.ndarray):
        speckle_intensity_array = np.zeros_like(amplitude_perc_array) * np.nan
        i_amp = 0
        while i_amp < amplitude_perc_array.size:

            probe_command = amplitude_perc_array[i_amp] * sinusoid(self.sink.shape, 1.0 / speckle_frequency, angle=speckle_angle_rad, phase=speckle_phase_rad)

            command = current_cmd + probe_command

            _current_sink_sample = self.sink.push_command(command)
            self.signals.snkSampled.emit(_current_sink_sample)
            time.sleep(0.1)

            _current_source_sample = self.source.pull_capture()
            self.signals.srcSampled.emit(_current_source_sample)
            time.sleep(0.2)

            self.i_tick = self.i_tick + 1
            self.signals.progressTicked.emit(self.i_tick, time.time() - self.t_start)

            speckle_intensity_array[i_amp] = np.mean(_current_source_sample.capture[speckle_stencil])
            logger.info("speckle_amp_search : amplitude_array[%s] = %s, speckle_intensity_array[%s] = %s", i_amp, amplitude_perc_array[i_amp], i_amp, speckle_intensity_array[i_amp])
            i_amp = i_amp + 1

            self.signals.amplitudeSwept.emit(speckle_intensity_array)

        try:
            logger.info("speckle_amp_search: amplitude_array = %s", amplitude_perc_array)
            logger.info("speckle_amp_search: speckle_intensity_array = %s", speckle_intensity_array)

            x_min, x_max = amplitude_perc_array[0], amplitude_perc_array[-1]
            x_range = x_max - x_min
            intensity_range = np.nanmax(speckle_intensity_array) - np.nanmin(speckle_intensity_array)
            a_max = 2 * intensity_range / x_range**2
            c_min, c_max = 0, np.nanmin(speckle_intensity_array)
            (fit_a, fit_x0, fit_c), _ = least_squares_fit(speckle_intensity_array, quadratic_fit_fn, x_coord=amplitude_perc_array, bounds=([0, x_min, c_min], [a_max, x_max, c_max]))  # pylint: disable=unbalanced-tuple-unpacking
            self.signals.amplitudeFitted.emit(fit_a, fit_x0, fit_c)
        except RuntimeError:
            logger.info("speckle_amp_search: least_squares_fit failed")
            speckle_amplitude_perc = amplitude_perc_array[np.argmin(speckle_intensity_array)]
        else:
            speckle_amplitude_perc = fit_x0

        logger.info("speckle_amp_search: speckle_amplitude = %f", speckle_amplitude_perc)

        self.signals.amplitudeSolved.emit(speckle_amplitude_perc)

        return speckle_amplitude_perc

    @Slot()
    def run(self):
        super().run()

        measure_array = np.full(self.n_iterations + 1, fill_value=np.nan, dtype=[("avg", float), ("std", float), ("min", float), ("max", float)])
        # ---- blank --------------------------------------------------------------------------------------------------

        #  Inject test speckle
        current_cmd = np.zeros(self.sink.shape)
        # test_amp_perc = 0.01
        # test_amplitude = test_amp_perc / 100.0
        # test_command = test_amplitude * sinusoid(self.sink.shape, 1.0 / 0.035, 0, np.pi / 6)
        # current_cmd = current_cmd + test_command

        _current_sink_sample = self.sink.push_command(current_cmd)
        self.signals.snkSampled.emit(_current_sink_sample)
        time.sleep(0.1)

        _current_source_sample = self.source.pull_capture()
        self.signals.srcSampled.emit(_current_source_sample)
        time.sleep(0.2)

        measure_map = _current_source_sample.capture / (2**16 - 1)
        measure_map_dark_hole = measure_map[self.dark_hole_mask]
        measure_array[0]["avg"], measure_array[0]["std"], measure_array[0]["min"], measure_array[0]["max"] = np.mean(measure_map_dark_hole), np.std(measure_map_dark_hole), np.min(measure_map_dark_hole), np.max(measure_map_dark_hole)
        self.signals.contrastMeasured.emit(np.array(measure_map, copy=True), measure_array)
        logger.info("avg = %.4e, std = %.4e, min = %.4e, max = %.4e", measure_array[0]["avg"], measure_array[0]["std"], measure_array[0]["min"], measure_array[0]["max"])

        i_iteration = 0
        # ---- blank --------------------------------------------------------------------------------------------------

        logger.info("%s and %s ProcessWorker.run : iteration %s of %s", self.source.name, self.sink.name, i_iteration, self.n_iterations)

        center = (self.source.shape[0] / 2, self.source.shape[1] / 2)
        while ((self.n_iterations is None) or (self.n_iterations > i_iteration)) and self._running:
            # ---- stage 0: find speckle ------------------------------------------------------------------------------
            specks, speckle_stencil = find_speckles((_current_source_sample.capture * self.dark_hole_mask).astype(float), 1, 5)
            # ---- stage 0: speckle found -----------------------------------------------------------------------------

            # ---- stage 1: calculate speckle period and angle --------------------------------------------------------
            speckle_frequency, speckle_angle_rad = speckle_parameters(center, specks[0], self.speckle_calibration)
            speckle_angle_rad = np.pi - speckle_angle_rad
            self.signals.speckleLocated.emit(*specks[0], speckle_frequency, speckle_angle_rad)
            # ---- stage 1: speckle period and angle calculated -------------------------------------------------------

            # ---- stage 2: find speckle phase ------------------------------------------------------------------------
            speckle_phase_rad = self.speckle_phase_search(_current_sink_sample.command, speckle_frequency, self.phase_rad_array, speckle_angle_rad, speckle_stencil)
            # ---- stage 2: speckle phase found -----------------------------------------------------------------------

            # ---- stage 3: find speckle amplitude --------------------------------------------------------------------
            amplitude_array = self.sink.vrange * self.amplitude_perc_array
            speckle_amplitude_perc = self.speckle_amplitude_search(_current_sink_sample.command, speckle_frequency, speckle_phase_rad, speckle_angle_rad, amplitude_array, speckle_stencil)
            # ---- stage 3: speckle amplitude found -------------------------------------------------------------------

            # ---- stage 4: apply correction --------------------------------------------------------------------------
            correction = speckle_amplitude_perc * sinusoid(self.sink.shape, 1.0 / speckle_frequency, angle=speckle_angle_rad, phase=speckle_phase_rad)
            command = _current_sink_sample.command + correction

            _current_sink_sample = self.sink.push_command(command)
            self.signals.snkSampled.emit(_current_sink_sample)
            time.sleep(0.1)

            _current_source_sample = self.source.pull_capture()
            self.signals.srcSampled.emit(_current_source_sample)
            time.sleep(0.2)

            measure_map = _current_source_sample.capture / (2**16 - 1)
            measure_map_dark_hole = measure_map[self.dark_hole_mask]
            measure_array[i_iteration + 1]["avg"], measure_array[i_iteration + 1]["std"], measure_array[i_iteration + 1]["min"], measure_array[i_iteration + 1]["max"] = np.mean(measure_map_dark_hole), np.std(measure_map_dark_hole), np.min(measure_map_dark_hole), np.max(measure_map_dark_hole)
            self.signals.contrastMeasured.emit(np.array(measure_map, copy=True), measure_array)
            # logger.info("avg = %.4e, std = %.4e, min = %.4e, max = %.4e", measure_array[i_iteration + 1]["avg"], measure_array[i_iteration + 1]["std"], measure_array[i_iteration + 1]["min"], measure_array[i_iteration + 1]["max"])
            # ---- stage 4: apply correction --------------------------------------------------------------------------
            i_iteration = i_iteration + 1

        logger.info("speckle_nulling_worker.py - ProcessWorker() finished")
        self.stop()
        self.signals.finished.emit()
