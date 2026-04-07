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
from ..widget.camera_window import PreviewWindow as CameraPreviewWindow
from ..worker.camera_worker import ProcessWorker as CameraSamplingWorker
from .dialog import MessageDialog
from .resource import ICON_PAUSE, ICON_RUN

from . import DevicesSetupWidget, TaskControlsWidget, ExposureTimeArrayWidget, Window

_PROCESS_ = testbed.CAMERA_CALIBRATION
process_worker_id = f"{_PROCESS_}_worker"

logger = setup_logger(f"{_PROCESS_}_window", terminator="\n")


class ProcessSettingsWidget(QWidget):
    """
    Camera Calibration Process Settings
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
    Camera Calibration Process Window
    """

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Dialog)
        # self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setWindowTitle("Camera Calibration")
        self.source = None

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

    @Slot(Camera)
    def on_source_changed(self, device: Camera):
        self.source = device
        self.controls_widget.play_pause_button.setEnabled(False)
        if self.source is not None:
            self.controls_widget.play_pause_button.setEnabled(True)

    @Slot(int, float)  # step, elapsed_time
    def on_progress_tick(self, step: int, t_elapsed: float):
        self.controls_widget.progressbar.setValue(step + 1)
        self.controls_widget.progressbar.setTime(t_elapsed)
        self.controls_widget.progressbar.updateProgress()

    @Slot()
    def on_process_finished(self):
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

    @Slot()
    def on_source_storage_finished(self):
        assert self.source is not None
        source_storage_worker_id = f"{self.source.name}_storage_worker"
        if source_storage_worker_id in testbed.data.workers:
            source_storage_worker: SourceStorageWorker = testbed.data.workers[source_storage_worker_id]
            source_storage_worker.stop()

    @Slot()
    def on_start_stop_clicked(self):
        if self.source is None:
            message_dialog = MessageDialog("Devices not selected", "Source device not selected.", icon=QMessageBox.Icon.Information, buttons=QMessageBox.StandardButton.Ok)
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

            if process_worker_id in testbed.data.workers:  # an update worker is in progress
                process_worker: ProcessWorker = testbed.data.workers[process_worker_id]
                process_worker.stop()
                testbed.data.workers.pop(process_worker_id)

                self.controls_widget.play_pause_button.setIconHint(QIcon(ICON_RUN), "Run")
                self.controls_widget.progressbar.setMaximum(100)
                self.controls_widget.progressbar.reset()
                self.controls_widget.progressbar.updateProgress()

                return

            self.controls_widget.progressbar.setMaximum(self.settings_widget.exposure_times_array.size)

            process_worker = ProcessWorker(self.source, self.settings_widget.exposure_times_array)
            process_worker.signals.progressTicked.connect(self.on_progress_tick)
            process_worker.signals.finished.connect(self.on_process_finished)

            self.controls_widget.play_pause_button.setIconHint(QIcon(ICON_PAUSE), "Pause")

            timestamp = timestamp_string(frmt="%Y%m%d.%H%M%S", ms=None)
            source_storage_worker = SourceStorageWorker(f"data/output/{timestamp}_{_PROCESS_}_{self.source.name}.raw", self.settings_widget.exposure_times_array.size)
            process_worker.signals.srcSampled.connect(source_storage_worker.on_sampled)

            source_storage_worker.signals.finished.connect(self.on_source_storage_finished)

            source_preview_window_id = f"{self.source.name}_preview_window"
            if source_preview_window_id in testbed.data.windows:
                source_preview_window: CameraPreviewWindow = testbed.data.windows[source_preview_window_id]
                process_worker.signals.srcSampled.connect(source_preview_window.on_sampled)

            testbed.data.workers[source_storage_worker_id] = source_storage_worker
            testbed.data.threadpool.start(source_storage_worker)

            testbed.data.workers[process_worker_id] = process_worker
            testbed.data.threadpool.start(process_worker)

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
