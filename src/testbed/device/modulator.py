import numpy as np
from datetime import datetime

from . import Device, Stream, ZMQLink, SinkSample
from ..function import Flip, Rotation

from pykato.log import setup_logger

logger = setup_logger("Modulator", terminator="\n")


class Modulator(Device):
    """
    Modulator
    """

    __slots__ = ("_stream", "_shape", "_max_radius", "_link", "_rotation", "_flip", "_sample", "post_request", "wait_for_response")

    def __init__(self, stream: Stream):
        super().__init__(stream.name)
        self._stream = stream
        self._max_radius = self._stream.keywords["RADMAX"].value
        self._rotation = Rotation.UP  # UP for 0deg, RIGHT for 90deg, DOWN for 180deg, LEFT for 270deg
        self._flip = Flip.NEG
        self._shape = (int(2 * np.ceil(self.radius)), int(2 * np.ceil(self.radius)))
        self._link = None
        if self._stream.port != -1:
            self._link = ZMQLink(port=self._stream.port)
            self._link.connect()
        self._sample = SinkSample(self.last_access_time, self.frame_rate_fps, self.center, self.radius, self.blank)
        self.post_request = self._stream.post_request
        self.wait_for_response = self._stream.wait_for_response

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
    def sample(self) -> SinkSample:
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

    def push_command(self, _command: np.ndarray) -> SinkSample:
        self._stream.set_data(_command)
        self._sample = SinkSample(self.last_access_time, self.frame_rate_fps, self.center, self.radius, _command.copy())
        return self._sample

    def get_command(self) -> SinkSample:
        command = self._stream.get_data().reshape(self.shape)
        self._sample = SinkSample(self.last_access_time, self.frame_rate_fps, self.center, self.radius, command.copy())
        return self._sample

    @property
    def center(self) -> tuple[float, float]:
        return (self._stream.keywords["CENTER.X"].value, self._stream.keywords["CENTER.Y"].value)

    @property
    def radius(self) -> float:
        return self._stream.keywords["RADIUS"].value

    @property
    def max_radius(self) -> int:
        return self._max_radius

    def update_keywords(self):
        self._stream.update_keywords()

    def sync_settings(self) -> dict:
        return self.link.sync_settings()

    def move_center(self, x: int, y: int) -> dict:
        """
        Move roi by x y amount
        """
        logger.info("nudge center by (%d, %d)", x, y)
        command = {"settings": {"nudge": {"x": x, "y": y}}}
        reply = self.link.send_command(command)
        return reply["settings"]["center"]

    def set_radius(self, radius: float) -> float:
        """
        Change radius
        """
        command = {"settings": {"radius": radius}}
        reply = self.link.send_command(command)
        return reply["settings"]["radius"]

    def __del__(self):
        logger.info("Modulator object %s removed", self.name)
        super().__del__()
