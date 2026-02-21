import numpy as np
from numpy.typing import NDArray

from matplotlib.axes import Axes
from matplotlib.image import AxesImage
from matplotlib.lines import Line2D
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpecFromSubplotSpec
from matplotlib.ticker import MaxNLocator
from matplotlib.ticker import FuncFormatter, LinearLocator
from matplotlib.colors import LogNorm, Normalize

import matplotlib.pyplot as plt
import matplotlib.patches as patches

from mpl_toolkits.axes_grid1 import make_axes_locatable

from pykato.plotfunction.gridspec_layout import GridSpec_Layout
from pykato.plotfunction.preset import _pi_formatter, patch_alpha_mask_show, patch_cmap_name, patch_cmap_norm, Imshow_Colorbar_Preset, Complex_ImageGrid_TwoColorbars_Preset
from pykato.log import setup_logger

logger = setup_logger("preset", terminator="\n")


def Image_Plot_Preset(capture: NDArray[np.float64], cmap_norm: Normalize | None = None, cmap_name: str | None = None, alpha_mask: NDArray[np.bool] | None = None, figure: Figure | None = None) -> Figure:
    """
    Plot preset used to display source images.

    Parameters:
        capture: NDArray[np.float64]
            Capture image

        cmap_norm: bool | None = None
            Colormap normalization

        cmap_name: str | None = None
            Colormap Name

        mask: NDArray[np.bool] | None = None
            Mask

        figure: Figure | None = None
            Figure object

    Returns: figure: Figure | None = None
            Figure object
    """

    figure = Imshow_Colorbar_Preset(capture, figure=figure)

    if cmap_name is not None:
        patch_cmap_name(figure.get_image())
        figure.get_image().set_cmap_name(cmap_name)

    if cmap_norm is not None:
        patch_cmap_norm(figure.get_image())
        figure.get_image().set_cmap_norm(cmap_norm)

    if alpha_mask is not None:
        patch_alpha_mask_show(figure.get_image(), alpha_mask)
        figure.get_image().set_alpha_mask_show(True)

    return figure


def Speckle_Nulling_Process_Plot_Preset(phs_lim: tuple[float, float], amp_lim: tuple[float, float], figure: Figure | None = None) -> Figure:
    """
    Plot preset used to illustrate speckle nulling process.
    Consists of two plot axes for the phase and the intensity sweeps.

    Examples:
        figure = Speckle_Nulling_Process_Plot_Preset(phs_lim, amp_lim)

    Parameters:
        phs_lim: tuple[float, float]
            phase plot limits min and max

        amp_lim: tuple[float, float]
            amplitude plot limits min and max

        figure: Figure | None = None
            Figure object

    Returns: figure: Figure | None = None
            Figure object

    Functions:
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

    figure = GridSpec_Layout(nrows=2, ncols=1, hspace=0.5, figure=figure)

    plot_ax_phs, plot_ax_amp = figure.get_axes()

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


def Contrast_Evolution_Plot_Preset(contrast: np.ndarray, n_iteration: int, dark_hole_mask: NDArray[np.bool], figure: Figure | None = None) -> Figure:
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

        dark_hole_mask: NDArray[np.bool] = None
            dark hole mask

        figure: Figure | None = None
            Figure object.

    Returns: figure: Figure | None = None
            Figure object.

    Functions:

        close()
            Properly close the figure

    """

    figure = GridSpec_Layout(nrows=1, ncols=1, aspect_ratios=(8,), figure=figure)

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
    plot_ax.set_xlim((0, n_iteration))
    plot_ax.set_yscale("log")
    plot_ax.set_ylim(1, 2**12 - 1)
    plot_ax.set_ylabel("", size=10)
    plot_ax.set_yticklabels([])
    (data_plot,) = plot_ax.plot([], [], marker="+", linestyle="None")

    # -----------------------------------------------------------------------------------------------------------------
    def _get_image() -> AxesImage:
        return imshow_image

    figure.get_image = _get_image
    # -----------------------------------------------------------------------------------------------------------------

    # -----------------------------------------------------------------------------------------------------------------
    def _get_image_ax() -> Axes:
        return image_ax

    figure.get_image_ax = _get_image_ax
    # -----------------------------------------------------------------------------------------------------------------

    # -----------------------------------------------------------------------------------------------------------------
    def _get_plot() -> Line2D:
        return data_plot

    figure.get_plot = _get_plot
    # -----------------------------------------------------------------------------------------------------------------

    # -----------------------------------------------------------------------------------------------------------------
    def _get_plot_ax() -> Axes:
        return plot_ax

    figure.get_plot_ax = _get_plot_ax
    # -----------------------------------------------------------------------------------------------------------------

    # -----------------------------------------------------------------------------------------------------------------
    def _get_speckle() -> tuple[Line2D, Line2D]:
        return speckle

    figure.get_speckle = _get_speckle
    # -----------------------------------------------------------------------------------------------------------------

    # -----------------------------------------------------------------------------------------------------------------
    def _close():
        plt.close(figure)

    figure.close = _close
    # -----------------------------------------------------------------------------------------------------------------

    patch_cmap_name(imshow_image)
    imshow_image.set_cmap_name("jet")

    patch_cmap_norm(imshow_image)
    imshow_image.set_cmap_norm(LogNorm(1, 1e-5))

    patch_alpha_mask_show(imshow_image, dark_hole_mask)
    imshow_image.set_alpha_mask_show(True)

    return figure


def DOTF_Measure_Process_Plot_Preset(dotf_maps: list[NDArray[np.complex64]], figure: Figure | None = None) -> Figure:

    # """
    # Plot preset used to illustrate DOTF wavefront measurement process.
    # Consists of complex image plot axes to display DOTF maps.

    # Examples:
    #     figure = DOTF_Sensing_Process_Plot_Preset(capture, command)
    # """

    figure = Complex_ImageGrid_TwoColorbars_Preset(dotf_maps, figure=figure)

    for index, imshow_ax in enumerate(figure.get_imshow_axes_list()):
        imshow_ax.set_xlabel("px", size=10)
        if index == 0:
            imshow_ax.set_ylabel("px", size=10)

    # gs = figure.get_gridspec()

    # # ---- sink -------------------------------------------------------------------------------------------------------
    # imshow_ax_sink = figure.add_subplot(gs[0])
    # imshow_ax_sink.set_title("Command", size=10)
    # imshow_ax_sink.set_xlabel("px", size=10)
    # imshow_ax_sink.set_ylabel("px", size=10)
    # imshow_ax_sink.axhline(command.shape[0] / 2 - 0.5, alpha=0.25, linewidth=0.5, color="white")
    # imshow_ax_sink.axvline(command.shape[1] / 2 - 0.5, alpha=0.25, linewidth=0.5, color="white")
    # imshow_ax_sink.add_patch(patches.Circle((command.shape[0] / 2 - 0.5, command.shape[1] / 2 - 0.5), radius=command.shape[1] / 2, fill=False, alpha=0.25, linewidth=0.5, color="white", transform=imshow_ax_sink.transData))
    # imshow_image_sink = imshow_ax_sink.imshow(command)
    # imshow_image_sink.set_clim(0, 2**16 - 1)
    # imshow_ax_sink.invert_yaxis()

    # divider = make_axes_locatable(imshow_ax_sink)

    # colorbar_ax_sink = divider.append_axes("right", size="5%", pad=0.1)
    # figure.colorbar(imshow_image_sink, cax=colorbar_ax_sink)
    # colorbar_ax_sink.set_title("adu", size=10)
    # # ---- sink -------------------------------------------------------------------------------------------------------

    # # ---- source -----------------------------------------------------------------------------------------------------
    # imshow_ax_source = divider.append_axes("right", size="100%", pad=1.5)
    # imshow_ax_source.set_title("Capture", size=10)
    # imshow_ax_source.set_xlabel("px", size=10)
    # imshow_ax_source.set_ylabel("px", size=10)
    # imshow_ax_source.axhline(capture.shape[0] / 2, alpha=0.25, linewidth=0.5, color="white")
    # imshow_ax_source.axvline(capture.shape[1] / 2, alpha=0.25, linewidth=0.5, color="white")
    # imshow_ax_source.add_patch(patches.Circle((capture.shape[0] / 2, capture.shape[1] / 2), radius=225, fill=False, alpha=0.25, linewidth=0.5, color="white", transform=imshow_ax_source.transData))
    # imshow_image_source = imshow_ax_source.imshow(capture)
    # imshow_ax_source.set_facecolor("black")
    # imshow_ax_source.invert_yaxis()

    # colorbar_ax_source = divider.append_axes("right", size="5%", pad=0.1)
    # figure.colorbar(imshow_image_source, cax=colorbar_ax_source)
    # colorbar_ax_source.set_title("adu", size=10)
    # # ---- source -----------------------------------------------------------------------------------------------------

    # # ---- dotf -------------------------------------------------------------------------------------------------------
    # imshow_ax_dotf = divider.append_axes("right", size="100%", pad=1.5)
    # imshow_ax_dotf.set_title("DOTF", size=10)
    # imshow_ax_dotf.set_xlabel("px", size=10)
    # imshow_ax_dotf.set_ylabel("px", size=10)
    # imshow_ax_dotf.axhline(capture.shape[0] / 2, alpha=0.25, linewidth=0.5, color="white")
    # imshow_ax_dotf.axvline(capture.shape[1] / 2, alpha=0.25, linewidth=0.5, color="white")
    # bg_imshow_image_dotf = imshow_ax_dotf.imshow(np.zeros_like(capture, dtype=float), "gray", vmin=0, vmax=1)
    # imshow_image_dotf = imshow_ax_dotf.imshow(np.zeros_like(capture, dtype=float), alpha=np.zeros_like(capture, dtype=float), cmap="hsv", vmin=-np.pi, vmax=np.pi)
    # imshow_ax_dotf.set_facecolor("black")
    # imshow_ax_dotf.invert_yaxis()

    # arg_colorbar_ax_dotf = divider.append_axes("right", size="5%", pad=0.1)
    # figure.colorbar(imshow_image_dotf, cax=arg_colorbar_ax_dotf)
    # arg_colorbar_ax_dotf.yaxis.set_major_locator(LinearLocator(numticks=9))
    # arg_colorbar_ax_dotf.yaxis.set_major_formatter(FuncFormatter(_pi_formatter))
    # arg_colorbar_ax_dotf.set_title("arg", size=10)

    # mod_colorbar_ax_dotf = divider.append_axes("right", size="5%", pad=0.4)
    # figure.colorbar(bg_imshow_image_dotf, cax=mod_colorbar_ax_dotf)
    # mod_colorbar_ax_dotf.set_title("mod", size=10)
    # # ---- source -----------------------------------------------------------------------------------------------------

    # # ---- wavefront --------------------------------------------------------------------------------------------------
    # imshow_ax_wf = divider.append_axes("right", size="100%", pad=1.5)
    # imshow_ax_wf.set_title("Wavefront", size=10)
    # imshow_ax_wf.set_xlabel("px", size=10)
    # imshow_ax_wf.set_ylabel("px", size=10)
    # imshow_ax_wf.axhline(capture.shape[0] / 2, alpha=0.25, linewidth=0.5, color="white")
    # imshow_ax_wf.axvline(capture.shape[1] / 2, alpha=0.25, linewidth=0.5, color="white")
    # imshow_ax_wf.add_patch(patches.Circle((capture.shape[0] / 2, capture.shape[1] / 2), radius=225, fill=False, alpha=0.25, linewidth=0.5, color="white", transform=imshow_ax_wf.transData))
    # bg_imshow_image_wf = imshow_ax_wf.imshow(np.zeros_like(capture, dtype=float), "gray", vmin=0, vmax=1)
    # imshow_image_wf = imshow_ax_wf.imshow(np.zeros_like(capture, dtype=float), alpha=np.zeros_like(capture, dtype=float), cmap="hsv", vmin=-np.pi, vmax=np.pi)
    # imshow_ax_wf.set_facecolor("black")
    # imshow_ax_wf.invert_yaxis()

    # arg_colorbar_ax_wf = divider.append_axes("right", size="5%", pad=0.1)
    # figure.colorbar(imshow_image_wf, cax=arg_colorbar_ax_wf)
    # arg_colorbar_ax_wf.yaxis.set_major_locator(LinearLocator(numticks=9))
    # arg_colorbar_ax_wf.yaxis.set_major_formatter(FuncFormatter(_pi_formatter))
    # arg_colorbar_ax_wf.set_title("arg", size=10)

    # mod_colorbar_ax_wf = divider.append_axes("right", size="5%", pad=0.4)
    # figure.colorbar(bg_imshow_image_wf, cax=mod_colorbar_ax_wf)
    # mod_colorbar_ax_wf.set_title("mod", size=10)
    # # ---- wavefront --------------------------------------------------------------------------------------------------

    return figure


def Pairwise_FPWFS_Process_Plot_Preset(capture: NDArray[np.float64], command: NDArray[np.float64], figure: Figure | None = None) -> Figure:
    """
    Plot preset used to illustrate pairwise FPWF process.
    Consists of two Imshow axes with corresponding colorbars for the capture and the command.
    Third Imshow displays the measure wavefront.

    Examples:
        figure = Pairwise_FPWFS_Process_Plot_Preset(capture, command)
    """

    figure = GridSpec_Layout(nrows=1, ncols=1, init=False, figure=figure)

    gs = figure.get_gridspec()

    # ---- sink -------------------------------------------------------------------------------------------------------
    imshow_ax_sink = figure.add_subplot(gs[0])
    imshow_ax_sink.set_title("Command", size=10)
    imshow_ax_sink.set_xlabel("px", size=10)
    imshow_ax_sink.set_ylabel("px", size=10)
    imshow_ax_sink.axhline(command.shape[0] / 2 - 0.5, alpha=0.25, linewidth=0.5, color="white")
    imshow_ax_sink.axvline(command.shape[1] / 2 - 0.5, alpha=0.25, linewidth=0.5, color="white")
    imshow_ax_sink.add_patch(patches.Circle((command.shape[0] / 2 - 0.5, command.shape[1] / 2 - 0.5), radius=command.shape[1] / 2, fill=False, alpha=0.25, linewidth=0.5, color="white", transform=imshow_ax_sink.transData))
    imshow_image_sink = imshow_ax_sink.imshow(command)
    imshow_image_sink.set_clim(0, 2**16 - 1)
    imshow_ax_sink.invert_yaxis()

    divider = make_axes_locatable(imshow_ax_sink)

    colorbar_ax_sink = divider.append_axes("right", size="5%", pad=0.1)
    figure.colorbar(imshow_image_sink, cax=colorbar_ax_sink)
    colorbar_ax_sink.set_title("adu", size=10)
    # ---- sink -------------------------------------------------------------------------------------------------------

    # ---- source -----------------------------------------------------------------------------------------------------
    imshow_ax_source = divider.append_axes("right", size="100%", pad=1.5)
    imshow_ax_source.set_title("Capture", size=10)
    imshow_ax_source.set_xlabel("px", size=10)
    imshow_ax_source.set_ylabel("px", size=10)
    imshow_ax_source.axhline(capture.shape[0] / 2, alpha=0.25, linewidth=0.5, color="white")
    imshow_ax_source.axvline(capture.shape[1] / 2, alpha=0.25, linewidth=0.5, color="white")
    imshow_ax_source.add_patch(patches.Circle((capture.shape[0] / 2, capture.shape[1] / 2), radius=225, fill=False, alpha=0.25, linewidth=0.5, color="white", transform=imshow_ax_source.transData))
    imshow_image_source = imshow_ax_source.imshow(capture)
    imshow_ax_source.set_facecolor("black")
    imshow_ax_source.invert_yaxis()

    colorbar_ax_source = divider.append_axes("right", size="5%", pad=0.1)
    figure.colorbar(imshow_image_source, cax=colorbar_ax_source)
    colorbar_ax_source.set_title("adu", size=10)
    # ---- source -----------------------------------------------------------------------------------------------------

    # ---- wavefront --------------------------------------------------------------------------------------------------
    imshow_ax_wf = divider.append_axes("right", size="100%", pad=1.5)
    imshow_ax_wf.set_title("Wavefront", size=10)
    imshow_ax_wf.set_xlabel("px", size=10)
    imshow_ax_wf.set_ylabel("px", size=10)
    imshow_ax_wf.axhline(capture.shape[0] / 2, alpha=0.25, linewidth=0.5, color="white")
    imshow_ax_wf.axvline(capture.shape[1] / 2, alpha=0.25, linewidth=0.5, color="white")
    imshow_ax_wf.add_patch(patches.Circle((capture.shape[0] / 2, capture.shape[1] / 2), radius=225, fill=False, alpha=0.25, linewidth=0.5, color="white", transform=imshow_ax_wf.transData))
    bg_imshow_image_wf = imshow_ax_wf.imshow(np.zeros_like(capture, dtype=float), "gray", vmin=0, vmax=1)
    imshow_image_wf = imshow_ax_wf.imshow(np.zeros_like(capture, dtype=float), alpha=np.zeros_like(capture, dtype=float), cmap="hsv", vmin=-np.pi, vmax=np.pi)
    imshow_ax_wf.set_facecolor("black")
    imshow_ax_wf.invert_yaxis()

    arg_colorbar_ax_wf = divider.append_axes("right", size="5%", pad=0.1)
    figure.colorbar(imshow_image_wf, cax=arg_colorbar_ax_wf)
    arg_colorbar_ax_wf.yaxis.set_major_locator(LinearLocator(numticks=9))
    arg_colorbar_ax_wf.yaxis.set_major_formatter(FuncFormatter(_pi_formatter))
    arg_colorbar_ax_wf.set_title("arg", size=10)

    mod_colorbar_ax_wf = divider.append_axes("right", size="5%", pad=0.4)
    figure.colorbar(bg_imshow_image_wf, cax=mod_colorbar_ax_wf)
    mod_colorbar_ax_wf.set_title("mod", size=10)
    # ---- wavefront --------------------------------------------------------------------------------------------------

    return figure
