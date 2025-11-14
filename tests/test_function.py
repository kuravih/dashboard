import unittest
from testbed.function import read_source_samples, read_sink_samples
from pykato.log import setup_logger
from pykato.plotfunction.preset import Imshow_Preset

logger = setup_logger("test_read_functions", terminator="\n")


class TestFunction(unittest.TestCase):
    # pylint: disable=missing-class-docstring

    def test_read_source_samples(self):
        header, samples = read_source_samples("data/output/20251110.123116_source.raw")
        logger.info("header.magic            : %s", header["magic"])
        logger.info("header.w x h            : %d x %d", header["height"], header["width"])
        logger.info("header.exposure_time_us : %d", header["exposure_time_us"])
        logger.info("header.gain             : %f", header["gain"])
        logger.info("header.frame_rate_fps   : %f", header["frame_rate_fps"])
        logger.info("header.temperature_c    : %f", header["temperature_c"])
        logger.info("header.roi              : %s", header["roi"])
        logger.info("header.dtype            : %s", header["dtype"])

        imshow_preset = Imshow_Preset(samples[0]["capture"])
        imshow_preset.savefig("data/plot/20251110.123116_source.png")

    def test_read_sink_samples(self):
        header, samples = read_sink_samples("data/output/20251110.123116_sink.raw")
        logger.info("header.magic            : %s", header["magic"])
        logger.info("header.w x h            : %d x %d", header["height"], header["width"])
        logger.info("header.frame_rate_fps   : %f", header["frame_rate_fps"])
        logger.info("header.center           : %s", header["center"])
        logger.info("header.radius           : %f", header["radius"])
        logger.info("header.dtype            : %s", header["dtype"])

        imshow_preset = Imshow_Preset(samples[0]["command"])
        imshow_preset.savefig("data/plot/20251110.123116_sink.png")
