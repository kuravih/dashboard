from collections.abc import Iterator, Callable
import numpy as np
import time
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QDoubleSpinBox, QSpinBox, QComboBox, QPushButton, QLabel, QProgressBar, QGridLayout, QSpacerItem, QSizePolicy, QToolTip, QRadioButton, QButtonGroup, QCheckBox, QLineEdit, QFileDialog, QMessageBox, QStyle
from PySide6.QtCore import Signal, Slot, Qt, QFileInfo, QSize
from PySide6.QtGui import QIcon, QCursor, QPixmap, QPainter, QColor

from ..device import Device
from ..device.camera import Camera
from ..device.modulator import Modulator
from ..widget.resource import ICON_RUN, ICON_EYE, ICON_UP_ARROW, ICON_DOWN_ARROW, ICON_LEFT_ARROW, ICON_RIGHT_ARROW, ICON_INFO, ICON_GEAR, ICON_FOLDER, ICON_BACKSPACE, ICON_PLUS, ICON_MINUS
from ..widget.dialog import MessageDialog
from ..function import Rotation, Flip, DOTFProbeDirection, PairwiseProbeDirection


class Window(QWidget):
    """Window class"""


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

        sink_device_label = QLabel("Sink", self)
        sink_device_label.hide()

        sink_device_combobox = DevicesComboBox(self.devices, (Modulator,), self)
        sink_device_combobox.setToolTip("Required")
        sink_device_combobox.hide()

        @Slot(str)
        def on_sink_device_select(key: str):
            self.sinkChanged.emit(self.devices[key])

        sink_device_combobox.currentTextChanged.connect(on_sink_device_select)

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

        layout = QGridLayout()

        row = 0
        col = 0

        if self.setup_sink:
            sink_device_label.show()
            layout.addWidget(sink_device_label, row, col)
            col += 1
            sink_device_combobox.show()
            layout.addWidget(sink_device_combobox, row, col)

        if self.setup_source:
            row += 1
            col = 0
            source_device_label.show()
            layout.addWidget(source_device_label, row, col)
            col += 1
            source_device_combobox.show()
            layout.addWidget(source_device_combobox, row, col)

        self.setLayout(layout)


class ProgressBar(QWidget):
    """
    Progress bar widget with time text
    """

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

        self.setValue = self.bar.setValue
        self.reset = self.bar.reset

    def setMaximum(self, maximum: int | None):
        if maximum is None:
            self.bar.setMaximum(-1)
        else:
            self.bar.setMaximum(maximum)

    def setTime(self, timeVal: float):
        self.time = timeVal

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

    Signals:
        valueChanged: Signal(np.ndarray)
            Signal changing values
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
        self.help_button.setFixedWidth(self.num_spinbox.sizeHint().height())
        self.help_button.setFixedHeight(self.num_spinbox.sizeHint().height())
        self.help_button.clicked.connect(lambda: QToolTip.showText(QCursor.pos(), f"{np.array2string(self.value(), precision=4, separator=', ')}"))

        layout = QHBoxLayout()
        layout.addWidget(self.start_spinbox, stretch=1)
        layout.addWidget(self.stop_spinbox, stretch=1)
        layout.addWidget(self.num_spinbox, stretch=1)
        layout.addWidget(self.help_button, alignment=Qt.AlignmentFlag.AlignRight)

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

    valueChanged = Signal(tuple)

    def __init__(self, count: int = 2, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self._spinboxes = []
        for _ in range(count):
            spinbox = QDoubleSpinBox(self)
            spinbox.valueChanged.connect(self._on_value_changed)
            self._spinboxes.append(spinbox)
            layout.addWidget(spinbox)

        layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(layout)

    @Slot(int)
    def _on_value_changed(self, _: int):
        self.valueChanged.emit(self.value())

    def __getitem__(self, index) -> QDoubleSpinBox:
        return self._spinboxes[index]

    def __iter__(self) -> Iterator[QDoubleSpinBox]:
        return iter(self._spinboxes)

    def value(self) -> tuple[float]:
        return tuple(spinbox.value() for spinbox in self._spinboxes)


class NSpinBoxesWidget(QWidget):
    """
    Widget with multiple spinboxes.

    Parameter:
        count: int = 2
            Number of spinboxes.

    Function:
        value(): tuple[int]
            tuple of values.
    """

    valueChanged = Signal(tuple)

    def __init__(self, count=2, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout()

        self._spinboxes = []
        for _ in range(count):
            spinbox = QSpinBox(self)
            spinbox.valueChanged.connect(self._on_value_changed)
            self._spinboxes.append(spinbox)
            layout.addWidget(spinbox)

        layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(layout)

    @Slot(int)
    def _on_value_changed(self, _: int):
        self.valueChanged.emit(self.value())

    def __getitem__(self, index) -> QSpinBox:
        return self._spinboxes[index]

    def __iter__(self) -> Iterator[QSpinBox]:
        return iter(self._spinboxes)

    def value(self) -> tuple[int, ...]:
        return tuple(spinbox.value() for spinbox in self._spinboxes)


class OrientationWidget(QWidget):
    """
    Widget for rotation and mirroring

    Parameter:
        rotation: Rotation = Rotation.UP
            Rotation radio buttons.
        flip: Flip = Flip.NEG
            Flip checkboxes

    Function:
        get_flip(self) -> Flip:
            flip

        set_flip(self, flip: Flip):
            set flip

        get_rotation(self) -> Rotation:
            get orientation

        set_rotation(self, rotation: Rotation):
            set orientation

    Signals:
        rotationChanged = Signal(Rotation)
            Signal changing rotation

        flipChanged = Signal(Flip)
            Signal changing flip
    """

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
    def _on_rotation_changed(self, index: int):
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


class ROIWidget(QWidget):
    """
    Widget for Region of interest

    Parameter:
        roi: dict[str, tuple[int, int]]
            Region of interest
        step: int = 8
            step

    Function:
        set_roi(self, roi: dict[str, tuple[int, int]])
            set roi

    Signals:
        roiMoveClicked = Signal(int, int)
            Signal moving roi

    """

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
        up_button = IconButton(QIcon(ICON_UP_ARROW), parent=self)
        up_button.setToolTip("Move ROI up")

        down_button = IconButton(QIcon(ICON_DOWN_ARROW), parent=self)
        down_button.setToolTip("Move ROI down")

        left_button = IconButton(QIcon(ICON_LEFT_ARROW), parent=self)
        left_button.setToolTip("Move ROI left")

        right_button = IconButton(QIcon(ICON_RIGHT_ARROW), parent=self)
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
    """
    Widget for center

    Parameter:
        center: tuple[int, int]
            center
        step: int = 8
            step size

    Function:
        set_center(self, center: tuple[int, int]):
            set center

    Signals:
        centerMoveClicked = Signal(int, int)
            Signal moving center

    """

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
        up_button = IconButton(QIcon(ICON_UP_ARROW), parent=self)
        up_button.setToolTip("Move ROI up")

        down_button = IconButton(QIcon(ICON_DOWN_ARROW), parent=self)
        down_button.setToolTip("Move ROI down")

        left_button = IconButton(QIcon(ICON_LEFT_ARROW), parent=self)
        left_button.setToolTip("Move ROI left")

        right_button = IconButton(QIcon(ICON_RIGHT_ARROW), parent=self)
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
    """
    Widget for changing an integer value

    Function:
        setValue(self, value: int):
            set value

    Signals:
        valueSetClicked = Signal(int)
            Signal changing value

    """

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
    """
    Widget for changing an float value

    Function:
        setValue(self, value: float):
            set value

    Signals:
        valueSetClicked = Signal(float)
            Signal changing value

    """

    valueSetClicked = Signal(float)

    def __init__(self, suffix: str = "", parent=None):
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
        spinbox.setToolTip("Exposure time in s (maximum 5min)")
        spinbox.setValue(value)
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
            # button = QPushButton("", self)
            button = IconButton(QIcon(ICON_PLUS), parent=self)
            # button.setFixedWidth(button.sizeHint().height())
            step_layout = QHBoxLayout()
            step_layout.addWidget(exp_time_label)
            step_layout.addWidget(spinbox)
            step_layout.addWidget(button)
            if index == 0:
                button.setIcon(QIcon(ICON_PLUS))
                button.clicked.connect(lambda: self._on_add_step(2 * self._spinboxes[-1].value()))
            else:
                button.setIcon(QIcon(ICON_MINUS))
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
        spinbox.setToolTip("Exposure time in s (maximum 5min)")
        spinbox.setValue(value)
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

        self.progressbar = ProgressBar(self)

        self.run_stop_button = IconButton(QIcon(ICON_RUN), parent=self)
        self.run_stop_button.setFixedHeight(self.progressbar.bar.sizeHint().height())
        self.run_stop_button.setFixedWidth(self.progressbar.bar.sizeHint().height())
        self.run_stop_button.setToolTip("Run Process")
        self.run_stop_button.setEnabled(False)

        self.preview_button = IconButton(QIcon(ICON_EYE), parent=self)
        self.preview_button.setFixedHeight(self.progressbar.bar.sizeHint().height())
        self.preview_button.setFixedWidth(self.progressbar.bar.sizeHint().height())
        self.preview_button.setToolTip("Preview")
        self.preview_button.setEnabled(False)

        self.info_button = IconButton(QIcon(ICON_INFO), parent=self)
        self.info_button.setFixedHeight(self.progressbar.bar.sizeHint().height())
        self.info_button.setFixedWidth(self.progressbar.bar.sizeHint().height())
        self.info_button.setToolTip("Info")
        self.info_button.setEnabled(False)

        layout = QHBoxLayout()
        layout.addWidget(self.run_stop_button)
        layout.addWidget(self.progressbar, stretch=1)
        layout.addWidget(self.info_button)
        layout.addWidget(self.preview_button)
        layout.addStretch()

        self.setLayout(layout)


class FileLoadWidget(QWidget):
    """
    File load widget
    """

    fileChanged = Signal()

    def __init__(self, caption: str = "", directory: str = ".", file_filter="", validator: Callable[[str], bool] = lambda _: True, parent=None):
        super().__init__(parent)
        self._validator = validator
        self.filepath: str | None = None

        self.file_lineedit = QLineEdit(self)
        self.file_lineedit.setEnabled(False)
        self.file_lineedit.setText("")
        self.file_lineedit.setToolTip("File")

        self.file_browse_button = IconButton(QIcon(ICON_FOLDER), parent=self)
        self.file_browse_button.setToolTip("Browse")

        self.file_clear_button = IconButton(QIcon(ICON_BACKSPACE), parent=self)
        self.file_clear_button.setToolTip("Clear")
        self.file_clear_button.hide()

        @Slot()
        def on_browse_clicked():
            dialog_filename, _ = QFileDialog.getOpenFileName(self, caption, directory, file_filter, options=QFileDialog.Option.DontUseNativeDialog | QFileDialog.Option.ReadOnly)
            if dialog_filename:
                file_info = QFileInfo(dialog_filename)
                filename = file_info.fileName()
                self.filepath = f"{file_info.absolutePath()}/{filename}"
                if validator(self.filepath):
                    self.file_lineedit.setText(filename)
                    self.file_browse_button.hide()
                    self.file_clear_button.show()
                    self.fileChanged.emit()
                else:
                    self.filepath = None
                    message_dialog = MessageDialog("Invalid Calibration", "File invalid.", icon=QMessageBox.Icon.Information, buttons=QMessageBox.StandardButton.Ok)
                    message_dialog.exec()

        self.file_browse_button.clicked.connect(on_browse_clicked)

        @Slot()
        def on_clear_clicked():
            self.filepath = None
            self.file_lineedit.setText("")
            self.file_browse_button.show()
            self.file_clear_button.hide()
            self.fileChanged.emit()

        self.file_clear_button.clicked.connect(on_clear_clicked)

        layout = QHBoxLayout()
        layout.addWidget(self.file_lineedit, stretch=1)
        layout.addWidget(self.file_browse_button, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.file_clear_button, alignment=Qt.AlignmentFlag.AlignRight)
        layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(layout)

    def setFilepath(self, filepath: str | None):
        if filepath is not None and not self._validator(filepath):
            return
        self.filepath = filepath
        self.file_lineedit.setText(self.filepath)
        if self.filepath is None:
            self.file_browse_button.show()
            self.file_clear_button.hide()
        else:
            self.file_browse_button.hide()
            self.file_clear_button.show()


class DOTFProbeDirectionWidget(QWidget):
    """
    Widget with four checkboxes for the four DOTF probes (03, 06, 09 & 12 o'clock).

    Function:
        value(): List[DOTFProbeDirection]
            List of DOTFProbeDirection.
    """

    valueChanged = Signal(list)  # emits List[DOTFProbeDirection]

    def __init__(self, exclusive: bool = False, parent=None):
        super().__init__(parent)

        self._exclusive = exclusive
        layout = QHBoxLayout()

        self._checkboxes: list[QCheckBox] = []

        for _direction in DOTFProbeDirection:
            checkbox = QCheckBox(_direction.to_str(), self)
            checkbox.setChecked(True)
            checkbox.toggled.connect(self._on_checkbox_toggled)
            self._checkboxes.append(checkbox)
            layout.addWidget(checkbox)

        if self._exclusive:
            # Start with only the first one checked
            for checkbox in self._checkboxes[1:]:
                checkbox.blockSignals(True)
                checkbox.setChecked(False)
                checkbox.blockSignals(False)

        layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(layout)

    def __getitem__(self, index) -> QCheckBox:
        return self._checkboxes[index]

    def __iter__(self) -> Iterator[QCheckBox]:
        return iter(self._checkboxes)

    def value(self) -> list[DOTFProbeDirection]:
        return [direction for checkbox, direction in zip(self._checkboxes, DOTFProbeDirection) if checkbox.isChecked()]

    def _on_checkbox_toggled(self, checked: bool):
        if self._exclusive:
            if not checked:
                # Prevent unchecking if it's the last one checked
                if not any(cb.isChecked() for cb in self._checkboxes):
                    sender = self.sender()
                    if isinstance(sender, QCheckBox):
                        sender.blockSignals(True)
                        sender.setChecked(True)
                        sender.blockSignals(False)
            else:
                # Uncheck all others
                sender = self.sender()
                for checkbox in self._checkboxes:
                    if checkbox is not sender:
                        checkbox.blockSignals(True)
                        checkbox.setChecked(False)
                        checkbox.blockSignals(False)
        else:
            if not any(cb.isChecked() for cb in self._checkboxes):
                sender = self.sender()
                if isinstance(sender, QCheckBox):
                    sender.blockSignals(True)
                    sender.setChecked(True)
                    sender.blockSignals(False)

        self.valueChanged.emit(self.value())


class PairwiseProbeDirectionWidget(QWidget):
    """
    Widget with four checkboxes for horizontal/vertical pairwise probes.

    Function:
        value(): List[PairwiseProbeDirection]
            List of PairwiseProbeDirection.
    """

    valueChanged = Signal(list)  # emits List[PairwiseProbeDirection]

    def __init__(self, exclusive: bool = False, parent=None):
        super().__init__(parent)

        self._exclusive = exclusive
        layout = QHBoxLayout()

        self._checkboxes: list[QCheckBox] = []

        for _direction in PairwiseProbeDirection:  # pylint: disable=invalid-name
            checkbox = QCheckBox(_direction.to_str(), self)
            checkbox.setChecked(True)
            checkbox.toggled.connect(self._on_checkbox_toggled)
            self._checkboxes.append(checkbox)
            layout.addWidget(checkbox)

        if self._exclusive:
            for checkbox in self._checkboxes[1:]:
                checkbox.blockSignals(True)
                checkbox.setChecked(False)
                checkbox.blockSignals(False)

        layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(layout)

    def __getitem__(self, index) -> QCheckBox:
        return self._checkboxes[index]

    def __iter__(self) -> Iterator[QCheckBox]:
        return iter(self._checkboxes)

    def value(self) -> list[PairwiseProbeDirection]:
        return [direction for checkbox, direction in zip(self._checkboxes, PairwiseProbeDirection) if checkbox.isChecked()]

    def _on_checkbox_toggled(self, checked: bool):
        if self._exclusive:
            if not checked:
                if not any(cb.isChecked() for cb in self._checkboxes):
                    sender = self.sender()
                    if isinstance(sender, QCheckBox):
                        sender.blockSignals(True)
                        sender.setChecked(True)
                        sender.blockSignals(False)
            else:
                sender = self.sender()
                for checkbox in self._checkboxes:
                    if checkbox is not sender:
                        checkbox.blockSignals(True)
                        checkbox.setChecked(False)
                        checkbox.blockSignals(False)
        else:
            if not any(cb.isChecked() for cb in self._checkboxes):
                sender = self.sender()
                if isinstance(sender, QCheckBox):
                    sender.blockSignals(True)
                    sender.setChecked(True)
                    sender.blockSignals(False)

        self.valueChanged.emit(self.value())


def _tint_pixmap(src: QPixmap, color: QColor) -> QPixmap:
    out = QPixmap(src.size())
    out.setDevicePixelRatio(src.devicePixelRatio())
    out.fill(Qt.GlobalColor.transparent)  # REQUIRED
    p = QPainter(out)
    p.drawPixmap(0, 0, src)
    p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    p.fillRect(out.rect(), color)
    p.end()
    return out


class IconButton(QPushButton):
    """
    A QPushButton whose icon is generated from a base QIcon and tinted
    for Normal/Disabled, using the button's current iconSize (or style default).
    """

    def __init__(self, base_icon: QIcon, normal_hex: str = "#FFFFFF", disabled_hex: str = "#555555", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._base_icon = base_icon
        self._normal = QColor(normal_hex)
        self._disabled = QColor(disabled_hex)
        self._last_size: QSize | None = None
        self._rebuild_icon()
        self.setFixedWidth(self.sizeHint().height())

    def setTintColors(self, normal_hex: str, disabled_hex: str) -> None:
        self._normal = QColor(normal_hex)
        self._disabled = QColor(disabled_hex)
        self._rebuild_icon(force=True)

    def setBaseIcon(self, base_icon: QIcon) -> None:
        self._base_icon = base_icon
        self._rebuild_icon(force=True)

    def _effective_icon_size(self) -> QSize:
        sz = self.iconSize()
        if not sz.isValid() or sz.isEmpty():
            px = self.style().pixelMetric(QStyle.PixelMetric.PM_SmallIconSize, None, self)
            sz = QSize(px, px)
        return sz

    def _rebuild_icon(self, force: bool = False) -> None:
        sz = self._effective_icon_size()
        if not force and self._last_size == sz:
            return
        self._last_size = QSize(sz)

        # Rasterize base icon at the current size (Qt will pick DPR for the target)
        src = self._base_icon.pixmap(sz, QIcon.Mode.Normal, QIcon.State.Off)

        icon = QIcon()
        icon.addPixmap(_tint_pixmap(src, self._normal), QIcon.Mode.Normal)
        icon.addPixmap(_tint_pixmap(src, self._disabled), QIcon.Mode.Disabled)

        self.setIcon(icon)

    def changeEvent(self, event):
        # Rebuild when style/palette/screen changes can affect icon sizes/DPR
        t = event.type()
        if t in (event.Type.EnabledChange, event.Type.StyleChange, event.Type.PaletteChange, event.Type.FontChange, event.Type.ScreenChangeInternal):
            self._rebuild_icon(force=(t == event.Type.EnabledChange))
        super().changeEvent(event)

    def resizeEvent(self, event):
        # If some code updates iconSize indirectly with layout changes, catch it
        self._rebuild_icon()
        super().resizeEvent(event)

    def setIconHint(self, icon: QIcon, hint: str):
        self.setIcon(icon)
        self.setToolTip(hint)
