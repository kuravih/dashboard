import time
import numpy as np
from PySide6.QtCore import Slot, Signal

from pykato.function import preroll
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
        while ((self._n_steps is None) or (self._n_steps > i_step)) and self._running:
            time.sleep(0.1)
            count = time.time() % 60.0
            command = (2**16 - 1) * preroll(self._sink.shape, int(count), count / 60.0, 100)
            logger.info("%s and %s SimpleProcWorker.run", self._source.name, self._sink.name)
            self._sink.push_command(command.astype(np.uint16))
            self.signals.new_source_sample.emit(self._source.pull_sample())
            self.signals.new_sink_sample.emit(self._sink.pull_sample())
            self.signals.progress.emit(i_step, time.time() - t_start)
            i_step = i_step + 1
        self.signals.finished.emit()
