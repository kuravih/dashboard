import cloudpickle
from enum import Enum, IntEnum, auto
import struct
import numpy as np
from datetime import datetime

from numpy.typing import NDArray
from .device import SinkSample, SourceSample
from io import FileIO
from pykato.log import setup_logger
from pykato.function import box, generate_coordinates, invert_2x2_arrays

from scipy.interpolate import CubicSpline
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
        """
        Construct a Flip from a boolean value.

        Parameters:
            value: bool
                True maps to POS, False maps to NEG.

        Returns: Flip
            The corresponding Flip enum value.
        """
        return cls.POS if value else cls.NEG

    def to_bool(self) -> bool:
        """
        Convert the Flip to a boolean.

        Returns: bool
            True if POS, False if NEG.
        """
        return self is Flip.POS


class Rotation(Enum):
    UP = auto()
    LEFT = auto()
    DOWN = auto()
    RIGHT = auto()

    @classmethod
    def from_int(cls, i: int) -> "Rotation":
        """
        Construct a Rotation from an integer.

        Parameters:
            i: int
                Rotation index: 0=UP, 1=LEFT, 2=DOWN, 3=RIGHT.

        Returns: Rotation
            The corresponding Rotation enum value.
        """
        return {0: cls.UP, 1: cls.LEFT, 2: cls.DOWN, 3: cls.RIGHT}[i]

    def to_int(self):
        """
        Convert the Rotation to an integer.

        Returns: int
            0 for UP, 1 for LEFT, 2 for DOWN, 3 for RIGHT.
        """
        return {Rotation.UP: 0, Rotation.LEFT: 1, Rotation.DOWN: 2, Rotation.RIGHT: 3}[self]


def flip_rotate_frame(frame: np.ndarray, flip: Flip, rotation: Rotation) -> np.ndarray:
    """
    Apply rotation then horizontal flip to a frame array.
    Parameters:
        frame: np.ndarray
            Input frame
        flip: Flip
            Flip
        rotation: Rotation
            Rotation

    Returns: np.ndarray
        Rotated flipped frame
    """
    frame = np.rot90(frame, rotation.to_int())
    if flip == Flip.NEG:
        frame = np.fliplr(frame)
    return frame


def flip_rotate_points(xs: np.ndarray, ys: np.ndarray, image_shape: tuple[int, int], flip: Flip, rotation: Rotation) -> tuple[np.ndarray, np.ndarray]:
    """
    Transform point coordinates to match a flip and rotation applied to an image.
    Parameters:
        xs: np.ndarray
            x coordinates
        ys: np.ndarray
            y coordinates
        image_shape: tuple[int, int]
            Image shape
        flip: Flip
            Flip
        rotation: Rotation
            Rotation

    Returns: tuple[np.ndarray, np.ndarray]
        Rotated flipped x coordinates, Rotated flipped y coordinates
    """
    height, width = image_shape

    if rotation == Rotation.UP:  # UP
        xs_new, ys_new = xs, ys
        height_new, width_new = height, width
    elif rotation == Rotation.LEFT:  # LEFT (90° CCW)
        xs_new, ys_new = width - 1 - ys, xs
        height_new, width_new = width, height
    elif rotation == Rotation.DOWN:  # DOWN (180°)
        xs_new, ys_new = height - 1 - xs, width - 1 - ys
        height_new, width_new = height, width
    elif rotation == Rotation.RIGHT:  # RIGHT (270° CCW)
        xs_new, ys_new = ys, height - 1 - xs
        height_new, width_new = width, height

    if flip == Flip.NEG:
        ys_new = width_new - 1 - ys_new

    return xs_new, ys_new


def write_source_sample_header(fileio: FileIO, sample: SourceSample):
    """
    Write the binary file header (tag, shape, dtype) for a source sample recording.

    Parameters:
        fileio: FileIO
            Open binary file to write to.
        sample: SourceSample
            Source sample whose capture shape and dtype define the header.
    """
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
    """
    Append source sample metadata and raw capture bytes to a binary file.

    Parameters:
        fileio: FileIO
            Open binary file to write to.
        sample: SourceSample
            Source sample to serialize.
    """
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
    """
    Read and return all source samples from a binary recording file.

    Parameters:
        filename: str
            Path to the binary source sample file.

    Returns: list[SourceSample]
        List of source samples in file order.
    """
    header_size = struct.calcsize(HEADER_FORMAT)
    src_header_size = struct.calcsize(SRC_HEADER_FORMAT)

    with open(filename, "rb") as rbfile:
        # --- read header ---
        header_bytes = rbfile.read(header_size)
        tag, h, w, dtype_code = struct.unpack(HEADER_FORMAT, header_bytes)
        if tag != SRC_TAG:
            raise ValueError(f"Invalid file header (tag mismatch) looking for {SRC_TAG.decode('utf-8')}, found {tag}")

        dtype = INV_DTYPE_MAP[dtype_code]
        capture_size = h * w * np.dtype(dtype).itemsize

        # --- read capture records ---
        sample_list = []
        while True:
            src_header_bytes = rbfile.read(src_header_size)
            if len(src_header_bytes) < src_header_size:
                break  # EOF
            (timestamp, frame_rate_fps, temperature_c, gain, exposure_time_s, tl_x, tl_y, br_x, br_y) = struct.unpack(SRC_HEADER_FORMAT, src_header_bytes)  # double timestamp + double frame_rate_fps + double temperature_c + double gain + double exposure_time_s + unsigned short roi.tl.x + unsigned short roi.tl.y + unsigned short roi.br.x + unsigned short roi.br.y

            capture_bytes = rbfile.read(capture_size)
            if len(capture_bytes) < capture_size:
                break  # incomplete capture

            capture = np.frombuffer(capture_bytes, dtype=dtype).reshape((h, w))
            timestamp = datetime.fromtimestamp(timestamp)

            sample_list.append(SourceSample(timestamp, exposure_time_s, gain, frame_rate_fps, temperature_c, {"tl": (tl_x, tl_y), "br": (br_x, br_y)}, capture))

        return sample_list


def write_sink_sample_header(fileio: FileIO, sample: SinkSample):
    """
    Write the binary file header (tag, shape, dtype) for a sink sample recording.

    Parameters:
        fileio: FileIO
            Open binary file to write to.
        sample: SinkSample
            Sink sample whose command shape and dtype define the header.
    """
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
    """
    Append sink sample metadata and raw command bytes to a binary file.

    Parameters:
        fileio: FileIO
            Open binary file to write to.
        sample: SinkSample
            Sink sample to serialize.
    """
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
    """
    Read and return all sink samples from a binary recording file.

    Parameters:
        filename: str
            Path to the binary sink sample file.

    Returns: list[SinkSample]
        List of sink samples in file order.
    """
    header_size = struct.calcsize(HEADER_FORMAT)
    snk_header_size = struct.calcsize(SNK_HEADER_FORMAT)

    with open(filename, "rb") as rbfile:
        # --- read header ---
        header_bytes = rbfile.read(header_size)
        tag, h, w, dtype_code = struct.unpack(HEADER_FORMAT, header_bytes)
        if tag != SNK_TAG:
            raise ValueError(f"Invalid file header (tag mismatch) looking for {SNK_TAG.decode('utf-8')}, found {tag}")

        dtype = INV_DTYPE_MAP[dtype_code]
        command_size = h * w * np.dtype(dtype).itemsize

        # --- read command records ---
        sample_list = []
        while True:
            snk_header_bytes = rbfile.read(snk_header_size)
            if len(snk_header_bytes) < snk_header_size:
                break  # EOF
            (timestamp, frame_rate_fps, radius, center_x, center_y) = struct.unpack(SNK_HEADER_FORMAT, snk_header_bytes)  # double timestamp + double frame_rate_fps + unsigned short radius + unsigned short center.x + unsigned short center.y

            command_bytes = rbfile.read(command_size)
            if len(command_bytes) < command_size:
                break  # incomplete command

            command = np.frombuffer(command_bytes, dtype=dtype).reshape((h, w))
            timestamp = datetime.fromtimestamp(timestamp)

            sample_list.append(SinkSample(timestamp, frame_rate_fps, (center_x, center_y), radius, command))

    return sample_list


def find_speckles(speckle_image: np.ndarray, num_peaks: int = 1, footprint_size: int = 10, min_distance: int = 1) -> tuple[list[tuple[float, float]], np.ndarray]:
    """
    Locate speckle peaks and return their weighted centroids sorted by x and the dilated peak mask.

    Parameters:
        speckle_image: np.ndarray
            2D intensity image to search for speckle peaks.
        num_peaks: int
            Number of speckle peaks to find.
        footprint_size: int
            Radius of the disk used to dilate each peak into a region.
        min_distance: int
            Minimum pixel separation between detected peaks.

    Returns: tuple[list[tuple[float, float]], np.ndarray]
        Weighted centroids as (x, y) pairs sorted by x, and the boolean peak mask.
    """
    peak_idx = []
    threshold_rel = 1.0
    while len(peak_idx) < num_peaks:
        peak_idx = peak_local_max(speckle_image, num_peaks=num_peaks, min_distance=min_distance, threshold_rel=threshold_rel, threshold_abs=None, exclude_border=20)
        threshold_rel = threshold_rel / 2
        if threshold_rel < 0.0625:
            break
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
    """
    Convert a speckle pixel position to calibrated frequency and angle.

    Parameters:
        center: tuple[float, float]
            Reference center pixel (x, y).
        speckle_location_px: tuple[float, float]
            Detected speckle centroid in pixels (x, y).
        speck_calibration: dict[str, dict[str, float]]
            Calibration dict with speck_dist_cmd_freq and speck_angle_cmd_angle slope/intercept entries.

    Returns: tuple[float, float]
        Calibrated speckle frequency and angle in radians.
    """
    speckle_location_px_delta = np.array(speckle_location_px) - np.array(center)
    speckle_dist = np.hypot(speckle_location_px_delta[0], speckle_location_px_delta[1])
    speckle_angle_rad = -np.arctan2(speckle_location_px_delta[0], speckle_location_px_delta[1])
    speckle_frequency = (speckle_dist - speck_calibration["speck_dist_cmd_freq"]["intercept"]) / speck_calibration["speck_dist_cmd_freq"]["slope"]
    speckle_angle_rad = (speckle_angle_rad - speck_calibration["speck_angle_cmd_angle"]["intercept"]) / speck_calibration["speck_angle_cmd_angle"]["slope"]
    return speckle_frequency, speckle_angle_rad


def is_speckle_calibration_file_valid(filename: str) -> bool:
    """
    Return True if the speckle calibration pickle file contains the required slope/intercept keys.

    Parameters:
        filename: str
            Path to the speckle calibration pickle file.

    Returns: bool
        True if valid, False otherwise.
    """
    with open(filename, "rb") as rbfile:
        d = cloudpickle.load(rbfile)

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


def read_speckle_calibration_file(filename: str) -> dict[str, dict[str, float]]:
    """
    Load and return the speckle calibration dict from a pickle file.

    Parameters:
        filename: str
            Path to the speckle calibration pickle file.

    Returns: dict[str, dict[str, float]]
        Calibration dict with speck_dist_cmd_freq and speck_angle_cmd_angle entries.
    """
    with open(filename, "rb") as rbfile:
        return cloudpickle.load(rbfile)


def write_speckle_calibration_file(speckle_calibration_dict: dict[str, dict[str, float]], filename: str):
    """
    Serialize the speckle calibration dict to a pickle file.

    Parameters:
        speckle_calibration_dict: dict[str, dict[str, float]]
            Calibration dict to save.
        filename: str
            Destination file path.
    """
    with open(filename, "wb") as wbfile:
        cloudpickle.dump(speckle_calibration_dict, wbfile)


def is_camera_calibration_file_valid(filename: str, shape: tuple[int, int]) -> bool:
    """
    Return True if the camera calibration FITS file contains 3 image frames, a QE table, full well capacity,
    and bit depth, all matching the expected shape.

    Parameters:
        filename: str
            Path to the camera calibration FITS file.
        shape: tuple[int, int]
            Expected (width, height) of each calibration frame.

    Returns: bool
        True if valid, False otherwise.
    """
    with fits.open(filename) as hdul:
        if len(hdul[0].data) != 3:
            return False
        if not ((hdul[0].data[0].shape == shape) & (hdul[0].data[1].shape == shape) & (hdul[0].data[2].shape == shape)):
            return False
        if "QE" not in hdul:
            logger.info('"QE" not in hdul')
            return False
        qe_names = hdul["QE"].data.names
        if "wavelength_nm" not in qe_names or "quantum_efficiency" not in qe_names:
            logger.info('"wavelength_nm" not in qe_names or "quantum_efficiency" not in qe_names')
            return False
        if "FULLWELL" not in hdul[0].header or "BITDEPTH" not in hdul[0].header or "GAIN" not in hdul[0].header:
            logger.info('"FULLWELL" not in hdul[0].header or "BITDEPTH" not in hdul[0].header')
            return False
        return True


def read_camera_calibration_file(filename: str, roi: dict[str, tuple[int, int]] | None = None) -> dict:
    """
    Load dark_rate, bias, read_noise, quantum_efficiency, full_well_capacity, and bit_depth from a camera calibration FITS file.

    Parameters:
        filename: str
            Path to the camera calibration FITS file.

    Returns: dict
        Dict with keys:
            dark_rate: np.ndarray
                per-pixel dark current rate (ADU/s).
            bias: np.ndarray
                per-pixel bias frame (ADU).
            read_noise: np.ndarray
                per-pixel read noise (ADU).
            quantum_efficiency: np.
                shape (2, N): row 0 = wavelength (nm), row 1 = QE fraction.
            full_well_capacity: float
                full well capacity (electrons).
            bit_depth: int
                ADC bit depth.
    """
    with fits.open(filename) as hdul:
        dark_rate_data = hdul[0].data[0]
        bias_data = hdul[0].data[1]
        read_noise_data = hdul[0].data[2]
        gain = hdul[0].header["GAIN"]
        full_well_capacity = hdul[0].header["FULLWELL"]
        bit_depth = hdul[0].header["BITDEPTH"]
        qe_data = hdul["QE"].data
        λ_m_qe_perc_data = np.stack([qe_data["wavelength_nm"], qe_data["quantum_efficiency"]])
        if roi is None:
            roi = {"br": (None, None), "tl": (None, None)}
        return {"dark_rate": dark_rate_data[roi["tl"][1] : roi["br"][1], roi["tl"][0] : roi["br"][0]], "bias": bias_data[roi["tl"][1] : roi["br"][1], roi["tl"][0] : roi["br"][0]], "read_noise": read_noise_data[roi["tl"][1] : roi["br"][1], roi["tl"][0] : roi["br"][0]], "quantum_efficiency": λ_m_qe_perc_data, "gain": gain, "full_well_capacity": full_well_capacity, "bit_depth": bit_depth}


def write_camera_calibration_file(filename: str, dark_rate: np.ndarray, bias: np.ndarray, read_noise: np.ndarray, λ_m_qe_perc_data: tuple[np.ndarray, np.ndarray], gain: float, full_well_capacity: float, bit_depth: int):
    """
    Write dark_rate, bias, read_noise, and quantum_efficiency arrays to a camera calibration FITS file.

    Parameters:
        filename: str
            Destination file path.
        dark_rate: np.ndarray
            Dark current rate frame.
        bias: np.ndarray
            Bias frame.
        read_noise: np.ndarray
            Read noise frame.
        quantum_efficiency: np.ndarray
            QE table with shape (2, N): row 0 = wavelength in nm, row 1 = QE fraction.
        gain: float
            Electron count to adu conversion gain (ADU/e)
        full_well_capacity: float
            Maximum number of electrons a pixel can hold before saturation (electrons).
        bit_depth: int
            ADC bit depth, determining the number of discrete ADU levels (2**bit_depth levels).
    """
    fits_calibration = np.stack([dark_rate, bias, read_noise], axis=0)
    fits_calibration_hdu = fits.PrimaryHDU(fits_calibration)
    fits_calibration_hdu.header["FULLWELL"] = (full_well_capacity, "Full well capacity (electrons)")
    fits_calibration_hdu.header["BITDEPTH"] = (bit_depth, "ADC bit depth")
    fits_calibration_hdu.header["GAIN"] = (gain, "Conversion gain (ADU/e)")
    fits_calibration_hdu.header["NFRAME"] = 3
    fits_calibration_hdu.header["FRAME0"] = "dark_rate"
    fits_calibration_hdu.header["FRAME1"] = "bias"
    fits_calibration_hdu.header["FRAME2"] = "read_noise"
    qe_hdu = fits.BinTableHDU.from_columns(
        [
            fits.Column(name="wavelength_nm", format="D", array=λ_m_qe_perc_data[0]),
            fits.Column(name="quantum_efficiency", format="D", array=λ_m_qe_perc_data[1]),
        ],
        name="QE",
    )
    fits.HDUList([fits_calibration_hdu, qe_hdu]).writeto(filename, overwrite=True)


def read_quantum_efficiency_file(filename: str) -> tuple[np.ndarray, np.ndarray]:
    """
    Read quantum efficiency data from a 2-column CSV file.

    The file must have a single header row followed by rows of
    (wavelength_nm, quantum_efficiency) values.

    Parameters:
        filename: str
            Path to the CSV file.

    Returns: tuple[np.ndarray, np.ndarray]
        wavelength and quantum efficiency arrays
    """
    data = np.loadtxt(filename, delimiter=",", skiprows=1)
    return data[:, 0], data[:, 1]


def calculate_quantum_efficiency(λ: float | np.ndarray, λs: np.ndarray, qes: np.ndarray) -> float | np.ndarray:
    """
    Interpolate quantum efficiency at a given wavelength.

    Parameters:
        λ: float
            Query wavelength.
        λs: np.ndarray
            Wavelength sample points (must be monotonically increasing).
        qes: np.ndarray
            Quantum efficiency values corresponding to λs.

    Returns: float
        Interpolated quantum efficiency at λ.
    """
    cs = CubicSpline(λs, qes)
    return cs(λ)


def is_modulator_calibration_file_valid(filename: str, shape: tuple[int, int]) -> bool:
    """
    Return True if the modulator calibration FITS file contains 2 frames matching the expected shape.

    Parameters:
        filename: str
            Path to the modulator calibration FITS file.
        shape: tuple[int, int]
            Expected (width, height) of each calibration frame.

    Returns: bool
        True if valid, False otherwise.
    """
    with fits.open(filename) as hdul:
        if len(hdul[0].data) != 2:
            return False
        else:
            data_shape = (shape[1], shape[0])
            return (hdul[0].data[0].shape == data_shape) & (hdul[0].data[1].shape == data_shape)


def read_modulator_calibration_file(filename: str) -> dict[str, np.ndarray]:
    """
    Load slope and flat arrays from a modulator calibration FITS file.

    Parameters:
        filename: str
            Path to the modulator calibration FITS file.

    Returns: dict[str, np.ndarray]
        Dict with keys slope and flat.
    """
    with fits.open(filename) as hdul:
        slope_data = hdul[0].data[0]
        flat_data = hdul[0].data[1]
        return {"slope": slope_data, "flat": flat_data}


def write_modulator_calibration_file(filename: str, slope_nm_to_adu: np.ndarray, intercept_nm: np.ndarray):
    """
    Write slope and flat calibration arrays to a modulator calibration FITS file.

    Parameters:
        filename: str
            Destination file path.
        slope_nm_to_adu: np.ndarray
            Pixel-wise slope converting nm deflection to ADU.
        intercept_nm: np.ndarray
            Pixel-wise flat command in ADU.
    """
    fits_calibration = np.stack([slope_nm_to_adu, intercept_nm], axis=0)
    fits_calibration_hdu = fits.PrimaryHDU(fits_calibration)
    fits_calibration_hdu.header["NFRAME"] = 2
    fits_calibration_hdu.header["FRAME0"] = "slope"
    fits_calibration_hdu.header["FRAME1"] = "flat"
    fits_calibration_hdu.writeto(filename, overwrite=True)


def sin_fit_fn(x, amplitude: float, frequency: float, phase: float, offset: float):
    """
    Evaluate amplitude * sin(frequency * x + phase) + offset.

    Parameters:
        x:
            Input variable.
        amplitude: float
            Amplitude of the sinusoid.
        frequency: float
            Angular frequency.
        phase: float
            Phase offset in radians.
        offset: float
            Vertical offset.

    Returns: float | np.ndarray
        Evaluated sinusoid.
    """
    return amplitude * np.sin(frequency * x + phase) + offset


def constrained_sin_fit_fn(x, amplitude: float, phase: float, offset: float):
    """
    Evaluate a unit-frequency sinusoid: amplitude * sin(x + phase) + offset.

    Parameters:
        x:
            Input variable.
        amplitude: float
            Amplitude of the sinusoid.
        phase: float
            Phase offset in radians.
        offset: float
            Vertical offset.

    Returns: float | np.ndarray
        Evaluated sinusoid.
    """
    return sin_fit_fn(x, amplitude, 1, phase, offset)


def quadratic_fit_fn(x, a: float, x0: float, c: float):
    """
    Evaluate a vertex-form quadratic: a * (x - x0)^2 + c.

    Parameters:
        x:
            Input variable.
        a: float
            Curvature coefficient.
        x0: float
            Vertex location.
        c: float
            Vertex value.

    Returns: float | np.ndarray
        Evaluated quadratic.
    """
    return a * (x - x0) ** 2 + c


# def quadratic_fit_fn(x, a: float, b: float, c: float):
#     return a * x * x + b * x + c


def linear_fit_fn(x, m: float, c: float):
    """
    Evaluate a linear function: m * x + c.

    Parameters:
        x:
            Input variable.
        m: float
            Slope.
        c: float
            Intercept.

    Returns: float | np.ndarray
        Evaluated linear function.
    """
    return m * x + c


def deflection_to_command(deflection_m: np.ndarray, slope_adu_per_m: np.ndarray, flat_adu: np.ndarray) -> np.ndarray:
    """
    Parameters:
        deflection_m: np.ndarray
            Deflection (m)
        slope_adu_per_m: np.ndarray
            conversion from m to adu (adu/m)
        flat_adu: np.ndarray
            flat command in (adu)

    Returns: np.ndarray
        Command (adu)
    """
    return deflection_m * slope_adu_per_m + flat_adu


def command_to_deflection(command_adu: np.ndarray, slope_adu_per_m: np.ndarray, flat_adu: np.ndarray) -> np.ndarray:
    """
    Parameters:
        command: np.ndarray
            Command (adu)
        slope_adu_per_m: np.ndarray
            conversion from m to adu (adu/m)
        flat_adu: np.ndarray
            flat command in (adu)

    Returns: np.ndarray
        Deflection (m)
    """
    return (command_adu - flat_adu) / slope_adu_per_m


def intensity_limits(limits: tuple[float, float] | tuple[int, int], exp_time_s: float, dark_rate: np.ndarray, bias: np.ndarray, qe: float, gain: float) -> tuple[float, float]:
    """
    Parameters:
        limits: tuple[float, float]
            min max limits
        exp_time_s: float
            Exposure time in seconds
        dark_rate: np.ndarray
            dark rate
        bias: np.ndarray
            bias

    Returns: tuple[float, float]
        min max limits
    """
    return np.min(capture_to_intensity(limits[0], exp_time_s, dark_rate, bias, qe, gain)), np.max(capture_to_intensity(limits[1], exp_time_s, dark_rate, bias, qe, gain))


def capture_to_intensity(capture: np.ndarray | float | int, exp_time_s: float, dark_rate: np.ndarray, bias: np.ndarray, qe: float, gain: float) -> np.ndarray:
    """
    Inverse of intensity_to_capture (noise-free, ignoring clipping and quantization).

    Parameters:
        capture: np.ndarray
            Raw capture in adu
        exp_time_s: float
            Exposure time in seconds
        dark_rate: np.ndarray
            Dark current rate in adu/s
        bias: np.ndarray
            Bias in adu
        qe: float
            Quantum efficiency (0-1)
        gain: float
            Electron count to adu conversion gain (ADU/e)

    Returns: np.ndarray
        Intensity in photons/s
    """
    return ((capture - bias) - dark_rate * exp_time_s) / (gain * qe * exp_time_s)


def intensity_to_capture(intensity: np.ndarray, exp_time_s: float, dark_rate: np.ndarray, bias: np.ndarray, qe: float, gain:float, full_well_capacity: float, bit_depth: int, read_noise: float | np.ndarray) -> np.ndarray:
    """
    Parameters:
        intensity: np.ndarray
            Intensity in photons/s
        exp_time_s: float
            Exposure time in seconds
        dark_rate: np.ndarray
            Dark current rate in adu/s
        bias: np.ndarray
            Bias in adu
        qe: float
            Quantum efficiency (%)
        gain: float
            Electron count to adu conversion gain (ADU/e)
        full_well_capacity: float
            Full well capacity in e
        bit_depth: int
            Bit depth for digitization
        read_noise: float or np.ndarray
            RMS read noise in adu. Default: 0.

    Returns: np.ndarray
        Capture in adu
    """

    dark_rate_e = dark_rate * gain
    bias_e = bias * gain
    read_noise_e = read_noise * gain

    # Signal accumulation in electrons
    signal_e = intensity * qe * exp_time_s

    # Photon shot noise (Poisson, applied in electron space)
    signal_e = np.random.poisson(np.maximum(signal_e, 0)).astype(float)

    # Read noise (Gaussian, in electrons)
    signal_e += np.random.normal(loc=0, scale=read_noise_e)

    # Add dark current and bias in electron counts
    accumulated_e = signal_e + dark_rate_e * exp_time_s + bias_e

    # Clip to full well capacity
    accumulated_e = np.clip(accumulated_e, 0, full_well_capacity)

    # Convert to edu
    accumulated_adu = accumulated_e * gain

    adu_max = 2**bit_depth - 1
    # Clip to adu_max
    return np.clip(np.round(accumulated_adu), 0, adu_max)


class DOTFProbeDirection(IntEnum):
    RIGHT = 3
    BOTTOM = 6
    LEFT = 9
    TOP = 12

    def to_str(self) -> str:
        """
        Return the zero-padded string representation of the direction value.

        Returns: str
            Two-character zero-padded integer string, e.g. "03", "06", "09", "12".
        """
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
        """
        Return the lowercase string name of the direction.

        Returns: str
            "horizontal" or "vertical".
        """
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
            Probe rectangle size (along the PairwiseProbeDirection).
        dη: float
            Probe rectangle size (perpendicular to the PairwiseProbeDirection).
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
        return np.sinc(dξ * _2pi_xx) * np.sinc(dη * _2pi_yy) * np.sin(_invξc_2pi_xx + θ)

    if direction == PairwiseProbeDirection.HORIZONTAL:
        return _pairwise_probe(shape, dξ, dη, ξc, θ)
    else:
        return np.rot90(_pairwise_probe(shape, dξ, dη, ξc, θ))


def pairwise_estimation_matrices(Δp_1: NDArray[np.complex64], Δp_2: NDArray[np.complex64]) -> tuple[float | np.ndarray, float | np.ndarray, float | np.ndarray, float | np.ndarray]:
    """
    Compute the inversion matrices for pairwise wavefront estimation from two complex probe fields.

    Parameters:
        Δp_1: NDArray[np.complex64]
            Complex probe field for probe pair 1.
        Δp_2: NDArray[np.complex64]
            Complex probe field for probe pair 2.

    Returns: tuple[NDArray, NDArray, NDArray, NDArray]
        Inversion matrix elements (p, q, r, s).
    """
    return invert_2x2_arrays(-2 * np.imag(Δp_1), 2 * np.real(Δp_1), -2 * np.imag(Δp_2), 2 * np.real(Δp_2))


def pairwise_estimate(intensity_p1: NDArray[np.float64], intensity_m1: NDArray[np.float64], intensity_p2: NDArray[np.float64], intensity_m2: NDArray[np.float64], pqrs: tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]) -> NDArray[np.complex64]:
    """
    Estimate the complex electric field from pairwise intensity differences using the inversion matrices.

    Parameters:
        intensity_p1: NDArray[np.float64]
            Positive-probe intensity for pair 1.
        intensity_m1: NDArray[np.float64]
            Negative-probe intensity for pair 1.
        intensity_p2: NDArray[np.float64]
            Positive-probe intensity for pair 2.
        intensity_m2: NDArray[np.float64]
            Negative-probe intensity for pair 2.
        pqrs: tuple[NDArray, NDArray, NDArray, NDArray]
            Inversion matrix elements (p, q, r, s) from pairwise_estimation_matrices.

    Returns: NDArray[np.complex64]
        Estimated complex electric field.
    """
    p, q, r, s = pqrs
    δ1 = (intensity_p1 - intensity_m1) / 2
    δ2 = (intensity_p2 - intensity_m2) / 2
    re_field = p * δ1 + q * δ2
    im_field = r * δ1 + s * δ2
    return re_field + 1j * im_field


def pairwise_estimation_matrices_2(φ_1: NDArray[np.complex64], φ_2: NDArray[np.complex64]) -> tuple[float | np.ndarray, float | np.ndarray, float | np.ndarray, float | np.ndarray]:
    """
    Compute the inversion matrices for pairwise estimation using the imaginary-probe formulation.

    Parameters:
        φ_1: NDArray[np.complex64]
            Complex probe field for pair 1.
        φ_2: NDArray[np.complex64]
            Complex probe field for pair 2.

    Returns: tuple[NDArray, NDArray, NDArray, NDArray]
        Inversion matrix elements (p, q, r, s).
    """
    return invert_2x2_arrays(4 * np.real(1j * φ_1), 4 * np.imag(1j * φ_1), 4 * np.real(1j * φ_2), 4 * np.imag(1j * φ_2))


def pairwise_estimate_2(intensity_p1: NDArray[np.float64], intensity_m1: NDArray[np.float64], intensity_p2: NDArray[np.float64], intensity_m2: NDArray[np.float64], pqrs: tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]) -> NDArray[np.complex64]:
    """
    Estimate the complex electric field using the imaginary-probe pairwise formulation.

    Parameters:
        intensity_p1: NDArray[np.float64]
            Positive-probe intensity for pair 1.
        intensity_m1: NDArray[np.float64]
            Negative-probe intensity for pair 1.
        intensity_p2: NDArray[np.float64]
            Positive-probe intensity for pair 2.
        intensity_m2: NDArray[np.float64]
            Negative-probe intensity for pair 2.
        pqrs: tuple[NDArray, NDArray, NDArray, NDArray]
            Inversion matrix elements (p, q, r, s) from pairwise_estimation_matrices_2.

    Returns: NDArray[np.complex64]
        Estimated complex electric field.
    """
    p, q, r, s = pqrs
    δ1 = intensity_p1 - intensity_m1
    δ2 = intensity_p2 - intensity_m2
    re_field = p * δ1 + q * δ2
    im_field = r * δ1 + s * δ2
    return re_field + 1j * im_field


def is_pairwise_calibration_file_valid(filename: str) -> bool:
    """
    Return True if the pairwise calibration pickle file contains entries for both probes 1 and 2.

    Parameters:
        filename: str
            Path to the pairwise calibration pickle file.

    Returns: bool
        True if valid, False otherwise.
    """
    with open(filename, "rb") as rbfile:
        calibration, amplitude_m, ξc, dξ, dη = cloudpickle.load(rbfile)
    if 1 not in calibration:
        return False
    if 2 not in calibration:
        return False
    return True


def read_pairwise_calibration_file(filename: str) -> tuple[dict[int, NDArray[np.float64 | np.complex64]], float, float, float, float]:
    """
    Load and return pairwise calibration data from a pickle file.

    Parameters:
        filename: str
            Path to the pairwise calibration pickle file.

    Returns: tuple[dict[int, NDArray], float, float, float, float]
        Calibration dict keyed by probe index, amplitude_m, ξc, dξ, dη.
    """
    with open(filename, "rb") as rbfile:
        return cloudpickle.load(rbfile)


def write_pairwise_calibration_file(pairwise_calibration_dict: tuple[dict[int, NDArray[np.float64 | np.complex64]], float, float, float, float], filename: str):
    """
    Serialize pairwise calibration data to a pickle file.

    Parameters:
        pairwise_calibration_dict: tuple[dict[int, NDArray], float, float, float, float]
            Calibration data (probe dict, amplitude_m, ξc, dξ, dη).
        filename: str
            Destination file path.
    """
    with open(filename, "wb") as wbfile:
        cloudpickle.dump(pairwise_calibration_dict, wbfile)
