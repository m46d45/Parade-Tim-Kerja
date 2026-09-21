/**
 * Cost metrics — port of parade_of_trades_analysis.compute_cost_metrics.
 * Biaya = (periode aktif + periode idle) × tarif, per tim, window start…finish.
 */

import type { ParadeResult } from "./types";

export interface TradeCostRow {
  tradeIndex: number;
  name: string;
  costPerPeriod: number;
  periodsActive: number;
  periodsIdle: number;
  costActive: number;
  costIdle: number;
  costTotal: number;
  startPeriod: number | null;
  finishPeriod: number | null;
}

export interface CostMetrics {
  trades: TradeCostRow[];
  totalActive: number;
  totalIdle: number;
  totalCost: number;
}

export function computeCostMetrics(
  result: ParadeResult,
  costPerPeriod: number[],
): CostMetrics {
  const n = result.config.trades.length;
  const rates = [...costPerPeriod];
  while (rates.length < n) {
    rates.push(rates.length ? rates[rates.length - 1] : 100);
  }
  const clipped = rates.slice(0, n).map((r) => Math.max(0, Number(r) || 0));

  const prodMap = new Map<number, number[]>();
  for (const rec of result.history) {
    prodMap.set(rec.period, rec.production.map((x) => x | 0));
  }

  const rows: TradeCostRow[] = [];
  for (let i = 0; i < n; i++) {
    const m = result.tradeMetrics[i];
    const startP = m.startPeriod;
    const finP = m.periodsToFinish ? (m.periodsToFinish | 0) : null;
    if (startP == null || finP == null) {
      rows.push({
        tradeIndex: i,
        name: m.name,
        costPerPeriod: clipped[i],
        periodsActive: 0,
        periodsIdle: 0,
        costActive: 0,
        costIdle: 0,
        costTotal: 0,
        startPeriod: startP,
        finishPeriod: finP,
      });
      continue;
    }

    let start = startP | 0;
    let fin = finP | 0;
    if (fin < start) fin = start;

    let nActive = 0;
    let nIdle = 0;
    for (let p = start; p <= fin; p++) {
      const row = prodMap.get(p);
      const prod = row && i < row.length ? row[i] : 0;
      if (prod > 0) nActive += 1;
      else nIdle += 1;
    }

    const tos = fin - start + 1;
    if (nActive + nIdle !== tos) {
      nIdle = Math.max(0, tos - nActive);
    }

    const ca = nActive * clipped[i];
    const ci = nIdle * clipped[i];
    rows.push({
      tradeIndex: i,
      name: m.name,
      costPerPeriod: clipped[i],
      periodsActive: nActive,
      periodsIdle: nIdle,
      costActive: ca,
      costIdle: ci,
      costTotal: ca + ci,
      startPeriod: start,
      finishPeriod: fin,
    });
  }

  const ta = rows.reduce((s, r) => s + r.costActive, 0);
  const ti = rows.reduce((s, r) => s + r.costIdle, 0);
  return { trades: rows, totalActive: ta, totalIdle: ti, totalCost: ta + ti };
}
