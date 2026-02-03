import pickle

import numpy as np
from pykato.function import timestamp_string
from pykato.log import setup_logger
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget, QMessageBox

import testbed

from ..device.camera import Camera
from ..worker.camera_calibration_worker import ProcessWorker
from ..worker.storage_worker import SourceStorageWorker
from .camera_window import InfoWindow as CameraInfoWindow
from .camera_window import PreviewWindow as CameraPreviewWindow
from .camera_window import SettingsWindow as CameraSettingsWindow
from .dialog import MessageDialog
from .resource import ICON_PAUSE, ICON_RUN

from . import DevicesSetupWidget, TaskControlsWidget, ExposureTimeArrayWidget, Window

_PROCESS_ = testbed.CAMERA_CALIBRATION
process_worker_id = f"{_PROCESS_}_worker"
source_storage_worker_id = f"{_PROCESS_}_source_storage_worker"

logger = setup_logger(f"{_PROCESS_}_window", terminator="\n")


class ProcessSettingsWidget(QWidget):
    """
    Speckle Calibration Process Settings
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.exposure_time_s_spinboxes = ExposureTimeArrayWidget(parent=self)

        layout = QHBoxLayout()
        layout.addWidget(self.exposure_time_s_spinboxes)

        self.setLayout(layout)

    @property
    def exposure_times_array(self) -> np.ndarray:
        return np.array(self.exposure_time_s_spinboxes.value())


class ProcessWindow(Window):
    """
    Speckle Calibration Process Window
    """

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Dialog)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setWindowTitle("Camera Calibration")
        self._source = None

        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self.setup_main_widget())
        self.setLayout(layout)

    @property
    def source(self) -> Camera | None:
        return self._source

    def on_source_changed(self, _device: Camera):
        self.device_widget.source_info_button.setEnabled(True)
        self.device_widget.source_settings_button.setEnabled(True)
        self.device_widget.source_preview_button.setEnabled(True)
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
        self.device_widget.source_info_button.clicked.connect(lambda _, _device=_device: self.open_device_info_window(_device))
        self.device_widget.source_settings_button.clicked.connect(lambda _, _device=_device: self.open_device_settings_window(_device))
        self.device_widget.source_preview_button.clicked.connect(lambda _, _device=_device: self.open_device_preview_window(_device))
        if self._source is not None:
            self.controls_widget.preview_button.setEnabled(True)
            self.controls_widget.play_pause_button.setEnabled(True)

    def open_device_info_window(self, _device: Camera):
        device_info_window_id = f"{_device.name}_info_window"

        @Slot()
        def on_window_closed():
            testbed.data.windows.pop(device_info_window_id, None)

        if device_info_window_id not in testbed.data.windows:
            info_window: CameraInfoWindow | None = None
            if isinstance(_device, Camera):
                info_window = CameraInfoWindow(_device, self)
                if process_worker_id in testbed.data.workers:  # an update worker is in progress
                    testbed.data.workers[process_worker_id].signals.srcSampled.connect(info_window.on_sampled)
            else:
                raise ValueError("Invalid device")
            info_window.destroyed.connect(on_window_closed)
            info_window.show()
            info_window.raise_()
            info_window.activateWindow()
            testbed.data.windows[device_info_window_id] = info_window

    def open_device_settings_window(self, _device: Camera):
        device_settings_window_id = f"{_device.name}_settings_window"

        @Slot()
        def on_window_closed():
            testbed.data.windows.pop(device_settings_window_id, None)

        if device_settings_window_id not in testbed.data.windows:
            settings_window: CameraSettingsWindow | None = None
            if isinstance(_device, Camera):
                settings_window = CameraSettingsWindow(_device, self)
            else:
                raise ValueError("Invalid device")
            settings_window.destroyed.connect(on_window_closed)
            settings_window.show()
            settings_window.raise_()
            settings_window.activateWindow()
            testbed.data.windows[device_settings_window_id] = settings_window

    def open_device_preview_window(self, _device: Camera):
        device_preview_window_id = f"{_device.name}_preview_window"

        @Slot()
        def on_window_closed():
            testbed.data.windows.pop(device_preview_window_id, None)

        if device_preview_window_id not in testbed.data.windows:
            preview_window: CameraPreviewWindow | None = None
            if isinstance(_device, Camera):
                preview_window = CameraPreviewWindow(_device, self)
                if process_worker_id in testbed.data.workers:  # an update worker is in progress
                    testbed.data.workers[process_worker_id].signals.srcSampled.connect(preview_window.on_sampled)
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
    def on_start_stop_clicked(self):
        if self.source is None:
            message_dialog = MessageDialog("Devices not selected", "Source device not selected.", icon=QMessageBox.Icon.Information, buttons=QMessageBox.StandardButton.Ok)
            message_dialog.exec()
        else:
            source_preview_window_id = f"{self.source.name}_preview_window"

            if process_worker_id in testbed.data.workers:  # an update worker is in progress
                logger.info("stopping running process")
                current_worker = testbed.data.workers.pop(process_worker_id)
                current_worker.stop()
                self.controls_widget.play_pause_button.setIcon(QIcon(ICON_RUN))
                self.device_widget.source_settings_button.setEnabled(True)
                self.controls_widget.progressbar.setMaximum(100)
                self.controls_widget.progressbar.reset()
                self.controls_widget.progressbar.updateProgress()
                if source_storage_worker_id in testbed.data.workers:
                    current_source_storage_worker = testbed.data.workers.pop(source_storage_worker_id)
                    current_source_storage_worker.stop()
                return

            self.controls_widget.progressbar.setMaximum(self.settings_widget.exposure_times_array.size)

            worker = ProcessWorker(self.source, self.settings_widget.exposure_times_array)
            worker.signals.progressTicked.connect(self.on_progress_tick)
            worker.signals.finished.connect(self.on_finished)

            timestamp = timestamp_string(frmt="%Y%m%d.%H%M%S", ms=None)

            source_storage_worker = SourceStorageWorker(f"data/output/{timestamp}_{_PROCESS_}_source.raw", self.settings_widget.exposure_times_array.size)
            worker.signals.srcSampled.connect(source_storage_worker.on_sampled)
            source_storage_worker.signals.finished.connect(self.on_source_storage_finished)
            testbed.data.workers[source_storage_worker_id] = source_storage_worker
            testbed.data.threadpool.start(source_storage_worker)

            self.controls_widget.play_pause_button.setIcon(QIcon(ICON_PAUSE))
            self.device_widget.source_settings_button.setEnabled(False)

            if source_preview_window_id in testbed.data.windows:
                worker.signals.srcSampled.connect(testbed.data.windows[source_preview_window_id].on_sampled)

            testbed.data.workers[process_worker_id] = worker
            testbed.data.threadpool.start(worker)

    def setup_main_widget(self) -> QWidget:
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        widget.setLayout(layout)

        self.device_widget = DevicesSetupWidget(testbed.data.devices, setup_sink=False, parent=self)
        self.device_widget.sourceChanged.connect(self.on_source_changed)

        self.settings_widget = ProcessSettingsWidget(self)

        self.controls_widget = TaskControlsWidget(self)
        self.controls_widget.play_pause_button.clicked.connect(self.on_start_stop_clicked)
        self.controls_widget.preview_button.hide()
        self.controls_widget.info_button.hide()

        layout.addWidget(self.device_widget)
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
