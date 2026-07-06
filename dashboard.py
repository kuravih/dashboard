import sys
from typing import NamedTuple, cast

from pykato.log import setup_logger
from PySide6.QtCore import QFileInfo, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QFileDialog, QHBoxLayout, QHeaderView, QMainWindow, QMessageBox, QPushButton, QSizePolicy, QSpacerItem, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

import testbed
from testbed.device import Stream
from testbed.device.camera import Camera
from testbed.device.modulator import Modulator
from testbed.widget import IconButton
from testbed.widget.camera_calibration_window import ProcessWindow as CameraCalibrationWindow
from testbed.widget.camera_window import InfoWindow as CameraInfoWindow
from testbed.widget.camera_window import PreviewWindow as CameraPreviewWindow
from testbed.widget.camera_window import SettingsWindow as CameraSettingsWindow
from testbed.widget.capture_loop_window import ProcessWindow as CaptureLoopWindow
from testbed.widget.dialog import MessageDialog
from testbed.widget.dotf_measurement_window import ProcessWindow as DOTFMeasurementWindow
from testbed.widget.modulator_window import InfoWindow as ModulatorInfoWindow
from testbed.widget.modulator_window import PreviewWindow as ModulatorPreviewWindow
from testbed.widget.modulator_window import SettingsWindow as ModulatorSettingsWindow
from testbed.widget.pairwise_fpwfs_window import ProcessWindow as PairwiseFPWFSWindow
from testbed.widget.recenter_window import ProcessWindow as RecenterWindow
from testbed.widget.resource import ICON_EYE, ICON_GEAR, ICON_INFO, ICON_PAUSE, ICON_PLAY
from testbed.widget.simple_loop_window import ProcessWindow as SimpleLoopWindow
from testbed.widget.speckle_capture_window import ProcessWindow as SpeckleCaptureWindow
from testbed.widget.speckle_nulling_window import ProcessWindow as SpeckleNullingWindow
from testbed.worker.camera_worker import ProcessWorker as CameraSamplingWorker
from testbed.worker.modulator_worker import ProcessWorker as ModulatorSamplingWorker

logger = setup_logger("dashboard", terminator="\n")


class DeviceButtons(NamedTuple):
    settings: IconButton
    play_pause: IconButton


class MainWindow(QMainWindow):
    """Main Window"""

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

        capture_loop_button = QPushButton("Capture Process")
        capture_loop_button.clicked.connect(self.on_capture_loop_clicked)

        speckle_capture_button = QPushButton("Speckle Capture Process")
        speckle_capture_button.clicked.connect(self.on_speckle_capture_clicked)

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
        layout.addWidget(capture_loop_button)
        layout.addWidget(speckle_capture_button)
        layout.addWidget(speckle_nulling_button)
        layout.addWidget(recenter_button)
        layout.addWidget(camera_calibration_button)
        layout.addWidget(dotf_measurement_button)
        layout.addWidget(pairwise_fpwfs_button)
        self.setCentralWidget(container)

    def open_device_preview_window(self, device: Camera | Modulator):

        @Slot()
        def on_window_closed():
            testbed.data.windows.pop(device.preview_window_id, None)

        if not testbed.data.is_window_alive(device.preview_window_id):
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
            testbed.data.windows[device.preview_window_id] = preview_window

            if testbed.data.is_worker_alive(device.sampling_worker_id):
                testbed.data.workers[device.sampling_worker_id].signals.sampled.connect(testbed.data.windows[device.preview_window_id].on_sampled)

    def open_device_info_window(self, device: Camera | Modulator):

        @Slot()
        def on_window_closed():
            testbed.data.windows.pop(device.info_window_id, None)

        if not testbed.data.is_window_alive(device.info_window_id):
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
            testbed.data.windows[device.info_window_id] = info_window

            if testbed.data.is_worker_alive(device.sampling_worker_id):
                testbed.data.workers[device.sampling_worker_id].signals.sampled.connect(testbed.data.windows[device.info_window_id].on_sampled)

    def open_device_settings_window(self, device: Camera | Modulator):

        @Slot()
        def on_window_closed():
            testbed.data.windows.pop(device.settings_window_id, None)

        if not testbed.data.is_window_alive(device.settings_window_id):
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
            testbed.data.windows[device.settings_window_id] = settings_window

    def on_play_pause(self, device: Camera | Modulator, button: IconButton):

        if testbed.data.is_worker_alive(device.sampling_worker_id):  # an update worker is in progress
            device_sampling_worker = cast(CameraSamplingWorker | ModulatorSamplingWorker, testbed.data.workers[device.sampling_worker_id])
            device_sampling_worker.stop()
            return

        device_sampling_worker = None
        if isinstance(device, Camera):
            device_sampling_worker = CameraSamplingWorker(device)
        elif isinstance(device, Modulator):
            device_sampling_worker = ModulatorSamplingWorker(device)
        else:
            raise ValueError("Invalid device")

        if testbed.data.is_window_alive(device.preview_window_id):
            device_preview_window = cast(CameraPreviewWindow | ModulatorPreviewWindow, testbed.data.windows[device.preview_window_id])
            device_sampling_worker.signals.sampled.connect(device_preview_window.on_sampled)
        if testbed.data.is_window_alive(device.info_window_id):
            device_info_window = cast(CameraInfoWindow | ModulatorInfoWindow, testbed.data.windows[device.info_window_id])
            device_sampling_worker.signals.sampled.connect(device_info_window.on_sampled)

        device_sampling_worker.signals.finished.connect(lambda d=device, b=button: self.on_sampling_worker_pause(d, b))

        testbed.data.workers[device.sampling_worker_id] = device_sampling_worker

        testbed.data.threadpool.start(device_sampling_worker)
        button.setBaseIconHint(QIcon(ICON_PAUSE), "Pause")
        self.on_sampling_worker_play(device)

    def on_sampling_worker_play(self, device: Camera | Modulator):
        if testbed.data.is_window_alive(SimpleLoopWindow.wid):
            simple_loop_window = cast(SimpleLoopWindow, testbed.data.windows[SimpleLoopWindow.wid])
            if simple_loop_window.source == device or simple_loop_window.sink == device:
                simple_loop_window.update_process_controls()
        if testbed.data.is_window_alive(SpeckleCaptureWindow.wid):
            speckle_calibration_window = cast(SpeckleCaptureWindow, testbed.data.windows[SpeckleCaptureWindow.wid])
            if speckle_calibration_window.source == device or speckle_calibration_window.sink == device:
                speckle_calibration_window.update_process_controls()
        if testbed.data.is_window_alive(SpeckleNullingWindow.wid):
            speckle_nulling_window = cast(SpeckleNullingWindow, testbed.data.windows[SpeckleNullingWindow.wid])
            if speckle_nulling_window.source == device or speckle_nulling_window.sink == device:
                speckle_nulling_window.update_process_controls()
        if testbed.data.is_window_alive(RecenterWindow.wid):
            recenter_window = cast(RecenterWindow, testbed.data.windows[RecenterWindow.wid])
            if recenter_window.source == device or recenter_window.sink == device:
                recenter_window.update_process_controls()
        if testbed.data.is_window_alive(CameraCalibrationWindow.wid):
            camera_calibration_window = cast(CameraCalibrationWindow, testbed.data.windows[CameraCalibrationWindow.wid])
            if camera_calibration_window.source == device:
                camera_calibration_window.update_process_controls()
        if testbed.data.is_window_alive(DOTFMeasurementWindow.wid):
            dotf_measurement_window = cast(DOTFMeasurementWindow, testbed.data.windows[DOTFMeasurementWindow.wid])
            if dotf_measurement_window.source == device or dotf_measurement_window.sink == device:
                dotf_measurement_window.update_process_controls()
        if testbed.data.is_window_alive(PairwiseFPWFSWindow.wid):
            pairwise_fpwfs_window = cast(PairwiseFPWFSWindow, testbed.data.windows[PairwiseFPWFSWindow.wid])
            if pairwise_fpwfs_window.source == device or pairwise_fpwfs_window.sink == device:
                pairwise_fpwfs_window.update_process_controls()

    def on_sampling_worker_pause(self, device: Camera | Modulator, button: IconButton):
        if testbed.data.is_worker_alive(device.sampling_worker_id):
            testbed.data.workers.pop(device.sampling_worker_id)
            button.setBaseIconHint(QIcon(ICON_PLAY), "play")
        if testbed.data.is_window_alive(SimpleLoopWindow.wid):
            simple_loop_window = cast(SimpleLoopWindow, testbed.data.windows[SimpleLoopWindow.wid])
            simple_loop_window.update_process_controls()
        if testbed.data.is_window_alive(SpeckleCaptureWindow.wid):
            speckle_calibration_window = cast(SpeckleCaptureWindow, testbed.data.windows[SpeckleCaptureWindow.wid])
            speckle_calibration_window.update_process_controls()
        if testbed.data.is_window_alive(SpeckleNullingWindow.wid):
            speckle_nulling_window = cast(SpeckleNullingWindow, testbed.data.windows[SpeckleNullingWindow.wid])
            speckle_nulling_window.update_process_controls()
        if testbed.data.is_window_alive(RecenterWindow.wid):
            recenter_window = cast(RecenterWindow, testbed.data.windows[RecenterWindow.wid])
            recenter_window.update_process_controls()
        if testbed.data.is_window_alive(CameraCalibrationWindow.wid):
            camera_calibration_window = cast(CameraCalibrationWindow, testbed.data.windows[CameraCalibrationWindow.wid])
            camera_calibration_window.update_process_controls()
        if testbed.data.is_window_alive(DOTFMeasurementWindow.wid):
            dotf_measurement_window = cast(DOTFMeasurementWindow, testbed.data.windows[DOTFMeasurementWindow.wid])
            dotf_measurement_window.update_process_controls()
        if testbed.data.is_window_alive(PairwiseFPWFSWindow.wid):
            pairwise_fpwfs_window = cast(PairwiseFPWFSWindow, testbed.data.windows[PairwiseFPWFSWindow.wid])
            pairwise_fpwfs_window.update_process_controls()

    @Slot()
    def on_add_device_clicked(self):
        dialog_filenames, _ = QFileDialog.getOpenFileNames(self, "Open Device Streams", "/dev/shm", "Streams (*.shm)", options=QFileDialog.Option.DontUseNativeDialog)
        for dialog_filename in dialog_filenames:
            stream_id = QFileInfo(dialog_filename).completeBaseName()

            if not testbed.data.is_device_alive(stream_id):
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

        @Slot()
        def on_window_closed():
            testbed.data.windows.pop(SimpleLoopWindow.wid, None)

        if not testbed.data.is_window_alive(SimpleLoopWindow.wid):
            simple_loop_window = SimpleLoopWindow(self)
            simple_loop_window.destroyed.connect(on_window_closed)
            simple_loop_window.show()
            simple_loop_window.raise_()
            simple_loop_window.activateWindow()
            testbed.data.windows[SimpleLoopWindow.wid] = simple_loop_window

    @Slot()
    def on_capture_loop_clicked(self):

        @Slot()
        def on_window_closed():
            testbed.data.windows.pop(CaptureLoopWindow.wid, None)

        if not testbed.data.is_window_alive(CaptureLoopWindow.wid):
            capture_window = CaptureLoopWindow(self)
            capture_window.destroyed.connect(on_window_closed)
            capture_window.show()
            capture_window.raise_()
            capture_window.activateWindow()
            testbed.data.windows[CaptureLoopWindow.wid] = capture_window

    @Slot()
    def on_speckle_capture_clicked(self):

        @Slot()
        def on_window_closed():
            testbed.data.windows.pop(SpeckleCaptureWindow.wid, None)

        if not testbed.data.is_window_alive(SpeckleCaptureWindow.wid):
            speckle_capture_window = SpeckleCaptureWindow(self)
            speckle_capture_window.destroyed.connect(on_window_closed)
            speckle_capture_window.show()
            speckle_capture_window.raise_()
            speckle_capture_window.activateWindow()
            testbed.data.windows[SpeckleCaptureWindow.wid] = speckle_capture_window

    @Slot()
    def on_open_speckle_nulling_clicked(self):

        @Slot()
        def on_window_closed():
            testbed.data.windows.pop(SpeckleNullingWindow.wid, None)

        if not testbed.data.is_window_alive(SpeckleNullingWindow.wid):
            speckle_nulling_window = SpeckleNullingWindow(self)
            speckle_nulling_window.destroyed.connect(on_window_closed)
            speckle_nulling_window.show()
            speckle_nulling_window.raise_()
            speckle_nulling_window.activateWindow()
            testbed.data.windows[SpeckleNullingWindow.wid] = speckle_nulling_window

    @Slot()
    def on_open_recenter_clicked(self):

        @Slot()
        def on_window_closed():
            testbed.data.windows.pop(RecenterWindow.wid, None)

        if not testbed.data.is_window_alive(RecenterWindow.wid):
            recenter_window = RecenterWindow(self)
            recenter_window.destroyed.connect(on_window_closed)
            recenter_window.show()
            recenter_window.raise_()
            recenter_window.activateWindow()
            testbed.data.windows[RecenterWindow.wid] = recenter_window

    @Slot()
    def on_open_camera_calibration_clicked(self):

        @Slot()
        def on_window_closed():
            testbed.data.windows.pop(CameraCalibrationWindow.wid, None)

        if not testbed.data.is_window_alive(CameraCalibrationWindow.wid):
            camera_calibration_window = CameraCalibrationWindow(self)
            camera_calibration_window.destroyed.connect(on_window_closed)
            camera_calibration_window.show()
            camera_calibration_window.raise_()
            camera_calibration_window.activateWindow()
            testbed.data.windows[CameraCalibrationWindow.wid] = camera_calibration_window

    @Slot()
    def on_open_dotf_measurement_clicked(self):

        @Slot()
        def on_window_closed():
            testbed.data.windows.pop(DOTFMeasurementWindow.wid, None)

        if not testbed.data.is_window_alive(DOTFMeasurementWindow.wid):
            dotf_measurement_window = DOTFMeasurementWindow(self)
            dotf_measurement_window.destroyed.connect(on_window_closed)
            dotf_measurement_window.show()
            dotf_measurement_window.raise_()
            dotf_measurement_window.activateWindow()
            testbed.data.windows[DOTFMeasurementWindow.wid] = dotf_measurement_window

    @Slot()
    def on_open_pairwise_fpwfs_clicked(self):

        @Slot()
        def on_window_closed():
            testbed.data.windows.pop(PairwiseFPWFSWindow.wid, None)

        if not testbed.data.is_window_alive(PairwiseFPWFSWindow.wid):
            pairwise_fpwfs_window = PairwiseFPWFSWindow(self)
            pairwise_fpwfs_window.destroyed.connect(on_window_closed)
            pairwise_fpwfs_window.show()
            pairwise_fpwfs_window.raise_()
            pairwise_fpwfs_window.activateWindow()
            testbed.data.windows[PairwiseFPWFSWindow.wid] = pairwise_fpwfs_window

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
