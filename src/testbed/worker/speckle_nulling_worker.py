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

_PROCESS_ = testbed.SPECKLE_NULLING

logger = setup_logger(f"{_PROCESS_}_worker", terminator="\n")


class ProcessWorkerSignals(WorkerSignals):
    srcSampled = Signal(SourceSample)
    snkSampled = Signal(SinkSample)

    speckleLocated = Signal(float, float, float, float)

    phsSwept = Signal(np.ndarray)
    phsFitted = Signal(float, float, float)
    phsSolved = Signal(float)

    ampSwept = Signal(np.ndarray)
    ampFitted = Signal(float, float, float)
    ampSolved = Signal(float)

    contrastMeasured = Signal(np.ndarray, np.ndarray)


class ProcessWorker(Worker):
    def __init__(self, source: Camera, sink: Modulator, dark_hole_mask: np.ndarray, speckle_calibration: tuple[tuple[float, float], tuple[float, float]], phs_array: np.ndarray, amp_array: np.ndarray, n_iterations: int | None = None):
        super().__init__()
        self.signals = ProcessWorkerSignals()
        self._source = source
        self._sink = sink
        self._dark_hole_mask = dark_hole_mask
        self._speckle_calibration = speckle_calibration
        self._phs_array = phs_array
        self._amp_array = amp_array
        self._n_iterations = n_iterations

    def speckle_phs_search(self, current_cmd: np.ndarray, speckle_frequency: float, phs_array: np.ndarray, speckle_angle: float, speckle_stencil: np.ndarray):
        speckle_intensity = np.zeros_like(phs_array) * np.nan
        amplitude = 0.5
        i_phs = 0
        while i_phs < phs_array.size:
            probe_command = amplitude * self._sink.pxmax * sinusoid(self._sink.shape, 1.0 / speckle_frequency, np.deg2rad(phs_array[i_phs]), speckle_angle) / 2
            command = current_cmd + probe_command
            command = np.clip(command, 0, self._sink.pxmax)

            _current_sink_sample = self._sink.push_command(command.astype(np.uint16))
            self.signals.snkSampled.emit(_current_sink_sample)
            time.sleep(0.1)

            _current_source_sample = self._source.pull_capture()
            self.signals.srcSampled.emit(_current_source_sample)
            time.sleep(0.2)

            speckle_intensity[i_phs] = np.mean(_current_source_sample.capture[speckle_stencil])
            i_phs = i_phs + 1

            self.signals.phsSwept.emit(speckle_intensity)

        try:
            guess_offset = np.mean(speckle_intensity)
            offset_min, offset_max = guess_offset * 0.5, guess_offset * 1.5
            guess_amplitude = (np.max(speckle_intensity) - np.min(speckle_intensity)) / 2
            amplitude_min, amplitude_max = guess_amplitude * 0.5, guess_amplitude * 1.5
            guess_phase = np.pi
            phase_min, phase_max = 0, 2 * np.pi
            (fit_amplitude, fit_phase, fit_offset), _ = least_squares_fit(speckle_intensity, constrained_sin_fit_fn, x_coord=np.deg2rad(phs_array), guess_prms=(guess_amplitude, guess_phase, guess_offset), bounds=([amplitude_min, phase_min, offset_min], [amplitude_max, phase_max, offset_max]))  # pylint: disable=unbalanced-tuple-unpacking
            self.signals.phsFitted.emit(fit_amplitude, fit_phase, fit_offset)
        except RuntimeError:
            logger.info("speckle_phs_search: least_squares_fit failed")
            speckle_phase = 0
        else:
            speckle_phase = (-np.pi / 2 - fit_phase) % (2 * np.pi)

        # logger.info("speckle_phs_search: speckle_phase = %f", np.rad2deg(speckle_phase))

        self.signals.phsSolved.emit(speckle_phase)

        return speckle_phase

    def speckle_amp_search(self, current_cmd: np.ndarray, speckle_frequency: float, speckle_phase: float, speckle_angle: float, amp_array: np.ndarray, speckle_stencil: np.ndarray):
        speckle_intensity = np.zeros_like(amp_array) * np.nan
        i_amp = 0
        while i_amp < amp_array.size:
            probe_command = amp_array[i_amp] * self._sink.pxmax * sinusoid(self._sink.shape, 1.0 / speckle_frequency, speckle_phase, speckle_angle) / 2
            command = current_cmd + probe_command
            command = np.clip(command, 0, self._sink.pxmax)

            _current_sink_sample = self._sink.push_command(command.astype(np.uint16))
            self.signals.snkSampled.emit(_current_sink_sample)
            time.sleep(0.1)

            _current_source_sample = self._source.pull_capture()
            self.signals.srcSampled.emit(_current_source_sample)
            time.sleep(0.2)

            speckle_intensity[i_amp] = np.mean(_current_source_sample.capture[speckle_stencil])
            i_amp = i_amp + 1

            self.signals.ampSwept.emit(speckle_intensity)

        try:
            (fit_a, fit_b, fit_c), _ = least_squares_fit(speckle_intensity, quadratic_fit_fn, x_coord=amp_array, bounds=([0, -np.inf, -np.inf], [np.inf, 0, np.inf]))  # pylint: disable=unbalanced-tuple-unpacking
            self.signals.ampFitted.emit(fit_a, fit_b, fit_c)
        except RuntimeError:
            logger.info("speckle_amp_search: least_squares_fit failed")
            speckle_amplitude = amp_array[np.argmin(speckle_intensity)]
        else:
            speckle_amplitude = -fit_b / (2 * fit_a)

        # logger.info("speckle_amp_search: speckle_amplitude = %f", speckle_amplitude)

        self.signals.ampSolved.emit(speckle_amplitude)

        return speckle_amplitude

    @Slot()
    def run(self):
        super().run()
        t_start = time.time()

        measure_array = np.full(self._n_iterations + 1, fill_value=np.nan, dtype=[("avg", float), ("std", float), ("min", float), ("max", float)])
        # ---- blank --------------------------------------------------------------------------------------------------
        current_cmd = self._sink.pxmax * (np.zeros(self._sink.shape) + 0.5)

        #  Inject test speckle
        test_command = 0.1 * self._sink.pxmax * sinusoid(self._sink.shape, 1.0 / 0.035, 0, np.pi / 6) / 2
        command = current_cmd + test_command
        command = np.clip(command, 0, self._sink.pxmax)

        _current_sink_sample = self._sink.push_command(command.astype(np.uint16))
        self.signals.snkSampled.emit(_current_sink_sample)
        time.sleep(0.1)

        _current_source_sample = self._source.pull_capture()
        self.signals.srcSampled.emit(_current_source_sample)
        time.sleep(0.2)

        measure_map = _current_source_sample.capture / (2**12 - 1)
        mesure_map_dark_hole = measure_map[self._dark_hole_mask]
        measure_array[0]["avg"], measure_array[0]["std"], measure_array[0]["min"], measure_array[0]["max"] = np.mean(mesure_map_dark_hole), np.std(mesure_map_dark_hole), np.min(mesure_map_dark_hole), np.max(mesure_map_dark_hole)
        self.signals.contrastMeasured.emit(np.array(measure_map, copy=True), measure_array)
        logger.info("avg = %.4e, std = %.4e, min = %.4e, max = %.4e", measure_array[0]["avg"], measure_array[0]["std"], measure_array[0]["min"], measure_array[0]["max"])

        i_iteration = 0
        self.signals.progressTicked.emit(i_iteration, time.time() - t_start)
        # ---- blank --------------------------------------------------------------------------------------------------

        logger.info("%s and %s ProcessWorker.run : iteration %s of %s", self._source.name, self._sink.name, i_iteration, self._n_iterations)

        center = (self._source.shape[0] / 2, self._source.shape[1] / 2)
        while ((self._n_iterations is None) or (self._n_iterations > i_iteration)) and self._running:
            # ---- stage 0: find speckle ------------------------------------------------------------------------------
            specks, speckle_stencil = find_speckles((_current_source_sample.capture * self._dark_hole_mask).astype(float), 1, 5)
            # ---- stage 0: speckle found -----------------------------------------------------------------------------

            # ---- stage 1: calculate speckle period and angle --------------------------------------------------------
            speckle_frequency, speckle_angle = speckle_parameters(center, specks[0], self._speckle_calibration)
            speckle_angle = np.pi - speckle_angle
            self.signals.speckleLocated.emit(*specks[0], speckle_frequency, speckle_angle)
            # ---- stage 1: speckle period and angle calculated -------------------------------------------------------

            # ---- stage 2: find speckle phase ------------------------------------------------------------------------
            speckle_phase = self.speckle_phs_search(_current_sink_sample.command, speckle_frequency, self._phs_array, speckle_angle, speckle_stencil)
            # ---- stage 2: speckle phase found -----------------------------------------------------------------------

            # ---- stage 3: find speckle amplitude --------------------------------------------------------------------
            speckle_amplitude = self.speckle_amp_search(_current_sink_sample.command, speckle_frequency, speckle_phase, speckle_angle, self._amp_array, speckle_stencil)
            # ---- stage 3: speckle amplitude found -------------------------------------------------------------------

            # ---- stage 4: apply correction --------------------------------------------------------------------------
            correction = speckle_amplitude * self._sink.pxmax * sinusoid(self._sink.shape, 1.0 / speckle_frequency, speckle_phase, speckle_angle) / 2
            command = _current_sink_sample.command + correction
            command = np.clip(command, 0, self._sink.pxmax)

            _current_sink_sample = self._sink.push_command(command.astype(np.uint16))
            self.signals.snkSampled.emit(_current_sink_sample)
            time.sleep(0.1)

            _current_source_sample = self._source.pull_capture()
            self.signals.srcSampled.emit(_current_source_sample)
            time.sleep(0.2)

            measure_map = _current_source_sample.capture / (2**12 - 1)
            mesure_map_dark_hole = measure_map[self._dark_hole_mask]
            measure_array[i_iteration + 1]["avg"], measure_array[i_iteration + 1]["std"], measure_array[i_iteration + 1]["min"], measure_array[i_iteration + 1]["max"] = np.mean(mesure_map_dark_hole), np.std(mesure_map_dark_hole), np.min(mesure_map_dark_hole), np.max(mesure_map_dark_hole)
            self.signals.contrastMeasured.emit(np.array(measure_map, copy=True), measure_array)
            logger.info("avg = %.4e, std = %.4e, min = %.4e, max = %.4e", measure_array[i_iteration + 1]["avg"], measure_array[i_iteration + 1]["std"], measure_array[i_iteration + 1]["min"], measure_array[i_iteration + 1]["max"])
            # ---- stage 4: apply correction --------------------------------------------------------------------------
            i_iteration = i_iteration + 1
            self.signals.progressTicked.emit(i_iteration, time.time() - t_start)

        self.signals.finished.emit()
