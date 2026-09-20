import { describe, expect, it } from "vitest";
import { classroomConfig, cumulativeSeries, runParade } from "../src/core";
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
});
