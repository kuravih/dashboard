import numpy as np

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtGui import QAction, QIcon

from pykato.plotfunction.preset import Imshow_Colorbar_Preset, Imshow_Colorbar_Imshow_Colorbar_Preset
from pykato.plotfunction.gridspec_layout import GridSpec_Layout
from pykato.log import setup_logger

import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT
from matplotlib.gridspec import GridSpecFromSubplotSpec
from matplotlib.colors import LogNorm, Normalize
from matplotlib.ticker import MaxNLocator
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

    def __init__(self, frame: np.ndarray, pxmax: float, show_toolbar: bool = False, parent=None):
        super().__init__(Imshow_Colorbar_Preset(frame), show_toolbar, parent)
        self.figure.get_image().set_clim(0, pxmax)
        self.figure.get_imshow_ax().set_title("Sink", size=10)
        self.setMinimumSize(100, 100)


class MirrorFigureWidget(SinkFigureWidget):
    """
    Mirror Figure widget
    """

    def __init__(self, frame: np.ndarray, pxmax: float, show_toolbar: bool = False, parent=None):
        super().__init__(frame, pxmax, show_toolbar, parent)
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

    def __init__(self, frame: np.ndarray, pxmax: float, show_toolbar: bool = False, parent=None):
        super().__init__(frame, pxmax, show_toolbar, parent)
        self.figure.get_imshow_ax().set_title("SLM", size=10)
        self.figure.get_imshow_ax().set_xlabel("px", size=10)
        self.figure.get_imshow_ax().set_ylabel("px", size=10)
        self.figure.get_image().set_cmap("bwr")
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
        self.figure.get_image().set_clim(0, pxmax)
        self.figure.get_imshow_ax().set_title("Source", size=10)
        self.figure.get_imshow_ax().set_xlabel("px", size=10)
        self.figure.get_imshow_ax().set_ylabel("px", size=10)
        self.figure.get_image().set_cmap("hot")
        self.figure.get_cbar_ax().set_title("adu", size=10)
        self.figure.get_imshow_ax().axhline(frame.shape[0] / 2, alpha=0.25, linewidth=0.5, color="white")
        self.figure.get_imshow_ax().axvline(frame.shape[1] / 2, alpha=0.25, linewidth=0.5, color="white")
        self.figure.get_imshow_ax().add_patch(patches.Circle((frame.shape[0] / 2, frame.shape[1] / 2), radius=225, fill=False, alpha=0.25, linewidth=0.5, color="white", transform=self.figure.get_imshow_ax().transData))
        self.setMinimumSize(100, 100)


class ContrastFigureWidget(FigureWidget):
    """
    Contrast Figure widget
    """

    def __init__(self, measurement: np.ndarray, n_iteration: int, mask: np.ndarray | None = None, show_toolbar: bool = False, parent=None):
        super().__init__(GridSpec_Layout(1, 1, aspect_ratios=(8,)), show_toolbar=show_toolbar, parent=parent)
        self.mask = mask
        self.cmap_name: str = "jet"
        self.cmap_log: bool = True
        self.mask_show: bool = True

        (self.image_ax,) = self.figure.get_axes()

        self.image_ax.set_title("Speckles", size=10)
        self.image_ax.set_xlabel("px", size=10)
        self.image_ax.set_ylabel("px", size=10)
        self.image_ax.axhline(measurement.shape[0] / 2 - 0.5, alpha=0.25, linewidth=0.5, color="white")
        self.image_ax.axvline(measurement.shape[1] / 2 - 0.5, alpha=0.25, linewidth=0.5, color="white")
        self.speckle = (self.image_ax.axvline(np.nan, alpha=0.5, linewidth=0.5, color="red"), self.image_ax.axhline(np.nan, alpha=0.5, linewidth=0.5, color="red"))
        self.image_ax.add_patch(patches.Circle((measurement.shape[0] / 2 - 0.5, measurement.shape[1] / 2 - 0.5), radius=measurement.shape[1] / 2, fill=False, alpha=0.25, linewidth=0.5, color="white", transform=self.image_ax.transData))
        self.imshow_image = self.image_ax.imshow(measurement)
        self.image_ax.set_facecolor("black")
        self.image_ax.invert_yaxis()

        divider = make_axes_locatable(self.image_ax)

        self.colorbar_ax = divider.append_axes("right", size="5%", pad=0.1)
        self.figure.colorbar(self.imshow_image, cax=self.colorbar_ax)
        self.colorbar_ax.set_title("Contrast", size=10)

        self.plot_ax = divider.append_axes("right", size="200%", pad=0.5)
        self.plot_ax.set_title("Evolution", size=10)
        self.plot_ax.set_xlabel("Iteration", size=10)
        self.plot_ax.set_ylabel("", size=10)
        self.plot_ax.set_xlim((0, n_iteration))
        self.plot_ax.set_yticklabels([])
        (self.data_plot,) = self.plot_ax.plot([], [], marker="+", linestyle="None")

        self.set_cmap(self.cmap_name)
        self.set_cmap_norm(self.cmap_log)
        self.set_mask_show(self.mask_show)

        self.setMinimumHeight(512)

    def set_contrast_map(self, contrast_map: np.ndarray):
        self.imshow_image.set_data(contrast_map)

    def set_contrast_array(self, contrast_array: np.ndarray):
        self.data_plot.set_xdata(np.arange(contrast_array.size))
        self.data_plot.set_ydata(contrast_array["avg"])

    def set_speckle(self, xy: list[float]):
        self.speckle[0].set_xdata([xy[0], xy[0]])
        self.speckle[1].set_ydata([xy[1], xy[1]])

    @property
    def cmap_name(self) -> str:
        return self._cmap_name

    @cmap_name.setter
    def cmap_name(self, value: str):
        self._cmap_name = value
        self.cmap = mpl.colormaps[value].copy()
        self.cmap.set_bad(color="black")

    def set_cmap(self, cmap_name: str):
        self.cmap_name = cmap_name
        self.imshow_image.set_cmap(self.cmap)

    @property
    def cmap_log(self) -> bool:
        return self._cmap_log

    @cmap_log.setter
    def cmap_log(self, value: bool):
        self._cmap_log = value

    def set_cmap_norm(self, checked: bool):
        self.cmap_log = checked
        if self.cmap_log:
            self.imshow_image.set_norm(LogNorm(vmin=1e-5, vmax=1))
            self.plot_ax.set_yscale("log")
        else:
            self.imshow_image.set_norm(Normalize(vmin=1e-5, vmax=1))
            self.plot_ax.set_yscale("linear")
        self.plot_ax.set_ylim(1e-5, 1)
        self.plot_ax.set_yticklabels([])

    @property
    def mask_show(self) -> bool:
        return self._mask_show

    @mask_show.setter
    def mask_show(self, value: bool):
        self._mask_show = value

    def set_mask_show(self, checked: bool):
        self.mask_show = checked
        if self.mask_show:
            self.imshow_image._alpha = np.where(self.mask, 1.0, 0.9)
        else:
            self.imshow_image._alpha = None


class SpeckleNullingFigureWidget(FigureWidget):
    """
    Speckle Nulling Figure widget
    """

    def __init__(self, capture: np.ndarray, command: np.ndarray, phs_lim: list[float], amp_lim: list[float], src_mask: np.ndarray | None = None, show_toolbar: bool = False, parent=None):
        super().__init__(GridSpec_Layout(nrows=3, ncols=1, height_ratios=(1, 0.2, 0.2), hspace=0.5), show_toolbar, parent)
        self.src_mask = src_mask
        self.src_cmap_name: str = "hot"
        self.snk_cmap_name: str = "bwr"
        self.src_cmap_log: bool = True
        self.src_mask_show: bool = False

        _image_axes, self.plot_ax_phs, self.plot_ax_amp = self.figure.get_axes()
        _image_axes.remove()

        self.plot_ax_phs.set_title("Phase modulation", size=10)
        self.plot_ax_phs.set_xlabel("Phase", size=10)
        self.plot_ax_phs.set_ylabel("Intensity", size=10)
        self.plot_ax_phs.set_xlim((phs_lim[0], phs_lim[1]))
        self.plot_ax_phs.xaxis.set_major_locator(MaxNLocator(nbins=7))
        (self.phs_data_plot,) = self.plot_ax_phs.plot([], [], marker="+", linestyle="None")
        (self.phs_fit_plot,) = self.plot_ax_phs.plot([], [], color="red")
        self.phs_solve_line = self.plot_ax_phs.axvline(np.nan, color="red")

        self.plot_ax_amp.set_title("Amplitude modulation", size=10)
        self.plot_ax_amp.set_xlabel("Amplitude", size=10)
        self.plot_ax_amp.set_ylabel("Intensity", size=10)
        self.plot_ax_amp.set_xlim((amp_lim[0], amp_lim[-1]))
        (self.amp_data_plot,) = self.plot_ax_amp.plot([], [], marker="+", linestyle="None")
        (self.amp_fit_plot,) = self.plot_ax_amp.plot([], [], color="red")
        self.amp_solve_line = self.plot_ax_amp.axvline(np.nan, color="red")

        gs1 = self.figure.get_gridspec()
        gs2 = GridSpecFromSubplotSpec(nrows=1, ncols=2, subplot_spec=gs1[0])

        imshow_ax_sink = self.figure.add_subplot(gs2[0])
        imshow_ax_sink.set_title("SLM", size=10)
        imshow_ax_sink.set_xlabel("px", size=10)
        imshow_ax_sink.set_ylabel("px", size=10)
        imshow_ax_sink.axhline(command.shape[0] / 2 - 0.5, alpha=0.25, linewidth=0.5, color="white")
        imshow_ax_sink.axvline(command.shape[1] / 2 - 0.5, alpha=0.25, linewidth=0.5, color="white")
        imshow_ax_sink.add_patch(patches.Circle((command.shape[0] / 2 - 0.5, command.shape[1] / 2 - 0.5), radius=command.shape[1] / 2, fill=False, alpha=0.25, linewidth=0.5, color="white", transform=imshow_ax_sink.transData))
        self.imshow_image_sink = imshow_ax_sink.imshow(command)
        self.imshow_image_sink.set_clim(0, 2**16 - 1)
        imshow_ax_sink.invert_yaxis()

        divider_sink = make_axes_locatable(imshow_ax_sink)

        self.colorbar_ax_sink = divider_sink.append_axes("right", size="5%", pad=0.1)
        self.figure.colorbar(self.imshow_image_sink, cax=self.colorbar_ax_sink)
        self.colorbar_ax_sink.set_title("adu", size=10)

        imshow_ax_source = self.figure.add_subplot(gs2[1])
        imshow_ax_source.set_title("Source", size=10)
        imshow_ax_source.set_xlabel("px", size=10)
        imshow_ax_source.set_ylabel("px", size=10)
        imshow_ax_source.axhline(capture.shape[0] / 2, alpha=0.25, linewidth=0.5, color="white")
        imshow_ax_source.axvline(capture.shape[1] / 2, alpha=0.25, linewidth=0.5, color="white")
        self.speckle_vline, self.speckle_hline = imshow_ax_source.axvline(np.nan, alpha=0.5, linewidth=0.5, color="red"), imshow_ax_source.axhline(np.nan, alpha=0.5, linewidth=0.5, color="red")
        imshow_ax_source.add_patch(patches.Circle((capture.shape[0] / 2, capture.shape[1] / 2), radius=225, fill=False, alpha=0.25, linewidth=0.5, color="white", transform=imshow_ax_source.transData))
        self.imshow_image_source = imshow_ax_source.imshow(capture)
        imshow_ax_source.set_facecolor("black")
        imshow_ax_source.invert_yaxis()

        divider_source = make_axes_locatable(imshow_ax_source)

        self.colorbar_ax_source = divider_source.append_axes("right", size="5%", pad=0.1)
        self.figure.colorbar(self.imshow_image_source, cax=self.colorbar_ax_source)
        self.colorbar_ax_source.set_title("adu", size=10)

        self.set_src_cmap(self.src_cmap_name)
        self.set_src_cmap_norm(self.src_cmap_log)
        self.set_src_mask_show(self.src_mask_show)
        self.set_snk_cmap(self.snk_cmap_name)

        self.setMinimumHeight(512)

    def set_command(self, command: np.ndarray):
        self.imshow_image_sink.set_data(command)

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
        self.imshow_image_source.set_cmap(self._src_cmap)

    @property
    def src_cmap_log(self) -> bool:
        return self._src_cmap_log

    @src_cmap_log.setter
    def src_cmap_log(self, value: bool):
        self._src_cmap_log = value

    def set_src_cmap_norm(self, checked: bool):
        self.src_cmap_log = checked
        if self.src_cmap_log:
            self.imshow_image_source.set_norm(LogNorm(vmin=1, vmax=2**12 - 1))
        else:
            self.imshow_image_source.set_norm(Normalize(vmin=1, vmax=2**12 - 1))

    @property
    def src_mask_show(self) -> bool:
        return self._src_mask_show

    @src_mask_show.setter
    def src_mask_show(self, value: bool):
        self._src_mask_show = value

    def set_src_mask_show(self, checked: bool):
        self.src_mask_show = checked
        if self.src_mask_show:
            self.imshow_image_source._alpha = np.where(self.src_mask, 1.0, 0.9)
        else:
            self.imshow_image_source._alpha = None

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
        self.imshow_image_sink.set_cmap(self._snk_cmap)

    def set_capture(self, capture: np.ndarray):
        self.imshow_image_source.set_data(capture)

    def set_speckle(self, xy: list[float]):
        self.speckle_x_line.set_xdata([xy[0], xy[0]])
        self.speckle_y_line.set_ydata([xy[1], xy[1]])

    def set_phs_data_plot(self, phs_array: np.ndarray, phs_intensity_data_array: np.ndarray):
        self.phs_data_plot.set_xdata(phs_array)
        self.phs_data_plot.set_ydata(phs_intensity_data_array)

    def set_phs_fit_plot(self, phs_intensity_fit_x_data: np.ndarray, phs_intensity_fit_y_data: np.ndarray):
        self.phs_fit_plot.set_xdata(phs_intensity_fit_x_data)
        self.phs_fit_plot.set_ydata(phs_intensity_fit_y_data)

    def set_amp_data_plot(self, amp_array: np.ndarray, amp_intensity_data_array: np.ndarray):
        self.amp_data_plot.set_xdata(amp_array)
        self.amp_data_plot.set_ydata(amp_intensity_data_array)

    def set_amp_fit_plot(self, amp_intensity_fit_x_data: np.ndarray, amp_intensity_fit_y_data: np.ndarray):
        self.amp_fit_plot.set_xdata(amp_intensity_fit_x_data)
        self.amp_fit_plot.set_ydata(amp_intensity_fit_y_data)

    def set_phs_solve(self, solve: float):
        return self.phs_solve_line.set_xdata([solve, solve])

    def set_amp_solve(self, solve: float):
        return self.amp_solve_line.set_xdata([solve, solve])

    @property
    def phs_ax(self):
        return self.plot_ax_phs

    @property
    def amp_ax(self):
        return self.plot_ax_amp


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
        imshow_ax_snk.invert_yaxis()
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
        imshow_ax_src.invert_yaxis()

        cbar_ax_src.set_title("adu", size=10)

        self.set_src_cmap(self.src_cmap_name)
        self.set_src_cmap_norm(self.src_cmap_log)
        self.set_snk_cmap(self.snk_cmap_name)

        self.setMinimumHeight(512)

    def set_command(self, command: np.ndarray):
        self.image_snk.set_data(command)

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
        self.image_src.set_cmap(self._src_cmap)

    @property
    def src_cmap_log(self) -> bool:
        return self._src_cmap_log

    @src_cmap_log.setter
    def src_cmap_log(self, value: bool):
        self._src_cmap_log = value

    def set_src_cmap_norm(self, checked: bool):
        self.src_cmap_log = checked
        if self.src_cmap_log:
            self.image_src.set_norm(LogNorm(vmin=1, vmax=2**12 - 1))
        else:
            self.image_src.set_norm(Normalize(vmin=1, vmax=2**12 - 1))

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
        self.image_snk.set_cmap(self._snk_cmap)

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