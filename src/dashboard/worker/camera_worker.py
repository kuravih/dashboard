import time

from pykato.log import setup_logger
from PySide6.QtCore import Signal, Slot
from pytestbed import SourceSample

from pytestbed.device.camera import Camera
from ..worker import Worker, WorkerSignals

logger = setup_logger("camera_sampling_worker", terminator="\n")


class ProcessWorkerSignals(WorkerSignals):
    sampled = Signal(SourceSample)


class ProcessWorker(Worker):
    _allowed_slots_ = Worker._allowed_slots_ | {"signals", "_camera"}

    def __init__(self, camera: Camera):
        super().__init__()
        self.signals = ProcessWorkerSignals()
        self._camera = camera

    @property
    def wid(self):
        return f"{self._camera.name}_sampling_worker"

    @Slot()
    def run(self):
        super().run()
        while self._running:
            time.sleep(0.1)
            try:
                self.signals.sampled.emit(self._camera.pull_capture())
            except RuntimeError:
                break

        logger.info("camera_worker.py - ProcessWorker() finished")
        self.stop()
        try:
            self.signals.finished.emit()
        except RuntimeError:
            pass
