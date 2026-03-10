import numpy as np

from PySide6.QtWidgets import QWidget, QGridLayout, QDoubleSpinBox, QLabel, QSpinBox, QLineEdit
from PySide6.QtCore import Signal, Slot

from pykato.function import gradient, checkers, sinusoid, box, polka, register, text
from pykato.log import setup_logger
from ..widget import NSpinBoxesWidget, NDoubleSpinBoxesWidget, DOTFProbeDirectionWidget, PairwiseProbeDirectionWidget
from ..function import dotf_probe, DOTFProbeDirection, pairwise_probe, PairwiseProbeDirection

logger = setup_logger("command_preset", terminator="\n")


class CommandPresetWidget(QWidget):
    """
    Base class for command preset classes
    """

    changed = Signal(np.ndarray)

    def __init__(self, shape: tuple[int, int], vlim: tuple[int, int], parent=None):
        super().__init__(parent)
        self._vmin, self._vmax = vlim
        self._full_stroke = self._vmax - self._vmin
        self._command = np.zeros(shape)
        self.setup_main_widget()

    def setup_main_widget(self):
        pass

    @property
    def command(self) -> np.ndarray:
        return self._command


class ConstantPresetWidget(CommandPresetWidget):
    """
    Constant command preset widget
    """

    @Slot(float)
    def on_const_value_changed(self, const_perc: float):
        const = self._full_stroke * const_perc / 100.0
        self._command = np.zeros_like(self._command) + const
        self.changed.emit(self._command)

    def setup_main_widget(self):

        const_label = QLabel("Constant", self)
        const_label.setFixedWidth(100)

        self.const_spinbox = QDoubleSpinBox(self)
        self.const_spinbox.setFixedWidth(100)
        self.const_spinbox.setRange(-50, 50)
        self.const_spinbox.setSuffix(" %")
        self.const_spinbox.setValue(0)
        self.const_spinbox.setSingleStep(1)
        self.const_spinbox.valueChanged.connect(self.on_const_value_changed)

        layout = QGridLayout()

        row = 0
        col = 0
        layout.addWidget(const_label, row, col)
        col += 1
        layout.addWidget(self.const_spinbox, row, col)

        self.setLayout(layout)


class GradientPresetWidget(CommandPresetWidget):
    """
    Gradient command preset widget
    """

    @Slot(float, float)
    def on_values_changed(self, peak_valley_perc: float, angle: float):
        peak_valley = self._full_stroke * peak_valley_perc / 100.0
        grad_max = abs(np.cos(angle)) * self._command.shape[0] / 2 + abs(np.sin(angle)) * self._command.shape[1] / 2
        self._command = (gradient(self._command.shape, angle) / (2 * grad_max)) * peak_valley
        self.changed.emit(self._command)

    def setup_main_widget(self):

        grad_label = QLabel("P-V", self)
        grad_label.setFixedWidth(100)

        self.grad_spinbox = QDoubleSpinBox(self)
        self.grad_spinbox.setFixedWidth(100)
        self.grad_spinbox.setRange(-50, 50)
        self.grad_spinbox.setSuffix(" %")
        self.grad_spinbox.setValue(0)
        self.grad_spinbox.setSingleStep(1)
        self.grad_spinbox.valueChanged.connect(lambda _peak_valley_perc: self.on_values_changed(_peak_valley_perc, self.angle_spinbox.value()))

        angle_label = QLabel("Angle", self)

        self.angle_spinbox = QDoubleSpinBox(self)
        self.angle_spinbox.setFixedWidth(100)
        self.angle_spinbox.setRange(0.0, 360.0)
        self.angle_spinbox.setSingleStep(5.0)
        self.angle_spinbox.setSuffix(" °")
        self.angle_spinbox.setValue(0.0)
        self.angle_spinbox.valueChanged.connect(lambda _angle: self.on_values_changed(self.grad_spinbox.value(), np.deg2rad(_angle)))

        layout = QGridLayout()

        row = 0
        col = 0
        layout.addWidget(grad_label, row, col)
        col += 1
        layout.addWidget(self.grad_spinbox, row, col)

        row += 1
        col = 0
        layout.addWidget(angle_label, row, col)
        col += 1
        layout.addWidget(self.angle_spinbox, row, col)

        self.setLayout(layout)


class CheckerPresetWidget(CommandPresetWidget):
    """
    Checker command preset widget
    """

    @Slot(float, tuple, tuple, float)
    def on_values_changed(self, amp_perc: float, size: tuple[int, int], offset: tuple[int, int], mean_perc: float):
        amp = self._full_stroke * amp_perc / 100.0
        mean = self._full_stroke * mean_perc / 100.0
        self._command = amp * checkers(self._command.shape, size, offset) + mean
        self.changed.emit(self._command)

    def setup_main_widget(self):

        amplitude_label = QLabel("Amplitude", self)
        amplitude_label.setFixedWidth(100)

        self.amplitude_spinbox = QDoubleSpinBox(self)
        self.amplitude_spinbox.setFixedWidth(100)
        self.amplitude_spinbox.setRange(-50, 50)
        self.amplitude_spinbox.setSuffix(" %")
        self.amplitude_spinbox.setValue(0)
        self.amplitude_spinbox.setSingleStep(1)
        self.amplitude_spinbox.setToolTip("Checker amplitude")
        self.amplitude_spinbox.valueChanged.connect(lambda _amp_perc: self.on_values_changed(_amp_perc, self.size_spinboxes.value(), self.offset_spinboxes.value(), self.mean_spinbox.value()))

        mean_label = QLabel("Mean", self)

        self.mean_spinbox = QDoubleSpinBox(self)
        self.mean_spinbox.setFixedWidth(100)
        self.mean_spinbox.setRange(-50, 50)
        self.mean_spinbox.setSuffix(" %")
        self.mean_spinbox.setValue(0)
        self.mean_spinbox.setSingleStep(1)
        self.mean_spinbox.setToolTip("Mean of the sinusoid")
        self.mean_spinbox.valueChanged.connect(lambda _mean_perc: self.on_values_changed(self.amplitude_spinbox.value(), self.size_spinboxes.value(), self.offset_spinboxes.value(), _mean_perc))

        size_label = QLabel("Size", self)

        self.size_spinboxes = NSpinBoxesWidget(parent=self)
        self.size_spinboxes[0].setRange(0, self._command.shape[0])
        self.size_spinboxes[0].setValue(self._command.shape[0] // 2)
        self.size_spinboxes[0].setFixedWidth(100)
        self.size_spinboxes[1].setRange(0, self._command.shape[1])
        self.size_spinboxes[1].setValue(self._command.shape[1] // 2)
        self.size_spinboxes[1].setFixedWidth(100)
        self.size_spinboxes.valueChanged.connect(lambda _size: self.on_values_changed(self.amplitude_spinbox.value(), _size, self.offset_spinboxes.value(), self.mean_spinbox.value()))

        offset_label = QLabel("Offset", self)

        self.offset_spinboxes = NSpinBoxesWidget(parent=self)
        self.offset_spinboxes[0].setRange(-self.size_spinboxes[0].value() // 2, self.size_spinboxes[0].value() // 2)
        self.offset_spinboxes[0].setValue(self._command.shape[0] // 4)
        self.offset_spinboxes[0].setFixedWidth(100)
        self.offset_spinboxes[1].setRange(-self.size_spinboxes[1].value() // 2, self.size_spinboxes[1].value() // 2)
        self.offset_spinboxes[1].setValue(self._command.shape[1] // 4)
        self.offset_spinboxes[1].setFixedWidth(100)
        self.offset_spinboxes.valueChanged.connect(lambda _offset: self.on_values_changed(self.amplitude_spinbox.value(), self.size_spinboxes.value(), _offset, self.mean_spinbox.value()))

        layout = QGridLayout()

        row = 0
        col = 0
        layout.addWidget(amplitude_label, row, col)
        col += 1
        layout.addWidget(self.amplitude_spinbox, row, col)

        row += 1
        col = 0
        layout.addWidget(mean_label, row, col)
        col += 1
        layout.addWidget(self.mean_spinbox, row, col)

        row += 1
        col = 0
        layout.addWidget(size_label, row, col)
        col += 1
        layout.addWidget(self.size_spinboxes, row, col)

        row += 1
        col = 0
        layout.addWidget(offset_label, row, col)
        col += 1
        layout.addWidget(self.offset_spinboxes, row, col)

        self.setLayout(layout)


class SinusoidPresetWidget(CommandPresetWidget):
    """
    Sinusoidal command preset widget
    """

    @Slot(float, float, float, float, float)
    def on_values_changed(self, amp_perc: float, period: float, phase: float, angle: float, mean_perc: float):
        amp = self._full_stroke * amp_perc / 100.0
        mean = self._full_stroke * mean_perc / 100.0
        self._command = amp * sinusoid(self._command.shape, period, np.deg2rad(phase), np.deg2rad(angle)) + mean
        self.changed.emit(self._command)

    def setup_main_widget(self):
        amplitude_label = QLabel("Amplitude", self)
        amplitude_label.setFixedWidth(100)

        self.amplitude_spinbox = QDoubleSpinBox(self)
        self.amplitude_spinbox.setFixedWidth(100)
        self.amplitude_spinbox.setRange(-50, 50)
        self.amplitude_spinbox.setSuffix(" %")
        self.amplitude_spinbox.setValue(0)
        self.amplitude_spinbox.setSingleStep(1)
        self.amplitude_spinbox.setToolTip("Amplitude of the sinusoid")
        self.amplitude_spinbox.valueChanged.connect(lambda _amp_perc: self.on_values_changed(_amp_perc, self.period_spinbox.value(), self.phase_spinbox.value(), self.angle_spinbox.value(), self.mean_spinbox.value()))

        mean_label = QLabel("Mean", self)

        self.mean_spinbox = QDoubleSpinBox(self)
        self.mean_spinbox.setFixedWidth(100)
        self.mean_spinbox.setRange(-50, 50)
        self.mean_spinbox.setSuffix(" %")
        self.mean_spinbox.setValue(0)
        self.mean_spinbox.setSingleStep(1)
        self.mean_spinbox.setToolTip("Mean of the sinusoid")
        self.mean_spinbox.valueChanged.connect(lambda _mean_perc: self.on_values_changed(self.amplitude_spinbox.value(), self.period_spinbox.value(), self.phase_spinbox.value(), self.angle_spinbox.value(), _mean_perc))

        period_label = QLabel("Period", self)

        self.period_spinbox = QDoubleSpinBox(self)
        self.period_spinbox.setFixedWidth(100)
        self.period_spinbox.setRange(0.0, self._command.shape[0])
        self.period_spinbox.setSingleStep(1.0)
        self.period_spinbox.setValue(20)
        self.period_spinbox.valueChanged.connect(lambda _period: self.on_values_changed(self.amplitude_spinbox.value(), _period, self.phase_spinbox.value(), self.angle_spinbox.value(), self.mean_spinbox.value()))
        self.period_spinbox.setToolTip("Period of the sinusoid")

        phase_label = QLabel("Phase", self)

        self.phase_spinbox = QDoubleSpinBox(self)
        self.phase_spinbox.setFixedWidth(100)
        self.phase_spinbox.setRange(0.0, 360.0)
        self.phase_spinbox.setSingleStep(5.0)
        self.phase_spinbox.setValue(0.0)
        self.phase_spinbox.setSuffix(" °")
        self.phase_spinbox.setToolTip("Phase of the sinusoid")
        self.phase_spinbox.valueChanged.connect(lambda _phase: self.on_values_changed(self.amplitude_spinbox.value(), self.period_spinbox.value(), _phase, self.angle_spinbox.value(), self.mean_spinbox.value()))

        angle_label = QLabel("Angle", self)

        self.angle_spinbox = QDoubleSpinBox(self)
        self.angle_spinbox.setFixedWidth(100)
        self.angle_spinbox.setRange(0.0, 360.0)
        self.angle_spinbox.setSingleStep(5.0)
        self.angle_spinbox.setValue(45)
        self.angle_spinbox.setSuffix(" °")
        self.angle_spinbox.setToolTip("Angle of the sinusoid")
        self.angle_spinbox.valueChanged.connect(lambda _angle: self.on_values_changed(self.amplitude_spinbox.value(), self.period_spinbox.value(), self.phase_spinbox.value(), _angle, self.mean_spinbox.value()))

        layout = QGridLayout()

        row = 0
        col = 0
        layout.addWidget(amplitude_label, row, col)
        col += 1
        layout.addWidget(self.amplitude_spinbox, row, col)

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

        self.setLayout(layout)


class BoxPresetWidget(CommandPresetWidget):
    """
    Box command preset widget
    """

    @Slot(float, tuple, tuple, float)
    def on_values_changed(self, amp_perc: float, size: tuple[int, int], center: tuple[int, int], mean_perc: float):
        amp = self._full_stroke * amp_perc / 100.0
        mean = self._full_stroke * mean_perc / 100.0
        self._command = amp * box(self._command.shape, size, center) + mean
        self.changed.emit(self._command)

    def setup_main_widget(self):

        amplitude_label = QLabel("Amplitude", self)
        amplitude_label.setFixedWidth(100)

        self.amplitude_spinbox = QSpinBox(self)
        self.amplitude_spinbox.setFixedWidth(100)
        self.amplitude_spinbox.setRange(-50, 50)
        self.amplitude_spinbox.setSuffix(" %")
        self.amplitude_spinbox.setValue(0)
        self.amplitude_spinbox.setSingleStep(1)
        self.amplitude_spinbox.setToolTip("Box amplitude")
        self.amplitude_spinbox.valueChanged.connect(lambda _amp_perc: self.on_values_changed(_amp_perc, self.size_spinboxes.value(), self.center_spinboxes.value(), self.mean_spinbox.value()))

        mean_label = QLabel("Mean", self)

        self.mean_spinbox = QDoubleSpinBox(self)
        self.mean_spinbox.setFixedWidth(100)
        self.mean_spinbox.setRange(-50, 50)
        self.mean_spinbox.setSuffix(" %")
        self.mean_spinbox.setValue(0)
        self.mean_spinbox.setSingleStep(1)
        self.mean_spinbox.setToolTip("Mean of the sinusoid")
        self.mean_spinbox.valueChanged.connect(lambda _mean_perc: self.on_values_changed(self.amplitude_spinbox.value(), self.size_spinboxes.value(), self.center_spinboxes.value(), _mean_perc))

        size_label = QLabel("Size", self)

        self.size_spinboxes = NSpinBoxesWidget(parent=self)
        self.size_spinboxes[0].setFixedWidth(100)
        self.size_spinboxes[0].setRange(0, self._command.shape[0])
        self.size_spinboxes[0].setValue(self._command.shape[0] // 4)
        self.size_spinboxes[1].setFixedWidth(100)
        self.size_spinboxes[1].setRange(0, self._command.shape[1])
        self.size_spinboxes[1].setValue(self._command.shape[1] // 4)
        self.size_spinboxes.valueChanged.connect(lambda _size: self.on_values_changed(self.amplitude_spinbox.value(), _size, self.center_spinboxes.value(), self.mean_spinbox.value()))

        center_label = QLabel("Center", self)

        self.center_spinboxes = NSpinBoxesWidget(parent=self)
        self.center_spinboxes[0].setFixedWidth(100)
        self.center_spinboxes[0].setRange(-self._command.shape[0] // 2 - self.size_spinboxes[0].value(), self._command.shape[0] // 2 + self.size_spinboxes[0].value())
        self.center_spinboxes[0].setValue(-self._command.shape[0] // 2)
        self.center_spinboxes[1].setFixedWidth(100)
        self.center_spinboxes[1].setRange(-self._command.shape[1] // 2 - self.size_spinboxes[1].value(), self._command.shape[1] // 2 + self.size_spinboxes[1].value())
        self.center_spinboxes[1].setValue(-self._command.shape[1] // 2)
        self.center_spinboxes.valueChanged.connect(lambda _center: self.on_values_changed(self.amplitude_spinbox.value(), self.size_spinboxes.value(), _center, self.mean_spinbox.value()))

        layout = QGridLayout()

        row = 0
        col = 0
        layout.addWidget(amplitude_label, row, col)
        col += 1
        layout.addWidget(self.amplitude_spinbox, row, col)

        row += 1
        col = 0
        layout.addWidget(mean_label, row, col)
        col += 1
        layout.addWidget(self.mean_spinbox, row, col)

        row += 1
        col = 0
        layout.addWidget(size_label, row, col)
        col += 1
        layout.addWidget(self.size_spinboxes, row, col)

        row += 1
        col = 0
        layout.addWidget(center_label, row, col)
        col += 1
        layout.addWidget(self.center_spinboxes, row, col)

        self.setLayout(layout)


class PolkaPresetWidget(CommandPresetWidget):
    """
    Polka dot pattern command preset widget
    """

    @Slot(float, float, tuple, tuple, float)
    def on_values_changed(self, amp_perc: float, radius: float, spacing: tuple[int, int], offset: tuple[int, int], mean_perc: float):
        amp = self._full_stroke * amp_perc / 100.0
        mean = self._full_stroke * mean_perc / 100.0
        self._command = amp * polka(self._command.shape, radius, spacing, offset) + mean
        self.changed.emit(self._command)

    def setup_main_widget(self):

        amplitude_label = QLabel("Amplitude", self)
        amplitude_label.setFixedWidth(100)

        self.amplitude_spinbox = QSpinBox(self)
        self.amplitude_spinbox.setFixedWidth(100)
        self.amplitude_spinbox.setRange(-50, 50)
        self.amplitude_spinbox.setSuffix(" %")
        self.amplitude_spinbox.setValue(0)
        self.amplitude_spinbox.setSingleStep(1)
        self.amplitude_spinbox.setToolTip("Polka dot amplitude")
        self.amplitude_spinbox.valueChanged.connect(lambda _amp_perc: self.on_values_changed(_amp_perc, self.radius_spinbox.value(), self.spacing_spinboxes.value(), self.offset_spinboxes.value(), self.mean_spinbox.value()))

        mean_label = QLabel("Mean", self)

        self.mean_spinbox = QDoubleSpinBox(self)
        self.mean_spinbox.setFixedWidth(100)
        self.mean_spinbox.setRange(-50, 50)
        self.mean_spinbox.setSuffix(" %")
        self.mean_spinbox.setValue(0)
        self.mean_spinbox.setSingleStep(1)
        self.mean_spinbox.setToolTip("Mean of the sinusoid")
        self.mean_spinbox.valueChanged.connect(lambda _mean_perc: self.on_values_changed(self.amplitude_spinbox.value(), self.radius_spinbox.value(), self.spacing_spinboxes.value(), self.offset_spinboxes.value(), _mean_perc))

        radius_label = QLabel("Radius", self)

        self.radius_spinbox = QDoubleSpinBox(self)
        self.radius_spinbox.setFixedWidth(100)
        self.radius_spinbox.setValue(4)
        self.radius_spinbox.valueChanged.connect(lambda _radius: self.on_values_changed(self.amplitude_spinbox.value(), _radius, self.spacing_spinboxes.value(), self.offset_spinboxes.value(), self.mean_spinbox.value()))

        spacing_label = QLabel("Spacing", self)

        self.spacing_spinboxes = NDoubleSpinBoxesWidget(2, self)
        self.spacing_spinboxes[0].setFixedWidth(100)
        self.spacing_spinboxes[0].setRange(0, self._command.shape[0])
        self.spacing_spinboxes[0].setValue(self._command.shape[0] / 8)
        self.spacing_spinboxes[1].setFixedWidth(100)
        self.spacing_spinboxes[1].setRange(0, self._command.shape[1])
        self.spacing_spinboxes[1].setValue(self._command.shape[1] / 8)
        self.spacing_spinboxes.valueChanged.connect(lambda _spacing: self.on_values_changed(self.amplitude_spinbox.value(), self.radius_spinbox.value(), _spacing, self.offset_spinboxes.value(), self.mean_spinbox.value()))

        offset_label = QLabel("Offset", self)

        self.offset_spinboxes = NDoubleSpinBoxesWidget(2, self)
        self.offset_spinboxes[0].setFixedWidth(100)
        self.offset_spinboxes[0].setRange(-self.spacing_spinboxes[0].value() / 2, self.spacing_spinboxes[0].value() / 2)
        self.offset_spinboxes[0].setValue(-self._command.shape[0] / 16)
        self.offset_spinboxes[1].setFixedWidth(100)
        self.offset_spinboxes[1].setRange(-self.spacing_spinboxes[1].value() / 2, self.spacing_spinboxes[1].value() / 2)
        self.offset_spinboxes[1].setValue(-self._command.shape[1] / 16)
        self.offset_spinboxes.valueChanged.connect(lambda _offset: self.on_values_changed(self.amplitude_spinbox.value(), self.radius_spinbox.value(), self.spacing_spinboxes.value(), _offset, self.mean_spinbox.value()))

        layout = QGridLayout()

        row = 0
        col = 0
        layout.addWidget(amplitude_label, row, col)
        col += 1
        layout.addWidget(self.amplitude_spinbox, row, col)

        row += 1
        col = 0
        layout.addWidget(mean_label, row, col)
        col += 1
        layout.addWidget(self.mean_spinbox, row, col)

        row += 1
        col = 0
        layout.addWidget(radius_label, row, col)
        col += 1
        layout.addWidget(self.radius_spinbox, row, col)

        row += 1
        col = 0
        layout.addWidget(spacing_label, row, col)
        col += 1
        layout.addWidget(self.spacing_spinboxes, row, col)

        row += 1
        col = 0
        layout.addWidget(offset_label, row, col)
        col += 1
        layout.addWidget(self.offset_spinboxes, row, col)

        self.setLayout(layout)


class RegisterPresetWidget(CommandPresetWidget):
    """
    Registration dot pattern command preset widget
    """

    @Slot(float, tuple, float, tuple, tuple, float)
    def on_values_changed(self, amp_perc: float, count: tuple[int, int], radius: float, spacing: tuple[int, int], center: tuple[int, int], mean_perc: float):
        amp = self._full_stroke * amp_perc / 100.0
        mean = self._full_stroke * mean_perc / 100.0
        self._command = amp * register(self._command.shape, count, radius, spacing, center) + mean
        self.changed.emit(self._command)

    def setup_main_widget(self):

        amplitude_label = QLabel("Amplitude", self)
        amplitude_label.setFixedWidth(100)

        self.amplitude_spinbox = QSpinBox(self)
        self.amplitude_spinbox.setFixedWidth(100)
        self.amplitude_spinbox.setRange(-50, 50)
        self.amplitude_spinbox.setSuffix(" %")
        self.amplitude_spinbox.setValue(0)
        self.amplitude_spinbox.setSingleStep(1)
        self.amplitude_spinbox.setToolTip("Register pattern amplitude")
        self.amplitude_spinbox.valueChanged.connect(lambda _amp_perc: self.on_values_changed(_amp_perc, self.count_spinboxes.value(), self.radius_spinbox.value(), self.spacing_spinboxes.value(), self.center_spinboxes.value(), self.mean_spinbox.value()))

        mean_label = QLabel("Mean", self)

        self.mean_spinbox = QDoubleSpinBox(self)
        self.mean_spinbox.setFixedWidth(100)
        self.mean_spinbox.setRange(-50, 50)
        self.mean_spinbox.setSuffix(" %")
        self.mean_spinbox.setValue(0)
        self.mean_spinbox.setSingleStep(1)
        self.mean_spinbox.setToolTip("Mean of the sinusoid")
        self.mean_spinbox.valueChanged.connect(lambda _mean_perc: self.on_values_changed(self.amplitude_spinbox.value(), self.count_spinboxes.value(), self.radius_spinbox.value(), self.spacing_spinboxes.value(), self.center_spinboxes.value(), _mean_perc))

        count_label = QLabel("Count", self)

        self.count_spinboxes = NSpinBoxesWidget(parent=self)
        self.count_spinboxes[0].setFixedWidth(100)
        self.count_spinboxes[0].setRange(1, 20)
        self.count_spinboxes[0].setValue(6)
        self.count_spinboxes[1].setFixedWidth(100)
        self.count_spinboxes[1].setRange(1, 20)
        self.count_spinboxes[1].setValue(6)
        self.count_spinboxes.valueChanged.connect(lambda _count: self.on_values_changed(self.amplitude_spinbox.value(), _count, self.radius_spinbox.value(), self.spacing_spinboxes.value(), self.center_spinboxes.value(), self.mean_spinbox.value()))

        radius_label = QLabel("Radius", self)

        self.radius_spinbox = QDoubleSpinBox(self)
        self.radius_spinbox.setFixedWidth(100)
        self.radius_spinbox.setValue(4)
        self.radius_spinbox.valueChanged.connect(lambda _radius: self.on_values_changed(self.amplitude_spinbox.value(), self.count_spinboxes.value(), _radius, self.spacing_spinboxes.value(), self.center_spinboxes.value(), self.mean_spinbox.value()))

        spacing_label = QLabel("Spacing", self)

        self.spacing_spinboxes = NDoubleSpinBoxesWidget(2, self)
        self.spacing_spinboxes[0].setFixedWidth(100)
        self.spacing_spinboxes[0].setRange(0, self._command.shape[0])
        self.spacing_spinboxes[0].setValue(self._command.shape[0] / 8)
        self.spacing_spinboxes[1].setFixedWidth(100)
        self.spacing_spinboxes[1].setRange(0, self._command.shape[1])
        self.spacing_spinboxes[1].setValue(self._command.shape[1] / 8)
        self.spacing_spinboxes.valueChanged.connect(lambda _spacing: self.on_values_changed(self.amplitude_spinbox.value(), self.count_spinboxes.value(), self.radius_spinbox.value(), _spacing, self.center_spinboxes.value(), self.mean_spinbox.value()))

        center_label = QLabel("Center", self)

        self.center_spinboxes = NDoubleSpinBoxesWidget(2, self)
        self.center_spinboxes[0].setFixedWidth(100)
        self.center_spinboxes[0].setRange(0, self._command.shape[0])
        self.center_spinboxes[0].setValue(self._command.shape[0] // 2)
        self.center_spinboxes[1].setFixedWidth(100)
        self.center_spinboxes[1].setRange(0, self._command.shape[1])
        self.center_spinboxes[1].setValue(self._command.shape[1] // 2)
        self.center_spinboxes.valueChanged.connect(lambda _center: self.on_values_changed(self.amplitude_spinbox.value(), self.count_spinboxes.value(), self.radius_spinbox.value(), self.spacing_spinboxes.value(), _center, self.mean_spinbox.value()))

        layout = QGridLayout()

        row = 0
        col = 0
        layout.addWidget(amplitude_label, row, col)
        col += 1
        layout.addWidget(self.amplitude_spinbox, row, col)

        row += 1
        col = 0
        layout.addWidget(mean_label, row, col)
        col += 1
        layout.addWidget(self.mean_spinbox, row, col)

        row += 1
        col = 0
        layout.addWidget(count_label, row, col)
        col += 1
        layout.addWidget(self.count_spinboxes, row, col)

        row += 1
        col = 0
        layout.addWidget(radius_label, row, col)
        col += 1
        layout.addWidget(self.radius_spinbox, row, col)

        row += 1
        col = 0
        layout.addWidget(spacing_label, row, col)
        col += 1
        layout.addWidget(self.spacing_spinboxes, row, col)

        row += 1
        col = 0
        layout.addWidget(center_label, row, col)
        col += 1
        layout.addWidget(self.center_spinboxes, row, col)

        self.setLayout(layout)


class TextPresetWidget(CommandPresetWidget):
    """
    Text command preset widget
    """

    @Slot(float, str, tuple, int, float)
    def on_values_changed(self, amp_perc: float, stringdata: str, position: tuple[int, int], font_size: int, mean_perc: float):
        amp = self._full_stroke * amp_perc / 100.0
        mean = self._full_stroke * mean_perc / 100.0
        self._command = amp * text(self._command.shape, stringdata, position, font_size) + mean
        self.changed.emit(self._command)

    def setup_main_widget(self):

        amplitude_label = QLabel("Amplitude", self)
        amplitude_label.setFixedWidth(100)

        self.amplitude_spinbox = QSpinBox(self)
        self.amplitude_spinbox.setFixedWidth(100)
        self.amplitude_spinbox.setRange(-50, 50)
        self.amplitude_spinbox.setSuffix(" %")
        self.amplitude_spinbox.setValue(0)
        self.amplitude_spinbox.setSingleStep(1)
        self.amplitude_spinbox.setToolTip("Text amplitude")
        self.amplitude_spinbox.valueChanged.connect(lambda _amp_perc: self.on_values_changed(_amp_perc, self.string_textbox.text(), self.position_spinboxes.value(), self.size_spinbox.value(), self.mean_spinbox.value()))

        mean_label = QLabel("Mean", self)

        self.mean_spinbox = QDoubleSpinBox(self)
        self.mean_spinbox.setFixedWidth(100)
        self.mean_spinbox.setRange(-50, 50)
        self.mean_spinbox.setSuffix(" %")
        self.mean_spinbox.setValue(0)
        self.mean_spinbox.setSingleStep(1)
        self.mean_spinbox.setToolTip("Mean of the sinusoid")
        self.mean_spinbox.valueChanged.connect(lambda _mean_perc: self.on_values_changed(self.amplitude_spinbox.value(), self.string_textbox.text(), self.position_spinboxes.value(), self.size_spinbox.value(), _mean_perc))

        size_label = QLabel("Size", self)

        self.size_spinbox = QSpinBox(self)
        self.size_spinbox.setFixedWidth(100)
        self.size_spinbox.setRange(0, self._command.shape[0])
        self.size_spinbox.setValue(self._command.shape[0])
        self.size_spinbox.valueChanged.connect(lambda _size: self.on_values_changed(self.amplitude_spinbox.value(), self.string_textbox.text(), self.position_spinboxes.value(), _size, self.mean_spinbox.value()))

        position_label = QLabel("Position", self)

        self.position_spinboxes = NSpinBoxesWidget(parent=self)
        self.position_spinboxes[0].setFixedWidth(100)
        self.position_spinboxes[0].setRange(-self.size_spinbox.value() // 2, self.size_spinbox.value() // 2)
        self.position_spinboxes[0].setValue(self._command.shape[0] // 2)
        self.position_spinboxes[1].setFixedWidth(100)
        self.position_spinboxes[1].setRange(-self.size_spinbox.value() // 2, self.size_spinbox.value() // 2)
        self.position_spinboxes[1].setValue(self._command.shape[1] // 2)
        self.position_spinboxes.valueChanged.connect(lambda _position: self.on_values_changed(self.amplitude_spinbox.value(), self.string_textbox.text(), _position, self.size_spinbox.value(), self.mean_spinbox.value()))

        string_label = QLabel("Text", self)

        self.string_textbox = QLineEdit(self)
        self.string_textbox.setText("F")
        self.string_textbox.setFixedWidth(100)
        self.string_textbox.textChanged.connect(lambda _text: self.on_values_changed(self.amplitude_spinbox.value(), _text, self.position_spinboxes.value(), self.size_spinbox.value(), self.mean_spinbox.value()))

        layout = QGridLayout()

        row = 0
        col = 0
        layout.addWidget(amplitude_label, row, col)
        col += 1
        layout.addWidget(self.amplitude_spinbox, row, col)

        row += 1
        col = 0
        layout.addWidget(mean_label, row, col)
        col += 1
        layout.addWidget(self.mean_spinbox, row, col)

        row += 1
        col = 0
        layout.addWidget(string_label, row, col)
        col += 1
        layout.addWidget(self.string_textbox, row, col)

        row += 1
        col = 0
        layout.addWidget(size_label, row, col)
        col += 1
        layout.addWidget(self.size_spinbox, row, col)

        row += 1
        col = 0
        layout.addWidget(position_label, row, col)
        col += 1
        layout.addWidget(self.position_spinboxes, row, col)

        self.setLayout(layout)


class DOTFProbePresetWidget(CommandPresetWidget):
    """
    DOTF Probe command preset widget
    """

    @Slot(float, tuple, DOTFProbeDirection)
    def on_values_changed(self, amp_perc: float, size: tuple[int, int], direction: DOTFProbeDirection):
        amp = self._full_stroke * amp_perc / 100.0
        self._command = amp * dotf_probe(self._command.shape, size, direction)
        self.changed.emit(self._command)

    def setup_main_widget(self):

        amplitude_label = QLabel("Amplitude", self)
        amplitude_label.setFixedWidth(100)

        self.amplitude_spinbox = QSpinBox(self)
        self.amplitude_spinbox.setFixedWidth(100)
        self.amplitude_spinbox.setRange(-50, 50)
        self.amplitude_spinbox.setSuffix(" %")
        self.amplitude_spinbox.setValue(0)
        self.amplitude_spinbox.setSingleStep(1)
        self.amplitude_spinbox.setToolTip("Probe amplitude")
        self.amplitude_spinbox.valueChanged.connect(lambda _amp_perc: self.on_values_changed(_amp_perc, self.size_spinboxes.value(), self.probe_dir_checkboxes.value()[0]))

        size_label = QLabel("Size", self)

        self.size_spinboxes = NSpinBoxesWidget(parent=self)
        self.size_spinboxes[0].setFixedWidth(100)
        self.size_spinboxes[0].setRange(0, self._command.shape[0])
        self.size_spinboxes[0].setValue(11)
        self.size_spinboxes[1].setFixedWidth(100)
        self.size_spinboxes[1].setRange(0, self._command.shape[1])
        self.size_spinboxes[1].setValue(4)
        self.size_spinboxes.valueChanged.connect(lambda _size: self.on_values_changed(self.amplitude_spinbox.value(), _size, self.probe_dir_checkboxes.value()[0]))

        probe_dir_label = QLabel("Probe dir.", self)

        self.probe_dir_checkboxes = DOTFProbeDirectionWidget(exclusive=True, parent=self)
        self.probe_dir_checkboxes.valueChanged.connect(lambda _directions: self.on_values_changed(self.amplitude_spinbox.value(), self.size_spinboxes.value(), _directions[0]))

        layout = QGridLayout()

        row = 0
        col = 0
        layout.addWidget(amplitude_label, row, col)
        col += 1
        layout.addWidget(self.amplitude_spinbox, row, col)

        row += 1
        col = 0
        layout.addWidget(size_label, row, col)
        col += 1
        layout.addWidget(self.size_spinboxes, row, col)

        row += 1
        col = 0
        layout.addWidget(probe_dir_label, row, col)
        col += 1
        layout.addWidget(self.probe_dir_checkboxes, row, col)

        self.setLayout(layout)


class PairwiseProbePresetWidget(CommandPresetWidget):
    """
    Pairwise probe command preset widget
    """

    @Slot(float, float, float, float, float, PairwiseProbeDirection)
    def on_values_changed(self, amp_perc: float, dξ: float, dη: float, ξc: float, θ: float, direction: PairwiseProbeDirection):
        amp = self._full_stroke * amp_perc / 100.0
        self._command = amp * pairwise_probe(self._command.shape, dξ, dη, ξc, θ, direction)
        self.changed.emit(self._command)

    def setup_main_widget(self):

        amplitude_label = QLabel("Amplitude", self)
        amplitude_label.setFixedWidth(100)

        self.amplitude_spinbox = QSpinBox(self)
        self.amplitude_spinbox.setFixedWidth(100)
        self.amplitude_spinbox.setRange(-50, 50)
        self.amplitude_spinbox.setSuffix(" %")
        self.amplitude_spinbox.setValue(0)
        self.amplitude_spinbox.setSingleStep(1)
        self.amplitude_spinbox.setToolTip("Probe amplitude")
        self.amplitude_spinbox.valueChanged.connect(lambda _amp_perc: self.on_values_changed(_amp_perc, self.dξ_spinbox.value(), self.dη_spinbox.value(), self.ξc_spinbox.value(), self.θ_spinbox.value(), self.probe_dir_checkboxes.value()[0]))

        dξ_label = QLabel("dξ", self)  # pylint: disable=invalid-name,non-ascii-name

        self.dξ_spinbox = QDoubleSpinBox(self)  # pylint: disable=invalid-name,non-ascii-name
        self.dξ_spinbox.setFixedWidth(100)
        self.dξ_spinbox.setMinimum(0.0)
        self.dξ_spinbox.setSingleStep(0.001)
        self.dξ_spinbox.setDecimals(3)
        self.dξ_spinbox.setValue(0.008)
        self.dξ_spinbox.setToolTip("Probe box width\n(higher the value wider the box)")
        self.dξ_spinbox.valueChanged.connect(lambda _dξ: self.on_values_changed(self.amplitude_spinbox.value(), _dξ, self.dη_spinbox.value(), self.ξc_spinbox.value(), self.θ_spinbox.value(), self.probe_dir_checkboxes.value()[0]))

        dη_label = QLabel("dη", self)  # pylint: disable=invalid-name,non-ascii-name

        self.dη_spinbox = QDoubleSpinBox(self)  # pylint: disable=invalid-name,non-ascii-name
        self.dη_spinbox.setFixedWidth(100)
        self.dη_spinbox.setMinimum(0.0)
        self.dη_spinbox.setSingleStep(0.001)
        self.dη_spinbox.setDecimals(3)
        self.dη_spinbox.setValue(0.018)
        self.dη_spinbox.setToolTip("Probe box height\n(higher the value taller the box)")
        self.dη_spinbox.valueChanged.connect(lambda _dη: self.on_values_changed(self.amplitude_spinbox.value(), self.dξ_spinbox.value(), _dη, self.ξc_spinbox.value(), self.θ_spinbox.value(), self.probe_dir_checkboxes.value()[0]))

        ξc_label = QLabel("ξc", self)  # pylint: disable=invalid-name,non-ascii-name

        self.ξc_spinbox = QDoubleSpinBox(self)  # pylint: disable=invalid-name,non-ascii-name
        self.ξc_spinbox.setFixedWidth(100)
        self.ξc_spinbox.setRange(1.0, self._command.shape[0])
        self.ξc_spinbox.setSingleStep(1.0)
        self.ξc_spinbox.setValue(29.0)
        self.ξc_spinbox.setToolTip("Probe box separation\n(higher the value closer to the center)")
        self.ξc_spinbox.valueChanged.connect(lambda _ξc: self.on_values_changed(self.amplitude_spinbox.value(), self.dξ_spinbox.value(), self.dη_spinbox.value(), _ξc, self.θ_spinbox.value(), self.probe_dir_checkboxes.value()[0]))

        θ_label = QLabel("θ", self)  # pylint: disable=invalid-name,non-ascii-name

        self.θ_spinbox = QDoubleSpinBox(self)  # pylint: disable=invalid-name,non-ascii-name
        self.θ_spinbox.setFixedWidth(100)
        self.θ_spinbox.setRange(0.0, 360.0)
        self.θ_spinbox.setSingleStep(5.0)
        self.θ_spinbox.setDecimals(1)
        self.θ_spinbox.setValue(0.0)
        self.θ_spinbox.setToolTip("Probe box phase")
        self.θ_spinbox.valueChanged.connect(lambda _θ: self.on_values_changed(self.amplitude_spinbox.value(), self.dξ_spinbox.value(), self.dη_spinbox.value(), self.ξc_spinbox.value(), _θ, self.probe_dir_checkboxes.value()[0]))

        probe_dir_label = QLabel("Probe dir.", self)

        self.probe_dir_checkboxes = PairwiseProbeDirectionWidget(exclusive=True, parent=self)
        self.probe_dir_checkboxes.valueChanged.connect(lambda _directions: self.on_values_changed(self.amplitude_spinbox.value(), self.dξ_spinbox.value(), self.dη_spinbox.value(), self.ξc_spinbox.value(), self.θ_spinbox.value(), _directions[0]))

        layout = QGridLayout()

        row = 0
        col = 0
        layout.addWidget(amplitude_label, row, col)
        col += 1
        layout.addWidget(self.amplitude_spinbox, row, col)

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
        layout.addWidget(probe_dir_label, row, col)
        col += 1
        layout.addWidget(self.probe_dir_checkboxes, row, col)

        self.setLayout(layout)
