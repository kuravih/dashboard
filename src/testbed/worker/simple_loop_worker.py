import time
import numpy as np
from PySide6.QtCore import Slot, Signal

from pykato.function import text
from pykato.log import setup_logger

import testbed
from ..device import SourceSample, SinkSample
from ..device.camera import Camera
from ..device.modulator import Modulator
from . import Worker, WorkerSignals

_PROCESS_ = testbed.SIMPLE_LOOP

logger = setup_logger(f"{_PROCESS_}_worker", terminator="\n")


class ProcessWorkerSignals(WorkerSignals):
    srcSampled = Signal(SourceSample)
    snkSampled = Signal(SinkSample)


class ProcessWorker(Worker):
    def __init__(self, source: Camera, sink: Modulator, amplitude: float, n_steps: int | None = None):
        """
        Simple Loop Process Worker

        Parameters:
            source: Camera
                Data source

            sink: Modulator
                Data sink

            amplitude: float
                Amplitude percentage

            n_steps: int
                Number of steps

        """
        super().__init__()
        self.signals = ProcessWorkerSignals()
        self.source = source
        self.sink = sink
        self.amplitude = amplitude
        self.n_steps = n_steps

    @Slot()
    def run(self):
        super().run()
        t_start = time.time()

        self.source.pull_capture() # Flush the sensor
        time.sleep(0.2)

        # ---- blank --------------------------------------------------------------------------------------------------
        current_cmd = np.zeros(self.sink.shape)

        _current_sink_sample = self.sink.push_command(current_cmd)
        self.signals.snkSampled.emit(_current_sink_sample)
        time.sleep(0.1)

        _current_source_sample = self.source.pull_capture()
        self.signals.srcSampled.emit(_current_source_sample)
        time.sleep(0.2)

        i_step = 0
        self.signals.progressTicked.emit(i_step, time.time() - t_start)
        # ---- blank --------------------------------------------------------------------------------------------------

        logger.info("%s and %s ProcessWorker.run : step %i of %.0f", self.source.name, self.sink.name, i_step, self.n_steps if self.n_steps else np.inf)

        while ((self.n_steps is None) or (self.n_steps > i_step)) and self._running:

            probe_command = self.amplitude * text(self.sink.shape, f"{i_step:02d}", font_size=150)

            command = current_cmd + probe_command

            _current_sink_sample = self.sink.push_command(command)
            self.signals.snkSampled.emit(_current_sink_sample)
            time.sleep(0.1)

            _current_source_sample = self.source.pull_capture()
            self.signals.srcSampled.emit(_current_source_sample)
            time.sleep(0.2)

            i_step = i_step + 1
            self.signals.progressTicked.emit(i_step, time.time() - t_start)

            logger.info("%s and %s ProcessWorker.run : step %i of %.0f", self.source.name, self.sink.name, i_step, self.n_steps if self.n_steps else np.inf)

        self.signals.finished.emit()
