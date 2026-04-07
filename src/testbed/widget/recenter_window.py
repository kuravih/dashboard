import numpy as np

from matplotlib.lines import Line2D
from numpy.typing import NDArray
from pykato.log import setup_logger
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDoubleSpinBox, QGridLayout, QHBoxLayout, QLabel, QSpinBox, QVBoxLayout, QWidget, QMessageBox, QLineEdit

import testbed

from ..device.camera import Camera
from ..device.modulator import Modulator, FULL_STROKE_NM
from ..function import flip_rotate_frame, flip_rotate_points
from ..worker.recenter_worker import ProcessWorker
from .dialog import MessageDialog
from .resource import ICON_PAUSE, ICON_RUN, ICON_CENTER
from ..widget.camera_window import PreviewWindow as CameraPreviewWindow
from ..widget.modulator_window import PreviewWindow as ModulatorPreviewWindow
from ..worker.camera_worker import ProcessWorker as CameraSamplingWorker
from ..worker.modulator_worker import ProcessWorker as ModulatorSamplingWorker
from ..worker.storage_worker import SourceStorageWorker, SinkStorageWorker

from . import DevicesSetupWidget, TaskControlsWidget, Window, IconButton

_PROCESS_ = testbed.RECENTER
process_worker_id = f"{_PROCESS_}_worker"

logger = setup_logger(f"{_PROCESS_}_window", terminator="\n")


class ProcessSettingsWidget(QWidget):
    """
    Re-centering process settings window
    """

    def __init__(self, parent=None):
        self._center = [np.nan, np.nan]
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
        self.n_steps_spinbox.setValue(2)

        n_steps_layout = QHBoxLayout()
        n_steps_layout.addWidget(self.n_steps_spinbox)

        sleep_label = QLabel("Sleep", self)
        sleep_label.setFixedWidth(100)

        self.sleep_s_spinbox = QDoubleSpinBox(self)
        self.sleep_s_spinbox.setMinimum(0)
        self.sleep_s_spinbox.setSingleStep(0.0001)
        self.sleep_s_spinbox.setDecimals(4)
        self.sleep_s_spinbox.setSuffix(" s")
        self.sleep_s_spinbox.setValue(0.1)

        center_label = QLabel("Center", self)
        sleep_label.setFixedWidth(100)

        self.center_xvalue_textbox = QLineEdit(self)
        self.center_xvalue_textbox.setEnabled(False)
        self.center_xvalue_textbox.setText(f"{self._center[0]:.0f}")
        self.center_yvalue_textbox = QLineEdit(self)
        self.center_yvalue_textbox.setEnabled(False)
        self.center_yvalue_textbox.setText(f"{self._center[1]:.0f}")

        self.move_pushbutton = IconButton(QIcon(ICON_CENTER), parent=self)
        self.move_pushbutton.setFixedHeight(self.amplitude_spinbox.sizeHint().height())
        self.move_pushbutton.setFixedWidth(self.amplitude_spinbox.sizeHint().height())
        self.move_pushbutton.setToolTip("Move to center")
        self.move_pushbutton.setEnabled(False)

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
        widget_layout.addWidget(center_label, row, col)
        col += 1
        widget_layout.addWidget(self.center_xvalue_textbox, row, col)
        col += 1
        widget_layout.addWidget(self.center_yvalue_textbox, row, col)
        col += 1
        widget_layout.addWidget(self.move_pushbutton, row, col)

        self.setLayout(widget_layout)

    @property
    def amplitude(self) -> float:
        return FULL_STROKE_NM * self.amplitude_spinbox.value() / 100.0

    @property
    def n_steps(self) -> int:
        return self.n_steps_spinbox.value()

    @property
    def sleep_s(self) -> float:
        return self.sleep_s_spinbox.value()

    @property
    def center(self) -> list[float]:
        return self._center

    @center.setter
    def center(self, value: list[float]):
        self._center = value
        self.center_xvalue_textbox.setText(f"{self._center[0]:.0f}")
        self.center_yvalue_textbox.setText(f"{self._center[1]:.0f}")
        if (self._center[0] != 0) or (self._center[1] != 0):
            self.move_pushbutton.setEnabled(True)


class ProcessWindow(Window):
    """
    Re-centering process window
    """

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Dialog)
        # self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setWindowTitle("Recenter Process")
        self.sink = None
        self.source = None

        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self.setup_main_widget())

        self.speckles = np.full((self.settings_widget.n_steps, 2, 2), np.nan)
        self.speckles_plot = None
        self.center_plot = None

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
        return self._speckles

    @speckles.setter
    def speckles(self, value: NDArray[np.float64]):
        self._speckles = value

    @property
    def speckles_plot(self) -> Line2D | None:
        return self._speckles_plot

    @speckles_plot.setter
    def speckles_plot(self, value: Line2D | None):
        self._speckles_plot = value

    @property
    def center(self) -> list[float]:
        return self.settings_widget.center

    @center.setter
    def center(self, value: list[float]):
        self.settings_widget.center = value

    @property
    def center_plot(self) -> Line2D | None:
        return self._center_plot

    @center_plot.setter
    def center_plot(self, value: Line2D | None):
        self._center_plot = value

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

            self.controls_widget.progressbar.setMaximum(self.settings_widget.n_steps)

            process_worker = ProcessWorker(self.source, self.sink, self.settings_widget.amplitude, self.settings_widget.n_steps)
            process_worker.signals.progressTicked.connect(self.on_progress_tick)
            process_worker.signals.finished.connect(self.on_process_finished)

            self.controls_widget.play_pause_button.setIconHint(QIcon(ICON_PAUSE), "Pause")

            source_preview_window_id = f"{self.source.name}_preview_window"
            if source_preview_window_id in testbed.data.windows:
                source_preview_window: CameraPreviewWindow = testbed.data.windows[source_preview_window_id]
                process_worker.signals.srcSampled.connect(source_preview_window.on_sampled)

                if self.speckles_plot is not None:
                    self.speckles_plot.remove()
                    self.speckles = np.full((self.settings_widget.n_steps, 2, 2), np.nan)

                if self.center_plot is not None:
                    self.center_plot.remove()
                    self.center = [np.nan, np.nan]

                (self.speckles_plot,) = source_preview_window.preview_figure_widget.figure.get_imshow_axes().plot([], [], color="red", marker="o", markersize=10, markerfacecolor="none", linestyle="none")

                @Slot(np.ndarray)
                def on_speckles_located(speckles):
                    self.speckles = speckles

                process_worker.signals.specklesLocated.connect(on_speckles_located)

                (self.center_plot,) = source_preview_window.preview_figure_widget.figure.get_imshow_axes().plot([], [], color="blue", marker="o", markersize=10, markerfacecolor="none", linestyle="none")

                @Slot(float, float)
                def on_center_located(xc: float, yc: float):
                    self.center = [xc, yc]
                    self.settings_widget.center = [xc, yc]

                process_worker.signals.centerLocated.connect(on_center_located)

                source_preview_window.update_timer.stop()
                source_preview_window.update_timer.timeout.disconnect()

                @Slot()
                def on_source_update_timer_tick():
                    source_preview_window.preview_figure_widget.figure.get_image().set_data(flip_rotate_frame(source_preview_window.sample.capture, source_preview_window.preview_figure_widget.flip, source_preview_window.preview_figure_widget.rotation))
                    speckles_x, speckles_y = flip_rotate_points(self.speckles[:, :, 0], self.speckles[:, :, 1], source_preview_window.sample.capture.shape, source_preview_window.preview_figure_widget.flip, source_preview_window.preview_figure_widget.rotation)
                    self.speckles_plot.set_xdata([speckles_x])
                    self.speckles_plot.set_ydata([speckles_y])
                    center_x, center_y = flip_rotate_points(self.center[0], self.center[1], source_preview_window.sample.capture.shape, source_preview_window.preview_figure_widget.flip, source_preview_window.preview_figure_widget.rotation)
                    self.center_plot.set_xdata([center_x])
                    self.center_plot.set_ydata([center_y])
                    source_preview_window.preview_figure_widget.figure.canvas.draw_idle()

                source_preview_window.update_timer.timeout.connect(on_source_update_timer_tick)
                source_preview_window.update_timer.start(100)  # Update window every 100 ms

            sink_preview_window_id = f"{self.sink.name}_preview_window"
            if sink_preview_window_id in testbed.data.windows:
                sink_preview_window: ModulatorPreviewWindow = testbed.data.windows[sink_preview_window_id]
                process_worker.signals.snkSampled.connect(sink_preview_window.on_sampled)

            testbed.data.workers[process_worker_id] = process_worker
            testbed.data.threadpool.start(process_worker)

    @Slot()
    def on_center_move_clicked(self):
        if self.source is None:
            message_dialog = MessageDialog("Devices not selected", "Source device not selected.", icon=QMessageBox.Icon.Information, buttons=QMessageBox.StandardButton.Ok)
            message_dialog.exec()
        else:
            delta = [int(self.source.shape[0] / 2 - self.settings_widget.center[0]), int(self.source.shape[1] / 2 - self.settings_widget.center[1])]
            logger.info("delta %s", delta)
            reply = self.source.move_roi(-delta[0], -delta[1])
            logger.info("reply = %s", reply)

    def setup_main_widget(self) -> QWidget:
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        widget.setLayout(layout)

        self.devices_widget = DevicesSetupWidget(testbed.data.devices, parent=self)
        self.devices_widget.sourceChanged.connect(self.on_source_changed)
        self.devices_widget.sinkChanged.connect(self.on_sink_changed)

        self.settings_widget = ProcessSettingsWidget(self)
        self.settings_widget.move_pushbutton.clicked.connect(self.on_center_move_clicked)

        self.controls_widget = TaskControlsWidget(self)
        self.controls_widget.play_pause_button.clicked.connect(self.on_start_stop_clicked)
        self.controls_widget.info_button.hide()
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
