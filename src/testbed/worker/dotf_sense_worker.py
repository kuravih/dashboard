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
        super().__init__()
        self.signals = ProcessWorkerSignals()
        self.source = source
        self.sink = sink
        self.amplitude = amplitude
        self.n_steps = n_steps

    @Slot()
    def run(self):
        super().run()
        i_step = 0
        t_start = time.time()

        # ---- blank --------------------------------------------------------------------------------------------------
        current_cmd = self.sink.pxmax * (np.zeros(self.sink.shape) + 0.5)

        self.signals.snkSampled.emit(self.sink.push_command(current_cmd.astype(np.uint16)))
        time.sleep(0.1)

        self.signals.srcSampled.emit(self.source.pull_capture())
        time.sleep(0.2)

        self.signals.progressTicked.emit(i_step, time.time() - t_start)
        # ---- blank --------------------------------------------------------------------------------------------------

        logger.info("%s and %s ProcessWorker.run : step %i of %i", self.source.name, self.sink.name, i_step, self.n_steps)

        while ((self.n_steps is None) or (self.n_steps > i_step)) and self._running:
            probe_command = self.amplitude * self.sink.pxmax * (text(self.sink.shape, f"{i_step:02d}", font_size=150) - 0.5)
            command = current_cmd + probe_command
            command = np.clip(command, 0, self.sink.pxmax)

            _current_sink_sample = self.sink.push_command(command.astype(np.uint16))
            self.signals.snkSampled.emit(_current_sink_sample)
            time.sleep(0.1)

            _current_source_sample = self.source.pull_capture()
            self.signals.srcSampled.emit(_current_source_sample)
            time.sleep(0.2)

            i_step = i_step + 1
            self.signals.progressTicked.emit(i_step, time.time() - t_start)

            logger.info("%s and %s ProcessWorker.run : step %i of %i", self.source.name, self.sink.name, i_step, self.n_steps)

        self.signals.finished.emit()
