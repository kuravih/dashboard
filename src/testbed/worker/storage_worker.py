from PySide6.QtCore import Slot
from ..worker import Worker, WorkerSignals
from ..device import SourceSample, SinkSample
from queue import Queue
import struct
from ..function import DTYPE_MAP


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
            header_sample = self.queue.get()
            h, w = header_sample.capture.shape[:2]
            tl = header_sample.roi.get("tl", (0, 0))
            br = header_sample.roi.get("br", (w, h))
            dtype_code = DTYPE_MAP[header_sample.capture.dtype.type]
            header = struct.pack(
                "<7s" + "HH" + "I" + "fff" + "HHHH" + "B",
                b"SRCSMPL",
                h,  # unsigned short - H
                w,  # unsigned short - H
                header_sample.exposure_time_us,  # unsigned int - I
                header_sample.gain,  # float - f
                header_sample.frame_rate_fps,  # float - f
                header_sample.temperature_c,  # float - f
                tl[0],  # unsigned short - H
                tl[1],  # unsigned short - H
                br[0],  # unsigned short - H
                br[1],  # unsigned short - H
                dtype_code,  # unsigned byte - B
            )
            _file.write(header)
            while self._running:
                sample = self.queue.get()
                if sample is None:
                    break
                _file.write(struct.pack("<d", sample.last_access_time.timestamp()) + sample.capture.tobytes())
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
            header_sample = self.queue.get()
            h, w = header_sample.command.shape[:2]
            center = header_sample.center
            dtype_code = DTYPE_MAP[header_sample.command.dtype.type]
            header = struct.pack(
                "<7s" + "HH" + "f" + "fff" + "B",
                b"SNKSMPL",
                h,  # unsigned short - H
                w,  # unsigned short - H
                header_sample.frame_rate_fps,  # float - f
                center[0],  # unsigned short - H
                center[1],  # unsigned short - H
                header_sample.radius,  # unsigned short - H
                dtype_code,  # unsigned byte - B
            )
            _file.write(header)
            while self._running:
                sample = self.queue.get()
                if sample is None:
                    break
                _file.write(struct.pack("<d", sample.last_access_time.timestamp()) + sample.command.tobytes())
        self.signals.finish.emit()
