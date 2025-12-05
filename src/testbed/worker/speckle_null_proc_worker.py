import time
import numpy as np
from PySide6.QtCore import Slot, Signal

from pykato.function import sinusoid
from pykato.log import setup_logger

from ..device import SourceSample, SinkSample
from ..device.camera import Camera
from ..device.modulator import Modulator
from ..device.mirror import Mirror
from ..worker import Worker, WorkerSignals

logger = setup_logger("speckle_null_proc_worker", terminator="\n")


class SpeckleNullProcWorkerSignals(WorkerSignals):
    new_source_sample = Signal(SourceSample)
    new_sink_sample = Signal(SinkSample)


class SpeckleNullProcWorker(Worker):
    def __init__(self, _source: Camera, _sink: Modulator | Mirror, _freqs: np.ndarray, _angles: np.ndarray, _phases: np.ndarray):
        super().__init__()
        self.signals = SpeckleNullProcWorkerSignals()
        self._source = _source
        self._sink = _sink
        self._freqs = _freqs
        self._angles = _angles
        self._phases = _phases
        self._n_steps = _freqs.size * _angles.size * _phases.size

    @Slot()
    def run(self):
        super().run()
        i_step = 0
        t_start = time.time()
        for _freq in self._freqs:
            for _angle in self._angles:
                for _phase in self._phases:
                    time.sleep(0.1)
                    command = self._sink.pxmax * np.clip(0.25 * sinusoid(self._sink.shape, 1.0 / _freq, np.deg2rad(_phase), np.deg2rad(_angle)) + 0.5, 0, 1)
                    logger.info("%s and %s SpeckleNullProcWorker.run : step %s of %s", self._source.name, self._sink.name, i_step, self._n_steps)
                    self._sink.push_command(command.astype(np.uint16))
                    self.signals.new_source_sample.emit(self._source.pull_sample())
                    self.signals.new_sink_sample.emit(self._sink.pull_sample())
                    self.signals.progress.emit(i_step, time.time() - t_start)
                    i_step = i_step + 1
        self.signals.finish.emit()
