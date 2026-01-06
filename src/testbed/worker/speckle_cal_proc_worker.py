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

logger = setup_logger("speckle_cal_proc_worker", terminator="\n")


class SpeckleCalProcWorkerSignals(WorkerSignals):
    new_source_sample = Signal(SourceSample)
    new_sink_sample = Signal(SinkSample)


class SpeckleCalProcWorker(Worker):
    def __init__(self, _source: Camera, _sink: Modulator | Mirror, _ampl: float, _freqs: np.ndarray, _angles: np.ndarray, _phases: np.ndarray):
        super().__init__()
        self.signals = SpeckleCalProcWorkerSignals()
        self._source = _source
        self._sink = _sink
        self._ampl = _ampl
        self._freqs = _freqs
        self._angles = _angles
        self._phases = _phases
        self._n_steps = _freqs.size * _angles.size * _phases.size

    @Slot()
    def run(self):
        super().run()
        i_step = 0
        t_start = time.time()

        # ---- blank --------------------------------------------------------------------------------------------------
        command = self._sink.pxmax * np.clip(np.zeros(self._sink.shape) + 0.5, 0, 1)

        self.signals.new_sink_sample.emit(self._sink.push_command(command.astype(np.uint16)))
        time.sleep(0.1)

        self.signals.new_source_sample.emit(self._source.pull_capture())
        time.sleep(0.2)

        self.signals.progress.emit(i_step, time.time() - t_start)
        # ---- blank --------------------------------------------------------------------------------------------------

        for _freq in self._freqs:
            for _angle in self._angles:
                for _phase in self._phases:
                    command = self._sink.pxmax * np.clip(self._ampl * sinusoid(self._sink.shape, 1.0 / _freq, np.deg2rad(_phase), np.deg2rad(_angle)) + 0.5, 0, 1)

                    self.signals.new_sink_sample.emit(self._sink.push_command(command.astype(np.uint16)))
                    time.sleep(0.1)
                    
                    self.signals.new_source_sample.emit(self._source.pull_capture())
                    time.sleep(0.2)
                
                    i_step = i_step + 1
                    self.signals.progress.emit(i_step, time.time() - t_start)

                    logger.info("%s and %s SpeckleCalProcWorker.run : step %s of %s", self._source.name, self._sink.name, i_step, self._n_steps)

        self.signals.finish.emit()

        # self._sink.push_command(_current_sink_sample.command.astype(np.uint16))
