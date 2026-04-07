import numpy as np
from numpy.typing import NDArray

from pykato.function import chord
from pykato.log import setup_logger

from PySide6.QtCore import Qt, Slot, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDoubleSpinBox, QGridLayout, QHBoxLayout, QLabel, QSpinBox, QVBoxLayout, QWidget, QMessageBox, QCheckBox

import testbed

from ..device.camera import Camera
from ..device.modulator import Modulator, FULL_STROKE_NM
from ..function import is_pairwise_calibration_file_valid, read_pairwise_calibration_file, PairwiseProbeDirection
from ..worker.pairwise_fpwfs_worker import ProcessWorker
from ..worker.camera_worker import ProcessWorker as CameraSamplingWorker
from ..worker.modulator_worker import ProcessWorker as ModulatorSamplingWorker
from ..worker.storage_worker import SinkStorageWorker, SourceStorageWorker
from ..widget import PairwiseProbeDirectionWidget
from .camera_window import PreviewWindow as CameraPreviewWindow
from .modulator_window import PreviewWindow as ModulatorPreviewWindow
from .dialog import MessageDialog
from .figure_widget import WavefrontFigureWidget
from .resource import ICON_PAUSE, ICON_RUN

from . import DevicesSetupWidget, TaskControlsWidget, Window, FileLoadWidget

_PROCESS_ = testbed.PAIRWISE_FPWFS
process_worker_id = f"{_PROCESS_}_worker"
process_info_window_id = f"{_PROCESS_}_info_window"

logger = setup_logger(f"{_PROCESS_}_window", terminator="\n")


class ProcessSettingsWidget(QWidget):
    """
    Pairwise FPWFS process settings window
    """

    def __init__(self, parent=None):
        self.dark_hole_mask = None  # chord(self.source.shape, self.source.shape[0] * 5 / 16, 0.6)
        self.pairwise_calibration = None

        super().__init__(parent)

        probe_amp_label = QLabel("Probe Amp.", self)
        probe_amp_label.setFixedWidth(100)

        self.probe_amp_spinbox = QDoubleSpinBox(self)
        self.probe_amp_spinbox.setRange(-100, 100)
        self.probe_amp_spinbox.setSuffix(" %")
        self.probe_amp_spinbox.setSingleStep(1)
        self.probe_amp_spinbox.setToolTip("Probe amplitude")
        self.probe_amp_spinbox.setValue(20)

        probe_dξ_label = QLabel("Probe dξ", self)
        probe_dξ_label.setFixedWidth(100)

        self.probe_dξ_spinbox = QDoubleSpinBox(self)
        self.probe_dξ_spinbox.setRange(-1.0, 1.0)
        self.probe_dξ_spinbox.setSingleStep(0.001)
        self.probe_dξ_spinbox.setDecimals(3)
        self.probe_dξ_spinbox.setToolTip("Probe dξ")
        # self._probe_dξ.setValue(0.008)
        self.probe_dξ_spinbox.setValue(0.075)

        probe_dη_label = QLabel("Probe dη", self)
        probe_dη_label.setFixedWidth(100)

        self.probe_dη_spinbox = QDoubleSpinBox(self)
        self.probe_dη_spinbox.setRange(-1.0, 1.0)
        self.probe_dη_spinbox.setSingleStep(0.001)
        self.probe_dη_spinbox.setDecimals(3)
        self.probe_dη_spinbox.setToolTip("Probe dη")
        # self._probe_dη.setValue(0.017)
        self.probe_dη_spinbox.setValue(0.155)

        probe_ξc_label = QLabel("Probe ξc", self)
        probe_ξc_label.setFixedWidth(100)

        self.probe_ξc_spinbox = QDoubleSpinBox(self)
        self.probe_ξc_spinbox.setRange(0.0, 100.0)
        self.probe_ξc_spinbox.setSingleStep(0.00000001)
        self.probe_ξc_spinbox.setToolTip("Probe ξc")
        # self._probe_ξc.setValue(35.0)
        self.probe_ξc_spinbox.setDecimals(8)
        self.probe_ξc_spinbox.setValue(0.00010133)

        probe_dir_label = QLabel("Probe dir.", self)
        probe_dir_label.setFixedWidth(100)

        self.probe_dir_checkboxes = PairwiseProbeDirectionWidget(parent=self)
        self.probe_dir_checkboxes[1].setChecked(False)
        self.probe_dir_checkboxes.setEnabled(False)

        n_reps_label = QLabel("Reps", self)
        n_reps_label.setFixedWidth(100)

        self.n_reps_spinbox = QSpinBox(self)
        self.n_reps_spinbox.setRange(0, 9999)
        self.n_reps_spinbox.setSingleStep(1)
        self.n_reps_spinbox.setToolTip("Number of reps to average")
        self.n_reps_spinbox.setValue(2)

        self.continuous_checkbox = QCheckBox("continuous", self)
        self.continuous_checkbox.setToolTip("Run till stop/pause button is clicked")

        @Slot(bool)
        def on_continuous_toggled(checked: bool):
            if checked:
                self.n_reps_spinbox.setEnabled(False)
            else:
                self.n_reps_spinbox.setEnabled(True)

        self.continuous_checkbox.toggled.connect(on_continuous_toggled)

        pairwise_calibration_label = QLabel("Calibration", self)
        pairwise_calibration_label.setFixedWidth(100)

        self.calibration_widget = FileLoadWidget(caption="Open Calibration File", directory="./data/output", file_filter="Pickle file (*.pkl)", validator=is_pairwise_calibration_file_valid, parent=self)

        n_reps_layout = QHBoxLayout()
        n_reps_layout.addWidget(self.n_reps_spinbox, stretch=1)
        n_reps_layout.addWidget(self.continuous_checkbox, alignment=Qt.AlignmentFlag.AlignRight)

        sleep_label = QLabel("Sleep", self)
        sleep_label.setFixedWidth(100)

        self._sleep_s_spinbox = QDoubleSpinBox(self)
        self._sleep_s_spinbox.setMinimum(0)
        self._sleep_s_spinbox.setSingleStep(0.0001)
        self._sleep_s_spinbox.setDecimals(4)
        self._sleep_s_spinbox.setSuffix(" s")
        self._sleep_s_spinbox.setValue(0.1)

        widget_layout = QGridLayout()

        row = 0
        col = 0
        widget_layout.addWidget(probe_amp_label, row, col)
        col += 1
        widget_layout.addWidget(self.probe_amp_spinbox, row, col, 1, 3)

        row += 1
        col = 0
        widget_layout.addWidget(probe_dξ_label, row, col)
        col += 1
        widget_layout.addWidget(self.probe_dξ_spinbox, row, col, 1, 3)

        row += 1
        col = 0
        widget_layout.addWidget(probe_dη_label, row, col)
        col += 1
        widget_layout.addWidget(self.probe_dη_spinbox, row, col, 1, 3)

        row += 1
        col = 0
        widget_layout.addWidget(probe_ξc_label, row, col)
        col += 1
        widget_layout.addWidget(self.probe_ξc_spinbox, row, col, 1, 3)

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
        widget_layout.addWidget(pairwise_calibration_label, row, col)
        col += 1
        widget_layout.addWidget(self.calibration_widget, row, col)

        row += 1
        col = 0
        widget_layout.addWidget(sleep_label, row, col)
        col += 1
        widget_layout.addWidget(self._sleep_s_spinbox, row, col, 1, 3)

        self.setLayout(widget_layout)

    @property
    def probe_amplitude(self) -> float:
        return FULL_STROKE_NM * self.probe_amp_spinbox.value() / 100.0

    @property
    def probe_dξ(self) -> float:
        return self.probe_dξ_spinbox.value()

    @property
    def probe_dη(self) -> float:
        return self.probe_dη_spinbox.value()

    @property
    def probe_ξc(self) -> float:
        return self.probe_ξc_spinbox.value()

    @property
    def probe_directions(self) -> list[PairwiseProbeDirection]:
        return self.probe_dir_checkboxes.value()

    @property
    def continuous(self) -> bool:
        return self.continuous_checkbox.isChecked()

    @property
    def n_reps(self) -> int:
        return self.n_reps_spinbox.value()

    @property
    def sleep_s(self) -> float:
        return self._sleep_s_spinbox.value()

    @property
    def dark_hole_mask(self) -> NDArray[np.bool] | None:
        return self._dark_hole_mask  # chord(self.source.shape, self.source.shape[0] * 5 / 16, 0.6)

    @dark_hole_mask.setter
    def dark_hole_mask(self, value: NDArray[np.bool] | None):
        self._dark_hole_mask = value

    @property
    def pairwise_calibration(self) -> dict | None:
        return self._pairwise_calibration

    @pairwise_calibration.setter
    def pairwise_calibration(self, value: dict | None):
        self._pairwise_calibration = value


class ProcessInfoWindow(Window):
    """
    Pairwise FPWFS process info window
    """

    def __init__(self, shape: tuple[int, int], parent: QWidget | None = None):
        super().__init__(parent, Qt.WindowType.Dialog)

        self.wavefront = np.zeros(shape, dtype=np.complex64)

        self.setWindowTitle("Focal Plane Wavefront Measurement")

        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self.setup_info_widget())
        self.setLayout(layout)

        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.on_update_timer_tick)
        self.update_timer.start(100)  # Update window every 100 ms

    @Slot(PairwiseProbeDirection, np.ndarray)
    def on_wf_sensed(self, direction: PairwiseProbeDirection, wavefront: NDArray[np.complex64]):
        self.wavefront[:] = wavefront[:]

    def setup_info_widget(self) -> QWidget:
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(2, 2, 2, 2)
        widget.setLayout(layout)
        self.process_info_figure_widget = WavefrontFigureWidget(self.wavefront, ["Home", "Pan", "Zoom", "Save"], parent=self)
        layout.addWidget(self.process_info_figure_widget)
        return widget

    @Slot()
    def on_update_timer_tick(self):
        self.process_info_figure_widget.set_wavefront_data(self.wavefront)
        self.process_info_figure_widget.figure.canvas.draw_idle()

    def closeEvent(self, event):
        if self.update_timer.isActive():
            self.update_timer.stop()
        self.deleteLater()
        event.accept()


class ProcessWindow(Window):
    """
    Pairwise FPWFS process window
    """

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Dialog)
        # self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setWindowTitle("Pairwise FPWFS Process")
        self.sink = None
        self.source = None
        self.pairwise_calibration = None

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

    @property
    def pairwise_calibration(self) -> dict[int, NDArray[np.float64]] | None:
        return self._pairwise_calibration

    @pairwise_calibration.setter
    def pairwise_calibration(self, value: dict[int, NDArray[np.float64]] | None):
        self._pairwise_calibration = value

    @Slot()
    def on_calibration_change(self):
        self.controls_widget.info_button.setEnabled(False)
        self.controls_widget.play_pause_button.setEnabled(False)
        if self.source is not None and self.sink is not None and self.settings_widget.calibration_widget.filepath is not None:
            self.pairwise_calibration = read_pairwise_calibration_file(self.settings_widget.calibration_widget.filepath)
            self.controls_widget.info_button.setEnabled(True)
            self.controls_widget.play_pause_button.setEnabled(True)

    @Slot(Camera)
    def on_source_changed(self, device: Camera):
        self.source = device
        if process_info_window_id in testbed.data.windows:
            process_info_window = testbed.data.windows[process_info_window_id]
            process_info_window.close()
        self.controls_widget.info_button.setEnabled(False)
        self.controls_widget.play_pause_button.setEnabled(False)
        if self.source is not None and self.sink is not None:
            self.controls_widget.info_button.setEnabled(True)
            self.controls_widget.play_pause_button.setEnabled(True)

    @Slot(Modulator)
    def on_sink_changed(self, device: Modulator):
        self.sink = device
        if process_info_window_id in testbed.data.windows:
            process_info_window = testbed.data.windows[process_info_window_id]
            process_info_window.close()
        self.controls_widget.info_button.setEnabled(False)
        self.controls_widget.play_pause_button.setEnabled(False)
        if self.source is not None and self.sink is not None:
            self.controls_widget.info_button.setEnabled(True)
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
                self.controls_widget.progressbar.setMaximum(self.settings_widget.n_reps)

            process_worker = ProcessWorker(self.source, self.sink, self.settings_widget.dark_hole_mask, self.pairwise_calibration, self.settings_widget.probe_amplitude, self.settings_widget.probe_dξ, self.settings_widget.probe_dη, self.settings_widget.probe_ξc, self.settings_widget.probe_directions, self.settings_widget.n_reps)
            process_worker.signals.progressTicked.connect(self.on_progress_tick)
            process_worker.signals.finished.connect(self.on_process_finished)

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
                process_worker.signals.wfSensed.connect(process_info_window.on_wf_sensed)

            testbed.data.workers[process_worker_id] = process_worker
            testbed.data.threadpool.start(process_worker)

    def open_process_info_clicked(self):
        @Slot()
        def on_window_closed():
            testbed.data.windows.pop(process_info_window_id, None)

        if process_info_window_id not in testbed.data.windows and self.source is not None and self.sink is not None:
            process_info_window = ProcessInfoWindow(self.source.shape, parent=self)
            process_info_window.destroyed.connect(on_window_closed)
            process_info_window.show()
            process_info_window.raise_()
            process_info_window.activateWindow()
            testbed.data.windows[process_info_window_id] = process_info_window

            if process_worker_id in testbed.data.workers:
                process_worker: ProcessWorker = testbed.data.workers[process_worker_id]
                process_worker.signals.wfSensed.connect(process_info_window.on_wf_sensed)

    def setup_main_widget(self) -> QWidget:
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        widget.setLayout(layout)

        self.devices_widget = DevicesSetupWidget(testbed.data.devices, parent=self)
        self.devices_widget.sourceChanged.connect(self.on_source_changed)
        self.devices_widget.sinkChanged.connect(self.on_sink_changed)

        self.settings_widget = ProcessSettingsWidget(self)
        self.settings_widget.calibration_widget.fileChanged.connect(self.on_calibration_change)

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
