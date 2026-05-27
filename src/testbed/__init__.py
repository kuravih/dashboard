from PySide6.QtCore import QThreadPool

from .device.camera import Camera
from .device.modulator import Modulator
from .widget.camera_window import PreviewWindow as CameraPreviewWindow, InfoWindow as CameraInfoWindow, SettingsWindow as CameraSettingsWindow
from .widget.modulator_window import PreviewWindow as ModulatorPreviewWindow, InfoWindow as ModulatorInfoWindow, SettingsWindow as ModulatorSettingsWindow, PresetsWindow as ModulatorPresetsWindow

SIMPLE_LOOP = "simple_loop"
from .widget.simple_loop_window import ProcessWindow as SimpleLoopWindow
from .worker.simple_loop_worker import ProcessWorker as SimpleLoopWorker

CAPTURE_LOOP = "capture_loop"
from .widget.capture_loop_window import ProcessWindow as CaptureLoopWindow
from .worker.capture_loop_worker import ProcessWorker as CaptureLoopWorker

SPECKLE_CAPTURE_LOOP = "speckle_capture_loop"
from .widget.speckle_capture_window import ProcessWindow as SpeckleCaptureLoopWindow
from .worker.speckle_capture_worker import ProcessWorker as SpeckleCaptureLoopWorker

SPECKLE_CALIBRATION = "speckle_calibration"
from .widget.speckle_calibration_window import ProcessWindow as SpeckleCalibrationWindow
from .worker.speckle_calibration_worker import ProcessWorker as SpeckleCalibrationWorker

SPECKLE_NULLING = "speckle_nulling"
from .widget.speckle_nulling_window import ProcessWindow as SpeckleNullingWindow, ProcessPreviewWindow as SpeckleNullingPreviewWindow, ProcessInfoWindow as SpeckleNullingInfoWindow
from .worker.speckle_nulling_worker import ProcessWorker as SpeckleNullingWorker

RECENTER = "recenter"
from .widget.recenter_window import ProcessWindow as RecenterWindow
from .worker.recenter_worker import ProcessWorker as RecenterWorker

CAMERA_CALIBRATION = "camera_calibration"
from .widget.camera_calibration_window import ProcessWindow as CameraCalibrationWindow
from .worker.camera_calibration_worker import ProcessWorker as CameraCalibrationWorker

DOTF_MEASUREMENT = "dotf_measurement"
from .widget.dotf_measurement_window import ProcessWindow as DOTFMeasurementWindow
from .worker.dotf_measurement_worker import ProcessWorker as DOTFMeasurementWorker

PAIRWISE_FPWFS = "pairwise_fpwfs"
from .widget.pairwise_fpwfs_window import ProcessWindow as PairwiseFPWFSWindow
from .worker.pairwise_fpwfs_worker import ProcessWorker as PairwiseFPWFSWorker

from .worker.camera_worker import ProcessWorker as CameraSamplingWorker
from .worker.modulator_worker import ProcessWorker as ModulatorSamplingWorker
from .worker.storage_worker import SourceStorageWorker, SinkStorageWorker


class Data:
    threadpool = QThreadPool.globalInstance()
    devices: dict[str, Camera | Modulator] = {}
    windows: dict[str, CameraPreviewWindow | CameraInfoWindow | CameraSettingsWindow | ModulatorPreviewWindow | ModulatorInfoWindow | ModulatorSettingsWindow | ModulatorPresetsWindow | SimpleLoopWindow | CaptureLoopWindow | SpeckleCaptureLoopWindow | SpeckleCalibrationWindow | SpeckleNullingWindow | SpeckleNullingPreviewWindow | SpeckleNullingInfoWindow | RecenterWindow | CameraCalibrationWindow | DOTFMeasurementWindow | PairwiseFPWFSWindow] = {}
    workers: dict[str, CameraSamplingWorker | ModulatorSamplingWorker | SourceStorageWorker | SinkStorageWorker | SimpleLoopWorker | CaptureLoopWorker | SpeckleCaptureLoopWorker | SpeckleCalibrationWorker | SpeckleNullingWorker | RecenterWorker | CameraCalibrationWorker | DOTFMeasurementWorker | PairwiseFPWFSWorker] = {}

    @classmethod
    def is_device_alive(cls, name: str) -> bool:
        return name in cls.devices

    @classmethod
    def is_window_alive(cls, name: str) -> bool:
        return name in cls.windows

    @classmethod
    def is_worker_alive(cls, name: str) -> bool:
        return name in cls.workers


data = Data()
