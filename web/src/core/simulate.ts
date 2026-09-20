/**
 * Zone-flow Parade Tim Kerja engine (port of parade_of_trades_core.py).
 * Focus: classroom zone_flow path used by the Streamlit app.
 */

import {
  buildIdealTwinConfig,
  nInterfaces,
  tradeMean,
} from "./config";
import type {
  ParadeConfig,
  ParadeResult,
  PeriodRecord,
  TradeMetrics,
} from "./types";

/** Mulberry32 — deterministic in JS; not bit-identical to Python random. */
function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

class ParadeOfTrades {
  config: ParadeConfig;
  private rng: () => number;
  period = 0;
  cumulative: number[] = [];
  buffers: number[] = [];
  rawRemaining = 0;
  maxBuffer: number[] = [];
  history: PeriodRecord[] = [];
  private zoneProgress: number[] = [];
  private zoneRate: Array<number | null> = [];
  private batchDone: number[] = [];
  private working: boolean[] = [];
  private totalCapacity: number[] = [];
  private totalEffective: number[] = [];
  private totalProduction: number[] = [];
  private totalIdle: number[] = [];
  private totalStandby: number[] = [];
  private executions: number[] = [];
  private finishPeriod: Array<number | null> = [];
  private startPeriod: Array<number | null> = [];

  constructor(config: ParadeConfig) {
    this.config = config;
    const seed = config.seed == null ? 0 : config.seed;
    this.rng = mulberry32(seed);
    this.reset();
  }

  reset(): void {
    const n = this.config.trades.length;
    const nIf = nInterfaces(this.config);
    this.period = 0;
    this.cumulative = Array(n).fill(0);
    this.buffers = Array(nIf).fill(0);
    this.rawRemaining = this.config.totalUnits;
    this.maxBuffer = Array(nIf).fill(0);
    this.history = [];
    this.zoneProgress = Array(n).fill(0);
    this.zoneRate = Array(n).fill(null);
    this.batchDone = Array(n).fill(0);
    this.working = Array(n).fill(false);
    this.totalCapacity = Array(n).fill(0);
    this.totalEffective = Array(n).fill(0);
    this.totalProduction = Array(n).fill(0);
    this.totalIdle = Array(n).fill(0);
    this.totalStandby = Array(n).fill(0);
    this.executions = Array(n).fill(0);
    this.finishPeriod = Array(n).fill(null);
    this.startPeriod = Array(n).fill(null);
  }

  get isComplete(): boolean {
    return this.cumulative[this.cumulative.length - 1] >= this.config.totalUnits;
  }

  private isMobilized(tradeIdx: number): boolean {
    const offs = this.config.mobilizationOffsets;
    if (offs != null) {
      const delay = tradeIdx < offs.length ? offs[tradeIdx] : 0;
      return this.period >= delay + 1;
    }
    if (!this.config.staggeredMobilization) return true;
    return this.period >= tradeIdx + 1;
  }

  private drawZoneRate(tradeIdx: number): number {
    const t = this.config.trades[tradeIdx];
    if (t.deterministic || t.low === t.high) {
      return Math.max(1e-9, t.baseSpeed || tradeMean(t));
    }
    const rate = this.rng() < t.pHigh ? t.high : t.low;
    return Math.max(1e-9, rate);
  }

  private crewCap(rate: number): number {
    if (rate + 1e-12 >= 1.0) return Math.max(1, Math.round(rate));
    return 1;
  }

  step(): PeriodRecord {
    if (this.isComplete) throw new Error("Simulation already complete; call reset()");
    if (!this.config.zoneFlow) {
      throw new Error("JS engine v0.1: only zone_flow=true is implemented");
    }
    return this.stepZoneFlow();
  }

  private stepZoneFlow(): PeriodRecord {
    this.period += 1;
    const n = this.config.trades.length;
    const total = this.config.totalUnits;
    const batchSize = Math.max(1, this.config.batchSize | 0);

    const capacities = Array(n).fill(0);
    const effectives = Array(n).fill(0);
    const standbys = Array(n).fill(0);
    const productions = Array(n).fill(0);
    const idles = Array(n).fill(0);
    const released = Array(n).fill(0);

    const available = [this.rawRemaining, ...this.buffers];

    for (let i = 0; i < n; i++) {
      if (this.cumulative[i] >= total || !this.isMobilized(i)) continue;

      const tcfg = this.config.trades[i];
      const baseRate = tcfg.baseSpeed || tradeMean(tcfg);
      let rateApplied = 0;
      const hasStarted = this.startPeriod[i] != null;

      if (!this.working[i] && available[i] <= 0) {
        if (hasStarted && this.cumulative[i] < total) {
          const cap = this.crewCap(baseRate);
          capacities[i] = cap;
          effectives[i] = cap;
          productions[i] = 0;
          idles[i] = cap;
          this.executions[i] += 1;
          this.totalCapacity[i] += cap;
          this.totalEffective[i] += cap;
          this.totalIdle[i] += cap;
        }
        continue;
      }

      if (!this.working[i]) {
        available[i] -= 1;
        this.working[i] = true;
        this.zoneProgress[i] = 0;
        this.zoneRate[i] = this.drawZoneRate(i);
        if (this.startPeriod[i] == null) this.startPeriod[i] = this.period;
      }

      const rate = this.zoneRate[i] ?? 0;
      rateApplied = rate;
      this.zoneProgress[i] += rate;

      while (this.zoneProgress[i] + 1e-12 >= 1.0 && this.cumulative[i] < total) {
        this.zoneProgress[i] -= 1.0;
        this.cumulative[i] += 1;
        productions[i] += 1;
        this.batchDone[i] += 1;
        this.working[i] = false;

        if (this.batchDone[i] >= batchSize) {
          released[i] += this.batchDone[i];
          this.batchDone[i] = 0;
        }

        if (this.cumulative[i] >= total) {
          this.zoneProgress[i] = 0;
          if (this.finishPeriod[i] == null) this.finishPeriod[i] = this.period;
          break;
        }

        if (this.zoneProgress[i] > 1e-12) {
          if (available[i] > 0) {
            available[i] -= 1;
            this.working[i] = true;
            this.zoneRate[i] = this.drawZoneRate(i);
          } else {
            this.zoneProgress[i] = 0;
            break;
          }
        } else {
          break;
        }
      }

      if (this.cumulative[i] >= total && this.batchDone[i] > 0) {
        released[i] += this.batchDone[i];
        this.batchDone[i] = 0;
      }

      let cap: number;
      let idle: number;
      if (rateApplied + 1e-12 >= 1.0) {
        cap = Math.max(productions[i], this.crewCap(rateApplied));
        idle = Math.max(0, cap - productions[i]);
      } else {
        cap = productions[i];
        idle = 0;
      }
      capacities[i] = cap;
      effectives[i] = cap;
      idles[i] = idle;

      if (productions[i] > 0 || this.working[i] || idle > 0) {
        this.executions[i] += 1;
      }
      this.totalCapacity[i] += capacities[i];
      this.totalEffective[i] += effectives[i];
      this.totalProduction[i] += productions[i];
      this.totalIdle[i] += idles[i];
    }

    this.rawRemaining = available[0];
    const newBuffers = Array(nInterfaces(this.config)).fill(0);
    for (let j = 0; j < nInterfaces(this.config); j++) {
      newBuffers[j] = available[j + 1] + released[j];
      if (newBuffers[j] > this.maxBuffer[j]) this.maxBuffer[j] = newBuffers[j];
    }
    this.buffers = newBuffers;

    const fractional = this.cumulative.map((c, i) =>
      Math.min(total, c + (this.working[i] ? this.zoneProgress[i] : 0)),
    );

    const rec: PeriodRecord = {
      period: this.period,
      capacity: capacities,
      production: productions,
      idleCapacity: idles,
      cumulative: [...this.cumulative],
      buffers: [...this.buffers],
      rawRemaining: this.rawRemaining,
      effectiveCapacity: effectives,
      standbyUsed: standbys,
      fractionalCumulative: fractional,
    };
    this.history.push(rec);
    return rec;
  }

  run(opts?: { maxPeriods?: number; computeIdeal?: boolean }): ParadeResult {
    const computeIdeal = opts?.computeIdeal ?? true;
    let maxPeriods = opts?.maxPeriods;
    if (maxPeriods == null) {
      if (this.config.zoneFlow) {
        const minRate = Math.min(
          ...this.config.trades.map((t) => Math.max(t.low, 1e-6)),
        );
        maxPeriods = Math.max(
          Math.floor(
            (this.config.totalUnits / minRate) * this.config.trades.length * 4,
          ) +
            this.config.batchSize * this.config.trades.length * 2 +
            100,
          this.config.totalUnits * this.config.trades.length * 5,
          500,
        );
      } else {
        maxPeriods = Math.max(
          this.config.totalUnits * this.config.trades.length * 5,
          this.config.totalUnits * 10,
          1,
        );
      }
    }

    while (!this.isComplete) {
      if (this.period >= maxPeriods) {
        throw new Error(`Simulation exceeded max_periods=${maxPeriods}`);
      }
      this.step();
    }
    return this.buildResult(computeIdeal);
  }

  private buildResult(computeIdeal: boolean): ParadeResult {
    const total = this.config.totalUnits;
    const n = this.config.trades.length;
    const metrics: TradeMetrics[] = [];
    for (let i = 0; i < n; i++) {
      const t = this.config.trades[i];
      const eff = this.totalEffective[i];
      const base = this.totalCapacity[i];
      const prod = this.totalProduction[i];
      const denom = eff > 0 ? eff : base;
      const util = denom > 0 ? prod / denom : 0;
      let finish = this.finishPeriod[i];
      if (finish == null && this.cumulative[i] >= total) finish = this.period;
      const start = this.startPeriod[i];
      const timeOnSite =
        finish != null && start != null ? finish - start + 1 : this.executions[i];
      metrics.push({
        name: t.name,
        meanCapacity: tradeMean(t),
        totalProduction: prod,
        totalIdle: this.totalIdle[i],
        totalEffectiveCapacity: eff,
        utilization: util,
        periodsToFinish: finish ?? this.period,
        timeOnSite,
        startPeriod: start,
      });
    }

    const duration = this.period;
    const throughput = duration > 0 ? total / duration : 0;

    let idealDuration: number;
    let idealLast: number[];
    if (computeIdeal) {
      const twin = runParade(buildIdealTwinConfig(this.config), {
        computeIdeal: false,
      });
      idealDuration = twin.duration;
      idealLast = twin.idealLastTradeCumulative;
    } else {
      idealDuration = duration;
      const cum: number[][] = Array.from({ length: n }, () => [0]);
      for (const rec of this.history) {
        for (let i = 0; i < n; i++) cum[i].push(rec.cumulative[i] | 0);
      }
      idealLast = cum[n - 1] ?? [0];
    }

    return {
      config: this.config,
      duration,
      history: [...this.history],
      tradeMetrics: metrics,
      maxBuffer: [...this.maxBuffer],
      totalIdleCapacity: this.totalIdle.reduce((a, b) => a + b, 0),
      systemThroughput: throughput,
      idealDuration,
      idealLastTradeCumulative: idealLast,
    };
  }
}

export function runParade(
  config: ParadeConfig,
  opts?: { maxPeriods?: number; computeIdeal?: boolean },
): ParadeResult {
  return new ParadeOfTrades(config).run(opts);
}

export function cumulativeSeries(result: ParadeResult): number[][] {
  const n = result.config.trades.length;
  const series: number[][] = Array.from({ length: n }, () => [0]);
  for (const rec of result.history) {
    for (let i = 0; i < n; i++) series[i].push(rec.cumulative[i] | 0);
  }
  return series;
}

export function bufferSeries(result: ParadeResult): number[][] {
  const nIf = nInterfaces(result.config);
  const series: number[][] = Array.from({ length: nIf }, () => [0]);
  for (const rec of result.history) {
    for (let j = 0; j < nIf; j++) series[j].push(rec.buffers[j] | 0);
  }
  return series;
}
