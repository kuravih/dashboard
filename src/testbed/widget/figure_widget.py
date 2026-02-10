import numpy as np
from numpy.typing import NDArray

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtGui import QAction, QIcon

from pykato.plotfunction.preset import Imshow_Colorbar_Preset, Imshow_Colorbar_Imshow_Colorbar_Preset, Complex_ImageGrid_TwoColorbars_Preset, Complex_Imshow_TwoColorbars_Preset
from pykato.log import setup_logger

import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT
from matplotlib.colors import LogNorm, Normalize

from testbed.function import Flip, Rotation
from testbed.plot.preset import Speckle_Nulling_Process_Plot_Preset, Contrast_Evolution_Plot_Preset

from .resource import ICON_HOUSE, ICON_MOVE, ICON_MAGNIFY, ICON_DISK, ICON_GEAR


logger = setup_logger("figure_widget", terminator="\n")


class NavigationToolbar(NavigationToolbar2QT):
    """
    Navigation toolbar with only the buttons we need
    """

    settingsClicked = Signal()

    toolitems = [t for t in NavigationToolbar2QT.toolitems if t[0] in ("Home", "Pan", "Zoom", "Save")]
    toolitems.append(("Settings", "Settings", "settings", "settings_button_callback"))

    def __init__(self, canvas, parent=None):
        super().__init__(canvas, parent)

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
            else:
                pass

    def settings_button_callback(self):
        self.settingsClicked.emit()


class FigureWidget(QWidget):
    """
    Figure widget
    """

    def __init__(self, figure: Figure | None = None, show_toolbar: bool = False, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        if figure is None:
            figure = plt.figure()
        self.figure_canvas = FigureCanvas(figure)
        self._toolbar = None
        if show_toolbar:
            self._toolbar = NavigationToolbar(self.figure_canvas, self)
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
    """
    Sink Figure widget
    """

    def __init__(self, frame: np.ndarray, pxmax: float, show_toolbar: bool = False, parent=None):
        super().__init__(Imshow_Colorbar_Preset(frame), show_toolbar, parent)
        self.cmap_name: str = "bwr"
        self.rotation = Rotation.UP
        self.flip = Flip.POS

        self.figure.get_image().set_clim(0, pxmax)
        self.figure.get_imshow_ax().set_title("Sink", size=10)
        self.setMinimumSize(100, 100)

        self.set_cmap(self.cmap_name)
        self.set_rotation(self.rotation)
        self.set_flip(self.flip)

    @property
    def cmap_name(self) -> str:
        return self._cmap_name

    @cmap_name.setter
    def cmap_name(self, value: str):
        self._cmap_name = value
        self._cmap = mpl.colormaps[value].copy()
        self._cmap.set_bad(color="black")

    def set_cmap(self, cmap_name: str):
        self.cmap_name = cmap_name
        self.figure.get_image().set_cmap(self._cmap)

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
    """
    Mirror Figure widget
    """

    def __init__(self, frame: np.ndarray, pxmax: float, show_toolbar: bool = False, parent=None):
        super().__init__(frame, pxmax, show_toolbar, parent)
        self.figure.get_imshow_ax().set_title("DM")
        self.figure.get_imshow_ax().set_xlabel("act", size=10)
        self.figure.get_imshow_ax().set_ylabel("act", size=10)
        self.figure.get_imshow_ax().axhline(4.5, alpha=0.25, linewidth=0.5, color="white")
        self.figure.get_imshow_ax().axhline(10.5, alpha=0.25, linewidth=0.5, color="white")
        self.figure.get_imshow_ax().axhline(16.5, alpha=0.25, linewidth=0.5, color="white")
        self.figure.get_imshow_ax().axhline(22.5, alpha=0.25, linewidth=0.5, color="white")
        self.figure.get_imshow_ax().axhline(28.5, alpha=0.25, linewidth=0.5, color="white")
        self.figure.get_imshow_ax().axvline(4.5, alpha=0.25, linewidth=0.5, color="white")
        self.figure.get_imshow_ax().axvline(10.5, alpha=0.25, linewidth=0.5, color="white")
        self.figure.get_imshow_ax().axvline(16.5, alpha=0.25, linewidth=0.5, color="white")
        self.figure.get_imshow_ax().axvline(22.5, alpha=0.25, linewidth=0.5, color="white")
        self.figure.get_imshow_ax().axvline(28.5, alpha=0.25, linewidth=0.5, color="white")
        self.figure.get_cbar_ax().set_title("V", size=10)
        self.setMinimumSize(100, 100)


class ModulatorFigureWidget(SinkFigureWidget):
    """
    Modulator Figure widget
    """

    def __init__(self, frame: np.ndarray, pxmax: float, show_toolbar: bool = False, parent=None):
        super().__init__(frame, pxmax, show_toolbar, parent)
        self.figure.get_imshow_ax().set_title("SLM", size=10)
        self.figure.get_imshow_ax().set_xlabel("px", size=10)
        self.figure.get_imshow_ax().set_ylabel("px", size=10)
        self.figure.get_cbar_ax().set_title("adu", size=10)
        self.figure.get_imshow_ax().axhline(frame.shape[0] / 2 - 0.5, alpha=0.25, linewidth=0.5, color="white")
        self.figure.get_imshow_ax().axvline(frame.shape[1] / 2 - 0.5, alpha=0.25, linewidth=0.5, color="white")
        self.figure.get_imshow_ax().add_patch(patches.Circle((frame.shape[0] / 2 - 0.5, frame.shape[1] / 2 - 0.5), radius=frame.shape[1] / 2, fill=False, alpha=0.25, linewidth=0.5, color="white", transform=self.figure.get_imshow_ax().transData))
        self.setMinimumSize(100, 100)


class SourceFigureWidget(FigureWidget):
    """
    Source Figure widget
    """

    def __init__(self, frame: np.ndarray, pxmax: float, show_toolbar: bool = False, parent=None):
        super().__init__(Imshow_Colorbar_Preset(frame), show_toolbar, parent)
        self.cmap_name: str = "hot"
        self.cmap_log: bool = True
        self.rotation = Rotation.UP
        self.flip = Flip.POS

        self.figure.get_image().set_clim(0, pxmax)
        self.figure.get_imshow_ax().set_title("Source", size=10)
        self.figure.get_imshow_ax().set_xlabel("px", size=10)
        self.figure.get_imshow_ax().set_ylabel("px", size=10)
        self.figure.get_cbar_ax().set_title("adu", size=10)
        self.figure.get_imshow_ax().axhline(frame.shape[0] / 2, alpha=0.25, linewidth=0.5, color="white")
        self.figure.get_imshow_ax().axvline(frame.shape[1] / 2, alpha=0.25, linewidth=0.5, color="white")
        self.figure.get_imshow_ax().add_patch(patches.Circle((frame.shape[0] / 2, frame.shape[1] / 2), radius=225, fill=False, alpha=0.25, linewidth=0.5, color="white", transform=self.figure.get_imshow_ax().transData))
        self.setMinimumSize(100, 100)

        self.set_cmap(self.cmap_name)
        self.set_cmap_norm(self.cmap_log)
        self.set_rotation(self.rotation)
        self.set_flip(self.flip)

    @property
    def cmap_name(self) -> str:
        return self._cmap_name

    @cmap_name.setter
    def cmap_name(self, value: str):
        self._cmap_name = value
        self._cmap = mpl.colormaps[value].copy()
        self._cmap.set_bad(color="black")

    def set_cmap(self, cmap_name: str):
        self.cmap_name = cmap_name
        self.figure.get_image().set_cmap(self._cmap)

    @property
    def cmap_log(self) -> bool:
        return self._cmap_log

    @cmap_log.setter
    def cmap_log(self, value: bool):
        self._cmap_log = value

    def set_cmap_norm(self, checked: bool):
        self.cmap_log = checked
        if self.cmap_log:
            self.figure.get_image().set_norm(LogNorm(vmin=1, vmax=2**12 - 1))
        else:
            self.figure.get_image().set_norm(Normalize(vmin=1, vmax=2**12 - 1))

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


class ContrastFigureWidget(FigureWidget):
    """
    Contrast Figure widget
    """

    def __init__(self, contrast: np.ndarray, n_iteration: int, dark_hole_mask: NDArray[np.bool] | None = None, show_toolbar: bool = False, parent=None):
        super().__init__(Contrast_Evolution_Plot_Preset(contrast, n_iteration, dark_hole_mask), show_toolbar, parent)
        self.cmap_name: str = "jet"
        self.cmap_norm: bool = True
        self.mask_show: bool = True
        self.setMinimumHeight(512)

    def set_contrast(self, contrast: np.ndarray):
        self.figure.set_contrast(contrast)

    def set_contrast_plot(self, contrast_array: np.ndarray):
        self.figure.set_contrast_plot(contrast_array)

    def set_speckle(self, xy: list[float]):
        self.figure.set_speckle(xy)

    @property
    def cmap_name(self) -> str:
        return self.figure.get_cmap_name()

    @cmap_name.setter
    def cmap_name(self, value: str):
        self.figure.set_cmap_name(value)

    @property
    def cmap_norm(self) -> bool:
        return self.figure.get_cmap_norm()

    @cmap_norm.setter
    def cmap_norm(self, value: bool):
        self.figure.set_cmap_norm(value)

    @property
    def mask_show(self) -> bool:
        self.figure.get_mask_show()

    @mask_show.setter
    def mask_show(self, value: bool):
        self.figure.set_mask_show(value)


class SpeckleNullingFigureWidget(FigureWidget):
    """
    Speckle Nulling Figure widget
    """

    def __init__(self, capture: NDArray[np.float64], command: NDArray[np.float64], phs_lim: tuple[float, float], amp_lim: tuple[float, float], dark_hole_mask: NDArray[np.bool] | None = None, show_toolbar: bool = False, parent=None):
        super().__init__(Speckle_Nulling_Process_Plot_Preset(capture, command, phs_lim, amp_lim, dark_hole_mask), show_toolbar, parent)
        self.src_cmap_name: str = "hot"
        self.snk_cmap_name: str = "bwr"
        self.src_cmap_norm: bool = True
        self.src_mask_show: bool = True
        self.setMinimumHeight(512)

    def set_command(self, command: np.ndarray):
        self.figure.set_command(command)

    @property
    def src_cmap_name(self) -> str:
        return self.figure.get_src_cmap_name()

    @src_cmap_name.setter
    def src_cmap_name(self, value: str):
        self.figure.set_src_cmap_name(value)

    @property
    def src_cmap_norm(self) -> bool:
        return self.figure.get_src_cmap_norm()

    @src_cmap_norm.setter
    def src_cmap_norm(self, value: bool):
        self.figure.set_src_cmap_norm(value)

    @property
    def src_mask_show(self) -> bool:
        self.figure.get_src_mask_show()

    @src_mask_show.setter
    def src_mask_show(self, value: bool):
        self.figure.set_src_mask_show(value)

    @property
    def snk_cmap_name(self) -> str:
        return self.figure.get_snk_cmap_name()

    @snk_cmap_name.setter
    def snk_cmap_name(self, value: str):
        self.figure.set_snk_cmap_name(value)

    def set_capture(self, capture: np.ndarray):
        self.figure.set_capture(capture)

    def set_speckle(self, xy: list[float]):
        self.figure.set_speckle(xy)

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


class RecenteringFigureWidget(FigureWidget):
    """
    Recentering Figure widget
    """

    def __init__(self, capture: np.ndarray, command: np.ndarray, show_toolbar: bool = False, parent=None):
        super().__init__(Imshow_Colorbar_Imshow_Colorbar_Preset((capture, command)), show_toolbar=show_toolbar, parent=parent)
        self.src_cmap_name: str = "hot"
        self.snk_cmap_name: str = "bwr"
        self.src_cmap_log: bool = True

        self.image_src, self.image_snk = self.figure.get_images()
        imshow_ax_src, imshow_ax_snk = self.figure.get_imshow_axes()
        cbar_ax_src, cbar_ax_snk = self.figure.get_cbar_axes()

        self.image_snk.set_clim(0, 2**16 - 1)
        imshow_ax_snk.set_title("SLM", size=10)
        imshow_ax_snk.set_xlabel("px", size=10)
        imshow_ax_snk.set_ylabel("px", size=10)
        imshow_ax_snk.axhline(command.shape[0] / 2 - 0.5, alpha=0.25, linewidth=0.5, color="white")
        imshow_ax_snk.axvline(command.shape[1] / 2 - 0.5, alpha=0.25, linewidth=0.5, color="white")
        imshow_ax_snk.add_patch(patches.Circle((command.shape[0] / 2 - 0.5, command.shape[1] / 2 - 0.5), radius=command.shape[1] / 2, fill=False, alpha=0.25, linewidth=0.5, color="white", transform=imshow_ax_snk.transData))
        self.image_snk.set_data(command)

        cbar_ax_snk.set_title("adu", size=10)

        imshow_ax_src.set_title("Source", size=10)
        imshow_ax_src.set_xlabel("px", size=10)
        imshow_ax_src.set_ylabel("px", size=10)
        imshow_ax_src.axhline(capture.shape[0] / 2, alpha=0.25, linewidth=0.5, color="white")
        imshow_ax_src.axvline(capture.shape[1] / 2, alpha=0.25, linewidth=0.5, color="white")
        self.speckles = ((imshow_ax_src.axvline(np.nan, alpha=0.5, linewidth=0.5, color="red"), imshow_ax_src.axhline(np.nan, alpha=0.5, linewidth=0.5, color="red")), (imshow_ax_src.axvline(np.nan, alpha=0.5, linewidth=0.5, color="red"), imshow_ax_src.axhline(np.nan, alpha=0.5, linewidth=0.5, color="red")))
        self.center = (imshow_ax_src.axvline(np.nan, alpha=0.5, linewidth=0.5, color="blue"), imshow_ax_src.axhline(np.nan, alpha=0.5, linewidth=0.5, color="blue"))
        self.center_circle = imshow_ax_src.add_patch(patches.Circle((capture.shape[0] / 2, capture.shape[1] / 2), radius=capture.shape[1] / 2, fill=False, alpha=0.25, linewidth=0.5, color="white", transform=imshow_ax_src.transData))
        self.image_src.set_data(capture)
        imshow_ax_src.set_facecolor("black")

        cbar_ax_src.set_title("adu", size=10)

        self.set_src_cmap(self.src_cmap_name)
        self.set_src_cmap_norm(self.src_cmap_log)
        self.set_snk_cmap(self.snk_cmap_name)

        self.setMinimumHeight(512)

    def set_command(self, command: np.ndarray):
        self.image_snk.set_data(command)

    @property
    def src_cmap_name(self) -> str:
        return self.figure.get_src_cmap_name()

    @src_cmap_name.setter
    def src_cmap_name(self, value: str):
        self.figure.set_src_cmap_name(value)

    @property
    def src_cmap_log(self) -> bool:
        return self.figure.get_src_cmap_log()

    @src_cmap_log.setter
    def src_cmap_log(self, value: bool):
        self.figure.set_src_cmap_log(value)

    @property
    def snk_cmap_name(self) -> str:
        return self.figure.get_snk_cmap_name()

    @snk_cmap_name.setter
    def snk_cmap_name(self, value: str):
        self.figure.set_snk_cmap_name(value)

    def set_capture(self, capture: np.ndarray):
        self.image_src.set_data(capture)

    def set_speckles(self, xys: list[list[float]]):
        self.speckles[0][0].set_xdata([xys[0][0], xys[0][0]])
        self.speckles[0][1].set_ydata([xys[0][1], xys[0][1]])
        self.speckles[1][0].set_xdata([xys[1][0], xys[1][0]])
        self.speckles[1][1].set_ydata([xys[1][1], xys[1][1]])

    def set_center(self, xy: list[float]):
        self.center[0].set_xdata([xy[0], xy[0]])
        self.center[1].set_ydata([xy[1], xy[1]])
        self.center_circle.set_center(xy)

class DOTFSenseFigureWidget(FigureWidget):
    """
    DOTF Figure widget
    """

    def __init__(self, captures: list[np.ndarray], commands: list[np.ndarray], toolbar: bool = False, parent=None):
        super().__init__(Complex_ImageGrid_TwoColorbars_Preset(captures, commands), toolbar, parent)
        # self.figure.set_xlim((shape[0] * 5 // 16, shape[1] * 11 // 16))
        # self.figure.set_ylim((shape[0] * 5 // 16, shape[1] * 11 // 16))
        # self.title = self.figure.suptitle("DOTF", y=0.9, size=10)
        # self.setMinimumSize(100, 100)

        # self.actuator_plots = self.figure.get_plots

        # for index, imshow_ax in enumerate(self.figure.get_imshow_axes()):
        #     imshow_ax.set_xlabel("px", size=10)
        #     if index == 0:
        #         imshow_ax.set_ylabel("px", size=10)


class WavefrontFigureWidget(FigureWidget):
    """
    Wavefront Figure widget
    """

    def __init__(self, shape: tuple[int, int], toolbar: bool = False, parent=None):
        super().__init__(Complex_Imshow_TwoColorbars_Preset(np.zeros(shape, dtype=np.complex64)), toolbar, parent)
