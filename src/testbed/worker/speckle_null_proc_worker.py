import time
import numpy as np
from PySide6.QtCore import Slot, Signal

from pykato.function import sinusoid, text
from pykato.log import setup_logger

from ..device import SourceSample, SinkSample
from ..device.camera import Camera
from ..device.modulator import Modulator
from ..device.mirror import Mirror
from ..worker import Worker, WorkerSignals
from ..function import find_speckles, speckle_parameters

logger = setup_logger("speckle_null_proc_worker", terminator="\n")


def _phs_search(source: Camera, sink: Modulator | Mirror, current_cmd: np.ndarray, speck_freq: float, phases: np.ndarray, speck_angle: float, speck_stencil: np.ndarray):
    # speck_intensity = np.zeros_like(phases) * np.nan
    # amplitude = 0.025
    # i_phs = 0
    # while i_phs < phases.size:
    #     # logger.info("_phs_search phases[%d] = %f", i_phs, phases[i_phs])
    #     # command = current_cmd + 0.5 * sink.pixel_max * amplitude * sinusoid(sink.shape, 1.0 / speck_freq, np.deg2rad(phases[i_phs]), speck_angle)
    #     # command = command - np.mean(command) + sink.pixel_max / 2
    #     # -------------------------------------------------------------------------------------------------------------
    #     probe_command = sink.pixel_max * amplitude * (sinusoid(sink.shape, 1.0 / speck_freq, np.deg2rad(phases[i_phs]), speck_angle) / 2 + 0.5)
    #     command = current_cmd + probe_command
    #     command = np.clip(command, 0, sink.pixel_max)
    #     # -------------------------------------------------------------------------------------------------------------
    #     capture = source.acquire_image(sink.send_command_image(command))
    #     speck_intensity[i_phs] = np.mean(capture[speck_stencil])
    #     phs_probe_data.emit(speck_intensity, command, capture)
    #     i_phs = i_phs + 1

    # _ = source.acquire_image(sink.send_command_image(current_cmd))  # leave as found

    # try:
    #     guess_offset = np.mean(speck_intensity)
    #     offset_min, offset_max = guess_offset * 0.5, guess_offset * 1.5
    #     guess_amplitude = (np.max(speck_intensity) - np.min(speck_intensity)) / 2
    #     amplitude_min, amplitude_max = guess_amplitude * 0.5, guess_amplitude * 1.5
    #     guess_phase = np.pi
    #     phase_min, phase_max = 0, 2 * np.pi
    #     (fit_amplitude, fit_phase, fit_offset), _ = least_squares_fit(speck_intensity, constrained_sin_fit_fn, x_coord=np.deg2rad(phases), guess_prms=(guess_amplitude, guess_phase, guess_offset), bounds=([amplitude_min, phase_min, offset_min], [amplitude_max, phase_max, offset_max]))  # pylint: disable=unbalanced-tuple-unpacking
    # except RuntimeError:
    #     logger.info("_phs_search: least_squares_fit failed")
    #     speck_phase = 0
    # else:
    #     if fit_phase <= 3 * np.pi / 2:
    #         speck_phase = 3 * np.pi / 2 - fit_phase
    #     else:
    #         speck_phase = 7 * np.pi / 2 - fit_phase

    # return speck_phase
    return 0


def _amp_search(source: Camera, sink: Modulator | Mirror, current_cmd: np.ndarray, speck_freq: float, speck_phase: float, speck_angle: float, amplitudes: np.ndarray, speck_stencil: np.ndarray):

    # speck_intensity = np.zeros_like(amplitudes) * np.nan
    # i_amp = 0
    # while i_amp < amplitudes.size:
    #     # logger.info("_phs_search amplitudes[%d] = %f", i_amp, amplitudes[i_amp])
    #     # command = current_cmd + sink.pixel_max * amplitudes[i_amp] * sinusoid(sink.shape, 1.0 / speck_freq, speck_phase, speck_angle)
    #     # command = command - np.mean(command) + sink.pixel_max / 2
    #     # -------------------------------------------------------------------------------------------------------------
    #     probe_command = sink.pixel_max * amplitudes[i_amp] * (sinusoid(sink.shape, 1.0 / speck_freq, speck_phase, speck_angle) / 2 + 0.5)
    #     command = current_cmd + probe_command
    #     command = np.clip(command, 0, sink.pixel_max)
    #     # -------------------------------------------------------------------------------------------------------------
    #     capture = source.acquire_image(sink.send_command_image(command))
    #     speck_intensity[i_amp] = np.mean(capture[speck_stencil])
    #     amp_probe_data.emit(speck_intensity, command, capture)
    #     i_amp = i_amp + 1

    # _ = source.acquire_image(sink.send_command_image(current_cmd))  # leave as found

    # min_index = np.argmin(speck_intensity)

    # try:
    #     (fit_a, fit_b, fit_c), _ = least_squares_fit(speck_intensity, quadratic_fit_fn, x_coord=amplitudes, bounds=([0, -np.inf, -np.inf], [np.inf, 0, np.inf]))  # pylint: disable=unbalanced-tuple-unpacking
    # except RuntimeError:
    #     _speck_amplitude = amplitudes[min_index]
    # else:
    #     _speck_amplitude = -fit_b / (2 * fit_a)
    #     # if _speck_amplitude < amplitudes[0]:
    #     #     speck_amplitude = amplitudes[min_index]
    #     # elif _speck_amplitude > 0.2:
    #     #     speck_amplitude = amplitudes[min_index]
    #     # elif quadratic_fit_fn(_speck_amplitude, fit_a, fit_b, fit_c) > amplitudes[min_index]:
    #     #     speck_amplitude = amplitudes[min_index]
    #     # else:
    #     #     speck_amplitude = _speck_amplitude
    #     speck_amplitude = _speck_amplitude

    # return speck_amplitude
    return 0


class SpeckleNullProcWorkerSignals(WorkerSignals):
    new_source_sample = Signal(SourceSample)
    new_sink_sample = Signal(SinkSample)


class SpeckleNullProcWorker(Worker):
    def __init__(self, _source: Camera, _sink: Modulator | Mirror, _dh_mask: np.ndarray, _speck_calibration: tuple[tuple[float, float], tuple[float, float]], _phases: np.ndarray, _amplitudes: np.ndarray, _n_iterations: int | None = None):
        super().__init__()
        self.signals = SpeckleNullProcWorkerSignals()
        self._source = _source
        self._sink = _sink
        self._dh_mask = _dh_mask
        self._speck_calibration = _speck_calibration
        self._phases = _phases
        self._amplitudes = _amplitudes
        self._n_iterations = _n_iterations

    @Slot()
    def run(self):
        super().run()
        i_iteration = 0
        t_start = time.time()

        # ---- blank --------------------------------------------------------------------------------------------------
        command = self._sink.pxmax * np.clip(np.zeros(self._sink.shape) + 0.5, 0, 1)
        logger.info("%s and %s SpeckleNullProcWorker.run : blank", self._source.name, self._sink.name)

        self._sink.push_command(command.astype(np.uint16))

        _current_sink_sample = self._sink.pull_sample()
        time.sleep(0.1)
        self.signals.new_sink_sample.emit(_current_sink_sample)
        _current_source_sample = self._source.pull_sample()
        time.sleep(0.1)
        self.signals.new_source_sample.emit(_current_source_sample)

        self.signals.progress.emit(i_iteration, time.time() - t_start)
        # ---- blank --------------------------------------------------------------------------------------------------

        center = (self._source.shape[0] / 2, self._source.shape[1] / 2)
        while ((self._n_iterations is None) or (self._n_iterations > i_iteration)) and self._running:
            # command = self._sink.pxmax * np.clip(text(self._sink.shape, f"{i_iteration:02d}", font_size=150), 0, 1)
            logger.info("SpeckleNullProcWorker.run iteration = %s", (f"{i_iteration}") if (self._n_iterations is None) else (f"{i_iteration} of {self._n_iterations}"))

            # ---- stage 0: find speckle ------------------------------------------------------------------------------
            specks, speck_stencil = find_speckles((_current_source_sample.capture * self._dh_mask).astype(float), 1, 5)
            speck_stencil = np.rot90(speck_stencil, 3)
            _current_source_sample.capture = _current_source_sample.capture * self._dh_mask
            self.signals.new_source_sample.emit(_current_source_sample)
            # logger.info("SpeckleNullProcWorker.run speckle location = %s", str(specks[0].weighted_centroid))
            # ---- stage 0: speckle found -----------------------------------------------------------------------------

            # ---- stage 1: calculate speckle period and angle --------------------------------------------------------
            # speck_freq, speck_angle = speckle_parameters(center, specks[0].weighted_centroid, self._speck_calibration)
            # logger.info("SpeckleNullProcWorker.run speck_freq = %f (period = %f), speck_angle = %f", speck_freq, 1.0 / speck_freq, np.rad2deg(speck_angle))
            # speck_data.emit(specks[0].weighted_centroid, speck_freq, speck_angle, speck_stencil)
            # ---- stage 1: speckle period and angle calculated -------------------------------------------------------

            # ---- stage 2: find speckle phase ------------------------------------------------------------------------
            # speck_phase = _phs_search(self._source, self._sink, _current_sink_sample.command, speck_freq, self._phases, speck_angle, speck_stencil)
            # logger.info("SpeckleNullProcWorker.run speck_phase = %f", np.rad2deg(speck_phase))
            # ---- stage 2: speckle phase found -----------------------------------------------------------------------

            # ---- stage 3: find speckle amplitude --------------------------------------------------------------------
            # speck_amplitude = _amp_search(self._source, self._sink, _current_sink_sample.command, speck_freq, speck_phase, speck_angle, self._amplitudes, speck_stencil)
            # logger.info("SpeckleNullProcWorker.run speck_amplitude = %f", speck_amplitude)
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

        self.signals.finish.emit()
