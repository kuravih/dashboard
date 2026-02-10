import unittest
from click import command
from matplotlib.figure import Figure

import numpy as np

from testbed.plot.preset import Speckle_Nulling_Process_Plot_Preset


class TestPlotPreset(unittest.TestCase):
    def test_Speckle_Nulling_Process_Plot_Preset(self):
        capture = np.zeros((256, 256), dtype=np.float64)
        command = np.zeros((360, 360), dtype=np.float64)
        mask = np.zeros((360, 360), dtype=np.bool)
        amp_lim = (0, 360)
        phs_lim = (0, 0.1)
        speckle_nulling_process_figure = Speckle_Nulling_Process_Plot_Preset(capture, command, phs_lim, amp_lim, mask)
        self.assertIsInstance(speckle_nulling_process_figure, Figure, "Figure not created by gridspec_layout.GridSpec_Layout")

        speckle_nulling_process_figure.savefig("tests/output/test_Speckle_Nulling_Process_Plot_Preset.png")
