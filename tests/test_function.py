import unittest
from testbed.function import read_source_samples, read_sink_samples
from pykato.log import setup_logger
from pykato.plotfunction.preset import Imshow_Preset

logger = setup_logger("test_read_functions", terminator="\n")


class TestFunction(unittest.TestCase):
    # pylint: disable=missing-class-docstring

    def test_read_source_samples(self):
        samples = read_source_samples("data/output/20251124.133154_capture_source.raw")
        logger.info("samples.exposure_time_us : %d", samples.exposure_time_us)
        logger.info("samples.gain             : %f", samples.gain)
        logger.info("samples.frame_rate_fps   : %f", samples.frame_rate_fps)
        logger.info("samples.temperature_c    : %f", samples.temperature_c)
        logger.info("samples.roi              : %s", samples.roi)
        imshow_preset = Imshow_Preset(samples.captures[0])
        imshow_preset.savefig("data/plot/20251110.123116_source.png")

    def test_read_sink_samples(self):
        samples = read_sink_samples("data/output/20251124.140308_command_sink_checker.raw")
        logger.info("samples.frame_rate_fps   : %f", samples.frame_rate_fps)
        logger.info("samples.center           : %s", samples.center)
        logger.info("samples.radius           : %f", samples.radius)
        imshow_preset = Imshow_Preset(samples.commands[0])
        imshow_preset.savefig("data/plot/20251124.140308_command_sink_checker.png")
