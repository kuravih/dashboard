import sys
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMainWindow, QPushButton, QFileDialog, QMessageBox, QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView
from PySide6.QtCore import Slot, QFileInfo

import testbed
from testbed.device import Stream

from testbed.device.camera import Camera
from testbed.widget.camera_window import PreviewWindow as CameraPreviewWindow, InfoWindow as CameraInfoWindow, SettingsWindow as CameraSettingsWindow
from testbed.worker.camera_worker import UpdateWorker as CameraUpdateWorker

from testbed.device.modulator import Modulator
from testbed.widget.modulator_window import PreviewWindow as ModulatorPreviewWindow, InfoWindow as ModulatorInfoWindow, SettingsWindow as ModulatorSettingsWindow
from testbed.worker.modulator_worker import UpdateWorker as ModulatorUpdateWorker

from testbed.device.mirror import Mirror
from testbed.widget.mirror_window import PreviewWindow as MirrorPreviewWindow, InfoWindow as MirrorInfoWindow, SettingsWindow as MirrorSettingsWindow
from testbed.worker.mirror_worker import UpdateWorker as MirrorUpdateWorker

from testbed.widget.simple_proc_window import SimpleProcWindow
from testbed.widget.speckle_cal_proc_window import SpeckleCalProcWindow
from testbed.widget.speckle_null_proc_window import SpeckleNullProcWindow
from testbed.widget.dotf_proc_window import DOTFProcWindow

from testbed.widget.dialog import MessageDialog
from testbed.widget.resource import ICON_EYE, ICON_GEAR, ICON_INFO, ICON_TRASH, ICON_PLAY, ICON_PAUSE

from pykato.log import setup_logger

logger = setup_logger("dashboard", terminator="\n")


class MainWindow(QMainWindow):
    """
    Main Window
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Testbed Controls")

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Name", "Kind", "Shape", "Dtype", ""])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)

        add_device_button = QPushButton("Add Device")
        add_device_button.clicked.connect(self.add_device_callback)

        remove_device_button = QPushButton("Remove Device")
        remove_device_button.clicked.connect(self.remove_device_callback)

        simple_proc_button = QPushButton("Simple Process")
        simple_proc_button.clicked.connect(self.open_simple_proc_window)

        speckle_cal_proc_button = QPushButton("Speckle Calibration Process")
        speckle_cal_proc_button.clicked.connect(self.open_speckle_cal_proc_window)

        speckle_null_proc_button = QPushButton("Speckle Nulling Process")
        speckle_null_proc_button.clicked.connect(self.open_speckle_null_proc_window)

        dotf_proc_button = QPushButton("DOTF Process")
        dotf_proc_button.clicked.connect(self.open_dotf_proc_window)

        device_button_layout = QHBoxLayout()
        device_button_layout.addWidget(add_device_button)
        device_button_layout.addWidget(remove_device_button)

        # Layout setup
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(self.table)
        layout.addLayout(device_button_layout)
        layout.addWidget(simple_proc_button)
        layout.addWidget(speckle_cal_proc_button)
        layout.addWidget(speckle_null_proc_button)
        layout.addWidget(dotf_proc_button)
        self.setCentralWidget(container)

    def open_preview_window(self, _device: Camera | Modulator | Mirror):

        window_name = _device.name + "_preview"
        update_worker_id = _device.name + "_worker"

        @Slot()
        def close_window():
            if update_worker_id in testbed.data.workers:
                testbed.data.workers[update_worker_id].signals.new_sample.disconnect(testbed.data.windows[window_name].on_new_sample)
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

            if update_worker_id in testbed.data.workers:
                testbed.data.workers[update_worker_id].signals.new_sample.connect(testbed.data.windows[window_name].on_new_sample)

    def open_info_window(self, _device: Camera | Modulator | Mirror):

        window_name = _device.name + "_info"
        update_worker_id = _device.name + "_worker"

        @Slot()
        def close_window():
            if update_worker_id in testbed.data.workers:
                testbed.data.workers[update_worker_id].signals.new_sample.disconnect(testbed.data.windows[window_name].on_new_sample)
            testbed.data.windows.pop(window_name, None)

        if window_name not in testbed.data.windows:
            if isinstance(_device, Camera):
                window = CameraInfoWindow(_device)
            elif isinstance(_device, Modulator):
                window = ModulatorInfoWindow(_device)
            elif isinstance(_device, Mirror):
                window = MirrorInfoWindow(_device)
            else:
                raise ValueError("Invalid device")
            window.destroyed.connect(close_window)
            window.show()
            window.raise_()
            window.activateWindow()
            testbed.data.windows[window_name] = window

            if update_worker_id in testbed.data.workers:
                testbed.data.workers[update_worker_id].signals.new_sample.connect(testbed.data.windows[window_name].on_new_sample)

    def open_settings_window(self, _device: Camera | Modulator | Mirror):

        window_name = _device.name + "_settings"
        update_worker_id = _device.name + "_worker"

        @Slot()
        def close_window():
            if update_worker_id in testbed.data.workers:
                testbed.data.workers[update_worker_id].signals.new_sample.disconnect(testbed.data.windows[window_name].on_new_sample)
            testbed.data.windows.pop(window_name, None)

        if window_name not in testbed.data.windows:
            if isinstance(_device, Camera):
                window = CameraSettingsWindow(_device)
            elif isinstance(_device, Modulator):
                window = ModulatorSettingsWindow(_device)
            elif isinstance(_device, Mirror):
                window = MirrorSettingsWindow(_device)
            else:
                raise ValueError("Invalid device")
            window.destroyed.connect(close_window)
            window.show()
            window.raise_()
            window.activateWindow()
            testbed.data.windows[window_name] = window

            if update_worker_id in testbed.data.workers:
                testbed.data.workers[update_worker_id].signals.new_sample.connect(testbed.data.windows[window_name].on_new_sample)

    def on_start_stop(self, _device: Camera | Modulator | Mirror, _button: QPushButton):

        update_worker_id = _device.name + "_worker"
        preview_window_name = _device.name + "_preview"
        info_window_name = _device.name + "_info"
        settings_window_name = _device.name + "_settings"

        if update_worker_id in testbed.data.workers:  # an update worker is in progress
            current_update_worker = testbed.data.workers.pop(update_worker_id)
            current_update_worker.stop()
            _button.setIcon(QIcon(ICON_PLAY))
            return

        if isinstance(_device, Camera):
            update_worker = CameraUpdateWorker(_device)
        elif isinstance(_device, Modulator):
            update_worker = ModulatorUpdateWorker(_device)
        elif isinstance(_device, Mirror):
            update_worker = MirrorUpdateWorker(_device)
        else:
            raise ValueError("Invalid device")

        testbed.data.threadpool.start(update_worker)
        _button.setIcon(QIcon(ICON_PAUSE))

        if preview_window_name in testbed.data.windows:
            update_worker.signals.new_sample.connect(testbed.data.windows[preview_window_name].on_new_sample)
        if info_window_name in testbed.data.windows:
            update_worker.signals.new_sample.connect(testbed.data.windows[info_window_name].on_new_sample)
        if settings_window_name in testbed.data.windows:
            update_worker.signals.new_sample.connect(testbed.data.windows[settings_window_name].on_new_sample)

        testbed.data.workers[update_worker_id] = update_worker

    @Slot()
    def add_device_callback(self):
        dialog_filenames, _ = QFileDialog.getOpenFileNames(self, "Open Device Streams", "/dev/shm", "Streams (*.shm)", options=QFileDialog.Option.DontUseNativeDialog)
        for dialog_filename in dialog_filenames:
            stream_name = QFileInfo(dialog_filename).completeBaseName()

            if stream_name not in testbed.data.devices:
                stream = Stream(stream_name)
                row = self.table.rowCount()
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(stream.name))
                self.table.setItem(row, 1, QTableWidgetItem(stream.kind.to_str()))

                cell_widget = QWidget()
                button_layout = QHBoxLayout(cell_widget)
                button_layout.setContentsMargins(0, 0, 0, 0)

                info_button = QPushButton(QIcon(ICON_INFO), "", flat=True)
                info_button.setFixedWidth(info_button.sizeHint().height())
                info_button.setToolTip("Information")
                button_layout.addWidget(info_button)

                settings_button = QPushButton(QIcon(ICON_GEAR), "", flat=True)
                settings_button.setFixedWidth(settings_button.sizeHint().height())
                settings_button.setToolTip("Settings")
                button_layout.addWidget(settings_button)

                preview_button = QPushButton(QIcon(ICON_EYE), "", flat=True)
                preview_button.setFixedWidth(preview_button.sizeHint().height())
                preview_button.setToolTip("Preview")
                button_layout.addWidget(preview_button)

                play_pause_button = QPushButton(QIcon(ICON_PLAY), "", flat=True)
                play_pause_button.setFixedWidth(play_pause_button.sizeHint().height())
                play_pause_button.setToolTip("Play")
                button_layout.addWidget(play_pause_button)

                if stream.kind == Stream.Kind.CAMERA:
                    camera = Camera(stream)
                    self.table.setItem(row, 2, QTableWidgetItem(str(camera.shape)))
                    self.table.setItem(row, 3, QTableWidgetItem("dtype"))
                    preview_button.clicked.connect(lambda _, _camera=camera: self.open_preview_window(_camera))
                    info_button.clicked.connect(lambda _, _camera=camera: self.open_info_window(_camera))
                    settings_button.clicked.connect(lambda _, _camera=camera: self.open_settings_window(_camera))
                    play_pause_button.clicked.connect(lambda _, _button=play_pause_button, _camera=camera: self.on_start_stop(_camera, _button))
                    testbed.data.devices[stream_name] = camera
                    # self.on_start_stop(camera, play_pause_button) # TODO: uncomment
                    # self.open_preview_window(camera) # TODO: uncomment
                elif stream.kind == Stream.Kind.SLM:
                    modulator = Modulator(stream)
                    self.table.setItem(row, 2, QTableWidgetItem(str(modulator.shape)))
                    self.table.setItem(row, 3, QTableWidgetItem("dtype"))
                    preview_button.clicked.connect(lambda _, _modulator=modulator: self.open_preview_window(_modulator))
                    info_button.clicked.connect(lambda _, _modulator=modulator: self.open_info_window(_modulator))
                    settings_button.clicked.connect(lambda _, _modulator=modulator: self.open_settings_window(_modulator))
                    play_pause_button.clicked.connect(lambda _, _button=play_pause_button, _modulator=modulator: self.on_start_stop(_modulator, _button))
                    testbed.data.devices[stream_name] = modulator
                    # self.on_start_stop(modulator, play_pause_button) # TODO: uncomment
                    # self.open_preview_window(modulator) # TODO: uncomment
                elif stream.kind == Stream.Kind.DM:
                    mirror = Mirror(stream)
                    self.table.setItem(row, 2, QTableWidgetItem(str(mirror.shape)))
                    self.table.setItem(row, 3, QTableWidgetItem("dtype"))
                    preview_button.clicked.connect(lambda _, _mirror=mirror: self.open_preview_window(_mirror))
                    info_button.clicked.connect(lambda _, _mirror=mirror: self.open_info_window(_mirror))
                    settings_button.clicked.connect(lambda _, _mirror=mirror: self.open_settings_window(_mirror))
                    play_pause_button.clicked.connect(lambda _, _button=play_pause_button, _mirror=mirror: self.on_start_stop(_mirror, _button))
                    testbed.data.devices[stream_name] = mirror
                    # self.on_start_stop(mirror, play_pause_button) # TODO: uncomment
                    # self.open_preview_window(mirror) # TODO: uncomment

                trash_button = QPushButton(QIcon(ICON_TRASH), "", flat=True)
                trash_button.setFixedWidth(trash_button.sizeHint().height())
                trash_button.setToolTip("Delete")
                trash_button.clicked.connect(self.remove_device_callback)
                button_layout.addWidget(trash_button)

                self.table.setCellWidget(row, 4, cell_widget)

            else:
                message_dialog = MessageDialog("Device available", "Device already available. Access via device menu.", icon=QMessageBox.Icon.Information, buttons=QMessageBox.StandardButton.Ok)
                message_dialog.exec()

    @Slot()
    def remove_device_callback(self):
        for index in sorted(set(i.row() for i in self.table.selectedIndexes()), reverse=True):
            for _index, _device in enumerate(testbed.data.devices):
                if self.table.item(index, 0).text() == _device.name:
                    logger.info("Device name %s, %d, table value %s ", _device.name, _index, self.table.item(index, 0).text())
                    testbed.data.devices.pop(index)
            self.table.removeRow(index)

    @Slot()
    def open_simple_proc_window(self):

        window_name = "simple_proc_window"

        @Slot()
        def close_window():
            testbed.data.windows.pop(window_name, None)

        if window_name not in testbed.data.windows:
            window = SimpleProcWindow(self)
            window.destroyed.connect(close_window)
            window.show()
            window.raise_()
            window.activateWindow()
            testbed.data.windows[window_name] = window

    @Slot()
    def open_speckle_cal_proc_window(self):

        window_name = "speckle_cal_proc_window"

        @Slot()
        def close_window():
            testbed.data.windows.pop(window_name, None)

        if window_name not in testbed.data.windows:
            window = SpeckleCalProcWindow(self)
            window.destroyed.connect(close_window)
            window.show()
            window.raise_()
            window.activateWindow()
            testbed.data.windows[window_name] = window

    @Slot()
    def open_speckle_null_proc_window(self):

        window_name = "speckle_null_proc_window"

        @Slot()
        def close_window():
            testbed.data.windows.pop(window_name, None)

        if window_name not in testbed.data.windows:
            window = SpeckleNullProcWindow(self)
            window.destroyed.connect(close_window)
            window.show()
            window.raise_()
            window.activateWindow()
            testbed.data.windows[window_name] = window

    @Slot()
    def open_dotf_proc_window(self):

        window_name = "dotf_proc_window"

        @Slot()
        def close_window():
            testbed.data.windows.pop(window_name, None)

        if window_name not in testbed.data.windows:
            window = DOTFProcWindow(self)
            window.destroyed.connect(close_window)
            window.show()
            window.raise_()
            window.activateWindow()
            testbed.data.windows[window_name] = window

    @Slot()
    def control_experiment_callback(self):
        self.open_control_experiment_window()

    def closeEvent(self, event):
        if testbed.data.windows:
            logger.info("Cannot close main window until all child windows are closed.")
            event.ignore()
        else:
            while testbed.data.workers:
                key, worker = testbed.data.workers.popitem()
                worker.stop()
                logger.info("stopping worker %s", key)
            self.deleteLater()
            event.accept()


# Run the application
if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec())
