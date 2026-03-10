import pickle
from enum import Enum, IntEnum, auto
import struct
import numpy as np
from datetime import datetime
from .device import SinkSample, SourceSample
from io import FileIO
from pykato.log import setup_logger
from pykato.function import box, generate_coordinates

from skimage.feature import peak_local_max
from skimage.morphology import disk, dilation
from skimage.measure import label, regionprops
from astropy.io import fits

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

HEADER_FORMAT = "=7s2HB"  # 7 char tag + unsigned short width + unsigned short height + unsigned byte datatype
SRC_TAG = b"SRCSMPL"
SRC_HEADER_FORMAT = "=5d4H"  # double timestamp + double frame_rate_fps + double temperature_c + double gain + double exposure_time_s + unsigned short roi.tl.x + unsigned short roi.tl.y + unsigned short roi.br.x + unsigned short roi.br.y
SNK_TAG = b"SNKSMPL"
SNK_HEADER_FORMAT = "=2d3H"  # double timestamp + double frame_rate_fps + unsigned short radius + unsigned short center.x + unsigned short center.y


class Flip(Enum):
    NEG = auto()
    POS = auto()

    @classmethod
    def from_bool(cls, value: bool) -> "Flip":
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


def flip_rotate(frame: np.ndarray, flip: Flip, rotation: Rotation) -> np.ndarray:
    frame = np.rot90(frame, rotation.to_int())
    if flip == Flip.NEG:
        frame = np.fliplr(frame)
    return frame


def write_source_sample_header(fileio: FileIO, sample: SourceSample):
    h, w = sample.capture.shape[:2]
    dtype_code = DTYPE_MAP[sample.capture.dtype.type]
    header = struct.pack(
        HEADER_FORMAT,  # 7 char tag + unsigned short width + unsigned short height + unsigned byte datatype
        SRC_TAG,  # 7 char tag - 7s
        np.uint16(h),  # unsigned short height - H
        np.uint16(w),  # unsigned int width - H
        dtype_code,  # unsigned byte datatype - B
    )
    fileio.write(header)


def write_source_sample_data(fileio: FileIO, sample: SourceSample):
    h, w = sample.capture.shape[:2]
    tl = sample.roi.get("tl", (0, 0))
    br = sample.roi.get("br", (w, h))
    sub_header = struct.pack(
        SRC_HEADER_FORMAT,  # double timestamp + double frame_rate_fps + double temperature_c + double gain + double exposure_time_s + unsigned short roi.tl.x + unsigned short roi.tl.y + unsigned short roi.br.x + unsigned short roi.br.y
        np.float64(sample.last_access_time.timestamp()),  # double timestamp - d
        np.float64(sample.frame_rate_fps),  # double frame_rate_fps - d
        np.float64(sample.temperature_c),  # double temperature_c - d
        np.float64(sample.gain),  # double gain - d
        np.float64(sample.exposure_time_s),  # double exposure_time_s - d
        np.uint16(tl[0]),  # unsigned short roi.tl.x - H
        np.uint16(tl[1]),  # unsigned short roi.tl.y - H
        np.uint16(br[0]),  # unsigned short roi.br.x - H
        np.uint16(br[1]),  # unsigned short roi.br.y - H
    )
    fileio.write(sub_header + sample.capture.tobytes())


def read_source_samples(filename: str) -> list[SourceSample]:

    header_size = struct.calcsize(HEADER_FORMAT)
    src_header_size = struct.calcsize(SRC_HEADER_FORMAT)

    with open(filename, "rb") as fileio:
        # --- read header ---
        header_bytes = fileio.read(header_size)
        tag, h, w, dtype_code = struct.unpack(HEADER_FORMAT, header_bytes)
        if tag != SRC_TAG:
            raise ValueError(f"Invalid file header (tag mismatch) looking for {SRC_TAG.decode('utf-8')}, found {tag}")

        dtype = INV_DTYPE_MAP[dtype_code]
        capture_size = h * w * np.dtype(dtype).itemsize

        # --- read capture records ---
        sample_list = []
        while True:
            src_header_bytes = fileio.read(src_header_size)
            if len(src_header_bytes) < src_header_size:
                break  # EOF
            (timestamp, frame_rate_fps, temperature_c, gain, exposure_time_s, tl_x, tl_y, br_x, br_y) = struct.unpack(SRC_HEADER_FORMAT, src_header_bytes)  # double timestamp + double frame_rate_fps + double temperature_c + double gain + double exposure_time_s + unsigned short roi.tl.x + unsigned short roi.tl.y + unsigned short roi.br.x + unsigned short roi.br.y

            capture_bytes = fileio.read(capture_size)
            if len(capture_bytes) < capture_size:
                break  # incomplete capture

            capture = np.frombuffer(capture_bytes, dtype=dtype).reshape((h, w))
            timestamp = datetime.fromtimestamp(timestamp)

            sample_list.append(SourceSample(timestamp, exposure_time_s, gain, frame_rate_fps, temperature_c, {"tl": (tl_x, tl_y), "br": (br_x, br_y)}, capture))

        return sample_list


def write_sink_sample_header(fileio: FileIO, sample: SinkSample):
    h, w = sample.command.shape[:2]
    dtype_code = DTYPE_MAP[sample.command.dtype.type]
    header = struct.pack(
        HEADER_FORMAT,  # 7 char tag + unsigned short width + unsigned short height + unsigned byte datatype
        SNK_TAG,  # 7 char tag - 7s
        np.uint16(h),  # unsigned short height - H
        np.uint16(w),  # unsigned int width - H
        dtype_code,  # unsigned byte datatype - B
    )
    fileio.write(header)


def write_sink_sample_data(fileio: FileIO, sample: SinkSample):
    center = sample.center
    sub_header = struct.pack(
        SNK_HEADER_FORMAT,  # double timestamp + double frame_rate_fps + unsigned short radius + unsigned short center.x + unsigned short center.y
        np.float64(sample.last_access_time.timestamp()),  # double timestamp - d
        np.float64(sample.frame_rate_fps),  # double frame_rate_fps - d
        np.uint16(sample.radius),  # unsigned short radius - H
        np.uint16(center[0]),  # unsigned short center.x - H
        np.uint16(center[1]),  # unsigned short center.y - H
    )
    fileio.write(sub_header + sample.command.tobytes())


def read_sink_samples(filename: str) -> list[SinkSample]:

    header_size = struct.calcsize(HEADER_FORMAT)
    snk_header_size = struct.calcsize(SNK_HEADER_FORMAT)

    with open(filename, "rb") as fileio:
        # --- read header ---
        header_bytes = fileio.read(header_size)
        tag, h, w, dtype_code = struct.unpack(HEADER_FORMAT, header_bytes)
        if tag != SNK_TAG:
            raise ValueError(f"Invalid file header (tag mismatch) looking for {SNK_TAG.decode('utf-8')}, found {tag}")

        dtype = INV_DTYPE_MAP[dtype_code]
        command_size = h * w * np.dtype(dtype).itemsize

        # --- read command records ---
        sample_list = []
        while True:
            snk_header_bytes = fileio.read(snk_header_size)
            if len(snk_header_bytes) < snk_header_size:
                break  # EOF
            (timestamp, frame_rate_fps, radius, center_x, center_y) = struct.unpack(SNK_HEADER_FORMAT, snk_header_bytes)  # double timestamp + double frame_rate_fps + unsigned short radius + unsigned short center.x + unsigned short center.y

            command_bytes = fileio.read(command_size)
            if len(command_bytes) < command_size:
                break  # incomplete command

            command = np.frombuffer(command_bytes, dtype=dtype).reshape((h, w))
            timestamp = datetime.fromtimestamp(timestamp)

            sample_list.append(SinkSample(timestamp, frame_rate_fps, (center_x, center_y), radius, command))

    return sample_list


def find_speckles(speckle_image: np.ndarray, num_peaks: int = 1, footprint_size: int = 10, min_distance: int = 1) -> tuple[list[tuple[float, float]], np.ndarray]:
    peak_idx = peak_local_max(speckle_image, num_peaks=num_peaks, min_distance=min_distance, threshold_abs=None)
    assert len(peak_idx) == num_peaks, f"looking for {num_peaks} speckles, found {len(peak_idx)}"
    peak_mask = np.zeros_like(speckle_image, dtype=bool)
    peak_mask[tuple(peak_idx.T)] = True
    disk_mask = disk(footprint_size)
    peak_mask = dilation(peak_mask, disk_mask)
    label_image = label(peak_mask)
    speckles = regionprops(label_image, speckle_image)
    ind = np.lexsort(([speckle.centroid_weighted[0] for speckle in speckles], [speckle.centroid_weighted[1] for speckle in speckles]))
    return [(speckles[i].centroid_weighted[1], speckles[i].centroid_weighted[0]) for i in ind], peak_mask


def speckle_parameters(center: tuple[float, float], speckle_location_px: tuple[float, float], speck_calibration: dict[str, dict[str, float]]) -> tuple[float, float]:
    speckle_location_px_delta = np.array(speckle_location_px) - np.array(center)
    speckle_dist = np.hypot(speckle_location_px_delta[0], speckle_location_px_delta[1])
    speckle_angle = -np.arctan2(speckle_location_px_delta[0], speckle_location_px_delta[1])
    speckle_frequency = (speckle_dist - speck_calibration["speck_dist_cmd_freq"]["intercept"]) / speck_calibration["speck_dist_cmd_freq"]["slope"]
    speckle_angle = (speckle_angle - speck_calibration["speck_angle_cmd_angle"]["intercept"]) / speck_calibration["speck_angle_cmd_angle"]["slope"]
    return speckle_frequency, speckle_angle


def is_speckle_calibration_file_valid(filename: str) -> bool:
    with open(filename, "rb") as _input:
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


def read_speckle_calibration_file(filename: str) -> dict[str, str | np.ndarray]:
    with open(filename, "rb") as _input:
        return pickle.load(_input)


def is_camera_calibration_file_valid(filename: str, shape: tuple[int, int]) -> bool:
    with fits.open(filename) as hdul:
        if len(hdul[0].data) != 3:
            return False
        else:
            data_shape = (shape[1], shape[0])
            return (hdul[0].data[0].shape == data_shape) & (hdul[0].data[1].shape == data_shape) & (hdul[0].data[2].shape == data_shape)


def is_modulator_calibration_file_valid(filename: str, shape: tuple[int, int]) -> bool:
    with fits.open(filename) as hdul:
        if len(hdul[0].data) != 2:
            return False
        else:
            data_shape = (shape[1], shape[0])
            return (hdul[0].data[0].shape == data_shape) & (hdul[0].data[1].shape == data_shape)


def read_camera_calibration_file(filename: str) -> dict[str, np.ndarray]:
    with fits.open(filename) as hdul:
        dark_rate_data = hdul[0].data[0]
        bias_data = hdul[0].data[1]
        read_noise_data = hdul[0].data[2]
        return {"dark_rate": dark_rate_data, "bias": bias_data, "read_noise": read_noise_data}


def read_modulator_calibration_file(filename: str) -> dict[str, np.ndarray]:
    with fits.open(filename) as hdul:
        slope_data = hdul[0].data[0]
        flat_data = hdul[0].data[1]
        return {"slope": slope_data, "flat": flat_data}


def sin_fit_fn(x, amplitude: float, frequency: float, phase: float, offset: float):
    return amplitude * np.sin(frequency * x + phase) + offset


def constrained_sin_fit_fn(x, amplitude: float, phase: float, offset: float):
    return sin_fit_fn(x, amplitude, 1, phase, offset)


def quadratic_fit_fn(x, a: float, b: float, c: float):
    return a * x * x + b * x + c


def linear_fit_fn(x, m: float, c: float):
    return m * x + c


def write_camera_calibration_file(filename: str, dark_rate: np.ndarray, bias: np.ndarray, read_noise: np.ndarray):
    fits_dr_rn = np.stack([dark_rate, bias, read_noise], axis=0)
    fits_dr_rn_hdu = fits.PrimaryHDU(fits_dr_rn)
    fits_dr_rn_hdu.header["NFRAME"] = 3
    fits_dr_rn_hdu.header["FRAME0"] = "dark_rate"
    fits_dr_rn_hdu.header["FRAME1"] = "bias"
    fits_dr_rn_hdu.header["FRAME2"] = "read_noise"
    fits_dr_rn_hdu.writeto(filename, overwrite=True)


def write_modulator_calibration_file(filename: str, slope_nm_to_adu: np.ndarray, intercept_nm: np.ndarray):
    fits_dr_rn = np.stack([slope_nm_to_adu, intercept_nm], axis=0)
    fits_dr_rn_hdu = fits.PrimaryHDU(fits_dr_rn)
    fits_dr_rn_hdu.header["NFRAME"] = 2
    fits_dr_rn_hdu.header["FRAME0"] = "slope"
    fits_dr_rn_hdu.header["FRAME1"] = "flat"
    fits_dr_rn_hdu.writeto(filename, overwrite=True)


def apply_camera_calibration(capture: np.ndarray, exp_time_s: float, dark_rate: np.ndarray, bias: np.ndarray) -> np.ndarray:
    """
    Apply the camera calibration to the raw capture

    Parameters:
        capture: np.ndarray
            Raw capture in adu
        exp_time_s: float
            Exposure time in seconds
        dark_rate: np.ndarray
            dark rate
        bias: np.ndarray
            bias

    Returns: np.ndarray
        Image of count rate
    """
    return ((capture - bias) - dark_rate * exp_time_s) / exp_time_s


def apply_modulator_calibration(command: np.ndarray, slope: np.ndarray, flat: np.ndarray) -> np.ndarray:
    """
    Apply modulator calibration to command

    Parameters:
        command: np.ndarray
            Raw command in nm
        slope: np.ndarray
            conversion from nm to adu
        flat: np.ndarray (adu)
            flat command in adu.

    Returns: np.ndarray
        Command in adu
    """
    return command * slope - flat


class DOTFProbeDirection(IntEnum):
    RIGHT = 3
    BOTTOM = 6
    LEFT = 9
    TOP = 12

    def to_str(self) -> str:
        return f"{self.value:02d}"


def dotf_probe(shape: tuple[int, int], size: tuple[int, int], direction: DOTFProbeDirection) -> np.ndarray:
    """
    Create a DOTF probe pattern image.

    Example:
        image_dotf_probe = dotf_probe((200,200), (4,11), DOTFProbeDirection.TOP)

    Parameters:
        shape: tuple[int, int]
            Image shape.
        size: tuple[int, int]
            Size of the box.
        direction: DOTFProbeDirection
            direction of the probe.

    Returns: np.ndarray
        Image of the dotf probe pattern.
    """
    width, height = shape
    a, b = size
    if direction == DOTFProbeDirection.RIGHT:
        _center = (-width, -height // 2)
        _size = a, b
    elif direction == DOTFProbeDirection.BOTTOM:
        _center = (-width // 2, 0)
        _size = b, a
    elif direction == DOTFProbeDirection.LEFT:
        _center = (0, -height // 2)
        _size = a, b
    else:  # DOTFProbeDirection.TOP
        _center = (-width // 2, -height)
        _size = b, a
    return box(shape, _size, _center)


class PairwiseProbeDirection(Enum):
    HORIZONTAL = auto()
    VERTICAL = auto()

    def to_str(self) -> str:
        return self.name.lower()


def pairwise_probe(shape: tuple[int, int], dξ: float, dη: float, ξc: float, θ: float, direction: PairwiseProbeDirection) -> np.ndarray:
    """
    Create a pairwise probe pattern image.

    Example:
        image_pairwise_probe = pairwise_probe((200,200), 0.01, 0.01, 90, 0, PairwiseProbeDirection.HORIZONTAL)

    Parameters:
        shape: tuple[int, int]
            Image shape.
        dξ: float
            Probe rectangle size in (along the PairwiseProbeDirection).
        dη: float
            Probe rectangle size in (perpendicular to the PairwiseProbeDirection).
        ξc: float
            Period of the sinusoid (along the PairwiseProbeDirection).
        θ: float
            Phase of the sinusoid (along the PairwiseProbeDirection) in radians.

    Returns: np.ndarray
        Image of the pairwise probe pattern.
    """

    def _pairwise_probe(shape: tuple[int, int], dξ: float, dη: float, ξc: float, θ: float) -> np.ndarray:
        xx, yy = generate_coordinates(shape, cartesian=True, offset=(-shape[0] / 2 + 0.5, -shape[1] / 2 + 0.5))
        _2pi_xx = 2 * np.pi * xx
        _2pi_yy = 2 * np.pi * yy
        _invξc_2pi_xx = (1 / ξc) * _2pi_xx
        logger.info("_pairwise_probe θ = %s", θ)
        return (np.sinc(dξ * _2pi_xx) * np.sinc(dη * _2pi_yy) * np.sin(_invξc_2pi_xx + np.deg2rad(θ)) + 1) / 2

    if direction == PairwiseProbeDirection.HORIZONTAL:
        return _pairwise_probe(shape, dξ, dη, ξc, θ)
    else:
        return np.rot90(_pairwise_probe(shape, dξ, dη, ξc, θ))
