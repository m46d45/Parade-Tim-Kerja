import {
  DEFAULT_TRADE_NAMES,
  type ParadeConfig,
  type TradeConfig,
} from "./types";

export function makeTrade(opts: {
  name: string;
  low: number;
  high: number;
  pHigh?: number;
  baseSpeed?: number | null;
  deterministic?: boolean;
}): TradeConfig {
  const low = opts.low;
  const high = opts.high;
  if (low < 0 || high < 0) throw new Error(`Capacity must be non-negative: ${opts.name}`);
  if (low > high) throw new Error(`low (${low}) must be <= high (${high}) for ${opts.name}`);
  const pHigh = opts.pHigh ?? 0.5;
  let baseSpeed: number;
  if (opts.baseSpeed == null) {
    baseSpeed =
      low === high ? low : (1 - pHigh) * low + pHigh * high;
  } else {
    baseSpeed = opts.baseSpeed;
  }
  if (baseSpeed < 0) throw new Error(`base_speed must be non-negative: ${opts.name}`);
  return {
    name: opts.name,
    low,
    high,
    pHigh,
    baseSpeed,
    deterministic: opts.deterministic ?? false,
  };
}

export function tradeMean(t: TradeConfig): number {
  if (t.low === t.high) return t.low;
  return (1 - t.pHigh) * t.low + t.pHigh * t.high;
}

export function makeParadeConfig(opts: {
  trades: TradeConfig[];
  totalUnits: number;
  seed?: number | null;
  taktRate?: number | null;
  standbyCapacity?: number;
  samePeriodHandoff?: boolean;
  staggeredMobilization?: boolean;
  mobilizationOffsets?: number[] | null;
  zoneFlow?: boolean;
  batchSize?: number;
}): ParadeConfig {
  if (!opts.trades.length) throw new Error("At least one trade is required");
  if (opts.totalUnits <= 0) throw new Error("total_units must be positive");
  const batchSize = opts.batchSize ?? 1;
  if (batchSize < 1) throw new Error("batch_size must be >= 1");
  return {
    trades: opts.trades,
    totalUnits: opts.totalUnits,
    seed: opts.seed ?? null,
    taktRate: opts.taktRate ?? null,
    standbyCapacity: opts.standbyCapacity ?? 0,
    samePeriodHandoff: opts.samePeriodHandoff ?? false,
    staggeredMobilization: opts.staggeredMobilization ?? false,
    mobilizationOffsets: opts.mobilizationOffsets ?? null,
    zoneFlow: opts.zoneFlow ?? false,
    batchSize,
  };
}

/** Classroom helper: 5 Indonesian floor-cycle trades, zone-flow. */
export type VariabilityLevel = "none" | "low" | "medium";

const VAR_FACTORS: Record<
  VariabilityLevel,
  { lo: number; hi: number; deterministic: boolean; label: string }
> = {
  none: { lo: 1, hi: 1, deterministic: true, label: "Tanpa variability" },
  low: { lo: 0.75, hi: 1.25, deterministic: false, label: "Sedang (±25%)" },
  medium: { lo: 0.5, hi: 1.5, deterministic: false, label: "Tinggi (±50%)" },
};

export function variabilityLabel(level: VariabilityLevel): string {
  return VAR_FACTORS[level].label;
}

export function classroomConfig(opts: {
  totalUnits?: number;
  batchSize?: number;
  baseSpeed?: number;
  seed?: number;
  deterministic?: boolean;
  low?: number;
  high?: number;
  variability?: VariabilityLevel;
}): ParadeConfig {
  const speed = opts.baseSpeed ?? 1;
  const level = opts.variability ?? (opts.deterministic === false ? "medium" : "none");
  const profile = VAR_FACTORS[level];
  const low = opts.low ?? speed * profile.lo;
  const high = opts.high ?? speed * profile.hi;
  const deterministic = opts.deterministic ?? profile.deterministic;
  const trades = DEFAULT_TRADE_NAMES.map((name) =>
    makeTrade({
      name,
      low,
      high,
      baseSpeed: speed,
      deterministic,
    }),
  );
  return makeParadeConfig({
    trades,
    totalUnits: opts.totalUnits ?? 10,
    seed: opts.seed ?? 12345,
    zoneFlow: true,
    batchSize: opts.batchSize ?? 4,
  });
}

export function buildIdealTwinConfig(config: ParadeConfig): ParadeConfig {
  const trades = config.trades.map((t) => {
    if (config.zoneFlow) {
      const speed = Math.max(t.baseSpeed || tradeMean(t), 1e-9);
      return makeTrade({
        name: t.name,
        low: speed,
        high: speed,
        baseSpeed: speed,
        deterministic: true,
      });
    }
    const m = Math.max(tradeMean(t), 1e-9);
    return makeTrade({
      name: t.name,
      low: m,
      high: m,
      baseSpeed: m,
      deterministic: true,
    });
  });
  return makeParadeConfig({
    trades,
    totalUnits: config.totalUnits,
    seed: 0,
    taktRate: config.taktRate,
    standbyCapacity: config.standbyCapacity,
    samePeriodHandoff: config.samePeriodHandoff,
    staggeredMobilization: config.staggeredMobilization,
    mobilizationOffsets: config.mobilizationOffsets,
    zoneFlow: config.zoneFlow,
    batchSize: config.batchSize,
  });
}

export function nInterfaces(config: ParadeConfig): number {
  return Math.max(0, config.trades.length - 1);
}
