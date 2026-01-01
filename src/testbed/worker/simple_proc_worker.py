import time
import numpy as np
from PySide6.QtCore import Slot, Signal

from pykato.function import text
from pykato.log import setup_logger

from ..device import SourceSample, SinkSample
from ..device.camera import Camera
from ..device.modulator import Modulator
from ..device.mirror import Mirror
from ..worker import Worker, WorkerSignals

logger = setup_logger("simple_proc_worker", terminator="\n")


class SimpleProcWorkerSignals(WorkerSignals):
    new_source_sample = Signal(SourceSample)
    new_sink_sample = Signal(SinkSample)


class SimpleProcWorker(Worker):
    def __init__(self, _source: Camera, _sink: Modulator | Mirror, n_steps: int | None = None):
        super().__init__()
        self.signals = SimpleProcWorkerSignals()
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
        logger.info("%s and %s SimpleProcWorker.run : blank", self._source.name, self._sink.name)

        self.signals.new_sink_sample.emit(self._sink.push_command(command.astype(np.uint16)))
        time.sleep(5)
        self.signals.new_source_sample.emit(self._source.pull_capture())

        self.signals.progress.emit(i_step, time.time() - t_start)
        # ---- blank --------------------------------------------------------------------------------------------------

        while ((self._n_steps is None) or (self._n_steps > i_step)) and self._running:
            command = self._sink.pxmax * np.clip(text(self._sink.shape, f"{i_step:02d}", font_size=150), 0, 1)
            logger.info("%s and %s SimpleProcWorker.run : step %s of %s", self._source.name, self._sink.name, i_step, self._n_steps)
            self.signals.new_sink_sample.emit(self._sink.push_command(command.astype(np.uint16)))
            time.sleep(5)
            self.signals.new_source_sample.emit(self._source.pull_capture())
            time.sleep(5)
            i_step = i_step + 1
            self.signals.progress.emit(i_step, time.time() - t_start)
        self.signals.finish.emit()

        # self._sink.push_command(_current_sink_sample.command.astype(np.uint16))
