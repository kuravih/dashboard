import numpy as np
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QFileDialog, QMessageBox, QVBoxLayout, QWidget, QLabel, QSpinBox, QHBoxLayout, QCheckBox, QGridLayout, QLineEdit, QPushButton
from PySide6.QtCore import Slot, Qt, QFileInfo
import pickle

from pykato.log import setup_logger
from pykato.function import timestamp_string, chord

import testbed
from ..device.camera import Camera
from .camera_window import PreviewWindow as CameraPreviewWindow, InfoWindow as CameraInfoWindow, SettingsWindow as CameraSettingsWindow

from ..device.modulator import Modulator
from .modulator_window import PreviewWindow as ModulatorPreviewWindow, InfoWindow as ModulatorInfoWindow, SettingsWindow as ModulatorSettingsWindow

from ..device.mirror import Mirror
from .mirror_window import PreviewWindow as MirrorPreviewWindow, InfoWindow as MirrorInfoWindow, SettingsWindow as MirrorSettingsWindow

from ..worker.speckle_null_proc_worker import SpeckleNullProcWorker
from ..worker.storage_worker import SinkStorageWorker, SourceStorageWorker

from ..widget import DevicesSetupWidget, TaskControlsWidget, Window
from ..widget.resource import ICON_RUN, ICON_PAUSE, ICON_FOLDER, ICON_BACKSPACE
from ..widget import LinspaceWidget
from ..widget.dialog import MessageDialog

from ..function import is_speckle_calibration_file_valid

logger = setup_logger("speckle_null_proc_window", terminator="\n")


class SpeckleNullProcSettingsWidget(QWidget):
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
        def on_continuous_checkbox_toggle(checked: bool):
            if checked:
                self._n_iterations_spinbox.setEnabled(False)
            else:
                self._n_iterations_spinbox.setEnabled(True)

        self._continuous_checkbox.toggled.connect(on_continuous_checkbox_toggle)

        self.speck_calibration = None

        # ---- speckle_cal_paramters file -----------------------------------------------------------------------------
        speck_cal_label = QLabel("Speckle Calibration", self)
        speck_cal_label.setFixedWidth(100)

        self.speck_cal_lineedit = QLineEdit(self)
        self.speck_cal_lineedit.setEnabled(False)
        self.speck_cal_lineedit.setText("")
        self.speck_cal_lineedit.setToolTip("Speckle calibration file")
        self.speck_cal_browse_button = QPushButton("", self)
        self.speck_cal_browse_button.setFixedWidth(self.speck_cal_browse_button.sizeHint().height())
        self.speck_cal_browse_button.setIcon(QIcon(ICON_FOLDER))
        self.speck_cal_browse_button.setToolTip("Open calibration file")

        self.speck_cal_clear_button = QPushButton("", self)
        self.speck_cal_clear_button.setIcon(QIcon(ICON_BACKSPACE))
        self.speck_cal_clear_button.setToolTip("Remove calibration file")

        self.speck_cal_clear_button.hide()
        # ---- speckle cal file ---------------------------------------------------------------------------------------

        @Slot()
        def speck_cal_browse_button_clicked():
            dialog_filename, _ = QFileDialog.getOpenFileName(self, "Open Calibration File", "./data/output", "Pickle file (*.pkl)", options=QFileDialog.Option.DontUseNativeDialog | QFileDialog.Option.ReadOnly)
            if dialog_filename:
                speck_cal_file_info = QFileInfo(dialog_filename)
                speck_cal_filename = speck_cal_file_info.fileName()
                speck_cal_filepath = f"{speck_cal_file_info.absolutePath()}/{speck_cal_filename}"
                if is_speckle_calibration_file_valid(speck_cal_filepath):
                    self.speck_cal_lineedit.setText(speck_cal_filename)
                    with open(speck_cal_filepath, "rb") as _input:
                        self.speck_calibration = pickle.load(_input)
                    self.speck_cal_browse_button.hide()
                    self.speck_cal_clear_button.show()
                else:
                    message_dialog = MessageDialog("Invalid Calibration", "Calibration file invalid.", icon=QMessageBox.Icon.Information, buttons=QMessageBox.StandardButton.Ok)
                    message_dialog.exec()

        self.speck_cal_browse_button.clicked.connect(speck_cal_browse_button_clicked)

        @Slot()
        def speck_cal_clear_button_clicked():
            self.speck_calibration = None
            self.speck_cal_lineedit.setText("")
            self.speck_cal_browse_button.show()
            self.speck_cal_clear_button.hide()

        self.speck_cal_clear_button.clicked.connect(speck_cal_clear_button_clicked)

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
        widget_layout.addWidget(speck_cal_label, row, col)
        col += 1
        widget_layout.addWidget(self.speck_cal_lineedit, row, col)
        col += 1
        widget_layout.addWidget(self.speck_cal_browse_button, row, col)
        widget_layout.addWidget(self.speck_cal_clear_button, row, col)

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


class SpeckleNullProcWindow(Window):
    """
    Speckle Nulling Process Window
    """

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Dialog)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setWindowTitle("Speckle Nulling Process")
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

    @Slot()
    def on_source_change(self, _device: Camera):
        self.devices_widget.source_info_button.setEnabled(True)
        self.devices_widget.source_settings_button.setEnabled(True)
        self.devices_widget.source_preview_button.setEnabled(True)
        self._source = _device
        self.open_preview_window(_device)
        self.devices_widget.source_info_button.clicked.connect(lambda _, _device=_device: self.open_info_window(_device))
        self.devices_widget.source_settings_button.clicked.connect(lambda _, _device=_device: self.open_settings_window(_device))
        self.devices_widget.source_preview_button.clicked.connect(lambda _, _device=_device: self.open_preview_window(_device))

    @Slot()
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
        proc_worker_id = "speckle_null_proc_worker"
        self.controls_widget.progressbar.reset()
        self.controls_widget.progressbar.updateProgress()
        if proc_worker_id in testbed.data.workers:  # an update worker is in progress
            current_proc_worker = testbed.data.workers.pop(proc_worker_id)
            current_proc_worker.stop()
            self.controls_widget.play_pause_button.setIcon(QIcon(ICON_RUN))

    @Slot()
    def on_source_storage_finish(self):
        source_storage_worker_id = "speckle_null_proc_source_storage_worker"
        if source_storage_worker_id in testbed.data.workers:
            source_storage_worker = testbed.data.workers.pop(source_storage_worker_id)
            source_storage_worker.stop()

    @Slot()
    def on_sink_storage_finish(self):
        sink_storage_worker_id = "speckle_null_proc_sink_storage_worker"
        if sink_storage_worker_id in testbed.data.workers:
            sink_storage_worker = testbed.data.workers.pop(sink_storage_worker_id)
            sink_storage_worker.stop()

    @Slot()
    def on_start_stop(self):
        proc_worker_id = "speckle_null_proc_worker"
        source_storage_worker_id = "speckle_null_proc_source_storage_worker"
        sink_storage_worker_id = "speckle_null_proc_sink_storage_worker"
        source_preview_window_name = self.source.name + "_preview"
        sink_preview_window_name = self.sink.name + "_preview"

        if proc_worker_id in testbed.data.workers:  # an update worker is in progress
            current_proc_worker = testbed.data.workers.pop(proc_worker_id)
            current_proc_worker.stop()
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

        dark_hole_mask = chord(self.source.shape, 125, -0.25, np.pi / 2, center=(-self.source.shape[0] / 2, -self.source.shape[1] / 2)).astype(bool)
        speckle_mask = np.zeros_like(dark_hole_mask, dtype=bool)

        proc_worker = SpeckleNullProcWorker(self.source, self.sink, speckle_mask, self.settings_widget.speck_calibration, self.settings_widget.phs_array, self.settings_widget.amp_array, self.settings_widget.n_iterations)
        proc_worker.signals.progress.connect(self.on_progress)
        proc_worker.signals.finished.connect(self.on_finish)

        timestamp = timestamp_string(frmt="%Y%m%d.%H%M%S", ms=None)

        if self.settings_widget.record_source:
            source_storage_worker = SourceStorageWorker(f"data/output/{timestamp}_speckle_null_source.raw", self.settings_widget.n_iterations)
            proc_worker.signals.new_source_sample.connect(source_storage_worker.on_sample)
            source_storage_worker.signals.finished.connect(self.on_source_storage_finish)
            testbed.data.workers[source_storage_worker_id] = source_storage_worker
            testbed.data.threadpool.start(source_storage_worker)

        if self.settings_widget.record_sink:
            sink_storage_worker = SinkStorageWorker(f"data/output/{timestamp}_speckle_null_sink.raw", self.settings_widget.n_iterations)
            proc_worker.signals.new_sink_sample.connect(sink_storage_worker.on_sample)
            sink_storage_worker.signals.finished.connect(self.on_sink_storage_finish)
            testbed.data.workers[sink_storage_worker_id] = sink_storage_worker
            testbed.data.threadpool.start(sink_storage_worker)

        self.controls_widget.play_pause_button.setIcon(QIcon(ICON_PAUSE))
        self.devices_widget.sink_settings_button.setEnabled(False)
        self.devices_widget.source_settings_button.setEnabled(False)

        if source_preview_window_name in testbed.data.windows:
            proc_worker.signals.new_source_sample.connect(testbed.data.windows[source_preview_window_name].on_new_sample)
        if sink_preview_window_name in testbed.data.windows:
            proc_worker.signals.new_sink_sample.connect(testbed.data.windows[sink_preview_window_name].on_new_sample)

        testbed.data.workers[proc_worker_id] = proc_worker
        testbed.data.threadpool.start(proc_worker)

    def setup_main_widget(self) -> QWidget:
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        widget.setLayout(layout)

        self.devices_widget = DevicesSetupWidget(testbed.data.devices, parent=self)
        self.devices_widget.source_change.connect(self.on_source_change)
        self.devices_widget.sink_change.connect(self.on_sink_change)

        self.settings_widget = SpeckleNullProcSettingsWidget(self)
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
