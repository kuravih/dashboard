from datetime import datetime
from pathlib import Path
from typing import cast

import numpy as np
from astropy.io import fits
from matplotlib import colormaps
from pykato.function import disk
from pykato.log import setup_logger
from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QButtonGroup, QComboBox, QFileDialog, QGridLayout, QHBoxLayout, QLabel, QRadioButton, QSizePolicy, QSpacerItem, QVBoxLayout, QWidget

import testbed

from ..device.modulator import Modulator, SinkSample
from ..function import Flip, Rotation, flip_rotate_frame, is_modulator_calibration_file_valid
from ..widget import CenterWidget, DoubleValueSetWidget, FileLoadWidget, IconButton, OrientationWidget, Window
from ..widget.command_preset_widget import BoxPresetWidget, CheckerPresetWidget, ConstantPresetWidget, DOTFProbePresetWidget, GradientPresetWidget, PairwiseProbePresetWidget, PolkaPresetWidget, RegisterPresetWidget, SinusoidPresetWidget, TextPresetWidget
from ..widget.figure_widget import ModulatorFigureWidget, SinkHistFigureWidget
from ..widget.resource import ICON_GEAR, ICON_PAPER_PLANE, ICON_PLUS

logger = setup_logger("modulator_window", terminator="\n")

PRESETS = ["Constant", "Gradient", "Checker", "Sinusoid", "Box", "Polka", "Register", "Text", "dOTF", "Pairwise"]


# ==== HistogramSettingsWindow ========================================================================================
class HistogramSettingsWindow(Window):
    """Settings for the simple preview window."""

    def __init__(self, cmap_name: str, parent=None):
        self.cmap_name: str = cmap_name

        super().__init__(parent, Qt.WindowType.Dialog)

        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setWindowTitle("Preview Settings")
        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self.setup_preview_settings_widget())

        self.setLayout(layout)

    def setup_preview_settings_widget(self) -> QWidget:
        widget = QWidget(self)
        layout = QGridLayout(widget)
        widget.setLayout(layout)

        cmap_label = QLabel("Colormap", self)
        self.cmap_combobox = QComboBox(self)
        self.cmap_combobox.addItems(list(colormaps))
        self.cmap_combobox.setCurrentIndex(list(colormaps).index(self.cmap_name))

        row = 0
        col = 0
        layout.addWidget(cmap_label, row, col)
        col += 1
        layout.addWidget(self.cmap_combobox, row, col)

        return widget


# ==== InfoWindow =====================================================================================================
class InfoWindow(Window):
    """Modulator info window"""

    def __init__(self, modulator: Modulator, parent: QWidget | None = None):
        self.modulator = modulator
        # self.modulator.sync_settings()
        self.sample = self.modulator.sample

        super().__init__(parent, Qt.WindowType.Dialog)

        self.setWindowTitle(f"{self.modulator.name} Information")

        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self.setup_info_widget())

        self.setLayout(layout)

        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.on_update_timer_tick)
        self.update_timer.start(100)  # Update window every 100 ms

    @property
    def modulator(self) -> Modulator:
        return self._modulator

    @modulator.setter
    def modulator(self, device: Modulator):
        self._modulator = device

    @property
    def sample(self) -> SinkSample:
        return self._sample

    @sample.setter
    def sample(self, value: SinkSample):
        self._sample = value

    @Slot(SinkSample)
    def on_sampled(self, sample: SinkSample):
        self._sample = sample

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
        kind_camera_radiobutton = QRadioButton("CAMERA", self)
        kind_camera_radiobutton.setEnabled(False)
        kind_camera_radiobutton.setToolTip("Device is a Modulator")
        kind_slm_radiobutton = QRadioButton("SLM", self)
        kind_slm_radiobutton.setEnabled(False)
        kind_slm_radiobutton.setToolTip("Device is an SLM")
        kind_dm_radiobutton = QRadioButton("DM", self)
        kind_dm_radiobutton.setEnabled(False)
        kind_dm_radiobutton.setToolTip("Device is a DM")
        kind_camera_radiobutton.setChecked(False)
        kind_slm_radiobutton.setChecked(True)
        kind_dm_radiobutton.setChecked(False)

        frame_rate_label = QLabel("Frame rate (fps)", self)
        self.info_frame_rate_value_label = QLabel(f"{self.modulator.frame_rate_fps:.2f}", self)
        self.info_frame_rate_value_label.setToolTip("Frame rate (fps)")

        kind_spacer = QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        kind_group = QButtonGroup(self)
        kind_group.addButton(kind_camera_radiobutton)
        kind_group.addButton(kind_slm_radiobutton)
        kind_group.addButton(kind_dm_radiobutton)

        kind_layout = QHBoxLayout()
        kind_layout.addWidget(kind_camera_radiobutton)
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

        self.hist_figure_widget = SinkHistFigureWidget(self.modulator.blank, self.modulator.pxmax, parent=self)
        if self.hist_figure_widget.toolbar is not None:
            self.hist_figure_widget.toolbar.settingsClicked.connect(self.on_histogram_settings_clicked)

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
        layout.addWidget(self.hist_figure_widget, row, col, 1, 2)

        row += 1
        layout.setRowStretch(row, row)

        if (self.modulator.link is not None) and self.modulator.link.is_connected():
            uri_value_label.setText(f"{self.modulator.link.uri}")
            uri_value_label.show()
            uri_label.show()

        return widget

    @Slot()
    def on_histogram_settings_clicked(self):
        histogram_settings_window = HistogramSettingsWindow(self.hist_figure_widget.cmap_name, parent=self)
        histogram_settings_window.show()
        histogram_settings_window.raise_()
        histogram_settings_window.activateWindow()
        histogram_settings_window.cmap_combobox.currentTextChanged.connect(self.on_cmap_name_changed)

    @Slot(str)
    def on_cmap_name_changed(self, colormap: str):
        self.hist_figure_widget.cmap_name = colormap

    @Slot()
    def on_update_timer_tick(self):
        self.info_last_access_time_value_label.setText(f"{self.sample.last_access_time:%Y-%m-%d %H:%M:%S}.{self.sample.last_access_time:%f}"[:-2])
        self.info_center_value_label.setText(f"({self.sample.center[0]}, {self.sample.center[1]})")
        self.info_radius_value_label.setText(f"{self.sample.radius}")
        self.info_frame_rate_value_label.setText(f"{self.sample.frame_rate_fps:.2f}")
        self.hist_figure_widget.figure.set_data(self.sample.command)
        self.hist_figure_widget.figure.canvas.draw_idle()
        # logger.info("modulator_window.py - InfoWindow.on_update_timer_tick()")

    def closeEvent(self, event):
        if self.update_timer.isActive():
            self.update_timer.stop()
        self.deleteLater()
        event.accept()


# ==== SettingsWindow =================================================================================================
class SettingsWindow(Window):
    """Modulator settings window"""

    def __init__(self, modulator: Modulator, parent: QWidget | None = None):
        self.modulator = modulator
        # self.modulator.sync_settings()

        super().__init__(parent, Qt.WindowType.Dialog)

        self.setWindowTitle(f"{self._modulator.name} Settings")

        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self.setup_settings_widget())

        self.setLayout(layout)

    @property
    def modulator(self) -> Modulator:
        return self._modulator

    @modulator.setter
    def modulator(self, device: Modulator):
        self._modulator = device

    def setup_settings_widget(self):
        widget = QWidget(self)
        layout = QGridLayout(widget)
        widget.setLayout(layout)

        # ---- radius setting -----------------------------------------------------------------------------------------
        @Slot(int)
        def on_set_radius_clicked(radius: int):
            self.modulator.set_radius(radius)
            radius_widget.setValue(self.modulator.radius)
            mask = 0.5 * (1.0 - disk(self.modulator.shape, radius))
            if testbed.data.is_window_alive(self.modulator.preview_window_id):
                modulator_preview_window = cast(PreviewWindow, testbed.data.windows[self.modulator.preview_window_id])
                modulator_preview_window.preview_figure_widget.figure.get_imshow_axes().get_mask().set_alpha(mask.astype(np.float64))
            if testbed.data.is_window_alive(self.modulator.presets_window_id):
                modulator_presets_window = cast(PresetsWindow, testbed.data.windows[self.modulator.presets_window_id])
                modulator_presets_window.preview_figure_widget.figure.get_imshow_axes().get_mask().set_alpha(mask.astype(np.float64))

        radius_label = QLabel("Radius", self)
        radius_label.setFixedWidth(100)
        radius_widget = DoubleValueSetWidget(suffix=" px", parent=self)
        radius_widget.spinbox.setRange(1, self.modulator.max_radius)
        radius_widget.spinbox.setSingleStep(1)
        radius_widget.spinbox.setDecimals(1)
        radius_widget.spinbox.setSuffix(" px")
        radius_widget.spinbox.setToolTip("Radius")
        radius_widget.setValue(self.modulator.radius)
        radius_widget.valueSetClicked.connect(on_set_radius_clicked)
        # ---- radius setting -----------------------------------------------------------------------------------------

        # ---- center setting -----------------------------------------------------------------------------------------
        @Slot(int, int)
        def on_center_move_clicked(x: int, y: int):
            self.modulator.move_center(x, y)
            center_widget.set_center(self.modulator.center)

        center_label = QLabel("Move Center", self)
        center_label.setFixedWidth(100)
        center_widget = CenterWidget(self.modulator.center, step=1, parent=self)
        center_widget.centerMoveClicked.connect(on_center_move_clicked)
        # ---- center setting -----------------------------------------------------------------------------------------

        modulator_calibration_label = QLabel("Calibration", self)
        modulator_calibration_label.setFixedWidth(100)
        self.calibration_widget = FileLoadWidget(caption="Open Calibration File", directory="./data/output", file_filter="Fits file (*.fits)", validator=lambda _filename: is_modulator_calibration_file_valid(_filename, self.modulator.shape), parent=self)
        self.calibration_widget.setFilepath(self.modulator.calibration_file)

        @Slot()
        def on_calibration_change():
            self.modulator.calibration_file = self.calibration_widget.filepath

            pstr = "adu"
            plim = [0, 100]  # soft range
            if self.modulator.calibration:
                pstr = "m"
                plim = [-50, 50]

            if testbed.data.is_window_alive(self.modulator.preview_window_id):
                modulator_preview_window = cast(PreviewWindow, testbed.data.windows[self.modulator.preview_window_id])
                modulator_preview_window.preview_figure_widget.figure.get_image().set_clim(self.modulator.vlim)
                modulator_preview_window.preview_figure_widget.figure.get_cbar_axes().set_title(pstr, size=10)
            if testbed.data.is_window_alive(self.modulator.presets_window_id):
                modulator_presets_window = cast(PresetsWindow, testbed.data.windows[self.modulator.presets_window_id])
                modulator_presets_window.preview_figure_widget.figure.get_image().set_clim(self.modulator.vlim)
                modulator_presets_window.preview_figure_widget.figure.get_cbar_axes().set_title(pstr, size=10)
                modulator_presets_window.preview_figure_widget.figure.canvas.draw_idle()

                modulator_presets_window.constant_preset_param_widget.plim = plim
                modulator_presets_window.constant_preset_param_widget.vlim = self.modulator.vlim
                modulator_presets_window.constant_preset_param_widget.const_spinbox.setValue(0)

                modulator_presets_window.gradient_preset_param_widget.plim = plim
                modulator_presets_window.gradient_preset_param_widget.vlim = self.modulator.vlim
                modulator_presets_window.gradient_preset_param_widget.grad_spinbox.setValue(0)

                modulator_presets_window.checker_preset_param_widget.plim = plim
                modulator_presets_window.checker_preset_param_widget.vlim = self.modulator.vlim
                modulator_presets_window.checker_preset_param_widget.color1_spinbox.setValue(0)
                modulator_presets_window.checker_preset_param_widget.color2_spinbox.setValue(0)

                modulator_presets_window.sinusoid_preset_param_widget.plim = plim
                modulator_presets_window.sinusoid_preset_param_widget.vlim = self.modulator.vlim
                modulator_presets_window.sinusoid_preset_param_widget.amplitude_spinbox.setValue(0)
                modulator_presets_window.sinusoid_preset_param_widget.mean_spinbox.setValue(0)

                modulator_presets_window.box_preset_param_widget.plim = plim
                modulator_presets_window.box_preset_param_widget.vlim = self.modulator.vlim
                modulator_presets_window.box_preset_param_widget.color1_spinbox.setValue(0)
                modulator_presets_window.box_preset_param_widget.color2_spinbox.setValue(0)

                modulator_presets_window.polka_preset_param_widget.plim = plim
                modulator_presets_window.polka_preset_param_widget.vlim = self.modulator.vlim
                modulator_presets_window.polka_preset_param_widget.color1_spinbox.setValue(0)
                modulator_presets_window.polka_preset_param_widget.color2_spinbox.setValue(0)

                modulator_presets_window.register_preset_param_widget.plim = plim
                modulator_presets_window.register_preset_param_widget.vlim = self.modulator.vlim
                modulator_presets_window.register_preset_param_widget.amplitude_spinbox.setValue(0)
                modulator_presets_window.register_preset_param_widget.mean_spinbox.setValue(0)

                modulator_presets_window.text_preset_param_widget.plim = plim
                modulator_presets_window.text_preset_param_widget.vlim = self.modulator.vlim
                modulator_presets_window.text_preset_param_widget.foreground_spinbox.setValue(0)
                modulator_presets_window.text_preset_param_widget.background_spinbox.setValue(0)

                modulator_presets_window.dotf_preset_param_widget.plim = plim
                modulator_presets_window.dotf_preset_param_widget.vlim = self.modulator.vlim
                modulator_presets_window.dotf_preset_param_widget.amplitude_spinbox.setValue(0)

                modulator_presets_window.pairwise_preset_param_widget.plim = plim
                modulator_presets_window.pairwise_preset_param_widget.vlim = self.modulator.vlim
                modulator_presets_window.pairwise_preset_param_widget.amplitude_spinbox.setValue(0)
                modulator_presets_window.pairwise_preset_param_widget.dη_spinbox.setValue(0.017)
                modulator_presets_window.pairwise_preset_param_widget.dξ_spinbox.setValue(0.008)
                modulator_presets_window.pairwise_preset_param_widget.ξc_spinbox.setValue(35.0)
                modulator_presets_window.pairwise_preset_param_widget.θ_spinbox.setValue(0.0)

        self.calibration_widget.fileChanged.connect(on_calibration_change)

        presets_label = QLabel("Presets", self)
        presets_label.setFixedWidth(100)
        presets_button = IconButton(QIcon(ICON_GEAR), parent=self)

        @Slot()
        def on_presets_clicked():

            @Slot()
            def on_window_closed():
                testbed.data.windows.pop(self.modulator.presets_window_id, None)

            if not testbed.data.is_window_alive(self.modulator.presets_window_id):
                presets_window = PresetsWindow(self.modulator, parent=self)
                presets_window.destroyed.connect(on_window_closed)
                presets_window.show()
                presets_window.raise_()
                presets_window.activateWindow()
                testbed.data.windows[self.modulator.presets_window_id] = presets_window

        presets_button.clicked.connect(on_presets_clicked)

        row = 0
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
        col = 0
        layout.addWidget(modulator_calibration_label, row, col)
        col += 1
        layout.addWidget(self.calibration_widget, row, col)

        row += 1
        col = 0
        layout.addWidget(presets_label, row, col)
        col += 1
        layout.addWidget(presets_button, row, col)

        row += 1
        layout.setRowStretch(row, 1)

        return widget

    def closeEvent(self, event):
        self.deleteLater()
        event.accept()


# ==== PresetsWindow ===================================================================================================
class PresetsWindow(Window):
    """Modulator settings window"""

    def __init__(self, modulator: Modulator, parent: QWidget | None = None):
        self.modulator = modulator
        # self.modulator.sync_settings()
        self.command = np.ma.copy(self.modulator.blank)

        super().__init__(parent, Qt.WindowType.Dialog)

        self.setWindowTitle(f"{self._modulator.name} Presets")

        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self.setup_preview_widget())
        layout.addWidget(self.setup_command_widget())

        self.setLayout(layout)

    @property
    def modulator(self) -> Modulator:
        return self._modulator

    @modulator.setter
    def modulator(self, device: Modulator):
        self._modulator = device

    def setup_preview_widget(self) -> QWidget:
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(2, 2, 2, 2)
        widget.setLayout(layout)

        self._sample = self.modulator.sample

        self.pstr = "adu"
        self.plim = [0, 100]
        if self.modulator.calibration:
            self.pstr = "m"
            self.plim = [-50, 50]

        self.preview_figure_widget = ModulatorFigureWidget(self.modulator.blank, self.modulator.vlim, self.modulator.radius, toolitems=["Home", "Pan", "Zoom", "Save", "Settings"], parent=self)
        self.preview_figure_widget.figure.get_cbar_axes().set_title(self.pstr, size=10)

        if self.preview_figure_widget.toolbar is not None:
            self.preview_figure_widget.toolbar.settingsClicked.connect(self.on_preview_settings_clicked)

        layout.addWidget(self.preview_figure_widget)

        return widget

    @Slot()
    def on_preview_settings_clicked(self):
        preview_settings_window = PreviewSettingsWindow(self.preview_figure_widget.cmap_name, self.preview_figure_widget.rotation, self.preview_figure_widget.flip, parent=self)
        preview_settings_window.show()
        preview_settings_window.raise_()
        preview_settings_window.activateWindow()
        preview_settings_window.cmap_combobox.currentTextChanged.connect(self.on_cmap_changed)
        preview_settings_window.orientation_widget.rotationChanged.connect(self.on_rotation_changed)
        preview_settings_window.orientation_widget.flipChanged.connect(self.on_flip_changed)

    @Slot(str)
    def on_cmap_changed(self, colormap: str):
        self.preview_figure_widget.cmap_name = colormap
        self.preview_figure_widget.figure.get_image().set_data(flip_rotate_frame(self.command, self.preview_figure_widget.flip, self.preview_figure_widget.rotation))
        self.preview_figure_widget.figure.canvas.draw_idle()

    @Slot(str)
    def on_rotation_changed(self, rotation: Rotation):
        self.preview_figure_widget.rotation = rotation
        self.preview_figure_widget.figure.get_image().set_data(flip_rotate_frame(self.command, self.preview_figure_widget.flip, self.preview_figure_widget.rotation))
        self.preview_figure_widget.figure.canvas.draw_idle()

    @Slot(str)
    def on_flip_changed(self, flip: Flip):
        self.preview_figure_widget.flip = flip
        self.preview_figure_widget.figure.get_image().set_data(flip_rotate_frame(self.command, self.preview_figure_widget.flip, self.preview_figure_widget.rotation))
        self.preview_figure_widget.figure.canvas.draw_idle()

    def setup_command_widget(self):
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        widget.setLayout(layout)

        @Slot()
        def on_send_clicked():
            self.modulator.push_command(self.preset_widget.command)

        @Slot()
        def on_add_clicked():
            pass

        @Slot(np.ndarray)
        def on_preset_changed(command):
            self.command.data[:] = command[:]
            self.preview_figure_widget.figure.get_image().set_data(flip_rotate_frame(self.command, self.preview_figure_widget.flip, self.preview_figure_widget.rotation))
            self.preview_figure_widget.figure.canvas.draw_idle()

        preset_label = QLabel("Preset", self)
        preset_label.setFixedWidth(100)

        preset_combobox = QComboBox(self)
        for label in PRESETS:
            preset_combobox.addItem(label)
        preset_combobox.setCurrentIndex(0)

        send_button = IconButton(QIcon(ICON_PAPER_PLANE), parent=self)
        send_button.clicked.connect(on_send_clicked)

        add_button = IconButton(QIcon(ICON_PLUS), parent=self)
        add_button.clicked.connect(on_add_clicked)

        preset_layout = QHBoxLayout()
        preset_layout.addWidget(preset_label)
        preset_layout.addWidget(preset_combobox)
        preset_layout.addWidget(send_button)
        preset_layout.addWidget(add_button)

        self.constant_preset_param_widget = ConstantPresetWidget(self.modulator.shape, self.plim, self.modulator.vlim, self)
        self.constant_preset_param_widget.changed.connect(on_preset_changed)

        self.gradient_preset_param_widget = GradientPresetWidget(self.modulator.shape, self.plim, self.modulator.vlim, self)
        self.gradient_preset_param_widget.changed.connect(on_preset_changed)
        self.gradient_preset_param_widget.hide()

        self.checker_preset_param_widget = CheckerPresetWidget(self.modulator.shape, self.plim, self.modulator.vlim, self)
        self.checker_preset_param_widget.changed.connect(on_preset_changed)
        self.checker_preset_param_widget.hide()

        self.sinusoid_preset_param_widget = SinusoidPresetWidget(self.modulator.shape, self.plim, self.modulator.vlim, self)
        self.sinusoid_preset_param_widget.changed.connect(on_preset_changed)
        self.sinusoid_preset_param_widget.hide()

        self.box_preset_param_widget = BoxPresetWidget(self.modulator.shape, self.plim, self.modulator.vlim, self)
        self.box_preset_param_widget.changed.connect(on_preset_changed)
        self.box_preset_param_widget.hide()

        self.polka_preset_param_widget = PolkaPresetWidget(self.modulator.shape, self.plim, self.modulator.vlim, self)
        self.polka_preset_param_widget.changed.connect(on_preset_changed)
        self.polka_preset_param_widget.hide()

        self.register_preset_param_widget = RegisterPresetWidget(self.modulator.shape, self.plim, self.modulator.vlim, self)
        self.register_preset_param_widget.changed.connect(on_preset_changed)
        self.register_preset_param_widget.hide()

        self.text_preset_param_widget = TextPresetWidget(self.modulator.shape, self.plim, self.modulator.vlim, self)
        self.text_preset_param_widget.changed.connect(on_preset_changed)
        self.text_preset_param_widget.hide()

        self.dotf_preset_param_widget = DOTFProbePresetWidget(self.modulator.shape, self.plim, self.modulator.vlim, self)
        self.dotf_preset_param_widget.changed.connect(on_preset_changed)
        self.dotf_preset_param_widget.hide()

        self.pairwise_preset_param_widget = PairwiseProbePresetWidget(self.modulator.shape, self.plim, self.modulator.vlim, self)
        self.pairwise_preset_param_widget.changed.connect(on_preset_changed)
        self.pairwise_preset_param_widget.hide()

        layout.addLayout(preset_layout)
        layout.addWidget(self.constant_preset_param_widget)
        layout.addWidget(self.gradient_preset_param_widget)
        layout.addWidget(self.checker_preset_param_widget)
        layout.addWidget(self.sinusoid_preset_param_widget)
        layout.addWidget(self.box_preset_param_widget)
        layout.addWidget(self.polka_preset_param_widget)
        layout.addWidget(self.register_preset_param_widget)
        layout.addWidget(self.text_preset_param_widget)
        layout.addWidget(self.dotf_preset_param_widget)
        layout.addWidget(self.pairwise_preset_param_widget)

        preset_widgets = (self.constant_preset_param_widget, self.gradient_preset_param_widget, self.checker_preset_param_widget, self.sinusoid_preset_param_widget, self.box_preset_param_widget, self.polka_preset_param_widget, self.register_preset_param_widget, self.text_preset_param_widget, self.dotf_preset_param_widget, self.pairwise_preset_param_widget)

        self.preset_widget = preset_widgets[0]

        @Slot(int)
        def on_preset_select(index):
            for widget_index, a_preset_widget in enumerate(preset_widgets):
                if widget_index == index:
                    a_preset_widget.show()
                    self.preset_widget = a_preset_widget
                    on_preset_changed(self.preset_widget.command)
                else:
                    a_preset_widget.hide()

        preset_combobox.currentIndexChanged.connect(on_preset_select)

        return widget

    def closeEvent(self, event):
        self.deleteLater()
        event.accept()


# ==== PreviewSettingsWindow ==========================================================================================
class PreviewSettingsWindow(Window):
    """Settings for the simple preview window."""

    def __init__(self, cmap_name: str, rotation: Rotation, flip: Flip, parent: QWidget | None = None):
        self.cmap_name: str = cmap_name
        self.rotation: Rotation = rotation
        self.flip: Flip = flip
        super().__init__(parent, Qt.WindowType.Dialog)

        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setWindowTitle("Preview Settings")
        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self.setup_preview_settings_widget())

        self.setLayout(layout)

    def setup_preview_settings_widget(self) -> QWidget:
        widget = QWidget(self)
        layout = QGridLayout(widget)
        widget.setLayout(layout)

        cmap_label = QLabel("Colormap", self)
        self.cmap_combobox = QComboBox(self)
        self.cmap_combobox.addItems(list(colormaps))
        self.cmap_combobox.setCurrentIndex(list(colormaps).index(self.cmap_name))

        orientation_label = QLabel("Orientation", self)
        orientation_label.setFixedWidth(100)
        self.orientation_widget = OrientationWidget(self.rotation, self.flip, self)

        row = 0
        col = 0
        layout.addWidget(cmap_label, row, col)
        col += 1
        layout.addWidget(self.cmap_combobox, row, col)

        row += 1
        col = 0
        layout.addWidget(orientation_label, row, col)
        col += 1
        layout.addWidget(self.orientation_widget, row, col)

        return widget


# ==== PreviewWindow ==================================================================================================
class PreviewWindow(Window):
    """Simple preview window."""

    def __init__(self, modulator: Modulator, parent: QWidget | None = None):
        self.modulator = modulator
        # self.modulator.sync_settings()
        self.sample = self.modulator.sample

        super().__init__(parent, Qt.WindowType.Dialog)

        self.setWindowTitle(f"{self.modulator.name} Preview")

        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self.setup_preview_widget())

        self.setLayout(layout)

        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.on_update_timer_tick)
        self.update_timer.start(100)  # Update window every 100 ms

    @property
    def modulator(self) -> Modulator:
        return self._modulator

    @modulator.setter
    def modulator(self, device: Modulator):
        self._modulator = device

    @property
    def sample(self) -> SinkSample:
        return self._sample

    @sample.setter
    def sample(self, value: SinkSample):
        self._sample = value

    def setup_preview_widget(self) -> QWidget:
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(2, 2, 2, 2)
        widget.setLayout(layout)

        vstr = "adu"
        if self.modulator.calibration:
            vstr = "m"

        self.preview_figure_widget = ModulatorFigureWidget(self.modulator.blank, self.modulator.vlim, self.modulator.radius, parent=self)
        self.preview_figure_widget.figure.get_cbar_axes().set_title(vstr, size=10)

        if self.preview_figure_widget.toolbar is not None:
            self.preview_figure_widget.toolbar.settingsClicked.connect(self.on_preview_settings_clicked)
            self.preview_figure_widget.toolbar.captureClicked.connect(self.on_preview_capture_clicked)

        layout.addWidget(self.preview_figure_widget)

        return widget

    @Slot(SinkSample)
    def on_sampled(self, sample: SinkSample):
        self._sample = sample

    @Slot()
    def on_preview_settings_clicked(self):
        preview_settings_window = PreviewSettingsWindow(self.preview_figure_widget.cmap_name, self.preview_figure_widget.rotation, self.preview_figure_widget.flip, parent=self)
        preview_settings_window.show()
        preview_settings_window.raise_()
        preview_settings_window.activateWindow()
        preview_settings_window.cmap_combobox.currentTextChanged.connect(self.on_cmap_changed)
        preview_settings_window.orientation_widget.rotationChanged.connect(self.on_rotation_changed)
        preview_settings_window.orientation_widget.flipChanged.connect(self.on_flip_changed)

    @Slot()
    def on_preview_capture_clicked(self):
        default_name = f"command_{datetime.now():%Y%m%d_%H%M%S}.fits"
        filepath, _ = QFileDialog.getSaveFileName(self, "Save Command", str(Path("./data/output") / default_name), "FITS file (*.fits)")
        if not filepath:
            return
        sample = self._sample
        hdu = fits.PrimaryHDU(data=np.array(self.command))
        hdu.header["LACTIME"] = (sample.last_access_time.isoformat(), "Last access time")
        hdu.header["FRMRATE"] = (sample.frame_rate_fps, "Frame rate (fps)")
        hdu.header["CENTER.X"] = (sample.center[0], "Center X")
        hdu.header["CENTER.Y"] = (sample.center[1], "Center Y")
        hdu.header["RADIUS"] = (sample.radius, "Radius (px)")
        hdu.writeto(filepath, overwrite=True)
        logger.info("command saved to %s", filepath)

    @Slot(str)
    def on_cmap_changed(self, colormap: str):
        self.preview_figure_widget.cmap_name = colormap

    @Slot(str)
    def on_rotation_changed(self, rotation: Rotation):
        self.preview_figure_widget.rotation = rotation

    @Slot(str)
    def on_flip_changed(self, flip: Flip):
        self.preview_figure_widget.flip = flip

    @Slot()
    def on_update_timer_tick(self):
        self.preview_figure_widget.figure.get_image().set_data(flip_rotate_frame(self.sample.command, self.preview_figure_widget.flip, self.preview_figure_widget.rotation))
        vmin, vmax = float(self.sample.command.min()), float(self.sample.command.max())
        self.preview_figure_widget.figure.cbar_min_line.set_ydata([vmin, vmin])
        self.preview_figure_widget.figure.cbar_max_line.set_ydata([vmax, vmax])
        self.preview_figure_widget.figure.canvas.draw_idle()
        # logger.info("modulator_window.py - PreviewWindow.on_update_timer_tick()")

    def closeEvent(self, event):
        if self.update_timer.isActive():
            self.update_timer.stop()
        self.deleteLater()
        event.accept()
