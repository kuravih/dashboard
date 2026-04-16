import pickle
import numpy as np
from matplotlib.lines import Line2D
from numpy.typing import NDArray

from pykato.function import timestamp_string
from pykato.log import setup_logger
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDoubleSpinBox, QGridLayout, QLabel, QVBoxLayout, QWidget, QMessageBox

import testbed

from ..device.camera import Camera
from ..device.modulator import Modulator, FULL_STROKE_NM
from ..worker.speckle_calibration_worker import ProcessWorker
from ..worker.camera_worker import ProcessWorker as CameraSamplingWorker
from ..worker.modulator_worker import ProcessWorker as ModulatorSamplingWorker
from ..worker.storage_worker import SinkStorageWorker, SourceStorageWorker
from ..function import flip_rotate_points
from .camera_window import PreviewWindow as CameraPreviewWindow
from .modulator_window import PreviewWindow as ModulatorPreviewWindow
from .dialog import MessageDialog
from .resource import ICON_PAUSE, ICON_RUN

from . import DevicesSetupWidget, LinspaceWidget, TaskControlsWidget, Window

_PROCESS_ = testbed.SPECKLE_CALIBRATION
process_worker_id = f"{_PROCESS_}_worker"

logger = setup_logger(f"{_PROCESS_}_window", terminator="\n")


class ProcessSettingsWidget(QWidget):
    """
    Speckle Calibration Process Settings
    """

    def __init__(self, parent=None):
        _amplitude = 10.0
        _angle_start, _angle_stop, _angle_steps = 0, 170, 18
        _freq_start, _freq_stop, _freq_steps = 0.06, 0.02, 9
        _phase_start, _phase_stop, _phase_steps = 0, 180, 2
        super().__init__(parent)

        amplitude_label = QLabel("Amplitude", self)
        amplitude_label.setFixedWidth(100)

        self.amplitude_spinbox = QDoubleSpinBox(self)
        self.amplitude_spinbox.setRange(-100, 100)
        self.amplitude_spinbox.setSuffix(" %")
        self.amplitude_spinbox.setSingleStep(1)
        self.amplitude_spinbox.setToolTip("Command amplitude")
        self.amplitude_spinbox.setValue(_amplitude)

        angle_label = QLabel("Angle Steps", self)
        angle_label.setFixedWidth(100)

        self.angle_steps = LinspaceWidget(_angle_start, _angle_stop, _angle_steps, self)
        self.angle_steps.start_spinbox.setMinimumWidth(100)
        self.angle_steps.stop_spinbox.setMinimumWidth(100)
        self.angle_steps.num_spinbox.setMinimumWidth(100)

        freq_label = QLabel("Frequency Steps", self)
        freq_label.setFixedWidth(100)

        self.freq_steps = LinspaceWidget(_freq_start, _freq_stop, _freq_steps, self)
        self.freq_steps.start_spinbox.setMinimumWidth(100)
        self.freq_steps.stop_spinbox.setMinimumWidth(100)
        self.freq_steps.num_spinbox.setMinimumWidth(100)

        phase_label = QLabel("Phase Steps", self)
        phase_label.setFixedWidth(100)

        self.phase_steps = LinspaceWidget(_phase_start, _phase_stop, _phase_steps, self)
        self.phase_steps.start_spinbox.setMinimumWidth(100)
        self.phase_steps.stop_spinbox.setMinimumWidth(100)
        self.phase_steps.num_spinbox.setMinimumWidth(100)

        widget_layout = QGridLayout()

        row = 0
        col = 0
        widget_layout.addWidget(amplitude_label, row, col)
        col += 1
        widget_layout.addWidget(self.amplitude_spinbox, row, col, 1, 3)

        row += 1
        col = 0
        widget_layout.addWidget(angle_label, row, col)
        col += 1
        widget_layout.addWidget(self.angle_steps, row, col, 1, 3)

        row += 1
        col = 0
        widget_layout.addWidget(freq_label, row, col)
        col += 1
        widget_layout.addWidget(self.freq_steps, row, col, 1, 3)

        row += 1
        col = 0
        widget_layout.addWidget(phase_label, row, col)
        col += 1
        widget_layout.addWidget(self.phase_steps, row, col, 1, 3)

        self.setLayout(widget_layout)

        self.speckles = np.full((self.freqs_array.size, self.angles_array.size, 2, 2), np.nan)

    @property
    def amplitude(self) -> float:
        return FULL_STROKE_NM * self.amplitude_spinbox.value() / 100.0

    @property
    def angles_array(self) -> np.ndarray:
        return self.angle_steps.value()

    @property
    def freqs_array(self) -> np.ndarray:
        return self.freq_steps.value()

    @property
    def phases_array(self) -> np.ndarray:
        return self.phase_steps.value()

    @property
    def speckles(self) -> NDArray[np.float64]:
        return self._speckles

    @speckles.setter
    def speckles(self, value: NDArray[np.float64]):
        self._speckles = value


class ProcessWindow(Window):
    """
    Speckle Calibration Process Window
    """

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Dialog)
        self.setWindowTitle("Speckle Calibration")
        self.sink = None
        self.source = None

        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self.setup_main_widget())

        self.speckles_plot = None

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

    @property
    def speckles(self) -> NDArray[np.float64]:
        return self.settings_widget.speckles

    @speckles.setter
    def speckles(self, value: NDArray[np.float64]):
        self.settings_widget.speckles = value

    @property
    def speckles_plot(self) -> Line2D | None:
        return self._speckles_plot

    @speckles_plot.setter
    def speckles_plot(self, value: Line2D | None):
        self._speckles_plot = value

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
            testbed.data.workers.pop(process_worker_id)
            self.controls_widget.play_pause_button.setIconHint(QIcon(ICON_RUN), "Run")

    @Slot()
    def on_source_storage_finished(self):
        assert self.source is not None
        source_storage_worker_id = f"{self.source.name}_storage_worker"
        if source_storage_worker_id in testbed.data.workers:
            testbed.data.workers.pop(source_storage_worker_id)

    @Slot()
    def on_sink_storage_finished(self):
        assert self.sink is not None
        sink_storage_worker_id = f"{self.sink.name}_storage_worker"
        if sink_storage_worker_id in testbed.data.workers:
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

            source_storage_worker_id = f"{self.source.name}_storage_worker"
            if source_storage_worker_id in testbed.data.workers:
                source_storage_worker: SourceStorageWorker = testbed.data.workers[source_storage_worker_id]
                source_storage_worker.stop()

            sink_sampling_worker_id = f"{self.sink.name}_sampling_worker"
            if sink_sampling_worker_id in testbed.data.workers:
                sink_sampling_worker: ModulatorSamplingWorker = testbed.data.workers[sink_sampling_worker_id]
                sink_sampling_worker.stop()

            sink_storage_worker_id = f"{self.sink.name}_storage_worker"
            if sink_storage_worker_id in testbed.data.workers:
                sink_storage_worker: SinkStorageWorker = testbed.data.workers[sink_storage_worker_id]
                sink_storage_worker.stop()

            if process_worker_id in testbed.data.workers:  # a process worker is in progress
                process_worker: ProcessWorker = testbed.data.workers[process_worker_id]
                process_worker.stop()
                return

            process_worker = ProcessWorker(self.source, self.sink, self.settings_widget.amplitude, self.settings_widget.freqs_array, self.settings_widget.angles_array, self.settings_widget.phases_array)
            process_worker.signals.progressTicked.connect(self.on_progress_tick)
            process_worker.signals.finished.connect(self.on_process_finished)

            self.controls_widget.progressbar.setMaximum(process_worker.n_ticks)
            self.controls_widget.play_pause_button.setIconHint(QIcon(ICON_PAUSE), "Pause")

            timestamp = timestamp_string(frmt="%Y%m%d.%H%M%S", ms=None)

            with open(f"data/output/{timestamp}_{_PROCESS_}_parameters.pkl", "wb") as wbfile:
                parameters_dict = {"amplitudes": self.settings_widget.amplitude, "frequencies": self.settings_widget.freqs_array, "angles": self.settings_widget.angles_array, "phases": self.settings_widget.phases_array}
                pickle.dump(parameters_dict, wbfile, protocol=pickle.HIGHEST_PROTOCOL)

            source_storage_worker = SourceStorageWorker(f"data/output/{timestamp}_{_PROCESS_}_{self.source.name}.raw", process_worker.n_ticks)
            process_worker.signals.srcSampled.connect(source_storage_worker.on_sampled)
            source_storage_worker.signals.finished.connect(self.on_source_storage_finished)
            testbed.data.workers[source_storage_worker_id] = source_storage_worker
            testbed.data.threadpool.start(source_storage_worker)

            sink_storage_worker = SinkStorageWorker(f"data/output/{timestamp}_{_PROCESS_}_{self.sink.name}.raw", process_worker.n_ticks)
            process_worker.signals.snkSampled.connect(sink_storage_worker.on_sampled)
            sink_storage_worker.signals.finished.connect(self.on_sink_storage_finished)
            testbed.data.workers[sink_storage_worker_id] = sink_storage_worker
            testbed.data.threadpool.start(sink_storage_worker)

            source_preview_window_id = f"{self.source.name}_preview_window"
            if source_preview_window_id in testbed.data.windows:
                source_preview_window: CameraPreviewWindow = testbed.data.windows[source_preview_window_id]
                process_worker.signals.srcSampled.connect(source_preview_window.on_sampled)

                if self.speckles_plot is not None:
                    self.speckles_plot.remove()
                    self.speckles = np.full((self.settings_widget.freqs_array.size, self.settings_widget.angles_array.size, 2, 2), np.nan)

                (self.speckles_plot,) = source_preview_window.preview_figure_widget.figure.get_imshow_axes().plot([], [], color="red", marker="o", markersize=10, markerfacecolor="none", linestyle="none")

                @Slot(np.ndarray)
                def on_speckles_located(speckles):
                    self.speckles = speckles
                    speckles_x, speckles_y = flip_rotate_points(speckles[:, :, :, 0], speckles[:, :, :, 1], source_preview_window.sample.capture.shape, source_preview_window.preview_figure_widget.flip, source_preview_window.preview_figure_widget.rotation)
                    self.speckles_plot.set_xdata([speckles_x])
                    self.speckles_plot.set_ydata([speckles_y])

                process_worker.signals.specklesLocated.connect(on_speckles_located)

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
        if self.speckles_plot is not None:
            self.speckles_plot.remove()
        while testbed.data.workers:
            key, worker = testbed.data.workers.popitem()
            worker.stop()
            logger.info("stopping worker %s", key)
        self.deleteLater()
        event.accept()
