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
from ..device.modulator import Modulator
from ..function import is_speckle_calibration_file_valid, read_speckle_calibration_file, constrained_sin_fit_fn, quadratic_fit_fn
from ..worker.speckle_nulling_worker import ProcessWorker
from ..worker.storage_worker import SinkStorageWorker, SourceStorageWorker
from .camera_window import InfoWindow as CameraInfoWindow
from .camera_window import SpecklePreviewWindow as CameraPreviewWindow
from .camera_window import SettingsWindow as CameraSettingsWindow
from .modulator_window import InfoWindow as ModulatorInfoWindow
from .modulator_window import SpecklePreviewWindow as ModulatorPreviewWindow
from .modulator_window import SettingsWindow as ModulatorSettingsWindow
from .dialog import MessageDialog
from .figure_widget import ContrastFigureWidget, SpeckleNullingFigureWidget
from .resource import ICON_PAUSE, ICON_RUN

from . import DevicesSetupWidget, LinspaceWidget, TaskControlsWidget, Window, FileLoadWidget

_PROCESS_ = testbed.SPECKLE_NULLING
process_worker_id = f"{_PROCESS_}_worker"
process_info_window_id = f"{_PROCESS_}_info_window"
process_preview_window_id = f"{_PROCESS_}_preview_window"
source_storage_worker_id = f"{_PROCESS_}_source_storage_worker"
sink_storage_worker_id = f"{_PROCESS_}_sink_storage_worker"

logger = setup_logger(f"{_PROCESS_}_window", terminator="\n")


# ==== ProcessSettingsWidget ==========================================================================================
class ProcessSettingsWidget(QWidget):
    """
    Speckle Nulling Process Settings
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        phs_steps_label = QLabel("Phase steps", self)
        phs_steps_label.setFixedWidth(100)

        self._phs_steps = LinspaceWidget(0, 300, 6, self)

        amp_steps_label = QLabel("Amp. steps", self)
        amp_steps_label.setFixedWidth(100)

        self._amp_steps = LinspaceWidget(0.0, 0.1, 11, self)

        n_iterations_label = QLabel("Nulling iterations", self)
        n_iterations_label.setFixedWidth(100)

        self._n_iterations_spinbox = QSpinBox(self)
        self._n_iterations_spinbox.setRange(0, 9999)
        self._n_iterations_spinbox.setSingleStep(1)
        self._n_iterations_spinbox.setValue(10)
        self._n_iterations_spinbox.setToolTip("Number of nulling iterations")

        self._continuous_checkbox = QCheckBox("continuous", self)
        self._continuous_checkbox.setToolTip("Run till stop/pause button is clicked")
        self._continuous_checkbox.setMaximumWidth(90)

        @Slot(bool)
        def on_continuous_toggled(checked: bool):
            if checked:
                self._n_iterations_spinbox.setEnabled(False)
            else:
                self._n_iterations_spinbox.setEnabled(True)

        self._continuous_checkbox.toggled.connect(on_continuous_toggled)

        self.dark_hole_mask = None
        # self.dark_hole_mask = chord(self.source.shape, self.source.shape[0] * 7 / 16, 0.65)

        self.speckle_calibration = None

        # ---- speckle calibration file -------------------------------------------------------------------------------
        speckle_calibration_label = QLabel("Speckle Calibration", self)
        speckle_calibration_label.setFixedWidth(100)

        self.calibration_widget = FileLoadWidget(caption="Open Calibration File", directory="./data/output", file_filter="Pickle file (*.pkl)", validator=is_speckle_calibration_file_valid, parent=self)

        n_iterations_layout = QHBoxLayout()
        n_iterations_layout.addWidget(self._n_iterations_spinbox)
        n_iterations_layout.addWidget(self._continuous_checkbox)

        record_label = QLabel("Record", self)
        record_label.setFixedWidth(100)

        self._source_checkbox = QCheckBox("Source", self)
        self._source_checkbox.setToolTip("Source data")

        self._sink_checkbox = QCheckBox("Sink", self)
        self._sink_checkbox.setToolTip("Sink data")

        record_layout = QHBoxLayout()
        record_layout.addWidget(self._source_checkbox)
        record_layout.addWidget(self._sink_checkbox)

        widget_layout = QGridLayout()

        row = 0
        col = 0
        widget_layout.addWidget(phs_steps_label, row, col)
        col += 1
        widget_layout.addWidget(self._phs_steps, row, col)

        row += 1
        col = 0
        widget_layout.addWidget(amp_steps_label, row, col)
        col += 1
        widget_layout.addWidget(self._amp_steps, row, col)

        row += 1
        col = 0
        widget_layout.addWidget(n_iterations_label, row, col)
        col += 1
        widget_layout.addLayout(n_iterations_layout, row, col, 1, 3)

        row += 1
        col = 0
        widget_layout.addWidget(speckle_calibration_label, row, col)
        col += 1
        widget_layout.addWidget(self.calibration_widget, row, col)

        row += 1
        col = 0
        widget_layout.addWidget(record_label, row, col)
        col += 1
        widget_layout.addLayout(record_layout, row, col, 1, 3)

        self.setLayout(widget_layout)

    @property
    def continuous(self) -> bool:
        return self._continuous_checkbox.isChecked()

    @property
    def n_iterations(self) -> int | None:
        return None if self.continuous else self._n_iterations_spinbox.value()

    @property
    def record_source(self) -> bool:
        return self._source_checkbox.isChecked()

    @property
    def record_sink(self) -> bool:
        return self._sink_checkbox.isChecked()

    @property
    def phs_array(self) -> np.ndarray:
        return self._phs_steps.value()

    @property
    def amp_array(self) -> np.ndarray:
        return self._amp_steps.value()


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
    def on_amp_fitted(self, fit_a: float, fit_b: float, fit_c: float):
        self.amp_intensity_fit_y_data = quadratic_fit_fn(self.amp_intensity_fit_x_data, fit_a, fit_b, fit_c)

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
            self.process_preview_figure_widget.figure.get_plot_ax().set_yscale("log")
            self.process_preview_figure_widget.figure.get_plot_ax().set_ylim(1e-5, 1)
        else:
            self.process_preview_figure_widget.cmap_norm = Normalize(1e-5, 1)
            self.process_preview_figure_widget.figure.get_plot_ax().set_yscale("linear")
            self.process_preview_figure_widget.figure.get_plot_ax().set_ylim(1e-5, 1)
        self.process_preview_figure_widget.figure.get_plot_ax().set_yticklabels([])

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
        self.setWindowModality(Qt.WindowModality.WindowModal)
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
    def source(self, value: Camera | None):
        self._source = value

    @property
    def sink(self) -> Modulator | None:
        return self._sink

    @sink.setter
    def sink(self, value: Modulator | None):
        self._sink = value

    @property
    def speckle_calibration(self) -> dict[str, np.ndarray] | None:
        return self._speckle_calibration

    @speckle_calibration.setter
    def speckle_calibration(self, value: dict[str, np.ndarray] | None):
        self._speckle_calibration = value

    @Slot()
    def on_calibration_change(self):
        if self.source is not None and self.sink is not None:
            self.controls_widget.preview_button.setEnabled(True)
            if self.settings_widget.calibration_widget.filepath is not None:
                self.speckle_calibration = read_speckle_calibration_file(self.settings_widget.calibration_widget.filepath)
                self.controls_widget.play_pause_button.setEnabled(True)

    @Slot()
    def on_source_changed(self, _device: Camera):
        self.devices_widget.source_info_button.setEnabled(True)
        self.devices_widget.source_settings_button.setEnabled(True)
        self.devices_widget.source_preview_button.setEnabled(True)
        self.source = _device
        device_preview_window_id = f"{_device.name}_preview_window"
        if device_preview_window_id in testbed.data.windows:
            testbed.data.windows.pop(device_preview_window_id).close()
        device_info_window_id = f"{_device.name}_info_window"
        if device_info_window_id in testbed.data.windows:
            testbed.data.windows.pop(device_info_window_id).close()
        device_settings_window_id = f"{_device.name}_settings_window"
        if device_settings_window_id in testbed.data.windows:
            testbed.data.windows.pop(device_settings_window_id).close()
        self.devices_widget.source_info_button.clicked.connect(lambda _, _device=_device: self.open_device_info_window(_device))
        self.devices_widget.source_settings_button.clicked.connect(lambda _, _device=_device: self.open_device_settings_window(_device))
        self.devices_widget.source_preview_button.clicked.connect(lambda _, _device=_device: self.open_device_preview_window(_device))
        if self.source is not None and self.sink is not None:
            self.controls_widget.preview_button.setEnabled(True)
            self.controls_widget.info_button.setEnabled(True)
            self.settings_widget.dark_hole_mask = chord(self.source.shape, self.source.shape[0] * 7 / 16, 0.65)
            if self.settings_widget.calibration_widget.filepath is not None:
                self.speckle_calibration = read_speckle_calibration_file(self.settings_widget.calibration_widget.filepath)
                self.controls_widget.play_pause_button.setEnabled(True)

    @Slot()
    def on_sink_changed(self, _device: Modulator):
        self.devices_widget.sink_info_button.setEnabled(True)
        self.devices_widget.sink_settings_button.setEnabled(True)
        self.devices_widget.sink_preview_button.setEnabled(True)
        self.sink = _device
        device_preview_window_id = f"{_device.name}_preview_window"
        if device_preview_window_id in testbed.data.windows:
            testbed.data.windows.pop(device_preview_window_id).close()
        device_info_window_id = f"{_device.name}_info_window"
        if device_info_window_id in testbed.data.windows:
            testbed.data.windows.pop(device_info_window_id).close()
        device_settings_window_id = f"{_device.name}_settings_window"
        if device_settings_window_id in testbed.data.windows:
            testbed.data.windows.pop(device_settings_window_id).close()
        self.devices_widget.sink_info_button.clicked.connect(lambda _, _device=_device: self.open_device_info_window(_device))
        self.devices_widget.sink_settings_button.clicked.connect(lambda _, _device=_device: self.open_device_settings_window(_device))
        self.devices_widget.sink_preview_button.clicked.connect(lambda _, _device=_device: self.open_device_preview_window(_device))
        if self.source is not None and self.sink is not None:
            self.controls_widget.preview_button.setEnabled(True)
            self.controls_widget.info_button.setEnabled(True)
            if self.settings_widget.calibration_widget.filepath is not None:
                self.speckle_calibration = read_speckle_calibration_file(self.settings_widget.calibration_widget.filepath)
                self.controls_widget.play_pause_button.setEnabled(True)

    def open_device_info_window(self, _device: Camera | Modulator):
        device_info_window_id = f"{_device.name}_info_window"

        @Slot()
        def on_window_closed():
            testbed.data.windows.pop(device_info_window_id, None)

        if device_info_window_id not in testbed.data.windows:
            info_window: CameraInfoWindow | ModulatorInfoWindow | None = None
            if isinstance(_device, Camera):
                info_window = CameraInfoWindow(_device, parent=self)
                if process_worker_id in testbed.data.workers:  # an update worker is in progress
                    testbed.data.workers[process_worker_id].signals.srcSampled.connect(info_window.on_sampled)
            elif isinstance(_device, Modulator):
                info_window = ModulatorInfoWindow(_device, parent=self)
                if process_worker_id in testbed.data.workers:  # an update worker is in progress
                    testbed.data.workers[process_worker_id].signals.snkSampled.connect(info_window.on_sampled)
            else:
                raise ValueError("Invalid device")
            info_window.destroyed.connect(on_window_closed)
            info_window.show()
            info_window.raise_()
            info_window.activateWindow()
            testbed.data.windows[device_info_window_id] = info_window

    def open_device_settings_window(self, _device: Camera | Modulator):
        device_settings_window_id = f"{_device.name}_settings_window"

        @Slot()
        def on_window_closed():
            testbed.data.windows.pop(device_settings_window_id, None)

        if device_settings_window_id not in testbed.data.windows:
            settings_window: CameraSettingsWindow | ModulatorSettingsWindow | None = None
            if isinstance(_device, Camera):
                settings_window = CameraSettingsWindow(_device, parent=self)
            elif isinstance(_device, Modulator):
                settings_window = ModulatorSettingsWindow(_device, parent=self)
            else:
                raise ValueError("Invalid device")
            settings_window.destroyed.connect(on_window_closed)
            settings_window.show()
            settings_window.raise_()
            settings_window.activateWindow()
            testbed.data.windows[device_settings_window_id] = settings_window

    def open_device_preview_window(self, _device: Camera | Modulator):
        device_preview_window_id = f"{_device.name}_preview_window"

        def on_window_closed():
            testbed.data.windows.pop(device_preview_window_id, None)

        if device_preview_window_id not in testbed.data.windows:
            preview_window: CameraPreviewWindow | ModulatorPreviewWindow | None = None
            if isinstance(_device, Camera):
                preview_window = CameraPreviewWindow(_device, alpha_mask=self.settings_widget.dark_hole_mask, parent=self)
                if process_worker_id in testbed.data.workers:  # an update worker is in progress
                    testbed.data.workers[process_worker_id].signals.srcSampled.connect(preview_window.on_sampled)
            elif isinstance(_device, Modulator):
                preview_window = ModulatorPreviewWindow(_device, parent=self)
                if process_worker_id in testbed.data.workers:  # an update worker is in progress
                    testbed.data.workers[process_worker_id].signals.snkSampled.connect(preview_window.on_sampled)
            else:
                raise ValueError("Invalid device")
            preview_window.destroyed.connect(on_window_closed)
            preview_window.show()
            preview_window.raise_()
            preview_window.activateWindow()
            testbed.data.windows[device_preview_window_id] = preview_window

    @Slot(int, float)  # step, elapsed_time
    def on_progress_tick(self, step: int, t_elapsed: float):
        self.controls_widget.progressbar.setValue(step + 1)
        self.controls_widget.progressbar.setTime(t_elapsed)
        self.controls_widget.progressbar.updateProgress()

    @Slot()
    def on_finish(self):
        self.controls_widget.progressbar.reset()
        self.controls_widget.progressbar.updateProgress()
        if process_worker_id in testbed.data.workers:  # an update worker is in progress
            current_worker = testbed.data.workers.pop(process_worker_id)
            current_worker.stop()
            self.controls_widget.play_pause_button.setIcon(QIcon(ICON_RUN))

    @Slot()
    def on_source_storage_finish(self):
        if source_storage_worker_id in testbed.data.workers:
            source_storage_worker = testbed.data.workers.pop(source_storage_worker_id)
            source_storage_worker.stop()

    @Slot()
    def on_sink_storage_finish(self):
        if sink_storage_worker_id in testbed.data.workers:
            sink_storage_worker = testbed.data.workers.pop(sink_storage_worker_id)
            sink_storage_worker.stop()

    @Slot()
    def on_start_stop_clicked(self):
        if self.source is None or self.sink is None:
            message_dialog = MessageDialog("Devices not selected", "Source and sink devices not selected.", icon=QMessageBox.Icon.Information, buttons=QMessageBox.StandardButton.Ok)
            message_dialog.exec()
        else:
            source_preview_window_id = f"{self.source.name}_preview_window"
            sink_preview_window_id = f"{self.sink.name}_preview_window"

            if process_worker_id in testbed.data.workers:  # an update worker is in progress
                current_worker = testbed.data.workers.pop(process_worker_id)
                current_worker.stop()
                self.controls_widget.play_pause_button.setIcon(QIcon(ICON_RUN))
                self.devices_widget.sink_settings_button.setEnabled(False)
                self.devices_widget.source_settings_button.setEnabled(False)
                self.controls_widget.progressbar.setMaximum(100)
                self.controls_widget.progressbar.reset()
                self.controls_widget.progressbar.updateProgress()
                if source_storage_worker_id in testbed.data.workers:
                    current_source_storage_worker = testbed.data.workers.pop(source_storage_worker_id)
                    current_source_storage_worker.stop()
                if sink_storage_worker_id in testbed.data.workers:
                    current_sink_storage_worker = testbed.data.workers.pop(sink_storage_worker_id)
                    current_sink_storage_worker.stop()
                return

            if self.settings_widget.continuous:
                self.controls_widget.progressbar.setMaximum(0)
            else:
                self.controls_widget.progressbar.setMaximum(self.settings_widget.n_iterations)

            worker = ProcessWorker(self.source, self.sink, self.settings_widget.dark_hole_mask, self.speckle_calibration, self.settings_widget.phs_array, self.settings_widget.amp_array, self.settings_widget.n_iterations)
            worker.signals.progressTicked.connect(self.on_progress_tick)
            worker.signals.finished.connect(self.on_finish)

            timestamp = timestamp_string(frmt="%Y%m%d.%H%M%S", ms=None)

            if self.settings_widget.record_source:
                source_storage_worker = SourceStorageWorker(f"data/output/{timestamp}_{_PROCESS_}_source.raw", self.settings_widget.n_iterations)
                worker.signals.srcSampled.connect(source_storage_worker.on_sample)
                source_storage_worker.signals.finished.connect(self.on_source_storage_finish)
                testbed.data.workers[source_storage_worker_id] = source_storage_worker
                testbed.data.threadpool.start(source_storage_worker)

            if self.settings_widget.record_sink:
                sink_storage_worker = SinkStorageWorker(f"data/output/{timestamp}_{_PROCESS_}_sink.raw", self.settings_widget.n_iterations)
                worker.signals.snkSampled.connect(sink_storage_worker.on_sample)
                sink_storage_worker.signals.finished.connect(self.on_sink_storage_finish)
                testbed.data.workers[sink_storage_worker_id] = sink_storage_worker
                testbed.data.threadpool.start(sink_storage_worker)

            self.controls_widget.play_pause_button.setIcon(QIcon(ICON_PAUSE))
            self.devices_widget.sink_settings_button.setEnabled(False)
            self.devices_widget.source_settings_button.setEnabled(False)

            if source_preview_window_id in testbed.data.windows:
                worker.signals.srcSampled.connect(testbed.data.windows[source_preview_window_id].on_sampled)
                worker.signals.speckleLocated.connect(testbed.data.windows[source_preview_window_id].on_speckle_located)
            if sink_preview_window_id in testbed.data.windows:
                worker.signals.snkSampled.connect(testbed.data.windows[sink_preview_window_id].on_sampled)
            if process_info_window_id in testbed.data.windows:
                worker.signals.phsSwept.connect(testbed.data.windows[process_info_window_id].on_phs_swept)
                worker.signals.phsFitted.connect(testbed.data.windows[process_info_window_id].on_phs_fitted)
                worker.signals.phsSolved.connect(testbed.data.windows[process_info_window_id].on_phs_solved)
                worker.signals.ampSwept.connect(testbed.data.windows[process_info_window_id].on_amp_swept)
                worker.signals.ampFitted.connect(testbed.data.windows[process_info_window_id].on_amp_fitted)
                worker.signals.ampSolved.connect(testbed.data.windows[process_info_window_id].on_amp_solved)
            if process_preview_window_id in testbed.data.windows:
                worker.signals.contrastMeasured.connect(testbed.data.windows[process_preview_window_id].on_contrast_measured)
                worker.signals.speckleLocated.connect(testbed.data.windows[process_preview_window_id].on_speckle_located)

            testbed.data.workers[process_worker_id] = worker
            testbed.data.threadpool.start(worker)

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
                testbed.data.workers[process_worker_id].signals.contrastMeasured.connect(testbed.data.windows[process_preview_window_id].on_contrast_measured)
                testbed.data.workers[process_worker_id].signals.speckleLocated.connect(testbed.data.windows[process_preview_window_id].on_speckle_located)

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
                testbed.data.workers[process_worker_id].signals.srcSampled.connect(testbed.data.windows[process_info_window_id].on_src_sampled)
                testbed.data.workers[process_worker_id].signals.snkSampled.connect(testbed.data.windows[process_info_window_id].on_snk_sampled)
                testbed.data.workers[process_worker_id].signals.phsSwept.connect(testbed.data.windows[process_info_window_id].on_phs_swept)
                testbed.data.workers[process_worker_id].signals.phsFitted.connect(testbed.data.windows[process_info_window_id].on_phs_fitted)
                testbed.data.workers[process_worker_id].signals.phsSolved.connect(testbed.data.windows[process_info_window_id].on_phs_solved)
                testbed.data.workers[process_worker_id].signals.ampSwept.connect(testbed.data.windows[process_info_window_id].on_amp_swept)
                testbed.data.workers[process_worker_id].signals.ampFitted.connect(testbed.data.windows[process_info_window_id].on_amp_fitted)
                testbed.data.workers[process_worker_id].signals.ampSolved.connect(testbed.data.windows[process_info_window_id].on_amp_solved)

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
