/**
 * Comparison charts — overlay / grouped views for multi-scenario runs.
 */

import {
  bufferSeries,
  computeCostMetrics,
  cumulativeSeries,
  inventoryFillRateMetrics,
  littlesLawMetrics,
  type ParadeResult,
} from "../core";
import { IDEAL_COLOR, scenarioColor, shortTradeName } from "../theme";

export type NamedResult = { name: string; result: ParadeResult };

function prepCanvas(
  canvas: HTMLCanvasElement,
  cssH: number,
): { ctx: CanvasRenderingContext2D; cssW: number; cssH: number } | null {
  const dpr = window.devicePixelRatio || 1;
  const cssW = canvas.clientWidth || 640;
  canvas.width = Math.floor(cssW * dpr);
  canvas.height = Math.floor(cssH * dpr);
  canvas.style.height = `${cssH}px`;
  const ctx = canvas.getContext("2d");
  if (!ctx) return null;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, cssW, cssH);
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, cssW, cssH);
  return { ctx, cssW, cssH };
}

export function drawCompareLob(
  canvas: HTMLCanvasElement,
  items: NamedResult[],
  opts?: { cssHeight?: number },
): void {
  const prep = prepCanvas(canvas, opts?.cssHeight ?? 340);
  if (!prep || !items.length) return;
  const { ctx, cssW, cssH } = prep;
  const pad = { l: 48, r: 18, t: 28, b: 48 };
  const plotW = cssW - pad.l - pad.r;
  const plotH = cssH - pad.t - pad.b;
  const total = Math.max(...items.map((i) => i.result.config.totalUnits));
  const first = items[0].result;
  const ideal = first.idealLastTradeCumulative;
  let maxX = Math.max(first.duration, ideal.length - 1, 1);
  for (const it of items) maxX = Math.max(maxX, it.result.duration);

  const xScale = (x: number) => pad.l + (x / Math.max(maxX, 1)) * plotW;
  const yScale = (y: number) => pad.t + plotH - (y / Math.max(total, 1)) * plotH;

  ctx.font = "11px DM Sans, sans-serif";
  ctx.fillStyle = "#64748b";
  ctx.textAlign = "center";
  ctx.textBaseline = "bottom";
  ctx.fillText("Line of Balance — tim terakhir per skenario", pad.l + plotW / 2, pad.t - 8);

  for (let z = 0; z <= total; z++) {
    const yy = yScale(z);
    ctx.strokeStyle = z === 0 || z === total ? "rgba(26,54,93,0.25)" : "rgba(26,54,93,0.08)";
    ctx.beginPath();
    ctx.moveTo(pad.l, yy);
    ctx.lineTo(pad.l + plotW, yy);
    ctx.stroke();
  }

  if (ideal.length > 1) {
    ctx.strokeStyle = IDEAL_COLOR;
    ctx.setLineDash([5, 4]);
    ctx.lineWidth = 1.6;
    ctx.beginPath();
    ideal.forEach((y, i) => {
      const X = xScale(i);
      const Y = yScale(y);
      if (i === 0) ctx.moveTo(X, Y);
      else ctx.lineTo(X, Y);
    });
    ctx.stroke();
    ctx.setLineDash([]);
  }

  items.forEach((it, idx) => {
    const cum = cumulativeSeries(it.result);
    let series = [...cum[cum.length - 1]];
    if (!series.length || series[0] !== 0) series = [0, ...series];
    const color = scenarioColor(idx);
    ctx.strokeStyle = color;
    ctx.lineWidth = 2.2;
    ctx.beginPath();
    series.forEach((y, i) => {
      const X = xScale(i);
      const Y = yScale(y);
      if (i === 0) ctx.moveTo(X, Y);
      else ctx.lineTo(X, Y);
    });
    ctx.stroke();
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(xScale(0), yScale(0), 3.5, 0, Math.PI * 2);
    ctx.fill();
  });

  ctx.fillStyle = "#1a365d";
  ctx.font = "12px DM Sans, sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "bottom";
  ctx.fillText("Periode", pad.l + plotW / 2, cssH - 4);
}

export function drawCompareBuffers(
  canvas: HTMLCanvasElement,
  items: NamedResult[],
  opts?: { cssHeight?: number },
): void {
  const prep = prepCanvas(canvas, opts?.cssHeight ?? 320);
  if (!prep || !items.length) return;
  const { ctx, cssW, cssH } = prep;
  const pad = { l: 48, r: 18, t: 28, b: 48 };
  const plotW = cssW - pad.l - pad.r;
  const plotH = cssH - pad.t - pad.b;

  const totals = items.map((it) => {
    const buf = bufferSeries(it.result);
    if (!buf.length) return [0];
    return buf[0].map((_, t) => buf.reduce((s, row) => s + row[t], 0));
  });
  const maxX = Math.max(...totals.map((t) => t.length - 1), 1);
  const maxY = Math.max(1, ...totals.flat());
  const xScale = (x: number) => pad.l + (x / maxX) * plotW;
  const yScale = (y: number) => pad.t + plotH - (y / maxY) * plotH;

  ctx.font = "11px DM Sans, sans-serif";
  ctx.fillStyle = "#64748b";
  ctx.textAlign = "center";
  ctx.textBaseline = "bottom";
  ctx.fillText("Σ WIP buffer vs waktu — per skenario", pad.l + plotW / 2, pad.t - 8);

  totals.forEach((series, idx) => {
    const color = scenarioColor(idx);
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.beginPath();
    series.forEach((y, i) => {
      const X = xScale(i);
      const Y = yScale(y);
      if (i === 0) ctx.moveTo(X, Y);
      else ctx.lineTo(X, Y);
    });
    ctx.stroke();
  });

  ctx.fillStyle = "#1a365d";
  ctx.font = "12px DM Sans, sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "bottom";
  ctx.fillText("Periode", pad.l + plotW / 2, cssH - 4);
}

export function drawCompareUtil(
  canvas: HTMLCanvasElement,
  items: NamedResult[],
  opts?: { cssHeight?: number },
): void {
  const prep = prepCanvas(canvas, opts?.cssHeight ?? 300);
  if (!prep || !items.length) return;
  const { ctx, cssW, cssH } = prep;
  const nTrades = items[0].result.tradeMetrics.length;
  const pad = { l: 120, r: 18, t: 28, b: 40 };
  const plotW = cssW - pad.l - pad.r;
  const plotH = cssH - pad.t - pad.b;
  const groupH = plotH / nTrades;
  const barH = Math.min(14, (groupH * 0.7) / items.length);

  ctx.font = "11px DM Sans, sans-serif";
  ctx.fillStyle = "#64748b";
  ctx.textAlign = "center";
  ctx.textBaseline = "bottom";
  ctx.fillText("Utilisasi per tim — perbandingan skenario", pad.l + plotW / 2, pad.t - 8);

  for (let t = 0; t < nTrades; t++) {
    const y0 = pad.t + groupH * t + groupH / 2;
    ctx.fillStyle = "#1a202c";
    ctx.textAlign = "right";
    ctx.textBaseline = "middle";
    ctx.font = "11px DM Sans, sans-serif";
    const name = items[0].result.tradeMetrics[t].name;
    ctx.fillText(`T${t + 1}: ${shortTradeName(name, 10)}`, pad.l - 8, y0);

    items.forEach((it, idx) => {
      const util = Math.max(0, Math.min(1, it.result.tradeMetrics[t].utilization)) * 100;
      const y = y0 - (items.length * barH) / 2 + idx * barH;
      ctx.fillStyle = scenarioColor(idx);
      ctx.fillRect(pad.l, y, (util / 100) * plotW, Math.max(barH - 1, 2));
    });
  }

  ctx.strokeStyle = "rgba(26,54,93,0.3)";
  ctx.setLineDash([4, 4]);
  ctx.beginPath();
  ctx.moveTo(pad.l + plotW, pad.t);
  ctx.lineTo(pad.l + plotW, pad.t + plotH);
  ctx.stroke();
  ctx.setLineDash([]);
}

export function drawCompareCosts(
  canvas: HTMLCanvasElement,
  items: NamedResult[],
  rates: number[],
  opts?: { cssHeight?: number },
): void {
  const prep = prepCanvas(canvas, opts?.cssHeight ?? 280);
  if (!prep || !items.length) return;
  const { ctx, cssW, cssH } = prep;
  const pad = { l: 48, r: 18, t: 28, b: 56 };
  const plotW = cssW - pad.l - pad.r;
  const plotH = cssH - pad.t - pad.b;
  const costs = items.map((it) => computeCostMetrics(it.result, rates));
  const maxY = Math.max(1, ...costs.map((c) => c.totalCost));
  const groupW = plotW / items.length;
  const barW = groupW * 0.28;

  ctx.font = "11px DM Sans, sans-serif";
  ctx.fillStyle = "#64748b";
  ctx.textAlign = "center";
  ctx.textBaseline = "bottom";
  ctx.fillText("Biaya aktif vs idle (stacked = total)", pad.l + plotW / 2, pad.t - 8);

  const yScale = (y: number) => pad.t + plotH - (y / maxY) * plotH;

  costs.forEach((cm, idx) => {
    const cx = pad.l + groupW * idx + groupW / 2;
    const yIdle = yScale(cm.totalIdle);
    const yTotal = yScale(cm.totalCost);
    ctx.fillStyle = "#f59e0b";
    ctx.fillRect(cx - barW, yIdle, barW * 2, pad.t + plotH - yIdle);
    ctx.fillStyle = "#2563eb";
    ctx.fillRect(cx - barW, yTotal, barW * 2, yIdle - yTotal);
    ctx.fillStyle = "#64748b";
    ctx.font = "10px DM Sans, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    ctx.fillText(`S${idx + 1}`, cx, pad.t + plotH + 8);
  });

  ctx.fillStyle = "#2563eb";
  ctx.fillRect(pad.l, cssH - 14, 10, 3);
  ctx.fillStyle = "#1a365d";
  ctx.font = "10px DM Sans, sans-serif";
  ctx.textAlign = "left";
  ctx.fillText("Aktif", pad.l + 14, cssH - 16);
  ctx.fillStyle = "#f59e0b";
  ctx.fillRect(pad.l + 55, cssH - 14, 10, 3);
  ctx.fillStyle = "#1a365d";
  ctx.fillText("Idle", pad.l + 69, cssH - 16);
}

export function drawCompareMetricsBars(
  canvas: HTMLCanvasElement,
  items: NamedResult[],
  kind: "duration" | "th" | "cost" | "fr",
  rates: number[],
  opts?: { cssHeight?: number },
): void {
  const prep = prepCanvas(canvas, opts?.cssHeight ?? 240);
  if (!prep || !items.length) return;
  const { ctx, cssW, cssH } = prep;
  const pad = { l: 48, r: 18, t: 28, b: 48 };
  const plotW = cssW - pad.l - pad.r;
  const plotH = cssH - pad.t - pad.b;

  const values = items.map((it) => {
    if (kind === "duration") return it.result.duration;
    if (kind === "th") return littlesLawMetrics(it.result).throughput;
    if (kind === "cost") return computeCostMetrics(it.result, rates).totalCost;
    return 100 * inventoryFillRateMetrics(it.result).fillRateSystem;
  });
  const titles = {
    duration: "Durasi proyek",
    th: "Throughput (TH)",
    cost: "Total biaya",
    fr: "Fill rate sistem (%)",
  };
  const maxY = Math.max(1e-6, ...values);
  const groupW = plotW / items.length;
  const barW = groupW * 0.45;
  const yScale = (y: number) => pad.t + plotH - (y / maxY) * plotH;

  ctx.font = "11px DM Sans, sans-serif";
  ctx.fillStyle = "#64748b";
  ctx.textAlign = "center";
  ctx.textBaseline = "bottom";
  ctx.fillText(titles[kind], pad.l + plotW / 2, pad.t - 8);

  values.forEach((v, idx) => {
    const cx = pad.l + groupW * idx + groupW / 2;
    const y = yScale(v);
    ctx.fillStyle = scenarioColor(idx);
    ctx.fillRect(cx - barW / 2, y, barW, pad.t + plotH - y);
    ctx.fillStyle = "#1a365d";
    ctx.font = "10px DM Sans, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "bottom";
    ctx.fillText(
      kind === "th" ? v.toFixed(3) : kind === "fr" ? v.toFixed(1) : String(Math.round(v)),
      cx,
      y - 4,
    );
    ctx.textBaseline = "top";
    ctx.fillStyle = "#64748b";
    ctx.fillText(`S${idx + 1}`, cx, pad.t + plotH + 8);
  });
}

export function buildCompareLegend(items: NamedResult[]): { color: string; text: string }[] {
  return items.map((it, i) => ({
    color: scenarioColor(i),
    text: `${it.name} · T=${it.result.duration} · batch=${it.result.config.batchSize}`,
  }));
}
