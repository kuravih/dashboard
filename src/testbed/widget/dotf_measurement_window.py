import numpy as np
from numpy.typing import NDArray

from PySide6.QtCore import Qt, Slot, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDoubleSpinBox, QGridLayout, QHBoxLayout, QLabel, QSpinBox, QVBoxLayout, QWidget, QMessageBox, QCheckBox

import testbed

from ..function import DOTFProbeDirection
from ..widget import NSpinBoxesWidget, DOTFDirectionWidget
from ..device.camera import Camera
from ..device.modulator import Modulator
from ..worker.dotf_measurement_worker import ProcessWorker
from .camera_window import InfoWindow as CameraInfoWindow
from .camera_window import SimplePreviewWindow as CameraPreviewWindow
from .camera_window import SettingsWindow as CameraSettingsWindow
from .modulator_window import InfoWindow as ModulatorInfoWindow
from .modulator_window import SimplePreviewWindow as ModulatorPreviewWindow
from .modulator_window import SettingsWindow as ModulatorSettingsWindow
from .dialog import MessageDialog
from .figure_widget import DOTFMeasureFigureWidget
from .resource import ICON_PAUSE, ICON_RUN

from . import DevicesSetupWidget, TaskControlsWidget, Window

from pykato.log import setup_logger

_PROCESS_ = testbed.DOTF_MEASUREMENT
process_worker_id = f"{_PROCESS_}_worker"
process_info_window_id = f"{_PROCESS_}_info_window"
source_storage_worker_id = f"{_PROCESS_}_source_storage_worker"
sink_storage_worker_id = f"{_PROCESS_}_sink_storage_worker"

logger = setup_logger(f"{_PROCESS_}_window", terminator="\n")


class ProcessSettingsWidget(QWidget):
    """
    DOTF process settings window
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        probe_amp_label = QLabel("Probe Amp.", self)
        probe_amp_label.setFixedWidth(100)

        self._probe_amp_spinbox = QDoubleSpinBox(self)
        self._probe_amp_spinbox.setMinimum(0.0)
        self._probe_amp_spinbox.setMaximum(1.0)
        self._probe_amp_spinbox.setSingleStep(0.1)
        self._probe_amp_spinbox.setValue(0.5)
        self._probe_amp_spinbox.setToolTip("Probe amplitude")

        probe_size_label = QLabel("Probe size", self)
        probe_size_label.setFixedWidth(100)

        self._probe_size = NSpinBoxesWidget(2, self)
        self._probe_size[0].setMinimum(0)
        self._probe_size[0].setValue(2)
        self._probe_size[0].setMaximum(100)
        self._probe_size[0].setToolTip("Probe length")
        self._probe_size[1].setMinimum(0)
        self._probe_size[1].setValue(1)
        self._probe_size[1].setMaximum(100)
        self._probe_size[1].setToolTip("Probe width")

        probe_dir_label = QLabel("Probe dir.", self)
        probe_dir_label.setFixedWidth(100)

        self.probe_dir_checkboxes = DOTFDirectionWidget(self)

        n_reps_label = QLabel("Reps", self)
        n_reps_label.setFixedWidth(100)

        self._n_reps_spinbox = QSpinBox(self)
        self._n_reps_spinbox.setRange(0, 9999)
        self._n_reps_spinbox.setSingleStep(1)
        self._n_reps_spinbox.setValue(2)
        self._n_reps_spinbox.setToolTip("Number of reps to average")

        self._continuous_checkbox = QCheckBox("continuous", self)
        self._continuous_checkbox.setToolTip("Run till stop/pause button is clicked")
        self._continuous_checkbox.setMaximumWidth(90)

        @Slot(bool)
        def on_continuous_toggled(checked: bool):
            if checked:
                self._n_reps_spinbox.setEnabled(False)
            else:
                self._n_reps_spinbox.setEnabled(True)

        self._continuous_checkbox.toggled.connect(on_continuous_toggled)

        n_reps_layout = QHBoxLayout()
        n_reps_layout.addWidget(self._n_reps_spinbox)
        n_reps_layout.addWidget(self._continuous_checkbox)

        sleep_label = QLabel("Sleep", self)
        sleep_label.setFixedWidth(100)

        self._sleep_s_spinbox = QDoubleSpinBox(self)
        self._sleep_s_spinbox.setMinimum(0)
        self._sleep_s_spinbox.setSingleStep(0.0001)
        self._sleep_s_spinbox.setDecimals(4)
        self._sleep_s_spinbox.setValue(0.1)
        self._sleep_s_spinbox.setSuffix(" s")

        widget_layout = QGridLayout()

        row = 0
        col = 0
        widget_layout.addWidget(probe_amp_label, row, col)
        col += 1
        widget_layout.addWidget(self._probe_amp_spinbox, row, col, 1, 3)

        row += 1
        col = 0
        widget_layout.addWidget(probe_size_label, row, col)
        col += 1
        widget_layout.addWidget(self._probe_size, row, col, 1, 3)

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
        widget_layout.addWidget(self._sleep_s_spinbox, row, col, 1, 3)

        self.setLayout(widget_layout)

    @property
    def probe_amplitude(self) -> float:
        return self._probe_amp_spinbox.value()

    @property
    def probe_size(self) -> tuple[int, int]:
        return tuple(self._probe_size.value())

    @property
    def probe_directions(self) -> list[DOTFProbeDirection]:
        return self.probe_dir_checkboxes.value()

    @property
    def continuous(self) -> bool:
        return self._continuous_checkbox.isChecked()

    @property
    def n_reps(self) -> int | None:
        return None if self.continuous else self._n_reps_spinbox.value()

    @property
    def sleep_s(self) -> float:
        return self._sleep_s_spinbox.value()


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
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setWindowTitle("DOTF Measurement Process")
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

    def on_source_changed(self, device: Camera):
        self.devices_widget.source_info_button.setEnabled(True)
        self.devices_widget.source_settings_button.setEnabled(True)
        self.devices_widget.source_preview_button.setEnabled(True)
        self._source = device
        device_preview_window_id = f"{device.name}_preview_window"
        if device_preview_window_id in testbed.data.windows:
            testbed.data.windows.pop(device_preview_window_id).close()
        device_info_window_id = f"{device.name}_info_window"
        if device_info_window_id in testbed.data.windows:
            testbed.data.windows.pop(device_info_window_id).close()
        device_settings_window_id = f"{device.name}_settings_window"
        if device_settings_window_id in testbed.data.windows:
            testbed.data.windows.pop(device_settings_window_id).close()
        if process_info_window_id in testbed.data.windows:
            testbed.data.windows.pop(process_info_window_id).close()
        self.devices_widget.source_info_button.clicked.connect(lambda _, _device=device: self.open_device_info_window(_device))
        self.devices_widget.source_settings_button.clicked.connect(lambda _, _device=device: self.open_device_settings_window(_device))
        self.devices_widget.source_preview_button.clicked.connect(lambda _, _device=device: self.open_device_preview_window(_device))
        if self.source is not None and self.sink is not None:
            self.controls_widget.info_button.setEnabled(True)
            self.controls_widget.play_pause_button.setEnabled(True)

    def on_sink_changed(self, device: Modulator):
        self.devices_widget.sink_info_button.setEnabled(True)
        self.devices_widget.sink_settings_button.setEnabled(True)
        self.devices_widget.sink_preview_button.setEnabled(True)
        self._sink = device
        device_preview_window_id = f"{device.name}_preview_window"
        if device_preview_window_id in testbed.data.windows:
            testbed.data.windows.pop(device_preview_window_id).close()
        device_info_window_id = f"{device.name}_info_window"
        if device_info_window_id in testbed.data.windows:
            testbed.data.windows.pop(device_info_window_id).close()
        device_settings_window_id = f"{device.name}_settings_window"
        if device_settings_window_id in testbed.data.windows:
            testbed.data.windows.pop(device_settings_window_id).close()
        if process_info_window_id in testbed.data.windows:
            testbed.data.windows.pop(process_info_window_id).close()
        self.devices_widget.sink_info_button.clicked.connect(lambda _, _device=device: self.open_device_info_window(_device))
        self.devices_widget.sink_settings_button.clicked.connect(lambda _, _device=device: self.open_device_settings_window(_device))
        self.devices_widget.sink_preview_button.clicked.connect(lambda _, _device=device: self.open_device_preview_window(_device))
        if self.source is not None and self.sink is not None:
            self.controls_widget.info_button.setEnabled(True)
            self.controls_widget.play_pause_button.setEnabled(True)

    def open_device_info_window(self, device: Camera | Modulator):
        device_info_window_id = f"{device.name}_info_window"

        @Slot()
        def on_window_closed():
            testbed.data.windows.pop(device_info_window_id, None)

        if device_info_window_id not in testbed.data.windows:
            info_window: CameraInfoWindow | ModulatorInfoWindow | None = None
            if isinstance(device, Camera):
                info_window = CameraInfoWindow(device, self)
                if process_worker_id in testbed.data.workers:  # an update worker is in progress
                    testbed.data.workers[process_worker_id].signals.srcSampled.connect(info_window.on_sampled)
            elif isinstance(device, Modulator):
                info_window = ModulatorInfoWindow(device, self)
                if process_worker_id in testbed.data.workers:  # an update worker is in progress
                    testbed.data.workers[process_worker_id].signals.snkSampled.connect(info_window.on_sampled)
            else:
                raise ValueError("Invalid device")
            info_window.destroyed.connect(on_window_closed)
            info_window.show()
            info_window.raise_()
            info_window.activateWindow()
            testbed.data.windows[device_info_window_id] = info_window

    def open_device_settings_window(self, device: Camera | Modulator):
        device_settings_window_id = f"{device.name}_settings_window"

        @Slot()
        def on_window_closed():
            testbed.data.windows.pop(device_settings_window_id, None)

        if device_settings_window_id not in testbed.data.windows:
            settings_window: CameraSettingsWindow | ModulatorSettingsWindow | None = None
            if isinstance(device, Camera):
                settings_window = CameraSettingsWindow(device, self)
            elif isinstance(device, Modulator):
                settings_window = ModulatorSettingsWindow(device, self)
            else:
                raise ValueError("Invalid device")
            settings_window.destroyed.connect(on_window_closed)
            settings_window.show()
            settings_window.raise_()
            settings_window.activateWindow()
            testbed.data.windows[device_settings_window_id] = settings_window

    def open_device_preview_window(self, device: Camera | Modulator):
        device_preview_window_id = f"{device.name}_preview_window"

        @Slot()
        def on_window_closed():
            testbed.data.windows.pop(device_preview_window_id, None)

        if device_preview_window_id not in testbed.data.windows:
            preview_window: CameraPreviewWindow | ModulatorPreviewWindow | None = None
            if isinstance(device, Camera):
                preview_window = CameraPreviewWindow(device, self)
                if process_worker_id in testbed.data.workers:  # an update worker is in progress
                    testbed.data.workers[process_worker_id].signals.srcSampled.connect(preview_window.on_sampled)
            elif isinstance(device, Modulator):
                preview_window = ModulatorPreviewWindow(device, self)
                if process_worker_id in testbed.data.workers:  # an update worker is in progress
                    testbed.data.workers[process_worker_id].signals.snkSampled.connect(preview_window.on_sampled)
            else:
                raise ValueError("Invalid device")
            preview_window.destroyed.connect(on_window_closed)
            preview_window.show()
            preview_window.raise_()
            preview_window.activateWindow()
            testbed.data.windows[device_preview_window_id] = preview_window

    @Slot(int, float)  # step, elapsed_time
    def on_progress_tick(self, step: int, t_elapsed: float):
        self.controls_widget.progressbar.setValue(step + 1)
        self.controls_widget.progressbar.setTime(t_elapsed)
        self.controls_widget.progressbar.updateProgress()

    @Slot()
    def on_finished(self):
        self.controls_widget.progressbar.reset()
        self.controls_widget.progressbar.updateProgress()
        if process_worker_id in testbed.data.workers:  # an update worker is in progress
            current_worker = testbed.data.workers.pop(process_worker_id)
            current_worker.stop()
            self.controls_widget.play_pause_button.setIcon(QIcon(ICON_RUN))
            self.devices_widget.sink_settings_button.setEnabled(True)
            self.devices_widget.source_settings_button.setEnabled(True)

    @Slot()
    def on_source_storage_finished(self):
        if source_storage_worker_id in testbed.data.workers:
            source_storage_worker = testbed.data.workers.pop(source_storage_worker_id)
            source_storage_worker.stop()

    @Slot()
    def on_sink_storage_finished(self):
        if sink_storage_worker_id in testbed.data.workers:
            sink_storage_worker = testbed.data.workers.pop(sink_storage_worker_id)
            sink_storage_worker.stop()

    @Slot()
    def on_start_stop_clicked(self):
        if self.source is None or self.sink is None:
            message_dialog = MessageDialog("Devices not selected", "Source and sink devices not selected.", icon=QMessageBox.Icon.Information, buttons=QMessageBox.StandardButton.Ok)
            message_dialog.exec()
        else:
            source_preview_window_id = f"{self.source.name}_preview_window"
            sink_preview_window_id = f"{self.sink.name}_preview_window"

            if process_worker_id in testbed.data.workers:  # an update worker is in progress
                current_worker = testbed.data.workers.pop(process_worker_id)
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

            if self.settings_widget.continuous:
                self.controls_widget.progressbar.setMaximum(0)
            else:
                self.controls_widget.progressbar.setMaximum(self.settings_widget.n_reps)

            worker = ProcessWorker(self.source, self.sink, self.settings_widget.probe_amplitude, self.settings_widget.probe_size, self.settings_widget.probe_directions, self.settings_widget.n_reps)
            worker.signals.progressTicked.connect(self.on_progress_tick)
            worker.signals.finished.connect(self.on_finished)

            self.controls_widget.play_pause_button.setIcon(QIcon(ICON_PAUSE))
            self.devices_widget.sink_settings_button.setEnabled(False)
            self.devices_widget.source_settings_button.setEnabled(False)

            if source_preview_window_id in testbed.data.windows:
                worker.signals.srcSampled.connect(testbed.data.windows[source_preview_window_id].on_sampled)
            if sink_preview_window_id in testbed.data.windows:
                worker.signals.snkSampled.connect(testbed.data.windows[sink_preview_window_id].on_sampled)
            if process_info_window_id in testbed.data.windows:
                worker.signals.dotfMeasured.connect(testbed.data.windows[process_info_window_id].on_dotf_measured)

            testbed.data.workers[process_worker_id] = worker
            testbed.data.threadpool.start(worker)

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
                testbed.data.workers[process_worker_id].signals.dotfMeasured.connect(testbed.data.windows[process_info_window_id].on_dotf_measured)

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
