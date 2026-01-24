from enum import Enum, auto
import zmq
import toml
import numpy as np
from datetime import datetime

from pyshmio import SharedMemory, Keyword, KeywordType, DataType
from pykato.log import setup_logger

device_logger = setup_logger("Device", terminator="\n")


def create_camera_memory(name: str, full_size: tuple[int, int], roi_size: tuple[int, int], dtype: DataType, serial: str, pxmax: int, port: int) -> SharedMemory:
    # ---- constants ----
    kw_kind = Keyword("KIND", KeywordType.STRING, "CAMERA", "Device kind")
    kw_sn = Keyword("SN", KeywordType.STRING, serial, "Serial number")
    kw_pxmax = Keyword("PXMAX", KeywordType.LONG, int(pxmax), "Pixel max")
    kw_full_w = Keyword("FULL.W", KeywordType.LONG, int(full_size[0]), "Detector width")
    kw_full_h = Keyword("FULL.H", KeywordType.LONG, int(full_size[1]), "Detector height")
    kw_port = Keyword("PORT", KeywordType.LONG, int(port), "Link port")
    kw_width = Keyword("WIDTH", KeywordType.LONG, int(roi_size[0]), "Width (px)")
    kw_height = Keyword("HEIGHT", KeywordType.LONG, int(roi_size[1]), "Height (px)")
    # ---- variables ----
    kw_exptime = Keyword("EXPTIME", KeywordType.LONG, int(0), "Exposure time (us)")
    kw_frmrate = Keyword("FRMRATE", KeywordType.DOUBLE, float(0), "Frame rate (fps)")
    kw_gain = Keyword("GAIN", KeywordType.DOUBLE, float(0), "Gain (units)")
    kw_temp = Keyword("TEMP", KeywordType.DOUBLE, float(0), "Temperature (C)")
    kw_roi_tl_x = Keyword("ROI.TL.X", KeywordType.LONG, int(0), "Region of interest top left x")
    kw_roi_tl_y = Keyword("ROI.TL.Y", KeywordType.LONG, int(0), "Region of interest top left y")
    kw_roi_br_x = Keyword("ROI.BR.X", KeywordType.LONG, int(roi_size[0]), "Region of interest bottom right x")
    kw_roi_br_y = Keyword("ROI.BR.Y", KeywordType.LONG, int(roi_size[1]), "Region of interest bottom right y")

    return SharedMemory.create(name, roi_size[0] * roi_size[1], dtype, [kw_kind, kw_sn, kw_pxmax, kw_full_w, kw_full_h, kw_port, kw_width, kw_height, kw_exptime, kw_frmrate, kw_gain, kw_temp, kw_roi_tl_x, kw_roi_tl_y, kw_roi_br_x, kw_roi_br_y])


def create_modulator_memory(name: str, full_size: tuple[int, int], center: tuple[float, float], radius: float, dtype: DataType, serial: str, pxmax: int, port: int) -> SharedMemory:
    # ---- constants ----
    kw_kind = Keyword("KIND", KeywordType.STRING, "SLM", "Device kind")
    kw_sn = Keyword("SN", KeywordType.STRING, serial, "Serial number")
    kw_pxmax = Keyword("PXMAX", KeywordType.LONG, int(pxmax), "Pixel max")
    kw_full_w = Keyword("FULL.W", KeywordType.LONG, int(full_size[0]), "Detector width")
    kw_full_h = Keyword("FULL.H", KeywordType.LONG, int(full_size[1]), "Detector height")
    kw_port = Keyword("PORT", KeywordType.LONG, int(port), "Link port")
    kw_radmax = Keyword("RADMAX", KeywordType.LONG, int(radius), "Maximum Radius (px)")
    # ---- variables ----
    kw_radius = Keyword("RADIUS", KeywordType.DOUBLE, float(radius), "Radius (px)")
    kw_center_x = Keyword("CENTER.X", KeywordType.DOUBLE, float(center[0]), "Center x (px)")
    kw_center_y = Keyword("CENTER.Y", KeywordType.DOUBLE, float(center[1]), "Center y (px)")
    kw_frmrate = Keyword("FRMRATE", KeywordType.DOUBLE, float(0), "Frame rate (fps)")

    return SharedMemory.create(name, 2 * radius * 2 * radius, dtype, [kw_kind, kw_sn, kw_pxmax, kw_full_w, kw_full_h, kw_port, kw_radmax, kw_radius, kw_center_x, kw_center_y, kw_frmrate])


class Device:
    """
    Device

    Attributes:
        name: str
            name
    """

    __slots__ = ("_name",)

    def __init__(self, name: str):
        self.name = name

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
                raise ValueError(f"Unknown kind: {kind}")

        def to_str(self):
            return self.name.upper()

    __slots__ = ("_kind", "_sn", "_pxmax", "_full_shape", "_port", "_shape")

    def __init__(self, source: str | SharedMemory):
        """
        Construct stream object

        Parameters:
            source: str | SharedMemory
                Stream name or existing SharedMemory to attach to
        """

        if isinstance(source, str):
            super().__init__(source)
        else:
            super().__init__(source.name)

        self.kind = self.keywords["KIND"].value
        self._sn = self.keywords["SN"].value
        self._pxmax = self.keywords["PXMAX"].value
        self._full_shape = (self.keywords["FULL.W"].value, self.keywords["FULL.H"].value)
        self._port = self.keywords["PORT"].value

    @property
    def kind(self) -> Kind:
        return self._kind

    @kind.setter
    def kind(self, value: Kind | str):
        if isinstance(value, self.Kind):
            self._kind = value
        elif isinstance(value, str):
            self._kind = self.Kind.from_str(value)
        else:
            raise TypeError(f"kind must be Kind or str, got {type(value).__name__}")

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
        self.post_request()
        self.wait_for_response()
        return self.ndarray

    def set_data(self, array: np.ndarray):
        self.wait_for_request()
        self.ndarray[:] = array.ravel()
        self.post_response()


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
        elif (uri is None) and (address is None) and (port is not None):
            self._uri = f"tcp://127.0.0.1:{port}"
        elif (uri is None) and (address is not None) and (port is None):
            self._uri = f"tcp://{address}:5555"
        elif (uri is None) and (address is not None) and (port is not None):
            self._uri = f"tcp://{address}:{port}"
        elif uri is not None:
            self._uri = uri
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

    def __init__(self, last_access_time: datetime, exposure_time_us: int, gain: float, frame_rate_fps: float, temperature_c: float, roi: dict[str, tuple[int, int]], capture: np.ndarray):
        self.last_access_time = last_access_time
        self.exposure_time_us = exposure_time_us
        self.gain = gain
        self.frame_rate_fps = frame_rate_fps
        self.temperature_c = temperature_c
        self.roi = roi
        self.capture = capture


class SinkSample:
    __slots__ = ("last_access_time", "frame_rate_fps", "center", "radius", "command")

    def __init__(self, last_access_time: datetime, frame_rate_fps: float, center: tuple[float, float], radius: float, command: np.ndarray):
        self.last_access_time = last_access_time
        self.frame_rate_fps = frame_rate_fps
        self.center = center
        self.radius = radius
        self.command = command
