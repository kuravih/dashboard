import numpy as np
from numpy.typing import NDArray

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QRadioButton, QSpacerItem, QButtonGroup, QSizePolicy, QGridLayout, QHBoxLayout, QCheckBox, QComboBox
from PySide6.QtCore import Slot, QTimer, Qt
from matplotlib import colormaps

from pykato.log import setup_logger
from pykato.plotfunction.preset import Histogram_Colorbar_Preset

from ..device.camera import Camera, SourceSample
from ..function import Flip, Rotation, flip_rotate, is_camera_calibration_file_valid
from ..widget import Window, OrientationWidget, ROIWidget, DoubleValueSetWidget, FileLoadWidget
from ..widget.figure_widget import FigureWidget, SourceFigureWidget

logger = setup_logger("camera_window", terminator="\n")


# ==== PreviewSettingsWindow ==========================================================================================
class PreviewSettingsWindow(Window):
    """
    Settings for the camera preview window
    """

    def __init__(self, cmap_name: str, cmap_norm: bool, rotation:Rotation, flip: Flip, orientation_setting: bool = True, alpha_mask: NDArray[np.bool] | None = None, parent=None):
        super().__init__(parent, Qt.WindowType.Dialog)
        self.cmap_name: str = cmap_name
        self.cmap_norm: bool = cmap_norm
        self.rotation: Rotation = rotation
        self.flip: Flip = flip
        self.alpha_mask: NDArray[np.bool] | None = alpha_mask


        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setWindowTitle("Preview Settings")
        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self.setup_preview_settings_widget(orientation_setting))
        self.setLayout(layout)

    def setup_preview_settings_widget(self, orientation_setting: bool) -> QWidget:
        widget = QWidget(self)
        layout = QGridLayout(widget)
        widget.setLayout(layout)

        scale_label = QLabel("Scale", self)
        self.log_checkbox = QCheckBox("Log", self)
        self.log_checkbox.setToolTip("Log Scale")
        self.log_checkbox.setChecked(self.cmap_norm)

        cmap_label = QLabel("Colormap", self)
        self.cmap_combobox = QComboBox(self)
        self.cmap_combobox.addItems(list(colormaps))
        self.cmap_combobox.setCurrentIndex(list(colormaps).index(self.cmap_name))

        orientation_label = QLabel("Orientation", self)
        orientation_label.setFixedWidth(100)
        self.orientation_widget = OrientationWidget(self.rotation, self.flip, self)

        dark_hole_mask_label = QLabel("Dark Hole Mask", self)
        self.mask_checkbox = QCheckBox("Show", self)
        self.mask_checkbox.setToolTip("Show dark hole mask")
        self.mask_checkbox.setChecked(True)

        if self.alpha_mask is not None:
            dark_hole_mask_label.show()
            self.mask_checkbox.show()
            orientation_label.hide()
            self.orientation_widget.hide()
        else:
            dark_hole_mask_label.hide()
            self.mask_checkbox.hide()
            if orientation_setting:
                orientation_label.show()
                self.orientation_widget.show()
            else:
                orientation_label.hide()
                self.orientation_widget.hide()

        row = 0
        col = 0
        layout.addWidget(scale_label, row, col)
        col += 1
        layout.addWidget(self.log_checkbox, row, col)

        row += 1
        col = 0
        layout.addWidget(cmap_label, row, col)
        col += 1
        layout.addWidget(self.cmap_combobox, row, col)


        row += 1
        col = 0
        layout.addWidget(orientation_label, row, col)
        col += 1
        layout.addWidget(self.orientation_widget, row, col)

        row += 1
        col = 0
        layout.addWidget(dark_hole_mask_label, row, col)
        col += 1
        layout.addWidget(self.mask_checkbox, row, col)

        return widget


# ==== PreviewWindow ==================================================================================================
class PreviewWindow(Window):
    """
    Camera preview window
    """

    def __init__(self, camera: Camera, alpha_mask: NDArray[np.bool] | None = None, parent: QWidget | None = None):
        super().__init__(parent, Qt.WindowType.Dialog)
        self._camera = camera
        self._sample = self._camera.sample
        self._alpha_mask = alpha_mask

        self.setWindowTitle(f"{self._camera.name} Preview")

        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self.setup_preview_widget())
        self.setLayout(layout)

        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.on_update_timer_tick)
        self.update_timer.start(100)  # Update window every 100 ms

    @property
    def camera(self) -> Camera:
        return self._camera

    @property
    def sample(self) -> SourceSample:
        return self._sample

    @property
    def alpha_mask(self) -> NDArray[np.bool] | None:
        return self._alpha_mask

    @Slot(SourceSample)
    def on_sampled(self, _sample: SourceSample):
        self._sample = _sample

    def setup_preview_widget(self) -> QWidget:
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(2, 2, 2, 2)
        widget.setLayout(layout)

        self._sample = self.camera.sample
        self.preview_figure_widget = SourceFigureWidget(self.camera.blank, self.camera.pxmax, alpha_mask=self.alpha_mask, parent=self)
        if self.preview_figure_widget.toolbar is not None:
            self.preview_figure_widget.toolbar.settingsClicked.connect(self.on_preview_settings_clicked)

        layout.addWidget(self.preview_figure_widget)

        return widget

    @Slot()
    def on_preview_settings_clicked(self):
        preview_settings_window = PreviewSettingsWindow(cmap_name=self.preview_figure_widget.cmap_name, cmap_norm=self.preview_figure_widget.cmap_norm, rotation=self.preview_figure_widget.rotation, flip=self.preview_figure_widget.flip, alpha_mask=self.alpha_mask, parent=self)
        preview_settings_window.show()
        preview_settings_window.raise_()
        preview_settings_window.activateWindow()
        preview_settings_window.log_checkbox.checkStateChanged.connect(self.on_cmap_norm_changed)
        preview_settings_window.cmap_combobox.currentTextChanged.connect(self.on_cmap_name_changed)
        preview_settings_window.orientation_widget.rotationChanged.connect(self.on_rotation_changed)
        preview_settings_window.orientation_widget.flipChanged.connect(self.on_flip_changed)
        preview_settings_window.mask_checkbox.checkStateChanged.connect(self.on_mask_show_changed)

    @Slot(str)
    def on_cmap_name_changed(self, colormap: str):
        self.preview_figure_widget.cmap_name = colormap

    @Slot(bool)
    def on_cmap_norm_changed(self, checked: bool):
        self.preview_figure_widget.cmap_norm = checked == Qt.CheckState.Checked

    @Slot(str)
    def on_rotation_changed(self, rotation: Rotation):
        self.preview_figure_widget.rotation = rotation

    @Slot(str)
    def on_flip_changed(self, flip: Flip):
        self.preview_figure_widget.flip = flip

    @Slot(bool)
    def on_mask_show_changed(self, checked: Qt.CheckState):
        self.preview_figure_widget.alpha_mask_show = checked == Qt.CheckState.Checked

    @Slot()
    def on_update_timer_tick(self):
        self.preview_figure_widget.figure.get_image().set_data(flip_rotate(self.sample.capture, self.preview_figure_widget.flip, self.preview_figure_widget.rotation))
        self.preview_figure_widget.figure.canvas.draw_idle()

    def closeEvent(self, event):
        if self.update_timer.isActive():
            self.update_timer.stop()
        self.deleteLater()
        event.accept()


# ==== InfoWindow ===============================================================================================
class InfoWindow(Window):
    """
    Camera info window
    """

    def __init__(self, camera: Camera, parent=None):
        super().__init__(parent, Qt.WindowType.Dialog)
        self._camera = camera
        self._sample = SourceSample(self._camera.last_access_time, self._camera.exposure_time_s, self._camera.gain, self._camera.frame_rate_fps, self._camera.temperature_c, self._camera.roi, self._camera.blank)

        self.setWindowTitle(f"{self._camera.name} Information")

        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self.setup_info_widget())
        self.setLayout(layout)

        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.on_update_timer_tick)
        self.update_timer.start(100)  # Update window every 100 ms

    @property
    def camera(self) -> Camera:
        return self._camera

    @property
    def sample(self) -> SourceSample:
        return self._sample

    @Slot(SourceSample)
    def on_sampled(self, _sample: SourceSample):
        self._sample = _sample

    def setup_info_widget(self):
        widget = QWidget(self)
        layout = QGridLayout(widget)
        widget.setLayout(layout)

        name_label = QLabel("Name", self)
        name_label.setFixedWidth(100)
        name_value_label = QLabel(f"{self.camera.name}", self)
        name_value_label.setToolTip("Device Name")

        uri_label = QLabel("URI", self)
        uri_label.hide()
        uri_value_label = QLabel("uri", self)
        uri_value_label.hide()
        uri_value_label.setToolTip("Device URI")

        kind_label = QLabel("Kind", self)
        kind_camera_radiobutton = QRadioButton("CAMERA", self)
        kind_camera_radiobutton.setEnabled(False)
        kind_camera_radiobutton.setToolTip("Device is a Camera")
        kind_slm_radiobutton = QRadioButton("SLM", self)
        kind_slm_radiobutton.setEnabled(False)
        kind_slm_radiobutton.setToolTip("Device is an SLM")
        kind_dm_radiobutton = QRadioButton("DM", self)
        kind_dm_radiobutton.setEnabled(False)
        kind_dm_radiobutton.setToolTip("Device is a DM")
        kind_camera_radiobutton.setChecked(True)
        kind_slm_radiobutton.setChecked(False)
        kind_dm_radiobutton.setChecked(False)

        exposure_time_label = QLabel("Exposure time (s)", self)
        self.info_exposure_time_value_label = QLabel(f"{self.camera.exposure_time_s}", self)
        self.info_exposure_time_value_label.setToolTip("Exposure time (s)")

        frame_rate_label = QLabel("Frame rate (fps)", self)
        self.info_frame_rate_value_label = QLabel(f"{self.camera.frame_rate_fps:.2f}", self)
        self.info_frame_rate_value_label.setToolTip("Frame rate (fps)")

        gain_label = QLabel("Gain", self)
        self.info_gain_value_label = QLabel(f"{self.camera.gain}", self)
        self.info_gain_value_label.setToolTip("Gain")

        temperature_label = QLabel("Temperature (\u00b0C)", self)
        self.info_temperature_value_label = QLabel(f"{self.camera.temperature_c}", self)
        self.info_temperature_value_label.setToolTip("Temperature (\u00b0C)")

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
        serial_value_label = QLabel(f"{self.camera.sn}", self)
        serial_value_label.setToolTip("Stream Device")

        full_label = QLabel("Full", self)
        full_value_label = QLabel(f"{self.camera.full_shape[0]} × {self.camera.full_shape[1]}", self)
        full_value_label.setToolTip("Stream size")

        shape_label = QLabel("Shape", self)
        shape_value_label = QLabel(f"{self.camera.shape[0]} × {self.camera.shape[1]}", self)
        shape_value_label.setToolTip("Stream size")

        creation_time_label = QLabel("Creation time", self)
        creation_time_value_label = QLabel(f"{self.camera.creation_time:%Y-%m-%d %H:%M:%S}.{self.camera.creation_time:%f}"[:-2], self)
        creation_time_value_label.setToolTip("Creation time")

        last_access_time_label = QLabel("Last access time", self)
        self.info_last_access_time_value_label = QLabel(f"{self.camera.last_access_time:%Y-%m-%d %H:%M:%S}.{self.camera.last_access_time:%f}"[:-2], self)
        self.info_last_access_time_value_label.setToolTip("Last access time")

        roi_label = QLabel("ROI", self)
        self.info_roi_value_label = QLabel(f"[({self.camera.roi['br'][0]}, {self.camera.roi['br'][1]})," f"({self.camera.roi['tl'][0]}, {self.camera.roi['tl'][1]})]", self)  # pylint: disable=W1405:inconsistent-quotes
        self.info_roi_value_label.setToolTip("Region of interest [(x1,y1),(x2,y2)]")

        self.info_hist_figure_widget = FigureWidget(Histogram_Colorbar_Preset(self.camera.blank, position="bottom", vmin=0, vmax=self.camera.pxmax, nbins=256), show_toolbar=True)
        self.info_hist_figure_widget.figure.get_histogram_ax().set_ylabel("count", size=10)
        self.info_hist_figure_widget.figure.get_histogram_ax().set_ylim((0, 100))
        self.info_hist_figure_widget.figure.set_vlim(0, self.camera.pxmax)
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
        layout.addWidget(roi_label, row, col)
        col += 1
        layout.addWidget(self.info_roi_value_label, row, col)

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
        layout.addWidget(exposure_time_label, row, col)
        col += 1
        layout.addWidget(self.info_exposure_time_value_label, row, col)

        row += 1
        col = 0
        layout.addWidget(frame_rate_label, row, col)
        col += 1
        layout.addWidget(self.info_frame_rate_value_label, row, col)

        row += 1
        col = 0
        layout.addWidget(gain_label, row, col)
        col += 1
        layout.addWidget(self.info_gain_value_label, row, col)

        row += 1
        col = 0
        layout.addWidget(temperature_label, row, col)
        col += 1
        layout.addWidget(self.info_temperature_value_label, row, col)

        row += 1
        col = 0
        layout.addWidget(self.info_hist_figure_widget, row, col, 1, 2)

        row += 1
        layout.setRowStretch(row, row)

        if (self.camera.link is not None) and self.camera.link.is_connected():
            uri_value_label.setText(f"{self.camera.link.uri}")
            uri_value_label.show()
            uri_label.show()

        return widget

    @Slot()
    def on_update_timer_tick(self):
        # logger.info("InfoWindow.on_update_timer_tick")
        self.info_last_access_time_value_label.setText(f"{self.sample.last_access_time:%Y-%m-%d %H:%M:%S}.{self.sample.last_access_time:%f}"[:-2])
        self.info_exposure_time_value_label.setText(f"{self.sample.exposure_time_s}")
        self.info_gain_value_label.setText(f"{self.sample.gain}")
        self.info_frame_rate_value_label.setText(f"{self.sample.frame_rate_fps:.2f}")
        self.info_temperature_value_label.setText(f"{self.sample.temperature_c}")
        self.info_roi_value_label.setText(f"[({self.sample.roi['br'][0]}, {self.sample.roi['br'][1]})," f"({self.sample.roi['tl'][0]}, {self.sample.roi['tl'][1]})]")  # pylint: disable=W1405:inconsistent-quotes
        self.info_hist_figure_widget.figure.set_data(self.sample.capture)
        self.info_hist_figure_widget.figure.canvas.draw_idle()

    def closeEvent(self, event):
        if self.update_timer.isActive():
            self.update_timer.stop()
        self.deleteLater()
        event.accept()


# ==== SettingsWindow ===========================================================================================
class SettingsWindow(Window):
    """
    Camera settings window
    """

    def __init__(self, camera: Camera, parent=None):
        super().__init__(parent, Qt.WindowType.Dialog)
        self._camera = camera
        self._sample = SourceSample(self._camera.last_access_time, self._camera.exposure_time_s, self._camera.gain, self._camera.frame_rate_fps, self._camera.temperature_c, self._camera.roi, self._camera.blank)

        self.setWindowTitle(f"{self._camera.name} Settings")

        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self.setup_settings_widget())
        self.setLayout(layout)

    @property
    def camera(self) -> Camera:
        return self._camera

    @property
    def sample(self) -> SourceSample:
        return self._sample

    @Slot(SourceSample)
    def on_sampled(self, _sample: SourceSample):
        self._sample = _sample

    def setup_settings_widget(self):
        widget = QWidget(self)
        layout = QGridLayout(widget)
        widget.setLayout(layout)

        row = 0
        col = 0

        if self.camera.settings is not None:
            if "temperature_C" in self.camera.settings:
                # ---- temperature setting --------------------------------------------------------------------------------
                @Slot(float)
                def on_temperature_set_clicked(_temperature: float):
                    reply = self.camera.set_temperature_c(_temperature)
                    logger.info("reply = %s", reply)
                    temperature_widget.setValue(self.camera.temperature_c)

                temperature_label = QLabel("Temperature", self)
                temperature_label.setFixedWidth(100)
                temperature_widget = DoubleValueSetWidget(suffix=" \u00b0C", parent=self)
                temperature_widget.spinbox.setRange(10, 30)
                temperature_widget.spinbox.setDecimals(1)
                temperature_widget.spinbox.setSingleStep(0.1)
                temperature_widget.setValue(self.camera.temperature_c)
                temperature_widget.spinbox.setToolTip("Temperature (\u00b0C)")
                temperature_widget.valueSetClicked.connect(on_temperature_set_clicked)
                # ---- temperature setting --------------------------------------------------------------------------------

                row += 1
                col = 0
                layout.addWidget(temperature_label, row, col)
                col += 1
                layout.addWidget(temperature_widget, row, col)

            if "exposureTime_s" in self.camera.settings:
                # ---- exposure time setting ------------------------------------------------------------------------------
                @Slot(int)
                def on_exposure_time_set_clicked(_expTime: float):
                    reply = self.camera.set_exposure_time_s(_expTime)
                    logger.info("reply = %s", reply)
                    expTime_widget.setValue(self.camera.exposure_time_s)

                expTime_label = QLabel("Exposure Time", self)
                expTime_label.setFixedWidth(100)
                expTime_widget = DoubleValueSetWidget(suffix=" s", parent=self)
                expTime_widget.spinbox.setRange(0, 30000000)
                expTime_widget.spinbox.setDecimals(6)
                expTime_widget.spinbox.setSingleStep(0.001)
                expTime_widget.setValue(self.camera.exposure_time_s)
                expTime_widget.spinbox.setToolTip("Exposure time (s)")
                expTime_widget.valueSetClicked.connect(on_exposure_time_set_clicked)
                # ---- exposure time setting ------------------------------------------------------------------------------

                row += 1
                col = 0
                layout.addWidget(expTime_label, row, col)
                col += 1
                layout.addWidget(expTime_widget, row, col)

            if "gain" in self.camera.settings:

                # ---- gain setting ---------------------------------------------------------------------------------------
                @Slot(int)
                def on_gain_set_clicked(_gain: float):
                    reply = self.camera.set_gain(_gain)
                    logger.info("reply = %s", reply)
                    gain_widget.setValue(self.camera.gain)

                gain_label = QLabel("Gain", self)
                gain_label.setFixedWidth(100)
                gain_widget = DoubleValueSetWidget(parent=self)
                gain_widget.spinbox.setRange(0, 10)
                gain_widget.spinbox.setDecimals(1)
                gain_widget.spinbox.setSingleStep(0.1)
                gain_widget.setValue(self.camera.gain)
                gain_widget.spinbox.setToolTip("gain")
                gain_widget.valueSetClicked.connect(on_gain_set_clicked)
                # ---- gain setting ---------------------------------------------------------------------------------------

                row += 1
                col = 0
                layout.addWidget(gain_label, row, col)
                col += 1
                layout.addWidget(gain_widget, row, col)

            if "roi" in self.camera.settings:

                # ---- roi setting --------------------------------------------------------------------------------------------
                @Slot(int, int)
                def on_roi_move_clicked(x: int, y: int):
                    reply = self.camera.move_roi(x, y)
                    logger.info("reply = %s", reply)
                    roi_widget.set_roi(self.camera.roi)

                roi_label = QLabel("Move ROI", self)
                roi_label.setFixedWidth(100)
                roi_widget = ROIWidget(self.camera.roi, step=8, parent=self)
                roi_widget.roiMoveClicked.connect(on_roi_move_clicked)
                # ---- roi setting --------------------------------------------------------------------------------------------

                row += 1
                col = 0
                layout.addWidget(roi_label, row, col)
                col += 1
                layout.addWidget(roi_widget, row, col)

        camera_calibration_label = QLabel("Camera Calibration", self)
        self.calibration_widget = FileLoadWidget(caption="Open Calibration File", directory="./data/output", file_filter="Fits file (*.fits)", validator=lambda _filename: is_camera_calibration_file_valid(_filename, self.camera.full_shape), parent=self)
        self.calibration_widget.setFilepath(self.camera.calibration_file)

        @Slot()
        def on_calibration_change():
            self.camera.set_calibration(self.calibration_widget.filepath)

        self.calibration_widget.fileChanged.connect(on_calibration_change)

        row += 1
        col = 0
        layout.addWidget(camera_calibration_label, row, col)
        col += 1
        layout.addWidget(self.calibration_widget, row, col)

        row += 1
        layout.setRowStretch(row, 1)

        return widget

    def closeEvent(self, event):
        self.deleteLater()
        event.accept()


# ==== SettingsWindow =================================================================================================
