import numpy as np
from numpy.typing import NDArray

from PySide6.QtCore import Qt, Slot, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDoubleSpinBox, QGridLayout, QHBoxLayout, QLabel, QSpinBox, QVBoxLayout, QWidget, QMessageBox, QCheckBox

import testbed

from ..function import DOTFProbeDirection
from ..widget import NSpinBoxesWidget, DOTFProbeDirectionWidget
from ..device.camera import Camera
from ..device.modulator import Modulator, FULL_STROKE_NM
from ..worker.dotf_measurement_worker import ProcessWorker
from ..worker.camera_worker import ProcessWorker as CameraSamplingWorker
from ..worker.modulator_worker import ProcessWorker as ModulatorSamplingWorker
from .camera_window import PreviewWindow as CameraPreviewWindow
from .modulator_window import PreviewWindow as ModulatorPreviewWindow
from .dialog import MessageDialog
from .figure_widget import DOTFMeasureFigureWidget
from .resource import ICON_PAUSE, ICON_RUN

from . import DevicesSetupWidget, TaskControlsWidget, Window

from pykato.log import setup_logger

_PROCESS_ = testbed.DOTF_MEASUREMENT
process_worker_id = f"{_PROCESS_}_worker"
process_info_window_id = f"{_PROCESS_}_info_window"

logger = setup_logger(f"{_PROCESS_}_window", terminator="\n")


class ProcessSettingsWidget(QWidget):
    """
    DOTF process settings window
    """

    def __init__(self, parent=None):
        _probe_amplitude = 50.0
        _probe_width, _probe_length = 10, 20
        _reps = 2
        _sleep_s = 0.1
        super().__init__(parent)

        probe_amplitude_label = QLabel("Probe Amp.", self)
        probe_amplitude_label.setFixedWidth(100)

        self.probe_amplitude_spinbox = QDoubleSpinBox(self)
        self.probe_amplitude_spinbox.setRange(-100, 100)
        self.probe_amplitude_spinbox.setSuffix(" %")
        self.probe_amplitude_spinbox.setSingleStep(1)
        self.probe_amplitude_spinbox.setToolTip("Probe amplitude")
        self.probe_amplitude_spinbox.setValue(_probe_amplitude)

        probe_size_label = QLabel("Probe size", self)
        probe_size_label.setFixedWidth(100)

        self.probe_size_spinboxes = NSpinBoxesWidget(2, self)
        self.probe_size_spinboxes[0].setMinimum(0)
        self.probe_size_spinboxes[0].setMaximum(100)
        self.probe_size_spinboxes[0].setToolTip("Probe length")
        self.probe_size_spinboxes[0].setValue(_probe_length)
        self.probe_size_spinboxes[1].setMinimum(0)
        self.probe_size_spinboxes[1].setMaximum(100)
        self.probe_size_spinboxes[1].setToolTip("Probe width")
        self.probe_size_spinboxes[1].setValue(_probe_width)

        probe_dir_label = QLabel("Probe dir.", self)
        probe_dir_label.setFixedWidth(100)

        self.probe_dir_checkboxes = DOTFProbeDirectionWidget(parent=self)

        n_reps_label = QLabel("Reps", self)
        n_reps_label.setFixedWidth(100)

        self.n_reps_spinbox = QSpinBox(self)
        self.n_reps_spinbox.setRange(0, 9999)
        self.n_reps_spinbox.setSingleStep(1)
        self.n_reps_spinbox.setToolTip("Number of reps to average")
        self.n_reps_spinbox.setValue(_reps)

        self.continuous_checkbox = QCheckBox("continuous", self)
        self.continuous_checkbox.setToolTip("Run till stop/pause button is clicked")

        @Slot(bool)
        def on_continuous_toggled(checked: bool):
            if checked:
                self.n_reps_spinbox.setEnabled(False)
            else:
                self.n_reps_spinbox.setEnabled(True)

        self.continuous_checkbox.toggled.connect(on_continuous_toggled)

        n_reps_layout = QHBoxLayout()
        n_reps_layout.addWidget(self.n_reps_spinbox, stretch=1)
        n_reps_layout.addWidget(self.continuous_checkbox, alignment=Qt.AlignmentFlag.AlignRight)

        sleep_label = QLabel("Sleep", self)
        sleep_label.setFixedWidth(100)

        self.sleep_s_spinbox = QDoubleSpinBox(self)
        self.sleep_s_spinbox.setMinimum(0)
        self.sleep_s_spinbox.setSingleStep(0.0001)
        self.sleep_s_spinbox.setDecimals(4)
        self.sleep_s_spinbox.setSuffix(" s")
        self.sleep_s_spinbox.setValue(_sleep_s)

        widget_layout = QGridLayout()

        row = 0
        col = 0
        widget_layout.addWidget(probe_amplitude_label, row, col)
        col += 1
        widget_layout.addWidget(self.probe_amplitude_spinbox, row, col, 1, 3)

        row += 1
        col = 0
        widget_layout.addWidget(probe_size_label, row, col)
        col += 1
        widget_layout.addWidget(self.probe_size_spinboxes, row, col, 1, 3)

        row += 1
        col = 0
        widget_layout.addWidget(probe_dir_label, row, col)
        col += 1
        widget_layout.addWidget(self.probe_dir_checkboxes, row, col, 1, 3)

        row += 1
        col = 0
        widget_layout.addWidget(n_reps_label, row, col)
        col += 1
        widget_layout.addLayout(n_reps_layout, row, col, 1, 3)

        row += 1
        col = 0
        widget_layout.addWidget(sleep_label, row, col)
        col += 1
        widget_layout.addWidget(self.sleep_s_spinbox, row, col, 1, 3)

        self.setLayout(widget_layout)

    @property
    def probe_amplitude(self) -> float:
        return FULL_STROKE_NM * self.probe_amplitude_spinbox.value() / 100.0

    @property
    def probe_size(self) -> tuple[int, int]:
        return self.probe_size_spinboxes.value()[:2]

    @property
    def probe_directions(self) -> list[DOTFProbeDirection]:
        return self.probe_dir_checkboxes.value()

    @property
    def continuous(self) -> bool:
        return self.continuous_checkbox.isChecked()

    @property
    def n_reps(self) -> int:
        return 0 if self.continuous else self.n_reps_spinbox.value()

    @property
    def sleep_s(self) -> float:
        return self.sleep_s_spinbox.value()


class ProcessInfoWindow(Window):
    """
    DOTF process info window
    """

    def __init__(self, shape: tuple[int, int], probe_directions: list[DOTFProbeDirection], parent: QWidget | None = None):
        super().__init__(parent, Qt.WindowType.Dialog)

        self.dotf_measure_dict = {}
        for direction in probe_directions:
            self.dotf_measure_dict[direction] = np.zeros(shape, dtype=np.complex64)

        self.setWindowTitle("DOTF Measurement")

        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self.setup_info_widget())
        self.setLayout(layout)

        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.on_update_timer_tick)
        self.update_timer.start(100)  # Update window every 100 ms

    @Slot(DOTFProbeDirection, np.ndarray)
    def on_dotf_measured(self, direction: DOTFProbeDirection, measurement: NDArray[np.complex64]):
        self.dotf_measure_dict[direction][:] = measurement[:]

    def setup_info_widget(self) -> QWidget:
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(2, 2, 2, 2)
        widget.setLayout(layout)
        self.process_info_figure_widget = DOTFMeasureFigureWidget(self.dotf_measure_dict, ["Home", "Pan", "Zoom", "Save"], parent=self)
        layout.addWidget(self.process_info_figure_widget)
        return widget

    @Slot()
    def on_update_timer_tick(self):
        for probe, dotf_measure in self.dotf_measure_dict.items():
            self.process_info_figure_widget.set_dotf_map_data(probe, dotf_measure)
        self.process_info_figure_widget.figure.canvas.draw_idle()

    def closeEvent(self, event):
        if self.update_timer.isActive():
            self.update_timer.stop()
        self.deleteLater()
        event.accept()


class ProcessWindow(Window):
    """
    DOTF process window
    """

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Dialog)
        self.setWindowTitle("DOTF Measurement Process")
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
        self.controls_widget.info_button.setEnabled(False)
        self.controls_widget.play_pause_button.setEnabled(False)
        if self.source is not None and self.sink is not None:
            self.controls_widget.info_button.setEnabled(True)
            self.controls_widget.play_pause_button.setEnabled(True)
        if process_info_window_id in testbed.data.windows:
            process_info_window: ProcessInfoWindow = testbed.data.windows.pop(process_info_window_id)
            process_info_window.close()

    @Slot(Modulator)
    def on_sink_changed(self, device: Modulator):
        self.sink = device
        self.controls_widget.info_button.setEnabled(False)
        self.controls_widget.play_pause_button.setEnabled(False)
        if self.source is not None and self.sink is not None:
            self.controls_widget.info_button.setEnabled(True)
            self.controls_widget.play_pause_button.setEnabled(True)
        if process_info_window_id in testbed.data.windows:
            process_info_window: ProcessInfoWindow = testbed.data.windows.pop(process_info_window_id)
            process_info_window.close()

    @Slot(int, float)  # step, elapsed_time
    def on_progress_tick(self, step: int, t_elapsed: float):
        self.controls_widget.progressbar.setValue(step + 1)
        self.controls_widget.progressbar.setTime(t_elapsed)
        self.controls_widget.progressbar.updateProgress()

    @Slot(str)
    def on_process_error(self, message: str):
        MessageDialog("DOTF Measurement Worker Failed", message, icon=QMessageBox.Icon.Critical, buttons=QMessageBox.StandardButton.Ok).exec()
        self.on_process_finished()

    @Slot()
    def on_process_finished(self):
        self.controls_widget.progressbar.setMaximum(1)
        self.controls_widget.progressbar.reset()
        self.controls_widget.progressbar.updateProgress()
        if process_worker_id in testbed.data.workers:  # an update worker is in progress
            testbed.data.workers.pop(process_worker_id)
            self.controls_widget.play_pause_button.setIconHint(QIcon(ICON_RUN), "Run")

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

            sink_sampling_worker_id = f"{self.sink.name}_sampling_worker"
            if sink_sampling_worker_id in testbed.data.workers:
                sink_sampling_worker: ModulatorSamplingWorker = testbed.data.workers[sink_sampling_worker_id]
                sink_sampling_worker.stop()

            if process_worker_id in testbed.data.workers:  # a process worker is in progress
                process_worker: ProcessWorker = testbed.data.workers[process_worker_id]
                process_worker.stop()
                return

            process_worker = ProcessWorker(self.source, self.sink, self.settings_widget.probe_amplitude, self.settings_widget.probe_size, self.settings_widget.probe_directions, self.settings_widget.n_reps)
            process_worker.signals.progressTicked.connect(self.on_progress_tick)
            process_worker.signals.finished.connect(self.on_process_finished)
            process_worker.signals.error.connect(self.on_process_error)

            self.controls_widget.progressbar.setMaximum(process_worker.n_ticks)
            self.controls_widget.play_pause_button.setIconHint(QIcon(ICON_PAUSE), "Pause")

            source_preview_window_id = f"{self.source.name}_preview_window"
            if source_preview_window_id in testbed.data.windows:
                source_preview_window: CameraPreviewWindow = testbed.data.windows[source_preview_window_id]
                process_worker.signals.srcSampled.connect(source_preview_window.on_sampled)

            sink_preview_window_id = f"{self.sink.name}_preview_window"
            if sink_preview_window_id in testbed.data.windows:
                sink_preview_window: ModulatorPreviewWindow = testbed.data.windows[sink_preview_window_id]
                process_worker.signals.snkSampled.connect(sink_preview_window.on_sampled)

            if process_info_window_id in testbed.data.windows:
                process_info_window: ProcessInfoWindow = testbed.data.windows[process_info_window_id]
                process_worker.signals.dotfMeasured.connect(process_info_window.on_dotf_measured)

            testbed.data.workers[process_worker_id] = process_worker
            testbed.data.threadpool.start(process_worker)

    def open_process_info_clicked(self):
        @Slot()
        def on_window_closed():
            testbed.data.windows.pop(process_info_window_id, None)

        if process_info_window_id not in testbed.data.windows and self.source is not None and self.sink is not None:
            process_info_window = ProcessInfoWindow(self.source.shape, self.settings_widget.probe_directions, parent=self)
            process_info_window.destroyed.connect(on_window_closed)
            process_info_window.show()
            process_info_window.raise_()
            process_info_window.activateWindow()
            testbed.data.windows[process_info_window_id] = process_info_window

            if process_worker_id in testbed.data.workers:
                process_worker: ProcessWorker = testbed.data.workers[process_worker_id]
                process_worker.signals.dotfMeasured.connect(process_info_window.on_dotf_measured)

    def setup_main_widget(self) -> QWidget:
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        widget.setLayout(layout)

        self.devices_widget = DevicesSetupWidget(testbed.data.devices, parent=self)
        self.devices_widget.sourceChanged.connect(self.on_source_changed)
        self.devices_widget.sinkChanged.connect(self.on_sink_changed)

        def probe_direction_changed(values: list[DOTFProbeDirection]):
            if process_info_window_id in testbed.data.windows:
                testbed.data.windows.pop(process_info_window_id).close()

        self.settings_widget = ProcessSettingsWidget(self)
        self.settings_widget.probe_dir_checkboxes.valueChanged.connect(probe_direction_changed)

        self.controls_widget = TaskControlsWidget(self)
        self.controls_widget.play_pause_button.clicked.connect(self.on_start_stop_clicked)
        self.controls_widget.info_button.clicked.connect(self.open_process_info_clicked)
        self.controls_widget.preview_button.hide()

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
