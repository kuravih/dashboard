from __future__ import annotations
from typing import TYPE_CHECKING, cast

from pykato.function import timestamp_string
from pykato.log import setup_logger
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QCheckBox, QDoubleSpinBox, QGridLayout, QHBoxLayout, QLabel, QSpinBox, QVBoxLayout, QWidget, QMessageBox

import testbed
if TYPE_CHECKING:
    from dashboard import MainWindow
from ..device.camera import Camera
from ..device.modulator import Modulator, FULL_STROKE_NM
from ..worker.simple_loop_worker import ProcessWorker
from ..worker.storage_worker import SinkStorageWorker, SourceStorageWorker
from .camera_window import PreviewWindow as CameraPreviewWindow
from .modulator_window import PreviewWindow as ModulatorPreviewWindow
from .dialog import MessageDialog
from .resource import ICON_STOP, ICON_RUN

from . import DevicesSetupWidget, TaskControlsWidget, Window

logger = setup_logger(f"{testbed.SIMPLE_LOOP}_window", terminator="\n")


# ==== ProcessSettingsWidget ==========================================================================================
class ProcessSettingsWidget(QWidget):
    """
    Simple Process Settings
    """

    def __init__(self, parent=None):
        _n_steps = 9
        _amplitude = 10.0
        _sleep_s = 0.1
        super().__init__(parent)

        amplitude_label = QLabel("Amplitude", self)
        amplitude_label.setFixedWidth(100)

        self.amplitude_spinbox = QDoubleSpinBox(self)
        self.amplitude_spinbox.setRange(-100, 100)
        self.amplitude_spinbox.setSuffix(" %")
        self.amplitude_spinbox.setSingleStep(1)
        self.amplitude_spinbox.setToolTip("Command amplitude")
        self.amplitude_spinbox.setValue(_amplitude)

        n_steps_label = QLabel("Steps", self)
        n_steps_label.setFixedWidth(100)

        self.n_steps_spinbox = QSpinBox(self)
        self.n_steps_spinbox.setRange(0, 9999)
        self.n_steps_spinbox.setSingleStep(1)
        self.n_steps_spinbox.setToolTip("Number of steps")
        self.n_steps_spinbox.setValue(_n_steps)

        self.continuous_checkbox = QCheckBox("continuous", self)
        self.continuous_checkbox.setToolTip("Run till stop/pause button is clicked")

        @Slot(bool)
        def on_continuous_toggled(checked: bool):
            if checked:
                self.n_steps_spinbox.setEnabled(False)
            else:
                self.n_steps_spinbox.setEnabled(True)

        self.continuous_checkbox.toggled.connect(on_continuous_toggled)

        n_steps_layout = QHBoxLayout()
        n_steps_layout.addWidget(self.n_steps_spinbox, stretch=1)
        n_steps_layout.addWidget(self.continuous_checkbox, alignment=Qt.AlignmentFlag.AlignRight)

        sleep_label = QLabel("Sleep", self)
        sleep_label.setFixedWidth(100)

        self.sleep_s_spinbox = QDoubleSpinBox(self)
        self.sleep_s_spinbox.setMinimum(0)
        self.sleep_s_spinbox.setSingleStep(0.0001)
        self.sleep_s_spinbox.setDecimals(4)
        self.sleep_s_spinbox.setSuffix(" s")
        self.sleep_s_spinbox.setValue(_sleep_s)

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
        widget_layout.addWidget(amplitude_label, row, col)
        col += 1
        widget_layout.addWidget(self.amplitude_spinbox, row, col, 1, 3)

        row += 1
        col = 0
        widget_layout.addWidget(n_steps_label, row, col)
        col += 1
        widget_layout.addLayout(n_steps_layout, row, col, 1, 3)

        row += 1
        col = 0
        widget_layout.addWidget(sleep_label, row, col)
        col += 1
        widget_layout.addWidget(self.sleep_s_spinbox, row, col, 1, 3)

        row += 1
        col = 0
        widget_layout.addWidget(record_label, row, col)
        col += 1
        widget_layout.addLayout(record_layout, row, col, 1, 3)

        self.setLayout(widget_layout)

    @property
    def amplitude(self) -> float:
        return FULL_STROKE_NM * self.amplitude_spinbox.value() / 100.0

    @property
    def continuous(self) -> bool:
        return self.continuous_checkbox.isChecked()

    @property
    def n_steps(self) -> int:
        return 0 if self.continuous else self.n_steps_spinbox.value()

    @property
    def record_source(self) -> bool:
        return self.source_checkbox.isChecked()

    @property
    def record_sink(self) -> bool:
        return self.sink_checkbox.isChecked()

    @property
    def sleep_s(self) -> float:
        return self.sleep_s_spinbox.value()


# ==== ProcessWindow ==================================================================================================
class ProcessWindow(Window):
    """
    Simple Process Window
    """

    wid = f"{testbed.SIMPLE_LOOP}_window"

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Dialog)
        self.setWindowTitle("Simple Process")
        self.sink = None
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

    @property
    def sink(self) -> Modulator | None:
        return self._sink

    @sink.setter
    def sink(self, device: Modulator | None):
        self._sink = device

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
        MessageDialog("SimpleLoop Worker Failed", message, icon=QMessageBox.Icon.Critical, buttons=QMessageBox.StandardButton.Ok).exec()
        self.on_process_finished()

    @Slot()
    def on_process_finished(self):
        self.controls_widget.progressbar.setMaximum(1)
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

            process_worker = ProcessWorker(self.source, self.sink, self.settings_widget.amplitude, self.settings_widget.n_steps)
            process_worker.signals.progressTicked.connect(self.on_progress_tick)
            process_worker.signals.finished.connect(self.on_process_finished)
            process_worker.signals.error.connect(self.on_process_error)

            self.controls_widget.progressbar.setMaximum(process_worker.n_ticks)
            self.controls_widget.run_stop_button.setIconHint(QIcon(ICON_STOP), "Stop")

            timestamp = timestamp_string(frmt="%Y%m%d.%H%M%S", ms=None)

            if self.settings_widget.record_source:
                source_storage_worker = SourceStorageWorker(f"data/output/{timestamp}_{ProcessWorker.wid}_{self.source.name}.raw", self.settings_widget.n_steps)
                process_worker.signals.srcSampled.connect(source_storage_worker.on_sampled)
                source_storage_worker.signals.finished.connect(self.on_source_storage_finished)
                testbed.data.workers[self.source.storage_worker_id] = source_storage_worker
                testbed.data.threadpool.start(source_storage_worker)

            if self.settings_widget.record_sink:
                sink_storage_worker = SinkStorageWorker(f"data/output/{timestamp}_{ProcessWorker.wid}_{self.sink.name}.raw", self.settings_widget.n_steps)
                process_worker.signals.snkSampled.connect(sink_storage_worker.on_sampled)
                sink_storage_worker.signals.finished.connect(self.on_sink_storage_finished)
                testbed.data.workers[self.sink.storage_worker_id] = sink_storage_worker
                testbed.data.threadpool.start(sink_storage_worker)

            if testbed.data.is_window_alive(self.source.preview_window_id):
                source_preview_window = cast(CameraPreviewWindow, testbed.data.windows[self.source.preview_window_id])
                process_worker.signals.srcSampled.connect(source_preview_window.on_sampled)

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
        if testbed.data.is_worker_alive(ProcessWorker.wid):
            process_worker = cast(ProcessWorker, testbed.data.workers[ProcessWorker.wid])
            process_worker.stop()
        self.deleteLater()
        event.accept()
