import numpy as np
import toml
from pykato.log import setup_logger
from pytestbed.function import capture_to_intensity

logger = setup_logger("function", terminator="\n")


def speckle_parameters(center: tuple[float, float], speckle_location_px: tuple[float, float], speck_calibration: dict[str, dict[str, float]]) -> tuple[float, float]:
    """Convert a speckle pixel position to calibrated frequency and angle.

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


def intensity_limits(limits: tuple[float, float] | tuple[int, int], exp_time_s: float, dark_rate: np.ndarray, bias: np.ndarray, qe: float, gain: float) -> tuple[float, float]:
    """Calculate the intensity limits.

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


def speckle_preset_validator(filepath: str) -> dict | None:
    try:
        with open(filepath, "r") as f:
            data = toml.load(f)
    except (OSError, toml.TomlDecodeError):
        return None
    try:
        amplitude = data["amplitude"]
        angle = data["angle"]
        frequency = data["frequency"]
        phase = data["phase"]
        _ = float(amplitude["perc"])
        _ = float(angle["start_deg"]), float(angle["stop_deg"]), int(angle["steps"])
        _ = float(frequency["start"]), float(frequency["stop"]), int(frequency["steps"])
        _ = float(phase["start_deg"]), float(phase["stop_deg"]), int(phase["steps"])
        _ = int(data["repetitions"])
    except (KeyError, TypeError, ValueError):
        return None
    return data
