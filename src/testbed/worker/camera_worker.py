import time
from PySide6.QtCore import Slot, Signal

from pykato.log import setup_logger

from ..device import SourceSample
from ..device.camera import Camera
from ..worker import Worker, WorkerSignals

logger = setup_logger("camera_worker", terminator="\n")


class UpdateWorkerSignals(WorkerSignals):
    new_sample = Signal(SourceSample)


class UpdateWorker(Worker):
    def __init__(self, _camera: Camera):
        super().__init__()
        self.signals = UpdateWorkerSignals()
        self._camera = _camera

    @Slot()
    def run(self):
        super().run()
        while self._running:
            time.sleep(0.1)
            # logger.info("%s UpdateWorker.run", self._camera.name)
            self.signals.new_sample.emit(self._camera.pull_capture())
