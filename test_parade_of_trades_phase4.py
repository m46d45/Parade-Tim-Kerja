"""Tests for Phase 4: takt, replications, export."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from parade_of_trades_analysis import (
    compare_tommelein2020,
    export_result_csv,
    export_result_excel,
    run_replications,
)
from parade_of_trades_core import (
    ParadeConfig,
    ParadeOfTrades,
    run_preset,
    tommelein2020_scenarios,
)


class TestTaktStandby(unittest.TestCase):
    def test_standby_covers_shortfall(self):
        # Always roll 4, takt 5, standby 1 → effective always 5
        cfg = ParadeConfig.from_pairs(
            [(4, 4)] * 3,
            total_units=20,
            seed=0,
            takt_rate=5,
            standby_capacity=1,
            same_period_handoff=True,
        )
        sim = ParadeOfTrades(cfg)
        rec = sim.step()
        self.assertEqual(rec.capacity, [4, 4, 4])
        self.assertEqual(rec.effective_capacity, [5, 5, 5])
        self.assertEqual(rec.standby_used, [1, 1, 1])
        self.assertEqual(rec.production, [5, 5, 5])

    def test_no_standby_when_die_meets_takt(self):
        cfg = ParadeConfig.from_pairs(
            [(6, 6)] * 2,
            total_units=12,
            seed=0,
            takt_rate=5,
            standby_capacity=1,
            same_period_handoff=True,
        )
        sim = ParadeOfTrades(cfg)
        rec = sim.step()
        self.assertEqual(rec.capacity, [6, 6])
        self.assertEqual(rec.effective_capacity, [6, 6])
        self.assertEqual(rec.standby_used, [0, 0])
        self.assertEqual(rec.production, [6, 6])

    def test_takt_4_6_equivalent_to_5_6_production(self):
        # Force constant low die + standby → same as constant 5, with stagger.
        cfg_takt = ParadeConfig.from_pairs(
            [(4, 4), (4, 4)],
            total_units=20,
            seed=1,
            takt_rate=5,
            standby_capacity=1,
            same_period_handoff=False,
        )
        cfg_equiv = ParadeConfig.from_pairs(
            [(5, 5), (5, 5)],
            total_units=20,
            seed=1,
            same_period_handoff=False,
        )
        r1 = ParadeOfTrades(cfg_takt).run()
        r2 = ParadeOfTrades(cfg_equiv).run()
        self.assertEqual(r1.duration, r2.duration)
        # 20/5 = 4 work + 1 next-period lag between 2 trades
        self.assertEqual(r1.duration, 5)

    def test_classic_unchanged_without_takt(self):
        r = run_preset("no_variability", seed=0, total_units=100, verbose=False)
        # Default next-period handoff: 20 work + 4 zone-sequence lags
        self.assertEqual(r.duration, 24)
        self.assertEqual(r.total_standby_used, 0)
        self.assertFalse(r.config.takt_enabled)
        self.assertFalse(r.config.same_period_handoff)

    def test_staggered_mobilization_delays_downstream(self):
        cfg = ParadeConfig.from_pairs(
            [(5, 5)] * 3,
            total_units=15,
            seed=0,
            staggered_mobilization=True,
        )
        sim = ParadeOfTrades(cfg)
        r1 = sim.step()
        # Only trade 0 mobilized in period 1
        self.assertEqual(r1.production[0], 5)
        self.assertEqual(r1.production[1], 0)
        self.assertEqual(r1.production[2], 0)
        r2 = sim.step()
        self.assertEqual(r2.production[1], 5)
        self.assertEqual(r2.production[2], 0)
        result = sim.run()
        # Last trade starts period 3; needs 3 more periods → finish period 5
        self.assertEqual(result.trade_metrics[2].start_period, 3)
        self.assertEqual(result.duration, 5)

    def test_standby_tracked_in_result(self):
        r = run_preset(
            "low", seed=42, total_units=50, verbose=False,
            takt_rate=5, standby_capacity=1,
        )
        self.assertTrue(r.config.takt_enabled)
        self.assertGreater(r.total_standby_used, 0)
        self.assertTrue(any(m.total_standby_used > 0 for m in r.trade_metrics))


class TestReplications(unittest.TestCase):
    def test_run_replications_count(self):
        cfg = ParadeConfig.from_preset("medium", total_units=40)
        batch = run_replications(cfg, n_reps=12, seed_base=10, verbose=False)
        self.assertEqual(len(batch.results), 12)
        self.assertEqual(batch.seeds, list(range(10, 22)))
        st = batch.stats()
        self.assertEqual(st["duration"].n, 12)
        self.assertGreater(st["duration"].mean, 0)
        self.assertGreaterEqual(st["duration"].max, st["duration"].min)

    def test_tommelein2020_s2_more_stable_than_s1(self):
        # With enough reps, S2 duration std should be <= S1 (more reliable)
        cmp = compare_tommelein2020(
            n_reps=40, seed_base=0, total_units=100, verbose=False
        )
        s1 = cmp.batches["S1_classic_4/6"].stats()["duration"]
        s2 = cmp.batches["S2_takt_4/6+stby1"].stats()["duration"]
        s3 = cmp.batches["S3_classic_5/7"].stats()["duration"]
        # S2 mean duration between S1 and S3 typically; std of S2 smaller than S1
        self.assertLessEqual(s2.std, s1.std + 0.5)  # allow tiny noise
        self.assertLess(s2.mean, s1.mean)
        self.assertLessEqual(s3.mean, s2.mean + 1.0)

    def test_export_replications(self):
        cfg = ParadeConfig.from_preset("low", total_units=30)
        batch = run_replications(cfg, n_reps=5, seed_base=0, verbose=False)
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            csv_path = batch.export_csv(p / "r.csv")
            xlsx_path = batch.export_excel(p / "r.xlsx")
            self.assertTrue(csv_path.exists())
            self.assertTrue(xlsx_path.exists())
            self.assertGreater(csv_path.stat().st_size, 50)


class TestExport(unittest.TestCase):
    def test_export_single_run(self):
        r = run_preset("high", seed=3, total_units=25, verbose=False)
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            hist = export_result_csv(r, p / "h.csv")
            xlsx = export_result_excel(r, p / "r.xlsx")
            self.assertTrue(hist.exists())
            self.assertTrue((p / "h_summary.csv").exists())
            self.assertTrue(xlsx.exists())
            self.assertGreater(xlsx.stat().st_size, 1000)

    def test_export_takt_run(self):
        r = run_preset(
            "low", seed=1, total_units=40, verbose=False,
            takt_rate=5, standby_capacity=1,
        )
        with tempfile.TemporaryDirectory() as td:
            xlsx = export_result_excel(r, Path(td) / "takt.xlsx")
            self.assertTrue(xlsx.exists())


class TestTommeleinScenariosFactory(unittest.TestCase):
    def test_factory_keys(self):
        cfgs = tommelein2020_scenarios(total_units=100, seed=0)
        self.assertEqual(len(cfgs), 3)
        self.assertTrue(cfgs["S2_takt_4/6+stby1"].takt_enabled)
        self.assertEqual(cfgs["S2_takt_4/6+stby1"].standby_capacity, 1)
        self.assertFalse(cfgs["S1_classic_4/6"].takt_enabled)


if __name__ == "__main__":
    unittest.main()
