/**
 * Time–inventory buffer (Iris-style) — port of parade_of_trades_core + plots fits.
 */

import { makeParadeConfig, makeTrade } from "./config";
import { runParade } from "./simulate";
import { DEFAULT_TRADE_NAMES, type ParadeResult } from "./types";

export const BUFFER_VAR_PRESETS = ["no_variability", "low", "medium"] as const;
export type BufferVarPreset = (typeof BUFFER_VAR_PRESETS)[number];

export const BUFFER_VAR_FACTORS: Record<BufferVarPreset, [number, number]> = {
  no_variability: [1, 1],
  low: [0.75, 1.25],
  medium: [0.5, 1.5],
};

export const BUFFER_VAR_ALIASES: Record<string, BufferVarPreset> = {
  "5-5": "no_variability",
  tanpa: "no_variability",
  no_variability: "no_variability",
  "4-6": "low",
  sedang: "low",
  low: "low",
  "3-7": "medium",
  tinggi: "medium",
  medium: "medium",
};

export const IRIS_MOBILIZATION: Record<string, number[]> = {
  "0-1-2-3-4": [0, 1, 2, 3, 4],
  "0-2-4-6-8": [0, 2, 4, 6, 8],
  "0-3-6-9-12": [0, 3, 6, 9, 12],
};

export const IRIS_SLIDE_MOBS = [
  "0-1-2-3-4",
  "0-1-2-3-5",
  "0-1-2-4-5",
  "0-1-3-4-5",
  "0-2-3-4-5",
  "0-1-2-3-6",
  "0-1-2-4-6",
  "0-1-2-5-6",
  "0-1-3-4-6",
  "0-1-3-5-6",
  "0-1-4-5-6",
  "0-2-3-4-6",
  "0-2-3-5-6",
  "0-2-4-5-6",
  "0-3-4-5-6",
  "0-2-4-6-8",
  "0-3-6-9-12",
] as const;

export const BUF_VAR_LABEL: Record<string, string> = {
  no_variability: "Tanpa variability",
  low: "Sedang (±25%)",
  medium: "Tinggi (±50%)",
};

export const BUF_VAR_SHORT: Record<string, string> = {
  no_variability: "Tanpa var",
  low: "Sedang",
  medium: "Tinggi",
};

export const MOB_SHORT: Record<string, string> = {
  "0-1-2-3-4": "rapat",
  "0-2-4-6-8": "tengah",
  "0-3-6-9-12": "longgar",
};

export function parseMobilization(
  mobilization: string,
  nTrades = 5,
): number[] {
  let offs: number[];
  if (mobilization in IRIS_MOBILIZATION) {
    offs = [...IRIS_MOBILIZATION[mobilization]];
  } else {
    offs = String(mobilization)
      .split("-")
      .filter((x) => x !== "")
      .map((x) => Number.parseInt(x, 10));
  }
  if (nTrades !== offs.length) {
    if (nTrades !== 5) {
      const step = offs.length > 1 ? offs[1] - offs[0] : 1;
      offs = Array.from({ length: nTrades }, (_, i) => i * step);
    } else {
      throw new Error(
        `mobilization '${mobilization}' has ${offs.length} starts`,
      );
    }
  }
  return offs;
}

export function runTimeInventoryBuffer(opts: {
  die?: string;
  mobilization?: string;
  totalUnits?: number;
  seed?: number | null;
  nTrades?: number;
  baseSpeed?: number;
}): ParadeResult {
  const die = opts.die ?? "no_variability";
  const varKey = BUFFER_VAR_ALIASES[die] ?? (die as BufferVarPreset);
  if (!(varKey in BUFFER_VAR_FACTORS)) {
    throw new Error(
      `Unknown variability '${die}'. Use ${BUFFER_VAR_PRESETS.join(", ")}`,
    );
  }
  const nTrades = opts.nTrades ?? 5;
  const offs = parseMobilization(opts.mobilization ?? "0-1-2-3-4", nTrades);
  const [fLo, fHi] = BUFFER_VAR_FACTORS[varKey];
  const b = opts.baseSpeed ?? 1;
  const lo = Math.max(1e-9, b * fLo);
  const hi = Math.max(1e-9, b * fHi);
  const det = Math.abs(fLo - fHi) < 1e-12;
  const names = DEFAULT_TRADE_NAMES.slice(0, nTrades);
  const trades = Array.from({ length: nTrades }, (_, i) =>
    makeTrade({
      name: names[i] ?? `Tim ${i + 1}`,
      low: lo,
      high: hi,
      pHigh: 0.5,
      baseSpeed: b,
      deterministic: det,
    }),
  );
  const cfg = makeParadeConfig({
    trades,
    totalUnits: opts.totalUnits ?? 10,
    seed: opts.seed ?? 42,
    samePeriodHandoff: false,
    mobilizationOffsets: offs,
    zoneFlow: true,
    batchSize: 1,
  });
  return runParade(cfg);
}

export interface BufferSweepRow {
  die: string;
  mobilization: string;
  label: string;
  duration: number;
  time_on_site: number;
  inventory_time: number;
  anchor: boolean;
  tos_floor: number;
  n_reps: number;
}

export function irisBufferSweep(opts: {
  totalUnits?: number;
  seed?: number | null;
  dense?: boolean;
  nTrades?: number;
  nReps?: number;
}): BufferSweepRow[] {
  const keys = opts.dense
    ? [...IRIS_SLIDE_MOBS]
    : Object.keys(IRIS_MOBILIZATION);
  const base = opts.seed == null ? 0 : Math.trunc(opts.seed);
  const nTrades = opts.nTrades ?? 5;
  const totalUnits = opts.totalUnits ?? 10;
  const nReps = Math.max(1, Math.trunc(opts.nReps ?? 12));
  const rows: BufferSweepRow[] = [];

  for (const varKey of BUFFER_VAR_PRESETS) {
    for (const mob of keys) {
      const ds: number[] = [];
      const ts: number[] = [];
      const invs: number[] = [];
      for (let i = 0; i < nReps; i++) {
        const r = runTimeInventoryBuffer({
          die: varKey,
          mobilization: mob,
          totalUnits,
          seed: base + i,
          nTrades,
        });
        ds.push(r.duration);
        ts.push(r.totalTimeOnSite);
        invs.push(r.totalInventoryTime);
      }
      const n = ds.length;
      rows.push({
        die: varKey,
        mobilization: mob,
        label: `${varKey} ${mob}`,
        duration: ds.reduce((a, b) => a + b, 0) / n,
        time_on_site: ts.reduce((a, b) => a + b, 0) / n,
        inventory_time: invs.reduce((a, b) => a + b, 0) / n,
        anchor: mob in IRIS_MOBILIZATION,
        tos_floor: nTrades * totalUnits,
        n_reps: n,
      });
    }
  }
  return rows;
}

export function irisMobilizationGrid(maxGap = 3): Record<string, number[]> {
  const out: Record<string, number[]> = {};
  const vals = Array.from({ length: maxGap }, (_, i) => i + 1);
  function product(depth: number, cur: number[]): void {
    if (depth === 4) {
      const offs = [0];
      for (const g of cur) offs.push(offs[offs.length - 1] + g);
      out[offs.join("-")] = offs;
      return;
    }
    for (const v of vals) product(depth + 1, [...cur, v]);
  }
  product(0, []);
  return out;
}

/* —— curve fits (simplified numpy-free port) —— */

const TOS_FLOOR = 100;

export type BufferFit = {
  die: string;
  metric?: string;
  model: string;
  kind: string;
  coef: number[];
  eq: string;
  r2: number;
  aic: number;
  k: number;
  x_mean: number[];
  y_mean: number[];
  tos_floor?: number;
  vertical?: boolean;
  tos0?: number;
  inv_min?: number;
  inv_max?: number;
};

function binMeans(xs: number[], ys: number[]): [number[], number[]] {
  const buckets = new Map<number, number[]>();
  for (let i = 0; i < xs.length; i++) {
    const x = xs[i];
    const arr = buckets.get(x) ?? [];
    arr.push(ys[i]);
    buckets.set(x, arr);
  }
  const mx = [...buckets.keys()].sort((a, b) => a - b);
  const my = mx.map((x) => {
    const arr = buckets.get(x)!;
    return arr.reduce((a, b) => a + b, 0) / arr.length;
  });
  return [mx, my];
}

function mean(arr: number[]): number {
  return arr.reduce((a, b) => a + b, 0) / Math.max(1, arr.length);
}

function std(arr: number[]): number {
  if (arr.length < 2) return 0;
  const m = mean(arr);
  return Math.sqrt(mean(arr.map((v) => (v - m) ** 2)));
}

function r2Aic(y: number[], yhat: number[], k: number): [number, number] {
  const n = Math.max(1, y.length);
  const m = mean(y);
  let ssRes = 0;
  let ssTot = 0;
  for (let i = 0; i < y.length; i++) {
    ssRes += (y[i] - yhat[i]) ** 2;
    ssTot += (y[i] - m) ** 2;
  }
  const r2 = ssTot < 1e-12 ? 1 : 1 - ssRes / ssTot;
  const aic = n * Math.log(Math.max(ssRes, 1e-18) / n) + 2 * k;
  return [r2, aic];
}

function packFit(
  name: string,
  kind: string,
  coef: number[],
  y: number[],
  yhat: number[],
  mx: number[],
  my: number[],
  eq: string,
  extra?: Record<string, unknown>,
): BufferFit {
  const [r2, aic] = r2Aic(y, yhat, Math.max(1, coef.length));
  return {
    die: "",
    model: name,
    kind,
    coef: coef.map(Number),
    eq,
    r2,
    aic,
    k: coef.length,
    x_mean: [...mx],
    y_mean: [...my],
    ...(extra as object),
  };
}

function polyEquation(coef: number[], yname: string, xname = "D"): string {
  // coef is [slope, intercept] for degree 1 (numpy polyfit order high→low for polyval)
  // We store as [slope, intercept] matching _fit_inv_linear's [slope, intercept] then polyval
  // Actually Python: coef = [slope, intercept] then np.polyval(coef, x) expects highest degree first
  // so polyval([slope, intercept], x) = slope*x + intercept. Good.
  const c = coef.map(Number);
  const n = c.length - 1;
  const parts: string[] = [];
  for (let i = 0; i < c.length; i++) {
    const v = c[i];
    const p = n - i;
    if (Math.abs(v) < 5e-5) continue;
    const av = Math.abs(v);
    let term: string;
    if (p === 0) term = av.toFixed(3);
    else if (p === 1)
      term = Math.abs(av - 1) > 0.02 ? `${av.toFixed(4)}${xname}` : xname;
    else if (p === 2) term = `${av.toFixed(5)}${xname}²`;
    else term = `${av.toFixed(5)}${xname}^${p}`;
    if (!parts.length) parts.push(v < 0 ? `−${term}` : term);
    else parts.push((v < 0 ? " − " : " + ") + term);
  }
  if (!parts.length) parts.push("0");
  return `${yname} = ${parts.join("")}`;
}

function polyval(coef: number[], x: number): number {
  // highest degree first
  let y = 0;
  for (const c of coef) y = y * x + c;
  return y;
}

function inferTosFloor(rows: BufferSweepRow[]): number {
  for (const r of rows) {
    if (r.tos_floor) return r.tos_floor;
  }
  const stables = rows
    .filter((r) =>
      ["no_variability", "5-5", "tanpa"].includes(String(r.die)),
    )
    .map((r) => r.time_on_site);
  if (stables.length) return Math.min(...stables);
  return TOS_FLOOR;
}

function fitTosTheory(
  mx: number[],
  my: number[],
  tosFloor: number,
): BufferFit {
  const floor = tosFloor;
  const excess = my.map((y) => y - floor);
  const invx = mx.map((x) => 1 / Math.max(x, 1e-9));
  const denom = invx.reduce((a, b) => a + b * b, 0) || 1;
  const B = Math.max(
    0,
    invx.reduce((a, xi, i) => a + xi * excess[i], 0) / denom,
  );
  const yhatInv = mx.map((x) => floor + B / Math.max(x, 1e-9));
  const cands: BufferFit[] = [
    packFit(
      `Invers ke ${floor}`,
      "floor_inv",
      [B],
      my,
      yhatInv,
      mx,
      my,
      `TOS = ${floor} + ${B.toFixed(3)}/D`,
      { tos_floor: floor },
    ),
  ];

  let bestSse: number | null = null;
  let best: { A: number; lam: number; yhat: number[] } | null = null;
  for (let i = 0; i < 90; i++) {
    const lam = 0.015 + ((0.55 - 0.015) * i) / 89;
    const z = mx.map((x) => Math.exp(-lam * x));
    const zz = z.reduce((a, b) => a + b * b, 0) || 1;
    const A = Math.max(
      0,
      z.reduce((a, zi, j) => a + zi * excess[j], 0) / zz,
    );
    const yhat = mx.map((x) => floor + A * Math.exp(-lam * x));
    const sse = my.reduce((a, yi, j) => a + (yi - yhat[j]) ** 2, 0);
    if (bestSse == null || sse < bestSse) {
      bestSse = sse;
      best = { A, lam, yhat };
    }
  }
  if (best) {
    cands.push(
      packFit(
        `Exp ke ${floor}`,
        "floor_exp",
        [best.A, best.lam],
        my,
        best.yhat,
        mx,
        my,
        `TOS = ${floor} + ${best.A.toFixed(3)}·e^(-${best.lam.toFixed(4)} D)`,
        { tos_floor: floor },
      ),
    );
  }
  cands.sort((a, b) => b.r2 - a.r2 || a.aic - b.aic);
  return cands[0];
}

function fitInvLinear(mx: number[], my: number[]): BufferFit {
  const n = mx.length;
  const mxm = mean(mx);
  const mym = mean(my);
  let num = 0;
  let den = 0;
  for (let i = 0; i < n; i++) {
    num += (mx[i] - mxm) * (my[i] - mym);
    den += (mx[i] - mxm) ** 2;
  }
  let slope = den < 1e-18 ? 0 : num / den;
  let intercept = mym - slope * mxm;
  if (slope < 0) {
    slope = 0;
    intercept = mym;
  }
  const coef = [slope, intercept];
  const yhat = mx.map((x) => polyval(coef, x));
  return packFit(
    "Linier (teori tunda)",
    "poly",
    coef,
    my,
    yhat,
    mx,
    my,
    polyEquation(coef, "INV", "D"),
  );
}

export function fitBufferTrends(rows: BufferSweepRow[]): BufferFit[] {
  const byDie = new Map<string, BufferSweepRow[]>();
  for (const row of rows) {
    const arr = byDie.get(row.die) ?? [];
    arr.push(row);
    byDie.set(row.die, arr);
  }
  const floor = inferTosFloor(rows);
  const out: BufferFit[] = [];
  for (const [die, group] of byDie) {
    const xs = group.map((r) => r.duration);
    const tos = group.map((r) => r.time_on_site);
    const inv = group.map((r) => r.inventory_time);
    const [mxT, myT] = binMeans(xs, tos);
    const [mxI, myI] = binMeans(xs, inv);

    let fitT: BufferFit;
    if (
      ["no_variability", "5-5", "tanpa"].includes(die) ||
      std(myT) < 1e-6
    ) {
      const yhat = mxT.map(() => floor);
      fitT = packFit(
        "Lantai proses",
        "const",
        [floor],
        myT,
        yhat,
        mxT,
        myT,
        `TOS = ${floor}`,
        { tos_floor: floor },
      );
    } else {
      fitT = fitTosTheory(mxT, myT, floor);
    }
    fitT.die = die;
    fitT.metric = "time_on_site";
    out.push(fitT);

    const fitI = fitInvLinear(mxI, myI);
    fitI.die = die;
    fitI.metric = "inventory_time";
    fitI.tos_floor = floor;
    out.push(fitI);
  }
  return out;
}

export function fitInvVsTos(rows: BufferSweepRow[]): BufferFit[] {
  const byDie = new Map<string, BufferSweepRow[]>();
  for (const row of rows) {
    const arr = byDie.get(row.die) ?? [];
    arr.push(row);
    byDie.set(row.die, arr);
  }
  const floor = inferTosFloor(rows);
  const out: BufferFit[] = [];
  for (const [die, group] of byDie) {
    const tos = group.map((r) => r.time_on_site);
    const inv = group.map((r) => r.inventory_time);
    const [mx, my] = binMeans(tos, inv);
    if (
      ["no_variability", "5-5", "tanpa"].includes(die) ||
      std(mx) < 1e-6
    ) {
      out.push({
        ...packFit(
          "Vertikal",
          "const",
          [floor],
          my,
          my.map(() => floor),
          mx,
          my,
          `TOS = ${floor}  (vertikal; INV mengikuti tunda)`,
          { tos_floor: floor },
        ),
        die,
        vertical: true,
        tos0: floor,
        inv_min: Math.min(...inv),
        inv_max: Math.max(...inv),
        model: "Vertikal",
        r2: 1,
      });
      continue;
    }
    const z = mx.map((x) => 1 / Math.max(x - floor, 0.35));
    // least squares [1, z] → y : a + b*z
    let s1 = 0;
    let sz = 0;
    let szz = 0;
    let sy = 0;
    let szy = 0;
    const n = mx.length;
    for (let i = 0; i < n; i++) {
      s1 += 1;
      sz += z[i];
      szz += z[i] * z[i];
      sy += my[i];
      szy += z[i] * my[i];
    }
    const det = s1 * szz - sz * sz;
    let a = 0;
    let b = 0;
    if (Math.abs(det) > 1e-18) {
      a = (sy * szz - sz * szy) / det;
      b = (s1 * szy - sz * sy) / det;
    }
    if (b < 0) {
      b = 0;
      a = mean(my);
    }
    const yhat = z.map((zi) => a + b * zi);
    const fit = packFit(
      "Hiperbola (I vs T)",
      "hyp_tos",
      [a, b],
      my,
      yhat,
      mx,
      my,
      `INV = ${a.toFixed(1)} + ${b.toFixed(1)}/(TOS − ${floor})`,
      { tos_floor: floor },
    );
    fit.die = die;
    fit.vertical = false;
    out.push(fit);
  }
  return out;
}

export function predictBufferCurve(fit: BufferFit, xs: number[]): number[] {
  const kind = fit.kind;
  const c = fit.coef;
  const floor = fit.tos_floor ?? TOS_FLOOR;
  return xs.map((x) => {
    if (kind === "poly") return polyval(c, x);
    if (kind === "const") return c.length ? c[0] : floor;
    if (kind === "floor_inv") return floor + c[0] / Math.max(x, 1e-9);
    if (kind === "floor_exp")
      return floor + c[0] * Math.exp(-c[1] * x);
    if (kind === "hyp_tos")
      return c[0] + c[1] / Math.max(x - floor, 1e-3);
    return mean(fit.y_mean.length ? fit.y_mean : [0]);
  });
}
