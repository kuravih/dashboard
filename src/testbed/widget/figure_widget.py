import numpy as np

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtGui import QAction, QIcon

from pykato.plotfunction.preset import Imshow_Colorbar_Preset, Complex_Imshow_TwoColorbars_Preset, Complex_ImageGrid_TwoColorbars_Preset
from pykato.plotfunction.gridspec_layout import GridSpec_Layout
from pykato.log import setup_logger

import matplotlib as mpl
from matplotlib.colors import Colormap
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT
from matplotlib.gridspec import GridSpecFromSubplotSpec
from matplotlib.axes import Axes
from matplotlib.image import AxesImage
from matplotlib.axis import Axis
from matplotlib.colors import LogNorm, Normalize
from matplotlib.ticker import MaxNLocator
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from mpl_toolkits.axes_grid1 import make_axes_locatable

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

    def __init__(self, _frame: np.ndarray, _pxmax: float, show_toolbar: bool = False, parent=None):
        super().__init__(Imshow_Colorbar_Preset(_frame), show_toolbar, parent)
        self.figure.get_image().set_clim(0, _pxmax)
        self.figure.get_imshow_ax().set_title("Sink", size=10)
        self.setMinimumSize(100, 100)


class MirrorFigureWidget(SinkFigureWidget):
    """
    Mirror Figure widget
    """

    def __init__(self, _frame: np.ndarray, _pxmax: float, show_toolbar: bool = False, parent=None):
        super().__init__(_frame, _pxmax, show_toolbar, parent)
        self.figure.get_imshow_ax().set_title("DM")
        self.figure.get_imshow_ax().set_xlabel("act", size=10)
        self.figure.get_imshow_ax().set_ylabel("act", size=10)
        self.figure.get_image().set_cmap("bwr")
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

    def __init__(self, _frame: np.ndarray, _pxmax: float, show_toolbar: bool = False, parent=None):
        super().__init__(_frame, _pxmax, show_toolbar, parent)
        self.figure.get_imshow_ax().set_title("SLM", size=10)
        self.figure.get_imshow_ax().set_xlabel("px", size=10)
        self.figure.get_imshow_ax().set_ylabel("px", size=10)
        self.figure.get_imshow_ax().axhline(_frame.shape[0] / 2 - 0.5, alpha=0.25, linewidth=0.5, color="white")
        self.figure.get_imshow_ax().axvline(_frame.shape[1] / 2 - 0.5, alpha=0.25, linewidth=0.5, color="white")
        self.figure.get_imshow_ax().add_patch(patches.Circle((_frame.shape[0] / 2 - 0.5, _frame.shape[1] / 2 - 0.5), radius=_frame.shape[1] / 2, fill=False, alpha=0.25, linewidth=0.5, color="white", transform=self.figure.get_imshow_ax().transData))
        self.figure.get_cbar_ax().set_title("adu", size=10)
        self.setMinimumSize(100, 100)


class SourceFigureWidget(FigureWidget):
    """
    Source Figure widget
    """

    def __init__(self, _frame: np.ndarray, _pxmax: float, show_toolbar: bool = False, parent=None):
        super().__init__(Imshow_Colorbar_Preset(_frame), show_toolbar, parent)
        self.figure.get_image().set_clim(0, _pxmax)
        self.figure.get_imshow_ax().set_title("Source", size=10)
        self.figure.get_imshow_ax().set_xlabel("px", size=10)
        self.figure.get_imshow_ax().set_ylabel("px", size=10)
        self.figure.get_cbar_ax().set_title("adu", size=10)
        self.figure.get_imshow_ax().axhline(_frame.shape[0] / 2, alpha=0.25, linewidth=0.5, color="white")
        self.figure.get_imshow_ax().axvline(_frame.shape[1] / 2, alpha=0.25, linewidth=0.5, color="white")
        self.figure.get_imshow_ax().add_patch(patches.Circle((_frame.shape[0] / 2, _frame.shape[1] / 2), radius=225, fill=False, alpha=0.25, linewidth=0.5, color="white", transform=self.figure.get_imshow_ax().transData))
        self.setMinimumSize(100, 100)


class ContrastFigureWidget(FigureWidget):
    """
    Contrast Figure widget
    """

    def __init__(self, measurement: np.ndarray, n_iteration: int, mask: np.ndarray | None = None, cmap: str = "jet", cmap_log: bool = True, mask_show: bool = True, show_toolbar: bool = False, parent=None):
        super().__init__(GridSpec_Layout(1, 1, aspect_ratios=(8,)), show_toolbar=show_toolbar, parent=parent)
        self._mask = mask
        self.cmap_name = cmap
        self.cmap_log = cmap_log
        self.mask_show = mask_show

        (self._image_ax,) = self.figure.get_axes()

        self._image_ax.set_title("Speckles", size=10)
        self._image_ax.set_xlabel("px", size=10)
        self._image_ax.set_ylabel("px", size=10)
        self._image_ax.axhline(measurement.shape[0] / 2 - 0.5, alpha=0.25, linewidth=0.5, color="white")
        self._image_ax.axvline(measurement.shape[1] / 2 - 0.5, alpha=0.25, linewidth=0.5, color="white")
        self.speckle_x_line = self._image_ax.axvline(np.nan, alpha=0.5, linewidth=0.5, color="red")
        self.speckle_y_line = self._image_ax.axhline(np.nan, alpha=0.5, linewidth=0.5, color="red")
        self._image_ax.add_patch(patches.Circle((measurement.shape[0] / 2 - 0.5, measurement.shape[1] / 2 - 0.5), radius=measurement.shape[1] / 2, fill=False, alpha=0.25, linewidth=0.5, color="white", transform=self._image_ax.transData))
        self._imshow_image = self._image_ax.imshow(measurement)
        self._image_ax.set_facecolor("black")
        self._image_ax.invert_yaxis()

        divider = make_axes_locatable(self._image_ax)

        self._colorbar_ax = divider.append_axes("right", size="5%", pad=0.1)
        self.figure.colorbar(self._imshow_image, cax=self._colorbar_ax)
        self._colorbar_ax.set_title("Contrast", size=10)

        self._plot_ax = divider.append_axes("right", size="200%", pad=0.5)
        self._plot_ax.set_title("Evolution", size=10)
        self._plot_ax.set_xlabel("Iteration", size=10)
        self._plot_ax.set_ylabel("", size=10)
        self._plot_ax.set_xlim((0, n_iteration))
        self._plot_ax.set_yticklabels([])
        (self._data_plot,) = self._plot_ax.plot([], [], marker="+", linestyle="None")

        self.set_cmap(self.cmap_name)
        self.set_cmap_norm(self.cmap_log)
        self.set_mask_show(self.mask_show)

        self.setMinimumHeight(512)

    def set_contrast_map(self, contrast_map: np.ndarray):
        self._imshow_image.set_data(contrast_map)

    def set_contrast_array(self, contrast_array: np.ndarray):
        self._data_plot.set_xdata(np.arange(contrast_array.size))
        self._data_plot.set_ydata(contrast_array['avg'])

    def set_speckle(self, xy: list[float]):
        self.speckle_x_line.set_xdata([xy[0], xy[0]])
        self.speckle_y_line.set_ydata([xy[1], xy[1]])

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
        self._imshow_image.set_cmap(self._cmap)

    @property
    def cmap_log(self) -> bool:
        return self._cmap_log

    @cmap_log.setter
    def cmap_log(self, value: bool):
        self._cmap_log = value

    def set_cmap_norm(self, checked: bool):
        self.cmap_log = checked
        if self.cmap_log:
            self._imshow_image.set_norm(LogNorm(vmin=1e-5, vmax=1))
            self._plot_ax.set_yscale("log")
        else:
            self._imshow_image.set_norm(Normalize(vmin=1e-5, vmax=1))
            self._plot_ax.set_yscale("linear")
        self._plot_ax.set_ylim(1e-5, 1)
        self._plot_ax.set_yticklabels([])

    @property
    def mask_show(self) -> bool:
        return self._mask_show

    @mask_show.setter
    def mask_show(self, value: bool):
        self._mask_show = value

    def set_mask_show(self, checked: bool):
        self.mask_show = checked
        if self.mask_show:
            self._imshow_image._alpha = np.where(self._mask, 1.0, 0.9)
        else:
            self._imshow_image._alpha = None


class WavefrontFigureWidget(FigureWidget):
    """
    Wavefront Figure widget
    """

    def __init__(self, shape: tuple[int, int], show_toolbar: bool = False, parent=None):
        super().__init__(Complex_Imshow_TwoColorbars_Preset(np.zeros(shape, dtype=np.complex64)), show_toolbar, parent)
        self.figure.get_imshow_ax().set_title("Wavefront", size=10)
        self.figure.get_imshow_ax().set_xlabel("px", size=10)
        self.figure.get_imshow_ax().set_ylabel("px", size=10)
        self.setMinimumSize(100, 100)


# class DOTFFigureWidget(FigureWidget):
#     """
#     DOTF Figure widget
#     """

#     def __init__(self, shape: Tuple[int, int], count: int = 1, toolbar: bool = False, parent=None):
#         super().__init__(Complex_ImageGrid_TwoColorbars_Preset([np.zeros(shape, dtype=np.complex64)] * count), toolbar, parent)
#         self.figure.plot([[0, 0], [0, 0], [0, 0], [0, 0]], ",", color="red", markersize=1.0, alpha=0.25)
#         self.figure.set_xlim((shape[0] * 5 // 16, shape[1] * 11 // 16))
#         self.figure.set_ylim((shape[0] * 5 // 16, shape[1] * 11 // 16))
#         self.title = self.figure.suptitle("DOTF", y=0.9, size=10)
#         self.setMinimumSize(100, 100)

#         self.actuator_plots = self.figure.get_plots

#         for index, imshow_ax in enumerate(self.figure.get_imshow_axes()):
#             imshow_ax.set_xlabel("px", size=10)
#             if index == 0:
#                 imshow_ax.set_ylabel("px", size=10)


class PhaseModulationFigureWidget(FigureWidget):
    """
    Phase modulation figure widget
    """

    def __init__(self, show_toolbar: bool = False, parent=None):
        super().__init__(GridSpec_Layout(1, 1, aspect_ratios=(12,)), show_toolbar, parent)
        self.figure.get_axes()[0].set_title("Phase modulation", size=10)
        self.figure.get_axes()[0].set_xlabel("Phase", size=10)
        self.figure.get_axes()[0].set_ylabel("Intensity", size=10)

        # self.figure.get_axes()
        # axis.plot(x, log_error, "+", markersize=10)
        # axis.set_ylim(-16, -15)
        # axis.set_ylabel("error")
        # axis.set_xlim(0, 10)
        # axis.set_xlabel("x")


class AmpModulationFigureWidget(FigureWidget):
    """
    Amplitude modulation figure widget
    """

    def __init__(self, show_toolbar: bool = False, parent=None):
        super().__init__(GridSpec_Layout(1, 1, aspect_ratios=(12,)), show_toolbar, parent)
        self.figure.get_axes()[0].set_title("Phase modulation", size=10)
        self.figure.get_axes()[0].set_xlabel("Phase", size=10)
        self.figure.get_axes()[0].set_ylabel("Intensity", size=10)


class SpeckleNullingFigureWidget(FigureWidget):

    def __init__(self, capture: np.ndarray, command: np.ndarray, phs_lim: list[float], amp_lim: list[float], src_mask: np.ndarray | None = None, src_cmap: str = "hot", src_cmap_log: bool = True, src_mask_show: bool = True, snk_cmap: str = "bwr", show_toolbar: bool = False, parent=None):
        super().__init__(GridSpec_Layout(nrows=3, ncols=1, height_ratios=(1, 0.2, 0.2), hspace=0.5), show_toolbar, parent)

        self._src_mask = src_mask
        self.src_cmap_name = src_cmap
        self.snk_cmap_name = snk_cmap
        self.src_cmap_log = src_cmap_log
        self.src_mask_show = src_mask_show

        _image_axes, self._plot_ax_phs, self._plot_ax_amp = self.figure.get_axes()
        _image_axes.remove()

        self._plot_ax_phs.set_title("Phase modulation", size=10)
        self._plot_ax_phs.set_xlabel("Phase", size=10)
        self._plot_ax_phs.set_ylabel("Intensity", size=10)
        self._plot_ax_phs.set_xlim((phs_lim[0], phs_lim[1]))
        self._plot_ax_phs.xaxis.set_major_locator(MaxNLocator(nbins=7))
        (self._phs_data_plot,) = self._plot_ax_phs.plot([], [], marker="+", linestyle="None")
        (self._phs_fit_plot,) = self._plot_ax_phs.plot([], [], color="red")
        self._phs_solve_line = self._plot_ax_phs.axvline(np.nan, color="red")

        self._plot_ax_amp.set_title("Amplitude modulation", size=10)
        self._plot_ax_amp.set_xlabel("Amplitude", size=10)
        self._plot_ax_amp.set_ylabel("Intensity", size=10)
        self._plot_ax_amp.set_xlim((amp_lim[0], amp_lim[-1]))
        (self._amp_data_plot,) = self._plot_ax_amp.plot([], [], marker="+", linestyle="None")
        (self._amp_fit_plot,) = self._plot_ax_amp.plot([], [], color="red")
        self._amp_solve_line = self._plot_ax_amp.axvline(np.nan, color="red")

        gs1 = self.figure.get_gridspec()
        gs2 = GridSpecFromSubplotSpec(nrows=1, ncols=2, subplot_spec=gs1[0])

        imshow_ax_sink = self.figure.add_subplot(gs2[0])
        imshow_ax_sink.set_title("SLM", size=10)
        imshow_ax_sink.set_xlabel("px", size=10)
        imshow_ax_sink.set_ylabel("px", size=10)
        imshow_ax_sink.axhline(command.shape[0] / 2 - 0.5, alpha=0.25, linewidth=0.5, color="white")
        imshow_ax_sink.axvline(command.shape[1] / 2 - 0.5, alpha=0.25, linewidth=0.5, color="white")
        imshow_ax_sink.add_patch(patches.Circle((command.shape[0] / 2 - 0.5, command.shape[1] / 2 - 0.5), radius=command.shape[1] / 2, fill=False, alpha=0.25, linewidth=0.5, color="white", transform=imshow_ax_sink.transData))
        self._imshow_image_sink = imshow_ax_sink.imshow(command)
        self._imshow_image_sink.set_clim(0, 2**16 - 1)
        imshow_ax_sink.invert_yaxis()

        divider_sink = make_axes_locatable(imshow_ax_sink)

        self._colorbar_ax_sink = divider_sink.append_axes("right", size="5%", pad=0.1)
        self.figure.colorbar(self._imshow_image_sink, cax=self._colorbar_ax_sink)
        self._colorbar_ax_sink.set_title("adu", size=10)

        imshow_ax_source = self.figure.add_subplot(gs2[1])
        imshow_ax_source.set_title("Source", size=10)
        imshow_ax_source.set_xlabel("px", size=10)
        imshow_ax_source.set_ylabel("px", size=10)
        imshow_ax_source.axhline(capture.shape[0] / 2, alpha=0.25, linewidth=0.5, color="white")
        imshow_ax_source.axvline(capture.shape[1] / 2, alpha=0.25, linewidth=0.5, color="white")
        self.speckle_x_line = imshow_ax_source.axvline(np.nan, alpha=0.5, linewidth=0.5, color="red")
        self.speckle_y_line = imshow_ax_source.axhline(np.nan, alpha=0.5, linewidth=0.5, color="red")
        imshow_ax_source.add_patch(patches.Circle((capture.shape[0] / 2, capture.shape[1] / 2), radius=225, fill=False, alpha=0.25, linewidth=0.5, color="white", transform=imshow_ax_source.transData))
        self._imshow_image_source = imshow_ax_source.imshow(capture)
        imshow_ax_source.set_facecolor("black")
        imshow_ax_source.invert_yaxis()

        divider_source = make_axes_locatable(imshow_ax_source)

        self._colorbar_ax_source = divider_source.append_axes("right", size="5%", pad=0.1)
        self.figure.colorbar(self._imshow_image_source, cax=self._colorbar_ax_source)
        self._colorbar_ax_source.set_title("adu", size=10)

        self.set_src_cmap(self.src_cmap_name)
        self.set_src_cmap_norm(self.src_cmap_log)
        self.set_src_mask_show(self.src_mask_show)
        self.set_snk_cmap(self.snk_cmap_name)

        self.setMinimumHeight(512)

    def set_command(self, command: np.ndarray):
        self._imshow_image_sink.set_data(command)

    @property
    def src_cmap_name(self) -> str:
        return self._src_cmap_name

    @src_cmap_name.setter
    def src_cmap_name(self, value: str):
        self._src_cmap_name = value
        self._src_cmap = mpl.colormaps[value].copy()
        self._src_cmap.set_bad(color="black")

    def set_src_cmap(self, cmap_name: str):
        self.src_cmap_name = cmap_name
        self._imshow_image_source.set_cmap(self._src_cmap)

    @property
    def src_cmap_log(self) -> bool:
        return self._src_cmap_log

    @src_cmap_log.setter
    def src_cmap_log(self, value: bool):
        self._src_cmap_log = value

    def set_src_cmap_norm(self, checked: bool):
        self.src_cmap_log = checked
        if self.src_cmap_log:
            self._imshow_image_source.set_norm(LogNorm(vmin=1, vmax=2**12 - 1))
        else:
            self._imshow_image_source.set_norm(Normalize(vmin=1, vmax=2**12 - 1))

    @property
    def src_mask_show(self) -> bool:
        return self._src_mask_show

    @src_mask_show.setter
    def src_mask_show(self, value: bool):
        self._src_mask_show = value

    def set_src_mask_show(self, checked: bool):
        self.src_mask_show = checked
        if self.src_mask_show:
            self._imshow_image_source._alpha = np.where(self._src_mask, 1.0, 0.9)
        else:
            self._imshow_image_source._alpha = None

    @property
    def snk_cmap_name(self) -> str:
        return self._snk_cmap_name

    @snk_cmap_name.setter
    def snk_cmap_name(self, value: str):
        self._snk_cmap_name = value
        self._snk_cmap = mpl.colormaps[value].copy()
        self._snk_cmap.set_bad(color="black")

    def set_snk_cmap(self, cmap_name: str):
        self.snk_cmap_name = cmap_name
        self._imshow_image_sink.set_cmap(self._snk_cmap)

    def set_capture(self, capture: np.ndarray):
        self._imshow_image_source.set_data(capture)

    def set_speckle(self, xy: list[float]):
        self.speckle_x_line.set_xdata([xy[0], xy[0]])
        self.speckle_y_line.set_ydata([xy[1], xy[1]])

    def set_phs_data_plot(self, phs_array: np.ndarray, phs_intensity_data_array: np.ndarray):
        self._phs_data_plot.set_xdata(phs_array)
        self._phs_data_plot.set_ydata(phs_intensity_data_array)

    def set_phs_fit_plot(self, phs_intensity_fit_x_data: np.ndarray, phs_intensity_fit_y_data: np.ndarray):
        self._phs_fit_plot.set_xdata(phs_intensity_fit_x_data)
        self._phs_fit_plot.set_ydata(phs_intensity_fit_y_data)

    def set_amp_data_plot(self, amp_array: np.ndarray, amp_intensity_data_array: np.ndarray):
        self._amp_data_plot.set_xdata(amp_array)
        self._amp_data_plot.set_ydata(amp_intensity_data_array)

    def set_amp_fit_plot(self, amp_intensity_fit_x_data: np.ndarray, amp_intensity_fit_y_data: np.ndarray):
        self._amp_fit_plot.set_xdata(amp_intensity_fit_x_data)
        self._amp_fit_plot.set_ydata(amp_intensity_fit_y_data)

    def set_phs_solve(self, solve: float):
        return self._phs_solve_line.set_xdata([solve, solve])

    def set_amp_solve(self, solve: float):
        return self._amp_solve_line.set_xdata([solve, solve])

    @property
    def phs_ax(self):
        return self._plot_ax_phs

    @property
    def amp_ax(self):
        return self._plot_ax_amp
