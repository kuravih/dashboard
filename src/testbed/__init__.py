from PySide6.QtCore import QThreadPool

from .device.camera import Camera
from .device.modulator import Modulator
from .widget.camera_window import PreviewWindow as CameraPreviewWindow, InfoWindow as CameraInfoWindow, SettingsWindow as CameraSettingsWindow
from .widget.modulator_window import PreviewWindow as ModulatorPreviewWindow, InfoWindow as ModulatorInfoWindow, SettingsWindow as ModulatorSettingsWindow
from .widget.simple_proc_window import SimpleProcWindow
from .widget.speckle_cal_proc_window import SpeckleCalProcWindow
from .widget.speckle_null_proc_window import SpeckleNullProcWindow

from .worker.camera_worker import UpdateWorker as CameraUpdateWorker
from .worker.modulator_worker import UpdateWorker as ModulatorUpdateWorker


class Data:
    threadpool = QThreadPool.globalInstance()
    devices: dict[str, Camera | Modulator] = {}
    windows: dict[str, CameraPreviewWindow | CameraInfoWindow | CameraSettingsWindow | ModulatorPreviewWindow | ModulatorInfoWindow | ModulatorSettingsWindow | SimpleProcWindow | SpeckleCalProcWindow | SpeckleNullProcWindow] = {}
    workers: dict[str, CameraUpdateWorker | ModulatorUpdateWorker] = {}


data = Data()
