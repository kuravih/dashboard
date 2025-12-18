import numpy as np

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QRadioButton, QSpacerItem, QButtonGroup, QSizePolicy, QGridLayout, QHBoxLayout, QPushButton, QComboBox
from PySide6.QtCore import QTimer, Slot

from pykato.log import setup_logger
from pykato.plotfunction.preset import Histogram_Colorbar_Preset
from pykato.function import timestamp_string

from ..widget import Window, OrientationWidget, CenterWidget, DoubleValueSetWidget
from ..function import Flip, Rotation, write_sink_sample_data, write_sink_sample_header
from ..device.modulator import Modulator, SinkSample
from ..widget.command_preset_widget import EFCPresetWidget, ConstPresetWidget, GradientPresetWidget, CheckerPresetWidget, SinusoidPresetWidget, BoxPresetWidget, PolkaPresetWidget, RegisterPresetWidget, DOTFPresetWidget, TextPresetWidget
from ..widget.figure_widget import FigureWidget, ModulatorFigureWidget

logger = setup_logger("modulator_window", terminator="\n")

PRESETS = ["Constant", "Gradient", "Checker", "Sinusoid", "Box", "Polka", "Register", "dOTF", "EFC", "Text"]


# ==== PreviewWindow ==================================================================================================
class PreviewWindow(Window):
    """
    Modulator Preview Window
    """

    def __init__(self, modulator: Modulator):
        super().__init__()
        self._modulator = modulator
        self._sample = self._modulator.pull_blank_sample()

        self.setWindowTitle(f"{self._modulator.name} Preview")

        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self.setup_preview_widget())
        self.setLayout(layout)

        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.on_update_window)
        self.update_timer.start(100)  # Update window every 100 ms

    @property
    def modulator(self) -> Modulator:
        return self._modulator

    @property
    def sample(self) -> SinkSample:
        return self._sample

    @Slot(SinkSample)
    def on_new_sample(self, _sample: SinkSample):
        self._sample = _sample

    def setup_preview_widget(self) -> QWidget:
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(2, 2, 2, 2)
        widget.setLayout(layout)

        self.preview_figure_widget = ModulatorFigureWidget(self.modulator.blank, self.modulator.pxmax, True, self)

        layout.addWidget(self.preview_figure_widget)

        return widget

    @Slot()
    def on_update_window(self):
        # logger.info("PreviewWindow.on_update_window")
        self.preview_figure_widget.figure.get_image().set_data(self.sample.command)
        self.preview_figure_widget.figure.canvas.draw()

    def closeEvent(self, event):
        if self.update_timer.isActive():
            self.update_timer.stop()
        self.deleteLater()
        event.accept()


# ==== InfoWindow =====================================================================================================
class InfoWindow(Window):
    """
    Modulator Info Window
    """

    def __init__(self, modulator: Modulator):
        super().__init__()
        self._modulator = modulator
        self._sample = self._modulator.pull_sample()

        self.setWindowTitle(f"{self._modulator.name} Information")

        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self.setup_info_widget())
        self.setLayout(layout)

        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.on_update_window)
        self.update_timer.start(100)  # Update window every 100 ms

    @property
    def modulator(self) -> Modulator:
        return self._modulator

    @property
    def sample(self) -> SinkSample:
        return self._sample

    @Slot(SinkSample)
    def on_new_sample(self, _sample: SinkSample):
        self._sample = _sample

    def setup_info_widget(self):
        widget = QWidget(self)
        layout = QGridLayout(widget)
        widget.setLayout(layout)

        name_label = QLabel("Name", self)
        name_label.setFixedWidth(100)
        name_value_label = QLabel(f"{self.modulator.name}", self)
        name_value_label.setToolTip("Device Name")

        uri_label = QLabel("URI", self)
        uri_label.hide()
        uri_value_label = QLabel("uri", self)
        uri_value_label.hide()
        uri_value_label.setToolTip("Device URI")

        kind_label = QLabel("Kind", self)
        kind_modulator_radiobutton = QRadioButton("CAMERA", self)
        kind_modulator_radiobutton.setEnabled(False)
        kind_modulator_radiobutton.setToolTip("Device is a Modulator")
        kind_slm_radiobutton = QRadioButton("SLM", self)
        kind_slm_radiobutton.setEnabled(False)
        kind_slm_radiobutton.setToolTip("Device is an SLM")
        kind_dm_radiobutton = QRadioButton("DM", self)
        kind_dm_radiobutton.setEnabled(False)
        kind_dm_radiobutton.setToolTip("Device is a DM")
        kind_modulator_radiobutton.setChecked(True)
        kind_slm_radiobutton.setChecked(False)
        kind_dm_radiobutton.setChecked(False)

        frame_rate_label = QLabel("Frame rate (fps)", self)
        self.info_frame_rate_value_label = QLabel(f"{self.modulator.frame_rate_fps:.2f}", self)
        self.info_frame_rate_value_label.setToolTip("Frame rate (fps)")

        kind_spacer = QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        kind_group = QButtonGroup(self)
        kind_group.addButton(kind_modulator_radiobutton)
        kind_group.addButton(kind_slm_radiobutton)
        kind_group.addButton(kind_dm_radiobutton)

        kind_layout = QHBoxLayout()
        kind_layout.addWidget(kind_modulator_radiobutton)
        kind_layout.addWidget(kind_slm_radiobutton)
        kind_layout.addWidget(kind_dm_radiobutton)
        kind_layout.addItem(kind_spacer)

        serial_label = QLabel("Serial No.", self)
        serial_value_label = QLabel(f"{self.modulator.sn}", self)
        serial_value_label.setToolTip("Stream Device")

        full_label = QLabel("Full", self)
        full_value_label = QLabel(f"{self.modulator.full_shape[0]} × {self.modulator.full_shape[1]}", self)
        full_value_label.setToolTip("Stream size")

        shape_label = QLabel("Shape", self)
        shape_value_label = QLabel(f"{self.modulator.shape[0]} × {self.modulator.shape[1]}", self)
        shape_value_label.setToolTip("Stream size")

        creation_time_label = QLabel("Creation time", self)
        creation_time_value_label = QLabel(f"{self.modulator.creation_time:%Y-%m-%d %H:%M:%S}.{self.modulator.creation_time:%f}"[:-2], self)
        creation_time_value_label.setToolTip("Creation time")

        last_access_time_label = QLabel("Last access time", self)
        self.info_last_access_time_value_label = QLabel(f"{self.modulator.last_access_time:%Y-%m-%d %H:%M:%S}.{self.modulator.last_access_time:%f}"[:-2], self)
        self.info_last_access_time_value_label.setToolTip("Last access time")

        center_label = QLabel("Center", self)
        self.info_center_value_label = QLabel(f"({self.modulator.center[0]}, {self.modulator.center[1]})", self)
        self.info_center_value_label.setToolTip("Center")

        radius_label = QLabel("Radius", self)
        self.info_radius_value_label = QLabel(f"{self.modulator.radius}", self)
        self.info_radius_value_label.setToolTip("Radius")

        self.info_hist_figure_widget = FigureWidget(Histogram_Colorbar_Preset(self.modulator.command, position="bottom", vmin=0, vmax=self.modulator.pxmax, nbins=256), show_toolbar=True)
        self.info_hist_figure_widget.figure.get_histogram_ax().set_ylabel("count", size=10)
        self.info_hist_figure_widget.figure.set_vlim(0, self.modulator.pxmax)
        self.info_hist_figure_widget.figure.get_cbar_ax().set_xlabel("nadu", size=10)

        row = 0
        col = 0
        layout.addWidget(name_label, row, col)
        col += 1
        layout.addWidget(name_value_label, row, col)

        row += 1
        col = 0
        layout.addWidget(kind_label, row, col)
        col += 1
        layout.addLayout(kind_layout, row, col)

        row += 1
        col = 0
        layout.addWidget(uri_label, row, col)
        col += 1
        layout.addWidget(uri_value_label, row, col)

        row += 1
        col = 0
        layout.addWidget(serial_label, row, col)
        col += 1
        layout.addWidget(serial_value_label, row, col)

        row += 1
        col = 0
        layout.addWidget(full_label, row, col)
        col += 1
        layout.addWidget(full_value_label, row, col)

        row += 1
        col = 0
        layout.addWidget(shape_label, row, col)
        col += 1
        layout.addWidget(shape_value_label, row, col)

        row += 1
        col = 0
        layout.addWidget(center_label, row, col)
        col += 1
        layout.addWidget(self.info_center_value_label, row, col)

        row += 1
        col = 0
        layout.addWidget(radius_label, row, col)
        col += 1
        layout.addWidget(self.info_radius_value_label, row, col)

        row += 1
        col = 0
        layout.addWidget(creation_time_label, row, col)
        col += 1
        layout.addWidget(creation_time_value_label, row, col)

        row += 1
        col = 0
        layout.addWidget(last_access_time_label, row, col)
        col += 1
        layout.addWidget(self.info_last_access_time_value_label, row, col)

        row += 1
        col = 0
        layout.addWidget(frame_rate_label, row, col)
        col += 1
        layout.addWidget(self.info_frame_rate_value_label, row, col)

        row += 1
        col = 0
        layout.addWidget(self.info_hist_figure_widget, row, col, 1, 2)

        row += 1
        layout.setRowStretch(row, row)

        if self.modulator.link is not None and self.modulator.link.is_connected():
            uri_value_label.setText(f"{self.modulator.link.uri}")
            uri_value_label.show()
            uri_label.show()

        return widget

    @Slot()
    def on_update_window(self):
        # logger.info("InfoWindow.on_update_window")
        self.info_last_access_time_value_label.setText(f"{self.sample.last_access_time:%Y-%m-%d %H:%M:%S}.{self.sample.last_access_time:%f}"[:-2])
        self.info_center_value_label.setText(f"({self.sample.center[0]}, {self.sample.center[1]})")
        self.info_radius_value_label.setText(f"{self.sample.radius}")
        self.info_frame_rate_value_label.setText(f"{self.sample.frame_rate_fps:.2f}")
        self.info_hist_figure_widget.figure.set_data(self.sample.command)
        self.info_hist_figure_widget.figure.canvas.draw()

    def closeEvent(self, event):
        if self.update_timer.isActive():
            self.update_timer.stop()
        self.deleteLater()
        event.accept()


# ==== SettingsWindow =================================================================================================
class SettingsWindow(Window):

    def __init__(self, modulator: Modulator):
        super().__init__()
        self._modulator = modulator
        self._sample = self._modulator.pull_sample()

        self.setWindowTitle(f"{self._modulator.name} Settings")

        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self.setup_control_widget())
        layout.addWidget(self.setup_command_widget())

        self.setLayout(layout)

    @property
    def modulator(self) -> Modulator:
        return self._modulator

    @property
    def sample(self) -> SinkSample:
        return self._sample

    @Slot(SinkSample)
    def on_new_sample(self, _sample: SinkSample):
        self._sample = _sample

    def setup_control_widget(self):
        widget = QWidget(self)
        layout = QGridLayout(widget)
        widget.setLayout(layout)

        # ---- orientation setting ------------------------------------------------------------------------------------
        @Slot(Rotation)
        def set_rotation(_rotation: Rotation):
            self.modulator.rotation = _rotation

        @Slot(Flip)
        def set_flip(_flip: Flip):
            self.modulator.flip = _flip

        orientation_label = QLabel("Orientation", self)
        orientation_label.setFixedWidth(100)
        orientation_widget = OrientationWidget(self.modulator.rotation, self.modulator.flip, self)
        orientation_widget.rotation_change.connect(set_rotation)
        orientation_widget.flip_change.connect(set_flip)
        # ---- orientation setting ------------------------------------------------------------------------------------

        # ---- radius setting -----------------------------------------------------------------------------------------
        @Slot(int)
        def set_radius(_radius: int):
            reply = self.modulator.set_radius(_radius)
            logger.info("reply = %s", reply)
            radius_widget.setValue(self.modulator.radius)

        radius_label = QLabel("Radius", self)
        radius_label.setFixedWidth(100)
        radius_widget = DoubleValueSetWidget(self.modulator.radius, self)
        radius_widget.spinbox.setRange(1, self.modulator.max_radius)
        radius_widget.spinbox.setSingleStep(1)
        radius_widget.spinbox.setDecimals(1)
        radius_widget.spinbox.setSuffix(" px")
        radius_widget.spinbox.setToolTip("Radius")
        radius_widget.value_set.connect(set_radius)
        # ---- radius setting -----------------------------------------------------------------------------------------

        # ---- center setting -----------------------------------------------------------------------------------------
        @Slot(int, int)
        def move_center(x: int, y: int):
            reply = self.modulator.move_center(x, y)
            logger.info("reply = %s", reply)
            center_widget.set_center(self.modulator.center)

        center_label = QLabel("Move Center", self)
        center_label.setFixedWidth(100)
        center_widget = CenterWidget(self.modulator.center, step=1, parent=self)
        center_widget.center_move.connect(move_center)
        # ---- center setting -----------------------------------------------------------------------------------------

        row = 0
        col = 0
        layout.addWidget(orientation_label, row, col)
        col += 1
        layout.addWidget(orientation_widget, row, col)

        row += 1
        col = 0
        layout.addWidget(center_label, row, col)
        col += 1
        layout.addWidget(center_widget, row, col)

        row += 1
        col = 0
        layout.addWidget(radius_label, row, col)
        col += 1
        layout.addWidget(radius_widget, row, col)

        row += 1
        layout.setRowStretch(row, 1)

        return widget

    def setup_command_widget(self):
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        widget.setLayout(layout)

        @Slot()
        def save_command_callback():
            timestamp = timestamp_string(frmt="%Y%m%d.%H%M%S", ms=None)
            filename = f"data/output/{timestamp}_command_sink.raw"
            with open(filename, "wb", buffering=0) as _file:
                write_sink_sample_header(_file, self.sample)
                write_sink_sample_data(_file, self.sample)

        @Slot()
        def send_command_callback():
            self.modulator.push_command(self.preset_widget.command)

        @Slot()
        def add_command_callback():
            current = self.modulator.pull_sample()
            self.modulator.push_command(np.clip(current.command + self.preset_widget.command - np.nanmean(self.preset_widget.command), 0, self.modulator.pxmax))

        preset_figure_widget = ModulatorFigureWidget(self.modulator.blank, self.modulator.pxmax, True, self)

        @Slot(np.ndarray)
        def update_preset_figure(command):
            if np.any(command > self.modulator.pxmax):
                raise ValueError(f"Command values too high {np.max(command)}")
            elif np.any(command < 0):
                raise ValueError(f"Command values too low {np.min(command)}")
            image = np.ma.copy(self.modulator.blank)
            image.data[:] = command[:]

            preset_figure_widget.figure.get_image().set_data(image)
            preset_figure_widget.figure.canvas.draw()

        preset_label = QLabel("Preset", self)
        preset_label.setFixedWidth(100)

        preset_combobox = QComboBox(self)
        for label in PRESETS:
            preset_combobox.addItem(label)
        preset_combobox.setCurrentIndex(0)

        preset_layout = QHBoxLayout()
        preset_layout.addWidget(preset_label)
        preset_layout.addWidget(preset_combobox)

        const_preset_param_widget = ConstPresetWidget(self.modulator.shape, (0, self.modulator.pxmax), self)
        const_preset_param_widget.change.connect(update_preset_figure)

        gradient_preset_param_widget = GradientPresetWidget(self.modulator.shape, (0, self.modulator.pxmax), self)
        gradient_preset_param_widget.change.connect(update_preset_figure)
        gradient_preset_param_widget.hide()

        checker_preset_param_widget = CheckerPresetWidget(self.modulator.shape, (0, self.modulator.pxmax), self)
        checker_preset_param_widget.change.connect(update_preset_figure)
        checker_preset_param_widget.hide()

        sinusoid_preset_param_widget = SinusoidPresetWidget(self.modulator.shape, (0, self.modulator.pxmax), self)
        sinusoid_preset_param_widget.change.connect(update_preset_figure)
        sinusoid_preset_param_widget.hide()

        box_preset_param_widget = BoxPresetWidget(self.modulator.shape, (0, self.modulator.pxmax), self)
        box_preset_param_widget.change.connect(update_preset_figure)
        box_preset_param_widget.hide()

        polka_preset_param_widget = PolkaPresetWidget(self.modulator.shape, (0, self.modulator.pxmax), self)
        polka_preset_param_widget.change.connect(update_preset_figure)
        polka_preset_param_widget.hide()

        register_preset_param_widget = RegisterPresetWidget(self.modulator.shape, (0, self.modulator.pxmax), self)
        register_preset_param_widget.change.connect(update_preset_figure)
        register_preset_param_widget.hide()

        dotf_preset_param_widget = DOTFPresetWidget(self.modulator.shape, (0, self.modulator.pxmax), self)
        dotf_preset_param_widget.change.connect(update_preset_figure)
        dotf_preset_param_widget.hide()

        efc_preset_param_widget = EFCPresetWidget(self.modulator.shape, (0, self.modulator.pxmax), self)
        efc_preset_param_widget.change.connect(update_preset_figure)
        efc_preset_param_widget.hide()

        text_preset_param_widget = TextPresetWidget(self.modulator.shape, (0, self.modulator.pxmax), self)
        text_preset_param_widget.change.connect(update_preset_figure)
        text_preset_param_widget.hide()

        save_cmd_button = QPushButton("Save", self)

        send_cmd_button = QPushButton("Send", self)

        add_cmd_button = QPushButton("Add to Current", self)

        button_layout = QHBoxLayout()
        button_layout.addWidget(save_cmd_button)
        save_cmd_button.clicked.connect(save_command_callback)
        button_layout.addWidget(send_cmd_button)
        send_cmd_button.clicked.connect(send_command_callback)
        add_cmd_button.clicked.connect(add_command_callback)

        button_layout.addWidget(add_cmd_button)

        layout.addWidget(preset_figure_widget)
        layout.addLayout(preset_layout)
        layout.addWidget(const_preset_param_widget)
        layout.addWidget(gradient_preset_param_widget)
        layout.addWidget(checker_preset_param_widget)
        layout.addWidget(sinusoid_preset_param_widget)
        layout.addWidget(box_preset_param_widget)
        layout.addWidget(polka_preset_param_widget)
        layout.addWidget(register_preset_param_widget)
        layout.addWidget(dotf_preset_param_widget)
        layout.addWidget(efc_preset_param_widget)
        layout.addWidget(text_preset_param_widget)
        layout.addLayout(button_layout)

        preset_widgets = (const_preset_param_widget, gradient_preset_param_widget, checker_preset_param_widget, sinusoid_preset_param_widget, box_preset_param_widget, polka_preset_param_widget, register_preset_param_widget, dotf_preset_param_widget, efc_preset_param_widget, text_preset_param_widget)
        self.preset_widget = preset_widgets[0]

        @Slot(int)
        def preset_select(index):
            for widget_index, a_preset_widget in enumerate(preset_widgets):
                if widget_index == index:
                    a_preset_widget.show()
                    self.preset_widget = a_preset_widget
                    update_preset_figure(self.preset_widget.command)
                else:
                    a_preset_widget.hide()

        preset_combobox.currentIndexChanged.connect(preset_select)

        return widget

    def closeEvent(self, event):
        self.deleteLater()
        event.accept()


# ==== SettingsWindow ========================================================================================
