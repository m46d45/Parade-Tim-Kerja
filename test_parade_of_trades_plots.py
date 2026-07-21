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
    plot_line_of_balance,
    plot_run,
    plot_side_by_side_runs,
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
