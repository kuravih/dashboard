import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT
from matplotlib.colors import Normalize
from matplotlib.figure import Figure
from numpy.typing import NDArray
from pykato.function import disk
from pykato.log import setup_logger
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QVBoxLayout, QWidget

from testbed.function import DOTFProbeDirection, Flip, Rotation
from testbed.plot.preset import Contrast_Evolution_Plot_Preset, DOTF_Measurement_Plot_Preset, Histogram_Plot_Preset, Image_Plot_Preset, Speckle_Modulation_Plot_Preset, Wavefront_Plot_Preset

from . import IconButton
from .resource import ICON_CAMERA, ICON_DISK, ICON_GEAR, ICON_HOUSE, ICON_MAGNIFY, ICON_MOVE

logger = setup_logger("figure_widget", terminator="\n")


class NavigationToolbar(NavigationToolbar2QT):
    """Navigation toolbar with only the buttons we need"""

    settingsClicked = Signal()
    captureClicked = Signal()

    def __init__(self, canvas, items: list[str] | None = None, parent: QWidget | None = None):

        if items is None:
            items = ["Home", "Pan", "Zoom", "Save", "Settings", "Capture"]

        original_toolitems = NavigationToolbar2QT.toolitems
        custom_toolitems = [t for t in NavigationToolbar2QT.toolitems if t[0] in items]

        if "Settings" in items:
            custom_toolitems.append(("Settings", "Settings", "settings", "settings_button_callback"))

        if "Capture" in items:
            custom_toolitems.append(("Capture", "Capture", "capture", "capture_button_callback"))

        # temporarily override
        self.toolitems = custom_toolitems

        super().__init__(canvas, parent=parent)

        for action in self.findChildren(QAction):
            if action.text() == "Home":
                action.setIcon(QIcon(ICON_HOUSE))
            elif action.text() == "Pan":
                action.setIcon(QIcon(ICON_MOVE))
            elif action.text() == "Zoom":
                action.setIcon(QIcon(ICON_MAGNIFY))
            elif action.text() == "Save":
                action.setIcon(QIcon(ICON_DISK))
            elif action.text() == "Settings":
                action.setIcon(QIcon(ICON_GEAR))
            elif action.text() == "Capture":
                action.setIcon(QIcon(ICON_CAMERA))

        for action in list(self.actions()):
            if action.isSeparator() or action.icon().isNull():
                continue
            btn = IconButton(action.icon(), flat=True, parent=self)
            btn.setToolTip(action.toolTip())
            btn.setCheckable(action.isCheckable())
            btn.setChecked(action.isChecked())
            btn.clicked.connect(action.trigger)
            action.toggled.connect(btn.setChecked)
            self.insertWidget(action, btn)
            self.removeAction(action)

        self.toolitems = original_toolitems

    def settings_button_callback(self):
        self.settingsClicked.emit()

    def capture_button_callback(self):
        self.captureClicked.emit()


class FigureWidget(QWidget):
    """Figure widget"""

    def __init__(self, figure: Figure | None = None, toolitems: list[str] | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout()
        if figure is None:
            figure = plt.figure()
        self.figure_canvas = FigureCanvas(figure)
        self._toolbar = None
        if toolitems != []:
            self._toolbar = NavigationToolbar(self.figure_canvas, toolitems, parent=self)
            layout.addWidget(self._toolbar)
        layout.addWidget(self.figure_canvas)

        self.setLayout(layout)

    @property
    def toolbar(self) -> NavigationToolbar | None:
        return self._toolbar

    @property
    def figure(self) -> Figure:
        return self.figure_canvas.figure

    @figure.setter
    def figure(self, figure: Figure):
        self.figure_canvas.figure = figure


class SinkFigureWidget(FigureWidget):
    """Sink Figure widget"""

    def __init__(self, frame: np.ndarray, vlim: tuple[float, float], radius: float | None = None, toolitems: list[str] | None = None, parent: QWidget | None = None):
        super().__init__(Image_Plot_Preset(frame, cmap_name="bwr", mask=np.zeros_like(frame)), toolitems, parent=parent)
        self.figure.get_imshow_axes().get_mask().set_cmap("Greys_r")
        if radius is not None:
            mask = 0.5 * (1.0 - disk(frame.shape, radius))
            self.figure.get_imshow_axes().get_mask().set_alpha(mask)
        self.rotation = Rotation.UP
        self.flip = Flip.POS

        self.figure.get_image().set_clim(*vlim)
        self.figure.get_imshow_axes().set_title("Sink", size=10)
        self.setMinimumSize(100, 100)

        self.set_rotation(self.rotation)
        self.set_flip(self.flip)

    @property
    def cmap_name(self) -> str:
        return self.figure.get_image().get_cmap_name()

    @cmap_name.setter
    def cmap_name(self, value: str):
        self.figure.get_image().set_cmap_name(value)

    @property
    def rotation(self) -> Rotation:
        return self._rotation

    @rotation.setter
    def rotation(self, value: Rotation):
        self._rotation = value

    def set_rotation(self, rotation: Rotation):
        self.rotation = rotation

    @property
    def flip(self) -> Flip:
        return self._flip

    @flip.setter
    def flip(self, value: Flip):
        self._flip = value

    def set_flip(self, flip: Flip):
        self.flip = flip


class MirrorFigureWidget(SinkFigureWidget):
    """Mirror Figure widget"""

    def __init__(self, frame: np.ndarray, vlim: tuple[float, float], toolitems: list[str] | None = None, parent: QWidget | None = None):
        super().__init__(frame, vlim, toolitems, parent=parent)
        self.figure.get_imshow_ax().set_title("DM")
        self.figure.get_imshow_ax().set_xlabel("act", size=10)
        self.figure.get_imshow_ax().set_ylabel("act", size=10)
        self.figure.get_imshow_ax().axhline(4, alpha=0.25, linewidth=0.5, color="white")
        self.figure.get_imshow_ax().axhline(10, alpha=0.25, linewidth=0.5, color="white")
        self.figure.get_imshow_ax().axhline(16, alpha=0.25, linewidth=0.5, color="white")
        self.figure.get_imshow_ax().axhline(22, alpha=0.25, linewidth=0.5, color="white")
        self.figure.get_imshow_ax().axhline(28, alpha=0.25, linewidth=0.5, color="white")
        self.figure.get_imshow_ax().axvline(4, alpha=0.25, linewidth=0.5, color="white")
        self.figure.get_imshow_ax().axvline(10, alpha=0.25, linewidth=0.5, color="white")
        self.figure.get_imshow_ax().axvline(16, alpha=0.25, linewidth=0.5, color="white")
        self.figure.get_imshow_ax().axvline(22, alpha=0.25, linewidth=0.5, color="white")
        self.figure.get_imshow_ax().axvline(28, alpha=0.25, linewidth=0.5, color="white")
        self.figure.get_cbar_ax().set_title("V", size=10)
        self.setMinimumSize(100, 100)


class ModulatorFigureWidget(SinkFigureWidget):
    """Modulator Figure widget"""

    def __init__(self, command: np.ndarray, vlim: tuple[float, float], radius: float | None = None, toolitems: list[str] | None = None, parent: QWidget | None = None):
        super().__init__(command, vlim, radius, toolitems, parent=parent)
        self.figure.get_imshow_axes().set_title("SLM", size=10)
        self.figure.get_imshow_axes().set_xlabel("px", size=10)
        self.figure.get_imshow_axes().set_ylabel("px", size=10)
        self.figure.get_cbar_axes().set_title("adu", size=10)
        self.setMinimumSize(100, 100)


class SourceFigureWidget(FigureWidget):
    """Source Figure widget"""

    def __init__(self, frame: np.ndarray, clim: tuple[float, float], rotation: Rotation = Rotation.UP, flip: Flip = Flip.POS, mask: NDArray[np.bool] | None = None, toolitems: list[str] | None = None, parent: QWidget | None = None):
        super().__init__(Image_Plot_Preset(frame, cmap_name="hot", cmap_norm=Normalize(*clim), mask=mask), toolitems, parent)
        self.rotation = rotation
        self.flip = flip
        self.figure.get_imshow_axes().set_title("Source", size=10)
        self.figure.get_imshow_axes().set_xlabel("px", size=10)
        self.figure.get_imshow_axes().set_xlim((0 - 0.5, frame.shape[1] - 1 + 0.5))
        self.figure.get_imshow_axes().set_ylabel("px", size=10)
        self.figure.get_imshow_axes().set_ylim((0 - 0.5, frame.shape[0] - 1 + 0.5))
        self.figure.get_cbar_axes().set_title("adu", size=10)
        self.setMinimumSize(100, 100)

        self._drag_mode: str | None = None
        self._drag_offset: tuple[float, float] | None = None

        cx, cy = frame.shape[1] / 2, frame.shape[0] / 2
        r = 0.8 * frame.shape[0] / 2
        self.circle = patches.Circle((cx, cy), radius=r, fill=False, alpha=0.25, linewidth=0.5, color="white")
        self.figure.get_imshow_axes().add_patch(self.circle)
        self.hline = self.figure.get_imshow_axes().axhline(cy, color="white", linewidth=0.5, alpha=0.25)
        self.vline = self.figure.get_imshow_axes().axvline(cx, color="white", linewidth=0.5, alpha=0.25)
        self._original_center: tuple[float, float] = (cx, cy)
        self._original_radius: float = r

        self.figure_canvas.mpl_connect("button_press_event", self._on_select_press)
        self.figure_canvas.mpl_connect("motion_notify_event", self._on_select_motion)
        self.figure_canvas.mpl_connect("button_release_event", self._on_select_release)

    @property
    def cmap_name(self) -> str:
        return self.figure.get_image().get_cmap_name()

    @cmap_name.setter
    def cmap_name(self, value: str):
        self.figure.get_image().set_cmap_name(value)

    @property
    def clim(self) -> tuple[float, float]:
        return self.figure.get_image().get_clim()

    @clim.setter
    def clim(self, lim: tuple[float, float]):
        self.figure.get_image().set_clim(lim)

    @property
    def cmap_norm(self) -> Normalize:
        return self.figure.get_image().get_cmap_norm()

    @cmap_norm.setter
    def cmap_norm(self, value: Normalize):
        self.figure.get_image().set_cmap_norm(value)

    @property
    def mask_show(self) -> bool:
        return self.figure.get_image().get_mask_show()

    @mask_show.setter
    def mask_show(self, value: bool):
        self.figure.get_image().set_mask_show(value)

    @property
    def rotation(self) -> Rotation:
        return self._rotation

    @rotation.setter
    def rotation(self, value: Rotation):
        self._rotation = value

    @property
    def flip(self) -> Flip:
        return self._flip

    @flip.setter
    def flip(self, value: Flip):
        self._flip = value

    def _hit_test(self, x: float, y: float, ax) -> str | None:
        cx, cy = self.circle.center
        t = ax.transData
        click_px = t.transform([x, y])
        center_px = t.transform([cx, cy])
        edge_px = t.transform([cx + self.circle.get_radius(), cy])
        dist_px = np.hypot(click_px[0] - center_px[0], click_px[1] - center_px[1])
        radius_px = np.hypot(edge_px[0] - center_px[0], edge_px[1] - center_px[1])
        if dist_px < 8:
            return "move"
        if abs(dist_px - radius_px) < 8:
            return "resize"
        return None

    def _select(self):
        self.circle.set_alpha(0.5)
        self.circle.set_linewidth(1)
        self.circle.set_linestyle("--")
        self.hline.set_alpha(0.5)
        self.hline.set_linewidth(1)
        self.hline.set_linestyle("--")
        self.vline.set_alpha(0.5)
        self.vline.set_linewidth(1)
        self.vline.set_linestyle("--")
        self.figure_canvas.draw_idle()

    def _deselect(self):
        self.circle.set_alpha(0.25)
        self.circle.set_linewidth(0.5)
        self.circle.set_linestyle("-")
        self.hline.set_alpha(0.25)
        self.hline.set_linewidth(0.5)
        self.hline.set_linestyle("-")
        self.vline.set_alpha(0.25)
        self.vline.set_linewidth(0.5)
        self.vline.set_linestyle("-")
        self._drag_mode = None
        self._drag_offset = None
        self.figure_canvas.draw_idle()

    def _reset_circle(self):
        self.circle.set_center(self._original_center)
        self.circle.set_radius(self._original_radius)
        self.hline.set_ydata([self._original_center[1], self._original_center[1]])
        self.vline.set_xdata([self._original_center[0], self._original_center[0]])
        self.figure_canvas.draw_idle()

    def _on_select_press(self, event):
        if self._toolbar is not None and self._toolbar.mode:
            return
        if event.inaxes is None or event.button != 1:
            self._deselect()
            return
        hit = self._hit_test(event.xdata, event.ydata, event.inaxes)
        if hit is not None:
            if event.dblclick and hit == "move":
                self._reset_circle()
                return
            self._select()
            self._drag_mode = hit
            if hit == "move":
                cx, cy = self.circle.center
                self._drag_offset = (cx - event.xdata, cy - event.ydata)
        else:
            self._deselect()

    def _on_select_motion(self, event):
        if event.inaxes is None:
            return
        if self._drag_mode is None:
            if self._toolbar is not None and self._toolbar.mode:
                return
            hit = self._hit_test(event.xdata, event.ydata, event.inaxes)
            if hit == "move":
                self.figure_canvas.setCursor(Qt.CursorShape.SizeAllCursor)
            elif hit == "resize":
                self.figure_canvas.setCursor(Qt.CursorShape.SizeBDiagCursor)
            else:
                self.figure_canvas.setCursor(Qt.CursorShape.ArrowCursor)
            return
        if self._drag_mode == "move" and self._drag_offset is not None:
            new_center = (event.xdata + self._drag_offset[0], event.ydata + self._drag_offset[1])
            self.circle.set_center(new_center)
            self.hline.set_ydata([new_center[1], new_center[1]])
            self.vline.set_xdata([new_center[0], new_center[0]])
        elif self._drag_mode == "resize":
            cx, cy = self.circle.center
            radius = np.hypot(event.xdata - cx, event.ydata - cy)
            self.circle.set_radius(radius)
        self.figure_canvas.draw_idle()

    def _on_select_release(self, event):
        self._drag_mode = None
        self._drag_offset = None


class SourceHistFigureWidget(FigureWidget):
    """Source Histogram Figure widget"""

    def __init__(self, frame: np.ndarray, pxmax: float, toolitems: list[str] | None = None, parent: QWidget | None = None):
        super().__init__(Histogram_Plot_Preset(frame, cmap_name="hot", cmap_norm=Normalize(0, pxmax)), toolitems, parent)
        self.figure.get_histogram_axes().set_ylabel("count", size=10)
        self.figure.get_histogram_axes().set_ylim((0, 100))
        self.figure.get_cbar_axes().set_xlabel("nadu", size=10)

        self.setMinimumSize(100, 100)

    @property
    def cmap_name(self) -> str:
        return self.figure.get_cmap_name()

    @cmap_name.setter
    def cmap_name(self, value: str):
        self.figure.set_cmap_name(value)

    @property
    def cmap_norm(self) -> Normalize:
        return self.figure.get_cmap_norm()

    @cmap_norm.setter
    def cmap_norm(self, value: Normalize):
        self.figure.set_cmap_norm(value)


class SinkHistFigureWidget(FigureWidget):
    """Sink Histogram Figure widget"""

    def __init__(self, frame: np.ndarray, pxmax: float, toolitems: list[str] | None = None, parent: QWidget | None = None):
        super().__init__(Histogram_Plot_Preset(frame, cmap_name="bwr", cmap_norm=Normalize(0, pxmax)), toolitems, parent)
        self.figure.get_histogram_axes().set_ylabel("count", size=10)
        self.figure.get_histogram_axes().set_ylim((0, 100))
        self.figure.get_cbar_axes().set_xlabel("nadu", size=10)

        self.setMinimumSize(100, 100)

    @property
    def cmap_name(self) -> str:
        return self.figure.get_cmap_name()

    @cmap_name.setter
    def cmap_name(self, value: str):
        self.figure.set_cmap_name(value)


class ContrastFigureWidget(FigureWidget):
    """Contrast Figure widget"""

    def __init__(self, contrast: np.ndarray, n_iteration: int, dark_hole_mask: NDArray[np.float64], toolitems: list[str] | None = None, parent: QWidget | None = None):
        super().__init__(Contrast_Evolution_Plot_Preset(contrast, n_iteration, dark_hole_mask), toolitems, parent)
        self.setMinimumHeight(512)

    def set_contrast_map_data(self, contrast_map: np.ndarray):
        self.figure.get_image().set_data(contrast_map)

    def set_contrast_curve_data(self, contrast_curve):
        self.figure.get_plot().set_xdata(np.arange(contrast_curve.size))
        self.figure.get_plot().set_ydata(contrast_curve["avg"])

    def set_speckle_location_data(self, speckle_location: list[float]):
        self.figure.get_speckle().set_xdata([speckle_location[0]])
        self.figure.get_speckle().set_ydata([speckle_location[1]])

    @property
    def cmap_name(self) -> str:
        return self.figure.get_image().get_cmap_name()

    @cmap_name.setter
    def cmap_name(self, value: str):
        self.figure.get_image().set_cmap_name(value)

    @property
    def cmap_norm(self) -> Normalize:
        return self.figure.get_image().get_cmap_norm()

    @cmap_norm.setter
    def cmap_norm(self, value: Normalize):
        self.figure.get_image().set_cmap_norm(value)

    @property
    def mask_show(self) -> bool:
        return self.figure.get_image().get_mask_show()

    @mask_show.setter
    def mask_show(self, value: bool):
        self.figure.get_image().set_mask_show(value)


class SpeckleNullingFigureWidget(FigureWidget):
    """Speckle Nulling Figure widget"""

    def __init__(self, phs_lim: tuple[float, float], amp_lim: tuple[float, float], toolitems: list[str] | None = None, parent: QWidget | None = None):
        super().__init__(Speckle_Modulation_Plot_Preset(phs_lim, amp_lim), toolitems, parent)
        self.setMinimumHeight(512)

    def set_phs_data_plot(self, phs_array: np.ndarray, phs_intensity_data_array: np.ndarray):
        self.figure.set_phs_data_plot(phs_array, phs_intensity_data_array)

    def set_phs_fit_plot(self, phs_intensity_fit_x_data: np.ndarray, phs_intensity_fit_y_data: np.ndarray):
        self.figure.set_phs_fit_plot(phs_intensity_fit_x_data, phs_intensity_fit_y_data)

    def set_amp_data_plot(self, amp_array: np.ndarray, amp_intensity_data_array: np.ndarray):
        self.figure.set_amp_data_plot(amp_array, amp_intensity_data_array)

    def set_amp_fit_plot(self, amp_intensity_fit_x_data: np.ndarray, amp_intensity_fit_y_data: np.ndarray):
        self.figure.set_amp_fit_plot(amp_intensity_fit_x_data, amp_intensity_fit_y_data)

    def set_phs_solve(self, solve: float):
        self.figure.set_phs_solve(solve)

    def set_amp_solve(self, solve: float):
        self.figure.set_amp_solve(solve)

    @property
    def phs_ax(self):
        return self.figure.phs_ax()

    @property
    def amp_ax(self):
        return self.figure.amp_ax()


class DOTFMeasureFigureWidget(FigureWidget):
    """DOTF measure figure widget"""

    def __init__(self, measure_dict: dict[DOTFProbeDirection, NDArray[np.complex64]], toolitems: list[str] | None = None, parent: QWidget | None = None):
        super().__init__(DOTF_Measurement_Plot_Preset(measure_dict), toolitems, parent=parent)
        self.setMinimumHeight(512)

    def set_dotf_map_data(self, probe: DOTFProbeDirection, dotf_map: NDArray[np.complex64]):
        self.figure.get_image_dict()[probe].set_data(dotf_map)


class WavefrontFigureWidget(FigureWidget):
    """Wavefront figure widget"""

    def __init__(self, wavefront: NDArray[np.complex64], toolitems: list[str] | None = None, parent: QWidget | None = None):
        super().__init__(Wavefront_Plot_Preset(wavefront), toolitems, parent)

    def set_wavefront_data(self, wavefront: NDArray[np.complex64], abs_min: float | None = None, abs_max: float | None = None):
        self.figure.get_image().set_data(wavefront, abs_min, abs_max)
