import numpy as np
import pickle
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QFileDialog, QMessageBox, QVBoxLayout, QWidget, QLabel, QSpinBox, QHBoxLayout, QCheckBox, QGridLayout, QLineEdit, QPushButton
from PySide6.QtCore import Slot, Qt, QFileInfo, QTimer, Signal

from pykato.log import setup_logger
from pykato.function import timestamp_string, chord

import testbed
from ..device.camera import Camera
from .camera_window import PreviewWindow as CameraPreviewWindow, InfoWindow as CameraInfoWindow, SettingsWindow as CameraSettingsWindow

from ..device.modulator import Modulator
from .modulator_window import PreviewWindow as ModulatorPreviewWindow, InfoWindow as ModulatorInfoWindow, SettingsWindow as ModulatorSettingsWindow

from ..worker.speckle_nulling_worker import MainWorker
from ..worker.storage_worker import SinkStorageWorker, SourceStorageWorker

from . import DevicesSetupWidget, TaskControlsWidget, Window
from .resource import ICON_RUN, ICON_PAUSE, ICON_FOLDER, ICON_BACKSPACE
from . import LinspaceWidget
from .dialog import MessageDialog
from .figure_widget import ContrastFigureWidget

from ..function import is_speckle_calibration_file_valid

_PROCESS_ = testbed.SPECKLE_NULLING

logger = setup_logger(f"{_PROCESS_}_window", terminator="\n")


class MainSettingsWidget(QWidget):
    """
    Speckle Nulling Process Settings
    """

    calibration_changed = Signal()

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

        self.dark_hole_mask = None

        self.speckle_calibration = None

        # ---- speckle calibration file -------------------------------------------------------------------------------
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
        self.speck_cal_clear_button.setFixedWidth(self.speck_cal_clear_button.sizeHint().height())
        self.speck_cal_clear_button.setToolTip("Remove calibration file")

        self.speck_cal_clear_button.hide()
        # ---- speckle calibration file -------------------------------------------------------------------------------

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
                        self.speckle_calibration = pickle.load(_input)
                    self.speck_cal_browse_button.hide()
                    self.speck_cal_clear_button.show()
                else:
                    message_dialog = MessageDialog("Invalid Calibration", "Calibration file invalid.", icon=QMessageBox.Icon.Information, buttons=QMessageBox.StandardButton.Ok)
                    message_dialog.exec()
                self.calibration_changed.emit()

        self.speck_cal_browse_button.clicked.connect(speck_cal_browse_button_clicked)

        @Slot()
        def speck_cal_clear_button_clicked():
            self.speckle_calibration = None
            self.speck_cal_lineedit.setText("")
            self.speck_cal_browse_button.show()
            self.speck_cal_clear_button.hide()
            self.calibration_changed.emit()

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


class SpeckleNullProcContrastWindow(Window):
    """
    Speckle Nulling Contrast Window
    """

    def __init__(self, source: Camera, sink: Modulator, mask: np.ndarray, parent: QWidget | None = None):
        super().__init__(parent, Qt.WindowType.Dialog)
        self._source = source
        self._sink = sink

        self._measurement = np.zeros_like(mask)
        self._mask = mask

        self.setWindowTitle("Speckle Nulling Contrast")

        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self.setup_preview_widget())
        self.setLayout(layout)

        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.on_update_window)
        self.update_timer.start(100)  # Update window every 100 ms

    @Slot(np.ndarray)
    def on_measurement(self, _measurement: np.ndarray):
        self._measurement = _measurement

    @Slot(float, float)
    def on_speckle_location(self, speckle_location_x: float, speckle_location_y: float):
        self.preview_figure_widget.figure.get_imshow_ax().axvline(speckle_location_x, alpha=0.5, linewidth=0.5, color="red")
        self.preview_figure_widget.figure.get_imshow_ax().axhline(speckle_location_y, alpha=0.5, linewidth=0.5, color="red")

    @Slot(float, float)
    def on_speckle_parameters(self, frequency: float, angle: float):
        logger.info("frequency = %f, angle = %f", frequency, np.rad2deg(angle))

    @property
    def measurement(self) -> np.ndarray:
        return self._measurement

    def setup_preview_widget(self) -> QWidget:
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(2, 2, 2, 2)
        widget.setLayout(layout)

        self.preview_figure_widget = ContrastFigureWidget(self.measurement, self._mask, True, self)

        layout.addWidget(self.preview_figure_widget)

        return widget

    @Slot()
    def on_update_window(self):
        self.preview_figure_widget.figure.get_image().set_data(self.measurement)
        self.preview_figure_widget.figure.canvas.draw_idle()

    def closeEvent(self, event):
        if self.update_timer.isActive():
            self.update_timer.stop()
        self.deleteLater()
        event.accept()




class SpeckleNullProcMoreWindow(Window):
    """
    Speckle Nulling Contrast Window
    """

    def __init__(self, source: Camera, sink: Modulator, mask: np.ndarray, parent: QWidget | None = None):
        super().__init__(parent, Qt.WindowType.Dialog)
        self._source = source
        self._sink = sink

        self._measurement = np.zeros_like(mask)
        self._mask = mask

        self.setWindowTitle("Speckle Nulling Contrast")

        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self.setup_preview_widget())
        self.setLayout(layout)

        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.on_update_window)
        self.update_timer.start(100)  # Update window every 100 ms

    @Slot(np.ndarray)
    def on_measurement(self, _measurement: np.ndarray):
        self._measurement = _measurement

    @Slot(float, float)
    def on_speckle_location(self, speckle_location_x: float, speckle_location_y: float):
        self.preview_figure_widget.figure.get_imshow_ax().axvline(speckle_location_x, alpha=0.5, linewidth=0.5, color="red")
        self.preview_figure_widget.figure.get_imshow_ax().axhline(speckle_location_y, alpha=0.5, linewidth=0.5, color="red")

    @Slot(float, float)
    def on_speckle_parameters(self, frequency: float, angle: float):
        logger.info("frequency = %f, angle = %f", frequency, np.rad2deg(angle))

    @property
    def measurement(self) -> np.ndarray:
        return self._measurement

    def setup_preview_widget(self) -> QWidget:
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(2, 2, 2, 2)
        widget.setLayout(layout)

        self.preview_figure_widget = ContrastFigureWidget(self.measurement, self._mask, True, self)

        layout.addWidget(self.preview_figure_widget)

        return widget

    @Slot()
    def on_update_window(self):
        self.preview_figure_widget.figure.get_image().set_data(self.measurement)
        self.preview_figure_widget.figure.canvas.draw_idle()

    def closeEvent(self, event):
        if self.update_timer.isActive():
            self.update_timer.stop()
        self.deleteLater()
        event.accept()







class MainWindow(Window):
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
    def sink(self) -> Modulator | None:
        return self._sink

    @Slot()
    def on_calibration_change(self):
        if self._source is not None and self._sink is not None:
            self.controls_widget.task_preview_button.setEnabled(True)
            if self.settings_widget.speckle_calibration is not None:
                self.controls_widget.play_pause_button.setEnabled(True)

    @Slot()
    def on_source_change(self, _device: Camera):
        self.devices_widget.source_info_button.setEnabled(True)
        self.devices_widget.source_settings_button.setEnabled(True)
        self.devices_widget.source_preview_button.setEnabled(True)
        self._source = _device
        self.open_device_preview_window(_device)
        self.devices_widget.source_info_button.clicked.connect(lambda _, _device=_device: self.open_device_info_window(_device))
        self.devices_widget.source_settings_button.clicked.connect(lambda _, _device=_device: self.open_device_settings_window(_device))
        self.devices_widget.source_preview_button.clicked.connect(lambda _, _device=_device: self.open_device_preview_window(_device))
        if self._source is not None and self._sink is not None:
            self.controls_widget.task_preview_button.setEnabled(True)
            self.settings_widget.dark_hole_mask = chord(self._source.shape, self._source.shape[0] * 7 / 16, 0.65)
            if self.settings_widget.speckle_calibration is not None:
                self.controls_widget.play_pause_button.setEnabled(True)

    @Slot()
    def on_sink_change(self, _device: Modulator):
        self.devices_widget.sink_info_button.setEnabled(True)
        self.devices_widget.sink_settings_button.setEnabled(True)
        self.devices_widget.sink_preview_button.setEnabled(True)
        self._sink = _device
        self.open_device_preview_window(_device)
        self.devices_widget.sink_info_button.clicked.connect(lambda _, _device=_device: self.open_device_info_window(_device))
        self.devices_widget.sink_settings_button.clicked.connect(lambda _, _device=_device: self.open_device_settings_window(_device))
        self.devices_widget.sink_preview_button.clicked.connect(lambda _, _device=_device: self.open_device_preview_window(_device))
        if self._source is not None and self._sink is not None:
            self.controls_widget.task_preview_button.setEnabled(True)
            if self.settings_widget.speck_calibration is not None:
                self.controls_widget.play_pause_button.setEnabled(True)

    def open_device_info_window(self, _device: Camera | Modulator):

        info_window_id = f"{_device.name}_info"

        @Slot()
        def close_window():
            testbed.data.windows.pop(info_window_id, None)

        if info_window_id not in testbed.data.windows:
            info_window: CameraInfoWindow | ModulatorInfoWindow | None = None
            if isinstance(_device, Camera):
                info_window = CameraInfoWindow(_device, parent=self)
            elif isinstance(_device, Modulator):
                info_window = ModulatorInfoWindow(_device, parent=self)
            else:
                raise ValueError("Invalid device")
            info_window.destroyed.connect(close_window)
            info_window.show()
            info_window.raise_()
            info_window.activateWindow()
            testbed.data.windows[info_window_id] = info_window

    def open_device_settings_window(self, _device: Camera | Modulator):

        settings_window_id = f"{_device.name}_settings"

        @Slot()
        def close_window():
            testbed.data.windows.pop(settings_window_id, None)

        if settings_window_id not in testbed.data.windows:
            settings_window: CameraSettingsWindow | ModulatorSettingsWindow | None = None
            if isinstance(_device, Camera):
                settings_window = CameraSettingsWindow(_device, parent=self)
            elif isinstance(_device, Modulator):
                settings_window = ModulatorSettingsWindow(_device, parent=self)
            else:
                raise ValueError("Invalid device")
            settings_window.destroyed.connect(close_window)
            settings_window.show()
            settings_window.raise_()
            settings_window.activateWindow()
            testbed.data.windows[settings_window_id] = settings_window

    def open_device_preview_window(self, _device: Camera | Modulator):

        preview_window_id = f"{_device.name}_preview"

        def close_window():
            testbed.data.windows.pop(preview_window_id, None)

        if preview_window_id not in testbed.data.windows:
            preview_window: CameraPreviewWindow | ModulatorPreviewWindow | None = None
            if isinstance(_device, Camera):
                preview_window = CameraPreviewWindow(_device, parent=self)
            elif isinstance(_device, Modulator):
                preview_window = ModulatorPreviewWindow(_device, parent=self)
            else:
                raise ValueError("Invalid device")
            preview_window.destroyed.connect(close_window)
            preview_window.show()
            preview_window.raise_()
            preview_window.activateWindow()
            testbed.data.windows[preview_window_id] = preview_window

    @Slot(int, float)  # step, elapsed_time
    def on_progress(self, step: int, t_elapsed: float):
        self.controls_widget.progressbar.setValue(step + 1)
        self.controls_widget.progressbar.setTime(t_elapsed)
        self.controls_widget.progressbar.updateProgress()

    @Slot()
    def on_finish(self):
        worker_id = f"{_PROCESS_}_worker"
        self.controls_widget.progressbar.reset()
        self.controls_widget.progressbar.updateProgress()
        if worker_id in testbed.data.workers:  # an update worker is in progress
            current_worker = testbed.data.workers.pop(worker_id)
            current_worker.stop()
            self.controls_widget.play_pause_button.setIcon(QIcon(ICON_RUN))

    @Slot()
    def on_source_storage_finish(self):
        source_storage_worker_id = f"{_PROCESS_}_source_storage_worker"
        if source_storage_worker_id in testbed.data.workers:
            source_storage_worker = testbed.data.workers.pop(source_storage_worker_id)
            source_storage_worker.stop()

    @Slot()
    def on_sink_storage_finish(self):
        sink_storage_worker_id = f"{_PROCESS_}_sink_storage_worker"
        if sink_storage_worker_id in testbed.data.workers:
            sink_storage_worker = testbed.data.workers.pop(sink_storage_worker_id)
            sink_storage_worker.stop()

    @Slot()
    def on_start_stop(self):
        worker_id = f"{_PROCESS_}_worker"
        source_storage_worker_id = f"{_PROCESS_}_source_storage_worker"
        sink_storage_worker_id = f"{_PROCESS_}_sink_storage_worker"
        source_preview_window_id = f"{self.source.name}_preview"
        sink_preview_window_id = f"{self.sink.name}_preview"
        proc_preview_window_id = f"{_PROCESS_}_preview_window"

        if worker_id in testbed.data.workers:  # an update worker is in progress
            current_worker = testbed.data.workers.pop(worker_id)
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

        worker = MainWorker(self.source, self.sink, self.settings_widget.dark_hole_mask, self.settings_widget.speckle_calibration, self.settings_widget.phs_array, self.settings_widget.amp_array, self.settings_widget.n_iterations)
        worker.signals.progress.connect(self.on_progress)
        worker.signals.finished.connect(self.on_finish)

        timestamp = timestamp_string(frmt="%Y%m%d.%H%M%S", ms=None)

        if self.settings_widget.record_source:
            source_storage_worker = SourceStorageWorker(f"data/output/{timestamp}_{_PROCESS_}_source.raw", self.settings_widget.n_iterations)
            worker.signals.new_source_sample.connect(source_storage_worker.on_sample)
            source_storage_worker.signals.finished.connect(self.on_source_storage_finish)
            testbed.data.workers[source_storage_worker_id] = source_storage_worker
            testbed.data.threadpool.start(source_storage_worker)

        if self.settings_widget.record_sink:
            sink_storage_worker = SinkStorageWorker(f"data/output/{timestamp}_{_PROCESS_}_sink.raw", self.settings_widget.n_iterations)
            worker.signals.new_sink_sample.connect(sink_storage_worker.on_sample)
            sink_storage_worker.signals.finished.connect(self.on_sink_storage_finish)
            testbed.data.workers[sink_storage_worker_id] = sink_storage_worker
            testbed.data.threadpool.start(sink_storage_worker)

        self.controls_widget.play_pause_button.setIcon(QIcon(ICON_PAUSE))
        self.devices_widget.sink_settings_button.setEnabled(False)
        self.devices_widget.source_settings_button.setEnabled(False)

        if source_preview_window_id in testbed.data.windows:
            worker.signals.new_source_sample.connect(testbed.data.windows[source_preview_window_id].on_new_sample)
        if sink_preview_window_id in testbed.data.windows:
            worker.signals.new_sink_sample.connect(testbed.data.windows[sink_preview_window_id].on_new_sample)
        if proc_preview_window_id in testbed.data.windows:
            worker.signals.speckle_location.connect(testbed.data.windows[proc_preview_window_id].on_speckle_location)
            worker.signals.speckle_parameters.connect(testbed.data.windows[proc_preview_window_id].on_speckle_parameters)
            worker.signals.measurement.connect(testbed.data.windows[proc_preview_window_id].on_measurement)

        testbed.data.workers[worker_id] = worker
        testbed.data.threadpool.start(worker)

    def open_preview_window(self):

        proc_preview_window_id = f"{_PROCESS_}_preview_window"

        @Slot()
        def close_window():
            testbed.data.windows.pop(proc_preview_window_id, None)

        if proc_preview_window_id not in testbed.data.windows and self._source is not None and self._sink is not None:
            proc_preview_window = SpeckleNullProcContrastWindow(self._source, self._sink, self.settings_widget.dark_hole_mask, parent=self)
            proc_preview_window.destroyed.connect(close_window)
            proc_preview_window.show()
            proc_preview_window.raise_()
            proc_preview_window.activateWindow()
            testbed.data.windows[proc_preview_window_id] = proc_preview_window

    def open_contrast_window(self):
        proc_contrast_window_id = f"{_PROCESS_}_contrast_window"

        @Slot()
        def close_window():
            testbed.data.windows.pop(proc_contrast_window_id, None)

        if proc_contrast_window_id not in testbed.data.windows and self._source is not None and self._sink is not None:
            proc_contrast_window = SpeckleNullProcMoreWindow(self._source, self._sink, self.settings_widget.dark_hole_mask, parent=self)
            proc_contrast_window.destroyed.connect(close_window)
            proc_contrast_window.show()
            proc_contrast_window.raise_()
            proc_contrast_window.activateWindow()
            testbed.data.windows[proc_contrast_window_id] = proc_contrast_window

    def setup_main_widget(self) -> QWidget:
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        widget.setLayout(layout)

        self.devices_widget = DevicesSetupWidget(testbed.data.devices, parent=self)
        self.devices_widget.source_changed.connect(self.on_source_change)
        self.devices_widget.sink_changed.connect(self.on_sink_change)

        self.settings_widget = MainSettingsWidget(self)
        self.settings_widget.calibration_changed.connect(self.on_calibration_change)

        self.controls_widget = TaskControlsWidget(self)
        self.controls_widget.play_pause_button.setEnabled(False)
        self.controls_widget.play_pause_button.clicked.connect(self.on_start_stop)
        self.controls_widget.task_preview_button.setEnabled(False)
        self.controls_widget.task_preview_button.clicked.connect(self.open_preview_window)
        self.controls_widget.contrast_preview_button.clicked.connect(self.open_contrast_window)

        layout.addWidget(self.devices_widget)
        layout.addWidget(self.settings_widget)
        layout.addWidget(self.controls_widget)
        layout.addStretch(5)

        return widget

    def closeEvent(self, event):
        if self.source is not None:
            source_preview_window_id = f"{self.source.name}_preview"
            if source_preview_window_id in testbed.data.windows:
                logger.info("Cannot close main window until preview windows are closed.")
                event.ignore()
                return

        if self.sink is not None:
            sink_preview_window_id = f"{self.sink.name}_preview"
            if sink_preview_window_id in testbed.data.windows:
                logger.info("Cannot close main window until preview windows are closed.")
                event.ignore()
                return

        while testbed.data.workers:
            key, worker = testbed.data.workers.popitem()
            worker.stop()
            logger.info("stopping worker %s", key)
        self.deleteLater()
        event.accept()
