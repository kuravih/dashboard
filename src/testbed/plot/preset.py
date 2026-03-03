import numpy as np
from numpy.typing import NDArray

from matplotlib.axes import Axes
from matplotlib.image import AxesImage
from matplotlib.lines import Line2D
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator
from matplotlib.colors import LogNorm, Normalize

import matplotlib.pyplot as plt
import matplotlib.patches as patches

from mpl_toolkits.axes_grid1 import make_axes_locatable

from pykato.plotfunction.gridspec_layout import GridSpec_Layout
from pykato.plotfunction.preset import patch_alpha_mask_show, patch_cmap_name, patch_cmap_norm, Imshow_Colorbar_Preset, Complex_ImageGrid_TwoColorbars_Preset, Complex_Imshow_TwoColorbars_Preset
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


def Speckle_Modulation_Plot_Preset(phs_lim: tuple[float, float], amp_lim: tuple[float, float], figure: Figure | None = None) -> Figure:
    """
    Plot preset used to illustrate speckle nulling process.
    Consists of two plot axes for the phase and the intensity sweeps.

    Examples:
        figure = Speckle_Modulation_Plot_Preset(phs_lim, amp_lim)

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
    # speckle = (image_ax.axvline(np.nan, alpha=0.5, linewidth=0.5, color="red"), image_ax.axhline(np.nan, alpha=0.5, linewidth=0.5, color="red"))
    (speckle,) = image_ax.plot([], [], color="red", marker="o", markersize=10, markerfacecolor="none", linestyle="none")
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
    def _get_image_axes() -> Axes:
        return image_axes

    figure.get_image_axes = _get_image_axes
    # -----------------------------------------------------------------------------------------------------------------

    # -----------------------------------------------------------------------------------------------------------------
    def _get_plot() -> Line2D:
        return data_plot

    figure.get_plot = _get_plot
    # -----------------------------------------------------------------------------------------------------------------

    # -----------------------------------------------------------------------------------------------------------------
    def _get_plot_axes() -> Axes:
        return plot_axes

    figure.get_plot_axes = _get_plot_axes
    # -----------------------------------------------------------------------------------------------------------------

    # -----------------------------------------------------------------------------------------------------------------
    def _get_speckle() -> Line2D:
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


def DOTF_Measurement_Plot_Preset(measure_dict: dict[int, NDArray[np.complex64]], figure: Figure | None = None) -> Figure:
    """
    Plot preset used to illustrate DOTF wavefront measurement process.
    Consists of complex image plot axes to display DOTF maps.

    Examples:
        figure = DOTF_Sensing_Process_Plot_Preset(measure_dict, command)
    """

    figure = Complex_ImageGrid_TwoColorbars_Preset(measure_dict.values(), figure=figure)

    imshow_image_dict = {}
    for index, (imshow_axes, image, key) in enumerate(zip(figure.get_imshow_axes_list(), figure.get_image_list(), measure_dict.keys())):
        imshow_axes.set_title(f"{key:02d}", size=10)
        imshow_axes.set_xlabel("px", size=10)
        if index == 0:
            imshow_axes.set_ylabel("px", size=10)
        imshow_image_dict[key] = image

    # -----------------------------------------------------------------------------------------------------------------
    def _get_image_dict() -> dict[int, AxesImage]:
        return imshow_image_dict

    figure.get_image_dict = _get_image_dict
    # -----------------------------------------------------------------------------------------------------------------

    return figure


def Wavefront_Plot_Preset(wavefront: NDArray[np.complex64], figure: Figure | None = None) -> Figure:
    """
    Plot preset used to illustrate wavefronts.

    Examples:
        figure = Wavefront_Plot_Preset(wavefront)
    """

    figure = Complex_Imshow_TwoColorbars_Preset(wavefront)
    figure.get_imshow_axes().set_xlabel("px", size=10)
    figure.get_imshow_axes().set_ylabel("px", size=10)

    return figure


