import sys
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMainWindow, QPushButton, QFileDialog, QMessageBox, QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QSpacerItem, QSizePolicy

from PySide6.QtCore import Slot, QFileInfo

import testbed
from testbed.device import Stream

from testbed.device.camera import Camera
from testbed.widget.camera_window import PreviewWindow as CameraPreviewWindow, InfoWindow as CameraInfoWindow, SettingsWindow as CameraSettingsWindow
from testbed.worker.camera_worker import UpdateWorker as CameraUpdateWorker

from testbed.device.modulator import Modulator
from testbed.widget.modulator_window import PreviewWindow as ModulatorPreviewWindow, InfoWindow as ModulatorInfoWindow, SettingsWindow as ModulatorSettingsWindow
from testbed.worker.modulator_worker import UpdateWorker as ModulatorUpdateWorker

from testbed.widget.simple_loop_window import ProcessWindow as SimpleLoopWindow
from testbed.widget.speckle_calibration_window import ProcessWindow as SpeckleCalibrationWindow
from testbed.widget.speckle_nulling_window import ProcessWindow as SpeckleNullingWindow
from testbed.widget.recenter_window import ProcessWindow as RecenterWindow
from testbed.widget.camera_calibration_window import ProcessWindow as CameraCalibrationWindow

from testbed.widget.dialog import MessageDialog
from testbed.widget.resource import ICON_EYE, ICON_GEAR, ICON_INFO, ICON_PLAY, ICON_PAUSE

from pykato.log import setup_logger

logger = setup_logger("dashboard", terminator="\n")


class MainWindow(QMainWindow):
    """
    Main Window
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Testbed Controls")
        self.setMinimumSize(640, 480)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Name", "Kind", "Shape", "Dtype", ""])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        add_device_button = QPushButton("Add Device")
        add_device_button.clicked.connect(self.on_add_device_clicked)

        remove_device_button = QPushButton("Remove Device")
        remove_device_button.clicked.connect(self.on_remove_device_clicked)

        simple_loop_button = QPushButton("Simple Process")
        simple_loop_button.clicked.connect(self.on_simple_loop_clicked)

        speckle_calibration_button = QPushButton("Speckle Calibration Process")
        speckle_calibration_button.clicked.connect(self.open_speckle_calibration_clicked)

        speckle_nulling_button = QPushButton("Speckle Nulling Process")
        speckle_nulling_button.clicked.connect(self.open_speckle_nulling_clicked)

        recenter_button = QPushButton("Recenter Process")
        recenter_button.clicked.connect(self.open_recenter_clicked)

        camera_calibration_button = QPushButton("Camera Calibration Process")
        camera_calibration_button.clicked.connect(self.open_camera_calibration_clicked)

        device_button_layout = QHBoxLayout()
        device_button_layout.addWidget(add_device_button)
        device_button_layout.addWidget(remove_device_button)

        # Layout setup
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(self.table)
        layout.addLayout(device_button_layout)
        layout.addWidget(simple_loop_button)
        layout.addWidget(speckle_calibration_button)
        layout.addWidget(speckle_nulling_button)
        layout.addWidget(recenter_button)
        layout.addWidget(camera_calibration_button)
        self.setCentralWidget(container)

    def open_device_preview_window(self, _device: Camera | Modulator):

        preview_window_id = f"{_device.name}_preview_window"
        device_update_worker_id = f"{_device.name}_update_worker"

        @Slot()
        def on_window_closed():
            testbed.data.windows.pop(preview_window_id, None)

        if preview_window_id not in testbed.data.windows:
            preview_window: CameraPreviewWindow | ModulatorPreviewWindow | None = None
            if isinstance(_device, Camera):
                preview_window = CameraPreviewWindow(_device, parent=self)
            elif isinstance(_device, Modulator):
                preview_window = ModulatorPreviewWindow(_device, parent=self)
            else:
                raise ValueError("Invalid device")

            preview_window.destroyed.connect(on_window_closed)
            preview_window.show()
            preview_window.raise_()
            preview_window.activateWindow()
            testbed.data.windows[preview_window_id] = preview_window

            if device_update_worker_id in testbed.data.workers:
                testbed.data.workers[device_update_worker_id].signals.sampled.connect(testbed.data.windows[preview_window_id].on_sampled)

    def open_device_info_window(self, _device: Camera | Modulator):

        info_window_id = f"{_device.name}_info_window"
        device_update_worker_id = f"{_device.name}_update_worker"

        @Slot()
        def on_window_closed():
            testbed.data.windows.pop(info_window_id, None)

        if info_window_id not in testbed.data.windows:
            info_window: CameraInfoWindow | ModulatorInfoWindow | None = None
            if isinstance(_device, Camera):
                info_window = CameraInfoWindow(_device, parent=self)
            elif isinstance(_device, Modulator):
                info_window = ModulatorInfoWindow(_device, parent=self)
            else:
                raise ValueError("Invalid device")
            info_window.destroyed.connect(on_window_closed)
            info_window.show()
            info_window.raise_()
            info_window.activateWindow()
            testbed.data.windows[info_window_id] = info_window

            if device_update_worker_id in testbed.data.workers:
                testbed.data.workers[device_update_worker_id].signals.sampled.connect(testbed.data.windows[info_window_id].on_sampled)

    def open_device_settings_window(self, _device: Camera | Modulator):

        settings_window_id = f"{_device.name}_settings_window"
        device_update_worker_id = f"{_device.name}_update_worker"

        @Slot()
        def on_window_closed():
            testbed.data.windows.pop(settings_window_id, None)

        if settings_window_id not in testbed.data.windows:
            settings_window: CameraSettingsWindow | ModulatorSettingsWindow | None = None
            if isinstance(_device, Camera):
                settings_window = CameraSettingsWindow(_device, parent=self)
            elif isinstance(_device, Modulator):
                settings_window = ModulatorSettingsWindow(_device, parent=self)
            else:
                raise ValueError("Invalid device")
            settings_window.destroyed.connect(on_window_closed)
            settings_window.show()
            settings_window.raise_()
            settings_window.activateWindow()
            testbed.data.windows[settings_window_id] = settings_window

            if device_update_worker_id in testbed.data.workers:
                testbed.data.workers[device_update_worker_id].signals.sampled.connect(testbed.data.windows[settings_window_id].on_sampled)

    def on_start_stop(self, _device: Camera | Modulator, _button: QPushButton):

        preview_window_id = f"{_device.name}_preview_window"
        info_window_id = f"{_device.name}_info_window"
        settings_window_id = f"{_device.name}_settings_window"
        device_update_worker_id = f"{_device.name}_update_worker"

        if device_update_worker_id in testbed.data.workers:  # an update worker is in progress
            current_device_update_worker = testbed.data.workers.pop(device_update_worker_id)
            current_device_update_worker.stop()
            _button.setIcon(QIcon(ICON_PLAY))
            _button.setToolTip("Stop")
            return

        device_update_worker: CameraUpdateWorker | ModulatorUpdateWorker | None = None
        if isinstance(_device, Camera):
            device_update_worker = CameraUpdateWorker(_device)
        elif isinstance(_device, Modulator):
            device_update_worker = ModulatorUpdateWorker(_device)
        else:
            raise ValueError("Invalid device")

        if preview_window_id in testbed.data.windows:
            device_update_worker.signals.sampled.connect(testbed.data.windows[preview_window_id].on_sampled)
        if info_window_id in testbed.data.windows:
            device_update_worker.signals.sampled.connect(testbed.data.windows[info_window_id].on_sampled)
        if settings_window_id in testbed.data.windows:
            device_update_worker.signals.sampled.connect(testbed.data.windows[settings_window_id].on_sampled)

        testbed.data.workers[device_update_worker_id] = device_update_worker

        testbed.data.threadpool.start(device_update_worker)
        _button.setIcon(QIcon(ICON_PAUSE))
        _button.setToolTip("Start")

    @Slot()
    def on_add_device_clicked(self):
        dialog_filenames, _ = QFileDialog.getOpenFileNames(self, "Open Device Streams", "/dev/shm", "Streams (*.shm)", options=QFileDialog.Option.DontUseNativeDialog)
        for dialog_filename in dialog_filenames:
            stream_id = QFileInfo(dialog_filename).completeBaseName()

            if stream_id not in testbed.data.devices:
                stream = Stream(stream_id)
                row = self.table.rowCount()
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(stream.name))
                self.table.setItem(row, 1, QTableWidgetItem(stream.kind.to_str()))

                cell_widget = QWidget()
                button_layout = QHBoxLayout(cell_widget)
                button_layout.setContentsMargins(0, 0, 0, 0)

                info_button = QPushButton(QIcon(ICON_INFO), "", flat=True, parent=self)
                info_button.setFixedWidth(info_button.sizeHint().height())
                info_button.setToolTip("Information")
                button_layout.addWidget(info_button)

                settings_button = QPushButton(QIcon(ICON_GEAR), "", flat=True, parent=self)
                settings_button.setFixedWidth(settings_button.sizeHint().height())
                settings_button.setToolTip("Settings")
                button_layout.addWidget(settings_button)

                preview_button = QPushButton(QIcon(ICON_EYE), "", flat=True, parent=self)
                preview_button.setFixedWidth(preview_button.sizeHint().height())
                preview_button.setToolTip("Preview")
                button_layout.addWidget(preview_button)

                play_pause_button = QPushButton(QIcon(ICON_PLAY), "", flat=True, parent=self)
                play_pause_button.setFixedWidth(play_pause_button.sizeHint().height())
                play_pause_button.setToolTip("Start")
                button_layout.addWidget(play_pause_button)

                if stream.kind == Stream.Kind.CAMERA:
                    camera = Camera(stream)
                    self.table.setItem(row, 2, QTableWidgetItem(str(camera.shape)))
                    self.table.setItem(row, 3, QTableWidgetItem("dtype"))
                    preview_button.clicked.connect(lambda _, _camera=camera: self.open_device_preview_window(_camera))
                    info_button.clicked.connect(lambda _, _camera=camera: self.open_device_info_window(_camera))
                    settings_button.clicked.connect(lambda _, _camera=camera: self.open_device_settings_window(_camera))
                    play_pause_button.clicked.connect(lambda _, _button=play_pause_button, _camera=camera: self.on_start_stop(_camera, _button))
                    testbed.data.devices[stream_id] = camera
                    # self.on_start_stop(camera, play_pause_button) # TODO: uncomment
                    # self.open_device_preview_window(camera) # TODO: uncomment
                elif stream.kind == Stream.Kind.SLM:
                    modulator = Modulator(stream)
                    self.table.setItem(row, 2, QTableWidgetItem(str(modulator.shape)))
                    self.table.setItem(row, 3, QTableWidgetItem("dtype"))
                    preview_button.clicked.connect(lambda _, _modulator=modulator: self.open_device_preview_window(_modulator))
                    info_button.clicked.connect(lambda _, _modulator=modulator: self.open_device_info_window(_modulator))
                    settings_button.clicked.connect(lambda _, _modulator=modulator: self.open_device_settings_window(_modulator))
                    play_pause_button.clicked.connect(lambda _, _button=play_pause_button, _modulator=modulator: self.on_start_stop(_modulator, _button))
                    testbed.data.devices[stream_id] = modulator
                    # self.on_start_stop(modulator, play_pause_button) # TODO: uncomment
                    # self.open_device_preview_window(modulator) # TODO: uncomment

                spacer = QSpacerItem(10, 10, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
                button_layout.addItem(spacer)

                self.table.setCellWidget(row, 4, cell_widget)

            else:
                message_dialog = MessageDialog("Device available", "Device already available. Access via device menu.", icon=QMessageBox.Icon.Information, buttons=QMessageBox.StandardButton.Ok)
                message_dialog.exec()

    @Slot()
    def on_remove_device_clicked(self):
        logger.info("on_remove_device_clicked")
        for index in sorted(set(i.row() for i in self.table.selectedIndexes()), reverse=True):
            _key = self.table.item(index, 0).text()
            testbed.data.devices.pop(_key, None)
            self.table.removeRow(index)

    @Slot()
    def on_simple_loop_clicked(self):

        simple_loop_window_id = f"{testbed.SIMPLE_LOOP}_window"

        @Slot()
        def on_window_closed():
            testbed.data.windows.pop(simple_loop_window_id, None)

        if simple_loop_window_id not in testbed.data.windows:
            simple_loop_window = SimpleLoopWindow(self)
            simple_loop_window.destroyed.connect(on_window_closed)
            simple_loop_window.show()
            simple_loop_window.raise_()
            simple_loop_window.activateWindow()
            testbed.data.windows[simple_loop_window_id] = simple_loop_window

    @Slot()
    def open_speckle_calibration_clicked(self):

        speckle_calibration_window_id = f"{testbed.SPECKLE_CALIBRATION}_window"

        @Slot()
        def on_window_closed():
            testbed.data.windows.pop(speckle_calibration_window_id, None)

        if speckle_calibration_window_id not in testbed.data.windows:
            speckle_calibration_window = SpeckleCalibrationWindow(self)
            speckle_calibration_window.destroyed.connect(on_window_closed)
            speckle_calibration_window.show()
            speckle_calibration_window.raise_()
            speckle_calibration_window.activateWindow()
            testbed.data.windows[speckle_calibration_window_id] = speckle_calibration_window

    @Slot()
    def open_speckle_nulling_clicked(self):

        speckle_nulling_window_id = f"{testbed.SPECKLE_NULLING}_window"

        @Slot()
        def on_window_closed():
            testbed.data.windows.pop(speckle_nulling_window_id, None)

        if speckle_nulling_window_id not in testbed.data.windows:
            speckle_nulling_window = SpeckleNullingWindow(self)
            speckle_nulling_window.destroyed.connect(on_window_closed)
            speckle_nulling_window.show()
            speckle_nulling_window.raise_()
            speckle_nulling_window.activateWindow()
            testbed.data.windows[speckle_nulling_window_id] = speckle_nulling_window

    @Slot()
    def open_recenter_clicked(self):

        recenter_window_id = f"{testbed.RECENTER}_window"

        @Slot()
        def on_window_closed():
            testbed.data.windows.pop(recenter_window_id, None)

        if recenter_window_id not in testbed.data.windows:
            recenter_window = RecenterWindow(self)
            recenter_window.destroyed.connect(on_window_closed)
            recenter_window.show()
            recenter_window.raise_()
            recenter_window.activateWindow()
            testbed.data.windows[recenter_window_id] = recenter_window

    @Slot()
    def open_camera_calibration_clicked(self):

        camera_calibration_window_id = f"{testbed.CAMERA_CALIBRATION}_window"

        @Slot()
        def on_window_closed():
            testbed.data.windows.pop(camera_calibration_window_id, None)

        if camera_calibration_window_id not in testbed.data.windows:
            camera_calibration_window = CameraCalibrationWindow(self)
            camera_calibration_window.destroyed.connect(on_window_closed)
            camera_calibration_window.show()
            camera_calibration_window.raise_()
            camera_calibration_window.activateWindow()
            testbed.data.windows[camera_calibration_window_id] = camera_calibration_window

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
