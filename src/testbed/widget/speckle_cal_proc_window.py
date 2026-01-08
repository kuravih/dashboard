import numpy as np
import pickle
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QVBoxLayout, QWidget, QLabel, QGridLayout, QDoubleSpinBox
from PySide6.QtCore import Slot, Qt

from pykato.log import setup_logger
from pykato.function import timestamp_string

import testbed
from ..device.camera import Camera
from .camera_window import PreviewWindow as CameraPreviewWindow, InfoWindow as CameraInfoWindow, SettingsWindow as CameraSettingsWindow

from ..device.modulator import Modulator
from .modulator_window import PreviewWindow as ModulatorPreviewWindow, InfoWindow as ModulatorInfoWindow, SettingsWindow as ModulatorSettingsWindow

from ..device.mirror import Mirror
from .mirror_window import PreviewWindow as MirrorPreviewWindow, InfoWindow as MirrorInfoWindow, SettingsWindow as MirrorSettingsWindow

from ..worker.speckle_cal_proc_worker import SpeckleCalProcWorker
from ..worker.storage_worker import SinkStorageWorker, SourceStorageWorker

from ..widget import DevicesSetupWidget, TaskControlsWidget
from ..widget.resource import ICON_RUN, ICON_PAUSE
from ..widget import LinspaceWidget

logger = setup_logger("speckle_cal_proc_window", terminator="\n")


class SpeckleCalProcSettingsWidget(QWidget):
    """
    Speckle Calibration Process Window
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


class SpeckleCalProcWindow(QWidget):
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
    def sink(self) -> Modulator | Mirror | None:
        return self._sink

    def on_source_change(self, _device: Camera):
        self.devices_widget.source_info_button.setEnabled(True)
        self.devices_widget.source_settings_button.setEnabled(True)
        self.devices_widget.source_preview_button.setEnabled(True)
        self._source = _device
        self.open_preview_window(_device)
        self.devices_widget.source_info_button.clicked.connect(lambda _, _device=_device: self.open_info_window(_device))
        self.devices_widget.source_settings_button.clicked.connect(lambda _, _device=_device: self.open_settings_window(_device))
        self.devices_widget.source_preview_button.clicked.connect(lambda _, _device=_device: self.open_preview_window(_device))

    def on_sink_change(self, _device: Modulator | Mirror):
        self.devices_widget.sink_info_button.setEnabled(True)
        self.devices_widget.sink_settings_button.setEnabled(True)
        self.devices_widget.sink_preview_button.setEnabled(True)
        self._sink = _device
        self.open_preview_window(_device)
        self.devices_widget.sink_info_button.clicked.connect(lambda _, _device=_device: self.open_info_window(_device))
        self.devices_widget.sink_settings_button.clicked.connect(lambda _, _device=_device: self.open_settings_window(_device))
        self.devices_widget.sink_preview_button.clicked.connect(lambda _, _device=_device: self.open_preview_window(_device))

    def open_info_window(self, _device: Camera | Modulator | Mirror):

        window_name = _device.name + "_info"

        @Slot()
        def close_window():
            testbed.data.windows.pop(window_name, None)

        if window_name not in testbed.data.windows:
            window: CameraInfoWindow | ModulatorInfoWindow | MirrorInfoWindow | None = None
            if isinstance(_device, Camera):
                window = CameraInfoWindow(_device)
            elif isinstance(_device, Modulator):
                window = ModulatorInfoWindow(_device)
            elif isinstance(_device, Mirror):
                window = MirrorInfoWindow(_device)
            else:
                raise ValueError("Invalid device")
            window.destroyed.connect(close_window)
            window.show()
            window.raise_()
            window.activateWindow()
            testbed.data.windows[window_name] = window

    def open_settings_window(self, _device: Camera | Modulator | Mirror):

        window_name = _device.name + "_settings"

        @Slot()
        def close_window():
            testbed.data.windows.pop(window_name, None)

        if window_name not in testbed.data.windows:
            window: CameraSettingsWindow | ModulatorSettingsWindow | MirrorSettingsWindow | None = None
            if isinstance(_device, Camera):
                window = CameraSettingsWindow(_device)
            elif isinstance(_device, Modulator):
                window = ModulatorSettingsWindow(_device)
            elif isinstance(_device, Mirror):
                window = MirrorSettingsWindow(_device)
            else:
                raise ValueError("Invalid device")
            window.destroyed.connect(close_window)
            window.show()
            window.raise_()
            window.activateWindow()
            testbed.data.windows[window_name] = window

    def open_preview_window(self, _device: Camera | Modulator | Mirror):

        window_name = _device.name + "_preview"

        @Slot()
        def close_window():
            testbed.data.windows.pop(window_name, None)

        if window_name not in testbed.data.windows:
            window: CameraPreviewWindow | ModulatorPreviewWindow | MirrorPreviewWindow | None = None
            if isinstance(_device, Camera):
                window = CameraPreviewWindow(_device)
            elif isinstance(_device, Modulator):
                window = ModulatorPreviewWindow(_device)
            elif isinstance(_device, Mirror):
                window = MirrorPreviewWindow(_device)
            else:
                raise ValueError("Invalid device")
            window.destroyed.connect(close_window)
            window.show()
            window.raise_()
            window.activateWindow()
            testbed.data.windows[window_name] = window

    @Slot(int, float)  # step, elapsed_time
    def on_progress(self, step: int, t_elapsed: float):
        self.controls_widget.progressbar.setValue(step + 1)
        self.controls_widget.progressbar.setTime(t_elapsed)
        self.controls_widget.progressbar.updateProgress()

    @Slot()
    def on_finish(self):
        proc_worker_id = "speckle_cal_proc_worker"
        self.controls_widget.progressbar.reset()
        self.controls_widget.progressbar.updateProgress()
        if proc_worker_id in testbed.data.workers:  # an update worker is in progress
            current_proc_worker = testbed.data.workers.pop(proc_worker_id)
            current_proc_worker.stop()
            self.controls_widget.play_pause_button.setIcon(QIcon(ICON_RUN))

    @Slot()
    def on_source_storage_finish(self):
        source_storage_worker_id = "speckle_cal_proc_source_storage_worker"
        if source_storage_worker_id in testbed.data.workers:
            source_storage_worker = testbed.data.workers.pop(source_storage_worker_id)
            source_storage_worker.stop()

    @Slot()
    def on_sink_storage_finish(self):
        sink_storage_worker_id = "speckle_cal_proc_sink_storage_worker"
        if sink_storage_worker_id in testbed.data.workers:
            sink_storage_worker = testbed.data.workers.pop(sink_storage_worker_id)
            sink_storage_worker.stop()

    @Slot()
    def on_start_stop(self):
        proc_worker_id = "speckle_cal_proc_worker"
        source_storage_worker_id = "speckle_cal_proc_source_storage_worker"
        sink_storage_worker_id = "speckle_cal_proc_sink_storage_worker"
        source_preview_window_name = self.source.name + "_preview"
        sink_preview_window_name = self.sink.name + "_preview"

        if proc_worker_id in testbed.data.workers:  # an update worker is in progress
            logger.info("stopping running process")
            current_proc_worker = testbed.data.workers.pop(proc_worker_id)
            current_proc_worker.stop()
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

        proc_worker = SpeckleCalProcWorker(self.source, self.sink, self.settings_widget.amplitude, self.settings_widget.freqs_array, self.settings_widget.angles_array, self.settings_widget.phases_array)
        proc_worker.signals.progress.connect(self.on_progress)
        proc_worker.signals.finish.connect(self.on_finish)

        timestamp = timestamp_string(frmt="%Y%m%d.%H%M%S", ms=None)

        source_storage_worker = SourceStorageWorker(f"data/output/{timestamp}_speckle_cal_source.raw", self.settings_widget.n_steps)
        proc_worker.signals.new_source_sample.connect(source_storage_worker.on_sample)
        testbed.data.threadpool.start(source_storage_worker)
        testbed.data.workers[source_storage_worker_id] = source_storage_worker
        source_storage_worker.signals.finish.connect(self.on_source_storage_finish)

        sink_storage_worker = SinkStorageWorker(f"data/output/{timestamp}_speckle_cal_sink.raw", self.settings_widget.n_steps)
        proc_worker.signals.new_sink_sample.connect(sink_storage_worker.on_sample)
        testbed.data.threadpool.start(sink_storage_worker)
        testbed.data.workers[sink_storage_worker_id] = sink_storage_worker
        sink_storage_worker.signals.finish.connect(self.on_sink_storage_finish)

        with open(f"data/output/{timestamp}_speckle_cal_parameters.pkl", "wb") as _file:
            parameters_dict = {"amplitudes": self.settings_widget.amplitude, "frequencies": self.settings_widget.freqs_array, "angles": self.settings_widget.angles_array, "phases": self.settings_widget.phases_array}
            pickle.dump(parameters_dict, _file, protocol=pickle.HIGHEST_PROTOCOL)

        testbed.data.threadpool.start(proc_worker)

        self.controls_widget.play_pause_button.setIcon(QIcon(ICON_PAUSE))
        self.devices_widget.sink_settings_button.setEnabled(False)
        self.devices_widget.source_settings_button.setEnabled(False)

        if source_preview_window_name in testbed.data.windows:
            proc_worker.signals.new_source_sample.connect(testbed.data.windows[source_preview_window_name].on_new_sample)
        if sink_preview_window_name in testbed.data.windows:
            proc_worker.signals.new_sink_sample.connect(testbed.data.windows[sink_preview_window_name].on_new_sample)

        testbed.data.workers[proc_worker_id] = proc_worker

    def setup_main_widget(self) -> QWidget:
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        widget.setLayout(layout)

        self.devices_widget = DevicesSetupWidget(testbed.data.devices, parent=self)
        self.devices_widget.source_change.connect(self.on_source_change)
        self.devices_widget.sink_change.connect(self.on_sink_change)

        self.settings_widget = SpeckleCalProcSettingsWidget(self)
        # self.settings_widget.hide()

        self.controls_widget = TaskControlsWidget(self)
        self.controls_widget.play_pause_button.clicked.connect(self.on_start_stop)
        # self.controls_widget.hide()

        layout.addWidget(self.devices_widget)
        layout.addWidget(self.settings_widget)
        layout.addWidget(self.controls_widget)
        layout.addStretch(5)

        return widget

    def closeEvent(self, event):
        if self.source is not None:
            source_preview_window_name = self.source.name + "_preview"
            if source_preview_window_name in testbed.data.windows:
                logger.info("Cannot close main window until preview windows are closed.")
                event.ignore()
                return

        if self.sink is not None:
            sink_preview_window_name = self.sink.name + "_preview"
            if sink_preview_window_name in testbed.data.windows:
                logger.info("Cannot close main window until preview windows are closed.")
                event.ignore()
                return

        while testbed.data.workers:
            key, worker = testbed.data.workers.popitem()
            worker.stop()
            logger.info("stopping worker %s", key)
        self.deleteLater()
        event.accept()
