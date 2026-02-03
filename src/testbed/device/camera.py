import numpy as np
from datetime import datetime

from . import Device, Stream, ZMQLink, SourceSample
from ..function import Flip, Rotation

from pykato.log import setup_logger

logger = setup_logger("Camera", terminator="\n")


class Camera(Device):
    """
    Camera
    """

    __slots__ = ("_stream", "_shape", "_link", "_rotation", "_flip", "_sample", "wait_for_request", "post_response")

    def __init__(self, stream: Stream):
        super().__init__(stream.name)
        self._stream = stream
        self._rotation = Rotation.UP  # UP for 0deg, RIGHT for 90deg, DOWN for 180deg, LEFT for 270deg
        self._flip = Flip.NEG
        self._shape = (self._stream.keywords["HEIGHT"].value, self._stream.keywords["WIDTH"].value)
        self._link = None
        if self._stream.port != -1:
            self._link = ZMQLink(port=self._stream.port)
            self._link.connect()
        self._sample = SourceSample(self.last_access_time, self.exposure_time_s, self.gain, self.frame_rate_fps, self.temperature_c, self.roi, self.blank)
        self.wait_for_request = self._stream.wait_for_request
        self.post_response = self._stream.post_response

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
    def full_shape(self) -> tuple[int, int]:
        return self._stream.full_shape

    @property
    def port(self) -> int:
        return self._stream.port

    @property
    def shape(self) -> tuple[int, int]:
        return self._shape

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

    @property
    def rotation(self) -> Rotation:
        return self._rotation

    @rotation.setter
    def rotation(self, value: Rotation):
        self._rotation = value

    @property
    def flip(self) -> Flip:
        return self._flip

    @flip.setter
    def flip(self, value: Flip):
        self._flip = value

    def pull_capture(self) -> SourceSample:
        capture = self._stream.get_data().reshape(self.shape)
        self._sample = SourceSample(self.last_access_time, self.exposure_time_s, self.gain, self.frame_rate_fps, self.temperature_c, self.roi, capture.copy())
        return self._sample
    
    def set_capture(self, capture: np.ndarray) -> SourceSample:
        self._stream.set_data(capture)
        self._sample = SourceSample(self.last_access_time, self.exposure_time_s, self.gain, self.frame_rate_fps, self.temperature_c, self.roi, capture.copy())
        return self._sample

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

    def update_keywords(self):
        self._stream.update_keywords()

    def sync_settings(self) -> dict:
        return self.link.sync_settings()

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
        return reply["settings"]["exposureTime_s"]

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
        return reply["settings"]["gain"]

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
        return reply["settings"]["temperature_C"]

    def move_roi(self, x: int, y: int):
        """
        Move roi by x y amount
        """
        logger.info("nudge roi by (%d, %d)", x, y)
        command = {"settings": {"nudge": {"x": x, "y": y}}}
        reply = self.link.send_command(command)
        return reply["settings"]["roi"]

    def __del__(self):
        logger.info("Camera object %s removed", self.name)
        super().__del__()
