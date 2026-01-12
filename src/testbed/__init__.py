from PySide6.QtCore import QThreadPool

from .device.camera import Camera
from .device.modulator import Modulator
from .widget.camera_window import PreviewWindow as CameraPreviewWindow, InfoWindow as CameraInfoWindow, SettingsWindow as CameraSettingsWindow
from .widget.modulator_window import PreviewWindow as ModulatorPreviewWindow, InfoWindow as ModulatorInfoWindow, SettingsWindow as ModulatorSettingsWindow

SIMPLE_LOOP = "simple_loop"
from .widget.simple_loop_window import MainWindow as SimpleLoopWindow
from .worker.simple_loop_worker import MainWorker as SimpleLoopWorker

SPECKLE_CALIBRATION = "speckle_calibration"
from .widget.speckle_calibration_window import MainWindow as SpeckleCalibrationWindow
from .worker.speckle_calibration_worker import MainWorker as SpeckleCalibrationWorker

SPECKLE_NULLING = "speckle_nulling"
from .widget.speckle_nulling_window import MainWindow as SpeckleNullingWindow
from .worker.speckle_nulling_worker import MainWorker as SpeckleNullingWorker

from .worker.camera_worker import UpdateWorker as CameraUpdateWorker
from .worker.modulator_worker import UpdateWorker as ModulatorUpdateWorker
from .worker.storage_worker import SourceStorageWorker, SinkStorageWorker


class Data:
    threadpool = QThreadPool.globalInstance()
    devices: dict[str, Camera | Modulator] = {}
    windows: dict[str, CameraPreviewWindow | CameraInfoWindow | CameraSettingsWindow | ModulatorPreviewWindow | ModulatorInfoWindow | ModulatorSettingsWindow | SimpleLoopWindow | SpeckleCalibrationWindow | SpeckleNullingWindow] = {}
    workers: dict[str, CameraUpdateWorker | ModulatorUpdateWorker | SourceStorageWorker | SinkStorageWorker | SimpleLoopWorker | SpeckleCalibrationWorker | SpeckleNullingWorker] = {}


data = Data()
