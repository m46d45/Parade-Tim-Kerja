/**
 * Inventory / fill-rate — port of parade_of_trades_analysis.inventory_fill_rate_*.
 */

import { kingmanCombined } from "./kingman";
import { littlesLawMetrics } from "./littles";
import { bufferSeries } from "./simulate";
import { nInterfaces } from "./config";
import type { ParadeResult } from "./types";

export interface InventoryInterfaceRow {
  buffer: string;
  from: string;
  to: string;
  avgInventory: number;
  peakInventory: number;
  fillRate: number;
  downstreamIdle: number;
  downstreamProd: number;
}

export interface InventoryFillRateMetrics {
  interfaces: InventoryInterfaceRow[];
  avgInventorySystem: number;
  fillRateSystem: number;
  fillRateT1: number;
  peakBufferTotal: number;
}

export interface InventoryFillRateCurve {
  inventory: number[];
  fillRate: number[];
  opInventory: number;
  opFillRate: number;
  interfaces: InventoryInterfaceRow[];
  mu: number;
  sigma: number;
}

/** Unit normal loss G(z) = φ(z) − z(1−Φ(z)). */
export function unitNormalLoss(z: number): number {
  const phi = Math.exp(-0.5 * z * z) / Math.sqrt(2 * Math.PI);
  const t = 1 / (1 + 0.2316419 * Math.abs(z));
  const d = 0.3989423 * Math.exp(-0.5 * z * z);
  const p =
    d *
    t *
    (0.3193815 +
      t * (-0.3565638 + t * (1.781478 + t * (-1.821256 + t * 1.330274))));
  const Phi = z >= 0 ? 1 - p : p;
  return phi - z * (1 - Phi);
}

export function inventoryFillRateMetrics(
  result: ParadeResult,
): InventoryFillRateMetrics {
  const n = result.config.trades.length;
  const buf = bufferSeries(result);
  const nIf = nInterfaces(result.config);
  const interfaces: InventoryInterfaceRow[] = [];

  for (let j = 0; j < nIf; j++) {
    const series = buf[j] ?? [];
    const avgInventory = series.length
      ? series.reduce((a, b) => a + b, 0) / series.length
      : 0;
    const peakInventory = series.length ? Math.max(...series) : 0;
    const up = result.config.trades[j].name;
    const down = result.config.trades[j + 1].name;
    const m = result.tradeMetrics[j + 1];
    const denom = m.totalProduction + m.totalIdle;
    const fillRate = denom > 0 ? m.totalProduction / denom : 1;
    interfaces.push({
      buffer: `B${j + 1}`,
      from: up,
      to: down,
      avgInventory,
      peakInventory,
      fillRate,
      downstreamIdle: m.totalIdle,
      downstreamProd: m.totalProduction,
    });
  }

  const avgInventorySystem =
    interfaces.reduce((s, r) => s + r.avgInventory, 0) /
    Math.max(interfaces.length, 1);

  let prod = 0;
  let idle = 0;
  for (let i = 1; i < n; i++) {
    prod += result.tradeMetrics[i].totalProduction;
    idle += result.tradeMetrics[i].totalIdle;
  }
  const fillRateSystem = prod + idle > 0 ? prod / (prod + idle) : 1;

  const m1 = result.tradeMetrics[0];
  const d1 = m1.totalProduction + m1.totalIdle;
  const fillRateT1 = d1 > 0 ? m1.totalProduction / d1 : 1;

  let peakBufferTotal = 0;
  for (const rec of result.history) {
    const s = rec.buffers.reduce((a, b) => a + b, 0);
    if (s > peakBufferTotal) peakBufferTotal = s;
  }

  return {
    interfaces,
    avgInventorySystem,
    fillRateSystem,
    fillRateT1,
    peakBufferTotal,
  };
}

export function inventoryFillRateCurve(
  result: ParadeResult,
  nPoints = 60,
): InventoryFillRateCurve {
  const comb = kingmanCombined(result);
  const ll = littlesLawMetrics(result);
  const mu = Math.max(ll.throughput, 0.1);
  const ce = Math.max(comb.cE, 0.05);
  const sigma = Math.max(ce * mu, 0.05);

  const inventory: number[] = [];
  const fillRate: number[] = [];
  for (let i = 0; i < nPoints; i++) {
    const z = -0.5 + (3.2 - -0.5) * (i / Math.max(nPoints - 1, 1));
    const cycle = mu * comb.tE * 0.5;
    const safety = Math.max(z, 0) * sigma;
    const inv = cycle + safety;
    const G = unitNormalLoss(z);
    let fr = 1 - (sigma * G) / mu;
    fr = Math.max(0, Math.min(1, fr));
    inventory.push(Math.max(inv, 0));
    fillRate.push(fr);
  }

  const emp = inventoryFillRateMetrics(result);
  return {
    inventory,
    fillRate,
    opInventory: emp.avgInventorySystem,
    opFillRate: emp.fillRateSystem,
    interfaces: emp.interfaces,
    mu,
    sigma,
  };
}
