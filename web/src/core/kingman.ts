/**
 * Kingman / VUT approximation — port of parade_of_trades_analysis.kingman_*.
 * CT ≈ t_e + ((c_a² + c_e²)/2) × (u/(1-u)) × t_e
 */

import { littlesLawMetrics } from "./littles";
import type { ParadeResult, TradeConfig } from "./types";
import { tradeMean } from "./config";

export interface KingmanStationRow {
  tradeIndex: number;
  name: string;
  utilization: number;
  tE: number;
  cE: number;
  cA: number;
  waitKingman: number;
  ctKingman: number;
  ctObserved: number;
  vFactor: number;
  uFactor: number;
}

export interface KingmanMetrics {
  stations: KingmanStationRow[];
  sumCtKingman: number;
  sumCtObserved: number;
  systemCtLittle: number;
  bottleneckU: number;
  note: string;
}

export interface KingmanCombined {
  uBar: number;
  tE: number;
  cA: number;
  cE: number;
  v: number;
  uFactor: number;
  wait: number;
  ct: number;
  bottleneckU: number;
}

function processTimeMoments(trade: TradeConfig): { tE: number; cE: number } {
  const lo = Math.max(trade.low, 1e-12);
  const hi = Math.max(trade.high, 1e-12);
  const p = trade.pHigh;
  if (trade.deterministic || Math.abs(lo - hi) < 1e-12) {
    const base = Math.max(trade.baseSpeed || tradeMean(trade), 1e-12);
    return { tE: 1 / base, cE: 0 };
  }
  const tLo = 1 / lo;
  const tHi = 1 / hi;
  const tE = (1 - p) * tLo + p * tHi;
  const variance = (1 - p) * (tLo - tE) ** 2 + p * (tHi - tE) ** 2;
  const cE = tE > 0 ? Math.sqrt(Math.max(variance, 0)) / tE : 0;
  return { tE, cE };
}

export function kingmanCt(
  u: number,
  tE: number,
  cA: number,
  cE: number,
): { wait: number; ct: number; vFactor: number; uFactor: number } {
  const uu = Number(u);
  const te = Math.max(Number(tE), 1e-12);
  const ca = Math.max(Number(cA), 0);
  const ce = Math.max(Number(cE), 0);
  const v = 0.5 * (ca ** 2 + ce ** 2);
  if (uu >= 1 - 1e-9) {
    return { wait: Infinity, ct: Infinity, vFactor: v, uFactor: Infinity };
  }
  if (uu <= 0) {
    return { wait: 0, ct: te, vFactor: v, uFactor: 0 };
  }
  const uFactor = uu / (1 - uu);
  const wait = v * uFactor * te;
  return { wait, ct: wait + te, vFactor: v, uFactor };
}

export function kingmanMetrics(result: ParadeResult): KingmanMetrics {
  const stations: KingmanStationRow[] = [];
  let prevCE = 0;
  for (let i = 0; i < result.tradeMetrics.length; i++) {
    const m = result.tradeMetrics[i];
    const trade = result.config.trades[i];
    const { tE, cE } = processTimeMoments(trade);
    const u = m.utilization;
    const uCalc = Math.min(u, 0.999);
    const cA = i === 0 ? 0 : prevCE;
    const { wait, ct, vFactor, uFactor } = kingmanCt(uCalc, tE, cA, cE);
    const prod = Math.max(m.totalProduction | 0, 1);
    const ctObserved = m.timeOnSite / prod;
    stations.push({
      tradeIndex: i,
      name: m.name,
      utilization: u,
      tE,
      cE,
      cA,
      waitKingman: wait,
      ctKingman: ct,
      ctObserved,
      vFactor,
      uFactor,
    });
    prevCE = cE;
  }

  const ll = littlesLawMetrics(result);
  const sumK = stations.reduce(
    (s, row) => s + (Number.isFinite(row.ctKingman) ? row.ctKingman : 0),
    0,
  );
  const sumO = stations.reduce((s, row) => s + row.ctObserved, 0);
  const bottleneckU = Math.max(0, ...stations.map((s) => s.utilization));

  return {
    stations,
    sumCtKingman: sumK,
    sumCtObserved: sumO,
    systemCtLittle: ll.cycleTimePipeline,
    bottleneckU,
    note:
      "Kingman = pendekatan antrian stasioner (VUT). Proyek parade berhingga + batch bisa beda; V↑ atau U↑ → CT↑.",
  };
}

export function kingmanCombined(result: ParadeResult): KingmanCombined {
  const k = kingmanMetrics(result);
  const n = Math.max(k.stations.length, 1);
  const uBar = k.stations.reduce((s, row) => s + row.utilization, 0) / n;
  const tE = k.stations.reduce((s, row) => s + row.tE, 0) / n;
  const cA = k.stations.reduce((s, row) => s + row.cA, 0) / n;
  const cE = k.stations.reduce((s, row) => s + row.cE, 0) / n;
  const v = 0.5 * (cA ** 2 + cE ** 2);
  const uC = Math.min(uBar, 0.999);
  const { wait, ct, uFactor } = kingmanCt(uC, tE, cA, cE);
  return {
    uBar,
    tE,
    cA,
    cE,
    v,
    uFactor,
    wait,
    ct,
    bottleneckU: k.bottleneckU,
  };
}

/** Sample CT(u) curve for teaching chart (gabungan t_e, c_a, c_e). */
export function kingmanCurvePoints(
  result: ParadeResult,
  nPoints = 60,
): { u: number; ct: number }[] {
  const comb = kingmanCombined(result);
  const pts: { u: number; ct: number }[] = [];
  for (let i = 0; i < nPoints; i++) {
    const u = 0.02 + (0.96 - 0.02) * (i / Math.max(nPoints - 1, 1));
    const { ct } = kingmanCt(u, comb.tE, comb.cA, comb.cE);
    if (Number.isFinite(ct)) pts.push({ u, ct });
  }
  return pts;
}
