from datetime import datetime
from pathlib import Path

import numpy as np
from astropy.io import fits
from matplotlib import colormaps
from matplotlib.colors import LogNorm, Normalize
from pykato.log import setup_logger
from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtWidgets import QButtonGroup, QCheckBox, QComboBox, QFileDialog, QGridLayout, QHBoxLayout, QLabel, QRadioButton, QSizePolicy, QSpacerItem, QVBoxLayout, QWidget

from ..device.camera import Camera, SourceSample
from ..function import Flip, Rotation, flip_rotate_frame, locate_single_airy
from ..widget import DoubleValueSetWidget, OrientationWidget, ROIWidget, Window
from ..widget.figure_widget import SourceFigureWidget, SourceHistFigureWidget

logger = setup_logger("camera_window", terminator="\n")


# ==== HistogramSettingsWindow ========================================================================================
class HistogramSettingsWindow(Window):
    """Settings for the histogram."""

    _allowed_slots_ = Window._allowed_slots_ | {"cmap_name", "cmap_norm", "log_checkbox", "cmap_combobox"}

    def __init__(self, cmap_name: str, cmap_norm: Normalize, parent=None):
        super().__init__(parent, Qt.WindowType.Dialog)

        self.cmap_name: str = cmap_name
        self.cmap_norm: Normalize = cmap_norm

        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setWindowTitle("Preview Settings")
        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self.setup_hist_settings_widget())

        self.setLayout(layout)

    def setup_hist_settings_widget(self) -> QWidget:
        widget = QWidget(self)
        layout = QGridLayout(widget)
        widget.setLayout(layout)

        scale_label = QLabel("Scale", self)
        self.log_checkbox = QCheckBox("Log", self)
        self.log_checkbox.setToolTip("Log Scale")

        if isinstance(self.cmap_norm, LogNorm):
            self.log_checkbox.setChecked(True)
        else:
            self.log_checkbox.setChecked(False)

        cmap_label = QLabel("Colormap", self)
        self.cmap_combobox = QComboBox(self)
        self.cmap_combobox.addItems(list(colormaps))
        self.cmap_combobox.setCurrentIndex(list(colormaps).index(self.cmap_name))

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

        return widget


# ==== InfoWindow =====================================================================================================
class InfoWindow(Window):
    """Camera info window"""

    _allowed_slots_ = Window._allowed_slots_ | {"_camera", "_sample", "update_timer", "info_exposure_time_value_label", "info_frame_rate_value_label", "info_gain_value_label", "info_temperature_value_label", "info_last_access_time_value_label", "info_roi_value_label", "hist_figure_widget", "histogram_settings_window"}

    def __init__(self, camera: Camera, parent=None):
        super().__init__(parent, f=Qt.WindowType.Dialog)

        self._camera = camera
        # self.camera.sync_settings()
        self._sample = self.camera.sample

        self.setWindowTitle(f"{self.camera.name} Information")

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

    @camera.setter
    def camera(self, device: Camera):
        self._camera = device

    @property
    def sample(self) -> SourceSample:
        return self._sample

    @sample.setter
    def sample(self, value: SourceSample):
        self._sample = value

    @Slot(SourceSample)
    def on_sampled(self, sample: SourceSample):
        self._sample = sample

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
        self.info_roi_value_label = QLabel(f"[({self.camera.roi['br'][0]}, {self.camera.roi['br'][1]}),({self.camera.roi['tl'][0]}, {self.camera.roi['tl'][1]})]", self)  # pylint: disable=W1405:inconsistent-quotes
        self.info_roi_value_label.setToolTip("Region of interest [(x1,y1),(x2,y2)]")

        self.hist_figure_widget = SourceHistFigureWidget(self.camera.blank, self.camera.pxmax, parent=self)
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
        layout.addWidget(self.hist_figure_widget, row, col, 1, 2)

        row += 1
        layout.setRowStretch(row, row)

        if (self.camera.link is not None) and self.camera.link.is_connected():
            uri_value_label.setText(f"{self.camera.link.uri}")
            uri_value_label.show()
            uri_label.show()

        return widget

    @Slot()
    def on_histogram_settings_clicked(self):
        self.histogram_settings_window = HistogramSettingsWindow(self.hist_figure_widget.cmap_name, self.hist_figure_widget.cmap_norm, parent=self)
        self.histogram_settings_window.show()
        self.histogram_settings_window.raise_()
        self.histogram_settings_window.activateWindow()
        self.histogram_settings_window.log_checkbox.checkStateChanged.connect(self.on_cmap_norm_changed)
        self.histogram_settings_window.cmap_combobox.currentTextChanged.connect(self.on_cmap_name_changed)

    @Slot(str)
    def on_cmap_name_changed(self, colormap: str):
        self.hist_figure_widget.cmap_name = colormap

    @Slot(bool)
    def on_cmap_norm_changed(self, checked: bool):
        if checked == Qt.CheckState.Checked:
            log_clim = np.floor(np.log10(1)), np.ceil(np.log10(self.camera.clim[1]))
            self.hist_figure_widget.cmap_norm = LogNorm(10 ** log_clim[0], 10 ** log_clim[1])
        else:
            lin_clim = self.camera.clim
            self.hist_figure_widget.cmap_norm = Normalize(lin_clim[0], lin_clim[1])

    @Slot()
    def on_update_timer_tick(self):
        self.info_last_access_time_value_label.setText(f"{self.sample.last_access_time:%Y-%m-%d %H:%M:%S}.{self.sample.last_access_time:%f}"[:-2])
        self.info_exposure_time_value_label.setText(f"{self.sample.exposure_time_s}")
        self.info_gain_value_label.setText(f"{self.sample.gain}")
        self.info_frame_rate_value_label.setText(f"{self.sample.frame_rate_fps:.2f}")
        self.info_temperature_value_label.setText(f"{self.sample.temperature_c}")
        self.info_roi_value_label.setText(f"[({self.sample.roi['br'][0]}, {self.sample.roi['br'][1]}),({self.sample.roi['tl'][0]}, {self.sample.roi['tl'][1]})]")  # pylint: disable=W1405:inconsistent-quotes
        self.hist_figure_widget.figure.set_data(self.sample.capture)
        self.hist_figure_widget.figure.canvas.draw_idle()
        # logger.info("camera_window.py - InfoWindow.on_update_timer_tick()")

    def closeEvent(self, event):
        if self.update_timer.isActive():
            self.update_timer.stop()
        self.deleteLater()
        event.accept()


# ==== SettingsWindow =================================================================================================
class SettingsWindow(Window):
    """Camera settings window."""

    _allowed_slots_ = Window._allowed_slots_ | {"_camera"}

    def __init__(self, camera: Camera, parent: QWidget | None = None):
        super().__init__(parent, Qt.WindowType.Dialog)

        self._camera = camera
        # self.camera.sync_settings()

        self.setWindowTitle(f"{self.camera.name} Settings")

        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self.setup_settings_widget())

        self.setLayout(layout)

    @property
    def camera(self) -> Camera:
        return self._camera

    @camera.setter
    def camera(self, device: Camera):
        self._camera = device

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
                def on_temperature_set_clicked(temperature: float):
                    self.camera.set_temperature_c(temperature)
                    temperature_widget.setValue(self.camera.temperature_c)

                temperature_label = QLabel("Temperature", self)
                temperature_label.setFixedWidth(100)
                temperature_widget = DoubleValueSetWidget(suffix=" \u00b0C", parent=self)
                temperature_widget.spinbox.setRange(10, 30)
                temperature_widget.spinbox.setDecimals(1)
                temperature_widget.spinbox.setSingleStep(0.1)
                temperature_widget.spinbox.setToolTip("Temperature (\u00b0C)")
                temperature_widget.setValue(self.camera.temperature_c)
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
                def on_exposure_time_set_clicked(expTime: float):
                    self.camera.set_exposure_time_s(expTime)
                    expTime_widget.setValue(self.camera.exposure_time_s)

                expTime_label = QLabel("Exposure Time", self)
                expTime_label.setFixedWidth(100)
                expTime_widget = DoubleValueSetWidget(suffix=" s", parent=self)
                expTime_widget.spinbox.setRange(0, 30000000)
                expTime_widget.spinbox.setDecimals(6)
                expTime_widget.spinbox.setSingleStep(0.001)
                expTime_widget.spinbox.setToolTip("Exposure time (s)")
                expTime_widget.setValue(self.camera.exposure_time_s)
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
                def on_gain_set_clicked(gain: float):
                    self.camera.set_gain(gain)
                    gain_widget.setValue(self.camera.gain)

                gain_label = QLabel("Gain", self)
                gain_label.setFixedWidth(100)
                gain_widget = DoubleValueSetWidget(parent=self)
                gain_widget.spinbox.setRange(0, 10)
                gain_widget.spinbox.setDecimals(1)
                gain_widget.spinbox.setSingleStep(0.1)
                gain_widget.spinbox.setToolTip("gain")
                gain_widget.setValue(self.camera.gain)
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
                    self.camera.move_roi(x, y)
                    roi_widget.set_roi(self.camera.roi)

                @Slot()
                def on_center_on_brightest_clicked():
                    guess_radius = 0.5
                    fit_center, _fit_radius, _fit_height = locate_single_airy(self.camera.sample.capture, guess_radius)
                    dx = int(fit_center[0] - self.camera.sample.capture.shape[1] // 2)
                    dy = int(fit_center[1] - self.camera.sample.capture.shape[0] // 2)
                    self.camera.move_roi(dx, dy)
                    roi_widget.set_roi(self.camera.roi)

                roi_label = QLabel("Move ROI", self)
                roi_label.setFixedWidth(100)
                roi_widget = ROIWidget(self.camera.roi, step=8, parent=self)
                roi_widget.roiMoveClicked.connect(on_roi_move_clicked)
                roi_widget.centerClicked.connect(on_center_on_brightest_clicked)
                # ---- roi setting --------------------------------------------------------------------------------------------

                row += 1
                col = 0
                layout.addWidget(roi_label, row, col)
                col += 1
                layout.addWidget(roi_widget, row, col)

        row += 1
        layout.setRowStretch(row, 1)

        return widget

    def closeEvent(self, event):
        self.deleteLater()
        event.accept()


# ==== PreviewSettingsWindow ====================================================================================
class PreviewSettingsWindow(Window):
    """Settings for the simple preview window."""

    _allowed_slots_ = Window._allowed_slots_ | {"cmap_name", "cmap_norm", "rotation", "flip", "log_checkbox", "cmap_combobox", "orientation_widget", "mask_checkbox"}

    def __init__(self, cmap_name: str, cmap_norm: Normalize, rotation: Rotation, flip: Flip, parent: QWidget | None = None):
        super().__init__(parent, Qt.WindowType.Dialog)

        self.cmap_name: str = cmap_name
        self.cmap_norm: Normalize = cmap_norm
        self.rotation: Rotation = rotation
        self.flip: Flip = flip

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

        scale_label = QLabel("Scale", self)
        self.log_checkbox = QCheckBox("Log", self)
        self.log_checkbox.setToolTip("Log Scale")

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
    """Alternate preview window (with orientation control)."""

    _allowed_slots_ = Window._allowed_slots_ | {"_camera", "_sample", "preview_figure_widget", "update_timer", "preview_settings_window"}

    def __init__(self, camera: Camera, parent: QWidget | None = None):
        super().__init__(parent, Qt.WindowType.Dialog)

        self._camera = camera
        # self.camera.sync_settings()
        self._sample = self.camera.sample

        self.setWindowTitle(f"{self.camera.name} Preview")

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

    @camera.setter
    def camera(self, device: Camera):
        self._camera = device

    @property
    def sample(self) -> SourceSample:
        return self._sample

    @sample.setter
    def sample(self, value: SourceSample):
        self._sample = value

    def setup_preview_widget(self) -> QWidget:
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(2, 2, 2, 2)
        widget.setLayout(layout)

        self._sample = self.camera.sample
        self.preview_figure_widget = SourceFigureWidget(self.camera.blank, (0, self.camera.pxmax), parent=self)
        if self.preview_figure_widget.toolbar is not None:
            self.preview_figure_widget.toolbar.settingsClicked.connect(self.on_preview_settings_clicked)
            self.preview_figure_widget.toolbar.captureClicked.connect(self.on_preview_capture_clicked)

        layout.addWidget(self.preview_figure_widget)

        return widget

    @Slot(SourceSample)
    def on_sampled(self, sample: SourceSample):
        self._sample = sample

    @Slot()
    def on_preview_settings_clicked(self):
        self.preview_settings_window = PreviewSettingsWindow(self.preview_figure_widget.cmap_name, self.preview_figure_widget.cmap_norm, self.preview_figure_widget.rotation, self.preview_figure_widget.flip, parent=self)
        self.preview_settings_window.show()
        self.preview_settings_window.raise_()
        self.preview_settings_window.activateWindow()
        self.preview_settings_window.log_checkbox.checkStateChanged.connect(self.on_cmap_norm_changed)
        self.preview_settings_window.cmap_combobox.currentTextChanged.connect(self.on_cmap_name_changed)
        self.preview_settings_window.orientation_widget.rotationChanged.connect(self.on_rotation_changed)
        self.preview_settings_window.orientation_widget.flipChanged.connect(self.on_flip_changed)

    @Slot()
    def on_preview_capture_clicked(self):
        default_name = f"capture_{datetime.now():%Y%m%d_%H%M%S}.fits"
        filepath, _ = QFileDialog.getSaveFileName(self, "Save Capture", str(Path("./data/output") / default_name), "FITS file (*.fits)")
        if not filepath:
            return
        sample = self.sample
        hdu = fits.PrimaryHDU(data=sample.capture)
        hdu.header["LACTIME"] = (sample.last_access_time.isoformat(), "Last access time")
        hdu.header["EXPTIME"] = (sample.exposure_time_s, "Exposure time (s)")
        hdu.header["GAIN"] = (sample.gain, "Gain")
        hdu.header["FRMRATE"] = (sample.frame_rate_fps, "Frame rate (fps)")
        hdu.header["TEMP"] = (sample.temperature_c, "Temperature (deg C)")
        hdu.header["ROI.BR.X"] = (sample.roi["br"][0], "ROI bottom-right X")
        hdu.header["ROI.BR.Y"] = (sample.roi["br"][1], "ROI bottom-right Y")
        hdu.header["ROI.TL.X"] = (sample.roi["tl"][0], "ROI top-left X")
        hdu.header["ROI.TL.Y"] = (sample.roi["tl"][1], "ROI top-left Y")
        hdu.writeto(filepath, overwrite=True)
        logger.info("capture saved to %s", filepath)

    @Slot(str)
    def on_cmap_name_changed(self, colormap: str):
        self.preview_figure_widget.cmap_name = colormap

    @Slot(bool)
    def on_cmap_norm_changed(self, checked: bool):
        if checked == Qt.CheckState.Checked:
            log_clim = np.floor(np.log10(1)), np.ceil(np.log10(self.camera.clim[1]))
            self.preview_figure_widget.cmap_norm = LogNorm(10 ** log_clim[0], 10 ** log_clim[1])
        else:
            lin_clim = self.camera.clim
            self.preview_figure_widget.cmap_norm = Normalize(lin_clim[0], lin_clim[1])

    @Slot(str)
    def on_rotation_changed(self, rotation: Rotation):
        self.preview_figure_widget.rotation = rotation

    @Slot(str)
    def on_flip_changed(self, flip: Flip):
        self.preview_figure_widget.flip = flip

    @Slot()
    def on_update_timer_tick(self):
        self.preview_figure_widget.figure.get_image().set_data(flip_rotate_frame(self.sample.capture, self.preview_figure_widget.flip, self.preview_figure_widget.rotation))
        vmin, vmax = float(self.sample.capture.min()), float(self.sample.capture.max())
        self.preview_figure_widget.figure.cbar_min_line.set_ydata([vmin, vmin])
        self.preview_figure_widget.figure.cbar_max_line.set_ydata([vmax, vmax])
        self.preview_figure_widget.figure.canvas.draw_idle()
        # logger.info("camera_window.py - PreviewWindow.on_update_timer_tick()")

    def closeEvent(self, event):
        if self.update_timer.isActive():
            self.update_timer.stop()
        self.deleteLater()
        event.accept()
