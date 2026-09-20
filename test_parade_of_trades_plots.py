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

    def test_lob_axes_zone_discrete_period_flexible(self):
        """LoB: Y = integer zones (accuracy lattice); X may be continuous."""
        import matplotlib.pyplot as plt
        import matplotlib.ticker as mticker
        import numpy as np

        small = run_preset("no_variability", seed=12345, total_units=10, verbose=False)

        fig, ax = plt.subplots()
        plot_line_of_balance(small, ax=ax)
        self.assertIn("0 = awal", ax.get_xlabel())
        self.assertIn("diskrit", ax.get_ylabel())
        self.assertIsInstance(ax.yaxis.get_major_locator(), mticker.MultipleLocator)
        self.assertIsInstance(ax.yaxis.get_minor_locator(), mticker.NullLocator)
        # Plotted trade lines use integer Y only (skip ideal/guide lines)
        for line in ax.lines:
            label = line.get_label() or ""
            if label.startswith("_") or "Ideal" in label:
                continue
            ys = np.asarray(line.get_ydata(), dtype=float)
            self.assertTrue(np.allclose(ys, np.round(ys)), msg=f"non-integer Y in {label}")
        # Engine series is integer and starts at 0
        cum = small.cumulative_series()
        self.assertEqual(cum[0][0], 0)
        self.assertTrue(all(isinstance(v, int) for v in cum[0]))
        plt.close(fig)

        fig, ax = plt.subplots()
        plot_line_of_balance_detail(small, ax=ax, max_period=8)
        self.assertIn("diskrit", ax.get_ylabel())
        for line in ax.lines:
            ys = np.asarray(line.get_ydata(), dtype=float)
            self.assertTrue(np.allclose(ys, np.round(ys)))
        plt.close(fig)

        fig, ax = plt.subplots()
        plot_comparison_lob(self.results, ax=ax)
        self.assertIn("diskrit", ax.get_ylabel())
        plt.close(fig)

        fig, ax = plt.subplots()
        plot_single_scenario_lob(self.result, ax=ax)
        self.assertIn("diskrit", ax.get_ylabel())
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
