from PySide6.QtCore import Slot
from ..worker import Worker, WorkerSignals
from ..device import SourceSample, SinkSample
from queue import Queue
from ..function import write_source_sample_header, write_source_sample_data, write_sink_sample_header, write_sink_sample_data


class SourceStorageWorker(Worker):
    def __init__(self, filename: str, maxsize: int | None = None):
        super().__init__()
        self.queue: Queue[SourceSample] = Queue(maxsize=-1 if maxsize is None else maxsize)
        self.filename = filename
        self.signals = WorkerSignals()

    @Slot(SourceSample)
    def on_sampled(self, sample: SourceSample):
        self.queue.put(sample)

    def run(self):
        super().run()
        with open(self.filename, "wb", buffering=0) as fileio:
            _sample = self.queue.get()
            write_source_sample_header(fileio, _sample)
            write_source_sample_data(fileio, _sample)
            while self._running:
                __sample = self.queue.get()
                if __sample is None:
                    break
                write_source_sample_data(fileio, __sample)
        self.signals.finished.emit()


class SinkStorageWorker(Worker):
    def __init__(self, filename: str, maxsize: int | None = None):
        super().__init__()
        self.queue: Queue[SinkSample] = Queue(maxsize=-1 if maxsize is None else maxsize)
        self.filename = filename
        self.signals = WorkerSignals()

    @Slot(SinkSample)
    def on_sampled(self, sample: SinkSample):
        self.queue.put(sample)

    def run(self):
        super().run()
        with open(self.filename, "wb", buffering=0) as fileio:
            _sample = self.queue.get()
            write_sink_sample_header(fileio, _sample)
            write_sink_sample_data(fileio, _sample)
            while self._running:
                __sample = self.queue.get()
                if __sample is None:
                    break
                write_sink_sample_data(fileio, __sample)
        self.signals.finished.emit()
