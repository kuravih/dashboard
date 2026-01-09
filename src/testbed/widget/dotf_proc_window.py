from collections.abc import Iterator
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QVBoxLayout, QWidget, QLabel, QSpinBox, QHBoxLayout, QCheckBox, QDoubleSpinBox, QGridLayout
from PySide6.QtCore import Slot, Qt

from pykato.log import setup_logger
from pykato.function import DOTFProbeDirection

import testbed
from ..device.camera import Camera
from ..device.modulator import Modulator
from ..device.mirror import Mirror

from .camera_window import PreviewWindow as CameraPreviewWindow
from .modulator_window import PreviewWindow as ModulatorPreviewWindow
from .mirror_window import PreviewWindow as MirrorPreviewWindow
from ..worker.simple_proc_worker import SimpleProcWorker

from ..widget import DevicesSetupWidget, TaskControlsWidget
from ..widget.resource import ICON_RUN, ICON_PAUSE

logger = setup_logger("dotf_proc_window", terminator="\n")


class DOTFProbeDirectionWidget(QWidget):
    """
    Widget with four checkboxes for the four DOTF probes (03, 06, 09 & 12 o'clock).

    Function:
        value(): list[DOTFProbeDirection]
            List of DOTFProbeDirection.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self._checkboxes = []
        for _direction in DOTFProbeDirection:  # pylint: disable=invalid-name
            checkbox = QCheckBox(_direction.to_str(), self)
            checkbox.toggled.connect(self._on_checkbox_toggled)
            self._checkboxes.append(checkbox)
            layout.addWidget(checkbox)

        self.setLayout(layout)

    def __getitem__(self, index) -> QCheckBox:
        return self._checkboxes[index]

    def __iter__(self) -> Iterator[QCheckBox]:
        return iter(self._checkboxes)

    def _on_checkbox_toggled(self):
        if not any(checkbox.isChecked() for checkbox in self._checkboxes):
            sender = self.sender()
            if isinstance(sender, QCheckBox):
                sender.blockSignals(True)
                sender.setChecked(True)
                sender.blockSignals(False)

    def value(self) -> list[DOTFProbeDirection]:
        return [direction for checkbox, direction in zip(self._checkboxes, DOTFProbeDirection) if checkbox.isChecked()]


class DOTFProcSettingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        n_steps_label = QLabel("Steps", self)
        n_steps_label.setFixedWidth(100)

        self._n_steps_spinbox = QSpinBox(self)
        self._n_steps_spinbox.setRange(0, 9999)
        self._n_steps_spinbox.setSingleStep(1)
        self._n_steps_spinbox.setValue(9)
        self._n_steps_spinbox.setToolTip("Number of steps")

        self._continuous_checkbox = QCheckBox("continuous", self)
        self._continuous_checkbox.setToolTip("Run till stop/pause button is clicked")
        self._continuous_checkbox.setMaximumWidth(100)

        @Slot(bool)
        def on_continuous_checkbox_toggle(checked: bool):
            if checked:
                self._n_steps_spinbox.setEnabled(False)
            else:
                self._n_steps_spinbox.setEnabled(True)

        self._continuous_checkbox.toggled.connect(on_continuous_checkbox_toggle)

        n_steps_layout = QHBoxLayout()
        n_steps_layout.addWidget(self._n_steps_spinbox)
        n_steps_layout.addWidget(self._continuous_checkbox)

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
    def continuous(self) -> bool:
        return self._continuous_checkbox.isChecked()

    @property
    def n_steps(self) -> int | None:
        return None if self.continuous else self._n_steps_spinbox.value()

    @property
    def sleep_s(self) -> float:
        return self._sleep_s_spinbox.value()


class DOTFProcWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Dialog)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setWindowTitle("DOTF Process")
        self._sink = None
        self._source = None

        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self.setup_main_widget())
        self.setLayout(layout)

    @property
    def source(self) -> Camera:
        return self._source

    @property
    def sink(self) -> Modulator | Mirror:
        return self._sink

    def on_source_change(self, _device: Camera):
        self._source = _device
        # self.open_device_preview_window(_device) # TODO: uncomment
        self.devices_widget.source_preview_button.clicked.connect(lambda _, _device=_device: self.open_device_preview_window(_device))

    def on_sink_change(self, _device: Modulator | Mirror):
        self._sink = _device
        # self.open_device_preview_window(_device) # TODO: uncomment
        self.devices_widget.sink_preview_button.clicked.connect(lambda _, _device=_device: self.open_device_preview_window(_device))

    def open_device_preview_window(self, _device: Camera | Modulator | Mirror):

        window_name = _device.name + "_preview"

        def close_window():
            testbed.data.windows.pop(window_name, None)

        if window_name not in testbed.data.windows:
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
        proc_worker_id = "simple_proc_worker"
        self.controls_widget.progressbar.reset()
        self.controls_widget.progressbar.updateProgress()
        if proc_worker_id in testbed.data.workers:  # an update worker is in progress
            current_proc_worker = testbed.data.workers.pop(proc_worker_id)
            current_proc_worker.stop()
            self.controls_widget.play_pause_button.setIcon(QIcon(ICON_RUN))

    def on_start_stop(self):
        proc_worker_id = "simple_proc_worker"
        source_preview_window_name = self.source.name + "_preview"
        sink_preview_window_name = self.sink.name + "_preview"

        if proc_worker_id in testbed.data.workers:  # an update worker is in progress
            current_proc_worker = testbed.data.workers.pop(proc_worker_id)
            current_proc_worker.stop()
            self.controls_widget.play_pause_button.setIcon(QIcon(ICON_RUN))
            self.controls_widget.progressbar.setMaximum(100)
            self.controls_widget.progressbar.reset()
            self.controls_widget.progressbar.updateProgress()
            return

        if self.settings_widget.continuous:
            self.controls_widget.progressbar.setMaximum(0)
        else:
            self.controls_widget.progressbar.setMaximum(self.settings_widget.n_steps)

        proc_worker = SimpleProcWorker(self.source, self.sink, self.settings_widget.n_steps)
        proc_worker.signals.progress.connect(self.on_progress)
        proc_worker.signals.finished.connect(self.on_finish)

        testbed.data.threadpool.start(proc_worker)
        self.controls_widget.play_pause_button.setIcon(QIcon(ICON_PAUSE))

        if source_preview_window_name in testbed.data.windows:
            proc_worker.signals.new_source_sample.connect(testbed.data.windows[source_preview_window_name].on_new_sample)
        if sink_preview_window_name in testbed.data.windows:
            proc_worker.signals.new_sink_sample.connect(testbed.data.windows[sink_preview_window_name].on_new_sample)

        testbed.data.workers[proc_worker_id] = proc_worker

    def setup_main_widget(self) -> QWidget:
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        widget.setLayout(layout)

        self.devices_widget = DevicesSetupWidget(testbed.data.devices, parent=self)
        self.devices_widget.source_changed.connect(self.on_source_change)
        self.devices_widget.sink_changed.connect(self.on_sink_change)

        self.settings_widget = DOTFProcSettingsWidget(self)
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
        source_preview_window_name = self.source.name + "_preview"
        sink_preview_window_name = self.sink.name + "_preview"
        if (source_preview_window_name in testbed.data.windows) or (sink_preview_window_name in testbed.data.windows):
            logger.info("Cannot close main window until preview windows are closed.")
            event.ignore()
        else:
            while testbed.data.workers:
                key, worker = testbed.data.workers.popitem()
                worker.stop()
                logger.info("stopping worker %s", key)
            self.deleteLater()
            event.accept()
