import time
from PySide6.QtCore import Slot, Signal

from pykato.log import setup_logger

from ..device import SourceSample
from ..device.camera import Camera
from ..worker import Worker, WorkerSignals

logger = setup_logger("camera_sampling_worker", terminator="\n")


class ProcessWorkerSignals(WorkerSignals):
    sampled = Signal(SourceSample)


class ProcessWorker(Worker):
    def __init__(self, camera: Camera):
        super().__init__()
        self.signals = ProcessWorkerSignals()
        self._camera = camera

    @Slot()
    def run(self):
        super().run()
        while self._running:
            time.sleep(0.1)
            # logger.info("%s UpdateWorker.run", self._camera.name)
            self.signals.sampled.emit(self._camera.pull_capture())
        logger.info("camera sampling worker finished")
        self.signals.finished.emit()
