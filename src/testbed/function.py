import pickle
from enum import Enum, auto
import struct
import numpy as np
from datetime import datetime
from .device import SinkSample, SinkSampleStore, SourceSample, SourceSampleStore
from io import FileIO
from pykato.log import setup_logger

from skimage.feature import peak_local_max
from skimage.morphology import disk, dilation
from skimage.measure import label, regionprops

logger = setup_logger("function", terminator="\n")

DTYPE_MAP = {
    np.uint8: 1,
    np.int8: 2,
    np.uint16: 3,
    np.int16: 4,
    np.uint32: 5,
    np.int32: 6,
    np.uint64: 7,
    np.int64: 8,
    np.float32: 9,
    np.float64: 10,
}
INV_DTYPE_MAP = {v: k for k, v in DTYPE_MAP.items()}


class Flip(Enum):
    NEG = auto()
    POS = auto()

    @classmethod
    def from_bool(cls, value: bool):
        return cls.POS if value else cls.NEG

    def to_bool(self) -> bool:
        return self is Flip.POS


class Rotation(Enum):
    UP = auto()
    RIGHT = auto()
    DOWN = auto()
    LEFT = auto()

    @classmethod
    def from_int(cls, i: int) -> "Rotation":
        return {0: cls.UP, 1: cls.RIGHT, 2: cls.DOWN, 3: cls.LEFT}[i]

    def to_int(self):
        return {Rotation.UP: 0, Rotation.RIGHT: 1, Rotation.DOWN: 2, Rotation.LEFT: 3}[self]


def flip_rotate(_frame: np.ndarray, _flip: Flip, _rotation: Rotation) -> np.ndarray:
    frame = np.rot90(_frame, _rotation.to_int())
    if _flip == Flip.NEG:
        frame = np.fliplr(frame)
    return frame


def write_source_sample_header(_file: FileIO, _sample: SourceSample):
    h, w = _sample.capture.shape[:2]
    tl = _sample.roi.get("tl", (0, 0))
    br = _sample.roi.get("br", (w, h))
    dtype_code = DTYPE_MAP[_sample.capture.dtype.type]
    header = struct.pack(
        "<7s" + "HH" + "I" + "fff" + "HHHH" + "B",
        b"SRCSMPL",
        h,  # unsigned short - H
        w,  # unsigned short - H
        _sample.exposure_time_us,  # unsigned int - I
        _sample.gain,  # float - f
        _sample.frame_rate_fps,  # float - f
        _sample.temperature_c,  # float - f
        tl[0],  # unsigned short - H
        tl[1],  # unsigned short - H
        br[0],  # unsigned short - H
        br[1],  # unsigned short - H
        dtype_code,  # unsigned byte - B
    )
    _file.write(header)


def write_source_sample_data(_file: FileIO, _sample: SourceSample):
    _file.write(struct.pack("<d", _sample.last_access_time.timestamp()) + _sample.capture.tobytes())


def read_source_samples(filename: str) -> SourceSampleStore:

    header_fmt = "<7s" + "HH" + "I" + "fff" + "HHHH" + "B"
    header_size = struct.calcsize(header_fmt)

    with open(filename, "rb") as f:
        # --- read header ---
        header_bytes = f.read(header_size)
        magic, h, w, exposure_us, gain, fps, temp_c, tlx, tly, brx, bry, dtype_code = struct.unpack(header_fmt, header_bytes)
        roi = {"tl": (tlx, tly), "br": (brx, bry)}

        if magic != b"SRCSMPL":
            raise ValueError("Invalid file header (magic mismatch)")

        dtype = INV_DTYPE_MAP[dtype_code]
        capture_size = h * w * np.dtype(dtype).itemsize

        # --- read capture records ---
        captures = []
        timestamps = []
        while True:
            ts_bytes = f.read(8)
            if len(ts_bytes) < 8:
                break  # EOF
            (timestamp,) = struct.unpack("<d", ts_bytes)

            capture_bytes = f.read(capture_size)
            if len(capture_bytes) < capture_size:
                break  # incomplete capture

            capture = np.frombuffer(capture_bytes, dtype=dtype).reshape((h, w))
            timestamp = datetime.fromtimestamp(timestamp)
            captures.append(capture)
            timestamps.append(timestamp)

    return SourceSampleStore(exposure_us, gain, fps, temp_c, roi, np.array(captures), np.array(timestamps))


def write_sink_sample_header(_file: FileIO, _sample: SinkSample):
    h, w = _sample.command.shape[:2]
    center = _sample.center
    dtype_code = DTYPE_MAP[_sample.command.dtype.type]
    header = struct.pack(
        "<7s" + "HH" + "f" + "fff" + "B",
        b"SNKSMPL",
        h,  # unsigned short - H
        w,  # unsigned short - H
        _sample.frame_rate_fps,  # float - f
        center[0],  # unsigned short - H
        center[1],  # unsigned short - H
        _sample.radius,  # unsigned short - H
        dtype_code,  # unsigned byte - B
    )
    _file.write(header)


def write_sink_sample_data(_file: FileIO, _sample: SinkSample):
    _file.write(struct.pack("<d", _sample.last_access_time.timestamp()) + _sample.command.tobytes())


def read_sink_samples(filename: str) -> SinkSampleStore:

    header_fmt = "<7s" + "HH" + "f" + "fff" + "B"
    header_size = struct.calcsize(header_fmt)

    with open(filename, "rb") as f:
        # --- read header ---
        header_bytes = f.read(header_size)
        magic, h, w, fps, centerx, centery, radius, dtype_code = struct.unpack(header_fmt, header_bytes)
        center = (centerx, centery)

        if magic != b"SNKSMPL":
            raise ValueError("Invalid file header (magic mismatch)")

        dtype = INV_DTYPE_MAP[dtype_code]
        command_size = h * w * np.dtype(dtype).itemsize

        # --- read command records ---
        commands = []
        timestamps = []
        while True:
            ts_bytes = f.read(8)
            if len(ts_bytes) < 8:
                break  # EOF
            (timestamp,) = struct.unpack("<d", ts_bytes)

            command_bytes = f.read(command_size)
            if len(command_bytes) < command_size:
                break  # incomplete command

            command = np.frombuffer(command_bytes, dtype=dtype).reshape((h, w))
            timestamp = datetime.fromtimestamp(timestamp)
            commands.append(command)
            timestamps.append(timestamp)

    return SinkSampleStore(fps, center, radius, np.array(commands), np.array(timestamps))


def find_speckles(speckle_image: np.ndarray, num_peaks: int = 1, footprint_size: int = 10, min_distance: int = 1) -> tuple[list[tuple[float, float]], np.ndarray]:
    rot_speckle_image = speckle_image
    peak_idx = peak_local_max(rot_speckle_image, num_peaks=num_peaks, min_distance=min_distance, threshold_abs=None)
    peak_mask = np.zeros_like(rot_speckle_image, dtype=bool)
    peak_mask[tuple(peak_idx.T)] = True
    disk_mask = disk(footprint_size)
    peak_mask = dilation(peak_mask, disk_mask)
    label_image = label(peak_mask)
    speckles = regionprops(label_image, rot_speckle_image)
    ind = np.lexsort(([speckle.centroid_weighted[0] for speckle in speckles], [speckle.centroid_weighted[1] for speckle in speckles]))
    return [(speckles[i].centroid_weighted[1], speckles[i].centroid_weighted[0]) for i in ind], peak_mask


def speckle_parameters(center: tuple[float, float], speckle_location_px: tuple[float, float], speck_calibration: dict[str, dict[str, float]]) -> tuple[float, float]:
    speckle_location_px_delta = np.array(speckle_location_px) - np.array(center)
    speckle_dist = np.hypot(speckle_location_px_delta[0], speckle_location_px_delta[1])
    speckle_angle = -np.arctan2(speckle_location_px_delta[0], speckle_location_px_delta[1])
    speckle_frequency = (speckle_dist - speck_calibration["speck_dist_cmd_freq"]["intercept"]) / speck_calibration["speck_dist_cmd_freq"]["slope"]
    speckle_angle = (speckle_angle - speck_calibration["speck_angle_cmd_angle"]["intercept"]) / speck_calibration["speck_angle_cmd_angle"]["slope"]
    return speckle_frequency, speckle_angle


def is_speckle_calibration_file_valid(speck_cal_filepath: str) -> bool:
    with open(speck_cal_filepath, "rb") as _input:
        d = pickle.load(_input)

    if "speck_angle_cmd_angle" not in d:
        return False
    if "slope" not in d["speck_angle_cmd_angle"]:
        return False
    if "intercept" not in d["speck_angle_cmd_angle"]:
        return False

    if "speck_dist_cmd_freq" not in d:
        return False
    if "slope" not in d["speck_dist_cmd_freq"]:
        return False
    if "intercept" not in d["speck_dist_cmd_freq"]:
        return False

    return True


def sin_fit_fn(x, amplitude, frequency, phase, offset):
    return amplitude * np.sin(frequency * x + phase) + offset


def constrained_sin_fit_fn(x, amplitude, phase, offset):
    return sin_fit_fn(x, amplitude, 1, phase, offset)


def quadratic_fit_fn(x, a, b, c):
    return a * x * x + b * x + c
