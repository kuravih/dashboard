from PySide6.QtWidgets import QMessageBox


class MessageDialog(QMessageBox):
    def __init__(self, title: str, message: str, icon: QMessageBox.Icon = QMessageBox.Icon.Information, buttons: QMessageBox.StandardButtons = (QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel), parent=None):
        super().__init__(parent)

        self.setWindowTitle(title)
        self.setText(message)
        self.setIcon(icon)
        self.setStandardButtons(buttons)
        self.setDefaultButton(QMessageBox.StandardButton.Ok)
