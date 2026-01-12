from PySide6.QtCore import QThreadPool

from .device.camera import Camera
from .device.modulator import Modulator
from .widget.camera_window import PreviewWindow as CameraPreviewWindow, InfoWindow as CameraInfoWindow, SettingsWindow as CameraSettingsWindow
from .widget.modulator_window import PreviewWindow as ModulatorPreviewWindow, InfoWindow as ModulatorInfoWindow, SettingsWindow as ModulatorSettingsWindow

SIMPLE = "simple"
from .widget.simple_proc_window import SimpleProcWindow
from .worker.simple_proc_worker import SimpleProcWorker

SPECKLE_CALIBRATION = "speckle_calibration"
from .widget.speckle_cal_proc_window import SpeckleCalProcWindow
from .worker.speckle_cal_proc_worker import SpeckleCalProcWorker

SPECKLE_NULLING = "speckle_nulling"
from .widget.speckle_null_proc_window import SpeckleNullProcWindow, SpeckleNullProcPreviewWindow
from .worker.speckle_null_proc_worker import SpeckleNullProcWorker

from .worker.camera_worker import UpdateWorker as CameraUpdateWorker
from .worker.modulator_worker import UpdateWorker as ModulatorUpdateWorker
from .worker.storage_worker import SourceStorageWorker, SinkStorageWorker


class Data:
    threadpool = QThreadPool.globalInstance()
    devices: dict[str, Camera | Modulator] = {}
    windows: dict[str, CameraPreviewWindow | CameraInfoWindow | CameraSettingsWindow | ModulatorPreviewWindow | ModulatorInfoWindow | ModulatorSettingsWindow | SimpleProcWindow | SpeckleCalProcWindow | SpeckleNullProcWindow | SpeckleNullProcPreviewWindow] = {}
    workers: dict[str, CameraUpdateWorker | ModulatorUpdateWorker | SourceStorageWorker | SinkStorageWorker | SimpleProcWorker | SpeckleCalProcWorker | SpeckleNullProcWorker] = {}


data = Data()
