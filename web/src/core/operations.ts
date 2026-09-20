/**
 * Little's Law operations curve + CONWIP evaluate — port of
 * littles_operations_curve / evaluate_at_wip.
 */

import { kingmanCombined, kingmanCt } from "./kingman";
import { littlesLawMetrics } from "./littles";
import { tradeMean } from "./config";
import type { ParadeResult } from "./types";

export interface LittlesOperationsCurve {
  wip: number[];
  th: number[];
  ct: number[];
  u: number[];
  opWip: number;
  opTh: number;
  opCt: number;
  tE: number;
  v: number;
  uBar: number;
  bcWip: number[];
  bcTh: number[];
  bcCt: number[];
  thMax: number;
  t0: number;
  w0: number;
  wMin: number;
  wOpt: number;
  wPwc: number;
  vFactor: number;
  conwip: number;
}

export interface EvaluateAtWip {
  wip: number;
  th: number;
  ct: number;
  thBest: number;
  ctBest: number;
  opWip: number;
  opTh: number;
  opCt: number;
  dTh: number;
  dCt: number;
  dWip: number;
  wMin: number;
  wOpt: number;
  thMax: number;
}

function interpXy(xs: number[], ys: number[], x: number): number {
  if (!xs.length) return Number.NaN;
  if (x <= xs[0]) return ys[0];
  if (x >= xs[xs.length - 1]) return ys[ys.length - 1];
  for (let i = 1; i < xs.length; i++) {
    if (x <= xs[i]) {
      const x0 = xs[i - 1];
      const x1 = xs[i];
      const y0 = ys[i - 1];
      const y1 = ys[i];
      if (Math.abs(x1 - x0) < 1e-15) return y0;
      const t = (x - x0) / (x1 - x0);
      return y0 + t * (y1 - y0);
    }
  }
  return ys[ys.length - 1];
}

export function littlesOperationsCurve(
  result: ParadeResult,
  nPoints = 80,
): LittlesOperationsCurve {
  const comb = kingmanCombined(result);
  const tEAvg = Math.max(comb.tE, 1e-9);
  const cA = comb.cA;
  const cE = comb.cE;

  const means: number[] = [];
  let t0 = 0;
  for (const tr of result.config.trades) {
    const meanC = Math.max(tradeMean(tr) || tr.baseSpeed || 1, 1e-9);
    means.push(meanC);
    t0 += 1 / Math.max(meanC, 1e-9);
  }
  const thMax = means.length ? Math.min(...means) : 1;
  t0 = Math.max(t0, 1e-9);
  const w0 = thMax * t0;

  const ll = littlesLawMetrics(result);
  const VEarly = Math.max(comb.v || 0, 0);
  const alphaTmp = 0.9;
  let wOptEst = w0;
  if (VEarly >= 1e-9) {
    wOptEst = alphaTmp * w0 * (1 + VEarly * (alphaTmp / (1 - alphaTmp)));
    wOptEst = Math.max(wOptEst, w0);
  }

  const wHi = Math.max(w0, wOptEst, ll.avgPipelineWip, 1) + 5;
  const wGrid = Array.from({ length: nPoints }, (_, i) =>
    Math.max((wHi * i) / Math.max(nPoints - 1, 1), 1e-6),
  );

  const bcTh: number[] = [];
  const bcCt: number[] = [];
  for (const w of wGrid) {
    if (w <= w0 + 1e-12) {
      bcTh.push(w / t0);
      bcCt.push(t0);
    } else {
      bcTh.push(thMax);
      bcCt.push(w / thMax);
    }
  }

  let wips: number[] = [];
  let ths: number[] = [];
  let cts: number[] = [];
  let us: number[] = [];
  const nU = Math.max(nPoints, 120);
  for (let i = 0; i < nU; i++) {
    const u = 0.02 + ((0.985 - 0.02) * i) / Math.max(nU - 1, 1);
    const { ct } = kingmanCt(u, tEAvg, cA, cE);
    if (!Number.isFinite(ct) || ct <= 0) continue;
    const th = Math.min(u / tEAvg, thMax * 0.999);
    if (th <= 1e-12) continue;
    us.push(u);
    ths.push(th);
    cts.push(ct);
    wips.push(th * ct);
  }

  if (wips.length) {
    const order = wips.map((_, i) => i).sort((a, b) => wips[a] - wips[b]);
    wips = order.map((i) => wips[i]);
    ths = order.map((i) => ths[i]);
    cts = order.map((i) => cts[i]);
    us = order.map((i) => us[i]);
    const wLast = wips[wips.length - 1];
    const thSat = ths[ths.length - 1];
    const thCeil = Math.min(
      thMax * (VEarly > 1e-9 ? 0.92 : 0.999),
      Math.max(thSat, thMax * 0.5),
    );
    if (wLast < wHi - 1e-6) {
      const nExt = Math.max(20, Math.floor(nPoints / 2));
      for (let j = 1; j <= nExt; j++) {
        const w = wLast + ((wHi - wLast) * j) / nExt;
        const frac = j / nExt;
        let th = thSat + (thCeil - thSat) * (1 - Math.exp(-3 * frac));
        th = Math.min(th, thMax * 0.999);
        wips.push(w);
        ths.push(th);
        cts.push(w / th);
        us.push(us[us.length - 1] ?? 0.9);
      }
    }
  }

  const wMin = w0;
  const V = Math.max(comb.v || 0, 0);
  const alpha = 0.9;
  let wOpt = wMin;
  if (V >= 1e-9) {
    const inflation = 1 + V * (alpha / (1 - alpha));
    wOpt = Math.max(alpha * wMin * inflation, wMin);
  }

  const alphaHi = 0.95;
  let wPwc = wMin;
  if (V >= 1e-9) {
    const inflHi = 1 + V * (alphaHi / (1 - alphaHi));
    wPwc = Math.max(wOpt, alphaHi * wMin * inflHi);
  }

  return {
    wip: wips,
    th: ths,
    ct: cts,
    u: us,
    opWip: ll.avgPipelineWip,
    opTh: ll.throughput,
    opCt: ll.cycleTimePipeline,
    tE: tEAvg,
    v: comb.v,
    uBar: comb.uBar,
    bcWip: wGrid,
    bcTh,
    bcCt,
    thMax,
    t0,
    w0,
    wMin,
    wOpt,
    wPwc,
    vFactor: V,
    conwip: wOpt,
  };
}

export function evaluateAtWip(
  result: ParadeResult,
  wipLevel: number,
): EvaluateAtWip {
  const d = littlesOperationsCurve(result);
  const w = Math.max(wipLevel, 1e-9);

  let aw = [...d.wip];
  let ath = [...d.th];
  let act = [...d.ct];
  if (aw.length) {
    const order = aw.map((_, i) => i).sort((a, b) => aw[a] - aw[b]);
    aw = order.map((i) => aw[i]);
    ath = order.map((i) => ath[i]);
    act = order.map((i) => act[i]);
  }
  let thA = aw.length ? interpXy(aw, ath, w) : Number.NaN;
  let ctA = aw.length ? interpXy(aw, act, w) : Number.NaN;
  if (Number.isFinite(thA) && thA > 1e-12 && (!Number.isFinite(ctA) || ctA <= 0)) {
    ctA = w / thA;
  }
  if (Number.isFinite(ctA) && ctA > 1e-12 && (!Number.isFinite(thA) || thA <= 0)) {
    thA = w / ctA;
  }

  const thB = d.bcWip.length ? interpXy(d.bcWip, d.bcTh, w) : Number.NaN;
  const ctB = d.bcWip.length ? interpXy(d.bcWip, d.bcCt, w) : Number.NaN;

  return {
    wip: w,
    th: thA,
    ct: ctA,
    thBest: thB,
    ctBest: ctB,
    opWip: d.opWip,
    opTh: d.opTh,
    opCt: d.opCt,
    dTh: thA - d.opTh,
    dCt: ctA - d.opCt,
    dWip: w - d.opWip,
    wMin: d.wMin,
    wOpt: d.wOpt,
    thMax: d.thMax,
  };
}
