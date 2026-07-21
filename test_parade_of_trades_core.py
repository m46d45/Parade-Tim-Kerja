"""
Unit tests for parade_of_trades_core.py

Covers:
  - Config construction and validation
  - Deterministic no-variability baseline
  - Sequential buffer availability within a period
  - Capacity constraint (cannot exceed available buffer)
  - Seed reproducibility
  - Completion condition and metrics
  - Preset comparison sanity (higher variability → longer / more idle, usually)
"""

from __future__ import annotations

import unittest

from parade_of_trades_core import (
    CAPACITY_PRESETS,
    DEFAULT_TOTAL_UNITS,
    ParadeConfig,
    ParadeOfTrades,
    TradeConfig,
    compare_presets,
    run_preset,
)


class TestTradeConfig(unittest.TestCase):
    def test_mean_and_label(self):
        t = TradeConfig("A", 3, 7)
        self.assertEqual(t.mean, 5.0)
        self.assertEqual(t.label(), "3/7")
        self.assertEqual(t.pair, (3, 7))

    def test_invalid_low_high(self):
        with self.assertRaises(ValueError):
            TradeConfig("A", 8, 2)

    def test_negative_capacity(self):
        with self.assertRaises(ValueError):
            TradeConfig("A", -1, 5)


class TestParadeConfig(unittest.TestCase):
    def test_from_preset_single(self):
        cfg = ParadeConfig.from_preset("medium", n_trades=5, seed=1)
        self.assertEqual(cfg.n_trades, 5)
        self.assertEqual(cfg.n_interfaces, 4)
        for t in cfg.trades:
            self.assertEqual(t.pair, (3, 7))
        self.assertEqual(cfg.trades[0].name, "Pemasangan Bekisting")
        self.assertEqual(cfg.trades[4].name, "Finishing Lantai")

    def test_from_preset_mixed(self):
        cfg = ParadeConfig.from_preset(
            ["no_variability", "low", "medium", "high", "very_high"]
        )
        expected = [(5, 5), (4, 6), (3, 7), (2, 8), (1, 9)]
        self.assertEqual([t.pair for t in cfg.trades], expected)

    def test_from_pairs(self):
        cfg = ParadeConfig.from_pairs([(2, 8), (1, 9), (5, 5)], seed=0)
        self.assertEqual(cfg.n_trades, 3)
        self.assertEqual(cfg.trades[2].pair, (5, 5))

    def test_unknown_preset(self):
        with self.assertRaises(ValueError):
            ParadeConfig.from_preset("extreme")

    def test_custom_names(self):
        cfg = ParadeConfig.from_preset(
            "low", n_trades=2, trade_names=["Alpha", "Beta"]
        )
        self.assertEqual(cfg.trades[0].name, "Alpha")
        self.assertEqual(cfg.trades[1].name, "Beta")


class TestNoVariabilityBaseline(unittest.TestCase):
    """With 5/5 everywhere, perfect flow: duration = total/5, zero WIP residual."""

    def setUp(self):
        self.cfg = ParadeConfig.from_preset(
            "no_variability", total_units=100, seed=42
        )
        self.sim = ParadeOfTrades(self.cfg)
        self.result = self.sim.run()

    def test_duration_is_ideal(self):
        # 100 units / 5 per period = 20
        self.assertEqual(self.result.duration, 20)
        self.assertEqual(self.result.ideal_duration, 20.0)

    def test_all_trades_finish_together(self):
        for m in self.result.trade_metrics:
            self.assertEqual(m.periods_to_finish, 20)
            self.assertEqual(m.total_production, 100)
            self.assertEqual(m.utilization, 1.0)
            self.assertEqual(m.total_idle, 0)

    def test_no_buffer_buildup(self):
        # Sequential same-period handoff with equal capacity → buffers stay 0
        for rec in self.result.history:
            self.assertEqual(rec.buffers, [0, 0, 0, 0])
        self.assertEqual(self.result.max_buffer, [0, 0, 0, 0])

    def test_constant_production_of_five(self):
        for rec in self.result.history:
            self.assertEqual(rec.production, [5, 5, 5, 5, 5])
            self.assertEqual(rec.capacity, [5, 5, 5, 5, 5])

    def test_throughput(self):
        self.assertAlmostEqual(self.result.system_throughput, 5.0)


class TestSequentialBufferUpdate(unittest.TestCase):
    """Upstream production must be available to downstream in the same period."""

    def test_first_period_all_can_work_if_capacity_allows(self):
        # Constant capacity 5: in period 1 every trade produces 5
        cfg = ParadeConfig.from_preset("no_variability", total_units=100, seed=0)
        sim = ParadeOfTrades(cfg)
        rec = sim.step()
        self.assertEqual(rec.production, [5, 5, 5, 5, 5])
        self.assertEqual(rec.cumulative, [5, 5, 5, 5, 5])
        self.assertEqual(rec.buffers, [0, 0, 0, 0])

    def test_starvation_when_upstream_low(self):
        # Trade 1 always 1, trade 2 always 9 → trade 2 limited by buffer
        cfg = ParadeConfig.from_pairs(
            [(1, 1), (9, 9)], total_units=10, seed=0
        )
        sim = ParadeOfTrades(cfg)
        rec = sim.step()
        # T1 produces 1 → buffer1 gets 1; T2 wants 9 but only 1 available
        self.assertEqual(rec.production[0], 1)
        self.assertEqual(rec.production[1], 1)
        self.assertEqual(rec.idle_capacity[1], 8)
        self.assertEqual(rec.buffers[0], 0)

    def test_buffer_builds_when_downstream_low(self):
        cfg = ParadeConfig.from_pairs(
            [(9, 9), (1, 1)], total_units=20, seed=0
        )
        sim = ParadeOfTrades(cfg)
        rec = sim.step()
        # T1 produces 9; T2 takes only 1 → buffer = 8
        self.assertEqual(rec.production[0], 9)
        self.assertEqual(rec.production[1], 1)
        self.assertEqual(rec.buffers[0], 8)
        self.assertEqual(sim.max_buffer[0], 8)


class TestCapacityAndRemainingWork(unittest.TestCase):
    def test_cannot_exceed_total_units(self):
        cfg = ParadeConfig.from_pairs([(8, 8)], total_units=10, seed=0)
        sim = ParadeOfTrades(cfg)
        r1 = sim.step()
        self.assertEqual(r1.production[0], 8)
        r2 = sim.step()
        self.assertEqual(r2.production[0], 2)  # only 2 remaining
        self.assertTrue(sim.is_complete)
        self.assertEqual(sim.cumulative[0], 10)

    def test_trade_stops_after_finish(self):
        cfg = ParadeConfig.from_pairs([(5, 5), (5, 5)], total_units=5, seed=0)
        sim = ParadeOfTrades(cfg)
        sim.step()  # both finish in period 1
        self.assertTrue(sim.is_complete)
        self.assertEqual(sim._executions, [1, 1])


class TestSeedReproducibility(unittest.TestCase):
    def test_same_seed_same_history(self):
        a = run_preset("high", seed=123, verbose=False)
        b = run_preset("high", seed=123, verbose=False)
        self.assertEqual(a.duration, b.duration)
        self.assertEqual(
            [h.production for h in a.history],
            [h.production for h in b.history],
        )
        self.assertEqual(a.max_buffer, b.max_buffer)

    def test_different_seed_can_differ(self):
        a = run_preset("very_high", seed=1, verbose=False)
        b = run_preset("very_high", seed=2, verbose=False)
        # Extremely unlikely to match full production history
        hist_a = [h.production for h in a.history]
        hist_b = [h.production for h in b.history]
        self.assertTrue(
            a.duration != b.duration or hist_a != hist_b,
            "Different seeds unexpectedly produced identical runs",
        )


class TestCompletionAndMetrics(unittest.TestCase):
    def test_step_after_complete_raises(self):
        cfg = ParadeConfig.from_preset("no_variability", total_units=5, seed=0)
        sim = ParadeOfTrades(cfg)
        sim.run()
        with self.assertRaises(RuntimeError):
            sim.step()

    def test_reset_allows_rerun(self):
        cfg = ParadeConfig.from_preset("medium", total_units=50, seed=7)
        sim = ParadeOfTrades(cfg)
        r1 = sim.run()
        sim.reset()
        # After reset without reseed, RNG continues — not same run.
        # Reseed for identical replay:
        sim.reseed(7)
        r2 = sim.run()
        self.assertEqual(r1.duration, r2.duration)
        self.assertEqual(
            [h.production for h in r1.history],
            [h.production for h in r2.history],
        )

    def test_history_series_helpers(self):
        r = run_preset("low", seed=0, total_units=30, verbose=False)
        cum = r.cumulative_series()
        buf = r.buffer_series()
        prod = r.production_series()
        self.assertEqual(len(cum), 5)
        self.assertEqual(len(cum[0]), r.duration + 1)  # includes period 0
        self.assertEqual(cum[0][0], 0)
        self.assertEqual(cum[-1][-1], 30)
        self.assertEqual(len(buf), 4)
        self.assertEqual(len(prod[0]), r.duration)

    def test_export_history_rows(self):
        cfg = ParadeConfig.from_preset("medium", total_units=20, seed=1)
        sim = ParadeOfTrades(cfg)
        sim.run()
        rows = sim.export_history_rows()
        self.assertEqual(len(rows), sim.period)
        self.assertIn("prod_1", rows[0])
        self.assertIn("buffer_1", rows[0])
        self.assertEqual(rows[-1]["cum_5"], 20)

    def test_to_dict_serialisable(self):
        import json

        r = run_preset("high", seed=5, total_units=40, verbose=False)
        d = r.to_dict()
        # must not raise
        s = json.dumps(d)
        self.assertIn("duration", s)


class TestVariabilityImpact(unittest.TestCase):
    """Qualitative checks aligned with Tommelein et al. findings."""

    def test_no_var_best_duration_same_seed(self):
        results = compare_presets(
            presets=["no_variability", "low", "medium", "high", "very_high"],
            seed=42,
            total_units=100,
            verbose=False,
        )
        no_var = results["no_variability"]
        self.assertEqual(no_var.duration, 20)
        self.assertEqual(no_var.total_idle_capacity, 0)

        # With variability, duration should be >= ideal (almost always >)
        for name in ["low", "medium", "high", "very_high"]:
            self.assertGreaterEqual(
                results[name].duration,
                no_var.duration,
                msg=f"{name} shorter than no_variability",
            )
            self.assertGreater(
                results[name].total_idle_capacity,
                0,
                msg=f"{name} should waste some capacity",
            )

    def test_higher_var_tends_to_more_idle(self):
        # Across a few seeds, average idle should increase with variability
        presets = ["low", "medium", "high", "very_high"]
        avg_idle = {p: 0.0 for p in presets}
        seeds = range(10)
        for seed in seeds:
            for p in presets:
                r = run_preset(p, seed=seed, verbose=False)
                avg_idle[p] += r.total_idle_capacity
        for p in presets:
            avg_idle[p] /= len(list(seeds))

        self.assertLess(avg_idle["low"], avg_idle["medium"])
        self.assertLess(avg_idle["medium"], avg_idle["high"])
        self.assertLess(avg_idle["high"], avg_idle["very_high"])


class TestEdgeCases(unittest.TestCase):
    def test_single_trade(self):
        cfg = ParadeConfig.from_pairs([(5, 5)], total_units=15, seed=0)
        sim = ParadeOfTrades(cfg)
        r = sim.run()
        self.assertEqual(r.duration, 3)
        self.assertEqual(r.max_buffer, [])
        self.assertEqual(r.trade_metrics[0].total_production, 15)

    def test_small_total(self):
        r = run_preset("medium", seed=0, total_units=1, verbose=False)
        self.assertEqual(r.trade_metrics[-1].total_production, 1)
        self.assertGreaterEqual(r.duration, 1)

    def test_all_presets_defined_mean_five(self):
        for name, (lo, hi) in CAPACITY_PRESETS.items():
            self.assertEqual((lo + hi) / 2, 5.0, msg=name)


if __name__ == "__main__":
    unittest.main()
