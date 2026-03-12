import numpy as np

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QRadioButton, QSpacerItem, QButtonGroup, QSizePolicy, QGridLayout, QHBoxLayout, QPushButton, QComboBox
from PySide6.QtCore import QTimer, Slot, Qt
from matplotlib import colormaps

from pykato.log import setup_logger
from pykato.function import timestamp_string

from ..widget import Window, OrientationWidget, CenterWidget, DoubleValueSetWidget, FileLoadWidget
from ..function import write_sink_sample_header, write_sink_sample_data, Flip, Rotation, flip_rotate, is_modulator_calibration_file_valid
from ..device.modulator import Modulator, SinkSample, FULL_STROKE_NM
from ..widget.command_preset_widget import ConstantPresetWidget, GradientPresetWidget, CheckerPresetWidget, SinusoidPresetWidget, BoxPresetWidget, PolkaPresetWidget, RegisterPresetWidget, TextPresetWidget, DOTFProbePresetWidget, PairwiseProbePresetWidget
from ..widget.figure_widget import ModulatorFigureWidget, SinkHistFigureWidget

logger = setup_logger("modulator_window", terminator="\n")

PRESETS = ["Constant", "Gradient", "Checker", "Sinusoid", "Box", "Polka", "Register", "Text", "dOTF", "Pairwise"]

# ==== SinkHistSettingsWidget =======================================================================================
class SinkHistSettingsWidget(Window):
    """
    Settings for the simple preview window.
    """

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
    """
    Modulator info window
    """

    def __init__(self, modulator: Modulator, parent: QWidget | None = None):
        self._modulator = modulator
        self._sample = SinkSample(self._modulator.last_access_time, self._modulator.frame_rate_fps, self._modulator.center, self._modulator.radius, self._modulator.blank)

        super().__init__(parent, Qt.WindowType.Dialog)

        self.setWindowTitle(f"{self._modulator.name} Information")

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

    @property
    def sample(self) -> SinkSample:
        return self._sample

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

        self.info_hist_figure_widget = SinkHistFigureWidget(self.modulator.blank, self.modulator.pxmax, parent=self)
        if self.info_hist_figure_widget.toolbar is not None:
            self.info_hist_figure_widget.toolbar.settingsClicked.connect(self.on_info_hist_settings_clicked)

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

        if (self.modulator.link is not None) and self.modulator.link.is_connected():
            uri_value_label.setText(f"{self.modulator.link.uri}")
            uri_value_label.show()
            uri_label.show()

        return widget

    @Slot()
    def on_info_hist_settings_clicked(self):
        info_hist_settings_window = SinkHistSettingsWidget(self.info_hist_figure_widget.cmap_name, parent=self)
        info_hist_settings_window.show()
        info_hist_settings_window.raise_()
        info_hist_settings_window.activateWindow()
        info_hist_settings_window.cmap_combobox.currentTextChanged.connect(self.on_cmap_name_changed)

    @Slot(str)
    def on_cmap_name_changed(self, colormap: str):
        self.info_hist_figure_widget.cmap_name = colormap

    @Slot()
    def on_update_timer_tick(self):
        self.info_last_access_time_value_label.setText(f"{self.sample.last_access_time:%Y-%m-%d %H:%M:%S}.{self.sample.last_access_time:%f}"[:-2])
        self.info_center_value_label.setText(f"({self.sample.center[0]}, {self.sample.center[1]})")
        self.info_radius_value_label.setText(f"{self.sample.radius}")
        self.info_frame_rate_value_label.setText(f"{self.sample.frame_rate_fps:.2f}")
        self.info_hist_figure_widget.figure.set_data(self.sample.command)
        self.info_hist_figure_widget.figure.canvas.draw_idle()

    def closeEvent(self, event):
        if self.update_timer.isActive():
            self.update_timer.stop()
        self.deleteLater()
        event.accept()


# ==== SettingsWindow =================================================================================================
class SettingsWindow(Window):
    """
    Modulator settings window
    """

    def __init__(self, modulator: Modulator, parent: QWidget | None = None):
        self._modulator = modulator
        self._sample = SinkSample(self._modulator.last_access_time, self._modulator.frame_rate_fps, self._modulator.center, self._modulator.radius, self._modulator.blank)

        super().__init__(parent, Qt.WindowType.Dialog)

        self.setWindowTitle(f"{self._modulator.name} Settings")

        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self.setup_settings_widget())
        layout.addWidget(self.setup_command_widget())

        self.setLayout(layout)

    @property
    def modulator(self) -> Modulator:
        return self._modulator

    @property
    def sample(self) -> SinkSample:
        return self._sample

    @Slot(SinkSample)
    def on_sampled(self, sample: SinkSample):
        self._sample = sample

    def setup_settings_widget(self):
        widget = QWidget(self)
        layout = QGridLayout(widget)
        widget.setLayout(layout)

        # ---- radius setting -----------------------------------------------------------------------------------------
        @Slot(int)
        def on_set_radius_clicked(radius: int):
            reply = self.modulator.set_radius(radius)
            logger.info("reply = %s", reply)
            radius_widget.setValue(self.modulator.radius)

        radius_label = QLabel("Radius", self)
        radius_label.setFixedWidth(100)
        radius_widget = DoubleValueSetWidget(suffix=" px", parent=self)
        radius_widget.spinbox.setRange(1, self.modulator.max_radius)
        radius_widget.spinbox.setSingleStep(1)
        radius_widget.spinbox.setDecimals(1)
        radius_widget.setValue(self.modulator.radius)
        radius_widget.spinbox.setSuffix(" px")
        radius_widget.spinbox.setToolTip("Radius")
        radius_widget.valueSetClicked.connect(on_set_radius_clicked)
        # ---- radius setting -----------------------------------------------------------------------------------------

        # ---- center setting -----------------------------------------------------------------------------------------
        @Slot(int, int)
        def on_center_move_clicked(x: int, y: int):
            reply = self.modulator.move_center(x, y)
            logger.info("reply = %s", reply)
            center_widget.set_center(self.modulator.center)

        center_label = QLabel("Move Center", self)
        center_label.setFixedWidth(100)
        center_widget = CenterWidget(self.modulator.center, step=1, parent=self)
        center_widget.centerMoveClicked.connect(on_center_move_clicked)
        # ---- center setting -----------------------------------------------------------------------------------------

        modulator_calibration_label = QLabel("Calibration", self)
        modulator_calibration_label.setFixedWidth(100)
        self.calibration_widget = FileLoadWidget(caption="Open Calibration File", directory="./data/output", file_filter="Fits file (*.fits)", validator=lambda _filename: is_modulator_calibration_file_valid(_filename, self.modulator.full_shape), parent=self)
        self.calibration_widget.setFilepath(self.modulator.calibration_file)

        @Slot()
        def on_calibration_change():
            self.modulator.set_calibration(self.calibration_widget.filepath)

        self.calibration_widget.fileChanged.connect(on_calibration_change)

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
        layout.setRowStretch(row, 1)

        return widget

    def setup_command_widget(self):
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        widget.setLayout(layout)

        @Slot()
        def on_save_clicked():
            timestamp = timestamp_string(frmt="%Y%m%d.%H%M%S", ms=None)
            filename = f"data/output/{timestamp}_command_sink.raw"
            with open(filename, "wb", buffering=0) as fileio:
                write_sink_sample_header(fileio, self.sample)
                write_sink_sample_data(fileio, self.sample)

        @Slot()
        def on_send_clicked():
            self.modulator.push_command(self.preset_widget.command)

        @Slot()
        def on_add_clicked():
            # current = self.modulator.pull_sample()
            # self.modulator.push_command(np.clip(current.command + self.preset_widget.command - np.nanmean(self.preset_widget.command), 0, self.modulator.pxmax))
            pass

        preset_figure_widget = ModulatorFigureWidget(self.modulator.blank, (-FULL_STROKE_NM/2, FULL_STROKE_NM/2), parent=self)

        @Slot(np.ndarray)
        def on_preset_changed(command):
            # if np.any(command > self.modulator.pxmax):
            #     raise ValueError(f"Command values too high {np.max(command)} (max is {self.modulator.pxmax})")
            # elif np.any(command < 0):
            #     raise ValueError(f"Command values too low {np.min(command)} (min is {0})")
            image = np.ma.copy(self.modulator.blank)
            image.data[:] = command[:]

            preset_figure_widget.figure.get_image().set_data(image)
            preset_figure_widget.figure.canvas.draw_idle()

        preset_label = QLabel("Preset", self)
        preset_label.setFixedWidth(100)

        preset_combobox = QComboBox(self)
        for label in PRESETS:
            preset_combobox.addItem(label)
        preset_combobox.setCurrentIndex(0)

        preset_layout = QHBoxLayout()
        preset_layout.addWidget(preset_label)
        preset_layout.addWidget(preset_combobox)

        constant_preset_param_widget = ConstantPresetWidget(self.modulator.shape, FULL_STROKE_NM, self)
        constant_preset_param_widget.changed.connect(on_preset_changed)

        gradient_preset_param_widget = GradientPresetWidget(self.modulator.shape, FULL_STROKE_NM, self)
        gradient_preset_param_widget.changed.connect(on_preset_changed)
        gradient_preset_param_widget.hide()

        checker_preset_param_widget = CheckerPresetWidget(self.modulator.shape, FULL_STROKE_NM, self)
        checker_preset_param_widget.changed.connect(on_preset_changed)
        checker_preset_param_widget.hide()

        sinusoid_preset_param_widget = SinusoidPresetWidget(self.modulator.shape, FULL_STROKE_NM, self)
        sinusoid_preset_param_widget.changed.connect(on_preset_changed)
        sinusoid_preset_param_widget.hide()

        box_preset_param_widget = BoxPresetWidget(self.modulator.shape, FULL_STROKE_NM, self)
        box_preset_param_widget.changed.connect(on_preset_changed)
        box_preset_param_widget.hide()

        polka_preset_param_widget = PolkaPresetWidget(self.modulator.shape, FULL_STROKE_NM, self)
        polka_preset_param_widget.changed.connect(on_preset_changed)
        polka_preset_param_widget.hide()

        register_preset_param_widget = RegisterPresetWidget(self.modulator.shape, FULL_STROKE_NM, self)
        register_preset_param_widget.changed.connect(on_preset_changed)
        register_preset_param_widget.hide()

        text_preset_param_widget = TextPresetWidget(self.modulator.shape, FULL_STROKE_NM, self)
        text_preset_param_widget.changed.connect(on_preset_changed)
        text_preset_param_widget.hide()

        dotf_preset_param_widget = DOTFProbePresetWidget(self.modulator.shape, FULL_STROKE_NM, self)
        dotf_preset_param_widget.changed.connect(on_preset_changed)
        dotf_preset_param_widget.hide()

        pairwise_preset_param_widget = PairwiseProbePresetWidget(self.modulator.shape, FULL_STROKE_NM, self)
        pairwise_preset_param_widget.changed.connect(on_preset_changed)
        pairwise_preset_param_widget.hide()

        save_cmd_button = QPushButton("Save", self)
        save_cmd_button.clicked.connect(on_save_clicked)

        send_cmd_button = QPushButton("Send", self)
        send_cmd_button.clicked.connect(on_send_clicked)

        add_cmd_button = QPushButton("Add to Current", self)
        add_cmd_button.clicked.connect(on_add_clicked)

        button_layout = QHBoxLayout()
        button_layout.addWidget(save_cmd_button)
        button_layout.addWidget(send_cmd_button)

        button_layout.addWidget(add_cmd_button)

        layout.addWidget(preset_figure_widget)
        layout.addLayout(preset_layout)
        layout.addWidget(constant_preset_param_widget)
        layout.addWidget(gradient_preset_param_widget)
        layout.addWidget(checker_preset_param_widget)
        layout.addWidget(sinusoid_preset_param_widget)
        layout.addWidget(box_preset_param_widget)
        layout.addWidget(polka_preset_param_widget)
        layout.addWidget(register_preset_param_widget)
        layout.addWidget(text_preset_param_widget)
        layout.addWidget(dotf_preset_param_widget)
        layout.addWidget(pairwise_preset_param_widget)
        layout.addLayout(button_layout)

        preset_widgets = (constant_preset_param_widget, gradient_preset_param_widget, checker_preset_param_widget, sinusoid_preset_param_widget, box_preset_param_widget, polka_preset_param_widget, register_preset_param_widget, text_preset_param_widget, dotf_preset_param_widget, pairwise_preset_param_widget)
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


# ==== SimplePreviewSettingsWindow ====================================================================================
class SimplePreviewSettingsWindow(Window):
    """
    Settings for the simple preview window.
    """

    def __init__(self, cmap_name: str, parent=None):
        self.cmap_name = cmap_name

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


# ==== PreviewWindow1 =================================================================================================
class SimplePreviewWindow(Window):
    """
    Simple preview window.
    """

    def __init__(self, modulator: Modulator, parent: QWidget | None = None):
        self._modulator = modulator
        self._sample = self._modulator.sample

        super().__init__(parent, Qt.WindowType.Dialog)

        self.setWindowTitle(f"{self._modulator.name} Preview")

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

    @property
    def sample(self) -> SinkSample:
        return self._sample

    @Slot(SinkSample)
    def on_sampled(self, sample: SinkSample):
        self._sample = sample

    def setup_preview_widget(self) -> QWidget:
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(2, 2, 2, 2)
        widget.setLayout(layout)

        self._sample = self.modulator.sample
        self.preview_figure_widget = ModulatorFigureWidget(self.modulator.blank, (-FULL_STROKE_NM/2, FULL_STROKE_NM/2), parent=self)
        if self.preview_figure_widget.toolbar is not None:
            self.preview_figure_widget.toolbar.settingsClicked.connect(self.on_preview_settings_clicked)

        layout.addWidget(self.preview_figure_widget)

        return widget

    @Slot()
    def on_preview_settings_clicked(self):
        preview_settings_window = SimplePreviewSettingsWindow(self.preview_figure_widget.cmap_name, parent=self)
        preview_settings_window.show()
        preview_settings_window.raise_()
        preview_settings_window.activateWindow()
        preview_settings_window.cmap_combobox.currentTextChanged.connect(self.on_cmap_changed)

    @Slot(str)
    def on_cmap_changed(self, colormap: str):
        self.preview_figure_widget.cmap_name = colormap

    @Slot()
    def on_update_timer_tick(self):
        self.preview_figure_widget.figure.get_image().set_data(self.sample.command)
        self.preview_figure_widget.figure.canvas.draw_idle()

    def closeEvent(self, event):
        if self.update_timer.isActive():
            self.update_timer.stop()
        self.deleteLater()
        event.accept()


# ==== AltPreviewWindowWindow =================================================================================
class AltPreviewSettingsWindowWindow(SimplePreviewSettingsWindow):
    """
    Settings for the alternate preview window (with orientation control).
    """

    def __init__(self, cmap_name: str, rotation: Rotation, flip: Flip, parent: QWidget | None = None):
        self.rotation: Rotation = rotation
        self.flip: Flip = flip
        super().__init__(cmap_name, parent=parent)

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


# ==== AltModulatorPreviewWindow =========================================================================================
class AltPreviewWindow(SimplePreviewWindow):
    """
    Alternate preview window (with orientation control).
    """

    def __init__(self, modulator: Modulator, parent: QWidget | None = None):
        super().__init__(modulator, parent=parent)

    @Slot()
    def on_preview_settings_clicked(self):
        preview_settings_window = AltPreviewSettingsWindowWindow(self.preview_figure_widget.cmap_name, self.preview_figure_widget.rotation, self.preview_figure_widget.flip, parent=self)
        preview_settings_window.show()
        preview_settings_window.raise_()
        preview_settings_window.activateWindow()
        preview_settings_window.cmap_combobox.currentTextChanged.connect(self.on_cmap_changed)
        preview_settings_window.orientation_widget.rotationChanged.connect(self.on_rotation_changed)
        preview_settings_window.orientation_widget.flipChanged.connect(self.on_flip_changed)

    @Slot(str)
    def on_rotation_changed(self, rotation: Rotation):
        self.preview_figure_widget.rotation = rotation

    @Slot(str)
    def on_flip_changed(self, flip: Flip):
        self.preview_figure_widget.flip = flip

    @Slot()
    def on_update_timer_tick(self):
        self.preview_figure_widget.figure.get_image().set_data(flip_rotate(self.sample.command, self.preview_figure_widget.flip, self.preview_figure_widget.rotation))
        self.preview_figure_widget.figure.canvas.draw_idle()
