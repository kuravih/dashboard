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
    sourceSampled = Signal(SourceSample)
    sinkSampled = Signal(SinkSample)


class ProcessWorker(Worker):
    def __init__(self, _source: Camera, _sink: Modulator, n_steps: int | None = None):
        super().__init__()
        self.signals = ProcessWorkerSignals()
        self._source = _source
        self._sink = _sink
        self._n_steps = n_steps

    @Slot()
    def run(self):
        super().run()
        i_step = 0
        t_start = time.time()

        # ---- blank --------------------------------------------------------------------------------------------------
        command = self._sink.pxmax * np.clip(np.zeros(self._sink.shape) + 0.5, 0, 1)

        self.signals.sinkSampled.emit(self._sink.push_command(command.astype(np.uint16)))
        time.sleep(0.1)

        self.signals.sourceSampled.emit(self._source.pull_capture())
        time.sleep(0.2)

        self.signals.progressTicked.emit(i_step, time.time() - t_start)
        # ---- blank --------------------------------------------------------------------------------------------------

        logger.info("%s and %s ProcessWorker.run : step %s of %s", self._source.name, self._sink.name, i_step, self._n_steps)

        while ((self._n_steps is None) or (self._n_steps > i_step)) and self._running:
            command = self._sink.pxmax * np.clip(text(self._sink.shape, f"{i_step:02d}", font_size=150), 0, 1)

            self.signals.sinkSampled.emit(self._sink.push_command(command.astype(np.uint16)))
            time.sleep(0.1)

            self.signals.sourceSampled.emit(self._source.pull_capture())
            time.sleep(0.2)

            i_step = i_step + 1
            self.signals.progressTicked.emit(i_step, time.time() - t_start)

            logger.info("%s and %s ProcessWorker.run : step %s of %s", self._source.name, self._sink.name, i_step, self._n_steps)

        self.signals.finished.emit()

        # self._sink.push_command(_current_sink_sample.command.astype(np.uint16))
