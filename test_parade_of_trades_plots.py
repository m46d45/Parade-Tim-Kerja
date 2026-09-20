"""Smoke tests for parade_of_trades_plots (no interactive display)."""

from __future__ import annotations

import unittest
from pathlib import Path
import tempfile

import matplotlib

matplotlib.use("Agg")  # non-interactive backend for CI / headless

from parade_of_trades_core import compare_presets, run_preset
from parade_of_trades_plots import (
    generate_demo_figures,
    plot_buffer_profile,
    plot_comparison,
    plot_comparison_lob,
    plot_line_of_balance,
    plot_line_of_balance_detail,
    plot_run,
    plot_side_by_side_runs,
    plot_single_scenario_lob,
    plot_utilization,
)


class TestPlotsSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = run_preset("medium", seed=1, total_units=40, verbose=False)
        cls.results = compare_presets(
            presets=["no_variability", "medium", "high"],
            seed=1,
            total_units=40,
            verbose=False,
        )

    def test_plot_run_saves(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "run.png"
            fig = plot_run(self.result, show=False, save_path=path)
            self.assertTrue(path.exists())
            self.assertGreater(path.stat().st_size, 1000)
            self.assertIsNotNone(fig)

    def test_individual_axes_helpers(self):
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(1, 3, figsize=(12, 3))
        plot_line_of_balance(self.result, ax=axes[0])
        plot_buffer_profile(self.result, ax=axes[1])
        plot_utilization(self.result, ax=axes[2])
        plt.close(fig)

    def test_lob_axes_are_zero_based(self):
        """LoB labels must match engine series (period 0 = start, zona from 0)."""
        import matplotlib.pyplot as plt
        import matplotlib.ticker as mticker

        fig, ax = plt.subplots()
        plot_line_of_balance(self.result, ax=ax)
        xlabel = ax.get_xlabel()
        ylabel = ax.get_ylabel()
        self.assertIn("0 = awal", xlabel)
        self.assertNotIn("1, 2, 3", xlabel)
        self.assertIn("dari 0", ylabel)
        self.assertNotIn("1, 2, 3", ylabel)
        self.assertIsInstance(ax.xaxis.get_minor_locator(), mticker.MultipleLocator)
        # Minor step = 1 period (MultipleLocator stores interval as .base in some versions)
        minor = ax.xaxis.get_minor_locator()
        step = getattr(minor, "base", None) or getattr(minor, "_base", None)
        if step is None:
            ticks = minor.tick_values(0, 5)
            self.assertAlmostEqual(float(ticks[1] - ticks[0]), 1.0)
        else:
            self.assertEqual(float(step), 1.0)
        # Series starts at origin
        cum = self.result.cumulative_series()
        self.assertEqual(cum[0][0], 0)
        plt.close(fig)

        fig, ax = plt.subplots()
        plot_line_of_balance_detail(self.result, ax=ax, max_period=8)
        self.assertIn("0 = awal", ax.get_xlabel())
        self.assertIn("dari 0", ax.get_ylabel())
        plt.close(fig)

        fig, ax = plt.subplots()
        plot_comparison_lob(self.results, ax=ax)
        self.assertIn("0 = awal", ax.get_xlabel())
        self.assertIn("dari 0", ax.get_ylabel())
        plt.close(fig)

        fig, ax = plt.subplots()
        plot_single_scenario_lob(self.result, ax=ax)
        self.assertIn("0 = awal", ax.get_xlabel())
        self.assertIn("dari 0", ax.get_ylabel())
        plt.close(fig)

    def test_plot_comparison_saves(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "cmp.png"
            plot_comparison(self.results, show=False, save_path=path)
            self.assertTrue(path.exists())
            self.assertGreater(path.stat().st_size, 1000)

    def test_side_by_side_saves(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "sbs.png"
            plot_side_by_side_runs(self.results, show=False, save_path=path)
            self.assertTrue(path.exists())

    def test_generate_demo_figures(self):
        with tempfile.TemporaryDirectory() as td:
            paths = generate_demo_figures(
                output_dir=td, seed=0, total_units=30, show=False
            )
            self.assertEqual(len(paths), 5)
            for p in paths:
                self.assertTrue(p.exists(), msg=str(p))


if __name__ == "__main__":
    unittest.main()
