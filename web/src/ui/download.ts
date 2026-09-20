/**
 * Browser downloads — CSV (opens in Excel) + PNG chart capture.
 */

import {
  bufferSeries,
  computeCostMetrics,
  cumulativeSeries,
  type CostMetrics,
  type ParadeResult,
} from "../core";
import { shortTradeName } from "../theme";

function escapeCsvCell(v: string | number | null | undefined): string {
  if (v == null) return "";
  const s = String(v);
  if (/[",\n\r]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
  return s;
}

export function rowsToCsv(rows: (string | number | null | undefined)[][]): string {
  return rows.map((r) => r.map(escapeCsvCell).join(",")).join("\n");
}

export function downloadText(
  filename: string,
  text: string,
  mime = "text/csv;charset=utf-8",
): void {
  // BOM helps Excel open UTF-8 correctly
  const bom = mime.includes("csv") ? "\uFEFF" : "";
  const blob = new Blob([bom + text], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function downloadCsv(
  filename: string,
  rows: (string | number | null | undefined)[][],
): void {
  downloadText(filename.endsWith(".csv") ? filename : `${filename}.csv`, rowsToCsv(rows));
}

export function downloadCanvasPng(
  canvas: HTMLCanvasElement,
  filename: string,
): void {
  const name = filename.endsWith(".png") ? filename : `${filename}.png`;
  const url = canvas.toDataURL("image/png");
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
}

export function resultSummaryRows(
  result: ParadeResult,
  rates?: number[],
): (string | number)[][] {
  const cm: CostMetrics | null = rates
    ? computeCostMetrics(result, rates)
    : null;
  const header = [
    "Tim",
    "Nama",
    "Mulai",
    "Selesai",
    "Time_on_site",
    "Produksi",
    "Kap_efektif",
    "Idle_kap",
    "Utilisasi",
    "Tarif",
    "Biaya_aktif",
    "Biaya_idle",
    "Biaya_total",
  ];
  const rows: (string | number)[][] = [header];
  for (let i = 0; i < result.tradeMetrics.length; i++) {
    const m = result.tradeMetrics[i];
    const t = cm?.trades[i];
    rows.push([
      `T${i + 1}`,
      shortTradeName(m.name),
      m.startPeriod ?? "",
      m.periodsToFinish,
      m.timeOnSite,
      m.totalProduction,
      m.totalEffectiveCapacity,
      m.totalIdle,
      Number((m.utilization * 100).toFixed(2)),
      t?.costPerPeriod ?? "",
      t ? Math.round(t.costActive) : "",
      t ? Math.round(t.costIdle) : "",
      t ? Math.round(t.costTotal) : "",
    ]);
  }
  rows.push([]);
  rows.push(["Durasi", result.duration]);
  rows.push(["Ideal", result.idealDuration]);
  rows.push(["Throughput", Number(result.systemThroughput.toFixed(6))]);
  rows.push(["Total_inventory_time", result.totalInventoryTime]);
  rows.push(["Total_time_on_site", result.totalTimeOnSite]);
  rows.push(["Batch", result.config.batchSize]);
  rows.push(["Zona", result.config.totalUnits]);
  rows.push(["Seed", result.config.seed ?? ""]);
  if (cm) {
    rows.push(["Biaya_aktif_total", Math.round(cm.totalActive)]);
    rows.push(["Biaya_idle_total", Math.round(cm.totalIdle)]);
    rows.push(["Biaya_total", Math.round(cm.totalCost)]);
  }
  return rows;
}

export function resultHistoryRows(result: ParadeResult): (string | number)[][] {
  const n = result.config.trades.length;
  const header = [
    "Periode",
    ...Array.from({ length: n }, (_, i) => `Prod_T${i + 1}`),
    ...Array.from({ length: n }, (_, i) => `Cum_T${i + 1}`),
    ...Array.from({ length: Math.max(0, n - 1) }, (_, j) => `WIP_B${j + 1}`),
  ];
  const rows: (string | number)[][] = [header];
  // t=0 baseline
  rows.push([
    0,
    ...Array(n).fill(0),
    ...Array(n).fill(0),
    ...Array(Math.max(0, n - 1)).fill(0),
  ]);
  for (const rec of result.history) {
    rows.push([
      rec.period,
      ...rec.production,
      ...rec.cumulative.map((v) => v | 0),
      ...rec.buffers,
    ]);
  }
  return rows;
}

export function compareSummaryRows(
  items: { name: string; result: ParadeResult }[],
  rates: number[],
  meta?: { variability?: string; batch?: number }[],
): (string | number)[][] {
  const header = [
    "Skenario",
    "Variability",
    "Batch",
    "Durasi",
    "Ideal",
    "Peak_WIP",
    "TH",
    "Biaya_aktif",
    "Biaya_idle",
    "Biaya_total",
    "TOS",
    "INV",
  ];
  const rows: (string | number)[][] = [header];
  items.forEach((it, i) => {
    const r = it.result;
    const cm = computeCostMetrics(r, rates);
    const buf = bufferSeries(r);
    let peak = 0;
    if (buf.length) {
      for (let t = 0; t < buf[0].length; t++) {
        const s = buf.reduce((a, series) => a + series[t], 0);
        if (s > peak) peak = s;
      }
    }
    rows.push([
      it.name,
      meta?.[i]?.variability ?? "",
      meta?.[i]?.batch ?? r.config.batchSize,
      r.duration,
      r.idealDuration,
      peak,
      Number(r.systemThroughput.toFixed(6)),
      Math.round(cm.totalActive),
      Math.round(cm.totalIdle),
      Math.round(cm.totalCost),
      r.totalTimeOnSite,
      r.totalInventoryTime,
    ]);
  });
  return rows;
}

/** Simple multi-section “workbook” as one CSV Excel can open. */
export function resultWorkbookCsv(
  result: ParadeResult,
  rates: number[],
): string {
  const parts: string[] = [];
  parts.push("### RINGKASAN");
  parts.push(rowsToCsv(resultSummaryRows(result, rates)));
  parts.push("");
  parts.push("### RIWAYAT");
  parts.push(rowsToCsv(resultHistoryRows(result)));
  parts.push("");
  parts.push("### KUMULATIF (LoB)");
  const cum = cumulativeSeries(result);
  const n = result.config.trades.length;
  const lobHeader = [
    "Periode",
    ...Array.from({ length: n }, (_, i) => `T${i + 1}_${shortTradeName(result.config.trades[i].name)}`),
    "Ideal_T_akhir",
  ];
  const lobRows: (string | number)[][] = [lobHeader];
  const ideal = result.idealLastTradeCumulative;
  const len = Math.max(...cum.map((s) => s.length), ideal.length);
  for (let t = 0; t < len; t++) {
    lobRows.push([
      t,
      ...cum.map((s) => s[t] ?? ""),
      ideal[t] ?? "",
    ]);
  }
  parts.push(rowsToCsv(lobRows));
  return parts.join("\n");
}
