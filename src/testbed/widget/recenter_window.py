import numpy as np

from pykato.log import setup_logger
from PySide6.QtCore import Qt, Slot, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QCheckBox, QDoubleSpinBox, QGridLayout, QHBoxLayout, QLabel, QSpinBox, QVBoxLayout, QWidget, QMessageBox, QComboBox
from matplotlib import colormaps

import testbed

from ..device.camera import Camera, SourceSample
from ..device.modulator import Modulator, SinkSample
from ..worker.recenter_worker import ProcessWorker
from .camera_window import InfoWindow as CameraInfoWindow
from .camera_window import PreviewWindow as CameraPreviewWindow
from .camera_window import SettingsWindow as CameraSettingsWindow
from .modulator_window import InfoWindow as ModulatorInfoWindow
from .modulator_window import PreviewWindow as ModulatorPreviewWindow
from .modulator_window import SettingsWindow as ModulatorSettingsWindow
from .dialog import MessageDialog
from .figure_widget import RecenteringFigureWidget
from .resource import ICON_PAUSE, ICON_RUN

from . import DevicesSetupWidget, TaskControlsWidget, Window

_PROCESS_ = testbed.RECENTER
process_worker_id = f"{_PROCESS_}_worker"
process_info_window_id = f"{_PROCESS_}_info_window"
source_storage_worker_id = f"{_PROCESS_}_source_storage_worker"
sink_storage_worker_id = f"{_PROCESS_}_sink_storage_worker"

logger = setup_logger(f"{_PROCESS_}_window", terminator="\n")


class ProcessSettingsWidget(QWidget):
    """
    Re-centering process settings window
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        n_steps_label = QLabel("Steps", self)
        n_steps_label.setFixedWidth(100)

        self._n_steps_spinbox = QSpinBox(self)
        self._n_steps_spinbox.setRange(0, 9999)
        self._n_steps_spinbox.setSingleStep(1)
        self._n_steps_spinbox.setValue(2)
        self._n_steps_spinbox.setToolTip("Number of steps")

        n_steps_layout = QHBoxLayout()
        n_steps_layout.addWidget(self._n_steps_spinbox)

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
        widget_layout.addWidget(n_steps_label, row, col)
        col += 1
        widget_layout.addLayout(n_steps_layout, row, col, 1, 3)

        row += 1
        col = 0
        widget_layout.addWidget(sleep_label, row, col)
        col += 1
        widget_layout.addWidget(self._sleep_s_spinbox, row, col, 1, 3)

        self.setLayout(widget_layout)

    @property
    def n_steps(self) -> int:
        return self._n_steps_spinbox.value()

    @property
    def sleep_s(self) -> float:
        return self._sleep_s_spinbox.value()


class ProcessInfoSettingsWindow(Window):
    """
    Settings for the re-centering process info window
    """

    def __init__(self, src_cmap: str, src_cmap_norm: bool, snk_cmap: str, parent=None):
        super().__init__(parent, Qt.WindowType.Dialog)
        self.src_cmap = src_cmap
        self.src_cmap_norm = src_cmap_norm
        self.snk_cmap = snk_cmap
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setWindowTitle("Process Info Settings")
        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self.setup_settings_widget())
        self.setLayout(layout)

    def setup_settings_widget(self) -> QWidget:
        widget = QWidget(self)
        layout = QGridLayout(widget)
        widget.setLayout(layout)

        source_cmap_label = QLabel("Source Colormap", self)
        self.source_cmap_combobox = QComboBox(self)
        self.source_cmap_combobox.addItems(list(colormaps))
        self.source_cmap_combobox.setCurrentIndex(list(colormaps).index(self.src_cmap))
        self.source_log_checkbox = QCheckBox("Log", self)
        self.source_log_checkbox.setToolTip("Log Scale")
        self.source_log_checkbox.setChecked(self.src_cmap_norm)

        sink_cmap_label = QLabel("Sink Colormap", self)
        self.sink_cmap_combobox = QComboBox(self)
        self.sink_cmap_combobox.addItems(list(colormaps))
        self.sink_cmap_combobox.setCurrentIndex(list(colormaps).index(self.snk_cmap))

        row = 0
        col = 0
        layout.addWidget(source_cmap_label, row, col)
        col += 1
        layout.addWidget(self.source_cmap_combobox, row, col)
        col += 1
        layout.addWidget(self.source_log_checkbox, row, col)
 
        row += 1
        col = 0
        layout.addWidget(sink_cmap_label, row, col)
        col += 1
        layout.addWidget(self.sink_cmap_combobox, row, col)

        return widget


class ProcessInfoWindow(Window):
    """
    Re-centering process info window
    """

    def __init__(self, source_sample: SourceSample, sink_sample: SinkSample, parent: QWidget | None = None):
        super().__init__(parent, Qt.WindowType.Dialog)
        self.source_sample = source_sample
        self.sink_sample = sink_sample

        self.speckles = [[np.nan, np.nan], [np.nan, np.nan]]
        self.center = [np.nan, np.nan]

        self.setWindowTitle("Re-centering")

        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self.setup_info_widget())
        self.setLayout(layout)

        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.on_update_timer_tick)
        self.update_timer.start(100)  # Update window every 100 ms

    @Slot(SourceSample)
    def on_src_sampled(self, sample: SourceSample):
        self.source_sample = sample

    @Slot(SinkSample)
    def on_snk_sampled(self, sample: SinkSample):
        self.sink_sample = sample

    @Slot(float, float, float, float)
    def on_speckles_located(self, x1: float, y1: float, x2: float, y2: float):
        self.speckles = [[x1, y1], [x2, y2]]

    @Slot(float, float)
    def on_center_located(self, x: float, y: float):
        self.center = [x, y]

    def setup_info_widget(self) -> QWidget:
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(2, 2, 2, 2)
        widget.setLayout(layout)
        self.process_info_figure = RecenteringFigureWidget(self.source_sample.capture, self.sink_sample.command, show_toolbar=True, parent=self)
        if self.process_info_figure.toolbar is not None:
            self.process_info_figure.toolbar.settingsClicked.connect(self.on_info_settings_clicked)
        layout.addWidget(self.process_info_figure)
        return widget

    @Slot()
    def on_info_settings_clicked(self):
        process_info_settings_window = ProcessInfoSettingsWindow(snk_cmap=self.process_info_figure.snk_cmap_name, src_cmap_log=self.process_info_figure.src_cmap_log, src_cmap=self.process_info_figure.src_cmap_name, parent=self)
        process_info_settings_window.show()
        process_info_settings_window.raise_()
        process_info_settings_window.activateWindow()
        process_info_settings_window.source_log_checkbox.checkStateChanged.connect(self.on_src_cmap_log_changed)
        process_info_settings_window.source_cmap_combobox.currentTextChanged.connect(self.on_src_cmap_changed)
        process_info_settings_window.sink_cmap_combobox.currentTextChanged.connect(self.on_snk_cmap_changed)

    @Slot(str)
    def on_src_cmap_changed(self, colormap: str):
        self.process_info_figure.set_src_cmap(colormap)

    @Slot(str)
    def on_snk_cmap_changed(self, colormap: str):
        self.process_info_figure.set_snk_cmap(colormap)

    @Slot(bool)
    def on_src_cmap_log_changed(self, checked: Qt.CheckState):
        if checked == Qt.CheckState.Checked:
            self.process_info_figure.set_src_cmap_norm(True)
        else:
            self.process_info_figure.set_src_cmap_norm(False)

    @Slot()
    def on_update_timer_tick(self):
        self.process_info_figure.set_command(self.sink_sample.command)
        self.process_info_figure.set_capture(self.source_sample.capture)
        self.process_info_figure.set_speckles(self.speckles)
        self.process_info_figure.set_center(self.center)
        self.process_info_figure.figure.canvas.draw_idle()

    def closeEvent(self, event):
        if self.update_timer.isActive():
            self.update_timer.stop()
        self.deleteLater()
        event.accept()


class ProcessWindow(Window):
    """
    Re-centering process window
    """

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Dialog)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setWindowTitle("Recenter Process")
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

    def on_source_changed(self, _device: Camera):
        self.devices_widget.source_info_button.setEnabled(True)
        self.devices_widget.source_settings_button.setEnabled(True)
        self.devices_widget.source_preview_button.setEnabled(True)
        self._source = _device
        device_preview_window_id = f"{_device.name}_preview_window"
        if device_preview_window_id in testbed.data.windows:
            testbed.data.windows.pop(device_preview_window_id).close()
        device_info_window_id = f"{_device.name}_info_window"
        if device_info_window_id in testbed.data.windows:
            testbed.data.windows.pop(device_info_window_id).close()
        device_settings_window_id = f"{_device.name}_settings_window"
        if device_settings_window_id in testbed.data.windows:
            testbed.data.windows.pop(device_settings_window_id).close()
        self.devices_widget.source_info_button.clicked.connect(lambda _, _device=_device: self.open_device_info_window(_device))
        self.devices_widget.source_settings_button.clicked.connect(lambda _, _device=_device: self.open_device_settings_window(_device))
        self.devices_widget.source_preview_button.clicked.connect(lambda _, _device=_device: self.open_device_preview_window(_device))
        if self._source is not None and self._sink is not None:
            self.controls_widget.info_button.setEnabled(True)
            self.controls_widget.play_pause_button.setEnabled(True)

    def on_sink_changed(self, _device: Modulator):
        self.devices_widget.sink_info_button.setEnabled(True)
        self.devices_widget.sink_settings_button.setEnabled(True)
        self.devices_widget.sink_preview_button.setEnabled(True)
        self._sink = _device
        device_preview_window_id = f"{_device.name}_preview_window"
        if device_preview_window_id in testbed.data.windows:
            testbed.data.windows.pop(device_preview_window_id).close()
        device_info_window_id = f"{_device.name}_info_window"
        if device_info_window_id in testbed.data.windows:
            testbed.data.windows.pop(device_info_window_id).close()
        device_settings_window_id = f"{_device.name}_settings_window"
        if device_settings_window_id in testbed.data.windows:
            testbed.data.windows.pop(device_settings_window_id).close()
        self.devices_widget.sink_info_button.clicked.connect(lambda _, _device=_device: self.open_device_info_window(_device))
        self.devices_widget.sink_settings_button.clicked.connect(lambda _, _device=_device: self.open_device_settings_window(_device))
        self.devices_widget.sink_preview_button.clicked.connect(lambda _, _device=_device: self.open_device_preview_window(_device))
        if self._source is not None and self._sink is not None:
            self.controls_widget.info_button.setEnabled(True)
            self.controls_widget.play_pause_button.setEnabled(True)

    def open_device_info_window(self, _device: Camera | Modulator):
        device_info_window_id = f"{_device.name}_info_window"

        @Slot()
        def on_window_closed():
            testbed.data.windows.pop(device_info_window_id, None)

        if device_info_window_id not in testbed.data.windows:
            info_window: CameraInfoWindow | ModulatorInfoWindow | None = None
            if isinstance(_device, Camera):
                info_window = CameraInfoWindow(_device, self)
                if process_worker_id in testbed.data.workers:  # an update worker is in progress
                    testbed.data.workers[process_worker_id].signals.srcSampled.connect(info_window.on_sampled)
            elif isinstance(_device, Modulator):
                info_window = ModulatorInfoWindow(_device, self)
                if process_worker_id in testbed.data.workers:  # an update worker is in progress
                    testbed.data.workers[process_worker_id].signals.snkSampled.connect(info_window.on_sampled)
            else:
                raise ValueError("Invalid device")
            info_window.destroyed.connect(on_window_closed)
            info_window.show()
            info_window.raise_()
            info_window.activateWindow()
            testbed.data.windows[device_info_window_id] = info_window

    def open_device_settings_window(self, _device: Camera | Modulator):
        device_settings_window_id = f"{_device.name}_settings_window"

        @Slot()
        def on_window_closed():
            testbed.data.windows.pop(device_settings_window_id, None)

        if device_settings_window_id not in testbed.data.windows:
            settings_window: CameraSettingsWindow | ModulatorSettingsWindow | None = None
            if isinstance(_device, Camera):
                settings_window = CameraSettingsWindow(_device, self)
            elif isinstance(_device, Modulator):
                settings_window = ModulatorSettingsWindow(_device, self)
            else:
                raise ValueError("Invalid device")
            settings_window.destroyed.connect(on_window_closed)
            settings_window.show()
            settings_window.raise_()
            settings_window.activateWindow()
            testbed.data.windows[device_settings_window_id] = settings_window

    def open_device_preview_window(self, _device: Camera | Modulator):
        device_preview_window_id = f"{_device.name}_preview_window"

        @Slot()
        def on_window_closed():
            testbed.data.windows.pop(device_preview_window_id, None)

        if device_preview_window_id not in testbed.data.windows:
            preview_window: CameraPreviewWindow | ModulatorPreviewWindow | None = None
            if isinstance(_device, Camera):
                preview_window = CameraPreviewWindow(_device, self)
                if process_worker_id in testbed.data.workers:  # an update worker is in progress
                    testbed.data.workers[process_worker_id].signals.srcSampled.connect(preview_window.on_sampled)
            elif isinstance(_device, Modulator):
                preview_window = ModulatorPreviewWindow(_device, self)
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

            worker = ProcessWorker(self.source, self.sink, self.settings_widget.n_steps)
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
                worker.signals.srcSampled.connect(testbed.data.windows[process_info_window_id].on_src_sampled)
                worker.signals.snkSampled.connect(testbed.data.windows[process_info_window_id].on_snk_sampled)
                worker.signals.specklesLocated.connect(testbed.data.windows[process_info_window_id].on_speckles_located)
                worker.signals.centerLocated.connect(testbed.data.windows[process_info_window_id].on_center_located)

            testbed.data.workers[process_worker_id] = worker
            testbed.data.threadpool.start(worker)

    def open_process_info_clicked(self):
        @Slot()
        def on_window_closed():
            testbed.data.windows.pop(process_info_window_id, None)

        if process_info_window_id not in testbed.data.windows and self._source is not None and self._sink is not None:
            process_info_window = ProcessInfoWindow(self._source.sample, self._sink.sample, parent=self)
            process_info_window.destroyed.connect(on_window_closed)
            process_info_window.show()
            process_info_window.raise_()
            process_info_window.activateWindow()
            testbed.data.windows[process_info_window_id] = process_info_window

            if process_worker_id in testbed.data.workers:
                testbed.data.workers[process_worker_id].signals.srcSampled.connect(testbed.data.windows[process_info_window_id].on_src_sampled)
                testbed.data.workers[process_worker_id].signals.snkSampled.connect(testbed.data.windows[process_info_window_id].on_snk_sampled)
                testbed.data.workers[process_worker_id].signals.specklesLocated.connect(testbed.data.windows[process_info_window_id].on_speckles_located)
                testbed.data.workers[process_worker_id].signals.centerLocated.connect(testbed.data.windows[process_info_window_id].on_center_located)

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
