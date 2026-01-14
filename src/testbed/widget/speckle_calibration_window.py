import pickle

import numpy as np
from pykato.function import timestamp_string
from pykato.log import setup_logger
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDoubleSpinBox, QGridLayout, QLabel, QVBoxLayout, QWidget

import testbed

from ..device.camera import Camera
from ..device.modulator import Modulator
from ..worker.speckle_calibration_worker import ProcessWorker
from ..worker.storage_worker import SinkStorageWorker, SourceStorageWorker
from . import DevicesSetupWidget, LinspaceWidget, TaskControlsWidget, Window
from .camera_window import InfoWindow as CameraInfoWindow
from .camera_window import PreviewWindow as CameraPreviewWindow
from .camera_window import SettingsWindow as CameraSettingsWindow
from .modulator_window import InfoWindow as ModulatorInfoWindow
from .modulator_window import PreviewWindow as ModulatorPreviewWindow
from .modulator_window import SettingsWindow as ModulatorSettingsWindow
from .resource import ICON_PAUSE, ICON_RUN

_PROCESS_ = testbed.SPECKLE_CALIBRATION

logger = setup_logger(f"{_PROCESS_}_window", terminator="\n")


class ProcessSettingsWidget(QWidget):
    """
    Speckle Calibration Process Settings
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        ampl_label = QLabel("Amplitude", self)
        ampl_label.setFixedWidth(100)

        self._ampl_spinbox = QDoubleSpinBox(self)
        self._ampl_spinbox.setRange(0, 0.5)
        self._ampl_spinbox.setValue(0.25)

        angle_label = QLabel("Angle Steps", self)
        angle_label.setFixedWidth(100)

        self._angle_steps = LinspaceWidget(0, 170, 18, self)

        freq_label = QLabel("Frequency Steps", self)
        freq_label.setFixedWidth(100)

        self._freq_steps = LinspaceWidget(0.06, 0.01, 11, self)

        phase_label = QLabel("Phase Steps", self)
        phase_label.setFixedWidth(100)

        self._phase_steps = LinspaceWidget(0, 180, 2, self)

        widget_layout = QGridLayout()

        row = 0
        col = 0
        widget_layout.addWidget(ampl_label, row, col)
        col += 1
        widget_layout.addWidget(self._ampl_spinbox, row, col)

        row += 1
        col = 0
        widget_layout.addWidget(angle_label, row, col)
        col += 1
        widget_layout.addWidget(self._angle_steps, row, col)

        row += 1
        col = 0
        widget_layout.addWidget(freq_label, row, col)
        col += 1
        widget_layout.addWidget(self._freq_steps, row, col)

        row += 1
        col = 0
        widget_layout.addWidget(phase_label, row, col)
        col += 1
        widget_layout.addWidget(self._phase_steps, row, col)

        self.setLayout(widget_layout)

    @property
    def amplitude(self) -> float:
        return self._ampl_spinbox.value()

    @property
    def angles_array(self) -> np.ndarray:
        return self._angle_steps.value()

    @property
    def freqs_array(self) -> np.ndarray:
        return self._freq_steps.value()

    @property
    def phases_array(self) -> np.ndarray:
        return self._phase_steps.value()

    @property
    def n_steps(self) -> int:
        return self.angles_array.size * self.freqs_array.size * self.phases_array.size + 1  # include blank


class ProcessWindow(Window):
    """
    Speckle Calibration Process Window
    """

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Dialog)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setWindowTitle("Speckle Calibration")
        self._sink = None
        self._source = None

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
        preview_window_id = f"{_device.name}_preview_window"
        if preview_window_id in testbed.data.windows:
            testbed.data.windows.pop(preview_window_id).close()
        info_window_id = f"{_device.name}_info_window"
        if info_window_id in testbed.data.windows:
            testbed.data.windows.pop(info_window_id).close()
        settings_window_id = f"{_device.name}_settings_window"
        if settings_window_id in testbed.data.windows:
            testbed.data.windows.pop(settings_window_id).close()
        self.devices_widget.source_info_button.clicked.connect(lambda _, _device=_device: self.open_device_info_window(_device))
        self.devices_widget.source_settings_button.clicked.connect(lambda _, _device=_device: self.open_device_settings_window(_device))
        self.devices_widget.source_preview_button.clicked.connect(lambda _, _device=_device: self.open_device_preview_window(_device))
        if self._source is not None and self._sink is not None:
            self.controls_widget.preview_button.setEnabled(True)
            self.controls_widget.play_pause_button.setEnabled(True)

    def on_sink_changed(self, _device: Modulator):
        self.devices_widget.sink_info_button.setEnabled(True)
        self.devices_widget.sink_settings_button.setEnabled(True)
        self.devices_widget.sink_preview_button.setEnabled(True)
        self._sink = _device
        preview_window_id = f"{_device.name}_preview_window"
        if preview_window_id in testbed.data.windows:
            testbed.data.windows.pop(preview_window_id).close()
        info_window_id = f"{_device.name}_info_window"
        if info_window_id in testbed.data.windows:
            testbed.data.windows.pop(info_window_id).close()
        settings_window_id = f"{_device.name}_settings_window"
        if settings_window_id in testbed.data.windows:
            testbed.data.windows.pop(settings_window_id).close()
        self.devices_widget.sink_info_button.clicked.connect(lambda _, _device=_device: self.open_device_info_window(_device))
        self.devices_widget.sink_settings_button.clicked.connect(lambda _, _device=_device: self.open_device_settings_window(_device))
        self.devices_widget.sink_preview_button.clicked.connect(lambda _, _device=_device: self.open_device_preview_window(_device))
        if self._source is not None and self._sink is not None:
            self.controls_widget.preview_button.setEnabled(True)
            self.controls_widget.play_pause_button.setEnabled(True)

    def open_device_info_window(self, _device: Camera | Modulator):
        info_window_id = f"{_device.name}_info_window"

        @Slot()
        def on_window_closed():
            testbed.data.windows.pop(info_window_id, None)

        if info_window_id not in testbed.data.windows:
            info_window: CameraInfoWindow | ModulatorInfoWindow | None = None
            if isinstance(_device, Camera):
                info_window = CameraInfoWindow(_device, self)
            elif isinstance(_device, Modulator):
                info_window = ModulatorInfoWindow(_device, self)
            else:
                raise ValueError("Invalid device")
            info_window.destroyed.connect(on_window_closed)
            info_window.show()
            info_window.raise_()
            info_window.activateWindow()
            testbed.data.windows[info_window_id] = info_window

    def open_device_settings_window(self, _device: Camera | Modulator):
        settings_window_id = f"{_device.name}_settings_window"

        @Slot()
        def on_window_closed():
            testbed.data.windows.pop(settings_window_id, None)

        if settings_window_id not in testbed.data.windows:
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
            testbed.data.windows[settings_window_id] = settings_window

    def open_device_preview_window(self, _device: Camera | Modulator):
        preview_window_id = f"{_device.name}_preview_window"

        @Slot()
        def on_window_closed():
            testbed.data.windows.pop(preview_window_id, None)

        if preview_window_id not in testbed.data.windows:
            preview_window: CameraPreviewWindow | ModulatorPreviewWindow | None = None
            if isinstance(_device, Camera):
                preview_window = CameraPreviewWindow(_device, self)
            elif isinstance(_device, Modulator):
                preview_window = ModulatorPreviewWindow(_device, self)
            else:
                raise ValueError("Invalid device")
            preview_window.destroyed.connect(on_window_closed)
            preview_window.show()
            preview_window.raise_()
            preview_window.activateWindow()
            testbed.data.windows[preview_window_id] = preview_window

    @Slot(int, float)  # step, elapsed_time
    def on_progress_tick(self, step: int, t_elapsed: float):
        self.controls_widget.progressbar.setValue(step + 1)
        self.controls_widget.progressbar.setTime(t_elapsed)
        self.controls_widget.progressbar.updateProgress()

    @Slot()
    def on_finished(self):
        worker_id = f"{_PROCESS_}_worker"
        self.controls_widget.progressbar.reset()
        self.controls_widget.progressbar.updateProgress()
        if worker_id in testbed.data.workers:  # an update worker is in progress
            current_worker = testbed.data.workers.pop(worker_id)
            current_worker.stop()
            self.controls_widget.play_pause_button.setIcon(QIcon(ICON_RUN))

    @Slot()
    def on_source_storage_finished(self):
        source_storage_worker_id = f"{_PROCESS_}_source_storage_worker"
        if source_storage_worker_id in testbed.data.workers:
            source_storage_worker = testbed.data.workers.pop(source_storage_worker_id)
            source_storage_worker.stop()

    @Slot()
    def on_sink_storage_finished(self):
        sink_storage_worker_id = f"{_PROCESS_}_sink_storage_worker"
        if sink_storage_worker_id in testbed.data.workers:
            sink_storage_worker = testbed.data.workers.pop(sink_storage_worker_id)
            sink_storage_worker.stop()

    @Slot()
    def on_start_stop_clicked(self):
        worker_id = f"{_PROCESS_}_worker"
        source_storage_worker_id = f"{_PROCESS_}_source_storage_worker"
        sink_storage_worker_id = f"{_PROCESS_}_sink_storage_worker"
        source_preview_window_id = f"{self.source.name}_preview_window"
        sink_preview_window_id = f"{self.sink.name}_preview_window"

        if worker_id in testbed.data.workers:  # an update worker is in progress
            logger.info("stopping running process")
            current_worker = testbed.data.workers.pop(worker_id)
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

        self.controls_widget.progressbar.setMaximum(self.settings_widget.n_steps)

        worker = ProcessWorker(self.source, self.sink, self.settings_widget.amplitude, self.settings_widget.freqs_array, self.settings_widget.angles_array, self.settings_widget.phases_array)
        worker.signals.progressTicked.connect(self.on_progress_tick)
        worker.signals.finished.connect(self.on_finished)

        timestamp = timestamp_string(frmt="%Y%m%d.%H%M%S", ms=None)

        source_storage_worker = SourceStorageWorker(f"data/output/{timestamp}_{_PROCESS_}_source.raw", self.settings_widget.n_steps)
        worker.signals.sourceSampled.connect(source_storage_worker.on_sampled)
        source_storage_worker.signals.finished.connect(self.on_source_storage_finished)
        testbed.data.workers[source_storage_worker_id] = source_storage_worker
        testbed.data.threadpool.start(source_storage_worker)

        sink_storage_worker = SinkStorageWorker(f"data/output/{timestamp}_{_PROCESS_}_sink.raw", self.settings_widget.n_steps)
        worker.signals.sinkSampled.connect(sink_storage_worker.on_sampled)
        sink_storage_worker.signals.finished.connect(self.on_sink_storage_finished)
        testbed.data.workers[sink_storage_worker_id] = sink_storage_worker
        testbed.data.threadpool.start(sink_storage_worker)

        with open(f"data/output/{timestamp}_{_PROCESS_}_parameters.pkl", "wb") as _file:
            parameters_dict = {"amplitudes": self.settings_widget.amplitude, "frequencies": self.settings_widget.freqs_array, "angles": self.settings_widget.angles_array, "phases": self.settings_widget.phases_array}
            pickle.dump(parameters_dict, _file, protocol=pickle.HIGHEST_PROTOCOL)

        self.controls_widget.play_pause_button.setIcon(QIcon(ICON_PAUSE))
        self.devices_widget.sink_settings_button.setEnabled(False)
        self.devices_widget.source_settings_button.setEnabled(False)

        if source_preview_window_id in testbed.data.windows:
            worker.signals.sourceSampled.connect(testbed.data.windows[source_preview_window_id].on_sampled)
        if sink_preview_window_id in testbed.data.windows:
            worker.signals.sinkSampled.connect(testbed.data.windows[sink_preview_window_id].on_sampled)

        testbed.data.workers[worker_id] = worker
        testbed.data.threadpool.start(worker)

    def setup_main_widget(self) -> QWidget:
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        widget.setLayout(layout)

        self.devices_widget = DevicesSetupWidget(testbed.data.devices, parent=self)
        self.devices_widget.sourceChanged.connect(self.on_source_changed)
        self.devices_widget.sinkChanged.connect(self.on_sink_changed)

        self.settings_widget = ProcessSettingsWidget(self)

        self.controls_widget = TaskControlsWidget(self)
        self.controls_widget.play_pause_button.setEnabled(False)
        self.controls_widget.play_pause_button.clicked.connect(self.on_start_stop_clicked)
        self.controls_widget.preview_button.hide()
        self.controls_widget.info_button.hide()

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
