import unittest
import numpy as np
from testbed.device import Stream
from testbed.device.camera import Camera
from testbed.device.modulator import Modulator
from pykato.log import setup_logger
from pykato.function import preroll
import time

logger = setup_logger("test_device", terminator="\n")


class TestDevice(unittest.TestCase):
    # pylint: disable=missing-class-docstring

    # ---- source -----------------------------------------------------------------------------------------------------
    def test_source_Stream(self):
        shm_name = "stb001_stbsource"
        stream = Stream(shm_name)
        # Properties common to all streams
        logger.info("stream.name                      : %s", stream.name)
        logger.info("stream.kind                      : %s", stream.kind)
        logger.info("stream.sn                        : %s", stream.sn)
        logger.info("stream.pxmax                     : %s", stream.pxmax)
        logger.info("stream.full_shape                : %s", stream.full_shape)
        logger.info("stream.port                      : %s", stream.port)
        logger.info("stream.metadata.creation_time    : %s", stream.creation_time)
        logger.info("stream.metadata.last_access_time : %s", stream.last_access_time)
        for ikey, key in enumerate(stream.keywords):
            logger.info("keyword %02d = keywords[%8s]  : {{.value = %s,.type = %s,.comment = %s}}", ikey, key, stream.keywords[key].value, stream.keywords[key].type, stream.keywords[key].comment)

    # ---- stbsource --------------------------------------------------------------------------------------------------
    def test_stbsource(self):
        camera = Camera(Stream("stb001_stbsource"))
        # Properties common to all streams
        logger.info("camera.name                      : %s", camera.name)
        logger.info("camera.kind                      : %s", camera.kind)
        logger.info("camera.sn                        : %s", camera.sn)
        logger.info("camera.pxmax                     : %s", camera.pxmax)
        logger.info("camera.full_shape                : %s", camera.full_shape)
        logger.info("camera.port                      : %s", camera.port)
        logger.info("camera.metadata.creation_time    : %s", camera.creation_time)
        logger.info("camera.metadata.last_access_time : %s", camera.last_access_time)
        # Properties specific to camera streams
        logger.info("camera.exposure_time_us          : %s", camera.exposure_time_us)
        logger.info("camera.gain                      : %s", camera.gain)
        logger.info("camera.temperature_c             : %s", camera.temperature_c)
        logger.info("camera.roi                       : %s", camera.roi)
        logger.info("camera.shape                     : %s", camera.shape)
        logger.info("camera.frame_rate_fps            : %s", camera.frame_rate_fps)

    def test_stbsource_capture(self):
        # ./stbsource must be running
        camera = Camera(Stream("stb001_stbsource"))
        for i in range(100):
            logger.info("frame : %s", i)
            print(camera.pull_capture())
            time.sleep(0.01)

    # ---- sink -------------------------------------------------------------------------------------------------------
    def test_sink_Stream(self):
        shm_name = "stb001_stbsink"
        stream = Stream(shm_name)
        # Properties common to all streams
        logger.info("stream.name                      : %s", stream.name)
        logger.info("stream.kind                      : %s", stream.kind)
        logger.info("stream.sn                        : %s", stream.sn)
        logger.info("stream.pxmax                     : %s", stream.pxmax)
        logger.info("stream.full_shape                : %s", stream.full_shape)
        logger.info("stream.port                      : %s", stream.port)
        logger.info("stream.metadata.creation_time    : %s", stream.creation_time)
        logger.info("stream.metadata.last_access_time : %s", stream.last_access_time)
        for ikey, key in enumerate(stream.keywords):
            logger.info("keyword %02d = keywords[%8s]  : {{.value = %s,.type = %s,.comment = %s}}", ikey, key, stream.keywords[key].value, stream.keywords[key].type, stream.keywords[key].comment)

    # ---- stbsink ----------------------------------------------------------------------------------------------------
    def test_stbsink(self):
        slm = Modulator(Stream("stb001_stbsink"))
        # Properties common to all streams
        logger.info("slm.name                         : %s", slm.name)
        logger.info("slm.kind                         : %s", slm.kind)
        logger.info("slm.sn                           : %s", slm.sn)
        logger.info("slm.pxmax                        : %s", slm.pxmax)
        logger.info("slm.full_shape                   : %s", slm.full_shape)
        logger.info("slm.port                         : %s", slm.port)
        logger.info("slm.metadata.creation_time       : %s", slm.creation_time)
        logger.info("slm.metadata.last_access_time    : %s", slm.last_access_time)
        # # Properties specific to slm streams
        logger.info("slm.max_radius                   : %s", slm.max_radius)
        logger.info("slm.radius                       : %s", slm.radius)
        logger.info("slm.center                       : %s", slm.center)
        logger.info("slm.shape                        : %s", slm.shape)
        logger.info("slm.frame_rate_fps               : %s", slm.frame_rate_fps)

    def test_stbsink_command(self):
        # ./stbsink must be running
        slm = Modulator(Stream("stb001_stbsink"))
        for i in range(100):
            logger.info("frame : %s", i)
            command = slm.blank
            slm.push_command(command)
            time.sleep(0.01)

    # ---- sink -------------------------------------------------------------------------------------------------------
    def test_lcdsink(self):
        slm = Modulator(Stream("lcd001_lcdsink"))
        # Properties common to all streams
        logger.info("slm.name                         : %s", slm.name)
        logger.info("slm.kind                         : %s", slm.kind)
        logger.info("slm.sn                           : %s", slm.sn)
        logger.info("slm.pxmax                        : %s", slm.pxmax)
        logger.info("slm.full_shape                   : %s", slm.full_shape)
        logger.info("slm.port                         : %s", slm.port)
        logger.info("slm.metadata.creation_time       : %s", slm.creation_time)
        logger.info("slm.metadata.last_access_time    : %s", slm.last_access_time)
        # # Properties specific to slm streams
        logger.info("slm.max_radius                   : %s", slm.max_radius)
        logger.info("slm.radius                       : %s", slm.radius)
        logger.info("slm.center                       : %s", slm.center)
        logger.info("slm.shape                        : %s", slm.shape)
        logger.info("slm.frame_rate_fps               : %s", slm.frame_rate_fps)

    def test_lcdsink_command(self):
        # ./lcdsink must be running
        slm = Modulator(Stream("lcd001_lcdsink"))
        for i in range(100):
            logger.info("frame : %s", i)
            slm.push_command(((2**16 - 1) * preroll(slm.shape, i, i / 100.0, 100)).astype(np.uint16))
            time.sleep(0.01)
