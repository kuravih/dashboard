import sys
from typing import NamedTuple
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMainWindow, QPushButton, QFileDialog, QMessageBox, QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QSpacerItem, QSizePolicy

from PySide6.QtCore import Slot, QFileInfo

import testbed
from testbed.device import Stream

from testbed.device.camera import Camera
from testbed.widget.camera_window import PreviewWindow as CameraPreviewWindow, InfoWindow as CameraInfoWindow, SettingsWindow as CameraSettingsWindow
from testbed.worker.camera_worker import ProcessWorker as CameraSamplingWorker

from testbed.device.modulator import Modulator
from testbed.widget.modulator_window import PreviewWindow as ModulatorPreviewWindow, InfoWindow as ModulatorInfoWindow, SettingsWindow as ModulatorSettingsWindow
from testbed.worker.modulator_worker import ProcessWorker as ModulatorSamplingWorker

from testbed.widget.simple_loop_window import ProcessWindow as SimpleLoopWindow
from testbed.widget.speckle_calibration_window import ProcessWindow as SpeckleCalibrationWindow
from testbed.widget.speckle_nulling_window import ProcessWindow as SpeckleNullingWindow
from testbed.widget.recenter_window import ProcessWindow as RecenterWindow
from testbed.widget.camera_calibration_window import ProcessWindow as CameraCalibrationWindow
from testbed.widget.dotf_measurement_window import ProcessWindow as DOTFMeasurementWindow
from testbed.widget.pairwise_fpwfs_window import ProcessWindow as PairwiseFPWFSWindow

from testbed.widget.dialog import MessageDialog
from testbed.widget.resource import ICON_EYE, ICON_GEAR, ICON_INFO, ICON_PLAY, ICON_PAUSE

from testbed.widget import IconButton

from pykato.log import setup_logger

logger = setup_logger("dashboard", terminator="\n")


class DeviceButtons(NamedTuple):
    settings: IconButton
    play_pause: IconButton


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
        self.device_buttons: dict[str, DeviceButtons] = {}

        add_device_button = QPushButton("Add Device")
        add_device_button.clicked.connect(self.on_add_device_clicked)

        remove_device_button = QPushButton("Remove Device")
        remove_device_button.clicked.connect(self.on_remove_device_clicked)

        simple_loop_button = QPushButton("Simple Process")
        simple_loop_button.clicked.connect(self.on_simple_loop_clicked)

        speckle_calibration_button = QPushButton("Speckle Calibration Process")
        speckle_calibration_button.clicked.connect(self.on_open_speckle_calibration_clicked)

        speckle_nulling_button = QPushButton("Speckle Nulling Process")
        speckle_nulling_button.clicked.connect(self.on_open_speckle_nulling_clicked)

        recenter_button = QPushButton("Recenter Process")
        recenter_button.clicked.connect(self.on_open_recenter_clicked)

        camera_calibration_button = QPushButton("Camera Calibration Process")
        camera_calibration_button.clicked.connect(self.on_open_camera_calibration_clicked)

        dotf_measurement_button = QPushButton("DOTF Measurement Process")
        dotf_measurement_button.clicked.connect(self.on_open_dotf_measurement_clicked)

        pairwise_fpwfs_button = QPushButton("Pairwise FPWFS Process")
        pairwise_fpwfs_button.clicked.connect(self.on_open_pairwise_fpwfs_clicked)

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
        layout.addWidget(dotf_measurement_button)
        layout.addWidget(pairwise_fpwfs_button)
        self.setCentralWidget(container)

    def open_device_preview_window(self, device: Camera | Modulator):
        device_preview_window_id = f"{device.name}_preview_window"
        device_sampling_worker_id = f"{device.name}_sampling_worker"

        @Slot()
        def on_window_closed():
            testbed.data.windows.pop(device_preview_window_id, None)

        if device_preview_window_id not in testbed.data.windows:
            preview_window: CameraPreviewWindow | ModulatorPreviewWindow | None = None
            if isinstance(device, Camera):
                preview_window = CameraPreviewWindow(device, parent=self)
            elif isinstance(device, Modulator):
                preview_window = ModulatorPreviewWindow(device, parent=self)
            else:
                raise ValueError("Invalid device")

            preview_window.destroyed.connect(on_window_closed)
            preview_window.show()
            preview_window.raise_()
            preview_window.activateWindow()
            testbed.data.windows[device_preview_window_id] = preview_window

            if device_sampling_worker_id in testbed.data.workers:
                testbed.data.workers[device_sampling_worker_id].signals.sampled.connect(testbed.data.windows[device_preview_window_id].on_sampled)

    def open_device_info_window(self, device: Camera | Modulator):

        device_info_window_id = f"{device.name}_info_window"
        device_sampling_worker_id = f"{device.name}_sampling_worker"

        @Slot()
        def on_window_closed():
            testbed.data.windows.pop(device_info_window_id, None)

        if device_info_window_id not in testbed.data.windows:
            info_window: CameraInfoWindow | ModulatorInfoWindow | None = None
            if isinstance(device, Camera):
                info_window = CameraInfoWindow(device, parent=self)
            elif isinstance(device, Modulator):
                info_window = ModulatorInfoWindow(device, parent=self)
            else:
                raise ValueError("Invalid device")
            info_window.destroyed.connect(on_window_closed)
            info_window.show()
            info_window.raise_()
            info_window.activateWindow()
            testbed.data.windows[device_info_window_id] = info_window

            if device_sampling_worker_id in testbed.data.workers:
                testbed.data.workers[device_sampling_worker_id].signals.sampled.connect(testbed.data.windows[device_info_window_id].on_sampled)

    def open_device_settings_window(self, device: Camera | Modulator):

        device_settings_window_id = f"{device.name}_settings_window"

        @Slot()
        def on_window_closed():
            testbed.data.windows.pop(device_settings_window_id, None)

        if device_settings_window_id not in testbed.data.windows:
            settings_window: CameraSettingsWindow | ModulatorSettingsWindow | None = None
            if isinstance(device, Camera):
                settings_window = CameraSettingsWindow(device, parent=self)
            elif isinstance(device, Modulator):
                settings_window = ModulatorSettingsWindow(device, parent=self)
            else:
                raise ValueError("Invalid device")
            settings_window.destroyed.connect(on_window_closed)
            settings_window.show()
            settings_window.raise_()
            settings_window.activateWindow()
            testbed.data.windows[device_settings_window_id] = settings_window

    def on_play_pause(self, device: Camera | Modulator, button: IconButton):

        device_preview_window_id = f"{device.name}_preview_window"
        device_info_window_id = f"{device.name}_info_window"
        device_sampling_worker_id = f"{device.name}_sampling_worker"

        if device_sampling_worker_id in testbed.data.workers:  # an update worker is in progress
            device_sampling_worker = testbed.data.workers[device_sampling_worker_id]
            device_sampling_worker.stop()
            return

        device_sampling_worker: CameraSamplingWorker | ModulatorSamplingWorker | None = None
        if isinstance(device, Camera):
            device_sampling_worker = CameraSamplingWorker(device)
        elif isinstance(device, Modulator):
            device_sampling_worker = ModulatorSamplingWorker(device)
        else:
            raise ValueError("Invalid device")

        if device_preview_window_id in testbed.data.windows:
            device_preview_window = testbed.data.windows[device_preview_window_id]
            device_sampling_worker.signals.sampled.connect(device_preview_window.on_sampled)
        if device_info_window_id in testbed.data.windows:
            device_info_window = testbed.data.windows[device_info_window_id]
            device_sampling_worker.signals.sampled.connect(device_info_window.on_sampled)

        device_sampling_worker.signals.finished.connect(lambda d=device, b=button: self.on_sampling_worker_pause(d, b))

        testbed.data.workers[device_sampling_worker_id] = device_sampling_worker

        testbed.data.threadpool.start(device_sampling_worker)
        button.setIconHint(QIcon(ICON_PAUSE), "Pause")
        self.on_sampling_worker_play(device)

    def on_sampling_worker_play(self, device: Camera | Modulator):
        simple_loop_window_id = f"{testbed.SIMPLE_LOOP}_window"
        if simple_loop_window_id in testbed.data.windows:
            simple_loop_window: SimpleLoopWindow = testbed.data.windows[simple_loop_window_id]
            if simple_loop_window.source == device or simple_loop_window.sink == device:
                simple_loop_window.update_play_pause_button()

    def on_sampling_worker_pause(self, device: Camera | Modulator, button: IconButton):
        device_sampling_worker_id = f"{device.name}_sampling_worker"
        if device_sampling_worker_id in testbed.data.workers:  # an update worker is in progress
            testbed.data.workers.pop(device_sampling_worker_id)
            button.setIconHint(QIcon(ICON_PLAY), "play")
        simple_loop_window_id = f"{testbed.SIMPLE_LOOP}_window"
        if simple_loop_window_id in testbed.data.windows:
            simple_loop_window: SimpleLoopWindow = testbed.data.windows[simple_loop_window_id]
            simple_loop_window.update_play_pause_button()

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

                info_button = IconButton(QIcon(ICON_INFO), flat=True, parent=self)
                info_button.setToolTip("Information")
                button_layout.addWidget(info_button)

                settings_button = IconButton(QIcon(ICON_GEAR), flat=True, parent=self)
                settings_button.setToolTip("Settings")
                button_layout.addWidget(settings_button)

                preview_button = IconButton(QIcon(ICON_EYE), flat=True, parent=self)
                preview_button.setToolTip("Preview")
                button_layout.addWidget(preview_button)

                play_pause_button = IconButton(QIcon(ICON_PLAY), flat=True, parent=self)
                play_pause_button.setToolTip("Play")
                button_layout.addWidget(play_pause_button)

                if stream.kind == Stream.Kind.CAMERA:
                    camera = Camera(stream)
                    self.table.setItem(row, 2, QTableWidgetItem(str(camera.shape)))
                    self.table.setItem(row, 3, QTableWidgetItem(str(stream.dtype)))
                    preview_button.clicked.connect(lambda _, c=camera: self.open_device_preview_window(c))
                    info_button.clicked.connect(lambda _, c=camera: self.open_device_info_window(c))
                    settings_button.clicked.connect(lambda _, c=camera: self.open_device_settings_window(c))
                    play_pause_button.clicked.connect(lambda _, b=play_pause_button, c=camera: self.on_play_pause(c, b))
                    testbed.data.devices[stream_id] = camera
                    # self.on_play_pause(camera, play_pause_button) # TODO: uncomment
                    # self.open_device_preview_window(camera) # TODO: uncomment
                elif stream.kind == Stream.Kind.SLM:
                    modulator = Modulator(stream)
                    self.table.setItem(row, 2, QTableWidgetItem(str(modulator.shape)))
                    self.table.setItem(row, 3, QTableWidgetItem(str(stream.dtype)))
                    preview_button.clicked.connect(lambda _, m=modulator: self.open_device_preview_window(m))
                    info_button.clicked.connect(lambda _, m=modulator: self.open_device_info_window(m))
                    settings_button.clicked.connect(lambda _, m=modulator: self.open_device_settings_window(m))
                    play_pause_button.clicked.connect(lambda _, b=play_pause_button, m=modulator: self.on_play_pause(m, b))
                    testbed.data.devices[stream_id] = modulator
                    # self.on_play_pause(modulator, play_pause_button) # TODO: uncomment
                    # self.open_device_preview_window(modulator) # TODO: uncomment
                self.device_buttons[stream_id] = DeviceButtons(settings_button, play_pause_button)

                spacer = QSpacerItem(10, 10, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
                button_layout.addItem(spacer)

                self.table.setCellWidget(row, 4, cell_widget)

            else:
                message_dialog = MessageDialog("Device available", "Device already available. Access via device menu.", icon=QMessageBox.Icon.Information, buttons=QMessageBox.StandardButton.Ok)
                message_dialog.exec()

    def set_device_buttons_enabled(self, device_name: str, enabled: bool):
        if device_name in self.device_buttons:
            self.device_buttons[device_name].settings.setEnabled(enabled)
            self.device_buttons[device_name].play_pause.setEnabled(enabled)

    @Slot()
    def on_remove_device_clicked(self):
        for index in sorted(set(i.row() for i in self.table.selectedIndexes()), reverse=True):
            _key = self.table.item(index, 0).text()
            testbed.data.devices.pop(_key, None)
            self.device_buttons.pop(_key, None)
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
    def on_open_speckle_calibration_clicked(self):

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
    def on_open_speckle_nulling_clicked(self):

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
    def on_open_recenter_clicked(self):

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
    def on_open_camera_calibration_clicked(self):

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

    @Slot()
    def on_open_dotf_measurement_clicked(self):

        dotf_measurement_window_id = f"{testbed.DOTF_MEASUREMENT}_window"

        @Slot()
        def on_window_closed():
            testbed.data.windows.pop(dotf_measurement_window_id, None)

        if dotf_measurement_window_id not in testbed.data.windows:
            dotf_measurement_window = DOTFMeasurementWindow(self)
            dotf_measurement_window.destroyed.connect(on_window_closed)
            dotf_measurement_window.show()
            dotf_measurement_window.raise_()
            dotf_measurement_window.activateWindow()
            testbed.data.windows[dotf_measurement_window_id] = dotf_measurement_window

    @Slot()
    def on_open_pairwise_fpwfs_clicked(self):

        pairwise_fpwfs_window_id = f"{testbed.PAIRWISE_FPWFS}_window"

        @Slot()
        def on_window_closed():
            testbed.data.windows.pop(pairwise_fpwfs_window_id, None)

        if pairwise_fpwfs_window_id not in testbed.data.windows:
            pairwise_fpwfs_window = PairwiseFPWFSWindow(self)
            pairwise_fpwfs_window.destroyed.connect(on_window_closed)
            pairwise_fpwfs_window.show()
            pairwise_fpwfs_window.raise_()
            pairwise_fpwfs_window.activateWindow()
            testbed.data.windows[pairwise_fpwfs_window_id] = pairwise_fpwfs_window

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
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec())
