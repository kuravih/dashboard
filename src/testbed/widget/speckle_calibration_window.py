from __future__ import annotations
from typing import TYPE_CHECKING, cast

import cloudpickle
import numpy as np
from matplotlib.lines import Line2D
from numpy.typing import NDArray

from pykato.function import timestamp_string
from pykato.log import setup_logger
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDoubleSpinBox, QGridLayout, QLabel, QVBoxLayout, QWidget, QMessageBox

import testbed

if TYPE_CHECKING:
    from dashboard import MainWindow
from ..device.camera import Camera
from ..device.modulator import Modulator
from ..worker.speckle_calibration_worker import ProcessWorker
from ..worker.storage_worker import SinkStorageWorker, SourceStorageWorker
from ..function import flip_rotate_points
from .camera_window import PreviewWindow as CameraPreviewWindow
from .modulator_window import PreviewWindow as ModulatorPreviewWindow
from .dialog import MessageDialog
from .resource import ICON_STOP, ICON_RUN

from . import DevicesSetupWidget, LinspaceWidget, TaskControlsWidget, Window

logger = setup_logger(f"{testbed.SPECKLE_CALIBRATION}_window", terminator="\n")


# ==== ProcessSettingsWidget ==========================================================================================
class ProcessSettingsWidget(QWidget):
    """
    Speckle Calibration Process Settings
    """

    def __init__(self, parent=None):
        _amplitude_perc_min, _amplitude_perc_max, _amplitude_perc = -100.0, 100.0, 10.0
        _angle_deg_start, _angle_deg_stop, _angle_deg_steps = 0, 170, 18
        _frequency_start, _frequency_stop, _frequency_steps = 0.06, 0.02, 9
        _phase_deg_start, _phase_deg_stop, _phase_deg_steps = 0, 180, 2
        super().__init__(parent)

        amplitude_label = QLabel("Amplitude", self)
        amplitude_label.setFixedWidth(100)

        self.amplitude_perc_spinbox = QDoubleSpinBox(self)
        self.amplitude_perc_spinbox.setRange(_amplitude_perc_min, _amplitude_perc_max)
        self.amplitude_perc_spinbox.setSuffix(" %")
        self.amplitude_perc_spinbox.setSingleStep(1)
        self.amplitude_perc_spinbox.setToolTip("Command amplitude")
        self.amplitude_perc_spinbox.setValue(_amplitude_perc)

        angle_steps_label = QLabel("Angle Steps", self)
        angle_steps_label.setFixedWidth(100)

        self.angle_deg_steps_linspace = LinspaceWidget(_angle_deg_start, _angle_deg_stop, _angle_deg_steps, self)
        self.angle_deg_steps_linspace.start_spinbox.setMinimumWidth(100)
        self.angle_deg_steps_linspace.stop_spinbox.setMinimumWidth(100)
        self.angle_deg_steps_linspace.num_spinbox.setMinimumWidth(100)

        frequency_steps_label = QLabel("Frequency Steps", self)
        frequency_steps_label.setFixedWidth(100)

        self.frequency_steps_linspace = LinspaceWidget(_frequency_start, _frequency_stop, _frequency_steps, self)
        self.frequency_steps_linspace.start_spinbox.setMinimumWidth(100)
        self.frequency_steps_linspace.stop_spinbox.setMinimumWidth(100)
        self.frequency_steps_linspace.num_spinbox.setMinimumWidth(100)

        phase_steps_label = QLabel("Phase Steps", self)
        phase_steps_label.setFixedWidth(100)

        self.phase_deg_steps_linspace = LinspaceWidget(_phase_deg_start, _phase_deg_stop, _phase_deg_steps, self)
        self.phase_deg_steps_linspace.start_spinbox.setMinimumWidth(100)
        self.phase_deg_steps_linspace.stop_spinbox.setMinimumWidth(100)
        self.phase_deg_steps_linspace.num_spinbox.setMinimumWidth(100)

        widget_layout = QGridLayout()

        row = 0
        col = 0
        widget_layout.addWidget(amplitude_label, row, col)
        col += 1
        widget_layout.addWidget(self.amplitude_perc_spinbox, row, col, 1, 3)

        row += 1
        col = 0
        widget_layout.addWidget(angle_steps_label, row, col)
        col += 1
        widget_layout.addWidget(self.angle_deg_steps_linspace, row, col, 1, 3)

        row += 1
        col = 0
        widget_layout.addWidget(frequency_steps_label, row, col)
        col += 1
        widget_layout.addWidget(self.frequency_steps_linspace, row, col, 1, 3)

        row += 1
        col = 0
        widget_layout.addWidget(phase_steps_label, row, col)
        col += 1
        widget_layout.addWidget(self.phase_deg_steps_linspace, row, col, 1, 3)

        self.setLayout(widget_layout)

        self.speckles = np.full((self.frequency_array.size, self.angle_rad_array.size, 2, 2), np.nan)

    @property
    def amplitude_nm(self) -> float:
        return self.amplitude_perc_spinbox.value() / 100.0

    @property
    def angle_deg_array(self) -> np.ndarray:
        return self.angle_deg_steps_linspace.value()

    @property
    def angle_rad_array(self) -> np.ndarray:
        return np.deg2rad(self.angle_deg_array)

    @property
    def frequency_array(self) -> np.ndarray:
        return self.frequency_steps_linspace.value()

    @property
    def phase_deg_array(self) -> np.ndarray:
        return self.phase_deg_steps_linspace.value()

    @property
    def phase_rad_array(self) -> np.ndarray:
        return np.deg2rad(self.phase_deg_array)

    @property
    def speckles(self) -> NDArray[np.float64]:
        return self._speckles

    @speckles.setter
    def speckles(self, value: NDArray[np.float64]):
        self._speckles = value


# ==== ProcessWindow ==================================================================================================
class ProcessWindow(Window):
    """
    Speckle Calibration Process Window
    """

    wid = f"{testbed.SPECKLE_CALIBRATION}_window"

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Dialog)
        self.setWindowTitle("Speckle Calibration")
        self.sink = None
        self.source = None

        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self.setup_main_widget())

        self.speckles_plot = None

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
    def speckles(self) -> NDArray[np.float64]:
        return self.settings_widget.speckles

    @speckles.setter
    def speckles(self, value: NDArray[np.float64]):
        self.settings_widget.speckles = value

    @property
    def speckles_plot(self) -> Line2D | None:
        return self._speckles_plot

    @speckles_plot.setter
    def speckles_plot(self, value: Line2D | None):
        self._speckles_plot = value

    def update_device_buttons(self, enabled: bool):
        main_window = cast("MainWindow", self.parent())
        if self.source is not None:
            main_window.set_device_buttons_enabled(self.source.name, enabled)
        if self.sink is not None:
            main_window.set_device_buttons_enabled(self.sink.name, enabled)

    def update_process_controls(self):
        enabled = False
        if self.source is not None and self.sink is not None:
            if not testbed.data.is_worker_alive(self.source.sampling_worker_id) and not testbed.data.is_worker_alive(self.sink.sampling_worker_id):
                enabled = True
        self.controls_widget.run_stop_button.setEnabled(enabled)

    @Slot(Camera)
    def on_source_changed(self, device: Camera):
        self.source = device
        self.update_process_controls()

    @Slot(Modulator)
    def on_sink_changed(self, device: Modulator):
        self.sink = device
        self.update_process_controls()

    @Slot(int, float)  # step, elapsed_time
    def on_progress_tick(self, step: int, t_elapsed: float):
        self.controls_widget.progressbar.setValue(step + 1)
        self.controls_widget.progressbar.setTime(t_elapsed)
        self.controls_widget.progressbar.updateProgress()

    @Slot(str)
    def on_process_error(self, message: str):
        MessageDialog("Speckle Calibration Worker Failed", message, icon=QMessageBox.Icon.Critical, buttons=QMessageBox.StandardButton.Ok).exec()
        self.on_process_finished()

    @Slot()
    def on_process_finished(self):
        self.controls_widget.progressbar.reset()
        self.controls_widget.progressbar.updateProgress()
        if testbed.data.is_worker_alive(ProcessWorker.wid):
            testbed.data.workers.pop(ProcessWorker.wid)
            self.controls_widget.run_stop_button.setIconHint(QIcon(ICON_RUN), "Run")
        self.update_device_buttons(True)

    @Slot()
    def on_source_storage_finished(self):
        assert self.source is not None
        if testbed.data.is_worker_alive(self.source.storage_worker_id):
            testbed.data.workers.pop(self.source.storage_worker_id)

    @Slot()
    def on_sink_storage_finished(self):
        assert self.sink is not None
        if testbed.data.is_worker_alive(self.sink.storage_worker_id):
            testbed.data.workers.pop(self.sink.storage_worker_id)

    @Slot()
    def on_start_stop_clicked(self):
        if self.source is None or self.sink is None:
            message_dialog = MessageDialog("Devices not selected", "Source and sink devices not selected.", icon=QMessageBox.Icon.Information, buttons=QMessageBox.StandardButton.Ok)
            message_dialog.exec()
        else:
            if testbed.data.is_worker_alive(self.source.storage_worker_id):
                source_storage_worker = cast(SourceStorageWorker, testbed.data.workers[self.source.storage_worker_id])
                source_storage_worker.stop()

            if testbed.data.is_worker_alive(self.sink.storage_worker_id):
                sink_storage_worker = cast(SinkStorageWorker, testbed.data.workers[self.sink.storage_worker_id])
                sink_storage_worker.stop()

            if testbed.data.is_worker_alive(ProcessWorker.wid):
                process_worker = cast(ProcessWorker, testbed.data.workers[ProcessWorker.wid])
                process_worker.stop()
                return

            process_worker = ProcessWorker(self.source, self.sink, self.settings_widget.amplitude_nm, self.settings_widget.frequency_array, self.settings_widget.angle_rad_array, self.settings_widget.phase_rad_array)
            process_worker.signals.progressTicked.connect(self.on_progress_tick)
            process_worker.signals.finished.connect(self.on_process_finished)
            process_worker.signals.error.connect(self.on_process_error)

            self.controls_widget.progressbar.setMaximum(process_worker.n_ticks)
            self.controls_widget.run_stop_button.setIconHint(QIcon(ICON_STOP), "Stop")

            timestamp = timestamp_string(frmt="%Y%m%d.%H%M%S", ms=None)

            with open(f"data/output/{timestamp}_{testbed.SPECKLE_CALIBRATION}_parameters.pkl", "wb") as wbfile:
                parameters_dict = {"amplitudes": self.settings_widget.amplitude_nm, "frequencies": self.settings_widget.frequency_array, "angles": self.settings_widget.angle_deg_array, "phases": self.settings_widget.phase_deg_array}
                cloudpickle.dump(parameters_dict, wbfile)

            source_storage_worker = SourceStorageWorker(f"data/output/{timestamp}_{testbed.SPECKLE_CALIBRATION}_{self.source.name}.raw", process_worker.n_ticks)
            process_worker.signals.srcSampled.connect(source_storage_worker.on_sampled)
            source_storage_worker.signals.finished.connect(self.on_source_storage_finished)
            testbed.data.workers[self.source.storage_worker_id] = source_storage_worker
            testbed.data.threadpool.start(source_storage_worker)

            sink_storage_worker = SinkStorageWorker(f"data/output/{timestamp}_{testbed.SPECKLE_CALIBRATION}_{self.sink.name}.raw", process_worker.n_ticks)
            process_worker.signals.snkSampled.connect(sink_storage_worker.on_sampled)
            sink_storage_worker.signals.finished.connect(self.on_sink_storage_finished)
            testbed.data.workers[self.sink.storage_worker_id] = sink_storage_worker
            testbed.data.threadpool.start(sink_storage_worker)

            if testbed.data.is_window_alive(self.source.preview_window_id):
                source_preview_window = cast(CameraPreviewWindow, testbed.data.windows[self.source.preview_window_id])
                process_worker.signals.srcSampled.connect(source_preview_window.on_sampled)

                if self.speckles_plot is not None:
                    self.speckles_plot.remove()
                    self.speckles = np.full((self.settings_widget.frequency_array.size, self.settings_widget.angle_deg_array.size, 2, 2), np.nan)

                (self.speckles_plot,) = source_preview_window.preview_figure_widget.figure.get_imshow_axes().plot([], [], color="red", marker="o", markersize=10, markerfacecolor="none", linestyle="none")

                @Slot(np.ndarray)
                def on_speckles_located(speckles):
                    self.speckles = speckles
                    speckles_x, speckles_y = flip_rotate_points(speckles[:, :, :, 0], speckles[:, :, :, 1], source_preview_window.sample.capture.shape, source_preview_window.preview_figure_widget.flip, source_preview_window.preview_figure_widget.rotation)
                    self.speckles_plot.set_xdata([speckles_x])
                    self.speckles_plot.set_ydata([speckles_y])

                process_worker.signals.specklesLocated.connect(on_speckles_located)

            if testbed.data.is_window_alive(self.sink.preview_window_id):
                sink_preview_window = cast(ModulatorPreviewWindow, testbed.data.windows[self.sink.preview_window_id])
                process_worker.signals.snkSampled.connect(sink_preview_window.on_sampled)

            testbed.data.workers[ProcessWorker.wid] = process_worker
            testbed.data.threadpool.start(process_worker)
            self.update_device_buttons(False)

    def setup_main_widget(self) -> QWidget:
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        widget.setLayout(layout)

        self.devices_widget = DevicesSetupWidget(testbed.data.devices, parent=self)
        self.devices_widget.sourceChanged.connect(self.on_source_changed)
        self.devices_widget.sinkChanged.connect(self.on_sink_changed)

        self.settings_widget = ProcessSettingsWidget(self)

        self.controls_widget = TaskControlsWidget(self)
        self.controls_widget.run_stop_button.clicked.connect(self.on_start_stop_clicked)
        self.controls_widget.preview_button.hide()
        self.controls_widget.info_button.hide()

        layout.addWidget(self.devices_widget)
        layout.addWidget(self.settings_widget)
        layout.addWidget(self.controls_widget)
        layout.addStretch(5)

        return widget

    def closeEvent(self, event):
        if self.speckles_plot is not None:
            self.speckles_plot.remove()
        if testbed.data.is_worker_alive(ProcessWorker.wid):
            process_worker = cast(ProcessWorker, testbed.data.workers[ProcessWorker.wid])
            process_worker.stop()
        if testbed.data.is_worker_alive(self.source.storage_worker_id):
            source_storage_worker = cast(SourceStorageWorker, testbed.data.workers[self.source.storage_worker_id])
            source_storage_worker.stop()
        if testbed.data.is_worker_alive(self.sink.storage_worker_id):
            sink_storage_worker = cast(SinkStorageWorker, testbed.data.workers[self.sink.storage_worker_id])
            sink_storage_worker.stop()
        self.deleteLater()
        event.accept()
