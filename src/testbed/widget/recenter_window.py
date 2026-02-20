import numpy as np

from pykato.log import setup_logger
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QCheckBox, QPushButton, QDoubleSpinBox, QGridLayout, QHBoxLayout, QLabel, QSpinBox, QVBoxLayout, QWidget, QMessageBox, QComboBox
from matplotlib import colormaps
from matplotlib.colors import Normalize, LogNorm

import testbed

from ..device.camera import Camera
from ..device.modulator import Modulator
from ..worker.recenter_worker import ProcessWorker
from ..widget.figure_widget import SourceFigureWidget
from .camera_window import InfoWindow as CameraInfoWindow
from .camera_window import PreviewWindow as _CameraPreviewWindow
from .camera_window import SettingsWindow as CameraSettingsWindow
from .modulator_window import InfoWindow as ModulatorInfoWindow
from .modulator_window import PreviewWindow as _ModulatorPreviewWindow
from .modulator_window import SettingsWindow as ModulatorSettingsWindow
from .dialog import MessageDialog
from .resource import ICON_PAUSE, ICON_RUN

from . import DevicesSetupWidget, TaskControlsWidget, Window

_PROCESS_ = testbed.RECENTER
process_worker_id = f"{_PROCESS_}_worker"
process_info_window_id = f"{_PROCESS_}_info_window"
source_storage_worker_id = f"{_PROCESS_}_source_storage_worker"
sink_storage_worker_id = f"{_PROCESS_}_sink_storage_worker"

logger = setup_logger(f"{_PROCESS_}_window", terminator="\n")


# ==== ModulatorPreviewSettingsWindow =================================================================================
class ModulatorPreviewSettingsWindow(Window):
    """
    Settings for the modulator preview window
    """

    def __init__(self, cmap: str, parent=None):
        super().__init__(parent, Qt.WindowType.Dialog)
        self.cmap = cmap

        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setWindowTitle("Preview Settings")
        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self.setup_preview_settings_widget())
        self.setLayout(layout)

    def setup_preview_settings_widget(self) -> QWidget:
        widget = QWidget(self)
        layout = QGridLayout(widget)
        widget.setLayout(layout)

        cmap_label = QLabel("Colormap", self)
        self.cmap_combobox = QComboBox(self)
        self.cmap_combobox.addItems(list(colormaps))
        self.cmap_combobox.setCurrentIndex(list(colormaps).index(self.cmap))

        row = 0
        col = 0
        layout.addWidget(cmap_label, row, col)
        col += 1
        layout.addWidget(self.cmap_combobox, row, col)

        return widget


# ==== ModulatorPreviewWindow =========================================================================================
class ModulatorPreviewWindow(_ModulatorPreviewWindow):
    """
    Modulator preview window
    """

    def __init__(self, modulator: Modulator, parent: QWidget | None = None):
        super().__init__(modulator, parent=parent)

    @Slot()
    def on_preview_settings_clicked(self):
        preview_settings_window = ModulatorPreviewSettingsWindow(cmap=self.preview_figure_widget.cmap_name, parent=self)
        preview_settings_window.show()
        preview_settings_window.raise_()
        preview_settings_window.activateWindow()
        preview_settings_window.cmap_combobox.currentTextChanged.connect(self.on_cmap_changed)

    @Slot()
    def on_update_timer_tick(self):
        self.preview_figure_widget.figure.get_image().set_data(self.sample.command)
        self.preview_figure_widget.figure.canvas.draw_idle()


# ==== CameraPreviewSettingsWindow ====================================================================================
class CameraPreviewSettingsWindow(Window):
    """
    Settings for the camera preview window
    """

    def __init__(self, cmap_name: str, cmap_norm: Normalize, parent=None):
        super().__init__(parent, Qt.WindowType.Dialog)
        self.cmap_name: str = cmap_name
        self.cmap_norm: Normalize = cmap_norm

        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setWindowTitle("Preview Settings")
        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self.setup_preview_settings_widget())
        self.setLayout(layout)

    def setup_preview_settings_widget(self) -> QWidget:
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

        return widget


# ==== CameraPreviewWindow ============================================================================================
class CameraPreviewWindow(_CameraPreviewWindow):
    """
    Camera speckle preview window
    """

    def __init__(self, camera: Camera, center: list[float] | None, parent: QWidget | None = None):
        self._speckles = [[np.nan, np.nan], [np.nan, np.nan]]
        if center is None:
            self._center = [camera.shape[0] / 2, camera.shape[1] / 2]
        else:
            self._center = center
        super().__init__(camera, parent=parent)

    @property
    def speckles(self) -> list[list[float]]:
        return self._speckles

    @property
    def center(self) -> list[float]:
        return self._center

    def setup_preview_widget(self) -> QWidget:
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(2, 2, 2, 2)
        widget.setLayout(layout)

        self._sample = self.camera.sample
        self.preview_figure_widget = SourceFigureWidget(self.camera.blank, self.camera.pxmax, parent=self)
        self.speckles_axlines = ((self.preview_figure_widget.figure.get_imshow_axes().axvline(np.nan, alpha=0.5, linewidth=0.5, color="red"), self.preview_figure_widget.figure.get_imshow_axes().axhline(np.nan, alpha=0.5, linewidth=0.5, color="red")), (self.preview_figure_widget.figure.get_imshow_axes().axvline(np.nan, alpha=0.5, linewidth=0.5, color="red"), self.preview_figure_widget.figure.get_imshow_axes().axhline(np.nan, alpha=0.5, linewidth=0.5, color="red")))
        self.center_axlines = (self.preview_figure_widget.figure.get_imshow_axes().axvline(np.nan, alpha=0.5, linewidth=0.5, color="blue"), self.preview_figure_widget.figure.get_imshow_axes().axhline(np.nan, alpha=0.5, linewidth=0.5, color="blue"))

        if self.preview_figure_widget.toolbar is not None:
            self.preview_figure_widget.toolbar.settingsClicked.connect(self.on_preview_settings_clicked)

        layout.addWidget(self.preview_figure_widget)

        return widget

    @Slot(float, float, float, float)
    def on_speckles_located(self, x0: float, y0: float, x1: float, y1: float):
        # self._center = [np.nan, np.nan]
        self._speckles = [[x0, y0], [x1, y1]]

    @Slot(float, float)
    def on_center_located(self, xc: float, yc: float):
        self._center = [xc, yc]
        # self._speckles = [[np.nan, np.nan], [np.nan, np.nan]]

    @Slot()
    def on_preview_settings_clicked(self):
        preview_settings_window = CameraPreviewSettingsWindow(cmap_name=self.preview_figure_widget.cmap_name, cmap_norm=self.preview_figure_widget.cmap_norm, parent=self)
        preview_settings_window.show()
        preview_settings_window.raise_()
        preview_settings_window.activateWindow()
        preview_settings_window.log_checkbox.checkStateChanged.connect(self.on_cmap_norm_changed)
        preview_settings_window.cmap_combobox.currentTextChanged.connect(self.on_cmap_name_changed)

    @Slot(str)
    def on_cmap_name_changed(self, colormap: str):
        self.preview_figure_widget.cmap_name = colormap

    @Slot(bool)
    def on_cmap_norm_changed(self, checked: bool):
        if checked == Qt.CheckState.Checked:
            self.preview_figure_widget.cmap_norm = LogNorm(1, 2**12 - 1)
        else:
            self.preview_figure_widget.cmap_norm = Normalize(0, 2**12 - 1)

    @Slot()
    def on_update_timer_tick(self):
        self.preview_figure_widget.figure.get_image().set_data(self.sample.capture)
        self.speckles_axlines[0][0].set_xdata([self.speckles[0][0], self.speckles[0][0]])
        self.speckles_axlines[0][1].set_ydata([self.speckles[0][1], self.speckles[0][1]])
        self.speckles_axlines[1][0].set_xdata([self.speckles[1][0], self.speckles[1][0]])
        self.speckles_axlines[1][1].set_ydata([self.speckles[1][1], self.speckles[1][1]])
        self.center_axlines[0].set_xdata([self.center[0], self.center[0]])
        self.center_axlines[1].set_ydata([self.center[1], self.center[1]])
        self.preview_figure_widget.figure.canvas.draw_idle()

    def closeEvent(self, event):
        if self.update_timer.isActive():
            self.update_timer.stop()
        self.deleteLater()
        event.accept()


class ProcessSettingsWidget(QWidget):
    """
    Re-centering process settings window
    """

    def __init__(self, parent=None):
        self._center = [np.nan, np.nan]
        super().__init__(parent)

        n_steps_label = QLabel("Steps", self)
        n_steps_label.setFixedWidth(100)

        self._n_steps_spinbox = QSpinBox(self)
        self._n_steps_spinbox.setRange(0, 9999)
        self._n_steps_spinbox.setSingleStep(1)
        self._n_steps_spinbox.setValue(2)
        self._n_steps_spinbox.setToolTip("Number of steps")

        n_steps_layout = QHBoxLayout()
        n_steps_layout.addWidget(self._n_steps_spinbox)

        sleep_label = QLabel("Sleep", self)
        sleep_label.setFixedWidth(100)

        self._sleep_s_spinbox = QDoubleSpinBox(self)
        self._sleep_s_spinbox.setMinimum(0)
        self._sleep_s_spinbox.setSingleStep(0.0001)
        self._sleep_s_spinbox.setDecimals(4)
        self._sleep_s_spinbox.setValue(0.1)
        self._sleep_s_spinbox.setSuffix(" s")

        center_label = QLabel("Center", self)
        sleep_label.setFixedWidth(100)

        self._center_values_label = QLabel(f"[[{self._center[0]:.0f}], [{self._center[1]:.0f}]]", self)
        sleep_label.setFixedWidth(100)

        self.move_pushbutton = QPushButton("Move", self)

        widget_layout = QGridLayout()

        row = 0
        col = 0
        widget_layout.addWidget(n_steps_label, row, col)
        col += 1
        widget_layout.addLayout(n_steps_layout, row, col, 1, 3)

        row += 1
        col = 0
        widget_layout.addWidget(sleep_label, row, col)
        col += 1
        widget_layout.addWidget(self._sleep_s_spinbox, row, col, 1, 3)

        row += 1
        col = 0
        widget_layout.addWidget(center_label, row, col)
        col += 1
        widget_layout.addWidget(self._center_values_label, row, col)
        col += 1
        widget_layout.addWidget(self.move_pushbutton, row, col, 1, 2)

        self.setLayout(widget_layout)

    @property
    def n_steps(self) -> int:
        return self._n_steps_spinbox.value()

    @property
    def sleep_s(self) -> float:
        return self._sleep_s_spinbox.value()

    @property
    def center(self) -> list[float]:
        return self._center

    @center.setter
    def center(self, value: list[float]):
        self._center = value
        self._center_values_label.setText(f"[[{self._center[0]:.0f}], [{self._center[1]:.0f}]]")


class ProcessWindow(Window):
    """
    Re-centering process window
    """

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Dialog)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setWindowTitle("Recenter Process")
        self._sink = None
        self._source = None
        self._center = [np.nan, np.nan]

        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self.setup_main_widget())
        self.setLayout(layout)

    @property
    def source(self) -> Camera | None:
        return self._source

    @property
    def sink(self) -> Modulator | None:
        return self._sink

    def on_source_changed(self, _device: Camera):
        self.devices_widget.source_info_button.setEnabled(True)
        self.devices_widget.source_settings_button.setEnabled(True)
        self.devices_widget.source_preview_button.setEnabled(True)
        self._source = _device
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
        if self._source is not None:
            self.settings_widget.center = [self._source.shape[0] / 2, self._source.shape[1] / 2]
            if self._sink is not None:
                self.controls_widget.play_pause_button.setEnabled(True)

    def on_sink_changed(self, _device: Modulator):
        self.devices_widget.sink_info_button.setEnabled(True)
        self.devices_widget.sink_settings_button.setEnabled(True)
        self.devices_widget.sink_preview_button.setEnabled(True)
        self._sink = _device
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
        if self._source is not None:
            self.settings_widget.center = [self._source.shape[0] / 2, self._source.shape[1] / 2]
            if self._sink is not None:
                self.controls_widget.play_pause_button.setEnabled(True)

    def open_device_info_window(self, _device: Camera | Modulator):
        device_info_window_id = f"{_device.name}_info_window"

        @Slot()
        def on_window_closed():
            testbed.data.windows.pop(device_info_window_id, None)

        if device_info_window_id not in testbed.data.windows:
            info_window: CameraInfoWindow | ModulatorInfoWindow | None = None
            if isinstance(_device, Camera):
                info_window = CameraInfoWindow(_device, self)
                if process_worker_id in testbed.data.workers:  # an update worker is in progress
                    testbed.data.workers[process_worker_id].signals.srcSampled.connect(info_window.on_sampled)
            elif isinstance(_device, Modulator):
                info_window = ModulatorInfoWindow(_device, self)
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
                settings_window = CameraSettingsWindow(_device, self)
            elif isinstance(_device, Modulator):
                settings_window = ModulatorSettingsWindow(_device, self)
            else:
                raise ValueError("Invalid device")
            settings_window.destroyed.connect(on_window_closed)
            settings_window.show()
            settings_window.raise_()
            settings_window.activateWindow()
            testbed.data.windows[device_settings_window_id] = settings_window

    def open_device_preview_window(self, _device: Camera | Modulator):
        device_preview_window_id = f"{_device.name}_preview_window"

        @Slot()
        def on_window_closed():
            testbed.data.windows.pop(device_preview_window_id, None)

        if device_preview_window_id not in testbed.data.windows:
            preview_window: CameraPreviewWindow | ModulatorPreviewWindow | None = None
            if isinstance(_device, Camera):
                preview_window = CameraPreviewWindow(_device, self.settings_widget.center, parent=self)
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
    def on_finished(self):
        self.controls_widget.progressbar.reset()
        self.controls_widget.progressbar.updateProgress()
        if process_worker_id in testbed.data.workers:  # an update worker is in progress
            current_worker = testbed.data.workers.pop(process_worker_id)
            current_worker.stop()
            self.controls_widget.play_pause_button.setIcon(QIcon(ICON_RUN))

    @Slot()
    def on_source_storage_finished(self):
        if source_storage_worker_id in testbed.data.workers:
            source_storage_worker = testbed.data.workers.pop(source_storage_worker_id)
            source_storage_worker.stop()

    @Slot()
    def on_sink_storage_finished(self):
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
                self.devices_widget.sink_settings_button.setEnabled(True)
                self.devices_widget.source_settings_button.setEnabled(True)
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

            worker = ProcessWorker(self.source, self.sink, self.settings_widget.n_steps)
            worker.signals.progressTicked.connect(self.on_progress_tick)
            worker.signals.finished.connect(self.on_finished)

            self.controls_widget.play_pause_button.setIcon(QIcon(ICON_PAUSE))
            self.devices_widget.sink_settings_button.setEnabled(False)
            self.devices_widget.source_settings_button.setEnabled(False)

            if source_preview_window_id in testbed.data.windows:
                worker.signals.srcSampled.connect(testbed.data.windows[source_preview_window_id].on_sampled)
                worker.signals.specklesLocated.connect(testbed.data.windows[source_preview_window_id].on_speckles_located)
                worker.signals.centerLocated.connect(testbed.data.windows[source_preview_window_id].on_center_located)
            if sink_preview_window_id in testbed.data.windows:
                worker.signals.snkSampled.connect(testbed.data.windows[sink_preview_window_id].on_sampled)

            worker.signals.centerLocated.connect(self.on_center_located)

            testbed.data.workers[process_worker_id] = worker
            testbed.data.threadpool.start(worker)

    def on_center_move_clicked(self):
        if self.source is None:
            message_dialog = MessageDialog("Devices not selected", "Source device not selected.", icon=QMessageBox.Icon.Information, buttons=QMessageBox.StandardButton.Ok)
            message_dialog.exec()
        else:
            delta = [self.source.shape[0]/2 - self.settings_widget.center[0], self.source.shape[1]/2 - self.settings_widget.center[1]]
            # reply = self.source.move_roi(delta[0], delta[1])
            # logger.info("reply = %s", reply)
            logger.info("delta %s", delta)

    def setup_main_widget(self) -> QWidget:
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        widget.setLayout(layout)

        self.settings_widget = ProcessSettingsWidget(self)
        self.settings_widget.move_pushbutton.clicked.connect(self.on_center_move_clicked)

        self.devices_widget = DevicesSetupWidget(testbed.data.devices, parent=self)
        self.devices_widget.sourceChanged.connect(self.on_source_changed)
        self.devices_widget.sinkChanged.connect(self.on_sink_changed)

        self.controls_widget = TaskControlsWidget(self)
        self.controls_widget.play_pause_button.clicked.connect(self.on_start_stop_clicked)
        self.controls_widget.info_button.hide()
        self.controls_widget.preview_button.hide()

        layout.addWidget(self.devices_widget)
        layout.addWidget(self.settings_widget)
        layout.addWidget(self.controls_widget)
        layout.addStretch(5)

        return widget

    @Slot(float, float)
    def on_center_located(self, xc: float, yc: float):
        self.settings_widget.center = [xc, yc]

    def closeEvent(self, event):
        while testbed.data.workers:
            key, worker = testbed.data.workers.popitem()
            worker.stop()
            logger.info("stopping worker %s", key)
        self.deleteLater()
        event.accept()
