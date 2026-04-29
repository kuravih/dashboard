from __future__ import annotations
from typing import TYPE_CHECKING, cast

import numpy as np
from numpy.typing import NDArray

from pykato.log import setup_logger

from PySide6.QtCore import Qt, Slot, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDoubleSpinBox, QGridLayout, QHBoxLayout, QLabel, QSpinBox, QVBoxLayout, QWidget, QMessageBox, QCheckBox

import testbed

if TYPE_CHECKING:
    from dashboard import MainWindow
from ..device.camera import Camera
from ..device.modulator import Modulator, FULL_STROKE_NM
from ..function import is_pairwise_calibration_file_valid, read_pairwise_calibration_file, PairwiseProbeDirection
from ..worker.pairwise_fpwfs_worker import ProcessWorker
from ..widget import PairwiseProbeDirectionWidget
from .camera_window import PreviewWindow as CameraPreviewWindow
from .modulator_window import PreviewWindow as ModulatorPreviewWindow
from .dialog import MessageDialog
from .figure_widget import WavefrontFigureWidget
from .resource import ICON_STOP, ICON_RUN

from . import DevicesSetupWidget, TaskControlsWidget, Window, FileLoadWidget

logger = setup_logger(f"{testbed.PAIRWISE_FPWFS}_window", terminator="\n")


# ==== ProcessSettingsWidget ==========================================================================================
class ProcessSettingsWidget(QWidget):
    """
    Pairwise FPWFS process settings window
    """

    def __init__(self, parent=None):
        _reps = 2
        _sleep_s = 0.1
        self.dark_hole_mask = None  # chord(self.source.shape, self.source.shape[0] * 5 / 16, 0.6)
        self.pairwise_calibration = None

        super().__init__(parent)

        probe_amp_label = QLabel("Probe Amp.", self)
        probe_amp_label.setFixedWidth(100)

        self.probe_amp_spinbox = QDoubleSpinBox(self)
        self.probe_amp_spinbox.setRange(-0, 100)
        self.probe_amp_spinbox.setSuffix(" %")
        self.probe_amp_spinbox.setSingleStep(1)
        self.probe_amp_spinbox.setToolTip("Probe amplitude")
        self.probe_amp_spinbox.setValue(0.0)
        self.probe_amp_spinbox.setEnabled(False)

        probe_dξ_label = QLabel("Probe dξ", self)
        probe_dξ_label.setFixedWidth(100)

        self.probe_dξ_spinbox = QDoubleSpinBox(self)
        self.probe_dξ_spinbox.setRange(0, 0.02000)
        self.probe_dξ_spinbox.setSingleStep(0.00001)
        self.probe_dξ_spinbox.setDecimals(5)
        self.probe_dξ_spinbox.setToolTip("Probe dξ")
        self.probe_dξ_spinbox.setValue(0)
        self.probe_dξ_spinbox.setEnabled(False)

        probe_dη_label = QLabel("Probe dη", self)
        probe_dη_label.setFixedWidth(100)

        self.probe_dη_spinbox = QDoubleSpinBox(self)
        self.probe_dη_spinbox.setRange(0, 0.0500)
        self.probe_dη_spinbox.setSingleStep(0.0001)
        self.probe_dη_spinbox.setDecimals(4)
        self.probe_dη_spinbox.setToolTip("Probe dη")
        self.probe_dη_spinbox.setValue(0)
        self.probe_dη_spinbox.setEnabled(False)

        probe_ξc_label = QLabel("Probe ξc", self)
        probe_ξc_label.setFixedWidth(100)

        self.probe_ξc_spinbox = QDoubleSpinBox(self)
        self.probe_ξc_spinbox.setRange(0.0, 0.0002000000000)
        self.probe_ξc_spinbox.setSingleStep(0.0000000000001)
        self.probe_ξc_spinbox.setToolTip("Probe ξc")
        self.probe_ξc_spinbox.setDecimals(13)
        self.probe_ξc_spinbox.setValue(0)
        self.probe_ξc_spinbox.setEnabled(False)

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
        self._sleep_s_spinbox.setValue(_sleep_s)

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
        return 0 if self.continuous else self.n_reps_spinbox.value()

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


# ==== ProcessInfoWindow ==============================================================================================
class ProcessInfoWindow(Window):
    """
    Pairwise FPWFS process info window
    """

    wid = f"{testbed.PAIRWISE_FPWFS}_info_window"

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


# ==== ProcessWindow ==================================================================================================
class ProcessWindow(Window):
    """
    Pairwise FPWFS process window
    """

    wid = f"{testbed.PAIRWISE_FPWFS}_window"

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Dialog)
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

    def update_device_buttons(self, enabled: bool):
        main_window = cast("MainWindow", self.parent())
        if self.source is not None:
            main_window.set_device_buttons_enabled(self.source.name, enabled)
        if self.sink is not None:
            main_window.set_device_buttons_enabled(self.sink.name, enabled)

    def update_process_controls(self):
        enabled = False
        if self.source is not None and self.sink is not None and self.settings_widget.calibration_widget.filepath is not None:
            if not testbed.data.is_worker_alive(self.source.sampling_worker_id) and not testbed.data.is_worker_alive(self.sink.sampling_worker_id):
                enabled = True
        self.controls_widget.info_button.setEnabled(enabled)
        self.controls_widget.run_stop_button.setEnabled(enabled)

    @Slot()
    def on_calibration_change(self):
        self.controls_widget.info_button.setEnabled(False)
        self.controls_widget.run_stop_button.setEnabled(False)
        if self.source is not None and self.sink is not None and self.settings_widget.calibration_widget.filepath is not None:
            self.pairwise_calibration, probe_amp, probe_ξc, probe_dξ, probe_dη = read_pairwise_calibration_file(self.settings_widget.calibration_widget.filepath)
            self.settings_widget.probe_amp_spinbox.setValue(probe_amp), self.settings_widget.probe_ξc_spinbox.setValue(probe_ξc), self.settings_widget.probe_dξ_spinbox.setValue(probe_dξ), self.settings_widget.probe_dη_spinbox.setValue(probe_dη)
            self.controls_widget.info_button.setEnabled(True)
            self.controls_widget.run_stop_button.setEnabled(True)

    @Slot(Camera)
    def on_source_changed(self, device: Camera):
        self.source = device
        self.update_process_controls()
        if testbed.data.is_window_alive(ProcessInfoWindow.wid):
            process_info_window = cast(ProcessInfoWindow, testbed.data.windows.pop(ProcessInfoWindow.wid))
            process_info_window.close()

    @Slot(Modulator)
    def on_sink_changed(self, device: Modulator):
        self.sink = device
        self.update_process_controls()
        if testbed.data.is_window_alive(ProcessInfoWindow.wid):
            process_info_window = cast(ProcessInfoWindow, testbed.data.windows.pop(ProcessInfoWindow.wid))
            process_info_window.close()

    @Slot(int, float)  # step, elapsed_time
    def on_progress_tick(self, step: int, t_elapsed: float):
        self.controls_widget.progressbar.setValue(step + 1)
        self.controls_widget.progressbar.setTime(t_elapsed)
        self.controls_widget.progressbar.updateProgress()

    @Slot(str)
    def on_process_error(self, message: str):
        MessageDialog("Pairwise FPWFS Measurement Worker Failed", message, icon=QMessageBox.Icon.Critical, buttons=QMessageBox.StandardButton.Ok).exec()
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
    def on_start_stop_clicked(self):
        if self.source is None or self.sink is None:
            message_dialog = MessageDialog("Devices not selected", "Source and sink devices not selected.", icon=QMessageBox.Icon.Information, buttons=QMessageBox.StandardButton.Ok)
            message_dialog.exec()
        else:
            if testbed.data.is_worker_alive(ProcessWorker.wid):
                process_worker = cast(ProcessWorker, testbed.data.workers[ProcessWorker.wid])
                process_worker.stop()
                return

            process_worker = ProcessWorker(self.source, self.sink, self.settings_widget.dark_hole_mask, self.pairwise_calibration, self.settings_widget.probe_amplitude, self.settings_widget.probe_dξ, self.settings_widget.probe_dη, self.settings_widget.probe_ξc, self.settings_widget.probe_directions, self.settings_widget.n_reps)
            process_worker.signals.progressTicked.connect(self.on_progress_tick)
            process_worker.signals.finished.connect(self.on_process_finished)
            process_worker.signals.error.connect(self.on_process_error)

            self.controls_widget.progressbar.setMaximum(process_worker.n_ticks)
            self.controls_widget.run_stop_button.setIconHint(QIcon(ICON_STOP), "Stop")

            if testbed.data.is_window_alive(self.source.preview_window_id):
                source_preview_window = cast(CameraPreviewWindow, testbed.data.windows[self.source.preview_window_id])
                process_worker.signals.srcSampled.connect(source_preview_window.on_sampled)

            if testbed.data.is_window_alive(self.sink.preview_window_id):
                sink_preview_window = cast(ModulatorPreviewWindow, testbed.data.windows[self.sink.preview_window_id])
                process_worker.signals.snkSampled.connect(sink_preview_window.on_sampled)

            if testbed.data.is_window_alive(ProcessInfoWindow.wid):
                process_info_window = cast(ProcessInfoWindow, testbed.data.windows[ProcessInfoWindow.wid])
                process_worker.signals.wfSensed.connect(process_info_window.on_wf_sensed)

            testbed.data.workers[ProcessWorker.wid] = process_worker
            testbed.data.threadpool.start(process_worker)
            self.update_device_buttons(False)

    def open_process_info_clicked(self):
        @Slot()
        def on_window_closed():
            testbed.data.windows.pop(ProcessInfoWindow.wid, None)

        if not testbed.data.is_window_alive(ProcessInfoWindow.wid) and self.source is not None and self.sink is not None:
            process_info_window = ProcessInfoWindow(self.source.shape, parent=self)
            process_info_window.destroyed.connect(on_window_closed)
            process_info_window.show()
            process_info_window.raise_()
            process_info_window.activateWindow()
            testbed.data.windows[ProcessInfoWindow.wid] = process_info_window

            if testbed.data.is_worker_alive(ProcessWorker.wid):
                process_worker = cast(ProcessWorker, testbed.data.workers[ProcessWorker.wid])
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
        self.controls_widget.run_stop_button.clicked.connect(self.on_start_stop_clicked)
        self.controls_widget.info_button.clicked.connect(self.open_process_info_clicked)
        self.controls_widget.preview_button.hide()

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
