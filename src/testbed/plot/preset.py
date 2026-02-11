import matplotlib as mpl
from matplotlib.axes import Axes
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpecFromSubplotSpec
from matplotlib.ticker import MaxNLocator
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib.colors import LogNorm, Normalize

import numpy as np
from numpy.typing import NDArray

from pykato.plotfunction.gridspec_layout import GridSpec_Layout
from pykato.log import setup_logger

logger = setup_logger("preset", terminator="\n")


def Speckle_Nulling_Process_Plot_Preset(capture: NDArray[np.float64], command: NDArray[np.float64], phs_lim: tuple[float, float], amp_lim: tuple[float, float], dark_hole_mask: NDArray[np.bool] | None = None, figure: Figure | None = None) -> Figure:
    """
    Plot preset used to illustrate speckle nulling process.
    consists of two Imshow axes with corresponding colorbars for the capture and the command as well as two plot axes for the phase and the intensity sweeps.

    Examples:
        figure = Speckle_Nulling_Process_Plot_Preset(capture, command, phs_lim, amp_lim, dark_hole_mask)

    Parameters:
        capture: NDArray[np.float64]
            Capture image

        command: NDArray[np.float64]
            Command image.

        phs_lim: tuple[float, float]
            phase plot limits min and max

        amp_lim: tuple[float, float]
            amplitude plot limits min and max

        dark_hole_mask: NDArray[np.bool] | None = None
            dark hole mask

        figure: Figure | None = None
            Figure object

    Returns: figure: Figure | None = None
            Figure object

    Functions:
        set_command(command: np.ndarray)
            set sink command

        get_src_cmap_name() -> str:
            get source colormap

        set_src_cmap_name(value: str)
            set source colormap

        get_src_cmap_norm() -> bool:
            get source colormap log normalization

        set_src_cmap_norm(value: bool)
            set source colormap log normalization

        get_src_mask_show() -> bool:
            get source mask

        set_src_mask_show(value: bool)
            set source mask

        get_snk_cmap_name() -> str:
            get sink color map

        set_snk_cmap_name(value: src)
            set sink color map

        set_capture(capture: np.ndarray)
            set capture

        set_speckle(xy: list[float])
            set speckle

        set_phs_data_plot(phs_array: np.ndarray, phs_intensity_data_array: np.ndarray)
            set phase data plot

        set_phs_fit_plot(phs_intensity_fit_x_data: np.ndarray, phs_intensity_fit_y_data: np.ndarray)
            set phase fit plot

        set_amp_data_plot(amp_array: np.ndarray, amp_intensity_data_array: np.ndarray)
            set amplitude data plot

        set_amp_fit_plot(amp_intensity_fit_x_data: np.ndarray, amp_intensity_fit_y_data: np.ndarray)
            set amplitude fit plot

        set_phs_solve(solve: float)
            set phase solve

        set_amp_solve(solve: float)
            set amplitude solve

        close()
            Properly close the figure

    """

    if figure is None:
        figure = plt.figure()

    figure = GridSpec_Layout(nrows=3, ncols=1, height_ratios=(1, 0.2, 0.2), hspace=0.5)

    _image_axes, plot_ax_phs, plot_ax_amp = figure.get_axes()
    _image_axes.remove()

    plot_ax_phs.set_title("Phase modulation", size=10)
    plot_ax_phs.set_xlabel("Phase", size=10)
    plot_ax_phs.set_ylabel("Intensity", size=10)
    plot_ax_phs.set_xlim((phs_lim[0], phs_lim[1]))
    plot_ax_phs.xaxis.set_major_locator(MaxNLocator(nbins=7))
    (phs_data_plot,) = plot_ax_phs.plot([], [], marker="+", linestyle="None")
    (phs_fit_plot,) = plot_ax_phs.plot([], [], color="red")
    phs_solve_line = plot_ax_phs.axvline(np.nan, color="red")

    plot_ax_amp.set_title("Amplitude modulation", size=10)
    plot_ax_amp.set_xlabel("Amplitude", size=10)
    plot_ax_amp.set_ylabel("Intensity", size=10)
    plot_ax_amp.set_xlim((amp_lim[0], amp_lim[-1]))
    (amp_data_plot,) = plot_ax_amp.plot([], [], marker="+", linestyle="None")
    (amp_fit_plot,) = plot_ax_amp.plot([], [], color="red")
    amp_solve_line = plot_ax_amp.axvline(np.nan, color="red")

    gs1 = figure.get_gridspec()
    gs2 = GridSpecFromSubplotSpec(nrows=1, ncols=2, subplot_spec=gs1[0])

    imshow_ax_sink = figure.add_subplot(gs2[0])
    imshow_ax_sink.set_title("SLM", size=10)
    imshow_ax_sink.set_xlabel("px", size=10)
    imshow_ax_sink.set_ylabel("px", size=10)
    imshow_ax_sink.axhline(command.shape[0] / 2 - 0.5, alpha=0.25, linewidth=0.5, color="white")
    imshow_ax_sink.axvline(command.shape[1] / 2 - 0.5, alpha=0.25, linewidth=0.5, color="white")
    imshow_ax_sink.add_patch(patches.Circle((command.shape[0] / 2 - 0.5, command.shape[1] / 2 - 0.5), radius=command.shape[1] / 2, fill=False, alpha=0.25, linewidth=0.5, color="white", transform=imshow_ax_sink.transData))
    imshow_image_sink = imshow_ax_sink.imshow(command)
    imshow_image_sink.set_clim(0, 2**16 - 1)
    imshow_ax_sink.invert_yaxis()

    divider_sink = make_axes_locatable(imshow_ax_sink)

    colorbar_ax_sink = divider_sink.append_axes("right", size="5%", pad=0.1)
    figure.colorbar(imshow_image_sink, cax=colorbar_ax_sink)
    colorbar_ax_sink.set_title("adu", size=10)

    imshow_ax_source = figure.add_subplot(gs2[1])
    imshow_ax_source.set_title("Source", size=10)
    imshow_ax_source.set_xlabel("px", size=10)
    imshow_ax_source.set_ylabel("px", size=10)
    imshow_ax_source.axhline(capture.shape[0] / 2, alpha=0.25, linewidth=0.5, color="white")
    imshow_ax_source.axvline(capture.shape[1] / 2, alpha=0.25, linewidth=0.5, color="white")
    speckle = (imshow_ax_source.axvline(np.nan, alpha=0.5, linewidth=0.5, color="red"), imshow_ax_source.axhline(np.nan, alpha=0.5, linewidth=0.5, color="red"))
    imshow_ax_source.add_patch(patches.Circle((capture.shape[0] / 2, capture.shape[1] / 2), radius=225, fill=False, alpha=0.25, linewidth=0.5, color="white", transform=imshow_ax_source.transData))
    imshow_image_source = imshow_ax_source.imshow(capture)
    imshow_ax_source.set_facecolor("black")
    imshow_ax_source.invert_yaxis()

    divider_source = make_axes_locatable(imshow_ax_source)

    colorbar_ax_source = divider_source.append_axes("right", size="5%", pad=0.1)
    figure.colorbar(imshow_image_source, cax=colorbar_ax_source)
    colorbar_ax_source.set_title("adu", size=10)

    # -----------------------------------------------------------------------------------------------------------------
    def _set_command(command: np.ndarray):
        imshow_image_sink.set_data(command)

    figure.set_command = _set_command
    # -----------------------------------------------------------------------------------------------------------------

    # -----------------------------------------------------------------------------------------------------------------
    figure._src_cmap_name: str = "hot"

    def _get_src_cmap_name() -> str:
        return figure._src_cmap_name

    figure.get_src_cmap_name = _get_src_cmap_name

    def _set_src_cmap_name(value: str):
        figure._src_cmap_name = value
        _src_cmap = mpl.colormaps[figure._src_cmap_name].copy()
        _src_cmap.set_bad(color="black")
        imshow_image_source.set_cmap(_src_cmap)

    figure.set_src_cmap_name = _set_src_cmap_name
    # -----------------------------------------------------------------------------------------------------------------

    # -----------------------------------------------------------------------------------------------------------------
    figure._src_cmap_norm: bool = True

    def _get_src_cmap_norm() -> bool:
        return figure._src_cmap_norm

    figure.get_src_cmap_norm = _get_src_cmap_norm

    def _set_src_cmap_norm(value: bool):
        figure._src_cmap_norm = value
        if figure._src_cmap_norm:
            imshow_image_source.set_norm(LogNorm(vmin=1, vmax=2**12 - 1))
        else:
            imshow_image_source.set_norm(Normalize(vmin=1, vmax=2**12 - 1))

    figure.set_src_cmap_norm = _set_src_cmap_norm
    # -----------------------------------------------------------------------------------------------------------------

    # -----------------------------------------------------------------------------------------------------------------
    figure._src_mask_show: bool = False

    def _get_src_mask_show() -> bool:
        return figure._src_mask_show

    figure.get_src_mask_show = _get_src_mask_show

    def _set_src_mask_show(value: bool):
        figure._src_mask_show = value
        if figure._src_mask_show & (dark_hole_mask is not None):
            imshow_image_source._alpha = np.where(dark_hole_mask, 1.0, 0.9)
        else:
            imshow_image_source._alpha = None

    figure.set_src_mask_show = _set_src_mask_show
    # -----------------------------------------------------------------------------------------------------------------

    # -----------------------------------------------------------------------------------------------------------------
    figure._snk_cmap_name: str = "bwr"

    def _get_snk_cmap_name() -> str:
        return figure._snk_cmap_name

    figure.get_snk_cmap_name = _get_snk_cmap_name

    def _set_snk_cmap_name(value: str):
        figure._snk_cmap_name = value
        _snk_cmap = mpl.colormaps[figure._snk_cmap_name].copy()
        _snk_cmap.set_bad(color="black")
        imshow_image_sink.set_cmap(_snk_cmap)

    figure.set_snk_cmap_name = _set_snk_cmap_name
    # -----------------------------------------------------------------------------------------------------------------

    # -----------------------------------------------------------------------------------------------------------------
    def _set_capture(capture: np.ndarray):
        imshow_image_source.set_data(capture)

    figure.set_capture = _set_capture
    # -----------------------------------------------------------------------------------------------------------------

    # -----------------------------------------------------------------------------------------------------------------
    def _set_speckle(xy: list[float]):
        speckle[0].set_xdata([xy[0], xy[0]])
        speckle[1].set_ydata([xy[1], xy[1]])

    figure.set_speckle = _set_speckle
    # -----------------------------------------------------------------------------------------------------------------

    # -----------------------------------------------------------------------------------------------------------------
    def _set_phs_data_plot(phs_array: np.ndarray, phs_intensity_data_array: np.ndarray):
        phs_data_plot.set_xdata(phs_array)
        phs_data_plot.set_ydata(phs_intensity_data_array)

    figure.set_phs_data_plot = _set_phs_data_plot
    # -----------------------------------------------------------------------------------------------------------------

    # -----------------------------------------------------------------------------------------------------------------
    def _set_phs_fit_plot(phs_intensity_fit_x_data: np.ndarray, phs_intensity_fit_y_data: np.ndarray):
        phs_fit_plot.set_xdata(phs_intensity_fit_x_data)
        phs_fit_plot.set_ydata(phs_intensity_fit_y_data)

    figure.set_phs_fit_plot = _set_phs_fit_plot
    # -----------------------------------------------------------------------------------------------------------------

    # -----------------------------------------------------------------------------------------------------------------
    def _set_amp_data_plot(amp_array: np.ndarray, amp_intensity_data_array: np.ndarray):
        amp_data_plot.set_xdata(amp_array)
        amp_data_plot.set_ydata(amp_intensity_data_array)

    figure.set_amp_data_plot = _set_amp_data_plot
    # -----------------------------------------------------------------------------------------------------------------

    # -----------------------------------------------------------------------------------------------------------------
    def _set_amp_fit_plot(amp_intensity_fit_x_data: np.ndarray, amp_intensity_fit_y_data: np.ndarray):
        amp_fit_plot.set_xdata(amp_intensity_fit_x_data)
        amp_fit_plot.set_ydata(amp_intensity_fit_y_data)

    figure.set_amp_fit_plot = _set_amp_fit_plot
    # -----------------------------------------------------------------------------------------------------------------

    # -----------------------------------------------------------------------------------------------------------------
    def _set_phs_solve(solve: float):
        phs_solve_line.set_xdata([solve, solve])

    figure.set_phs_solve = _set_phs_solve
    # -----------------------------------------------------------------------------------------------------------------

    # -----------------------------------------------------------------------------------------------------------------
    def _set_amp_solve(solve: float):
        amp_solve_line.set_xdata([solve, solve])

    figure.set_amp_solve = _set_amp_solve
    # -----------------------------------------------------------------------------------------------------------------

    # -----------------------------------------------------------------------------------------------------------------
    def _phs_ax() -> Axes:
        return plot_ax_phs

    figure.phs_ax = _phs_ax
    # -----------------------------------------------------------------------------------------------------------------

    # -----------------------------------------------------------------------------------------------------------------
    def _amp_ax() -> Axes:
        return plot_ax_amp

    figure.amp_ax = _amp_ax
    # -----------------------------------------------------------------------------------------------------------------

    # -----------------------------------------------------------------------------------------------------------------
    def _close():
        plt.close(figure)

    figure.close = _close
    # -----------------------------------------------------------------------------------------------------------------

    return figure


def Contrast_Evolution_Plot_Preset(contrast: NDArray[np.float64], n_iteration: int, dark_hole_mask: NDArray[np.bool] | None = None, figure: Figure | None = None) -> Figure:
    """
    Plot preset used to illustrate contrast evolution.
    Consists of and Imshow axis and corresponding colorbar for contrast and a plot for change in contrast with iteration.

    Examples:
        figure = Contrast_Evolution_Plot_Preset(contrast, n_iteration, dark_hole_mask)

    Parameters:
        contrast: NDArray[np.float64]
            Contrast image

        n_iteration: int
            Loop iterations

        dark_hole_mask: NDArray[np.bool] | None = None
            dark hole mask

        figure: Figure | None = None
            Figure object.

    Returns: figure: Figure | None = None
            Figure object.

    Functions:
        set_contrast(contrast: np.ndarray)
            set contrast map

        set_contrast_plot(contrast_array: np.ndarray)
            set contrast array

        set_speckle(xy: list[float])
            set speckle

        get_cmap_name() -> str:
            get colormap

        set_cmap_name(value: str)
            set colormap

        get_cmap_norm() -> str:
            get source colormap log normalization

        set_cmap_norm(value: str)
            set source colormap log normalization

        get_mask_show() -> bool
            get mask

        set_mask_show(value: bool)
            set mask

        close()
            Properly close the figure

    """

    if figure is None:
        figure = plt.figure()

    figure = GridSpec_Layout(nrows=1, ncols=1, aspect_ratios=(8,))

    (image_ax,) = figure.get_axes()

    image_ax.set_title("Speckles", size=10)
    image_ax.set_xlabel("px", size=10)
    image_ax.set_ylabel("px", size=10)
    image_ax.axhline(contrast.shape[0] / 2 - 0.5, alpha=0.25, linewidth=0.5, color="white")
    image_ax.axvline(contrast.shape[1] / 2 - 0.5, alpha=0.25, linewidth=0.5, color="white")
    speckle = (image_ax.axvline(np.nan, alpha=0.5, linewidth=0.5, color="red"), image_ax.axhline(np.nan, alpha=0.5, linewidth=0.5, color="red"))
    image_ax.add_patch(patches.Circle((contrast.shape[0] / 2 - 0.5, contrast.shape[1] / 2 - 0.5), radius=contrast.shape[1] / 2, fill=False, alpha=0.25, linewidth=0.5, color="white", transform=image_ax.transData))
    imshow_image = image_ax.imshow(contrast)
    image_ax.set_facecolor("black")
    image_ax.invert_yaxis()

    divider = make_axes_locatable(image_ax)

    colorbar_ax = divider.append_axes("right", size="5%", pad=0.1)
    figure.colorbar(imshow_image, cax=colorbar_ax)
    colorbar_ax.set_title("Contrast", size=10)

    plot_ax = divider.append_axes("right", size="200%", pad=0.5)
    plot_ax.set_title("Evolution", size=10)
    plot_ax.set_xlabel("Iteration", size=10)
    plot_ax.set_ylabel("", size=10)
    plot_ax.set_xlim((0, n_iteration))
    plot_ax.set_yticklabels([])
    (data_plot,) = plot_ax.plot([], [], marker="+", linestyle="None")

    # -----------------------------------------------------------------------------------------------------------------
    def _set_contrast(contrast: np.ndarray):
        imshow_image.set_data(contrast)

    figure.set_contrast = _set_contrast
    # -----------------------------------------------------------------------------------------------------------------

    # -----------------------------------------------------------------------------------------------------------------
    def _set_contrast_plot(contrast_array: np.ndarray):
        data_plot.set_xdata(np.arange(contrast_array.size))
        data_plot.set_ydata(contrast_array["avg"])

    figure.set_contrast_plot = _set_contrast_plot
    # -----------------------------------------------------------------------------------------------------------------

    # -----------------------------------------------------------------------------------------------------------------
    def _set_speckle(xy: list[float]):
        speckle[0].set_xdata([xy[0], xy[0]])
        speckle[1].set_ydata([xy[1], xy[1]])

    figure.set_speckle = _set_speckle
    # -----------------------------------------------------------------------------------------------------------------

    # -----------------------------------------------------------------------------------------------------------------
    figure._cmap_name: str = "jet"

    def _get_cmap_name() -> str:
        return figure._cmap_name

    figure.get_cmap_name = _get_cmap_name

    def _set_cmap_name(value: str):
        figure._cmap_name = value
        _src_cmap = mpl.colormaps[figure._cmap_name].copy()
        _src_cmap.set_bad(color="black")
        imshow_image.set_cmap(_src_cmap)

    figure.set_cmap_name = _set_cmap_name
    # -----------------------------------------------------------------------------------------------------------------

    # -----------------------------------------------------------------------------------------------------------------
    figure._cmap_norm: bool = True

    def _get_cmap_norm() -> bool:
        return figure._cmap_norm

    figure.get_cmap_norm = _get_cmap_norm

    def _set_cmap_norm(value: bool):
        figure._cmap_norm = value
        if figure._cmap_norm:
            imshow_image.set_norm(LogNorm(vmin=1e-5, vmax=1))
            plot_ax.set_yscale("log")
        else:
            imshow_image.set_norm(Normalize(vmin=1e-5, vmax=1))
            plot_ax.set_yscale("linear")
        plot_ax.set_ylim(1e-5, 1)
        plot_ax.set_yticklabels([])

    figure.set_cmap_norm = _set_cmap_norm
    # -----------------------------------------------------------------------------------------------------------------

    # -----------------------------------------------------------------------------------------------------------------
    figure._mask_show: bool = False

    def _get_mask_show() -> bool:
        return figure._mask_show

    figure.get_mask_show = _get_mask_show

    def _set_mask_show(value: bool):
        figure._mask_show = value
        if figure._mask_show & (dark_hole_mask is not None):
            imshow_image._alpha = np.where(dark_hole_mask, 1.0, 0.9)
        else:
            imshow_image._alpha = None

    figure.set_mask_show = _set_mask_show
    # -----------------------------------------------------------------------------------------------------------------

    # -----------------------------------------------------------------------------------------------------------------
    def _close():
        plt.close(figure)

    figure.close = _close
    # -----------------------------------------------------------------------------------------------------------------

    return figure