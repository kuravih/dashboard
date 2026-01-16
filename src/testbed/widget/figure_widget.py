from matplotlib import cm
import numpy as np

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtGui import QAction, QIcon

from pykato.plotfunction.preset import Imshow_Colorbar_Preset, Complex_Imshow_TwoColorbars_Preset, Complex_ImageGrid_TwoColorbars_Preset
from pykato.plotfunction.gridspec_layout import GridSpec_Layout
from pykato.log import setup_logger

from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT
from matplotlib.gridspec import GridSpecFromSubplotSpec
from matplotlib.axes import Axes
from matplotlib.image import AxesImage
from matplotlib.axis import Axis
from matplotlib.colors import LogNorm
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

    def __init__(self, _frame: np.ndarray, _pxmax: float, toolbar: bool = False, parent=None):
        super().__init__(Imshow_Colorbar_Preset(_frame), toolbar, parent)
        self.figure.get_image().set_clim(0, _pxmax)
        self.figure.get_imshow_ax().set_title("Sink", size=10)
        self.setMinimumSize(100, 100)


class MirrorFigureWidget(SinkFigureWidget):
    """
    Mirror Figure widget
    """

    def __init__(self, _frame: np.ndarray, _pxmax: float, toolbar: bool = False, parent=None):
        super().__init__(_frame, _pxmax, toolbar, parent)
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

    def __init__(self, _frame: np.ndarray, _pxmax: float, toolbar: bool = False, parent=None):
        super().__init__(_frame, _pxmax, toolbar, parent)
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

    def __init__(self, frame: np.ndarray, mask: np.ndarray, show_toolbar: bool = False, parent=None):
        super().__init__(Imshow_Colorbar_Preset(frame), show_toolbar, parent)
        self.figure.get_image().set_cmap("jet")
        self.figure.get_image().set_norm(LogNorm(vmax=1, vmin=1e-5))
        # self.figure.get_image().set_clim(-5, 0)
        self.figure.get_image().set_alpha(np.where(mask, 1.0, 0.9))
        # self.figure.get_image().set_clim(0, 2**12 - 1)
        self.figure.get_imshow_ax().set_title("Speckle field", size=10)
        self.figure.get_imshow_ax().set_xlabel("px", size=10)
        self.figure.get_imshow_ax().set_ylabel("px", size=10)
        self.figure.get_cbar_ax().set_title("Contrast", size=10)
        self.figure.get_imshow_ax().axhline(frame.shape[0] / 2, alpha=0.25, linewidth=0.5, color="white")
        self.figure.get_imshow_ax().axvline(frame.shape[1] / 2, alpha=0.25, linewidth=0.5, color="white")
        self.figure.get_imshow_ax().add_patch(patches.Circle((frame.shape[0] / 2, frame.shape[1] / 2), radius=225, fill=False, alpha=0.25, linewidth=0.5, color="white", transform=self.figure.get_imshow_ax().transData))
        self.figure.get_imshow_ax().imshow(np.zeros_like(frame), cmap="gray", vmin=0, vmax=1, zorder=-1)
        self.figure.get_imshow_ax().invert_yaxis()
        self.setMinimumSize(100, 100)


class WavefrontFigureWidget(FigureWidget):
    """
    Wavefront Figure widget
    """

    def __init__(self, shape: tuple[int, int], toolbar: bool = False, parent=None):
        super().__init__(Complex_Imshow_TwoColorbars_Preset(np.zeros(shape, dtype=np.complex64)), toolbar, parent)
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

    def __init__(self, toolbar: bool = False, parent=None):
        super().__init__(GridSpec_Layout(1, 1, aspect_ratios=(12,)), toolbar, parent)
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

    def __init__(self, toolbar: bool = False, parent=None):
        super().__init__(GridSpec_Layout(1, 1, aspect_ratios=(12,)), toolbar, parent)
        self.figure.get_axes()[0].set_title("Phase modulation", size=10)
        self.figure.get_axes()[0].set_xlabel("Phase", size=10)
        self.figure.get_axes()[0].set_ylabel("Intensity", size=10)


class SpeckleNullingFigureWidget(FigureWidget):

    def __init__(self, capture: np.ndarray, command: np.ndarray, phs_lim: list[float], amp_lim: list[float], toolbar: bool = False, parent=None):

        super().__init__(GridSpec_Layout(nrows=3, ncols=1, height_ratios=(1, 0.2, 0.2), hspace=0.5), toolbar, parent)

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
        cmap_snk = plt.cm.bwr.copy()
        cmap_snk.set_bad(color="black")
        self._imshow_image_sink = imshow_ax_sink.imshow(command, cmap=cmap_snk)
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
        self._imshow_image_source = imshow_ax_source.imshow(capture, cmap='hot', norm=LogNorm(vmin=1, vmax=2**12 - 1))
        self._imshow_image_source.set_clim(1, 2**12 - 1)
        imshow_ax_source.invert_yaxis()

        divider_source = make_axes_locatable(imshow_ax_source)

        self._colorbar_ax_source = divider_source.append_axes("right", size="5%", pad=0.1)
        self.figure.colorbar(self._imshow_image_source, cax=self._colorbar_ax_source)
        self._colorbar_ax_source.set_title("adu", size=10)

        plot_axes = [self._plot_ax_phs, self._plot_ax_amp]
        imshow_axes = [imshow_ax_sink, imshow_ax_source]
        imshow_images = [self._imshow_image_sink, self._imshow_image_source]
        colorbar_axes = [self._colorbar_ax_sink, self._colorbar_ax_source]

        self.setMinimumHeight(512)

        # -------------------------------------------------------------------------------------------------------------
        def _get_images() -> list[AxesImage]:
            return imshow_images

        self.figure.get_images = _get_images
        # -------------------------------------------------------------------------------------------------------------

        # -------------------------------------------------------------------------------------------------------------
        def _get_imshow_axes() -> list[Axes]:
            return imshow_axes

        self.figure.get_imshow_axes = _get_imshow_axes
        # -------------------------------------------------------------------------------------------------------------

        # -------------------------------------------------------------------------------------------------------------
        def _get_plot_axes() -> list[Axes]:
            return plot_axes

        self.figure.get_plot_axes = _get_plot_axes
        # -------------------------------------------------------------------------------------------------------------

        # -------------------------------------------------------------------------------------------------------------
        def _get_cbar_axes() -> list[Axis]:
            return colorbar_axes

        self.figure.get_cbar_axes = _get_cbar_axes
        # -------------------------------------------------------------------------------------------------------------

    def set_command(self, command: np.ndarray):
        self._imshow_image_sink.set_data(command)

    def set_capture(self, capture: np.ndarray):
        self._imshow_image_source.set_data(capture)

    def set_speckle(self, xy: list[float]):
        self.speckle_x_line.set_xdata([xy[0], xy[0]])
        self.speckle_y_line.set_ydata([xy[1], xy[1]])

    def set_phs_data_plot(self, phs_array:np.ndarray, phs_intensity_data_array:np.ndarray):
        self._phs_data_plot.set_xdata(phs_array)
        self._phs_data_plot.set_ydata(phs_intensity_data_array)

    def set_phs_fit_plot(self, phs_intensity_fit_x_data:np.ndarray, phs_intensity_fit_y_data:np.ndarray):
        self._phs_fit_plot.set_xdata(phs_intensity_fit_x_data)
        self._phs_fit_plot.set_ydata(phs_intensity_fit_y_data)

    def set_amp_data_plot(self, amp_array:np.ndarray, amp_intensity_data_array:np.ndarray):
        self._amp_data_plot.set_xdata(amp_array)
        self._amp_data_plot.set_ydata(amp_intensity_data_array)

    def set_amp_fit_plot(self, amp_intensity_fit_x_data:np.ndarray, amp_intensity_fit_y_data:np.ndarray):
        self._amp_fit_plot.set_xdata(amp_intensity_fit_x_data)
        self._amp_fit_plot.set_ydata(amp_intensity_fit_y_data)

    def set_phs_solve(self, solve:float):
        return self._phs_solve_line.set_xdata([solve, solve])
    
    def set_amp_solve(self, solve:float):
        return self._amp_solve_line.set_xdata([solve, solve])







    # def set_phase_search_data(self, intensity: np.ndarray):
    #     self._phs_data_plot.set_ydata(intensity)

    # def set_amplitude_search_data(self, intensity: np.ndarray):
    #     self._amp_data_plot.set_ydata(intensity)

    # @property
    # def speckle_x(self):
    #     return self.speckle_x_line

    # @property
    # def speckle_y(self):
    #     return self.speckle_y_line

    # @property
    # def sink_image(self):
    #     return self._imshow_image_sink

    # @property
    # def sink_colorbar(self):
    #     return self._colorbar_ax_sink

    # @property
    # def source_image(self):
    #     return self._imshow_image_source

    # @property
    # def source_mask(self):
    #     return self._imshow_image_source_mask

    # @property
    # def source_colorbar(self):
    #     return self._colorbar_ax_source

    @property
    def phs_ax(self):
        return self._plot_ax_phs

    @property
    def amp_ax(self):
        return self._plot_ax_amp

    # @property
    # def phs_data_plot(self):
    #     return self._phs_data_plot

    # @property
    # def amp_data_plot(self):
    #     return self._amp_data_plot

    # @property
    # def phs_fit_plot(self):
    #     return self._phs_fit_plot

    # @property
    # def amp_fit_plot(self):
    #     return self._amp_fit_plot

    # def set_phase_fit_plot(self, amplitude, phase, offset):
    #     self._phs_fit_plot.set_ydata(constrained_sin_fit_fn(np.deg2rad(self.phs_fit_x_data), amplitude, phase, offset))

    # def set_amplitude_fit_plot(self, a, b, c):
    #     self._amp_fit_plot.set_ydata(quadratic_fit_fn(self.amp_fit_x_data, a, b, c))



