from enum import Enum, auto
from collections.abc import Iterator
import numpy as np
import time
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QDoubleSpinBox, QSpinBox, QComboBox, QPushButton, QLabel, QProgressBar, QGridLayout, QSpacerItem, QSizePolicy, QToolTip, QRadioButton, QButtonGroup, QCheckBox
from PySide6.QtCore import Signal, Slot, Qt
from PySide6.QtGui import QIcon, QCursor

from ..device import Device
from ..device.camera import Camera
from ..device.modulator import Modulator
from ..widget.resource import ICON_RUN, ICON_EYE, ICON_UP_ARROW, ICON_DOWN_ARROW, ICON_LEFT_ARROW, ICON_RIGHT_ARROW, ICON_INFO, ICON_GEAR
from ..function import Rotation, Flip


class Window(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class DevicesComboBox(QComboBox):
    """
    Devices combo box.

    Parameters:
        devices: list[Device]
            Devices list to show.
        types: tuple[type, ...]
            Type of devices out of the list to show, specify multiple kinds to show devices of multiple kinds.

    Function:
        showPopup()
            Overridden pop up function will show only device options of a given kind.
    """

    def __init__(self, devices: dict[str, Camera | Modulator], types: tuple[type, ...], parent=None):
        super().__init__(parent)
        self.devices = devices
        self.types = types

    def showPopup(self):  # pylint: disable=C0103:invalid-name
        super().blockSignals(True)

        self.clear()

        for key, device in self.devices.items():
            if isinstance(device, self.types):
                self.addItem(key)
        self.setCurrentIndex(-1)

        super().showPopup()

        super().blockSignals(False)


class DevicesSetupWidget(QWidget):
    """
    Devices setup widget, with two comboboxes for sink devices and source devices.

    Parameters:
        devices: dict[str, Camera | Modulator]
            list of devices to show.
        setup_sink: bool = True
            Show the sink selection combobox
        setup_source: bool = True
            Show the source selection combobox
        setup_source_settings: bool = True,
            Show the source settings button?

    Signals:
        sinkChanged: Signal()
            Signal changing the sink.

        sourceChanged: Signal()
            Signal changing the source.
    """

    sinkChanged = Signal(Device)
    sourceChanged = Signal(Device)

    def __init__(self, devices: dict[str, Camera | Modulator], setup_sink: bool = True, setup_source: bool = True, parent=None):
        super().__init__(parent)
        self.devices = devices
        self.setup_sink = setup_sink
        self.setup_source = setup_source
        # self._setup_source_settings = setup_source_settings

        sink_device_label = QLabel("Sink", self)
        sink_device_label.hide()

        sink_device_combobox = DevicesComboBox(self.devices, (Modulator,), self)
        sink_device_combobox.setToolTip("Required")
        sink_device_combobox.hide()

        @Slot(str)
        def on_sink_device_select(key: str):
            self.sinkChanged.emit(self.devices[key])

        sink_device_combobox.currentTextChanged.connect(on_sink_device_select)

        self.sink_info_button = QPushButton(QIcon(ICON_INFO), "")
        self.sink_info_button.setEnabled(False)
        self.sink_info_button.setFixedWidth(self.sink_info_button.sizeHint().height())
        self.sink_info_button.setToolTip("Information")

        self.sink_settings_button = QPushButton(QIcon(ICON_GEAR), "")
        self.sink_settings_button.setEnabled(False)
        self.sink_settings_button.setFixedWidth(self.sink_settings_button.sizeHint().height())
        self.sink_settings_button.setToolTip("Settings")

        self.sink_preview_button = QPushButton(QIcon(ICON_EYE), "")
        self.sink_preview_button.setEnabled(False)
        self.sink_preview_button.setFixedWidth(self.sink_preview_button.sizeHint().height())
        self.sink_preview_button.setToolTip("Sink Preview")

        source_device_label = QLabel("Source")
        source_device_label.setFixedWidth(100)
        source_device_label.hide()

        source_device_combobox = DevicesComboBox(self.devices, (Camera,), self)
        source_device_combobox.setToolTip("Required")
        source_device_combobox.hide()

        @Slot(str)
        def on_source_device_select(key: str):
            self.sourceChanged.emit(self.devices[key])

        source_device_combobox.currentTextChanged.connect(on_source_device_select)

        self.source_info_button = QPushButton(QIcon(ICON_INFO), "")
        self.source_info_button.setEnabled(False)
        self.source_info_button.setFixedWidth(self.source_info_button.sizeHint().height())
        self.source_info_button.setToolTip("Information")

        self.source_settings_button = QPushButton(QIcon(ICON_GEAR), "")
        self.source_settings_button.setEnabled(False)
        self.source_settings_button.setFixedWidth(self.source_settings_button.sizeHint().height())
        self.source_settings_button.setToolTip("Settings")

        self.source_preview_button = QPushButton(QIcon(ICON_EYE), "")
        self.source_preview_button.setEnabled(False)
        self.source_preview_button.setFixedWidth(self.source_preview_button.sizeHint().height())
        self.source_preview_button.setToolTip("Source Preview")

        layout = QGridLayout()

        row = 0
        col = 0

        if self.setup_sink:
            sink_device_label.show()
            layout.addWidget(sink_device_label, row, col)
            col += 1
            sink_device_combobox.show()
            layout.addWidget(sink_device_combobox, row, col)
            col += 1
            layout.addWidget(self.sink_info_button, row, col)
            col += 1
            layout.addWidget(self.sink_settings_button, row, col)
            col += 1
            layout.addWidget(self.sink_preview_button, row, col)

        if self.setup_source:
            row += 1
            col = 0
            source_device_label.show()
            layout.addWidget(source_device_label, row, col)
            col += 1
            source_device_combobox.show()
            layout.addWidget(source_device_combobox, row, col)
            col += 1
            layout.addWidget(self.source_info_button, row, col)
            col += 1
            layout.addWidget(self.source_settings_button, row, col)
            col += 1
            layout.addWidget(self.source_preview_button, row, col)

        self.setLayout(layout)


class ProgressBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        grid = QGridLayout()

        self.time = 0
        self.bar = QProgressBar()
        self.label = QLabel("")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("color: white;")
        self.format = ""

        grid.addWidget(self.bar, 0, 0)
        grid.addWidget(self.label, 0, 0)
        self.setLayout(grid)

        self.setMaximum = self.bar.setMaximum
        self.setValue = self.bar.setValue
        self.reset = self.bar.reset

    def setTime(self, _time: float):
        self.time = _time

    def updateProgress(self):
        if self.bar.maximum() == 0:
            self.bar.setFormat("")
            self.label.setText(f"Step {self.bar.value()} - {time.strftime('%H:%M:%S', time.gmtime(self.time))}")
        else:
            self.bar.setFormat(f"Step {self.bar.value()} of {self.bar.maximum()} - {time.strftime('%H:%M:%S', time.gmtime(self.time))}")  # pylint: disable=W1405:inconsistent-quotes
            self.label.setText("")


class LinspaceWidget(QWidget):
    """
    Widget with a start, stop double spinboxes and a count spinbox.

    Function:
        value(): np.ndarray
            Array of np.linspace values.
    """

    valueChanged = Signal(np.ndarray)

    def __init__(self, start: float, stop: float, steps: int, parent=None):
        super().__init__(parent)

        self.start_spinbox = QDoubleSpinBox(self)
        self.start_spinbox.setRange(-999, 999)
        self.start_spinbox.setDecimals(2)
        self.start_spinbox.setToolTip("Start")
        self.start_spinbox.setValue(start)
        self.start_spinbox.valueChanged.connect(self._on_value_changed)

        self.stop_spinbox = QDoubleSpinBox(self)
        self.stop_spinbox.setRange(-999, 999)
        self.stop_spinbox.setDecimals(2)
        self.stop_spinbox.setToolTip("Stop")
        self.stop_spinbox.setValue(stop)
        self.stop_spinbox.valueChanged.connect(self._on_value_changed)

        self.num_spinbox = QSpinBox(self)
        self.num_spinbox.setMinimum(1)
        self.num_spinbox.setToolTip("Number of steps")
        self.num_spinbox.setValue(steps)
        self.num_spinbox.valueChanged.connect(self._on_value_changed)

        self.help_button = QPushButton("?", self)
        self.help_button.setFixedWidth(self.help_button.sizeHint().height())
        self.help_button.clicked.connect(lambda: QToolTip.showText(QCursor.pos(), f"{np.array2string(self.value(), precision=4, separator=', ')}"))

        layout = QHBoxLayout()
        layout.addWidget(self.start_spinbox)
        layout.addWidget(self.stop_spinbox)
        layout.addWidget(self.num_spinbox)
        layout.addWidget(self.help_button, alignment=Qt.AlignmentFlag.AlignLeft)

        layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(layout)

    def value(self) -> np.ndarray:
        return np.linspace(self.start_spinbox.value(), self.stop_spinbox.value(), self.num_spinbox.value())

    @Slot()
    def _on_value_changed(self):
        """Slot that emits the current linspace array when any spinbox changes."""
        self.valueChanged.emit(self.value())


class NDoubleSpinBoxesWidget(QWidget):
    """
    Widget with multiple double spinboxes.

    Parameter:
        count: int = 2
            Number of spinboxes.

    Function:
        value(): list[float]
            list of values.
    """

    def __init__(self, count: int = 2, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self._spinboxes = []
        for _ in range(count):
            spinbox = QDoubleSpinBox(self)
            self._spinboxes.append(spinbox)
            layout.addWidget(spinbox)

        self.setLayout(layout)

    def __getitem__(self, index) -> QDoubleSpinBox:
        return self._spinboxes[index]

    def __iter__(self) -> Iterator[QDoubleSpinBox]:
        return iter(self._spinboxes)

    def value(self) -> list[float]:
        return list(spinbox.value() for spinbox in self._spinboxes)


class NSpinBoxesWidget(QWidget):
    """
    Widget with multiple spinboxes.

    Parameter:
        count: int = 2
            Number of spinboxes.

    Function:
        value(): list[int]
            list of values.
    """

    def __init__(self, count=2, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self._spinboxes = []
        for _ in range(count):
            spinbox = QSpinBox(self)
            self._spinboxes.append(spinbox)
            layout.addWidget(spinbox)

        self.setLayout(layout)

    def __getitem__(self, index) -> QSpinBox:
        return self._spinboxes[index]

    def __iter__(self) -> Iterator[QSpinBox]:
        return iter(self._spinboxes)

    def value(self) -> list[int]:
        return list(spinbox.value() for spinbox in self._spinboxes)


class OrientationWidget(QWidget):

    rotationChanged = Signal(Rotation)
    flipChanged = Signal(Flip)

    def __init__(self, rotation: Rotation = Rotation.UP, flip: Flip = Flip.NEG, parent=None):
        super().__init__(parent)
        self.rotate_buttons = {Rotation.UP: QRadioButton("0\u00b0"), Rotation.RIGHT: QRadioButton("90\u00b0"), Rotation.DOWN: QRadioButton("180\u00b0"), Rotation.LEFT: QRadioButton("270\u00b0")}
        for _, b in self.rotate_buttons.items():
            b.setToolTip(f"Rotate preview {b.text()}")
        self.set_rotation(rotation)

        self.flip_checkbox = QCheckBox("Flip", self)
        self.flip_checkbox.setToolTip("flip preview horizontally")
        self.set_flip(flip)

        # --- button group ---
        self.rotate_group = QButtonGroup(self)
        for i, (_, button) in enumerate(self.rotate_buttons.items()):
            self.rotate_group.addButton(button, i)

        # --- layout ---
        layout = QHBoxLayout()
        for b in self.rotate_buttons.values():
            layout.addWidget(b)
        layout.addWidget(self.flip_checkbox)
        layout.addItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum))
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        # --- connections ---
        self.rotate_group.idClicked.connect(self._on_rotation_changed)
        self.flip_checkbox.stateChanged.connect(self._on_flip_change)

    @Slot()
    def _on_rotation_changed(self, index:int):
        mapping = [Rotation.UP, Rotation.RIGHT, Rotation.DOWN, Rotation.LEFT]
        self._rotation = mapping[index]
        self.rotationChanged.emit(self._rotation)

    @Slot()
    def _on_flip_change(self, state):
        self._flip = Flip.POS if state else Flip.NEG
        self.flipChanged.emit(self._flip)

    # --- getters / setters ---
    def get_flip(self) -> Flip:
        return self._flip

    def set_flip(self, flip: Flip):
        self._flip = flip
        self.flip_checkbox.setChecked(flip == Flip.POS)

    def get_rotation(self) -> Rotation:
        return self._rotation

    def set_rotation(self, rotation: Rotation):
        self._rotation = rotation
        self.rotate_buttons[rotation].setChecked(True)


class SquareROIWidget(QWidget):
    roiMoveClicked = Signal(int, int)  # (dx, dy)

    def __init__(self, roi: dict[str, tuple[int, int]], parent=None):
        super().__init__(parent)

        # --- spinbox ---
        Δ_spinbox = QSpinBox(self)
        Δ_spinbox.setRange(1, 100)
        Δ_spinbox.setSingleStep(8)
        Δ_spinbox.setSuffix(" px")
        Δ_spinbox.setFixedWidth(75)

        # --- directional buttons ---
        up_button = QPushButton("", self)
        up_button.setFixedWidth(up_button.sizeHint().height())
        up_button.setIcon(QIcon(ICON_UP_ARROW))
        up_button.setToolTip("Move ROI up")

        down_button = QPushButton("", self)
        down_button.setFixedWidth(down_button.sizeHint().height())
        down_button.setIcon(QIcon(ICON_DOWN_ARROW))
        down_button.setToolTip("Move ROI down")

        left_button = QPushButton("", self)
        left_button.setFixedWidth(left_button.sizeHint().height())
        left_button.setIcon(QIcon(ICON_LEFT_ARROW))
        left_button.setToolTip("Move ROI left")

        right_button = QPushButton("", self)
        right_button.setFixedWidth(right_button.sizeHint().height())
        right_button.setIcon(QIcon(ICON_RIGHT_ARROW))
        right_button.setToolTip("Move ROI right")

        # --- ROI value label ---
        self.value_label = QLabel("", self)
        self.value_label.setToolTip("Region of interest [(x1,y1),(x2,y2)]")

        self.set_roi(roi)

        # --- layout ---
        layout = QHBoxLayout()
        layout.addWidget(Δ_spinbox)
        layout.addWidget(up_button)
        layout.addWidget(down_button)
        layout.addWidget(left_button)
        layout.addWidget(right_button)
        layout.addWidget(self.value_label)
        layout.addItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum))
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        # --- connect handlers ---
        up_button.clicked.connect(lambda: self._emit_moved(0, -Δ_spinbox.value()))
        down_button.clicked.connect(lambda: self._emit_moved(0, Δ_spinbox.value()))
        left_button.clicked.connect(lambda: self._emit_moved(-Δ_spinbox.value(), 0))
        right_button.clicked.connect(lambda: self._emit_moved(Δ_spinbox.value(), 0))

    def _emit_moved(self, dx: int, dy: int):
        self.roiMoveClicked.emit(dx, dy)

    def set_roi(self, roi):
        br, tl = roi["br"], roi["tl"]
        self.value_label.setText(f"[({br[0]}, {br[1]}),({tl[0]}, {tl[1]})]")


class ROIWidget(QWidget):
    roiMoveClicked = Signal(int, int)  # (dx, dy)

    def __init__(self, roi: dict[str, tuple[int, int]], step: int = 8, parent=None):
        super().__init__(parent)

        # --- spinbox ---
        Δ_spinbox = QSpinBox(self)
        Δ_spinbox.setRange(0, 99)
        Δ_spinbox.setSingleStep(step)
        Δ_spinbox.setSuffix(" px")
        Δ_spinbox.setFixedWidth(75)

        # --- directional buttons ---
        up_button = QPushButton("", self)
        up_button.setFixedWidth(up_button.sizeHint().height())
        up_button.setIcon(QIcon(ICON_UP_ARROW))
        up_button.setToolTip("Move ROI up")

        down_button = QPushButton("", self)
        down_button.setFixedWidth(down_button.sizeHint().height())
        down_button.setIcon(QIcon(ICON_DOWN_ARROW))
        down_button.setToolTip("Move ROI down")

        left_button = QPushButton("", self)
        left_button.setFixedWidth(left_button.sizeHint().height())
        left_button.setIcon(QIcon(ICON_LEFT_ARROW))
        left_button.setToolTip("Move ROI left")

        right_button = QPushButton("", self)
        right_button.setFixedWidth(right_button.sizeHint().height())
        right_button.setIcon(QIcon(ICON_RIGHT_ARROW))
        right_button.setToolTip("Move ROI right")

        # --- ROI value label ---
        self.value_label = QLabel("", self)
        self.value_label.setToolTip("Region of interest [(x1,y1),(x2,y2)]")

        self.set_roi(roi)

        # --- layout ---
        layout = QHBoxLayout()
        layout.addWidget(Δ_spinbox)
        layout.addWidget(up_button)
        layout.addWidget(down_button)
        layout.addWidget(left_button)
        layout.addWidget(right_button)
        layout.addWidget(self.value_label)
        layout.addItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum))
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        # --- connect handlers ---
        up_button.clicked.connect(lambda: self._emit_moved(0, -Δ_spinbox.value()))
        down_button.clicked.connect(lambda: self._emit_moved(0, Δ_spinbox.value()))
        left_button.clicked.connect(lambda: self._emit_moved(-Δ_spinbox.value(), 0))
        right_button.clicked.connect(lambda: self._emit_moved(Δ_spinbox.value(), 0))

    def _emit_moved(self, dx: int, dy: int):
        self.roiMoveClicked.emit(dx, dy)

    def set_roi(self, roi: dict[str, tuple[int, int]]):
        br, tl = roi["br"], roi["tl"]
        self.value_label.setText(f"[({br[0]}, {br[1]}),({tl[0]}, {tl[1]})]")


class CenterWidget(QWidget):
    centerMoveClicked = Signal(int, int)  # (dx, dy)

    def __init__(self, center: tuple[int, int], step: int = 8, parent=None):
        super().__init__(parent)

        # --- spinbox ---
        Δ_spinbox = QSpinBox(self)
        Δ_spinbox.setRange(1, 100)
        Δ_spinbox.setSingleStep(step)
        Δ_spinbox.setSuffix(" px")
        Δ_spinbox.setFixedWidth(75)

        # --- directional buttons ---
        up_button = QPushButton("", self)
        up_button.setFixedWidth(up_button.sizeHint().height())
        up_button.setIcon(QIcon(ICON_UP_ARROW))
        up_button.setToolTip("Move ROI up")

        down_button = QPushButton("", self)
        down_button.setFixedWidth(down_button.sizeHint().height())
        down_button.setIcon(QIcon(ICON_DOWN_ARROW))
        down_button.setToolTip("Move ROI down")

        left_button = QPushButton("", self)
        left_button.setFixedWidth(left_button.sizeHint().height())
        left_button.setIcon(QIcon(ICON_LEFT_ARROW))
        left_button.setToolTip("Move ROI left")

        right_button = QPushButton("", self)
        right_button.setFixedWidth(right_button.sizeHint().height())
        right_button.setIcon(QIcon(ICON_RIGHT_ARROW))
        right_button.setToolTip("Move ROI right")

        # --- ROI value label ---
        self.value_label = QLabel("", self)
        self.value_label.setToolTip("Center (x1,y1)")

        self.set_center(center)

        # --- layout ---
        layout = QHBoxLayout()
        layout.addWidget(Δ_spinbox)
        layout.addWidget(up_button)
        layout.addWidget(down_button)
        layout.addWidget(left_button)
        layout.addWidget(right_button)
        layout.addWidget(self.value_label)
        layout.addItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum))
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        # --- connect handlers ---
        up_button.clicked.connect(lambda: self._emit_moved(0, -Δ_spinbox.value()))
        down_button.clicked.connect(lambda: self._emit_moved(0, Δ_spinbox.value()))
        left_button.clicked.connect(lambda: self._emit_moved(-Δ_spinbox.value(), 0))
        right_button.clicked.connect(lambda: self._emit_moved(Δ_spinbox.value(), 0))

    def _emit_moved(self, dx: int, dy: int):
        self.centerMoveClicked.emit(dx, dy)

    def set_center(self, center: tuple[int, int]):
        self.value_label.setText(f"({center[0]}, {center[1]})")


class ValueSetWidget(QWidget):
    valueSetClicked = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.spinbox = QSpinBox(self)
        self.spinbox.setFixedWidth(100)

        self.pushbutton = QPushButton("Set", self)
        self.pushbutton.setFixedWidth(75)

        self.label = QLabel("", self)

        layout = QHBoxLayout()
        layout.addWidget(self.spinbox)
        layout.addWidget(self.pushbutton)
        layout.addWidget(self.label)
        layout.addItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum))
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.pushbutton.clicked.connect(lambda: self._emit_clicked(self.spinbox.value()))

    def _emit_clicked(self, value: int):
        self.valueSetClicked.emit(value)

    def setValue(self, value: int):
        self.label.setText(f"{value}")


class DoubleValueSetWidget(QWidget):
    valueSetClicked = Signal(float)

    def __init__(self, suffix:str="", parent=None):
        super().__init__(parent)
        self.suffix = suffix
        self.spinbox = QDoubleSpinBox(self)
        self.spinbox.setSuffix(self.suffix)

        self.spinbox.setFixedWidth(100)

        self.pushbutton = QPushButton("Set", self)
        self.pushbutton.setFixedWidth(75)

        self.label = QLabel("", self)

        layout = QHBoxLayout()
        layout.addWidget(self.spinbox)
        layout.addWidget(self.pushbutton)
        layout.addWidget(self.label)
        layout.addItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum))
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.pushbutton.clicked.connect(lambda: self._emit_clicked(self.spinbox.value()))

    def _emit_clicked(self, value: float):
        self.valueSetClicked.emit(value)

    def setValue(self, value: float):
        self.spinbox.setValue(value)
        self.label.setText(f"{value}{self.suffix}")


class ExposureTimeArrayWidget(QWidget):
    """
    Exposure time array widget with add and remove step buttons.

    Parameter:
        value: int = 10
            1st Exposure time of the array.

    Function:
        value(): list[int]
            list of Exposure times (us).
    """

    def __init__(self, value: float = 0.001, parent=None):
        super().__init__(parent)

        self._layout = QVBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)

        spinbox = QDoubleSpinBox()
        spinbox.setRange(0, 30000000)
        spinbox.setDecimals(6)
        spinbox.setSingleStep(0.001)
        spinbox.setFixedWidth(150)
        spinbox.setSuffix(" s")
        spinbox.setValue(value)
        spinbox.setToolTip("Exposure time in s (maximum 5min)")
        self._spinboxes = [spinbox]
        self._layout_steps(self._layout, self._spinboxes)
        self.setLayout(self._layout)

    def _layout_steps(self, parent_layout: QVBoxLayout, spinboxes: list[QSpinBox]):
        """Layout a spinbox with a label and a +/- button

        Parameters:
            values: list[int]
                Exposure time values list
        """
        for index, spinbox in enumerate(spinboxes):
            exp_time_label = QLabel(f"Exp Time Step {index + 1}", self)
            button = QPushButton("", self)
            button.setFixedWidth(button.sizeHint().height())
            step_layout = QHBoxLayout()
            step_layout.addWidget(exp_time_label)
            step_layout.addWidget(spinbox)
            step_layout.addWidget(button)
            if index == 0:
                button.setText("+")
                button.clicked.connect(lambda: self._on_add_step(2 * self._spinboxes[-1].value()))
            else:
                button.setText("-")
                button.clicked.connect(lambda: self._on_remove_step(index))
            parent_layout.addLayout(step_layout)

    def clear_layout(self, layout: QVBoxLayout):
        while layout.count():
            item = layout.takeAt(0)  # Get the first item
            widget = item.widget()  # Get the widget from the item
            if isinstance(widget, (QLabel, QPushButton)):  # if button or label
                widget.deleteLater()  # delete it
            else:  # If the item is a layout, recursively clear it
                sub_layout = item.layout()
                if sub_layout:
                    self.clear_layout(sub_layout)

    def _on_add_step(self, value):
        spinbox = QDoubleSpinBox()
        spinbox.setRange(0, 30000000)
        spinbox.setDecimals(6)
        spinbox.setSingleStep(0.001)
        spinbox.setFixedWidth(150)
        spinbox.setSuffix(" s")
        spinbox.setValue(value)
        spinbox.setToolTip("Exposure time in s (maximum 5min)")
        self._spinboxes.append(spinbox)
        self.clear_layout(self._layout)
        self._layout_steps(self._layout, self._spinboxes)

    def _on_remove_step(self, index):
        self._spinboxes[index].deleteLater()
        self._spinboxes.pop(index)
        self.clear_layout(self._layout)
        self._layout_steps(self._layout, self._spinboxes)

    def __getitem__(self, index) -> QSpinBox:
        return self._spinboxes[index]

    def __iter__(self) -> Iterator[QSpinBox]:
        return iter(self._spinboxes)

    def value(self) -> list[float]:
        return [spinbox.value() for spinbox in self._spinboxes]


class TaskControlsWidget(QWidget):
    """
    Task control widget showing run, forward step, stop, pause, unpause buttons & a progress bar.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.play_pause_button = QPushButton(QIcon(ICON_RUN), "", parent=self)
        self.play_pause_button.setFixedWidth(self.play_pause_button.sizeHint().height())
        self.play_pause_button.setToolTip("Run Process")
        self.play_pause_button.setEnabled(False)

        self.progressbar = ProgressBar(self)

        self.preview_button = QPushButton(QIcon(ICON_EYE), "", parent=self)
        self.preview_button.setFixedWidth(self.preview_button.sizeHint().height())
        self.preview_button.setToolTip("Preview")
        self.preview_button.setEnabled(False)

        self.info_button = QPushButton(QIcon(ICON_INFO), "", parent=self)
        self.info_button.setFixedWidth(self.play_pause_button.sizeHint().height())
        self.info_button.setToolTip("Info")
        self.info_button.setEnabled(False)

        layout = QHBoxLayout()
        layout.addWidget(self.play_pause_button)
        layout.addWidget(self.progressbar, stretch=1)
        layout.addWidget(self.info_button)
        layout.addWidget(self.preview_button)
        layout.addStretch()

        self.setLayout(layout)
