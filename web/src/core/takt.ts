/**
 * Little's Takt Law + ideal OPF wagon plan (port of parade_of_trades_analysis).
 */

export interface TaktPlanCell {
  tradeIndex: number;
  zone: number; // 1-based
  periodStart: number;
  periodEnd: number;
  plannedRate: number;
}

export interface TaktPlan {
  nTrades: number;
  nZones: number;
  batchSize: number;
  rate: number;
  cells: TaktPlanCell[];
  duration: number;
  taktTime: number;
  handoffLag: number;
}

/** TD = (TW + TZ − 1) × TT */
export function littlesTaktDuration(
  nWagons: number,
  nZones: number,
  taktTime: number,
): number {
  return (
    (Math.max(1, Math.trunc(nWagons)) + Math.max(1, Math.trunc(nZones)) - 1) *
    Math.max(taktTime, 1e-12)
  );
}

/**
 * Ideal one-piece-flow takt train.
 * When totalWork is set, TT scales so scope stays fixed.
 */
export function buildTaktPlan(opts: {
  nTrades?: number;
  nZones?: number;
  batchSize?: number;
  rate?: number;
  handoffLag?: number;
  totalWork?: number | null;
}): TaktPlan {
  const nTrades = Math.max(1, Math.trunc(opts.nTrades ?? 5));
  const nZones = Math.max(1, Math.trunc(opts.nZones ?? 20));
  const rateIn = Math.max(opts.rate ?? 1, 1e-9);
  void opts.handoffLag;
  void opts.batchSize;

  let tt: number;
  let zoneRate: number;
  if (opts.totalWork != null) {
    const W = Math.max(opts.totalWork, 1e-9);
    tt = (1 / rateIn) * (W / nZones);
    zoneRate = (rateIn * nZones) / W;
  } else {
    tt = 1 / rateIn;
    zoneRate = rateIn;
  }

  const cells: TaktPlanCell[] = [];
  for (let i = 0; i < nTrades; i++) {
    for (let z = 0; z < nZones; z++) {
      const ps = (i + z) * tt;
      const pe = ps + tt;
      cells.push({
        tradeIndex: i,
        zone: z + 1,
        periodStart: ps,
        periodEnd: pe,
        plannedRate: zoneRate,
      });
    }
  }

  const td = littlesTaktDuration(nTrades, nZones, tt);
  return {
    nTrades,
    nZones,
    batchSize: 1,
    rate: zoneRate,
    cells,
    duration: Math.round(td * 1e6) / 1e6,
    taktTime: tt,
    handoffLag: 1,
  };
}

/** Classroom floor constants (app.py tab_takt). */
export const TAKT_FLOOR = {
  bayM: 3,
  bayArea: 9,
  areaFloor: 360,
  nBay: 40,
  tw: 5,
  capDefault: 4,
} as const;

export function taktTzOptions(nBay = TAKT_FLOOR.nBay): number[] {
  return [1, 5, 10, 20, 40].filter((d) => nBay % d === 0);
}

export function computeTaktClassroom(opts: {
  tz: number;
  capBayPerDay: number;
  tPerFloor: number;
  nFloors?: number;
}): {
  baysPerZone: number;
  areaPerZone: number;
  capZone: number;
  te: number;
  t0: number;
  tdFloor: number;
  rate: number;
  ok: boolean;
  plan: TaktPlan;
} {
  const tz = Math.max(1, Math.trunc(opts.tz));
  const baysPerZone = TAKT_FLOOR.nBay / tz;
  const areaPerZone = TAKT_FLOOR.areaFloor / tz;
  const capZone = opts.capBayPerDay / Math.max(baysPerZone, 1e-9);
  const te = 1 / Math.max(capZone, 1e-9);
  const t0 = tz * te;
  const tdFloor = littlesTaktDuration(TAKT_FLOOR.tw, tz, te);
  const plan = buildTaktPlan({
    nTrades: TAKT_FLOOR.tw,
    nZones: tz,
    batchSize: 1,
    rate: capZone,
    handoffLag: 1,
    totalWork: null,
  });
  return {
    baysPerZone,
    areaPerZone,
    capZone,
    te,
    t0,
    tdFloor,
    rate: capZone,
    ok: tdFloor <= opts.tPerFloor + 1e-9,
    plan,
  };
}
