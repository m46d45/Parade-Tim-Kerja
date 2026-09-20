import { describe, expect, it } from "vitest";
import {
  buildTaktPlan,
  classroomConfig,
  computeCostMetrics,
  computeTaktClassroom,
  cumulativeSeries,
  inventoryFillRateMetrics,
  irisBufferSweep,
  irisMobilizationGrid,
  kingmanCombined,
  kingmanMetrics,
  littlesLawMetrics,
  littlesOperationsCurve,
  littlesTaktDuration,
  runParade,
  runTimeInventoryBuffer,
} from "../src/core";
import batch1 from "../fixtures/zf_novar_batch1_z10.json";
import batch4 from "../fixtures/zf_novar_batch4_z10.json";
import speed05 from "../fixtures/zf_novar_batch1_speed05_z6.json";

type Fixture = typeof batch1;

function assertParity(fixture: Fixture, batch: number, speed: number, n: number) {
  const cfg = classroomConfig({
    totalUnits: n,
    batchSize: batch,
    baseSpeed: speed,
    seed: fixture.meta.seed,
    deterministic: true,
  });
  const r = runParade(cfg);
  expect(r.duration).toBe(fixture.duration);
  expect(r.idealDuration).toBe(fixture.ideal_duration);
  expect(r.maxBuffer).toEqual(fixture.max_buffer);
  expect(r.tradeMetrics.map((m) => m.startPeriod)).toEqual(fixture.starts);
  expect(r.tradeMetrics.map((m) => m.periodsToFinish)).toEqual(fixture.finishes);
  expect(cumulativeSeries(r)).toEqual(fixture.cumulative);
  expect(r.idealLastTradeCumulative).toEqual(fixture.ideal_last_trade_cumulative);
  expect(r.history.map((h) => h.production)).toEqual(fixture.production_history);
}

describe("zone-flow parity vs Python golden fixtures", () => {
  it("no-var batch=1, 10 zones", () => {
    assertParity(batch1, 1, 1.0, 10);
  });

  it("no-var batch=4, 10 zones", () => {
    assertParity(batch4, 4, 1.0, 10);
  });

  it("no-var speed=0.5, batch=1, 6 zones", () => {
    assertParity(speed05, 1, 0.5, 6);
  });

  it("ideal equals actual when deterministic", () => {
    const r = runParade(
      classroomConfig({ totalUnits: 10, batchSize: 4, baseSpeed: 1, deterministic: true }),
    );
    expect(r.duration).toBe(r.idealDuration);
    expect(r.idealLastTradeCumulative).toEqual(cumulativeSeries(r)[4]);
  });

  it("medium variability runs and is >= ideal duration", () => {
    const r = runParade(
      classroomConfig({
        totalUnits: 10,
        batchSize: 4,
        baseSpeed: 1,
        seed: 12345,
        variability: "medium",
      }),
    );
    expect(r.duration).toBeGreaterThanOrEqual(r.idealDuration);
    expect(r.idealDuration).toBe(26);
    expect(cumulativeSeries(r)[0][0]).toBe(0);
  });
});

describe("cost metrics (parity vs Python classroom batch=4)", () => {
  it("no-var: util 100%, total biaya 5000 @ tarif 100", () => {
    const r = runParade(
      classroomConfig({
        totalUnits: 10,
        batchSize: 4,
        baseSpeed: 1,
        seed: 12345,
        deterministic: true,
      }),
    );
    for (const m of r.tradeMetrics) {
      expect(m.utilization).toBe(1);
      expect(m.totalIdle).toBe(0);
      expect(m.totalProduction).toBe(10);
    }
    const cm = computeCostMetrics(r, [100, 100, 100, 100, 100]);
    expect(cm.totalActive).toBe(5000);
    expect(cm.totalIdle).toBe(0);
    expect(cm.totalCost).toBe(5000);
    for (const t of cm.trades) {
      expect(t.periodsActive).toBe(10);
      expect(t.periodsIdle).toBe(0);
      expect(t.costTotal).toBe(1000);
    }
  });

  it("scales with tarif", () => {
    const r = runParade(
      classroomConfig({ totalUnits: 10, batchSize: 4, deterministic: true }),
    );
    const cm = computeCostMetrics(r, [200, 200, 200, 200, 200]);
    expect(cm.totalCost).toBe(10000);
  });
});

describe("Little's Law + Kingman (parity vs Python no-var batch=4)", () => {
  it("Little metrics match Python golden", () => {
    const r = runParade(
      classroomConfig({
        totalUnits: 10,
        batchSize: 4,
        baseSpeed: 1,
        seed: 12345,
        deterministic: true,
      }),
    );
    const ll = littlesLawMetrics(r);
    expect(ll.throughput).toBeCloseTo(10 / 26, 10);
    expect(ll.avgPipelineWip).toBeCloseTo(5.925925925925926, 10);
    expect(ll.avgBufferWip).toBeCloseTo(4.0, 10);
    expect(ll.cycleTimePipeline).toBeCloseTo(15.407407407407407, 10);
    expect(ll.cycleTimeBuffer).toBeCloseTo(10.4, 10);
    expect(ll.checkPipeline).toBeCloseTo(ll.avgPipelineWip, 10);
    expect(ll.peakPipelineWip).toBe(10);
    expect(ll.peakBufferWip).toBe(10);
  });

  it("Kingman no-var: V=0, CT=t_e, Σ CT=5", () => {
    const r = runParade(
      classroomConfig({
        totalUnits: 10,
        batchSize: 4,
        baseSpeed: 1,
        seed: 12345,
        deterministic: true,
      }),
    );
    const kg = kingmanMetrics(r);
    const comb = kingmanCombined(r);
    expect(comb.uBar).toBeCloseTo(1, 10);
    expect(comb.v).toBeCloseTo(0, 10);
    expect(comb.ct).toBeCloseTo(1, 10);
    expect(kg.sumCtKingman).toBeCloseTo(5, 10);
    expect(kg.sumCtObserved).toBeCloseTo(5, 10);
    expect(kg.systemCtLittle).toBeCloseTo(15.407407407407407, 10);
    for (const s of kg.stations) {
      expect(s.ctKingman).toBeCloseTo(1, 10);
      expect(s.ctObserved).toBeCloseTo(1, 10);
      expect(s.cE).toBe(0);
    }
  });

  it("Kingman medium config moments: t_e=4/3, c_e>0", () => {
    const r = runParade(
      classroomConfig({
        totalUnits: 10,
        batchSize: 4,
        baseSpeed: 1,
        seed: 12345,
        variability: "medium",
      }),
    );
    const comb = kingmanCombined(r);
    expect(comb.tE).toBeCloseTo(4 / 3, 6);
    expect(comb.cE).toBeCloseTo(0.5, 6);
    expect(comb.v).toBeGreaterThan(0);
    expect(comb.ct).toBeGreaterThan(comb.tE);
  });
});

describe("Inventory/FR + operations curve (parity vs Python no-var batch=4)", () => {
  it("Inventory fill rate: I̅=1, FR=100%, peak per buffer=4", () => {
    const r = runParade(
      classroomConfig({
        totalUnits: 10,
        batchSize: 4,
        baseSpeed: 1,
        seed: 12345,
        deterministic: true,
      }),
    );
    const fr = inventoryFillRateMetrics(r);
    expect(fr.avgInventorySystem).toBeCloseTo(1, 10);
    expect(fr.fillRateSystem).toBeCloseTo(1, 10);
    expect(fr.fillRateT1).toBeCloseTo(1, 10);
    expect(fr.peakBufferTotal).toBe(10);
    expect(fr.interfaces).toHaveLength(4);
    for (const row of fr.interfaces) {
      expect(row.avgInventory).toBeCloseTo(1, 10);
      expect(row.peakInventory).toBe(4);
      expect(row.fillRate).toBeCloseTo(1, 10);
      expect(row.downstreamIdle).toBe(0);
    }
  });

  it("operations curve: W_min=W_opt=5, TH_max=1, T0=5", () => {
    const r = runParade(
      classroomConfig({
        totalUnits: 10,
        batchSize: 4,
        baseSpeed: 1,
        seed: 12345,
        deterministic: true,
      }),
    );
    const d = littlesOperationsCurve(r);
    expect(d.wMin).toBeCloseTo(5, 10);
    expect(d.wOpt).toBeCloseTo(5, 10);
    expect(d.conwip).toBeCloseTo(5, 10);
    expect(d.thMax).toBeCloseTo(1, 10);
    expect(d.t0).toBeCloseTo(5, 10);
    expect(d.vFactor).toBeCloseTo(0, 10);
    expect(d.opWip).toBeCloseTo(5.925925925925926, 10);
  });

  it("utilisasi exposes kapasitas efektif", () => {
    const r = runParade(
      classroomConfig({ totalUnits: 10, batchSize: 4, deterministic: true }),
    );
    for (const m of r.tradeMetrics) {
      expect(m.totalEffectiveCapacity).toBe(10);
      expect(m.totalProduction).toBe(10);
    }
  });
});

describe("perbandingan multi-skenario", () => {
  it("5× variability runs and duration is non-decreasing with var level", () => {
    const levels = ["none", "low", "medium", "high", "very_high"] as const;
    const results = levels.map((variability) =>
      runParade(
        classroomConfig({
          totalUnits: 10,
          batchSize: 4,
          baseSpeed: 1,
          seed: 12345,
          variability,
        }),
      ),
    );
    expect(results[0].duration).toBe(26);
    expect(results[0].duration).toBe(results[0].idealDuration);
    for (const r of results) {
      expect(r.duration).toBeGreaterThanOrEqual(r.idealDuration);
      expect(r.idealDuration).toBe(26);
    }
  });

  it("batch 1 vs 4: one-piece finishes earlier when no-var", () => {
    const b1 = runParade(
      classroomConfig({ totalUnits: 10, batchSize: 1, deterministic: true }),
    );
    const b4 = runParade(
      classroomConfig({ totalUnits: 10, batchSize: 4, deterministic: true }),
    );
    expect(b1.duration).toBeLessThan(b4.duration);
  });
});

describe("takt plan (Little's Takt Law)", () => {
  it("TD = (TW+TZ−1)×TT classroom defaults TZ=10, te=1 → TD=14", () => {
    expect(littlesTaktDuration(5, 10, 1)).toBe(14);
    const r = computeTaktClassroom({
      tz: 10,
      capBayPerDay: 4,
      tPerFloor: 15,
    });
    expect(r.baysPerZone).toBe(4);
    expect(r.capZone).toBeCloseTo(1, 10);
    expect(r.te).toBeCloseTo(1, 10);
    expect(r.tdFloor).toBeCloseTo(14, 10);
    expect(r.ok).toBe(true);
    expect(r.plan.duration).toBe(14);
    expect(r.plan.cells).toHaveLength(50);
    expect(r.plan.cells[0]).toMatchObject({
      tradeIndex: 0,
      zone: 1,
      periodStart: 0,
      periodEnd: 1,
    });
  });

  it("buildTaktPlan cells follow (i+z)×TT", () => {
    const p = buildTaktPlan({ nTrades: 5, nZones: 10, rate: 1 });
    expect(p.taktTime).toBe(1);
    expect(p.cells[p.cells.length - 1]).toMatchObject({
      tradeIndex: 4,
      zone: 10,
      periodStart: 13,
      periodEnd: 14,
    });
  });
});

describe("buffer waktu–inventory (Iris)", () => {
  it("no-var tight mobilization: TOS=50, duration≥14, INV>0", () => {
    const r = runTimeInventoryBuffer({
      die: "no_variability",
      mobilization: "0-1-2-3-4",
      totalUnits: 10,
      seed: 0,
    });
    expect(r.config.zoneFlow).toBe(true);
    expect(r.config.batchSize).toBe(1);
    expect(r.totalTimeOnSite).toBe(50);
    expect(r.totalInventoryTime).toBeGreaterThan(0);
    expect(r.duration).toBeGreaterThanOrEqual(14);
  });

  it("looser start → longer duration and ≥ inventory", () => {
    const tight = runTimeInventoryBuffer({
      die: "no_variability",
      mobilization: "0-1-2-3-4",
      totalUnits: 10,
      seed: 0,
    });
    const wide = runTimeInventoryBuffer({
      die: "no_variability",
      mobilization: "0-3-6-9-12",
      totalUnits: 10,
      seed: 0,
    });
    expect(wide.duration).toBeGreaterThan(tight.duration);
    expect(wide.totalInventoryTime).toBeGreaterThanOrEqual(
      tight.totalInventoryTime,
    );
  });

  it("irisBufferSweep yields 9 anchor points, tos_floor=50", () => {
    const grid = irisMobilizationGrid(3);
    expect(Object.keys(grid)).toHaveLength(81);
    const rows = irisBufferSweep({
      totalUnits: 10,
      seed: 1,
      nReps: 3,
    });
    expect(rows).toHaveLength(9);
    const labels = new Set(rows.map((r) => r.label));
    expect(labels.has("medium 0-3-6-9-12")).toBe(true);
    expect(labels.has("low 0-1-2-3-4")).toBe(true);
    expect(rows.every((r) => r.tos_floor === 50)).toBe(true);
  });

  it("ParadeResult exposes totalInventoryTime / totalTimeOnSite", () => {
    const r = runParade(
      classroomConfig({ totalUnits: 10, batchSize: 1, deterministic: true }),
    );
    expect(r.totalTimeOnSite).toBe(
      r.tradeMetrics.reduce((a, m) => a + m.timeOnSite, 0),
    );
    expect(r.totalInventoryTime).toBeGreaterThan(0);
  });
});
