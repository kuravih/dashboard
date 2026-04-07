from pykato.function import timestamp_string
from pykato.log import setup_logger
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QCheckBox, QDoubleSpinBox, QGridLayout, QHBoxLayout, QLabel, QSpinBox, QVBoxLayout, QWidget, QMessageBox

import testbed

from ..device.camera import Camera
from ..device.modulator import Modulator, FULL_STROKE_NM
from ..worker.simple_loop_worker import ProcessWorker
from ..worker.camera_worker import ProcessWorker as CameraSamplingWorker
from ..worker.modulator_worker import ProcessWorker as ModulatorSamplingWorker
from ..worker.storage_worker import SinkStorageWorker, SourceStorageWorker
from .camera_window import PreviewWindow as CameraPreviewWindow
from .modulator_window import PreviewWindow as ModulatorPreviewWindow
from .dialog import MessageDialog
from .resource import ICON_PAUSE, ICON_RUN

from . import DevicesSetupWidget, TaskControlsWidget, Window

_PROCESS_ = testbed.SIMPLE_LOOP
process_worker_id = f"{_PROCESS_}_worker"

logger = setup_logger(f"{_PROCESS_}_window", terminator="\n")


class ProcessSettingsWidget(QWidget):
    """
    Simple Process Settings
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        amplitude_label = QLabel("Amplitude", self)
        amplitude_label.setFixedWidth(100)

        self.amplitude_spinbox = QDoubleSpinBox(self)
        self.amplitude_spinbox.setRange(-100, 100)
        self.amplitude_spinbox.setSuffix(" %")
        self.amplitude_spinbox.setSingleStep(1)
        self.amplitude_spinbox.setToolTip("Command amplitude")
        self.amplitude_spinbox.setValue(10)

        n_steps_label = QLabel("Steps", self)
        n_steps_label.setFixedWidth(100)

        self.n_steps_spinbox = QSpinBox(self)
        self.n_steps_spinbox.setRange(0, 9999)
        self.n_steps_spinbox.setSingleStep(1)
        self.n_steps_spinbox.setToolTip("Number of steps")
        self.n_steps_spinbox.setValue(9)

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
        self.sleep_s_spinbox.setValue(0.1)

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
    def n_steps(self) -> int | None:
        return None if self.continuous else self.n_steps_spinbox.value()

    @property
    def record_source(self) -> bool:
        return self.source_checkbox.isChecked()

    @property
    def record_sink(self) -> bool:
        return self.sink_checkbox.isChecked()

    @property
    def sleep_s(self) -> float:
        return self.sleep_s_spinbox.value()


class ProcessWindow(Window):
    """
    Simple Process Window
    """

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Dialog)
        # self.setWindowModality(Qt.WindowModality.WindowModal)
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

    @Slot(Camera)
    def on_source_changed(self, device: Camera):
        self.source = device
        self.controls_widget.play_pause_button.setEnabled(False)
        if self.source is not None and self.sink is not None:
            self.controls_widget.play_pause_button.setEnabled(True)

    @Slot(Modulator)
    def on_sink_changed(self, device: Modulator):
        self.sink = device
        self.controls_widget.play_pause_button.setEnabled(False)
        if self.source is not None and self.sink is not None:
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

        assert self.sink is not None
        sink_preview_window_id = f"{self.sink.name}_preview_window"
        if sink_preview_window_id in testbed.data.windows:
            sink_preview_window: ModulatorPreviewWindow = testbed.data.windows[sink_preview_window_id]
            sink_preview_window.update_timer.stop()
            sink_preview_window.update_timer.timeout.disconnect()
            sink_preview_window.update_timer.timeout.connect(sink_preview_window.on_update_timer_tick)

    @Slot()
    def on_source_storage_finished(self):
        assert self.source is not None
        source_storage_worker_id = f"{self.source.name}_storage_worker"
        if source_storage_worker_id in testbed.data.workers:
            source_storage_worker: SourceStorageWorker = testbed.data.workers[source_storage_worker_id]
            source_storage_worker.stop()
            testbed.data.workers.pop(source_storage_worker_id)

    @Slot()
    def on_sink_storage_finished(self):
        assert self.sink is not None
        sink_storage_worker_id = f"{self.sink.name}_storage_worker"
        if sink_storage_worker_id in testbed.data.workers:
            sink_storage_worker: SinkStorageWorker = testbed.data.workers[sink_storage_worker_id]
            sink_storage_worker.stop()
            testbed.data.workers.pop(sink_storage_worker_id)

    @Slot()
    def on_start_stop_clicked(self):
        if self.source is None or self.sink is None:
            message_dialog = MessageDialog("Devices not selected", "Source and sink devices not selected.", icon=QMessageBox.Icon.Information, buttons=QMessageBox.StandardButton.Ok)
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

            sink_sampling_worker_id = f"{self.sink.name}_sampling_worker"
            if sink_sampling_worker_id in testbed.data.workers:
                sink_sampling_worker: ModulatorSamplingWorker = testbed.data.workers[sink_sampling_worker_id]
                sink_sampling_worker.stop()
                testbed.data.workers.pop(sink_sampling_worker_id)

            sink_storage_worker_id = f"{self.sink.name}_storage_worker"
            if sink_storage_worker_id in testbed.data.workers:
                sink_storage_worker: SinkStorageWorker = testbed.data.workers[sink_storage_worker_id]
                sink_storage_worker.stop()
                testbed.data.workers.pop(sink_storage_worker_id)

            if process_worker_id in testbed.data.workers:  # an update worker is in progress
                process_worker: ProcessWorker = testbed.data.workers[process_worker_id]
                process_worker.stop()
                testbed.data.workers.pop(process_worker_id)

                self.controls_widget.play_pause_button.setIconHint(QIcon(ICON_RUN), "Run")
                self.controls_widget.progressbar.setMaximum(100)
                self.controls_widget.progressbar.reset()
                self.controls_widget.progressbar.updateProgress()

                return

            if self.settings_widget.continuous:
                self.controls_widget.progressbar.setMaximum(0)
            else:
                self.controls_widget.progressbar.setMaximum(self.settings_widget.n_steps)

            process_worker = ProcessWorker(self.source, self.sink, self.settings_widget.amplitude, self.settings_widget.n_steps)
            process_worker.signals.progressTicked.connect(self.on_progress_tick)
            process_worker.signals.finished.connect(self.on_process_finished)

            self.controls_widget.play_pause_button.setIconHint(QIcon(ICON_PAUSE), "Pause")

            timestamp = timestamp_string(frmt="%Y%m%d.%H%M%S", ms=None)

            if self.settings_widget.record_source:
                source_storage_worker = SourceStorageWorker(f"data/output/{timestamp}_{_PROCESS_}_{self.source.name}.raw", self.settings_widget.n_steps)
                process_worker.signals.srcSampled.connect(source_storage_worker.on_sampled)
                source_storage_worker.signals.finished.connect(self.on_source_storage_finished)
                testbed.data.workers[source_storage_worker_id] = source_storage_worker
                testbed.data.threadpool.start(source_storage_worker)

            if self.settings_widget.record_sink:
                sink_storage_worker = SinkStorageWorker(f"data/output/{timestamp}_{_PROCESS_}_{self.sink.name}.raw", self.settings_widget.n_steps)
                process_worker.signals.snkSampled.connect(sink_storage_worker.on_sampled)
                sink_storage_worker.signals.finished.connect(self.on_sink_storage_finished)
                testbed.data.workers[sink_storage_worker_id] = sink_storage_worker
                testbed.data.threadpool.start(sink_storage_worker)

            source_preview_window_id = f"{self.source.name}_preview_window"
            if source_preview_window_id in testbed.data.windows:
                source_preview_window: CameraPreviewWindow = testbed.data.windows[source_preview_window_id]
                process_worker.signals.srcSampled.connect(source_preview_window.on_sampled)

            sink_preview_window_id = f"{self.sink.name}_preview_window"
            if sink_preview_window_id in testbed.data.windows:
                sink_preview_window: ModulatorPreviewWindow = testbed.data.windows[sink_preview_window_id]
                process_worker.signals.snkSampled.connect(sink_preview_window.on_sampled)

            testbed.data.workers[process_worker_id] = process_worker
            testbed.data.threadpool.start(process_worker)

    def setup_main_widget(self) -> QWidget:
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        widget.setLayout(layout)

        self.devices_widget = DevicesSetupWidget(testbed.data.devices, parent=self)
        self.devices_widget.sourceChanged.connect(self.on_source_changed)
        self.devices_widget.sinkChanged.connect(self.on_sink_changed)

        self.settings_widget = ProcessSettingsWidget(self)

        self.controls_widget = TaskControlsWidget(self)
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
