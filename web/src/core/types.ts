/** Shared types — aligned with parade_of_trades_core.py (zone-flow path). */

export interface TradeConfig {
  name: string;
  low: number;
  high: number;
  pHigh: number;
  baseSpeed: number;
  deterministic: boolean;
}

export interface ParadeConfig {
  trades: TradeConfig[];
  totalUnits: number;
  seed: number | null;
  taktRate: number | null;
  standbyCapacity: number;
  samePeriodHandoff: boolean;
  staggeredMobilization: boolean;
  mobilizationOffsets: number[] | null;
  zoneFlow: boolean;
  batchSize: number;
}

export interface PeriodRecord {
  period: number;
  capacity: number[];
  production: number[];
  idleCapacity: number[];
  cumulative: number[];
  buffers: number[];
  rawRemaining: number;
  effectiveCapacity: number[];
  standbyUsed: number[];
  fractionalCumulative: number[];
}

export interface TradeMetrics {
  name: string;
  meanCapacity: number;
  totalProduction: number;
  totalIdle: number;
  totalEffectiveCapacity: number;
  utilization: number;
  periodsToFinish: number;
  timeOnSite: number;
  startPeriod: number | null;
}

export interface ParadeResult {
  config: ParadeConfig;
  duration: number;
  history: PeriodRecord[];
  tradeMetrics: TradeMetrics[];
  maxBuffer: number[];
  totalIdleCapacity: number;
  systemThroughput: number;
  idealDuration: number;
  idealLastTradeCumulative: number[];
  /** Σ_t Σ_interfaces WIP(t) — Iris inventory time. */
  totalInventoryTime: number;
  /** Σ_trades time_on_site. */
  totalTimeOnSite: number;
}

export const DEFAULT_TRADE_NAMES = [
  "Bekisting",
  "Tulangan",
  "Cor",
  "Bongkar",
  "Finishing",
] as const;
