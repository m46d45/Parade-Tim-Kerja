"""
Unit tests for parade_of_trades_core.py
"""

from __future__ import annotations

import unittest

from parade_of_trades_core import (
    CAPACITY_PRESETS,
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
        self.assertFalse(cfg.same_period_handoff)
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


class TestZoneSequenceNextPeriod(unittest.TestCase):
    """Default: each zone waits 1 period between consecutive trades."""

    def setUp(self):
        self.cfg = ParadeConfig.from_preset(
            "no_variability", total_units=100, seed=42
        )
        self.assertFalse(self.cfg.same_period_handoff)
        self.sim = ParadeOfTrades(self.cfg)
        self.result = self.sim.run()

    def test_cascade_start_periods(self):
        # T1@1, T2@2, … T5@5 natural from empty downstream buffers
        for i, m in enumerate(self.result.trade_metrics):
            self.assertEqual(m.start_period, i + 1)
            self.assertEqual(m.periods_to_finish, 20 + i)
            self.assertEqual(m.total_production, 100)
            self.assertEqual(m.time_on_site, 20)

    def test_duration_pipeline(self):
        self.assertEqual(self.result.duration, 24)
        self.assertEqual(self.result.ideal_duration, 24.0)

    def test_period1_only_trade1(self):
        rec = self.result.history[0]
        self.assertEqual(rec.production, [5, 0, 0, 0, 0])
        self.assertEqual(rec.buffers[0], 5)
        self.assertEqual(rec.buffers[1:], [0, 0, 0])

    def test_period2_trade1_and_2(self):
        rec = self.result.history[1]
        self.assertEqual(rec.production[0], 5)
        self.assertEqual(rec.production[1], 5)
        self.assertEqual(rec.production[2], 0)
        # T1 put 5 more into B1; T2 took the 5 from period1 → B1 still 5; B2=5
        self.assertEqual(rec.buffers[0], 5)
        self.assertEqual(rec.buffers[1], 5)

    def test_zone_path_min_lag(self):
        # First finished unit reaches trade 5 only at period 5
        for rec in self.result.history:
            if rec.period < 5:
                self.assertEqual(rec.cumulative[-1], 0)
            else:
                self.assertGreater(rec.cumulative[-1], 0)
                break


class TestSamePeriodHandoff(unittest.TestCase):
    """Classic game: downstream may pull upstream output same period."""

    def setUp(self):
        self.cfg = ParadeConfig.from_preset(
            "no_variability", total_units=100, seed=42,
            same_period_handoff=True,
        )
        self.sim = ParadeOfTrades(self.cfg)
        self.result = self.sim.run()

    def test_duration_is_ideal(self):
        self.assertEqual(self.result.duration, 20)
        self.assertEqual(self.result.ideal_duration, 20.0)

    def test_all_trades_finish_together(self):
        for m in self.result.trade_metrics:
            self.assertEqual(m.periods_to_finish, 20)
            self.assertEqual(m.total_production, 100)
            self.assertEqual(m.utilization, 1.0)
            self.assertEqual(m.total_idle, 0)

    def test_no_buffer_buildup(self):
        for rec in self.result.history:
            self.assertEqual(rec.buffers, [0, 0, 0, 0])
        self.assertEqual(self.result.max_buffer, [0, 0, 0, 0])

    def test_first_period_all_produce(self):
        rec = self.result.history[0]
        self.assertEqual(rec.production, [5, 5, 5, 5, 5])


class TestSequentialBufferUpdate(unittest.TestCase):
    def test_starvation_when_upstream_low(self):
        cfg = ParadeConfig.from_pairs(
            [(1, 1), (9, 9)], total_units=10, seed=0,
            same_period_handoff=True,
        )
        sim = ParadeOfTrades(cfg)
        rec = sim.step()
        self.assertEqual(rec.production[0], 1)
        self.assertEqual(rec.production[1], 1)
        self.assertEqual(rec.idle_capacity[1], 8)
        self.assertEqual(rec.buffers[0], 0)

    def test_next_period_starvation_first_step(self):
        # Period 1: only T1 can work; T2 has empty buffer
        cfg = ParadeConfig.from_pairs(
            [(1, 1), (9, 9)], total_units=10, seed=0,
            same_period_handoff=False,
        )
        sim = ParadeOfTrades(cfg)
        rec = sim.step()
        self.assertEqual(rec.production[0], 1)
        self.assertEqual(rec.production[1], 0)
        self.assertEqual(rec.buffers[0], 1)

    def test_buffer_builds_when_downstream_low(self):
        cfg = ParadeConfig.from_pairs(
            [(9, 9), (1, 1)], total_units=20, seed=0,
            same_period_handoff=True,
        )
        sim = ParadeOfTrades(cfg)
        rec = sim.step()
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
        self.assertEqual(r2.production[0], 2)
        self.assertTrue(sim.is_complete)
        self.assertEqual(sim.cumulative[0], 10)

    def test_trade_stops_after_finish(self):
        cfg = ParadeConfig.from_pairs(
            [(5, 5), (5, 5)], total_units=5, seed=0,
            same_period_handoff=True,
        )
        sim = ParadeOfTrades(cfg)
        sim.step()
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
        self.assertEqual(len(cum[0]), r.duration + 1)
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
        s = json.dumps(d)
        self.assertIn("duration", s)


class TestVariabilityImpact(unittest.TestCase):
    def test_no_var_best_duration_same_seed(self):
        results = compare_presets(
            presets=["no_variability", "low", "medium", "high", "very_high"],
            seed=42,
            total_units=100,
            verbose=False,
        )
        no_var = results["no_variability"]
        self.assertEqual(no_var.duration, 24)
        self.assertEqual(no_var.total_idle_capacity, 0)

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

    def test_staggered_with_next_period(self):
        cfg = ParadeConfig.from_pairs(
            [(5, 5)] * 3, total_units=15, seed=0,
            same_period_handoff=False,
            staggered_mobilization=True,
        )
        sim = ParadeOfTrades(cfg)
        r1 = sim.step()
        self.assertEqual(r1.production, [5, 0, 0])
        result = sim.run()
        self.assertEqual(result.trade_metrics[2].start_period, 3)
        self.assertEqual(result.duration, 5)


if __name__ == "__main__":
    unittest.main()
