from PySide6.QtCore import Slot
from ..worker import Worker, WorkerSignals
from ..device import SourceSample, SinkSample
from queue import Queue
import struct
from ..function import write_source_sample, write_sink_sample


class SourceStorageWorker(Worker):
    def __init__(self, filename: str, _maxsize: int = -1):
        super().__init__()
        self.queue: Queue[SourceSample] = Queue(maxsize=_maxsize)
        self.filename = filename
        self.signals = WorkerSignals()

    @Slot(SourceSample)
    def on_sample(self, _sample: SourceSample):
        self.queue.put(_sample)

    def run(self):
        super().run()
        with open(self.filename, "wb", buffering=0) as _file:
            _sample = self.queue.get()
            write_source_sample(_file, _sample)
            while self._running:
                __sample = self.queue.get()
                if __sample is None:
                    break
                _file.write(struct.pack("<d", __sample.last_access_time.timestamp()) + __sample.capture.tobytes())
        self.signals.finish.emit()


class SinkStorageWorker(Worker):
    def __init__(self, filename: str, _maxsize: int = -1):
        super().__init__()
        self.queue: Queue[SinkSample] = Queue(maxsize=_maxsize)
        self.filename = filename
        self.signals = WorkerSignals()

    @Slot(SinkSample)
    def on_sample(self, _sample: SinkSample):
        self.queue.put(_sample)

    def run(self):
        super().run()
        with open(self.filename, "wb", buffering=0) as _file:
            _sample = self.queue.get()
            write_sink_sample(_file, _sample)
            while self._running:
                __sample = self.queue.get()
                if __sample is None:
                    break
                _file.write(struct.pack("<d", __sample.last_access_time.timestamp()) + __sample.command.tobytes())
        self.signals.finish.emit()
