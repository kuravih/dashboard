import numpy as np
from datetime import datetime

from . import Device, Stream, ZMQLink, SourceSample
from ..function import flip_rotate, Flip, Rotation

from pykato.log import setup_logger

logger = setup_logger("Camera", terminator="\n")


class Camera(Device):
    """
    Camera
    """

    __slots__ = ("_stream", "_shape", "_link", "_rotation", "_flip")

    def __init__(self, stream: Stream):
        super().__init__(stream.name)
        self._stream = stream
        self._rotation = Rotation.UP
        self._flip = Flip.POS
        self._shape = (self._stream.keywords["WIDTH"].value, self._stream.keywords["HEIGHT"].value)
        self._link = None
        if self._stream.port != -1:
            self._link = ZMQLink(port=self._stream.port)
            self._link.connect()

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
    def exposure_time_us(self) -> int:
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
    def shape(self) -> tuple[int, int]:
        return self._shape

    @property
    def frame_rate_fps(self) -> float:
        return self._stream.keywords["FRMRATE"].value

    @property
    def link(self) -> ZMQLink:
        assert self._link is not None, "Link is not setup"
        return self._link

    @property
    def blank(self) -> np.ndarray:
        return np.zeros(self.shape)

    @property
    def creation_time(self) -> datetime:
        return self._stream.creation_time

    @property
    def last_access_time(self) -> datetime:
        return self._stream.last_access_time

    def pull_capture(self) -> np.ndarray:
        return flip_rotate(self._stream.get_data().reshape(self.shape), self.flip, self.rotation)

    def pull_sample(self) -> SourceSample:
        return SourceSample(self.last_access_time, self.exposure_time_us, self.gain, self.frame_rate_fps, self.temperature_c, self.roi, self.pull_capture())

    def pull_blank_sample(self) -> SourceSample:
        return SourceSample(self.last_access_time, self.exposure_time_us, self.gain, self.frame_rate_fps, self.temperature_c, self.roi, self.blank)

    def update_keywords(self):
        self._stream.update_keywords()

    def sync_settings(self) -> dict:
        return self.link.sync_settings()

    def set_exposure_time_us(self, exposure_time_us: int) -> int:
        """
        Set the exposure time of the camera

        Parameters:
            exposure_time_us: int
                Exposure time in us

        Returns: int
            Exposure time response from camera
        """
        command = {"settings": {"exposureTime_us": exposure_time_us}}
        reply = self.link.send_command(command)
        return reply["settings"]["exposureTime_us"]

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

    @property
    def rotation(self) -> Rotation:
        return self._rotation

    @rotation.setter
    def rotation(self, _rotation: Rotation):
        self._rotation = _rotation

    @property
    def flip(self) -> Flip:
        return self._flip

    @flip.setter
    def flip(self, _flip: Flip):
        self._flip = _flip

    def __del__(self):
        logger.info("Camera object %s removed", self.name)
        super().__del__()
