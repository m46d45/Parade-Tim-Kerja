import { describe, expect, it } from "vitest";
import {
  classroomConfig,
  computeCostMetrics,
  cumulativeSeries,
  runParade,
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
