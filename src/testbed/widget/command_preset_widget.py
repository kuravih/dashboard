import numpy as np
from astropy.io import fits  # type: ignore

from PySide6.QtWidgets import QWidget, QGridLayout, QDoubleSpinBox, QLabel, QSpinBox, QRadioButton, QPushButton, QLineEdit, QFileDialog, QSpacerItem, QSizePolicy, QHBoxLayout
from PySide6.QtCore import QFileInfo, Signal, Slot

from pykato.function import gradient, checkers, sinusoid, vortex, box, polka, register, text
from ..widget import NSpinBoxesWidget, NDoubleSpinBoxesWidget
from ..function import dotf_probe, DOTFProbeDirection, efc_probe, PairwiseProbeDirection


class ConstPresetWidget(QWidget):
    """Constant command preset widget

    Controls :
        const: float
            Constant value.
    """

    changed = Signal(np.ndarray)

    def param_change(self, shape: tuple[int, int], const: float) -> np.ndarray:
        return self._range * (np.zeros(shape=shape) + const)

    def widget_change(self, const_spinbox) -> np.ndarray:
        return self.param_change(self.shape, const_spinbox.value())

    @Slot()
    def on_value_changed(self):
        self.changed.emit(self.widget_change(self.const_spinbox))

    def setup_main_widget(self):
        const_label = QLabel("Constant", self)
        const_label.setFixedWidth(100)

        const_spinbox = QDoubleSpinBox(self)
        const_spinbox.setSingleStep(0.01)
        const_spinbox.setRange(0, 1.0)
        const_spinbox.valueChanged.connect(self.on_value_changed)

        layout = QGridLayout()

        row = 0
        col = 0
        layout.addWidget(const_label, row, col)
        col += 1
        layout.addWidget(const_spinbox, row, col)

        row += 1
        layout.setRowStretch(row, 1)

        self.setLayout(layout)

        self.const_spinbox = const_spinbox

    def __init__(self, shape: tuple[int, int], vlim: tuple[float, float], parent=None):
        super().__init__(parent)
        self._min, self._max = vlim
        self._range = self._max - self._min
        self.shape = shape
        self.setup_main_widget()

    @property
    def command(self) -> np.ndarray:
        return self.widget_change(self.const_spinbox)


class GradientPresetWidget(QWidget):
    """Gradient command preset widget

    Controls :
        grad: int
            Gradient.
        angle : tuple[int, int]
            Angle of gradient.
    """

    changed = Signal(np.ndarray)

    def param_change(self, shape: tuple[int, int], grad: int, angle: float) -> np.ndarray:
        return self._range * grad * (gradient(shape, angle) / 2 + 0.5)

    def widget_change(self, grad_spinbox, angle_spinbox) -> np.ndarray:
        return self.param_change(self.shape, grad_spinbox.value(), angle_spinbox.value())

    @Slot()
    def on_value_changed(self):
        self.changed.emit(self.widget_change(self.grad_spinbox, self.angle_spinbox))

    def setup_main_widget(self):
        grad_label = QLabel("Gradient", self)
        grad_label.setFixedWidth(100)

        grad_spinbox = QDoubleSpinBox(self)
        grad_spinbox.setSingleStep(0.01)
        grad_spinbox.setRange(0, 1.0)
        grad_spinbox.valueChanged.connect(self.on_value_changed)
        pv_label = QLabel("PV", self)

        angle_label = QLabel("Angle", self)

        angle_spinbox = QDoubleSpinBox(self)
        angle_spinbox.setFixedWidth(75)
        angle_spinbox.setRange(0.0, 360.0)
        angle_spinbox.setSingleStep(1.0)
        angle_spinbox.setValue(0.0)
        angle_spinbox.valueChanged.connect(self.on_value_changed)

        layout = QGridLayout()

        row = 0
        col = 0
        layout.addWidget(grad_label, row, col)
        col += 1
        layout.addWidget(grad_spinbox, row, col)
        col += 1
        layout.addWidget(pv_label, row, col)

        row += 1
        col = 0
        layout.addWidget(angle_label, row, col)
        col += 1
        layout.addWidget(angle_spinbox, row, col)

        row += 1
        layout.setRowStretch(row, 1)

        self.setLayout(layout)

        self.grad_spinbox = grad_spinbox
        self.angle_spinbox = angle_spinbox

    def __init__(self, shape: tuple[int, int], vlim: tuple[float, float], parent=None):
        super().__init__(parent)
        self._min, self._max = vlim
        self._range = self._max - self._min
        self.shape = shape
        self.setup_main_widget()

    @property
    def command(self) -> np.ndarray:
        return self.widget_change(self.grad_spinbox, self.angle_spinbox)


class CheckerPresetWidget(QWidget):
    """Checker pattern command preset widget.

    Controls :
        amplitude: float
            Amplitude of the checker.
        size : tuple[int, int]
            Checker size.
        offset: tuple[int, int] = (0, 0)
            Origin offset.
    """

    changed = Signal(np.ndarray)

    def param_change(self, shape: tuple[int, int], amplitude: float, size: tuple[int, int], offset: tuple[int, int]) -> np.ndarray:
        return self._range * amplitude * checkers(shape, size, offset)

    def widget_change(self, amplitude_spinbox, size_spinboxes, offset_spinboxes) -> np.ndarray:
        size = size_spinboxes.value()
        offset_x_spinbox, offset_y_spinbox = offset_spinboxes
        offset_x_spinbox.setRange(-self.shape[0] - size[0], size[0])
        offset_y_spinbox.setRange(-self.shape[1] - size[1],size[1])
        return self.param_change(self.shape, amplitude_spinbox.value(), size, offset_spinboxes.value())

    @Slot()
    def on_value_changed(self):
        self.changed.emit(self.widget_change(self.amplitude_spinbox, self.size_spinboxes, self.offset_spinboxes))

    def setup_main_widget(self, shape: tuple[int, int]):
        amplitude_label = QLabel("Amplitude", self)
        amplitude_label.setFixedWidth(100)

        self.amplitude_spinbox = QDoubleSpinBox(self)
        self.amplitude_spinbox.setFixedWidth(75)
        self.amplitude_spinbox.setRange(0.0, 1.0)
        self.amplitude_spinbox.setSingleStep(0.1)
        self.amplitude_spinbox.setValue(0.5)
        self.amplitude_spinbox.valueChanged.connect(self.on_value_changed)

        size_label = QLabel("Size", self)

        self.size_spinboxes = NSpinBoxesWidget(2, self)
        size_x_spinbox, size_y_spinbox = self.size_spinboxes

        size_x_spinbox.setFixedWidth(75)
        size_x_spinbox.setRange(0, shape[0])
        size_x_spinbox.setValue(shape[0] // 2)
        size_x_spinbox.valueChanged.connect(self.on_value_changed)

        size_y_spinbox.setFixedWidth(75)
        size_y_spinbox.setRange(0, shape[1])
        size_y_spinbox.setValue(shape[1] // 2)
        size_y_spinbox.valueChanged.connect(self.on_value_changed)

        size_spacer = QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        size_layout = QHBoxLayout()
        size_layout.addWidget(self.size_spinboxes)
        size_layout.addItem(size_spacer)

        offset_label = QLabel("Offset", self)

        self.offset_spinboxes = NSpinBoxesWidget(2, self)
        offset_x_spinbox, offset_y_spinbox = self.offset_spinboxes

        offset_x_spinbox.setFixedWidth(75)
        offset_x_spinbox.setRange(-size_x_spinbox.value() // 2, size_x_spinbox.value() // 2)
        offset_x_spinbox.setValue(shape[0] // 4)
        offset_x_spinbox.valueChanged.connect(self.on_value_changed)

        offset_y_spinbox.setFixedWidth(75)
        offset_y_spinbox.setRange(-size_y_spinbox.value() // 2, size_y_spinbox.value() // 2)
        offset_y_spinbox.setValue(shape[1] // 4)
        offset_y_spinbox.valueChanged.connect(self.on_value_changed)

        offset_spacer = QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        offset_layout = QHBoxLayout()
        offset_layout.addWidget(self.offset_spinboxes)
        offset_layout.addItem(offset_spacer)

        layout = QGridLayout()

        row = 0
        col = 0
        layout.addWidget(amplitude_label, row, col)
        col += 1
        layout.addWidget(self.amplitude_spinbox, row, col, 1, 2)

        row += 1
        col = 0
        layout.addWidget(size_label, row, col)
        col += 1
        layout.addLayout(size_layout, row, col)

        row += 1
        col = 0
        layout.addWidget(offset_label, row, col)
        col += 1
        layout.addLayout(offset_layout, row, col)

        row += 1
        layout.setRowStretch(row, 1)

        self.setLayout(layout)

    def __init__(self, shape: tuple[int, int], vlim: tuple[float, float], parent=None):
        super().__init__(parent)
        self._min, self._max = vlim
        self._range = self._max - self._min
        self.shape = shape
        self.setup_main_widget(shape)

    @property
    def command(self) -> np.ndarray:
        return self.widget_change(self.amplitude_spinbox, self.size_spinboxes, self.offset_spinboxes)


class SinusoidPresetWidget(QWidget):
    """
    Sinusoid pattern command preset widget

    Controls :
        period : float
            Period of the sinusoid in pixels.
        phase : float
            Phase of the sinusoid in degrees.
        angle : float
            Angle of the sinusoid in degrees.
        mean : float
            Mean of the sinusoid.
    """

    changed = Signal(np.ndarray)

    def param_change(self, shape: tuple[int, int], amplitude: float, mean: float, period: float, phase: float, angle: float) -> np.ndarray:
        return self._range * (amplitude * sinusoid(shape, period, np.deg2rad(phase), np.deg2rad(angle)) + mean)

    def widget_change(self, amplitude_spinbox, mean_spinbox, period_spinbox, phase_spinbox, angle_spinbox) -> np.ndarray:
        return self.param_change(self.shape, amplitude_spinbox.value(), mean_spinbox.value(), period_spinbox.value(), phase_spinbox.value(), angle_spinbox.value())

    @Slot()
    def on_value_changed(self):
        self.changed.emit(self.widget_change(self.amplitude_spinbox, self.mean_spinbox, self.period_spinbox, self.phase_spinbox, self.angle_spinbox))

    def setup_main_widget(self, shape: tuple[int, int]):
        amplitude_label = QLabel("Amplitude", self)
        amplitude_label.setFixedWidth(100)

        self.amplitude_spinbox = QDoubleSpinBox(self)
        self.amplitude_spinbox.setFixedWidth(75)
        self.amplitude_spinbox.setRange(0.0, 1.0)
        self.amplitude_spinbox.setSingleStep(0.1)
        self.amplitude_spinbox.setValue(0.1)
        self.amplitude_spinbox.setToolTip("Amplitude of the sinusoid")

        mean_label = QLabel("Mean", self)

        self.mean_spinbox = QDoubleSpinBox(self)
        self.mean_spinbox.setFixedWidth(75)
        self.mean_spinbox.setSingleStep(0.1)
        self.mean_spinbox.setMinimum(0.0)
        self.mean_spinbox.setValue(0.5)
        self.mean_spinbox.setToolTip("Mean of the sinusoid")

        period_label = QLabel("Period", self)

        self.period_spinbox = QDoubleSpinBox(self)
        self.period_spinbox.setFixedWidth(75)
        self.period_spinbox.setRange(0.0, shape[0])
        self.period_spinbox.setSingleStep(1.0)
        self.period_spinbox.setValue(20)
        self.period_spinbox.setToolTip("Period of the sinusoid")
        self.period_spinbox.valueChanged.connect(self.on_value_changed)

        phase_label = QLabel("Phase", self)

        self.phase_spinbox = QDoubleSpinBox(self)
        self.phase_spinbox.setFixedWidth(75)
        self.phase_spinbox.setRange(0.0, 360.0)
        self.phase_spinbox.setSingleStep(5.0)
        self.phase_spinbox.setValue(0.0)
        phase_label.setToolTip("Phase of the sinusoid")
        self.phase_spinbox.valueChanged.connect(self.on_value_changed)

        angle_label = QLabel("Angle", self)

        self.angle_spinbox = QDoubleSpinBox(self)
        self.angle_spinbox.setFixedWidth(75)
        self.angle_spinbox.setRange(0.0, 360.0)
        self.angle_spinbox.setSingleStep(1.0)
        self.angle_spinbox.setValue(45)
        self.angle_spinbox.setToolTip("Angle of the sinusoid")
        self.angle_spinbox.valueChanged.connect(self.on_value_changed)

        @Slot(float)
        def amplitude_change(amplitude):
            self.mean_spinbox.setRange(amplitude / 2.0, 1.0 - amplitude / 2.0)
            return self.on_value_changed()

        self.amplitude_spinbox.valueChanged.connect(amplitude_change)

        @Slot(float)
        def mean_change(mean):
            if mean > 0.5:
                self.amplitude_spinbox.setMaximum(1 - mean)
            elif mean < 0.5:
                self.amplitude_spinbox.setMaximum(mean)
            else:
                self.amplitude_spinbox.setMaximum(0.5)
            return self.on_value_changed()

        self.mean_spinbox.valueChanged.connect(mean_change)

        layout = QGridLayout()

        row = 0
        col = 0
        layout.addWidget(amplitude_label, row, col)
        col += 1
        layout.addWidget(self.amplitude_spinbox, row, col, 1, 2)

        row += 1
        col = 0
        layout.addWidget(mean_label, row, col)
        col += 1
        layout.addWidget(self.mean_spinbox, row, col)

        row += 1
        col = 0
        layout.addWidget(period_label, row, col)
        col += 1
        layout.addWidget(self.period_spinbox, row, col)

        row += 1
        col = 0
        layout.addWidget(phase_label, row, col)
        col += 1
        layout.addWidget(self.phase_spinbox, row, col)

        row += 1
        col = 0
        layout.addWidget(angle_label, row, col)
        col += 1
        layout.addWidget(self.angle_spinbox, row, col)

        row += 1
        layout.setRowStretch(row, 1)

        self.setLayout(layout)

    def __init__(self, shape: tuple[int, int], vlim: tuple[float, float], parent=None):
        super().__init__(parent)
        self._min, self._max = vlim
        self._range = self._max - self._min
        self.shape = shape
        self.setup_main_widget(shape)

    @property
    def command(self) -> np.ndarray:
        return self.widget_change(self.amplitude_spinbox, self.mean_spinbox, self.period_spinbox, self.phase_spinbox, self.angle_spinbox)


class VortexPresetWidget(QWidget):
    """
    Vortex pattern command preset widget

    Controls :
        amplitude: float
            Amplitude of the checker.
        charge : int
            Charge of the vortex.
    """

    changed = Signal(np.ndarray)

    def param_change(self, shape: tuple[int, int], amplitude: float, charge: int) -> np.ndarray:
        return self._range * amplitude * vortex(shape, charge)

    def widget_change(self, amplitude_spinbox, charge_spinbox) -> np.ndarray:
        return self.param_change(self.shape, amplitude_spinbox.value(), charge_spinbox.value())

    @Slot()
    def on_value_changed(self):
        self.changed.emit(self.widget_change(self.amplitude_spinbox, self.charge_spinbox))

    def setup_main_widget(self):
        amplitude_label = QLabel("Amplitude", self)
        amplitude_label.setFixedWidth(100)

        self.amplitude_spinbox = QDoubleSpinBox(self)
        self.amplitude_spinbox.setFixedWidth(75)
        self.amplitude_spinbox.setRange(0.0, 1.0)
        self.amplitude_spinbox.setSingleStep(0.1)
        self.amplitude_spinbox.setValue(0.5)
        self.amplitude_spinbox.valueChanged.connect(self.on_value_changed)

        charge_label = QLabel("Charge", self)

        self.charge_spinbox = QSpinBox(self)
        self.charge_spinbox.setMinimum(0)
        self.charge_spinbox.setValue(2)
        self.charge_spinbox.valueChanged.connect(self.on_value_changed)

        layout = QGridLayout()

        row = 0
        col = 0
        layout.addWidget(amplitude_label, row, col)
        col += 1
        layout.addWidget(self.amplitude_spinbox, row, col, 1, 2)

        row += 1
        col = 0
        layout.addWidget(charge_label, row, col)
        col += 1
        layout.addWidget(self.charge_spinbox, row, col)

        row += 1
        layout.setRowStretch(row, 1)

        self.setLayout(layout)

    def __init__(self, shape: tuple[int, int], vlim: tuple[float, float], parent=None):
        super().__init__(parent)
        self._min, self._max = vlim
        self._range = self._max - self._min
        self.shape = shape
        self.setup_main_widget()

    @property
    def command(self) -> np.ndarray:
        return self.widget_change(self.amplitude_spinbox, self.charge_spinbox)


class BoxPresetWidget(QWidget):
    """
    Box pattern command preset widget

    Controls :
        amplitude: float
            Amplitude of the checker.
        size : tuple[int, int]
            Checker size.
        Center: tuple[int, int] = (0, 0)
            Center.

    """

    changed = Signal(np.ndarray)

    def param_change(self, shape: tuple[int, int], amplitude: float, size: tuple[int, int], center: tuple[int, int]) -> np.ndarray:
        return self._range * amplitude * box(shape, size, center)

    def widget_change(self, amplitude_spinbox, size_spinboxes, center_spinboxes) -> np.ndarray:
        size = tuple(size_spinbox.value() for size_spinbox in size_spinboxes)
        center_x_spinbox, center_y_spinbox = center_spinboxes
        center_x_spinbox.setRange(-self.shape[0] - size[0], size[0])
        center_y_spinbox.setRange(-self.shape[1] - size[1], size[1])
        return self.param_change(self.shape, amplitude_spinbox.value(), size, (center_x_spinbox.value(), center_y_spinbox.value()))

    @Slot()
    def on_value_changed(self):
        self.changed.emit(self.widget_change(self.amplitude_spinbox, self.size_spinboxes, self.center_spinboxes))

    def setup_main_widget(self, shape: tuple[int, int]):
        amplitude_label = QLabel("Amplitude", self)
        amplitude_label.setFixedWidth(100)

        self.amplitude_spinbox = QDoubleSpinBox(self)
        self.amplitude_spinbox.setFixedWidth(75)
        self.amplitude_spinbox.setRange(0.0, 1.0)
        self.amplitude_spinbox.setSingleStep(0.001)
        self.amplitude_spinbox.setValue(0.5)
        self.amplitude_spinbox.setDecimals(3)
        self.amplitude_spinbox.valueChanged.connect(self.on_value_changed)

        size_label = QLabel("Size", self)

        self.size_spinboxes = NSpinBoxesWidget(2, self)
        size_x_spinbox, size_y_spinbox = self.size_spinboxes

        size_x_spinbox.setFixedWidth(75)
        size_x_spinbox.setRange(0, shape[0])
        size_x_spinbox.setValue(shape[0] // 4)
        size_x_spinbox.valueChanged.connect(self.on_value_changed)

        size_y_spinbox.setFixedWidth(75)
        size_y_spinbox.setRange(0, shape[1])
        size_y_spinbox.setValue(shape[1] // 4)
        size_y_spinbox.valueChanged.connect(self.on_value_changed)

        size_spacer = QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        size_layout = QHBoxLayout()
        size_layout.addWidget(self.size_spinboxes)
        size_layout.addItem(size_spacer)

        center_label = QLabel("Center", self)

        self.center_spinboxes = NSpinBoxesWidget(2, self)
        center_x_spinbox, center_y_spinbox = self.center_spinboxes

        center_x_spinbox.setFixedWidth(75)
        center_x_spinbox.setRange(-shape[0] // 2 - size_x_spinbox.value(), shape[0] // 2 + size_x_spinbox.value())
        center_x_spinbox.setValue(-shape[0] // 2)
        center_x_spinbox.valueChanged.connect(self.on_value_changed)

        center_y_spinbox.setFixedWidth(75)
        center_y_spinbox.setRange(-shape[1] // 2 - size_y_spinbox.value(), shape[1] // 2 + size_y_spinbox.value())
        center_y_spinbox.setValue(-shape[1] // 2)
        center_y_spinbox.valueChanged.connect(self.on_value_changed)

        center_spacer = QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        center_layout = QHBoxLayout()
        center_layout.addWidget(self.center_spinboxes)
        center_layout.addItem(center_spacer)

        layout = QGridLayout()

        row = 0
        col = 0
        layout.addWidget(amplitude_label, row, col)
        col += 1
        layout.addWidget(self.amplitude_spinbox, row, col, 1, 2)

        row += 1
        col = 0
        layout.addWidget(size_label, row, col)
        col += 1
        layout.addLayout(size_layout, row, col)

        row += 1
        col = 0
        layout.addWidget(center_label, row, col)
        col += 1
        layout.addLayout(center_layout, row, col)

        row += 1
        layout.setRowStretch(row, 1)

        self.setLayout(layout)

    def __init__(self, shape: tuple[int, int], vlim: tuple[float, float], parent=None):
        super().__init__(parent)
        self._min, self._max = vlim
        self._range = self._max - self._min
        self.shape = shape
        self.setup_main_widget(shape)

    @property
    def command(self) -> np.ndarray:
        return self.widget_change(self.amplitude_spinbox, self.size_spinboxes, self.center_spinboxes)


class PolkaPresetWidget(QWidget):
    """
    Polka dot pattern command preset widget

    Controls :
        amplitude: float
            Amplitude of the dots.
        radius: float
            Polka dot radius.
        Center: tuple[int, int] = (0, 0)
            Center.
    """

    changed = Signal(np.ndarray)

    def param_change(self, shape: tuple[int, int], amplitude: float, radius: float, spacing: tuple[int, int], offset: tuple[int, int]) -> np.ndarray:
        return self._range * amplitude * polka(shape, radius, spacing, offset)

    def widget_change(self, amplitude_spinbox, radius_spinbox, spacing_spinboxes, offset_spinboxes) -> np.ndarray:
        spacing = tuple(spacing_spinbox.value() for spacing_spinbox in spacing_spinboxes)
        offset_x_spinbox, offset_y_spinbox = offset_spinboxes
        offset_x_spinbox.setRange(-self.shape[0] - spacing[0], spacing[0])
        offset_y_spinbox.setRange(-self.shape[1] - spacing[1], spacing[1])
        return self.param_change(self.shape, amplitude_spinbox.value(), radius_spinbox.value(), spacing, (offset_x_spinbox.value(), offset_y_spinbox.value()))

    @Slot()
    def on_value_changed(self):
        self.changed.emit(self.widget_change(self.amplitude_spinbox, self.radius_spinbox, self.spacing_spinboxes, self.offset_spinboxes))

    def setup_main_widget(self, shape: tuple[int, int]):
        amplitude_label = QLabel("Amplitude", self)
        amplitude_label.setFixedWidth(100)

        self.amplitude_spinbox = QDoubleSpinBox(self)
        self.amplitude_spinbox.setFixedWidth(75)
        self.amplitude_spinbox.setRange(0.0, 1.0)
        self.amplitude_spinbox.setSingleStep(0.1)
        self.amplitude_spinbox.setValue(0.5)
        self.amplitude_spinbox.valueChanged.connect(self.on_value_changed)

        radius_label = QLabel("Radius", self)

        self.radius_spinbox = QDoubleSpinBox(self)
        self.radius_spinbox.setFixedWidth(75)
        self.radius_spinbox.setValue(4)
        self.radius_spinbox.valueChanged.connect(self.on_value_changed)

        spacing_label = QLabel("Spacing", self)

        self.spacing_spinboxes = NDoubleSpinBoxesWidget(2, self)
        spacing_x_spinbox, spacing_y_spinbox = self.spacing_spinboxes

        spacing_x_spinbox.setFixedWidth(75)
        spacing_x_spinbox.setRange(0, shape[0])
        spacing_x_spinbox.setValue(shape[0] / 8)
        spacing_x_spinbox.valueChanged.connect(self.on_value_changed)

        spacing_y_spinbox.setFixedWidth(75)
        spacing_y_spinbox.setRange(0, shape[1])
        spacing_y_spinbox.setValue(shape[1] / 8)
        spacing_y_spinbox.valueChanged.connect(self.on_value_changed)

        spacing_spacer = QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        spacing_layout = QHBoxLayout()
        spacing_layout.addWidget(self.spacing_spinboxes)
        spacing_layout.addItem(spacing_spacer)

        offset_label = QLabel("Offset", self)

        self.offset_spinboxes = NDoubleSpinBoxesWidget(2, self)
        offset_x_spinbox, offset_y_spinbox = self.offset_spinboxes

        offset_x_spinbox.setFixedWidth(75)
        offset_x_spinbox.setRange(-spacing_x_spinbox.value() / 2, spacing_x_spinbox.value() / 2)
        offset_x_spinbox.setValue(-shape[0] / 16)
        offset_x_spinbox.valueChanged.connect(self.on_value_changed)

        offset_y_spinbox.setFixedWidth(75)
        offset_y_spinbox.setRange(-spacing_y_spinbox.value() / 2, spacing_y_spinbox.value() / 2)
        offset_y_spinbox.setValue(-shape[1] / 16)
        offset_y_spinbox.valueChanged.connect(self.on_value_changed)

        offset_spacer = QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        offset_layout = QHBoxLayout()
        offset_layout.addWidget(self.offset_spinboxes)
        offset_layout.addItem(offset_spacer)

        layout = QGridLayout()

        row = 0
        col = 0
        layout.addWidget(amplitude_label, row, col)
        col += 1
        layout.addWidget(self.amplitude_spinbox, row, col, 1, 2)

        row += 1
        col = 0
        layout.addWidget(radius_label, row, col)
        col += 1
        layout.addWidget(self.radius_spinbox, row, col)

        row += 1
        col = 0
        layout.addWidget(spacing_label, row, col)
        col += 1
        layout.addLayout(spacing_layout, row, col)

        row += 1
        col = 0
        layout.addWidget(offset_label, row, col)
        col += 1
        layout.addLayout(offset_layout, row, col)

        row += 1
        layout.setRowStretch(row, 1)

        self.setLayout(layout)

    def __init__(self, shape: tuple[int, int], vlim: tuple[float, float], parent=None):
        super().__init__(parent)
        self._min, self._max = vlim
        self._range = self._max - self._min
        self.shape = shape
        self.setup_main_widget(shape)

    @property
    def command(self) -> np.ndarray:
        return self.widget_change(self.amplitude_spinbox, self.radius_spinbox, self.spacing_spinboxes, self.offset_spinboxes)


class RegisterPresetWidget(QWidget):
    """
    Registration dot pattern command preset widget

    Controls :
        amplitude: float
            Amplitude of the dots.
        radius: float
            Dot radius.
        count: tuple[int, int]
            Number of dots along the horizontal and vertical
        Center: tuple[int, int] = (0, 0)
            Center.
    """

    changed = Signal(np.ndarray)

    def param_change(self, shape: tuple[int, int], amplitude: float, count: tuple[int, int], radius: float, spacing: tuple[int, int], center: tuple[int, int]) -> np.ndarray:
        return self._range * amplitude * register(shape, count, radius, spacing, center)

    def widget_change(self, amplitude_spinbox, count_spinboxes, radius_spinbox, spacing_spinboxes, center_spinboxes) -> np.ndarray:
        count = tuple(count_spinbox.value() for count_spinbox in count_spinboxes)
        spacing = tuple(spacing_spinbox.value() for spacing_spinbox in spacing_spinboxes)
        center = tuple(center_spinbox.value() for center_spinbox in center_spinboxes)
        return self.param_change(self.shape, amplitude_spinbox.value(), count, radius_spinbox.value(), spacing, center)

    @Slot()
    def on_value_changed(self):
        self.changed.emit(self.widget_change(self.amplitude_spinbox, self.count_spinboxes, self.radius_spinbox, self.spacing_spinboxes, self.center_spinboxes))

    def setup_main_widget(self, shape: tuple[int, int]):
        amplitude_label = QLabel("Amplitude", self)
        amplitude_label.setFixedWidth(100)

        self.amplitude_spinbox = QDoubleSpinBox(self)
        self.amplitude_spinbox.setFixedWidth(75)
        self.amplitude_spinbox.setRange(0.0, 1.0)
        self.amplitude_spinbox.setSingleStep(0.1)
        self.amplitude_spinbox.setValue(0.5)
        self.amplitude_spinbox.valueChanged.connect(self.on_value_changed)

        count_label = QLabel("Count", self)

        self.count_spinboxes = NSpinBoxesWidget(2, self)
        count_x_spinbox, count_y_spinbox = self.count_spinboxes

        count_x_spinbox.setFixedWidth(75)
        count_x_spinbox.setRange(1, 20)
        count_x_spinbox.setValue(6)
        count_x_spinbox.valueChanged.connect(self.on_value_changed)

        count_y_spinbox.setFixedWidth(75)
        count_y_spinbox.setRange(1, 20)
        count_y_spinbox.setValue(6)
        count_y_spinbox.valueChanged.connect(self.on_value_changed)

        count_spacer = QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        count_layout = QHBoxLayout()
        count_layout.addWidget(self.count_spinboxes)
        count_layout.addItem(count_spacer)

        radius_label = QLabel("Radius", self)

        self.radius_spinbox = QDoubleSpinBox(self)
        self.radius_spinbox.setFixedWidth(75)
        self.radius_spinbox.setValue(4)
        self.radius_spinbox.valueChanged.connect(self.on_value_changed)

        spacing_label = QLabel("Spacing", self)

        self.spacing_spinboxes = NDoubleSpinBoxesWidget(2, self)
        spacing_x_spinbox, spacing_y_spinbox = self.spacing_spinboxes

        spacing_x_spinbox.setFixedWidth(75)
        spacing_x_spinbox.setRange(0, shape[0])
        spacing_x_spinbox.setValue(shape[0] / 8)
        spacing_x_spinbox.valueChanged.connect(self.on_value_changed)

        spacing_y_spinbox.setFixedWidth(75)
        spacing_y_spinbox.setRange(0, shape[1])
        spacing_y_spinbox.setValue(shape[1] / 8)
        spacing_y_spinbox.valueChanged.connect(self.on_value_changed)

        spacing_spacer = QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        spacing_layout = QHBoxLayout()
        spacing_layout.addWidget(self.spacing_spinboxes)
        spacing_layout.addItem(spacing_spacer)

        center_label = QLabel("Center", self)

        self.center_spinboxes = NDoubleSpinBoxesWidget(2, self)
        center_x_spinbox, center_y_spinbox = self.center_spinboxes

        center_x_spinbox.setFixedWidth(75)
        center_x_spinbox.setRange(0, shape[0])
        center_x_spinbox.setValue(shape[0] // 2)
        center_x_spinbox.valueChanged.connect(self.on_value_changed)

        center_y_spinbox.setFixedWidth(75)
        center_y_spinbox.setRange(0, shape[1])
        center_y_spinbox.setValue(shape[1] // 2)
        center_y_spinbox.valueChanged.connect(self.on_value_changed)

        center_spacer = QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        center_layout = QHBoxLayout()
        center_layout.addWidget(self.center_spinboxes)
        center_layout.addItem(center_spacer)

        layout = QGridLayout()

        row = 0
        col = 0
        layout.addWidget(amplitude_label, row, col)
        col += 1
        layout.addWidget(self.amplitude_spinbox, row, col, 1, 2)

        row += 1
        col = 0
        layout.addWidget(count_label, row, col)
        col += 1
        layout.addLayout(count_layout, row, col)

        row += 1
        col = 0
        layout.addWidget(radius_label, row, col)
        col += 1
        layout.addWidget(self.radius_spinbox, row, col)

        row += 1
        col = 0
        layout.addWidget(spacing_label, row, col)
        col += 1
        layout.addLayout(spacing_layout, row, col)

        row += 1
        col = 0
        layout.addWidget(center_label, row, col)
        col += 1
        layout.addLayout(center_layout, row, col)

        row += 1
        layout.setRowStretch(row, 1)

        self.setLayout(layout)

    def __init__(self, shape: tuple[int, int], vlim: tuple[float, float], parent=None):
        super().__init__(parent)
        self._min, self._max = vlim
        self._range = self._max - self._min
        self.shape = shape
        self.setup_main_widget(shape)

    @property
    def command(self) -> np.ndarray:
        return self.widget_change(self.amplitude_spinbox, self.count_spinboxes, self.radius_spinbox, self.spacing_spinboxes, self.center_spinboxes)


class DOTFPresetWidget(QWidget):
    """
    DOTF probe pattern command preset widget

    Controls :
        amplitude: float
            Amplitude of the dots.
        size : tuple[int, int]
            Checker size.
        direction: DOTFProbeDirection
            Direction of the dotf probe.
    """

    changed = Signal(np.ndarray)

    def param_change(self, shape: tuple[int, int], amplitude: float, size: tuple[int, int], direction: DOTFProbeDirection) -> np.ndarray:
        return self._range * amplitude * dotf_probe(shape, size, direction)

    def widget_change(self, amplitude_spinbox, size_spinboxes, direction_radiobuttons) -> np.ndarray:
        size = tuple(size_spinbox.value() for size_spinbox in size_spinboxes)
        selected_direction = tuple(direction for direction, radiobutton in zip(list(DOTFProbeDirection), direction_radiobuttons) if radiobutton.isChecked())
        return self.param_change(self.shape, amplitude_spinbox.value(), size, selected_direction[0])

    @Slot()
    def on_value_changed(self):
        self.changed.emit(self.widget_change(self.amplitude_spinbox, self.size_spinboxes, self.direction_radiobuttons))

    def setup_main_widget(self, shape: tuple[int, int]):
        amplitude_label = QLabel("Amplitude", self)
        amplitude_label.setFixedWidth(100)

        self.amplitude_spinbox = QDoubleSpinBox(self)
        self.amplitude_spinbox.setFixedWidth(75)
        self.amplitude_spinbox.setRange(0.0, 1.0)
        self.amplitude_spinbox.setSingleStep(0.1)
        self.amplitude_spinbox.setValue(0.5)
        self.amplitude_spinbox.valueChanged.connect(self.on_value_changed)

        size_label = QLabel("Size", self)

        self.size_spinboxes = NSpinBoxesWidget(2, self)
        size_l_spinbox, size_w_spinbox = self.size_spinboxes

        size_l_spinbox.setFixedWidth(75)
        size_l_spinbox.setRange(0, shape[0])
        size_l_spinbox.setValue(11)
        size_l_spinbox.valueChanged.connect(self.on_value_changed)

        size_w_spinbox.setFixedWidth(75)
        size_w_spinbox.setRange(0, shape[1])
        size_w_spinbox.setValue(4)
        size_w_spinbox.valueChanged.connect(self.on_value_changed)

        size_spacer = QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        size_layout = QHBoxLayout()
        size_layout.addWidget(self.size_spinboxes)
        size_layout.addItem(size_spacer)

        direction_label = QLabel("Direction", self)

        direction_right_radiobutton = QRadioButton(DOTFProbeDirection.RIGHT.to_str(), self)
        direction_right_radiobutton.setFixedWidth(75)
        direction_right_radiobutton.setChecked(True)
        direction_right_radiobutton.clicked.connect(self.on_value_changed)

        direction_bottom_radiobutton = QRadioButton(DOTFProbeDirection.BOTTOM.to_str(), self)
        direction_bottom_radiobutton.setFixedWidth(75)
        direction_bottom_radiobutton.setChecked(False)
        direction_bottom_radiobutton.clicked.connect(self.on_value_changed)

        direction_left_radiobutton = QRadioButton(DOTFProbeDirection.LEFT.to_str(), self)
        direction_left_radiobutton.setFixedWidth(75)
        direction_left_radiobutton.setChecked(False)
        direction_left_radiobutton.clicked.connect(self.on_value_changed)

        direction_top_radiobutton = QRadioButton(DOTFProbeDirection.TOP.to_str(), self)
        direction_top_radiobutton.setFixedWidth(75)
        direction_top_radiobutton.setChecked(False)
        direction_top_radiobutton.clicked.connect(self.on_value_changed)

        direction_spacer = QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        direction_layout = QHBoxLayout()
        direction_layout.addWidget(direction_right_radiobutton)
        direction_layout.addWidget(direction_bottom_radiobutton)
        direction_layout.addWidget(direction_left_radiobutton)
        direction_layout.addWidget(direction_top_radiobutton)
        direction_layout.addItem(direction_spacer)

        layout = QGridLayout()

        row = 0
        col = 0
        layout.addWidget(amplitude_label, row, col)
        col += 1
        layout.addWidget(self.amplitude_spinbox, row, col, 1, 2)

        row += 1
        col = 0
        layout.addWidget(size_label, row, col)
        col += 1
        layout.addLayout(size_layout, row, col)

        row += 1
        col = 0
        layout.addWidget(direction_label, row, col)
        col += 1
        layout.addLayout(direction_layout, row, col)

        row += 1
        layout.setRowStretch(row, 1)

        self.setLayout(layout)

        self.direction_radiobuttons = (direction_right_radiobutton, direction_bottom_radiobutton, direction_left_radiobutton, direction_top_radiobutton)

    def __init__(self, shape: tuple[int, int], vlim: tuple[float, float], parent=None):
        super().__init__(parent)
        self._min, self._max = vlim
        self._range = self._max - self._min
        self.shape = shape
        self.setup_main_widget(shape)

    @property
    def command(self) -> np.ndarray:
        return self.widget_change(self.amplitude_spinbox, self.size_spinboxes, self.direction_radiobuttons)


class FilePresetWidget(QWidget):  # TODO: fix this, closing the stream window causes crash
    """
    Command file preset widget
    """

    changed = Signal(np.ndarray)

    def param_change(self) -> np.ndarray:
        return self._range * self._command

    def widget_change(self) -> np.ndarray:
        return self.param_change()

    @Slot()
    def on_value_changed(self):
        self.changed.emit(self.widget_change())

    def setup_main_widget(self):
        command_file_label = QLabel("File", self)
        command_file_label.setFixedWidth(100)

        command_file_lineedit = QLineEdit(self)
        command_file_lineedit.setEnabled(False)

        browse_command_file_button = QPushButton("Browse", self)
        # browse_command_file_button.clicked.connect(browse_cmd_file)
        browse_command_file_button.setFixedWidth(75)

        command_file_layout = QHBoxLayout()
        command_file_layout.addWidget(command_file_lineedit)
        command_file_layout.addWidget(browse_command_file_button)

        wavelength_label = QLabel("Wavelength", self)

        wavelength_spinbox = QDoubleSpinBox(self)
        wavelength_spinbox.setRange(0.0, 1000.0)
        wavelength_spinbox.setValue(633.0)
        wavelength_spinbox.setFixedWidth(75)

        flip_label = QLabel("Flip", self)

        flip_lr_button = QPushButton("↔", self)
        flip_lr_button.setFixedWidth(40)

        flip_ud_button = QPushButton("↕", self)
        flip_ud_button.setFixedWidth(40)

        spacer = QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        flip_layout = QHBoxLayout()
        flip_layout.addWidget(flip_lr_button)
        flip_layout.addWidget(flip_ud_button)
        flip_layout.addItem(spacer)

        rotate_label = QLabel("Rotate", self)
        rotate_ccw_button = QPushButton("↶", self)
        rotate_ccw_button.setFixedWidth(40)

        rotate_cw_button = QPushButton("↷", self)
        rotate_cw_button.setFixedWidth(40)

        rotate_layout = QHBoxLayout()
        rotate_layout.addWidget(rotate_ccw_button)
        rotate_layout.addWidget(rotate_cw_button)
        rotate_layout.addItem(spacer)

        sign_label = QLabel("Sign", self)
        flip_sign_button = QPushButton("Flip", self)
        flip_sign_button.setFixedWidth(75)

        layout = QGridLayout()

        row = 0
        col = 0
        layout.addWidget(command_file_label, row, col)
        col += 1
        layout.addLayout(command_file_layout, row, col)

        row += 1
        col = 0
        layout.addWidget(wavelength_label, row, col)
        col += 1
        layout.addWidget(wavelength_spinbox, row, col)

        row += 1
        col = 0
        layout.addWidget(flip_label, row, col)
        col += 1
        layout.addLayout(flip_layout, row, col)

        row += 1
        col = 0
        layout.addWidget(rotate_label, row, col)
        col += 1
        layout.addLayout(rotate_layout, row, col)

        row += 1
        col = 0
        layout.addWidget(sign_label, row, col)
        col += 1
        layout.addWidget(flip_sign_button, row, col)

        row += 1
        layout.setRowStretch(row, 1)

        self.setLayout(layout)

        self.command_file_lineedit = command_file_lineedit

        @Slot()
        def browse_cmd_file():
            dialog_filename, _ = QFileDialog.getOpenFileName(self, "Open Command", ".", "Command File (*.fits)", options=QFileDialog.Option.DontUseNativeDialog | QFileDialog.Option.ReadOnly)
            if dialog_filename:
                cmd_file_info = QFileInfo(dialog_filename)
                self.command_file_lineedit.setText(cmd_file_info.fileName())
                with fits.open(cmd_file_info.fileName()) as hdul:
                    if hdul[0].header["UNIT"] == "nm":
                        self._command = hdul[0].data / self.wavelength_spinbox.value()
                    elif hdul[0].header["UNIT"] == "adu":
                        self._command = hdul[0].data
                    elif hdul[0].header["UNIT"] == "rad":
                        self._command = np.nan_to_num(hdul[0].data / np.pi)
                    elif hdul[0].header["UNIT"] == "voltage":
                        self._command = hdul[0].data
                self.on_value_changed()

        @Slot()
        def flip_cmd_lr():
            self._command = np.fliplr(self._command)
            self.on_value_changed()

        flip_lr_button.clicked.connect(flip_cmd_lr)

        @Slot()
        def flip_cmd_ud():
            self._command = np.flipud(self._command)
            self.on_value_changed()

        flip_ud_button.clicked.connect(flip_cmd_ud)

        @Slot()
        def rotate_cmd_ccw():
            self._command = np.rot90(self._command, k=-1)
            self.on_value_changed()

        rotate_ccw_button.clicked.connect(rotate_cmd_ccw)

        @Slot()
        def rotate_cmd_cw():
            self._command = np.rot90(self._command, k=-1)
            self.on_value_changed()

        rotate_cw_button.clicked.connect(rotate_cmd_cw)

        @Slot()
        def flip_cmd_sign():
            self._command = -self._command
            self.on_value_changed()

        flip_sign_button.clicked.connect(flip_cmd_sign)

    def __init__(self, shape: tuple[int, int], vlim: tuple[float, float], parent=None):
        super().__init__(parent)
        self._min, self._max = vlim
        self._range = self._max - self._min
        self.shape = shape
        self._command = np.zeros(self.shape)
        self.setup_main_widget()

    @property
    def command(self) -> np.ndarray:
        return self.widget_change()


class EFCPresetWidget(QWidget):
    """
    EFC probe pattern command preset widget
    """

    changed = Signal(np.ndarray)

    def param_change(self, shape: tuple[int, int], amplitude: float, dξ: float, dη: float, ξc: float, θ: float, direction: PairwiseProbeDirection) -> np.ndarray:  # pylint: disable=invalid-name,non-ascii-name
        return self._range * amplitude * efc_probe(shape, dξ, dη, ξc, θ, direction)

    def widget_change(self, amplitude_spinbox, dξ_spinbox, dη_spinbox, ξc_spinbox, θ_spinbox, direction_radiobuttons) -> np.ndarray:  # pylint: disable=invalid-name,non-ascii-name
        selected_direction = tuple(direction for direction, radiobutton in zip(list(PairwiseProbeDirection), direction_radiobuttons) if radiobutton.isChecked())
        return self.param_change(self.shape, amplitude_spinbox.value(), dξ_spinbox.value(), dη_spinbox.value(), ξc_spinbox.value(), θ_spinbox.value(), selected_direction[0])

    def direction_widget_change(self, amplitude_spinbox, dξ_spinbox, dη_spinbox, ξc_spinbox, θ_spinbox, direction_radiobuttons) -> np.ndarray:  # pylint: disable=invalid-name,non-ascii-name
        return self.widget_change(amplitude_spinbox, dξ_spinbox, dη_spinbox, ξc_spinbox, θ_spinbox, direction_radiobuttons)

    @Slot()
    def emit_parameter_change(self):
        self.changed.emit(self.widget_change(self.amplitude_spinbox, self.dξ_spinbox, self.dη_spinbox, self.ξc_spinbox, self.θ_spinbox, self.direction_radiobuttons))

    @Slot()
    def emit_direction_change(self):
        self.changed.emit(self.direction_widget_change(self.amplitude_spinbox, self.dξ_spinbox, self.dη_spinbox, self.ξc_spinbox, self.θ_spinbox, self.direction_radiobuttons))

    def setup_main_widget(self, shape: tuple[int, int]):
        amplitude_label = QLabel("Amplitude", self)
        amplitude_label.setFixedWidth(100)

        self.amplitude_spinbox = QDoubleSpinBox(self)
        self.amplitude_spinbox.setFixedWidth(75)
        self.amplitude_spinbox.setRange(0.0, 1.0)
        self.amplitude_spinbox.setSingleStep(0.1)
        self.amplitude_spinbox.setValue(0.5)
        self.amplitude_spinbox.setToolTip("Probe box amplitude")
        self.amplitude_spinbox.valueChanged.connect(self.emit_parameter_change)

        dξ_label = QLabel("dξ", self)  # pylint: disable=invalid-name,non-ascii-name

        self.dξ_spinbox = QDoubleSpinBox(self)  # pylint: disable=invalid-name,non-ascii-name
        self.dξ_spinbox.setFixedWidth(75)
        self.dξ_spinbox.setMinimum(0.0)
        self.dξ_spinbox.setSingleStep(0.001)
        self.dξ_spinbox.setDecimals(3)
        self.dξ_spinbox.setValue(0.008)
        self.dξ_spinbox.setToolTip("Probe box width\n(higher the value wider the box)")
        self.dξ_spinbox.valueChanged.connect(self.emit_parameter_change)

        dη_label = QLabel("dη", self)  # pylint: disable=invalid-name,non-ascii-name

        self.dη_spinbox = QDoubleSpinBox(self)  # pylint: disable=invalid-name,non-ascii-name
        self.dη_spinbox.setFixedWidth(75)
        self.dη_spinbox.setMinimum(0.0)
        self.dη_spinbox.setSingleStep(0.001)
        self.dη_spinbox.setDecimals(3)
        self.dη_spinbox.setValue(0.018)
        self.dη_spinbox.setToolTip("Probe box height\n(higher the value taller the box)")
        self.dη_spinbox.valueChanged.connect(self.emit_parameter_change)

        ξc_label = QLabel("ξc", self)  # pylint: disable=invalid-name,non-ascii-name

        self.ξc_spinbox = QDoubleSpinBox(self)  # pylint: disable=invalid-name,non-ascii-name
        self.ξc_spinbox.setFixedWidth(75)
        self.ξc_spinbox.setRange(1.0, shape[0])
        self.ξc_spinbox.setSingleStep(1.0)
        self.ξc_spinbox.setValue(29.0)
        self.ξc_spinbox.setToolTip("Probe box separation\n(higher the value closer to the center)")
        self.ξc_spinbox.valueChanged.connect(self.emit_parameter_change)

        θ_label = QLabel("θ", self)  # pylint: disable=invalid-name,non-ascii-name

        self.θ_spinbox = QDoubleSpinBox(self)  # pylint: disable=invalid-name,non-ascii-name
        self.θ_spinbox.setFixedWidth(75)
        self.θ_spinbox.setRange(0.0, 360.0)
        self.θ_spinbox.setSingleStep(5.0)
        self.θ_spinbox.setDecimals(1)
        self.θ_spinbox.setValue(0.0)
        self.θ_spinbox.setToolTip("Probe box phase")
        self.θ_spinbox.valueChanged.connect(self.emit_parameter_change)

        direction_label = QLabel("Direction", self)

        direction_horizontal_radiobutton = QRadioButton(PairwiseProbeDirection.HORIZONTAL.to_str(), self)
        direction_horizontal_radiobutton.setFixedWidth(90)
        direction_horizontal_radiobutton.setChecked(True)
        direction_horizontal_radiobutton.clicked.connect(self.emit_direction_change)

        direction_vertical_radiobutton = QRadioButton(PairwiseProbeDirection.VERTICAL.to_str(), self)
        direction_vertical_radiobutton.setFixedWidth(90)
        direction_vertical_radiobutton.setChecked(False)
        direction_vertical_radiobutton.clicked.connect(self.emit_direction_change)

        direction_spacer = QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        direction_layout = QHBoxLayout()
        direction_layout.addWidget(direction_horizontal_radiobutton)
        direction_layout.addWidget(direction_vertical_radiobutton)
        direction_layout.addItem(direction_spacer)

        layout = QGridLayout()

        row = 0
        col = 0
        layout.addWidget(amplitude_label, row, col)
        col += 1
        layout.addWidget(self.amplitude_spinbox, row, col, 1, 2)

        row += 1
        col = 0
        layout.addWidget(dξ_label, row, col)
        col += 1
        layout.addWidget(self.dξ_spinbox, row, col)

        row += 1
        col = 0
        layout.addWidget(dη_label, row, col)
        col += 1
        layout.addWidget(self.dη_spinbox, row, col)

        row += 1
        col = 0
        layout.addWidget(ξc_label, row, col)
        col += 1
        layout.addWidget(self.ξc_spinbox, row, col)

        row += 1
        col = 0
        layout.addWidget(θ_label, row, col)
        col += 1
        layout.addWidget(self.θ_spinbox, row, col)

        row += 1
        col = 0
        layout.addWidget(direction_label, row, col)
        col += 1
        layout.addLayout(direction_layout, row, col)

        row += 1
        layout.setRowStretch(row, 1)

        self.setLayout(layout)

        self.direction_radiobuttons = (direction_horizontal_radiobutton, direction_vertical_radiobutton)

    def __init__(self, shape: tuple[int, int], vlim: tuple[float, float], parent=None):
        super().__init__(parent)
        self._min, self._max = vlim
        self._range = self._max - self._min
        self.shape = shape
        self.setup_main_widget(shape)

    @property
    def command(self) -> np.ndarray:
        return self.widget_change(self.amplitude_spinbox, self.dξ_spinbox, self.dη_spinbox, self.ξc_spinbox, self.θ_spinbox, self.direction_radiobuttons)


class TextPresetWidget(QWidget):
    """Text command preset widget.

    Controls :
        amplitude: float
            Amplitude of the checker.
        position: tuple[int, int] = (0, 0)
            Text position.
        font_size : int
            Text size.
    """

    changed = Signal(np.ndarray)

    def param_change(self, shape: tuple[int, int], amplitude: float, string: str, position: tuple[int, int], font_size: int) -> np.ndarray:
        return self._range * amplitude * text(shape, string, position, font_size)

    def widget_change(self, amplitude_spinbox, string_textbox, position_spinboxes, size_spinbox) -> np.ndarray:
        size = size_spinbox.value()
        offset_x_spinbox, offset_y_spinbox = position_spinboxes
        offset_x_spinbox.setRange(-self.shape[0] - size, size)
        offset_y_spinbox.setRange(-self.shape[1] - size, size)
        return self.param_change(self.shape, amplitude_spinbox.value(), string_textbox.text(), position_spinboxes.value(), size)

    @Slot()
    def on_value_changed(self):
        self.changed.emit(self.widget_change(self.amplitude_spinbox, self.string_textbox, self.position_spinboxes, self.size_spinbox))

    def setup_main_widget(self, shape: tuple[int, int]):
        amplitude_label = QLabel("Amplitude", self)
        amplitude_label.setFixedWidth(100)

        self.amplitude_spinbox = QDoubleSpinBox(self)
        self.amplitude_spinbox.setFixedWidth(75)
        self.amplitude_spinbox.setRange(0.0, 1.0)
        self.amplitude_spinbox.setSingleStep(0.1)
        self.amplitude_spinbox.setValue(0.5)
        self.amplitude_spinbox.valueChanged.connect(self.on_value_changed)

        size_label = QLabel("Size", self)

        self.size_spinbox = QSpinBox(self)
        self.size_spinbox.setFixedWidth(75)
        self.size_spinbox.setRange(0, shape[0])
        self.size_spinbox.setValue(shape[0])
        self.size_spinbox.valueChanged.connect(self.on_value_changed)

        size_spacer = QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        size_layout = QHBoxLayout()
        size_layout.addWidget(self.size_spinbox)
        size_layout.addItem(size_spacer)

        position_label = QLabel("Position", self)

        self.position_spinboxes = NSpinBoxesWidget(2, self)
        position_x_spinbox, position_y_spinbox = self.position_spinboxes

        position_x_spinbox.setFixedWidth(75)
        position_x_spinbox.setRange(-self.size_spinbox.value() // 2, self.size_spinbox.value() // 2)
        position_x_spinbox.setValue(shape[0] // 2)
        position_x_spinbox.valueChanged.connect(self.on_value_changed)

        position_y_spinbox.setFixedWidth(75)
        position_y_spinbox.setRange(-self.size_spinbox.value() // 2, self.size_spinbox.value() // 2)
        position_y_spinbox.setValue(shape[1] // 2)
        position_y_spinbox.valueChanged.connect(self.on_value_changed)

        string_label = QLabel("Text", self)

        self.string_textbox = QLineEdit(self)
        self.string_textbox.setText("F")
        self.string_textbox.textChanged.connect(self.on_value_changed)

        position_spacer = QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        position_layout = QHBoxLayout()
        position_layout.addWidget(self.position_spinboxes)
        position_layout.addItem(position_spacer)

        layout = QGridLayout()

        row = 0
        col = 0
        layout.addWidget(amplitude_label, row, col)
        col += 1
        layout.addWidget(self.amplitude_spinbox, row, col, 1, 2)

        row += 1
        col = 0
        layout.addWidget(string_label, row, col)
        col += 1
        layout.addWidget(self.string_textbox, row, col)

        row += 1
        col = 0
        layout.addWidget(size_label, row, col)
        col += 1
        layout.addLayout(size_layout, row, col)

        row += 1
        col = 0
        layout.addWidget(position_label, row, col)
        col += 1
        layout.addLayout(position_layout, row, col)

        row += 1
        layout.setRowStretch(row, 1)

        self.setLayout(layout)

    def __init__(self, shape: tuple[int, int], vlim: tuple[float, float], parent=None):
        super().__init__(parent)
        self._min, self._max = vlim
        self._range = self._max - self._min
        self.shape = shape
        self.setup_main_widget(shape)

    @property
    def command(self) -> np.ndarray:
        return self.widget_change(self.amplitude_spinbox, self.string_textbox, self.position_spinboxes, self.size_spinbox)


class FilePresetWidget2(QWidget):  # TODO: fix this, closing the stream window causes crash
    """
    Command file preset widget
    """

    changed = Signal(np.ndarray)

    def param_change(self) -> np.ndarray:
        return self._command

    def widget_change(self) -> np.ndarray:
        return self.param_change()

    @Slot()
    def on_value_changed(self):
        self.changed.emit(self.widget_change())

    def setup_main_widget(self):
        command_file_label = QLabel("File", self)
        command_file_label.setFixedWidth(100)

        command_file_lineedit = QLineEdit(self)
        command_file_lineedit.setEnabled(False)

        browse_command_file_button = QPushButton("Browse", self)
        browse_command_file_button.setFixedWidth(75)

        command_file_layout = QHBoxLayout()
        command_file_layout.addWidget(command_file_lineedit)
        command_file_layout.addWidget(browse_command_file_button)

        layout = QGridLayout()

        row = 0
        col = 0
        layout.addWidget(command_file_label, row, col)
        col += 1
        layout.addLayout(command_file_layout, row, col)

        row += 1
        layout.setRowStretch(row, 1)

        self.setLayout(layout)

        self.command_file_lineedit = command_file_lineedit

        @Slot()
        def browse_cmd_file():
            dialog_filename, _ = QFileDialog.getOpenFileName(self, "Open Command", ".", "Command File (*.fits)", options=QFileDialog.Option.DontUseNativeDialog | QFileDialog.Option.ReadOnly)
            if dialog_filename:
                cmd_file_info = QFileInfo(dialog_filename)
                cmd_filename = f"{cmd_file_info.absolutePath()}/{cmd_file_info.baseName()}.fits"
                self.command_file_lineedit.setText(cmd_filename)
                with fits.open(cmd_filename) as hdul:
                    self._command = hdul[0].data
                self.on_value_changed()

        browse_command_file_button.clicked.connect(browse_cmd_file)

    def __init__(self, shape, parent=None):
        super().__init__(parent)
        self._command = np.zeros(shape)
        self.setup_main_widget()

    @property
    def command(self) -> np.ndarray:
        return self.widget_change()
