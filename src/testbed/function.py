from enum import Enum, auto
import struct
import numpy as np
from astropy.io import fits
from datetime import datetime
import numpy as np


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


class Rotation(Enum):
    UP = auto()
    RIGHT = auto()
    DOWN = auto()
    LEFT = auto()


def flip_rotate(_frame: np.ndarray, _flip: Flip, _rotation: Rotation):
    frame = np.rot90(_frame, _rotation.value - 1)
    if _flip == Flip.NEG:
        return np.fliplr(frame)
    else:
        return frame


def save_command(filename: str, command: np.ndarray):
    primary_hdu = fits.PrimaryHDU(command)
    primary_hdu.header["UNIT"] = "Voltage"
    hdu_list = fits.HDUList([primary_hdu])
    hdu_list.writeto(filename, overwrite=True)


def read_source_samples(filename: str) -> tuple[dict[str, int | float | str | dict[str, tuple[int, int]]], list[dict[str, datetime | np.ndarray]]]:

    header_fmt = "<7s" + "HH" + "I" + "fff" + "HHHH" + "B"
    header_size = struct.calcsize(header_fmt)

    with open(filename, "rb") as f:
        # --- read header ---
        header_bytes = f.read(header_size)
        magic, h, w, exposure_us, gain, fps, temp_c, tlx, tly, brx, bry, dtype_code = struct.unpack(header_fmt, header_bytes)

        if magic != b"SRCSMPL":
            raise ValueError("Invalid file header (magic mismatch)")

        dtype = INV_DTYPE_MAP[dtype_code]
        capture_size = h * w * np.dtype(dtype).itemsize

        # --- read capture records ---
        samples = []
        while True:
            ts_bytes = f.read(8)
            if len(ts_bytes) < 8:
                break  # EOF
            (timestamp,) = struct.unpack("<d", ts_bytes)

            capture_bytes = f.read(capture_size)
            if len(capture_bytes) < capture_size:
                break  # incomplete capture

            capture = np.frombuffer(capture_bytes, dtype=dtype).reshape((h, w))
            samples.append(
                {
                    "timestamp": datetime.fromtimestamp(timestamp),
                    "capture": capture,
                }
            )

    header_info = {
        "magic": magic.decode(),
        "height": h,
        "width": w,
        "exposure_time_us": exposure_us,
        "gain": gain,
        "frame_rate_fps": fps,
        "temperature_c": temp_c,
        "roi": {"tl": (tlx, tly), "br": (brx, bry)},
        "dtype": dtype,
    }

    return header_info, samples


def read_sink_samples(filename: str) -> tuple[dict[str, int | float | str | dict[str, tuple[int, int]]], list[dict[str, datetime | np.ndarray]]]:

    header_fmt = "<7s" + "HH" + "f" + "fff" + "B"
    header_size = struct.calcsize(header_fmt)

    with open(filename, "rb") as f:
        # --- read header ---
        header_bytes = f.read(header_size)
        magic, h, w, fps, centerx, centery, radius, dtype_code = struct.unpack(header_fmt, header_bytes)

        if magic != b"SNKSMPL":
            raise ValueError("Invalid file header (magic mismatch)")

        dtype = INV_DTYPE_MAP[dtype_code]
        command_size = h * w * np.dtype(dtype).itemsize

        # --- read command records ---
        samples = []
        while True:
            ts_bytes = f.read(8)
            if len(ts_bytes) < 8:
                break  # EOF
            (timestamp,) = struct.unpack("<d", ts_bytes)

            command_bytes = f.read(command_size)
            if len(command_bytes) < command_size:
                break  # incomplete command

            command = np.frombuffer(command_bytes, dtype=dtype).reshape((h, w))
            samples.append(
                {
                    "timestamp": datetime.fromtimestamp(timestamp),
                    "command": command,
                }
            )

    header_info = {
        "magic": magic.decode(),
        "height": h,
        "width": w,
        "frame_rate_fps": fps,
        "center": (centerx, centery),
        "radius": radius,
        "dtype": dtype,
    }

    return header_info, samples
