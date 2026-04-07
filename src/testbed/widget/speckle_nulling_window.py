import numpy as np
from numpy.typing import NDArray

from pykato.function import chord, timestamp_string
from pykato.log import setup_logger

from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QCheckBox, QGridLayout, QHBoxLayout, QLabel, QMessageBox, QSpinBox, QVBoxLayout, QWidget, QComboBox
from matplotlib import colormaps
from matplotlib.colors import Normalize, LogNorm

import testbed

from ..device.camera import Camera
from ..device.modulator import Modulator, FULL_STROKE_NM
from ..function import is_speckle_calibration_file_valid, read_speckle_calibration_file, constrained_sin_fit_fn, quadratic_fit_fn
from ..worker.speckle_nulling_worker import ProcessWorker
from ..worker.storage_worker import SinkStorageWorker, SourceStorageWorker
from .camera_window import PreviewWindow as CameraPreviewWindow
from .camera_window import InfoWindow as CameraInfoWindow
from .camera_window import SettingsWindow as CameraSettingsWindow
from .modulator_window import InfoWindow as ModulatorInfoWindow
from .modulator_window import PreviewWindow as ModulatorPreviewWindow
from .modulator_window import SettingsWindow as ModulatorSettingsWindow
from .dialog import MessageDialog
from .figure_widget import ContrastFigureWidget, SpeckleNullingFigureWidget
from .resource import ICON_PAUSE, ICON_RUN

from . import DevicesSetupWidget, LinspaceWidget, TaskControlsWidget, Window, FileLoadWidget

_PROCESS_ = testbed.SPECKLE_NULLING
process_worker_id = f"{_PROCESS_}_worker"
process_info_window_id = f"{_PROCESS_}_info_window"
process_preview_window_id = f"{_PROCESS_}_preview_window"

logger = setup_logger(f"{_PROCESS_}_window", terminator="\n")


# ==== ProcessSettingsWidget ==========================================================================================
class ProcessSettingsWidget(QWidget):
    """
    Speckle Nulling Process Settings
    """

    def __init__(self, parent=None):
        self.dark_hole_mask = None  # chord(self.source.shape, self.source.shape[0] * 5 / 16, 0.6)
        self.speckle_calibration = None

        super().__init__(parent)

        phs_steps_label = QLabel("Phase steps", self)
        phs_steps_label.setFixedWidth(100)

        self.phs_steps_linspace = LinspaceWidget(0, 300, 6, self)
        self.phs_steps_linspace.start_spinbox.setMinimumWidth(100)
        self.phs_steps_linspace.stop_spinbox.setMinimumWidth(100)
        self.phs_steps_linspace.num_spinbox.setMinimumWidth(100)

        amp_steps_label = QLabel("Amp. steps", self)
        amp_steps_label.setFixedWidth(100)

        self.amp_steps_linspace = LinspaceWidget(0.0, 50, 11, self)
        self.amp_steps_linspace.start_spinbox.setRange(-100, 100)
        self.amp_steps_linspace.start_spinbox.setSuffix(" %")
        self.amp_steps_linspace.start_spinbox.setMinimumWidth(100)
        self.amp_steps_linspace.stop_spinbox.setRange(-100, 100)
        self.amp_steps_linspace.stop_spinbox.setSuffix(" %")
        self.amp_steps_linspace.stop_spinbox.setMinimumWidth(100)
        self.amp_steps_linspace.num_spinbox.setMinimumWidth(100)

        n_iterations_label = QLabel("Iterations", self)
        n_iterations_label.setFixedWidth(100)

        self.n_iterations_spinbox = QSpinBox(self)
        self.n_iterations_spinbox.setRange(0, 9999)
        self.n_iterations_spinbox.setSingleStep(1)
        self.n_iterations_spinbox.setToolTip("Number of nulling iterations")
        self.n_iterations_spinbox.setValue(2)

        self._continuous_checkbox = QCheckBox("continuous", self)
        self._continuous_checkbox.setToolTip("Run till stop/pause button is clicked")

        @Slot(bool)
        def on_continuous_toggled(checked: bool):
            if checked:
                self.n_iterations_spinbox.setEnabled(False)
            else:
                self.n_iterations_spinbox.setEnabled(True)

        self._continuous_checkbox.toggled.connect(on_continuous_toggled)

        speckle_calibration_label = QLabel("Calibration", self)
        speckle_calibration_label.setFixedWidth(100)

        self.calibration_widget = FileLoadWidget(caption="Open Calibration File", directory="./data/output", file_filter="Pickle file (*.pkl)", validator=is_speckle_calibration_file_valid, parent=self)

        n_iterations_layout = QHBoxLayout()
        n_iterations_layout.addWidget(self.n_iterations_spinbox, stretch=1)
        n_iterations_layout.addWidget(self._continuous_checkbox, alignment=Qt.AlignmentFlag.AlignRight)

        record_label = QLabel("Record", self)
        record_label.setFixedWidth(100)

        self.source_checkbox = QCheckBox("Source", self)
        self.source_checkbox.setToolTip("Source data")

        self.sink_checkbox = QCheckBox("Sink", self)
        self.sink_checkbox.setToolTip("Sink data")

        record_layout = QHBoxLayout()
        record_layout.addWidget(self.source_checkbox)
        record_layout.addWidget(self.sink_checkbox)

        widget_layout = QGridLayout()

        row = 0
        col = 0
        widget_layout.addWidget(phs_steps_label, row, col)
        col += 1
        widget_layout.addWidget(self.phs_steps_linspace, row, col)

        row += 1
        col = 0
        widget_layout.addWidget(amp_steps_label, row, col)
        col += 1
        widget_layout.addWidget(self.amp_steps_linspace, row, col)

        row += 1
        col = 0
        widget_layout.addWidget(n_iterations_label, row, col)
        col += 1
        widget_layout.addLayout(n_iterations_layout, row, col, 1, 2)

        row += 1
        col = 0
        widget_layout.addWidget(speckle_calibration_label, row, col)
        col += 1
        widget_layout.addWidget(self.calibration_widget, row, col)

        row += 1
        col = 0
        widget_layout.addWidget(record_label, row, col)
        col += 1
        widget_layout.addLayout(record_layout, row, col, 1, 2)

        self.setLayout(widget_layout)

    @property
    def continuous(self) -> bool:
        return self._continuous_checkbox.isChecked()

    @property
    def n_iterations(self) -> int | None:
        return None if self.continuous else self.n_iterations_spinbox.value()

    @property
    def record_source(self) -> bool:
        return self.source_checkbox.isChecked()

    @property
    def record_sink(self) -> bool:
        return self.sink_checkbox.isChecked()

    @property
    def phs_array(self) -> np.ndarray:
        return self.phs_steps_linspace.value()

    @property
    def amp_array(self) -> np.ndarray:
        return FULL_STROKE_NM * self.amp_steps_linspace.value() / 100.0

    @property
    def dark_hole_mask(self) -> NDArray[np.bool] | None:
        return self._dark_hole_mask  # chord(self.source.shape, self.source.shape[0] * 5 / 16, 0.6)

    @dark_hole_mask.setter
    def dark_hole_mask(self, value: NDArray[np.bool] | None):
        self._dark_hole_mask = value

    @property
    def speckle_calibration(self) -> dict | None:
        return self._speckle_calibration

    @speckle_calibration.setter
    def speckle_calibration(self, value: dict | None):
        self._speckle_calibration = value


# ==== ProcessInfoWindow ==============================================================================================
class ProcessInfoWindow(Window):
    """
    Speckle Nulling Process Information Window
    """

    def __init__(self, phs_lim: tuple[float, float], phs_array: np.ndarray, amp_lim: tuple[float, float], amp_array: np.ndarray, parent: QWidget | None = None):
        super().__init__(parent, Qt.WindowType.Dialog)

        self.phs_lim = phs_lim
        self.phs_array = phs_array
        self.phs_intensity_data_array = np.ones_like(phs_array) * np.nan

        self.phs_intensity_fit = None, None, None
        self.phs_intensity_fit_x_data = np.linspace(phs_lim[0], phs_lim[1], 361)
        self.phs_intensity_fit_y_data = np.ones_like(self.phs_intensity_fit_x_data) * np.nan
        self.phs_solve = np.nan

        self.amp_lim = amp_lim
        self.amp_array = amp_array
        self.amp_intensity_data_array = np.ones_like(amp_array) * np.nan

        self.amp_intensity_fit = None, None, None
        self.amp_intensity_fit_x_data = np.linspace(amp_lim[0], amp_lim[-1], 101)
        self.amp_intensity_fit_y_data = np.ones_like(self.amp_intensity_fit_x_data) * np.nan
        self.amp_solve = np.nan

        self.setWindowTitle("Speckle Nulling")

        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self.setup_info_widget())
        self.setLayout(layout)

        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.on_update_timer_tick)
        self.update_timer.start(100)  # Update window every 100 ms

    @Slot(np.ndarray)
    def on_phs_swept(self, intensity: np.ndarray):
        self.phs_intensity_data_array[:] = intensity[:]
        self.process_info_figure.phs_ax.relim()
        self.process_info_figure.phs_ax.autoscale_view(scalex=False, scaley=True)

    @Slot(float, float, float)
    def on_phs_fitted(self, fit_amplitude: float, fit_phase: float, fit_offset: float):
        self.phs_intensity_fit_y_data = constrained_sin_fit_fn(np.deg2rad(self.phs_intensity_fit_x_data), fit_amplitude, fit_phase, fit_offset)

    @Slot(float)
    def on_phs_solved(self, solve: float):
        self.phs_solve = np.rad2deg(solve)

    @Slot(np.ndarray)
    def on_amp_swept(self, intensity: np.ndarray):
        self.amp_intensity_data_array[:] = intensity[:]
        self.process_info_figure.amp_ax.relim()
        self.process_info_figure.amp_ax.autoscale_view(scalex=False, scaley=True)

    @Slot(float, float, float)
    def on_amp_fitted(self, fit_a: float, fit_x0: float, fit_c: float):
        self.amp_intensity_fit_y_data = quadratic_fit_fn(self.amp_intensity_fit_x_data, fit_a, fit_x0, fit_c)

    @Slot(float)
    def on_amp_solved(self, solve: float):
        self.amp_solve = solve

    def setup_info_widget(self) -> QWidget:
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(2, 2, 2, 2)
        widget.setLayout(layout)
        self.process_info_figure = SpeckleNullingFigureWidget(self.phs_lim, self.amp_lim, ["Home", "Pan", "Zoom", "Save"], parent=self)
        layout.addWidget(self.process_info_figure)
        return widget

    @Slot()
    def on_update_timer_tick(self):
        self.process_info_figure.set_phs_data_plot(self.phs_array, self.phs_intensity_data_array)
        self.process_info_figure.set_phs_fit_plot(self.phs_intensity_fit_x_data, self.phs_intensity_fit_y_data)
        self.process_info_figure.set_phs_solve(self.phs_solve)
        self.process_info_figure.set_amp_data_plot(self.amp_array, self.amp_intensity_data_array)
        self.process_info_figure.set_amp_fit_plot(self.amp_intensity_fit_x_data, self.amp_intensity_fit_y_data)
        self.process_info_figure.set_amp_solve(self.amp_solve)
        self.process_info_figure.figure.canvas.draw_idle()

    def closeEvent(self, event):
        if self.update_timer.isActive():
            self.update_timer.stop()
        self.deleteLater()
        event.accept()


# ==== ProcessPreviewSettingsWindow ===================================================================================
class ProcessPreviewSettingsWindow(Window):
    """
    Process Preview Settings Window
    """

    def __init__(self, cmap_name: str, cmap_norm: Normalize, alpha_mask_show: bool, parent=None):
        super().__init__(parent, Qt.WindowType.Dialog)
        self.cmap_name: str = cmap_name
        self.cmap_norm: Normalize = cmap_norm
        self.alpha_mask_show: bool = alpha_mask_show

        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setWindowTitle("Process Preview Settings")
        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self.setup_settings_widget())
        self.setLayout(layout)

    def setup_settings_widget(self) -> QWidget:
        widget = QWidget(self)
        layout = QGridLayout(widget)
        widget.setLayout(layout)

        scale_label = QLabel("Scale", self)
        self.log_checkbox = QCheckBox("Log", self)
        self.log_checkbox.setToolTip("Log Scale")
        if isinstance(self.cmap_norm, LogNorm):
            self.log_checkbox.setChecked(True)
        else:
            self.log_checkbox.setChecked(False)

        cmap_label = QLabel("Colormap", self)
        self.cmap_combobox = QComboBox(self)
        self.cmap_combobox.addItems(list(colormaps))
        self.cmap_combobox.setCurrentIndex(list(colormaps).index(self.cmap_name))

        dark_hole_mask_label = QLabel("Dark Hole Mask", self)
        self.mask_checkbox = QCheckBox("Show", self)
        self.mask_checkbox.setToolTip("Show dark hole mask")
        self.mask_checkbox.setChecked(self.alpha_mask_show)

        row = 0
        col = 0
        layout.addWidget(scale_label, row, col)
        col += 1
        layout.addWidget(self.log_checkbox, row, col)

        row += 1
        col = 0
        layout.addWidget(cmap_label, row, col)
        col += 1
        layout.addWidget(self.cmap_combobox, row, col)

        row += 1
        col = 0
        layout.addWidget(dark_hole_mask_label, row, col)
        col += 1
        layout.addWidget(self.mask_checkbox, row, col)

        return widget


# ==== ProcessPreviewWindow ===========================================================================================
class ProcessPreviewWindow(Window):
    """
    Speckle Nulling Contrast Result Window
    Consists of an Imshow axes for the contrast map and a Plot axes for a contrast evolution plot.
    """

    def __init__(self, measure_map: np.ndarray, n_iterations: int, dark_hole_mask: NDArray[np.bool], parent: QWidget | None = None):
        super().__init__(parent, Qt.WindowType.Dialog)
        self.measure_map = measure_map
        self.measure_curve = np.full(n_iterations + 1, fill_value=np.nan, dtype=[("avg", float), ("std", float), ("min", float), ("max", float)])
        self.n_iterations = n_iterations
        self.dark_hole_mask = dark_hole_mask

        self.speckle = [np.nan, np.nan]
        # self.speckle_frequency = np.nan
        # self.speckle_angle = np.nan

        self.setWindowTitle("Contrast")

        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self.setup_preview_widget())
        self.setLayout(layout)

        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.on_update_timer_tick)
        self.update_timer.start(100)  # Update window every 100 ms

    @Slot(np.ndarray, np.ndarray)
    def on_contrast_measured(self, measure_map: np.ndarray, measure_curve: np.ndarray):
        self.measure_map = measure_map
        self.measure_curve = measure_curve

    @Slot(float, float, float, float)
    def on_speckle_located(self, x: float, y: float, frequency: float, angle: float):
        self.speckle[0], self.speckle[1] = x, y
        # self.speckle_frequency = frequency
        # self.speckle_angle = angle

    def setup_preview_widget(self) -> QWidget:
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(2, 2, 2, 2)
        widget.setLayout(layout)
        self.process_preview_figure_widget = ContrastFigureWidget(self.measure_map, self.n_iterations, dark_hole_mask=self.dark_hole_mask, parent=self)
        if self.process_preview_figure_widget.toolbar is not None:
            self.process_preview_figure_widget.toolbar.settingsClicked.connect(self.on_preview_settings_clicked)
        layout.addWidget(self.process_preview_figure_widget)
        return widget

    @Slot()
    def on_preview_settings_clicked(self):
        process_preview_settings_window = ProcessPreviewSettingsWindow(cmap_name=self.process_preview_figure_widget.cmap_name, cmap_norm=self.process_preview_figure_widget.cmap_norm, alpha_mask_show=self.process_preview_figure_widget.alpha_mask_show, parent=self)
        process_preview_settings_window.show()
        process_preview_settings_window.raise_()
        process_preview_settings_window.activateWindow()
        process_preview_settings_window.log_checkbox.checkStateChanged.connect(self.on_cmap_norm_changed)
        process_preview_settings_window.cmap_combobox.currentTextChanged.connect(self.on_cmap_name_changed)
        process_preview_settings_window.mask_checkbox.checkStateChanged.connect(self.on_mask_show_changed)

    @Slot(str)
    def on_cmap_name_changed(self, colormap: str):
        self.process_preview_figure_widget.cmap_name = colormap

    @Slot(bool)
    def on_cmap_norm_changed(self, checked: Qt.CheckState):
        if checked == Qt.CheckState.Checked:
            self.process_preview_figure_widget.cmap_norm = LogNorm(1e-5, 1)
            self.process_preview_figure_widget.figure.get_plot_axes().set_yscale("log")
            self.process_preview_figure_widget.figure.get_plot_axes().set_ylim(1e-5, 1)
        else:
            self.process_preview_figure_widget.cmap_norm = Normalize(1e-5, 1)
            self.process_preview_figure_widget.figure.get_plot_axes().set_yscale("linear")
            self.process_preview_figure_widget.figure.get_plot_axes().set_ylim(1e-5, 1)
        self.process_preview_figure_widget.figure.get_plot_axes().set_yticklabels([])

    @Slot(bool)
    def on_mask_show_changed(self, checked: Qt.CheckState):
        self.process_preview_figure_widget.alpha_mask_show = checked == Qt.CheckState.Checked

    @Slot()
    def on_update_timer_tick(self):
        self.process_preview_figure_widget.set_contrast_map_data(self.measure_map)
        self.process_preview_figure_widget.set_contrast_curve_data(self.measure_curve)
        self.process_preview_figure_widget.set_speckle_location_data(self.speckle)
        self.process_preview_figure_widget.figure.canvas.draw_idle()

    def closeEvent(self, event):
        if self.update_timer.isActive():
            self.update_timer.stop()
        self.deleteLater()
        event.accept()


# ==== ProcessWindow ==================================================================================================
class ProcessWindow(Window):
    """
    Speckle Nulling Process Window
    """

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Dialog)
        # self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setWindowTitle("Speckle Nulling Process")
        self.sink = None
        self.source = None
        self.speckle_calibration = None

        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self.setup_main_widget())
        self.setLayout(layout)

    @property
    def source(self) -> Camera | None:
        return self._source

    @source.setter
    def source(self, device: Camera | None):
        self._source = device

    @property
    def sink(self) -> Modulator | None:
        return self._sink

    @sink.setter
    def sink(self, device: Modulator | None):
        self._sink = device

    @property
    def speckle_calibration(self) -> dict[str, dict[str, float]] | None:
        return self._speckle_calibration

    @speckle_calibration.setter
    def speckle_calibration(self, value: dict[str, dict[str, float]] | None):
        self._speckle_calibration = value

    @Slot()
    def on_calibration_change(self):
        self.controls_widget.info_button.setEnabled(False)
        self.controls_widget.preview_button.setEnabled(False)
        self.controls_widget.play_pause_button.setEnabled(False)
        if self.source is not None and self.sink is not None and self.settings_widget.calibration_widget.filepath is not None:
            self.speckle_calibration = read_speckle_calibration_file(self.settings_widget.calibration_widget.filepath)
            self.controls_widget.info_button.setEnabled(True)
            self.controls_widget.preview_button.setEnabled(True)
            self.controls_widget.play_pause_button.setEnabled(True)

    @Slot()
    def on_source_changed(self, device: Camera):
        self.source = device
        if process_info_window_id in testbed.data.windows:
            testbed.data.windows.pop(process_info_window_id).close()
        if process_preview_window_id in testbed.data.windows:
            testbed.data.windows.pop(process_preview_window_id).close()
        self.controls_widget.play_pause_button.setEnabled(False)
        if self.source is not None:
            self.settings_widget.dark_hole_mask = chord(self.source.shape, self.source.shape[0] * 5 / 16, 0.6)
            if self.sink is not None:
                self.controls_widget.preview_button.setEnabled(True)
                self.controls_widget.info_button.setEnabled(True)
                if self.settings_widget.calibration_widget.filepath is not None:
                    self.speckle_calibration = read_speckle_calibration_file(self.settings_widget.calibration_widget.filepath)
                    self.controls_widget.play_pause_button.setEnabled(True)

    @Slot()
    def on_sink_changed(self, device: Modulator):
        self.sink = device
        if process_info_window_id in testbed.data.windows:
            testbed.data.windows.pop(process_info_window_id).close()
        if process_preview_window_id in testbed.data.windows:
            testbed.data.windows.pop(process_preview_window_id).close()
        self.controls_widget.play_pause_button.setEnabled(False)
        if self.source is not None:
            self.settings_widget.dark_hole_mask = chord(self.source.shape, self.source.shape[0] * 5 / 16, 0.6)
            if self.sink is not None:
                self.controls_widget.preview_button.setEnabled(True)
                self.controls_widget.info_button.setEnabled(True)
                if self.settings_widget.calibration_widget.filepath is not None:
                    self.speckle_calibration = read_speckle_calibration_file(self.settings_widget.calibration_widget.filepath)
                    self.controls_widget.play_pause_button.setEnabled(True)

    @Slot(int, float)  # step, elapsed_time
    def on_progress_tick(self, step: int, t_elapsed: float):
        self.controls_widget.progressbar.setValue(step + 1)
        self.controls_widget.progressbar.setTime(t_elapsed)
        self.controls_widget.progressbar.updateProgress()

    @Slot()
    def on_finished(self):
        self.controls_widget.progressbar.reset()
        self.controls_widget.progressbar.updateProgress()
        if process_worker_id in testbed.data.workers:  # an update worker is in progress
            process_worker: ProcessWorker = testbed.data.workers[process_worker_id]
            process_worker.stop()
            self.controls_widget.play_pause_button.setIconHint(QIcon(ICON_RUN), "Run")
            testbed.data.workers.pop(process_worker_id)

        assert self.source is not None
        source_preview_window_id = f"{self.source.name}_preview_window"
        if source_preview_window_id in testbed.data.windows:
            source_preview_window: CameraPreviewWindow = testbed.data.windows[source_preview_window_id]
            source_preview_window.update_timer.stop()
            source_preview_window.update_timer.timeout.disconnect()
            source_preview_window.update_timer.timeout.connect(source_preview_window.on_update_timer_tick)

        assert self.sink is not None
        sink_preview_window_id = f"{self.sink.name}_preview_window"
        if sink_preview_window_id in testbed.data.windows:
            sink_preview_window: ModulatorPreviewWindow = testbed.data.windows[sink_preview_window_id]
            sink_preview_window.update_timer.stop()
            sink_preview_window.update_timer.timeout.disconnect()
            sink_preview_window.update_timer.timeout.connect(sink_preview_window.on_update_timer_tick)

    @Slot()
    def on_source_storage_finished(self):
        assert self.source is not None
        source_storage_worker_id = f"{self.source.name}_storage_worker"
        if source_storage_worker_id in testbed.data.workers:
            source_storage_worker: SourceStorageWorker = testbed.data.workers[source_storage_worker_id]
            source_storage_worker.stop()
            testbed.data.workers.pop(source_storage_worker_id)

    @Slot()
    def on_sink_storage_finished(self):
        assert self.sink is not None
        sink_storage_worker_id = f"{self.sink.name}_storage_worker"
        if sink_storage_worker_id in testbed.data.workers:
            sink_storage_worker: SinkStorageWorker = testbed.data.workers[sink_storage_worker_id]
            sink_storage_worker.stop()
            testbed.data.workers.pop(sink_storage_worker_id)

    @Slot()
    def on_start_stop_clicked(self):
        if self.source is None or self.sink is None:
            message_dialog = MessageDialog("Devices not selected", "Source and sink devices not selected.", icon=QMessageBox.Icon.Information, buttons=QMessageBox.StandardButton.Ok)
            message_dialog.exec()
        else:
            source_sampling_worker_id = f"{self.source.name}_sampling_worker"
            if source_sampling_worker_id in testbed.data.workers:
                source_sampling_worker: CameraSamplingWorker = testbed.data.workers[source_sampling_worker_id]
                source_sampling_worker.stop()
                testbed.data.workers.pop(source_sampling_worker_id)

            source_storage_worker_id = f"{self.source.name}_storage_worker"
            if source_storage_worker_id in testbed.data.workers:
                source_storage_worker: SourceStorageWorker = testbed.data.workers[source_storage_worker_id]
                source_storage_worker.stop()
                testbed.data.workers.pop(source_storage_worker_id)

            sink_sampling_worker_id = f"{self.sink.name}_sampling_worker"
            if sink_sampling_worker_id in testbed.data.workers:
                sink_sampling_worker: ModulatorSamplingWorker = testbed.data.workers[sink_sampling_worker_id]
                sink_sampling_worker.stop()
                testbed.data.workers.pop(sink_sampling_worker_id)

            sink_storage_worker_id = f"{self.sink.name}_storage_worker"
            if sink_storage_worker_id in testbed.data.workers:
                sink_storage_worker: SinkStorageWorker = testbed.data.workers[sink_storage_worker_id]
                sink_storage_worker.stop()
                testbed.data.workers.pop(sink_storage_worker_id)

            if process_worker_id in testbed.data.workers:  # an update worker is in progress
                process_worker: ProcessWorker = testbed.data.workers[process_worker_id]
                process_worker.stop()
                testbed.data.workers.pop(process_worker_id)

                self.controls_widget.play_pause_button.setIconHint(QIcon(ICON_RUN), "Run")
                self.controls_widget.progressbar.setMaximum(100)
                self.controls_widget.progressbar.reset()
                self.controls_widget.progressbar.updateProgress()

                return

            if self.settings_widget.continuous:
                self.controls_widget.progressbar.setMaximum(0)
            else:
                self.controls_widget.progressbar.setMaximum(self.settings_widget.n_iterations)

            process_worker = ProcessWorker(self.source, self.sink, self.settings_widget.dark_hole_mask, self.speckle_calibration, self.settings_widget.phs_array, self.settings_widget.amp_array, self.settings_widget.n_iterations)
            process_worker.signals.progressTicked.connect(self.on_progress_tick)
            process_worker.signals.finished.connect(self.on_finished)

            self.controls_widget.play_pause_button.setIconHint(QIcon(ICON_PAUSE), "Pause")

            source_preview_window_id = f"{self.source.name}_preview_window"
            if source_preview_window_id in testbed.data.windows:
                source_preview_window: CameraPreviewWindow = testbed.data.windows[source_preview_window_id]
                process_worker.signals.srcSampled.connect(source_preview_window.on_sampled)

            sink_preview_window_id = f"{self.sink.name}_preview_window"
            if sink_preview_window_id in testbed.data.windows:
                sink_preview_window: ModulatorPreviewWindow = testbed.data.windows[sink_preview_window_id]
                process_worker.signals.snkSampled.connect(sink_preview_window.on_sampled)

            if process_info_window_id in testbed.data.windows:
                process_info_window: ProcessInfoWindow = testbed.data.windows[process_info_window_id]
                process_worker.signals.phsSwept.connect(process_info_window.on_phs_swept)
                process_worker.signals.phsFitted.connect(process_info_window.on_phs_fitted)
                process_worker.signals.phsSolved.connect(process_info_window.on_phs_solved)
                process_worker.signals.ampSwept.connect(process_info_window.on_amp_swept)
                process_worker.signals.ampFitted.connect(process_info_window.on_amp_fitted)
                process_worker.signals.ampSolved.connect(process_info_window.on_amp_solved)

            if process_preview_window_id in testbed.data.windows:
                process_preview_window: ProcessPreviewWindow = testbed.data.windows[process_preview_window_id]
                process_worker.signals.speckleLocated.connect(process_preview_window.on_speckle_located)
                process_worker.signals.contrastMeasured.connect(process_preview_window.on_contrast_measured)

            testbed.data.workers[process_worker_id] = process_worker
            testbed.data.threadpool.start(process_worker)

    def open_process_preview_clicked(self):

        @Slot()
        def on_window_closed():
            testbed.data.windows.pop(process_preview_window_id, None)

        if process_preview_window_id not in testbed.data.windows and self.source is not None and self.sink is not None:
            process_preview_window = ProcessPreviewWindow(self.source.sample.capture, self.settings_widget.n_iterations, self.settings_widget.dark_hole_mask, parent=self)
            process_preview_window.destroyed.connect(on_window_closed)
            process_preview_window.show()
            process_preview_window.raise_()
            process_preview_window.activateWindow()
            testbed.data.windows[process_preview_window_id] = process_preview_window

            if process_worker_id in testbed.data.workers:
                process_worker: ProcessWorker = testbed.data.workers[process_worker_id]
                process_worker.signals.speckleLocated.connect(process_preview_window.on_speckle_located)
                process_worker.signals.contrastMeasured.connect(process_preview_window.on_contrast_measured)

    def open_process_info_clicked(self):

        @Slot()
        def on_window_closed():
            testbed.data.windows.pop(process_info_window_id, None)

        if process_info_window_id not in testbed.data.windows and self.source is not None and self.sink is not None:
            process_info_window = ProcessInfoWindow([0, 360], self.settings_widget.phs_array, [self.settings_widget.amp_array[0], self.settings_widget.amp_array[-1]], self.settings_widget.amp_array, parent=self)
            process_info_window.destroyed.connect(on_window_closed)
            process_info_window.show()
            process_info_window.raise_()
            process_info_window.activateWindow()
            testbed.data.windows[process_info_window_id] = process_info_window

            if process_worker_id in testbed.data.workers:
                process_worker = testbed.data.workers[process_worker_id]
                process_worker.signals.phsSwept.connect(process_info_window.on_phs_swept)
                process_worker.signals.phsFitted.connect(process_info_window.on_phs_fitted)
                process_worker.signals.phsSolved.connect(process_info_window.on_phs_solved)
                process_worker.signals.ampSwept.connect(process_info_window.on_amp_swept)
                process_worker.signals.ampFitted.connect(process_info_window.on_amp_fitted)
                process_worker.signals.ampSolved.connect(process_info_window.on_amp_solved)

    def setup_main_widget(self) -> QWidget:
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        widget.setLayout(layout)

        self.devices_widget = DevicesSetupWidget(testbed.data.devices, parent=self)
        self.devices_widget.sourceChanged.connect(self.on_source_changed)
        self.devices_widget.sinkChanged.connect(self.on_sink_changed)

        self.settings_widget = ProcessSettingsWidget(self)
        self.settings_widget.calibration_widget.fileChanged.connect(self.on_calibration_change)

        self.controls_widget = TaskControlsWidget(self)
        self.controls_widget.play_pause_button.clicked.connect(self.on_start_stop_clicked)
        self.controls_widget.info_button.clicked.connect(self.open_process_info_clicked)
        self.controls_widget.preview_button.clicked.connect(self.open_process_preview_clicked)

        layout.addWidget(self.devices_widget)
        layout.addWidget(self.settings_widget)
        layout.addWidget(self.controls_widget)
        layout.addStretch(5)

        return widget

    def closeEvent(self, event):
        while testbed.data.workers:
            key, worker = testbed.data.workers.popitem()
            worker.stop()
            logger.info("stopping worker %s", key)
        self.deleteLater()
        event.accept()
