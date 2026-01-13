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
    new_source_sample = Signal(SourceSample)
    new_sink_sample = Signal(SinkSample)
    speckle_location = Signal(float, float)
    speckle_parameters = Signal(float, float)
    measurement = Signal(np.ndarray)


class ProcessWorker(Worker):
    def __init__(self, _source: Camera, _sink: Modulator, _dh_mask: np.ndarray, _speck_calibration: tuple[tuple[float, float], tuple[float, float]], _phases: np.ndarray, _amplitudes: np.ndarray, _n_iterations: int | None = None):
        super().__init__()
        self.signals = ProcessWorkerSignals()
        self._source = _source
        self._sink = _sink
        self._dh_mask = _dh_mask
        self._speck_calibration = _speck_calibration
        self._phases = _phases
        self._amplitudes = _amplitudes
        self._n_iterations = _n_iterations

    def speckle_phase_search(self, current_cmd: np.ndarray, speck_freq: float, phases: np.ndarray, speck_angle: float, speck_stencil: np.ndarray):
        speck_intensity = np.zeros_like(phases) * np.nan
        amplitude = 0.025
        i_phs = 0
        while i_phs < phases.size:
            probe_command = amplitude * self._sink.pxmax * 0.5 * (sinusoid(self._sink.shape, 1.0 / speck_freq, np.deg2rad(phases[i_phs]), speck_angle) / 2 + 0.5)

            command = current_cmd + probe_command
            command = np.clip(command, 0, self._sink.pxmax)

            _current_sink_sample = self._sink.push_command(command.astype(np.uint16))
            self.signals.new_sink_sample.emit(_current_sink_sample)
            time.sleep(0.1)

            _current_source_sample = self._source.pull_capture()
            self.signals.new_source_sample.emit(_current_source_sample)
            time.sleep(0.2)

            measurement = np.log10(_current_source_sample.capture / (2**12 - 1))
            self.signals.measurement.emit(measurement)

            speck_intensity[i_phs] = np.mean(_current_source_sample.capture[speck_stencil])
            i_phs = i_phs + 1

        try:
            guess_offset = np.mean(speck_intensity)
            offset_min, offset_max = guess_offset * 0.5, guess_offset * 1.5
            guess_amplitude = (np.max(speck_intensity) - np.min(speck_intensity)) / 2
            amplitude_min, amplitude_max = guess_amplitude * 0.5, guess_amplitude * 1.5
            guess_phase = np.pi
            phase_min, phase_max = 0, 2 * np.pi
            (fit_amplitude, fit_phase, fit_offset), _ = least_squares_fit(speck_intensity, constrained_sin_fit_fn, x_coord=np.deg2rad(phases), guess_prms=(guess_amplitude, guess_phase, guess_offset), bounds=([amplitude_min, phase_min, offset_min], [amplitude_max, phase_max, offset_max]))  # pylint: disable=unbalanced-tuple-unpacking
        except RuntimeError:
            logger.info("speckle_phase_search: least_squares_fit failed")
            speck_phase = 0
        else:
            speck_phase = fit_phase

        logger.info("speckle_phase_search : %f", np.rad2deg(speck_phase))

        return speck_phase

    def speckle_amplitude_search(self, current_cmd: np.ndarray, speck_freq: float, speck_phase: float, speck_angle: float, amplitudes: np.ndarray, speck_stencil: np.ndarray):
        speck_intensity = np.zeros_like(amplitudes) * np.nan
        i_amp = 0
        while i_amp < amplitudes.size:
            probe_command = amplitudes[i_amp] * self._sink.pxmax * 0.5 * (sinusoid(self._sink.shape, 1.0 / speck_freq, speck_phase, speck_angle) / 2 + 0.5)

            command = current_cmd + probe_command
            command = np.clip(command, 0, self._sink.pxmax)

            _current_sink_sample = self._sink.push_command(command.astype(np.uint16))
            self.signals.new_sink_sample.emit(_current_sink_sample)
            time.sleep(0.1)

            _current_source_sample = self._source.pull_capture()
            self.signals.new_source_sample.emit(_current_source_sample)
            time.sleep(0.2)

            measurement = np.log10(_current_source_sample.capture / (2**12 - 1))
            self.signals.measurement.emit(measurement)

            speck_intensity[i_amp] = np.mean(_current_source_sample.capture[speck_stencil])
            i_amp = i_amp + 1

        min_index = np.argmin(speck_intensity)

        try:
            (fit_a, fit_b, fit_c), _ = least_squares_fit(speck_intensity, quadratic_fit_fn, x_coord=amplitudes, bounds=([0, -np.inf, -np.inf], [np.inf, 0, np.inf]))  # pylint: disable=unbalanced-tuple-unpacking
        except RuntimeError:
            _speck_amplitude = amplitudes[min_index]
        else:
            _speck_amplitude = -fit_b / (2 * fit_a)
            if _speck_amplitude < amplitudes[0]:
                speck_amplitude = amplitudes[min_index]
            elif _speck_amplitude > 0.2:
                speck_amplitude = amplitudes[min_index]
            elif quadratic_fit_fn(_speck_amplitude, fit_a, fit_b, fit_c) > amplitudes[min_index]:
                speck_amplitude = amplitudes[min_index]
            else:
                speck_amplitude = _speck_amplitude

        logger.info("speckle_amplitude_search : %f", speck_amplitude)

        return speck_amplitude

    @Slot()
    def run(self):
        super().run()
        i_iteration = 0
        t_start = time.time()

        # ---- blank --------------------------------------------------------------------------------------------------
        command = self._sink.pxmax * (np.zeros(self._sink.shape) + 0.5)
        command = command + self._sink.pxmax * 0.5 * (sinusoid(self._sink.shape, 1.0 / 0.035, 0, np.pi / 6) / 2 + 0.5)

        _current_sink_sample = self._sink.push_command(command.astype(np.uint16))
        self.signals.new_sink_sample.emit(_current_sink_sample)
        time.sleep(0.1)

        _current_source_sample = self._source.pull_capture()
        self.signals.new_source_sample.emit(_current_source_sample)
        time.sleep(0.2)

        # capture = flip_rotate(_current_source_sample.capture, self._source.flip, self._source.rotation)
        capture = _current_source_sample.capture
        measurement = np.log10(capture / (2**12 - 1))
        self.signals.measurement.emit(measurement)

        self.signals.progress.emit(i_iteration, time.time() - t_start)
        # ---- blank --------------------------------------------------------------------------------------------------

        logger.info("%s and %s ProcessWorker.run : iteration %s of %s", self._source.name, self._sink.name, i_iteration, self._n_iterations)

        center = (self._source.shape[0] / 2, self._source.shape[1] / 2)
        while ((self._n_iterations is None) or (self._n_iterations > i_iteration)) and self._running:
            # ---- stage 0: find speckle ------------------------------------------------------------------------------
            specks, speck_stencil = find_speckles((_current_source_sample.capture * self._dh_mask).astype(float), 1, 5)
            self.signals.speckle_location.emit(*specks[0])
            # ---- stage 0: speckle found -----------------------------------------------------------------------------

            # ---- stage 1: calculate speckle period and angle --------------------------------------------------------
            speck_freq, speck_angle = speckle_parameters(center, specks[0], self._speck_calibration)
            speck_angle = np.pi - speck_angle
            self.signals.speckle_parameters.emit(speck_freq, speck_angle)
            # ---- stage 1: speckle period and angle calculated -------------------------------------------------------

            # ---- stage 2: find speckle phase ------------------------------------------------------------------------
            speck_phase = self.speckle_phase_search(_current_sink_sample.command, speck_freq, self._phases, speck_angle, speck_stencil)
            # ---- stage 2: speckle phase found -----------------------------------------------------------------------

            # ---- stage 3: find speckle amplitude --------------------------------------------------------------------
            speck_amplitude = self.speckle_amplitude_search(_current_sink_sample.command, speck_freq, speck_phase, speck_angle, self._amplitudes, speck_stencil)
            # ---- stage 3: speckle amplitude found -------------------------------------------------------------------

            # ---- stage 4: apply correction --------------------------------------------------------------------------
            # ---------------------------------------------------------------------------------------------------------
            # # command = current_cmd + 0.5 * sink.pixel_max * speck_amplitude * sinusoid(sink.shape, 1.0 / speck_freq, speck_phase, speck_angle)
            # # command = command - np.mean(command) + sink.pixel_max / 2
            # ---------------------------------------------------------------------------------------------------------
            # correction = self._sink.pixel_max * speck_amplitude * (sinusoid(self._sink.shape, 1.0 / speck_freq, speck_phase, speck_angle) / 2 + 0.5)
            # command = _current_sink_sample.command + correction
            # ---------------------------------------------------------------------------------------------------------
            # command = command - np.mean(command) + self._sink.pixel_max / 2
            # command = np.clip(command, 0, self._sink.pixel_max)
            # # current_cmd[:] = command
            # ---- stage 4: apply correction --------------------------------------------------------------------------

            # # current_cap = self._source.acquire_image(self._sink.send_command_image(current_cmd))
            # # progress_data.emit(i_iteration, current_cmd, current_cap)
            # time.sleep(0.1)
            # # self.signals.progress.emit(i_iteration, time.time() - t_start)
            # i_iteration = i_iteration + 1

            # self._sink.push_command(command.astype(np.uint16))
            # self.signals.new_sink_sample.emit(self._sink.pull_sample())
            # time.sleep(0.1)
            # self.signals.new_source_sample.emit(self._source.pull_sample())
            # time.sleep(0.1)

            i_iteration = i_iteration + 1
            self.signals.progress.emit(i_iteration, time.time() - t_start)

        self.signals.finished.emit()
