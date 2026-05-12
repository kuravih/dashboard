import numpy as np
from datetime import datetime

from . import Device, Stream, ZMQLink, SourceSample
from ..function import is_camera_calibration_file_valid, read_camera_calibration_file, capture_to_intensity, calculate_quantum_efficiency, intensity_limits

from pykato.log import setup_logger

logger = setup_logger("Camera", terminator="\n")


class Camera(Device):
    """
    Camera
    """

    __slots__ = ("_stream", "_shape", "_link", "_sample", "wait_for_request", "post_response", "_settings", "_calibration_file", "_calibration")

    def __init__(self, stream: Stream):
        super().__init__(stream.name)
        self._stream = stream
        self._shape = (self._stream.keywords["HEIGHT"].value, self._stream.keywords["WIDTH"].value)
        self._link: ZMQLink | None = None
        self._settings: dict[str, float | dict[str, tuple[tuple[int, int], tuple[int, int]]]] | None = None
        if self._stream.port != -1:
            self._link = ZMQLink(port=self._stream.port)
            self._link.connect()
            self.sync_settings()
        self._sample = SourceSample(self.last_access_time, self.exposure_time_s, self.gain, self.frame_rate_fps, self.temperature_c, self.roi, self.blank)
        self.wait_for_request = self._stream.wait_for_request
        self.post_response = self._stream.post_response
        self._calibration_file: str | None = None
        self._calibration: dict[str, np.ndarray] | None = None

    @property
    def kind(self) -> Stream.Kind:
        return self._stream.kind

    @property
    def sn(self) -> str:
        return self._stream.sn

    @property
    def pxmax(self) -> float | int:
        return self._stream.pxmax

    @property
    def clim(self) -> tuple[float, float]:
        limits = (0.0, self.pxmax)
        if self.calibration is not None:
            qe_perc = calculate_quantum_efficiency(630.0, *self.calibration["quantum_efficiency"])
            limits = intensity_limits(limits, self.exposure_time_s, self.calibration["dark_rate"], self.calibration["bias"], qe_perc, self.calibration["gain"])
        return limits

    @property
    def full_shape(self) -> tuple[int, int]:
        return self._stream.full_shape

    @property
    def port(self) -> int:
        return self._stream.port

    @property
    def shape(self) -> tuple[int, int]:
        return self._shape

    @property
    def settings(self) -> dict[str, float | dict[str, tuple[tuple[int, int], tuple[int, int]]]] | None:
        return self._settings

    @property
    def frame_rate_fps(self) -> float:
        return self._stream.keywords["FRMRATE"].value

    @property
    def link(self) -> ZMQLink | None:
        return self._link

    @property
    def blank(self) -> np.ndarray:
        return np.zeros(self.shape)

    @property
    def sample(self) -> SourceSample:
        return self._sample

    @property
    def creation_time(self) -> datetime:
        return self._stream.creation_time

    @property
    def last_access_time(self) -> datetime:
        return self._stream.last_access_time

    def pull_capture(self) -> SourceSample:
        capture = self._stream.get_data().reshape(self.shape)
        if self.calibration is not None:
            qe_perc = calculate_quantum_efficiency(630.0, *self.calibration["quantum_efficiency"])
            capture = capture_to_intensity(capture, self.exposure_time_s, self.calibration["dark_rate"], self.calibration["bias"], qe_perc, self.calibration["gain"])
        self._sample = SourceSample(self.last_access_time, self.exposure_time_s, self.gain, self.frame_rate_fps, self.temperature_c, self.roi, capture.copy())
        return self._sample

    def set_capture(self, capture: np.ndarray):
        self._stream.set_data(capture)

    @property
    def exposure_time_s(self) -> int:
        return self._stream.keywords["EXPTIME"].value

    @property
    def gain(self) -> float:
        return self._stream.keywords["GAIN"].value

    @property
    def temperature_c(self) -> float:
        return self._stream.keywords["TEMP"].value

    @property
    def roi(self) -> dict[str, tuple[int, int]]:
        return {"br": (self._stream.keywords["ROI.BR.X"].value, self._stream.keywords["ROI.BR.Y"].value), "tl": (self._stream.keywords["ROI.TL.X"].value, self._stream.keywords["ROI.TL.Y"].value)}

    @property
    def calibration(self) -> dict[str, np.ndarray] | None:
        return self._calibration

    @calibration.setter
    def calibration(self, value: dict[str, np.ndarray] | None):
        self._calibration = value

    @property
    def calibration_file(self) -> str | None:
        return self._calibration_file

    @calibration_file.setter
    def calibration_file(self, value: str | None):
        self._calibration_file = value

    def set_calibration(self, calibration_file: str | None):
        self.calibration_file = calibration_file
        if self.calibration_file is not None and is_camera_calibration_file_valid(self.calibration_file, self.full_shape):
            self.calibration = read_camera_calibration_file(self.calibration_file, self.roi)
        else:
            self.calibration = None

    def update_keywords(self):
        self._stream.update_keywords()

    def sync_settings(self):
        self._settings = self.link.sync_settings()

    def set_exposure_time_s(self, exposure_time_s: float) -> int:
        """
        Set the exposure time of the camera

        Parameters:
            exposure_time_s: float
                Exposure time in s

        Returns: int
            Exposure time response from camera
        """
        command = {"settings": {"exposureTime_s": exposure_time_s}}
        reply = self.link.send_command(command)
        self._settings = reply["settings"]
        return self._settings["exposureTime_s"]

    def set_gain(self, gain: float) -> float:
        """
        Set the gain of the camera

        Parameters:
            gain: int
                gain

        Returns: int
            Gain response from camera
        """
        command = {"settings": {"gain": gain}}
        reply = self.link.send_command(command)
        self._settings = reply["settings"]
        return self._settings["gain"]

    def set_temperature_c(self, temperature_c: float) -> float:
        """
        Set the temperature of the camera

        Parameters:
            temperature_c: float
                temperature in c

        Returns: int
            Temperature response from camera
        """
        command = {"settings": {"temperature_C": temperature_c}}
        reply = self.link.send_command(command)
        self._settings = reply["settings"]
        return self._settings["temperature_C"]

    def move_roi(self, x: int, y: int):
        """
        Move roi by x y amount
        """
        logger.info("nudge roi by (%d, %d)", x, y)
        command = {"settings": {"nudge": {"x": x, "y": y}}}
        reply = self.link.send_command(command)
        self._settings = reply["settings"]
        return self._settings["roi"]

    def __del__(self):
        logger.info("Camera object %s removed", self.name)
        super().__del__()
