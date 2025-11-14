from enum import Enum, auto
from collections.abc import Iterator
import numpy as np
import time
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QDoubleSpinBox, QSpinBox, QComboBox, QPushButton, QLabel, QProgressBar, QGridLayout, QSpacerItem, QSizePolicy, QToolTip, QRadioButton, QButtonGroup, QCheckBox
from PySide6.QtCore import Signal, Slot, Qt
from PySide6.QtGui import QIcon, QCursor

from ..device import Device, Stream
from ..device.camera import Camera
from ..device.modulator import Modulator
from ..device.mirror import Mirror
from ..widget.figure_widget import FigureWidget, SourceFigureWidget, WavefrontFigureWidget, MirrorFigureWidget, ModulatorFigureWidget, PhaseModulationFigureWidget, AmpModulationFigureWidget, SpeckleNullFigureWidget
from ..widget.resource import ICON_RUN, ICON_STEP_FORWARD, ICON_PAUSE, ICON_UNPAUSE, ICON_DISK, ICON_STOP, ICON_PRINT, ICON_EYE, ICON_UP_ARROW, ICON_DOWN_ARROW, ICON_LEFT_ARROW, ICON_RIGHT_ARROW
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
        kinds: tuple[Stream.Kind, ...]
            Kind of devices out of the list to show, specify multiple kinds to show devices of multiple kinds.

    Function:
        showPopup()
            Overridden pop up function will show only device options of a given kind.
    """

    def __init__(self, devices: dict[str, Device], types: tuple[type], parent=None):
        super().__init__(parent)
        self._devices = devices
        self._types = types

    def showPopup(self):  # pylint: disable=C0103:invalid-name
        super().blockSignals(True)

        self.clear()

        for key, device in self._devices.items():
            if isinstance(device, self._types):
                self.addItem(key)
        self.setCurrentIndex(-1)

        super().showPopup()

        super().blockSignals(False)


class DevicesSetupWidget(QWidget):
    """
    Devices setup widget, with two comboboxes for sink devices and source devices.

    Parameters:
        devices: list[Device]
            list of devices to show.
        setup_sink: bool = True
            Show the sink selection combobox
        setup_source: bool = True
            Show the source selection combobox
        setup_source_settings: bool = True,
            Show the source settings button?

    Signals:
        sink_change: Signal()
            Signal changing the sink.

        source_change: Signal()
            Signal changing the source.
    """

    sink_change = Signal(Device)
    source_change = Signal(Device)

    def __init__(self, devices: dict[str, Device], setup_sink: bool = True, setup_source: bool = True, parent=None):
        super().__init__(parent)
        self._devices = devices
        self._setup_sink = setup_sink
        self._setup_source = setup_source
        # self._setup_source_settings = setup_source_settings

        sink_device_label = QLabel("Sink", self)
        sink_device_label.hide()

        sink_device_combobox = DevicesComboBox(self._devices, (Modulator,), self)
        sink_device_combobox.setToolTip("Required")
        sink_device_combobox.hide()

        @Slot(str)
        def on_sink_device_select(key: str):
            self.sink_change.emit(self._devices[key])

        sink_device_combobox.currentTextChanged.connect(on_sink_device_select)

        self.sink_preview_button = QPushButton(QIcon(ICON_EYE), "")
        self.sink_preview_button.setFixedWidth(self.sink_preview_button.sizeHint().height())
        self.sink_preview_button.setToolTip("Sink Preview")

        # source_device_settings_button = QPushButton("")
        # source_device_settings_button.setFixedWidth(source_device_settings_button.sizeHint().height())
        # source_device_settings_button.setIcon(QIcon(ICON_GEAR))
        # source_device_settings_button.setToolTip("Capture Stream Settings")
        # source_device_settings_button.setEnabled(False)
        # source_device_settings_button.hide()

        source_device_label = QLabel("Source")
        source_device_label.setFixedWidth(100)
        source_device_label.hide()

        source_device_combobox = DevicesComboBox(self._devices, (Camera,), self)
        source_device_combobox.setToolTip("Required")
        source_device_combobox.hide()

        @Slot(str)
        def on_source_device_select(key: str):
            self.source_change.emit(self._devices[key])

        source_device_combobox.currentTextChanged.connect(on_source_device_select)

        self.source_preview_button = QPushButton(QIcon(ICON_EYE), "")
        self.source_preview_button.setFixedWidth(self.source_preview_button.sizeHint().height())
        self.source_preview_button.setToolTip("Source Preview")

        layout = QGridLayout()

        row = 0
        col = 0

        if self._setup_sink:
            sink_device_label.show()
            layout.addWidget(sink_device_label, row, col)
            col += 1
            sink_device_combobox.show()
            layout.addWidget(sink_device_combobox, row, col)
            col += 1
            layout.addWidget(self.sink_preview_button, row, col)

        if self._setup_source:
            row += 1
            col = 0
            source_device_label.show()
            layout.addWidget(source_device_label, row, col)
            col += 1
            source_device_combobox.show()
            layout.addWidget(source_device_combobox, row, col)
            col += 1
            layout.addWidget(self.source_preview_button, row, col)

        self.setLayout(layout)


class ProgressBar(QWidget):
    def __init__(self, parent=None):
        super(ProgressBar, self).__init__(parent)
        grid = QGridLayout()

        self.time = 0
        self.bar = QProgressBar()
        self.label = QLabel("")
        self.label.setAlignment(Qt.AlignCenter)
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

    def update(self):
        if self.bar.maximum() == 0:
            self.bar.setFormat("")
            self.label.setText(f"Step {self.bar.value()} - {time.strftime('%H:%M:%S', time.gmtime(self.time))}")
        else:
            self.bar.setFormat(f"Step {self.bar.value()} of {self.bar.maximum()} - {time.strftime('%H:%M:%S', time.gmtime(self.time))}")  # pylint: disable=W1405:inconsistent-quotes
            self.label.setText("")


# class LinspaceWidget(QWidget):
#     """
#     Widget with a start, stop double spinboxes and a count spinbox.

#     Function:
#         value(): np.ndarray
#             Array of np.linspace values.
#     """

#     valueChanged = Signal(np.ndarray)

#     def __init__(self, start: float = 0, stop: float = 100, steps: int = 2, parent=None):
#         super().__init__(parent)

#         self._start_spinbox = QDoubleSpinBox(self)
#         self._start_spinbox.setMinimum(-999)
#         self._start_spinbox.setMaximum(999)
#         self._start_spinbox.setDecimals(2)
#         self._start_spinbox.setToolTip("Start")
#         self._start_spinbox.setValue(start)
#         self._start_spinbox.valueChanged.connect(self._on_value_changed)

#         self._stop_spinbox = QDoubleSpinBox(self)
#         self._stop_spinbox.setMinimum(-999)
#         self._stop_spinbox.setMaximum(999)
#         self._stop_spinbox.setDecimals(2)
#         self._stop_spinbox.setToolTip("Stop")
#         self._stop_spinbox.setValue(stop)
#         self._stop_spinbox.valueChanged.connect(self._on_value_changed)

#         self._num_spinbox = QSpinBox(self)
#         self._num_spinbox.setMinimum(1)
#         self._num_spinbox.setToolTip("Number of steps")
#         self._num_spinbox.setValue(steps)
#         self._num_spinbox.valueChanged.connect(self._on_value_changed)

#         self._help_button = QPushButton("?", self)
#         self._help_button.setFixedWidth(self._help_button.sizeHint().height())
#         self._help_button.clicked.connect(lambda: QToolTip.showText(QCursor.pos(), f"{np.array2string(self.value(), precision=4, separator=', ')}"))

#         layout = QHBoxLayout()
#         layout.addWidget(self._start_spinbox)
#         layout.addWidget(self._stop_spinbox)
#         layout.addWidget(self._num_spinbox)
#         layout.addWidget(self._help_button, alignment=Qt.AlignmentFlag.AlignLeft)

#         layout.setContentsMargins(0, 0, 0, 0)

#         self.setLayout(layout)

#     def value(self) -> np.ndarray:
#         return np.linspace(self._start_spinbox.value(), self._stop_spinbox.value(), self._num_spinbox.value())

#     @Slot()
#     def _on_value_changed(self):
#         """Slot that emits the current linspace array when any spinbox changes."""
#         self.valueChanged.emit(self.value())


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

    rotation_change = Signal(Rotation)
    flip_change = Signal(Flip)

    def __init__(self, rotation: Rotation = Rotation.UP, flip: Flip = Flip.NEG, parent=None):
        super().__init__(parent)
        self.rotate_buttons = {
            Rotation.UP: QRadioButton("0\u00b0"),
            Rotation.RIGHT: QRadioButton("90\u00b0"),
            Rotation.DOWN: QRadioButton("180\u00b0"),
            Rotation.LEFT: QRadioButton("270\u00b0"),
        }
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
    def _on_rotation_changed(self, id_):
        mapping = [Rotation.UP, Rotation.RIGHT, Rotation.DOWN, Rotation.LEFT]
        self._rotation = mapping[id_]
        self.rotation_change.emit(self._rotation)

    @Slot()
    def _on_flip_change(self, state):
        self._flip = Flip.POS if state else Flip.NEG
        self.flip_change.emit(self._flip)

    # --- getters / setters ---
    def get_flip(self) -> Flip:
        return self._flip

    def set_flip(self, _flip: Flip):
        self._flip = _flip
        self.flip_checkbox.setChecked(_flip == Flip.POS)

    def get_rotation(self) -> Rotation:
        return self._rotation

    def set_rotation(self, _rotation: Rotation):
        self._rotation = _rotation
        self.rotate_buttons[_rotation].setChecked(True)


class SquareROIWidget(QWidget):
    roi_move = Signal(int, int)  # (dx, dy)

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
        self.roi_move.emit(dx, dy)

    def set_roi(self, roi):
        br, tl = roi["br"], roi["tl"]
        self.value_label.setText(f"[({br[0]}, {br[1]}),({tl[0]}, {tl[1]})]")


class ROIWidget(QWidget):
    roi_move = Signal(int, int)  # (dx, dy)

    def __init__(self, _roi: dict[str, tuple[int, int]], step:int=8, parent=None):
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

        self.set_roi(_roi)

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

    def _emit_moved(self, _dx: int, _dy: int):
        self.roi_move.emit(_dx, _dy)

    def set_roi(self, _roi: dict[str, tuple[int, int]]):
        br, tl = _roi["br"], _roi["tl"]
        self.value_label.setText(f"[({br[0]}, {br[1]}),({tl[0]}, {tl[1]})]")


class CenterWidget(QWidget):
    center_move = Signal(int, int)  # (dx, dy)

    def __init__(self, _center: tuple[int, int], step:int=8, parent=None):
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

        self.set_center(_center)

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
        self.center_move.emit(dx, dy)

    def set_center(self, _center: tuple[int, int]):
        self.value_label.setText(f"({_center[0]}, {_center[1]})")


class ValueSetWidget(QWidget):
    value_set = Signal(int)

    def __init__(self, _value: int, parent=None):
        super().__init__(parent)
        self.spinbox = QSpinBox(self)
        self.spinbox.setValue(_value)
        self.spinbox.setFixedWidth(75)

        self.pushbutton = QPushButton("Set", self)
        self.pushbutton.setFixedWidth(75)

        self.label = QLabel("", self)
        self.label.setText(f"{_value}")

        layout = QHBoxLayout()
        layout.addWidget(self.spinbox)
        layout.addWidget(self.pushbutton)
        layout.addWidget(self.label)
        layout.addItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum))
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.pushbutton.clicked.connect(lambda: self._emit_clicked(self.spinbox.value()))

    def _emit_clicked(self, _value: int):
        self.value_set.emit(_value)

    def setValue(self, _value: int):
        self.label.setText(f"{_value}")


class DoubleValueSetWidget(QWidget):
    value_set = Signal(float)

    def __init__(self, _value: float, parent=None):
        super().__init__(parent)
        self.spinbox = QDoubleSpinBox(self)
        self.spinbox.setValue(_value)
        self.spinbox.setFixedWidth(75)

        self.pushbutton = QPushButton("Set", self)
        self.pushbutton.setFixedWidth(75)

        self.label = QLabel("", self)
        self.label.setText(f"{_value}")

        layout = QHBoxLayout()
        layout.addWidget(self.spinbox)
        layout.addWidget(self.pushbutton)
        layout.addWidget(self.label)
        layout.addItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum))
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.pushbutton.clicked.connect(lambda: self._emit_clicked(self.spinbox.value()))

    def _emit_clicked(self, _value: float):
        self.value_set.emit(_value)

    def setValue(self, _value: float):
        self.label.setText(f"{_value}")


# class ExposureTimeArrayWidget(QWidget):
#     """
#     Exposure time array widget with add and remove step buttons.

#     Parameter:
#         value: int = 10
#             1st Exposure time of the array.

#     Function:
#         value(): list[int]
#             list of Exposure times (us).
#     """

#     def __init__(self, value: int = 10, parent=None):
#         super().__init__(parent)

#         self._layout = QVBoxLayout()
#         self._layout.setContentsMargins(0, 0, 0, 0)

#         spinbox = QSpinBox()
#         spinbox.setRange(0, 300000000)
#         spinbox.setFixedWidth(100)
#         spinbox.setSuffix(" us")
#         spinbox.setValue(value)
#         spinbox.setToolTip("Exposure time in us (maximum 5min)")
#         self._spinboxes = [spinbox]
#         self._layout_steps(self._layout, self._spinboxes)
#         self.setLayout(self._layout)

#     def _layout_steps(self, parent_layout: QVBoxLayout, spinboxes: list[QSpinBox]):
#         """Layout a spinbox with a label and a +/- button

#         Parameters:
#             values: list[int]
#                 Exposure time values list
#         """
#         for index, spinbox in enumerate(spinboxes):
#             exp_time_label = QLabel(f"Exp Time Step {index + 1}", self)
#             button = QPushButton("", self)
#             button.setFixedWidth(button.sizeHint().height())
#             step_layout = QHBoxLayout()
#             step_layout.addWidget(exp_time_label)
#             step_layout.addWidget(spinbox)
#             step_layout.addWidget(button)
#             if index == 0:
#                 button.setText("+")
#                 button.clicked.connect(lambda: self._on_add_step(self._spinboxes[-1].value()))
#             else:
#                 button.setText("-")
#                 button.clicked.connect(lambda: self._on_remove_step(index))
#             parent_layout.addLayout(step_layout)

#     def clear_layout(self, layout: QVBoxLayout):
#         while layout.count():
#             item = layout.takeAt(0)  # Get the first item
#             widget = item.widget()  # Get the widget from the item
#             if isinstance(widget, (QLabel, QPushButton)):  # if button or label
#                 widget.deleteLater()  # delete it
#             else:  # If the item is a layout, recursively clear it
#                 sub_layout = item.layout()
#                 if sub_layout:
#                     self.clear_layout(sub_layout)

#     def _on_add_step(self, value):
#         spinbox = QSpinBox()
#         spinbox.setRange(0, 300000000)
#         spinbox.setFixedWidth(100)
#         spinbox.setSuffix(" us")
#         spinbox.setValue(value)
#         self._spinboxes.append(spinbox)
#         self.clear_layout(self._layout)
#         self._layout_steps(self._layout, self._spinboxes)

#     def _on_remove_step(self, index):
#         self._spinboxes[index].deleteLater()
#         self._spinboxes.pop(index)
#         self.clear_layout(self._layout)
#         self._layout_steps(self._layout, self._spinboxes)

#     def __getitem__(self, index) -> QSpinBox:
#         return self._spinboxes[index]

#     def __iter__(self) -> Iterator[QSpinBox]:
#         return iter(self._spinboxes)

#     def value(self) -> list[int]:
#         return [spinbox.value() for spinbox in self._spinboxes]


class TaskControlsWidget(QWidget):
    """
    Task control widget showing run, forward step, stop, pause, unpause buttons & a progress bar.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.play_pause_button = QPushButton("", self)
        self.play_pause_button.setFixedWidth(self.play_pause_button.sizeHint().height())
        self.play_pause_button.setIcon(QIcon(ICON_RUN))
        self.play_pause_button.setToolTip("Run Process")
        # self.play_pause_button.setEnabled(False)
        # self.play_pause_button.hide()

        self.progressbar = ProgressBar(self)
        # self.progressbar.hide()

        layout = QHBoxLayout()
        layout.addWidget(self.play_pause_button)
        layout.addWidget(self.progressbar, stretch=1)
        layout.addStretch()

        self.setLayout(layout)


# class PreviewControlsWidget(QWidget):
#     """
#     Preview controls widget showing a slider to switch between frames.

#     Signal:
#         valueChanged: Signal(int)
#             Signal changing value.
#     """

#     valueChanged = Signal(int)

#     def __init__(self, label: str = "Frame", parent=None):
#         super().__init__(parent)

#         self.label = QLabel(label, self)
#         self.label.setFixedWidth(100)

#         self.spinbox = QSpinBox(self)
#         self.spinbox.setFixedWidth(75)
#         self.spinbox.setMinimum(0)
#         self.spinbox.setSingleStep(1)
#         self.spinbox.setToolTip(f"{label} Number")
#         self.setMaximum = self.spinbox.setMaximum
#         self.setValue = self.spinbox.setValue
#         self.spinbox.valueChanged.connect(self.valueChanged)

#         prev_spacer = QSpacerItem(10, 10, QSizePolicy.Expanding, QSizePolicy.Maximum)

#         layout = QHBoxLayout()

#         layout.addWidget(self.label)
#         layout.addWidget(self.spinbox)
#         layout.addItem(prev_spacer)

#         self.setLayout(layout)


# class DataPreviewWidget(QWidget):
#     """
#     Preview widget with figures for a capture and a command.

#     Functions:
#         init_source_preview_widget(source: Camera)
#             Function to initialize the source plot size.

#         init_sink_preview_widget(sink: Union[DeformableMirror | SpatialLightModulator])
#             Function to initialize the sink plot size.
#     """

#     def __init__(self, parent=None):
#         super().__init__(parent)

#         layout = QVBoxLayout()
#         self.figure_layout = QHBoxLayout()

#         self._sink_figure_widget = QWidget()
#         self._source_figure_widget = QWidget()

#         self.control_widget = PreviewControlsWidget("Frame", self)
#         self.control_widget.hide()

#         self.figure_layout.addWidget(self._sink_figure_widget)
#         self.figure_layout.addWidget(self._source_figure_widget)

#         layout.addLayout(self.figure_layout)
#         layout.addWidget(self.control_widget)

#         self.setLayout(layout)

#     def init_sink_preview_widget(self, sink: Mirror | Modulator):
#         if isinstance(self._sink_figure_widget, FigureWidget):
#             self._sink_figure_widget.figure.close()
#         self._sink_figure_widget.deleteLater()
#         if type(sink) is DeformableMirror:
#             self._sink_figure_widget = MirrorFigureWidget(sink, False, self)
#         else:
#             self._sink_figure_widget = ModulatorFigureWidget(sink, False, self)
#         self.figure_layout.insertWidget(0, self._sink_figure_widget)

#     def init_source_preview_widget(self, source: Camera):
#         if isinstance(self._source_figure_widget, FigureWidget):
#             self._source_figure_widget.figure.close()
#         self._source_figure_widget.deleteLater()
#         self._source_figure_widget = SourceFigureWidget(source, False, self)
#         self.figure_layout.insertWidget(1, self._source_figure_widget)


# class SpeckleModulationWidget(QWidget):
#     def __init__(self, parent=None):
#         super().__init__(parent)

#         layout = QVBoxLayout()
#         self.figure_layout = QVBoxLayout()

#         self.phase_figure_widget = QWidget()
#         self.amplitude_figure_widget = QWidget()

#         self.figure_layout.addWidget(self.phase_figure_widget)
#         self.figure_layout.addWidget(self.amplitude_figure_widget)

#         layout.addLayout(self.figure_layout)

#         self.setLayout(layout)

#     def init_phase_plot_widget(self, phases: np.ndarray):
#         if isinstance(self.phase_figure_widget, FigureWidget):
#             self.phase_figure_widget.figure.close()
#         self.phase_figure_widget.deleteLater()
#         self.phase_figure_widget = PhaseModulationFigureWidget(False, self)
#         self.figure_layout.insertWidget(0, self.phase_figure_widget)

#     def init_amplitude_plot_widget(self, amplitudes: np.ndarray):
#         if isinstance(self.amplitude_figure_widget, FigureWidget):
#             self.amplitude_figure_widget.figure.close()
#         self.amplitude_figure_widget.deleteLater()
#         self.amplitude_figure_widget = AmpModulationFigureWidget(False, self)
#         self.figure_layout.insertWidget(1, self.amplitude_figure_widget)


# class SpeckleNullPreviewWidget(QWidget):
#     def __init__(self, parent=None):
#         super().__init__(parent)

#         layout = QVBoxLayout()
#         self.figure_layout = QHBoxLayout()

#         self.speckle_null_figure_widget = QWidget()

#         self.control_widget = PreviewControlsWidget("Wavefront", self)
#         self.control_widget.hide()

#         self.figure_layout.addWidget(self.speckle_null_figure_widget)

#         layout.addLayout(self.figure_layout)
#         layout.addWidget(self.control_widget)

#         self.setLayout(layout)

#     def init_speckle_null_preview_widget(self, source: Camera, sink: Mirror | Modulator, phs_array: np.ndarray, amp_array: np.ndarray):
#         if isinstance(self.speckle_null_figure_widget, FigureWidget):
#             self.speckle_null_figure_widget.figure.close()
#         self.speckle_null_figure_widget.deleteLater()
#         self.speckle_null_figure_widget = SpeckleNullFigureWidget(source.blank, sink.blank, phs_array, amp_array, False, self)
#         self.figure_layout.insertWidget(0, self.speckle_null_figure_widget)


# class WavefrontPreviewWidget(QWidget):
#     """
#     Preview widget with a wavefront figure.

#     Functions:
#         init_wavefront_preview_widget(shape: Tuple[int, int])
#             Function to initialize the dotf plot size.
#     """

#     def __init__(self, parent=None):
#         super().__init__(parent)

#         layout = QVBoxLayout()
#         self.figure_layout = QHBoxLayout()

#         self.wavefront_figure_widget = QWidget()

#         self.control_widget = PreviewControlsWidget("Wavefront", self)
#         self.control_widget.hide()

#         self.figure_layout.addWidget(self.wavefront_figure_widget)

#         layout.addLayout(self.figure_layout)
#         layout.addWidget(self.control_widget)

#         self.setLayout(layout)

#     def init_wavefront_preview_widget(self, shape: Tuple[int, int]):
#         if isinstance(self.wavefront_figure_widget, FigureWidget):
#             self.wavefront_figure_widget.figure.close()
#         self.wavefront_figure_widget.deleteLater()
#         self.wavefront_figure_widget = WavefrontFigureWidget(shape, self)
#         self.figure_layout.insertWidget(0, self.wavefront_figure_widget)


# class CommandPreviewWidget(QWidget):
#     """
#     Preview widget with a sink figure.

#     Functions:
#         init_command_preview_widget(sink: Union[DeformableMirror | SpatialLightModulator]):
#             Function to initialize the dotf plot size.
#     """

#     def __init__(self, parent=None):
#         super().__init__(parent)

#         layout = QVBoxLayout()
#         self.figure_layout = QHBoxLayout()

#         self.command_figure_widget = QWidget()

#         self.control_widget = PreviewControlsWidget("Command", self)
#         self.control_widget.hide()

#         self.figure_layout.addWidget(self.command_figure_widget)

#         layout.addLayout(self.figure_layout)
#         layout.addWidget(self.control_widget)

#         self.setLayout(layout)

#     def init_command_preview_widget(self, sink: Mirror):
#         if isinstance(self.command_figure_widget, FigureWidget):
#             self.command_figure_widget.figure.close()
#         self.command_figure_widget.deleteLater()
#         self.command_figure_widget = MirrorFigureWidget(sink, self)
#         self.figure_layout.insertWidget(0, self.command_figure_widget)


# class CapturePreviewWidget(QWidget):
#     """
#     Preview widget with a source figure.

#     Functions:
#         init_wavefront_preview_widget(shape: Tuple[int, int])
#             Function to initialize the dotf plot size.
#     """

#     def __init__(self, parent=None):
#         super().__init__(parent)

#         layout = QVBoxLayout()
#         self.figure_layout = QHBoxLayout()

#         self._source_figure_widget = QWidget()

#         self.control_widget = PreviewControlsWidget("Capture", self)
#         self.control_widget.hide()

#         self.figure_layout.addWidget(self._source_figure_widget)

#         layout.addLayout(self.figure_layout)
#         layout.addWidget(self.control_widget)

#         self.setLayout(layout)

#     def init_capture_preview_widget(self, source: Camera):
#         if isinstance(self._source_figure_widget, FigureWidget):
#             self._source_figure_widget.figure.close()
#         self._source_figure_widget.deleteLater()
#         self._source_figure_widget = SourceFigureWidget(source, self)
#         self.figure_layout.insertWidget(0, self._source_figure_widget)
