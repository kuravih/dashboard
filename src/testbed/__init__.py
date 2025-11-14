from PySide6.QtCore import QThreadPool

from .device import Device
from .widget import Window
from .worker import Worker


class Data:
    threadpool = QThreadPool()
    devices: dict[str, Device] = {}
    windows: dict[str, Window] = {}
    workers: dict[str, Worker] = {}


data = Data()
