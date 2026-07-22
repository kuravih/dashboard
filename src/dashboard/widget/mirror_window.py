from pykato.log import setup_logger

from pytestbed.device.mirror import Mirror
from ..widget import Window

logger = setup_logger("mirror_window", terminator="\n")


# ==== PreviewWindow ============================================================================================
class PreviewWindow(Window):
    """Mirror Preview Window"""

    def __init__(self, mirror: Mirror):
        super().__init__()
        self._mirror = mirror

    @property
    def mirror(self) -> Mirror:
        return self._mirror

    def closeEvent(self, event):
        self.deleteLater()
        event.accept()


# ==== InfoWindow ===============================================================================================
class InfoWindow(Window):
    """Mirror Info Window"""

    def __init__(self, mirror: Mirror):
        super().__init__()
        self._mirror = mirror

    @property
    def mirror(self) -> Mirror:
        return self._mirror

    def closeEvent(self, event):
        self.deleteLater()
        event.accept()


# ==== SettingsWindow ===========================================================================================
class SettingsWindow(Window):
    def __init__(self, mirror: Mirror):
        super().__init__()
        self._mirror = mirror

    @property
    def mirror(self) -> Mirror:
        return self._mirror

    def closeEvent(self, event):
        self.deleteLater()
        event.accept()
