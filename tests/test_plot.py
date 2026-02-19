import unittest
from matplotlib.figure import Figure

import numpy as np

from testbed.plot.preset import Speckle_Nulling_Process_Plot_Preset, Contrast_Evolution_Plot_Preset, DOTF_Measure_Process_Plot_Preset, Pairwise_FPWFS_Process_Plot_Preset


class TestPlotPreset(unittest.TestCase):

    def test_Speckle_Nulling_Process_Plot_Preset(self):
        capture = np.zeros((256, 256), dtype=np.float64)
        command = np.zeros((360, 360), dtype=np.float64)
        mask = np.zeros((360, 360), dtype=np.bool)
        amp_lim = (0, 360)
        phs_lim = (0, 0.1)

        speckle_nulling_process_figure = Speckle_Nulling_Process_Plot_Preset(capture, command, phs_lim, amp_lim, mask)
        speckle_nulling_process_figure.set_figwidth(10)

        self.assertIsInstance(speckle_nulling_process_figure, Figure, "Figure not created by gridspec_layout.GridSpec_Layout")

        speckle_nulling_process_figure.savefig("tests/output/test_Speckle_Nulling_Process_Plot_Preset.png")

    def test_Contrast_Evolution_Plot_Preset(self):
        contrast = np.zeros((256, 256), dtype=np.float64)
        n_iteration = 100
        dark_hole_mask = np.zeros_like(contrast, dtype=np.bool)

        contrast_evolution_figure = Contrast_Evolution_Plot_Preset(contrast, n_iteration, dark_hole_mask)
        self.assertIsInstance(contrast_evolution_figure, Figure, "Figure not created by gridspec_layout.GridSpec_Layout")
        contrast_evolution_figure.set_figwidth(10)

        contrast_evolution_figure.savefig("tests/output/test_Contrast_Evolution_Plot_Preset.png")

    def test_DOTF_Sensing_Process_Plot_Preset(self):
        capture = np.zeros((256, 256), dtype=np.float64)
        command = np.zeros((360, 360), dtype=np.float64)

        dotf_sensing_figure = DOTF_Measure_Process_Plot_Preset(capture, command)
        self.assertIsInstance(dotf_sensing_figure, Figure, "Figure not created by gridspec_layout.GridSpec_Layout")
        dotf_sensing_figure.set_figwidth(20)

        dotf_sensing_figure.savefig("tests/output/test_DOTF_Sensing_Process_Plot_Preset.png")

    def test_Pairwise_FPWFS_Process_Plot_Preset(self):
        capture = np.zeros((256, 256), dtype=np.float64)
        command = np.zeros((360, 360), dtype=np.float64)

        pairwise_sensing_figure = Pairwise_FPWFS_Process_Plot_Preset(capture, command)
        self.assertIsInstance(pairwise_sensing_figure, Figure, "Figure not created by gridspec_layout.GridSpec_Layout")
        pairwise_sensing_figure.set_figwidth(15)

        pairwise_sensing_figure.savefig("tests/output/test_Pairwise_FPWFS_Process_Plot_Preset.png")
