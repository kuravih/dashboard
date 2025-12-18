import numpy as np
from datetime import datetime

from . import Device, Stream, ZMQLink, SinkSample
from ..function import flip_rotate, Rotation, Flip

from pykato.log import setup_logger

logger = setup_logger("Modulator", terminator="\n")


class Modulator(Device):
    """
    Modulator
    """

    __slots__ = ("_stream", "_shape", "_max_radius", "_link", "_rotation", "_flip", "_command")

    def __init__(self, stream: Stream):
        super().__init__(stream.name)
        self._stream = stream
        self._max_radius = self._stream.keywords["RADMAX"].value
        self._rotation = Rotation.UP
        self._flip = Flip.POS
        self._shape = (int(2 * np.ceil(self.radius)), int(2 * np.ceil(self.radius)))
        self._command = self.blank
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
    def full_shape(self) -> tuple[int, int]:
        return self._stream.full_shape

    @property
    def port(self) -> int:
        return self._stream.port

    @property
    def shape(self) -> tuple[int, int]:
        return self._shape

    @property
    def center(self) -> tuple[float, float]:
        return (self._stream.keywords["CENTER.X"].value, self._stream.keywords["CENTER.Y"].value)

    @property
    def radius(self) -> float:
        return self._stream.keywords["RADIUS"].value

    @property
    def max_radius(self) -> int:
        return self._max_radius

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
    def command(self) -> np.ndarray:
        return flip_rotate(self._command, self.flip, self.rotation)

    @command.setter
    def command(self, cmd: np.ndarray):
        self._command = cmd

    def push_command(self, command: np.ndarray | None):
        if command is not None:
            self._command = command
        self._stream.set_data(self._command)

    def pull_sample(self) -> SinkSample:
        return SinkSample(self.last_access_time, self.frame_rate_fps, self.center, self.radius, self.command)

    def pull_blank_sample(self) -> SinkSample:
        return SinkSample(self.last_access_time, self.frame_rate_fps, self.center, self.radius, self.blank)

    @property
    def pxmax(self) -> float | int:
        return self._stream.pxmax

    @property
    def creation_time(self) -> datetime:
        return self._stream.creation_time

    @property
    def last_access_time(self) -> datetime:
        return self._stream.last_access_time

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
        logger.info("Modulator object %s removed", self.name)
        super().__del__()
