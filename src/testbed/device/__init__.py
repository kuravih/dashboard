from enum import Enum, auto
import zmq
import toml
import numpy as np
from datetime import datetime

from pyshmio import SharedMemory
from pykato.log import setup_logger

device_logger = setup_logger("Device", terminator="\n")


class Device:
    """
    Device

    Attributes:
        name: str
            name
    """

    __slots__ = ("_name",)

    def __init__(self, name: str):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str):
        if not isinstance(value, str):
            raise ValueError("Name must be a string")
        self._name = value

    def __del__(self):
        device_logger.info("Device object %s removed", self.name)


stream_logger = setup_logger("Stream", terminator="\n")


class Stream(SharedMemory):
    """
    Stream
    """

    __slots__ = ("_kind", "_sn", "_pxmax", "_full_shape", "_port", "_shape")

    class Kind(Enum):
        CAMERA = auto()
        SLM = auto()
        DM = auto()

        @classmethod
        def from_str(cls, kind: str):
            if kind.upper() == "CAMERA":
                return cls.CAMERA
            elif kind.upper() == "DM":
                return cls.DM
            elif kind.upper() == "SLM":
                return cls.SLM
            else:
                raise ValueError(f"Unknown color: {kind}")

        @classmethod
        def to_str(cls):
            return cls.name.upper()

        def to_str(self):
            return self.name.upper()

    def __init__(self, name: str):
        """
        Construct stream object

        Parameters:
            name: str
                Name of stream
        """
        super().__init__(name)
        if self.keywords["KIND"].value == "CAMERA":
            self._kind = Stream.Kind.CAMERA
        elif self.keywords["KIND"].value == "DM":
            self._kind = Stream.Kind.DM
        elif self.keywords["KIND"].value == "SLM":
            self._kind = Stream.Kind.SLM
        else:
            raise ValueError("Kind keyword not specified")
        self._sn = self.keywords["SN"].value
        self._pxmax = self.keywords["PXMAX"].value
        self._full_shape = (self.keywords["FULL.W"].value, self.keywords["FULL.H"].value)
        self._port = self.keywords["PORT"].value

    @property
    def kind(self) -> Kind:
        return self._kind

    @property
    def sn(self) -> str:
        return self._sn

    @property
    def pxmax(self) -> float | int:
        return self._pxmax

    @property
    def full_shape(self) -> tuple[int, int]:
        return self._full_shape

    @property
    def port(self) -> int:
        return self._port

    def get_data(self) -> np.ndarray:
        if self.pull_data_from_storage() == 0:
            return self.ndarray

    def set_data(self, array: np.ndarray):
        self.ndarray[:] = array.ravel()
        self.push_data_to_storage()


zmqlink_logger = setup_logger("ZMQLink", terminator="\n")


class ZMQLink:
    """
    ZMQ link
    """

    __slots__ = ("_uri", "_context", "_socket", "_connected")

    def __init__(self, uri: str | None = None, address: str | None = None, port: int | None = None):
        super().__init__()
        if (uri is None) and (address is None) and (port is None):
            self._uri = "tcp://127.0.0.1:555"
        elif (uri is not None) and (address is None) and (port is None):
            self._uri = uri
        elif (uri is None) and (address is None) and (port is not None):
            self._uri = f"tcp://127.0.0.1:{port}"
        elif (uri is None) and (address is not None) and (port is not None):
            self._uri = f"tcp://{address}:5555"
        self._context = zmq.Context()
        self._socket = self._context.socket(zmq.REQ)
        self._connected = False

    @property
    def uri(self) -> str:
        return self._uri

    def connect(self):
        self._socket.connect(self._uri)
        self._connected = True

    def disconnect(self):
        self._socket.disconnect(self._uri)
        self._connected = False

    def send(self, message: str):
        self._socket.send_string(message)

    def receive(self) -> str:
        return self._socket.recv_string()

    def send_command(self, command: dict) -> dict:
        self.send(toml.dumps(command))
        rx = self.receive()
        return toml.loads(rx)

    def sync_settings(self):
        command = {"settings": "sync"}
        reply = self.send_command(command)
        return reply["settings"]

    def close(self):
        self._socket.close()
        self._context.term()

    def __del__(self):
        self.close()

    def is_connected(self) -> bool:
        return self._connected


class SourceSample:
    __slots__ = ("last_access_time", "exposure_time_us", "gain", "frame_rate_fps", "temperature_c", "roi", "capture")

    def __init__(self, _last_access_time: datetime, _exposure_time_us: int, _gain: float, _frame_rate_fps: float, _temperature_c: float, _roi: dict[str, tuple[int, int]], _capture: np.ndarray):
        self.last_access_time = _last_access_time
        self.exposure_time_us = _exposure_time_us
        self.gain = _gain
        self.frame_rate_fps = _frame_rate_fps
        self.temperature_c = _temperature_c
        self.roi = _roi
        self.capture = _capture


class SourceSampleStore:
    __slots__ = ("exposure_time_us", "gain", "frame_rate_fps", "temperature_c", "roi", "captures", "timestamps")

    def __init__(self, _exposure_time_us: int, _gain: float, _frame_rate_fps: float, _temperature_c: float, _roi: dict[str, tuple[int, int]], _captures: list[np.ndarray], _timestamps: list[datetime]):
        self.exposure_time_us = _exposure_time_us
        self.gain = _gain
        self.frame_rate_fps = _frame_rate_fps
        self.temperature_c = _temperature_c
        self.roi = _roi
        self.captures = _captures
        self.timestamps = _timestamps


class SinkSample:
    __slots__ = ("last_access_time", "frame_rate_fps", "center", "radius", "command")

    def __init__(self, _last_access_time: datetime, _frame_rate_fps: float, _center: tuple[float, float], _radius: float, _command: np.ndarray):
        self.last_access_time = _last_access_time
        self.frame_rate_fps = _frame_rate_fps
        self.center = _center
        self.radius = _radius
        self.command = _command


class SinkSampleStore:
    __slots__ = ("frame_rate_fps", "center", "radius", "commands", "timestamps")

    def __init__(self, _frame_rate_fps: float, _center: tuple[float, float], _radius: float, _commands: list[np.ndarray], _timestamps: list[datetime]):
        self.frame_rate_fps = _frame_rate_fps
        self.center = _center
        self.radius = _radius
        self.commands = _commands
        self.timestamps = _timestamps
