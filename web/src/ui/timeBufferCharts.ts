/** Time–inventory buffer charts (Pareto + INV vs TOS). */

import {
  BUF_VAR_SHORT,
  MOB_SHORT,
  fitBufferTrends,
  fitInvVsTos,
  predictBufferCurve,
  type BufferFit,
  type BufferSweepRow,
} from "../core";
import { niceStep } from "./chartAxis";

const DIE_STYLE: Record<string, { color: string; marker: string; label: string }> = {
  no_variability: { color: "#2563eb", marker: "s", label: "Waktu di lapangan · tanpa var" },
  low: { color: "#06b6d4", marker: "o", label: "Waktu di lapangan · sedang" },
  medium: { color: "#7c3aed", marker: "D", label: "Waktu di lapangan · tinggi" },
};

const DIE_INV: Record<string, { color: string; marker: string; label: string }> = {
  no_variability: { color: "#f59e0b", marker: "s", label: "Inventory time · tanpa var" },
  low: { color: "#ea580c", marker: "o", label: "Inventory time · sedang" },
  medium: { color: "#dc2626", marker: "D", label: "Inventory time · tinggi" },
};

const IRIS_PAIR: Record<string, { color: string; marker: string; label: string }> = {
  no_variability: { color: "#16a34a", marker: "s", label: "Tanpa var" },
  low: { color: "#ca8a04", marker: "o", label: "Sedang" },
  medium: { color: "#dc2626", marker: "D", label: "Tinggi" },
};

function drawMarker(
  ctx: CanvasRenderingContext2D,
  kind: string,
  x: number,
  y: number,
  color: string,
  size: number,
): void {
  ctx.fillStyle = color;
  ctx.strokeStyle = "#ffffff";
  ctx.lineWidth = 1;
  ctx.beginPath();
  if (kind === "s") ctx.rect(x - size, y - size, size * 2, size * 2);
  else if (kind === "D") {
    ctx.moveTo(x, y - size);
    ctx.lineTo(x + size, y);
    ctx.lineTo(x, y + size);
    ctx.lineTo(x - size, y);
    ctx.closePath();
  } else ctx.arc(x, y, size, 0, Math.PI * 2);
  ctx.fill();
  ctx.stroke();
}

function setup(
  canvas: HTMLCanvasElement,
  h = 340,
): {
  ctx: CanvasRenderingContext2D;
  cssW: number;
  cssH: number;
  pad: { l: number; r: number; t: number; b: number };
} | null {
  const dpr = Math.max(1, window.devicePixelRatio || 1);
  const cssW = Math.max(320, canvas.clientWidth || 720);
  const cssH = h;
  canvas.width = Math.round(cssW * dpr);
  canvas.height = Math.round(cssH * dpr);
  canvas.style.height = `${cssH}px`;
  const ctx = canvas.getContext("2d");
  if (!ctx) return null;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, cssW, cssH);
  ctx.fillStyle = "#fff";
  ctx.fillRect(0, 0, cssW, cssH);
  return { ctx, cssW, cssH, pad: { l: 58, r: 58, t: 28, b: 48 } };
}

function linspace(a: number, b: number, n: number): number[] {
  if (n <= 1) return [a];
  return Array.from({ length: n }, (_, i) => a + ((b - a) * i) / (n - 1));
}

export function drawTimeInventoryPareto(
  canvas: HTMLCanvasElement,
  rows: BufferSweepRow[],
  highlight?: string | null,
): void {
  const s = setup(canvas, 360);
  if (!s) return;
  const { ctx, cssW, cssH, pad } = s;
  const plotW = cssW - pad.l - pad.r;
  const plotH = cssH - pad.t - pad.b;

  const byDie = new Map<string, BufferSweepRow[]>();
  for (const r of rows) {
    const arr = byDie.get(r.die) ?? [];
    arr.push(r);
    byDie.set(r.die, arr);
  }
  const fits = fitBufferTrends(rows);
  const fitMap = new Map(fits.map((f) => [`${f.die}|${f.metric}`, f]));

  const allX = rows.map((r) => r.duration);
  const allTos = rows.map((r) => r.time_on_site);
  const allInv = rows.map((r) => r.inventory_time);
  const xmin = Math.min(...allX);
  const xmax = Math.max(...allX);
  const tmin = Math.min(...allTos);
  const tmax = Math.max(...allTos);
  const imin = Math.min(...allInv);
  const imax = Math.max(...allInv);
  const x0 = xmin - 0.05 * (xmax - xmin || 1);
  const x1 = xmax + 0.35 * (xmax - xmin || 1);
  const t0 = tmin - 0.08 * (tmax - tmin || 1);
  const t1 = tmax + 0.08 * (tmax - tmin || 1);
  const i0 = imin - 0.08 * (imax - imin || 1);
  const i1 = imax + 0.08 * (imax - imin || 1);

  const xScale = (x: number) => pad.l + ((x - x0) / (x1 - x0)) * plotW;
  const yT = (y: number) => pad.t + plotH - ((y - t0) / (t1 - t0)) * plotH;
  const yI = (y: number) => pad.t + plotH - ((y - i0) / (i1 - i0)) * plotH;

  // X ticks (Durasi)
  const xStep = niceStep(x1 - x0);
  for (let v = Math.ceil(x0 / xStep) * xStep; v <= x1 + 1e-9; v += xStep) {
    const xx = xScale(v);
    ctx.strokeStyle = "rgba(100,116,139,0.12)";
    ctx.beginPath();
    ctx.moveTo(xx, pad.t);
    ctx.lineTo(xx, pad.t + plotH);
    ctx.stroke();
    ctx.fillStyle = "#475569";
    ctx.font = "10px DM Sans, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    ctx.fillText(String(Math.round(v)), xx, pad.t + plotH + 6);
  }
  // Left Y ticks (TOS)
  const tStep = niceStep(t1 - t0);
  for (let v = Math.ceil(t0 / tStep) * tStep; v <= t1 + 1e-9; v += tStep) {
    const yy = yT(v);
    ctx.strokeStyle = "rgba(100,116,139,0.12)";
    ctx.beginPath();
    ctx.moveTo(pad.l, yy);
    ctx.lineTo(pad.l + plotW, yy);
    ctx.stroke();
    ctx.fillStyle = "#1d4ed8";
    ctx.font = "10px DM Sans, sans-serif";
    ctx.textAlign = "right";
    ctx.textBaseline = "middle";
    ctx.fillText(String(Math.round(v)), pad.l - 8, yy);
  }
  // Right Y ticks (INV)
  const iStep = niceStep(i1 - i0);
  for (let v = Math.ceil(i0 / iStep) * iStep; v <= i1 + 1e-9; v += iStep) {
    const yy = yI(v);
    ctx.fillStyle = "#c2410c";
    ctx.font = "10px DM Sans, sans-serif";
    ctx.textAlign = "left";
    ctx.textBaseline = "middle";
    ctx.fillText(String(Math.round(v)), pad.l + plotW + 8, yy);
  }
  ctx.strokeStyle = "rgba(26,54,93,0.35)";
  ctx.beginPath();
  ctx.moveTo(pad.l, pad.t);
  ctx.lineTo(pad.l, pad.t + plotH);
  ctx.lineTo(pad.l + plotW, pad.t + plotH);
  ctx.stroke();

  const order = ["no_variability", "low", "medium"].filter((d) => byDie.has(d));
  const plottedT = new Set<string>();
  const plottedI = new Set<string>();

  for (const die of order) {
    const group = byDie.get(die)!;
    const stl = DIE_STYLE[die];
    const invs = DIE_INV[die];
    const fitT = fitMap.get(`${die}|time_on_site`);
    const fitI = fitMap.get(`${die}|inventory_time`);

    if (fitT) {
      const xs = linspace(
        Math.min(...fitT.x_mean),
        Math.max(...fitT.x_mean) + 0.35 * (Math.max(...fitT.x_mean) - Math.min(...fitT.x_mean) || 2),
        80,
      );
      const ys = predictBufferCurve(fitT, xs);
      ctx.strokeStyle = stl.color;
      ctx.lineWidth = 1.8;
      ctx.setLineDash([6, 4]);
      ctx.beginPath();
      xs.forEach((x, i) => {
        const px = xScale(x);
        const py = yT(ys[i]);
        if (i === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      });
      ctx.stroke();
      ctx.setLineDash([]);
      plottedT.add(die);
    }
    if (fitI) {
      const xs = linspace(Math.min(...fitI.x_mean), Math.max(...fitI.x_mean), 60);
      const ys = predictBufferCurve(fitI, xs);
      ctx.strokeStyle = invs.color;
      ctx.lineWidth = 1.8;
      ctx.setLineDash([6, 4]);
      ctx.beginPath();
      xs.forEach((x, i) => {
        const px = xScale(x);
        const py = yI(ys[i]);
        if (i === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      });
      ctx.stroke();
      ctx.setLineDash([]);
      plottedI.add(die);
    }

    for (const r of group) {
      const isAnchor =
        r.anchor || (highlight != null && r.label === highlight);
      const size = isAnchor ? 6.5 : 3.5;
      drawMarker(ctx, stl.marker, xScale(r.duration), yT(r.time_on_site), stl.color, size);
      drawMarker(ctx, invs.marker, xScale(r.duration), yI(r.inventory_time), invs.color, size);
      if (isAnchor) {
        const short = MOB_SHORT[r.mobilization] ?? "";
        if (short) {
          ctx.fillStyle = stl.color;
          ctx.font = "600 11px DM Sans, system-ui, sans-serif";
          ctx.textAlign = "left";
          ctx.textBaseline = "bottom";
          ctx.fillText(short, xScale(r.duration) + 6, yT(r.time_on_site) - 4);
        }
      }
    }
  }

  ctx.fillStyle = "#1d4ed8";
  ctx.font = "11px DM Sans, system-ui, sans-serif";
  ctx.textAlign = "center";
  ctx.fillText("Durasi D (periode)", pad.l + plotW / 2, cssH - 4);
  ctx.save();
  ctx.translate(14, pad.t + plotH / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText("Waktu di lapangan TOS (periode·tim)", 0, 0);
  ctx.restore();
  ctx.fillStyle = "#c2410c";
  ctx.save();
  ctx.translate(cssW - 12, pad.t + plotH / 2);
  ctx.rotate(Math.PI / 2);
  ctx.fillText("Inventory time INV (zona·periode)", 0, 0);
  ctx.restore();

  // legend
  let lx = pad.l;
  const ly = 10;
  ctx.font = "10px DM Sans, system-ui, sans-serif";
  ctx.textAlign = "left";
  ctx.textBaseline = "middle";
  for (const die of order) {
    if (!plottedT.has(die)) continue;
    const stl = DIE_STYLE[die];
    ctx.strokeStyle = stl.color;
    ctx.beginPath();
    ctx.moveTo(lx, ly);
    ctx.lineTo(lx + 14, ly);
    ctx.stroke();
    ctx.fillStyle = stl.color;
    ctx.fillText(BUF_VAR_SHORT[die] ?? die, lx + 18, ly);
    lx += 90;
  }
  void plottedI;
}

export function drawInventoryVsTos(
  canvas: HTMLCanvasElement,
  rows: BufferSweepRow[],
  highlight?: string | null,
): void {
  const s = setup(canvas, 340);
  if (!s) return;
  const { ctx, cssW, cssH, pad } = s;
  pad.r = 18;
  const plotW = cssW - pad.l - pad.r;
  const plotH = cssH - pad.t - pad.b;

  const byDie = new Map<string, BufferSweepRow[]>();
  for (const r of rows) {
    const arr = byDie.get(r.die) ?? [];
    arr.push(r);
    byDie.set(r.die, arr);
  }
  const fits = fitInvVsTos(rows);
  const fitMap = new Map(fits.map((f) => [f.die, f]));

  const allX = rows.map((r) => r.time_on_site);
  const allY = rows.map((r) => r.inventory_time);
  const xmin = Math.min(...allX);
  const xmax = Math.max(...allX);
  const ymin = Math.min(...allY);
  const ymax = Math.max(...allY);
  const x0 = xmin - 0.08 * (xmax - xmin || 1);
  const x1 = xmax + 0.08 * (xmax - xmin || 1);
  const y0 = ymin - 0.08 * (ymax - ymin || 1);
  const y1 = ymax + 0.08 * (ymax - ymin || 1);
  const xScale = (x: number) => pad.l + ((x - x0) / (x1 - x0)) * plotW;
  const yScale = (y: number) => pad.t + plotH - ((y - y0) / (y1 - y0)) * plotH;

  const xStep = niceStep(x1 - x0);
  for (let v = Math.ceil(x0 / xStep) * xStep; v <= x1 + 1e-9; v += xStep) {
    const xx = xScale(v);
    ctx.strokeStyle = "rgba(100,116,139,0.12)";
    ctx.beginPath();
    ctx.moveTo(xx, pad.t);
    ctx.lineTo(xx, pad.t + plotH);
    ctx.stroke();
    ctx.fillStyle = "#475569";
    ctx.font = "10px DM Sans, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    ctx.fillText(String(Math.round(v)), xx, pad.t + plotH + 6);
  }
  const yStep = niceStep(y1 - y0);
  for (let v = Math.ceil(y0 / yStep) * yStep; v <= y1 + 1e-9; v += yStep) {
    const yy = yScale(v);
    ctx.strokeStyle = "rgba(100,116,139,0.12)";
    ctx.beginPath();
    ctx.moveTo(pad.l, yy);
    ctx.lineTo(pad.l + plotW, yy);
    ctx.stroke();
    ctx.fillStyle = "#475569";
    ctx.font = "10px DM Sans, sans-serif";
    ctx.textAlign = "right";
    ctx.textBaseline = "middle";
    ctx.fillText(String(Math.round(v)), pad.l - 8, yy);
  }
  ctx.strokeStyle = "rgba(26,54,93,0.35)";
  ctx.beginPath();
  ctx.moveTo(pad.l, pad.t);
  ctx.lineTo(pad.l, pad.t + plotH);
  ctx.lineTo(pad.l + plotW, pad.t + plotH);
  ctx.stroke();

  const order = ["no_variability", "low", "medium"].filter((d) => byDie.has(d));
  for (const die of order) {
    const group = byDie.get(die)!;
    const stl = IRIS_PAIR[die];
    const fit = fitMap.get(die) as BufferFit | undefined;

    if (fit?.vertical) {
      ctx.strokeStyle = stl.color;
      ctx.lineWidth = 2;
      ctx.setLineDash([6, 4]);
      ctx.beginPath();
      ctx.moveTo(xScale(fit.tos0 ?? 0), yScale(fit.inv_min ?? 0));
      ctx.lineTo(xScale(fit.tos0 ?? 0), yScale(fit.inv_max ?? 0));
      ctx.stroke();
      ctx.setLineDash([]);
    } else if (fit && !fit.vertical) {
      const xs = linspace(Math.min(...fit.x_mean), Math.max(...fit.x_mean), 80);
      const ys = predictBufferCurve(fit, xs);
      ctx.strokeStyle = stl.color;
      ctx.lineWidth = 2;
      ctx.setLineDash([6, 4]);
      ctx.beginPath();
      xs.forEach((x, i) => {
        const px = xScale(x);
        const py = yScale(ys[i]);
        if (i === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      });
      ctx.stroke();
      ctx.setLineDash([]);
    }

    for (const r of group) {
      const isAnchor =
        r.anchor || (highlight != null && r.label === highlight);
      drawMarker(
        ctx,
        stl.marker,
        xScale(r.time_on_site),
        yScale(r.inventory_time),
        stl.color,
        isAnchor ? 7 : 2.5,
      );
      if (isAnchor) {
        const short = MOB_SHORT[r.mobilization] ?? "";
        if (short) {
          ctx.fillStyle = stl.color;
          ctx.font = "600 11px DM Sans, system-ui, sans-serif";
          ctx.textAlign = "left";
          ctx.fillText(
            short,
            xScale(r.time_on_site) + 8,
            yScale(r.inventory_time) - 4,
          );
        }
      }
    }
  }

  ctx.fillStyle = "#1a202c";
  ctx.font = "600 12px DM Sans, system-ui, sans-serif";
  ctx.textAlign = "left";
  ctx.fillText("Inventory time vs waktu di lapangan", pad.l, 10);
  ctx.fillStyle = "#64748b";
  ctx.font = "11px DM Sans, system-ui, sans-serif";
  ctx.textAlign = "center";
  ctx.fillText("Waktu di lapangan TOS (periode·tim)", pad.l + plotW / 2, cssH - 4);
  ctx.save();
  ctx.translate(14, pad.t + plotH / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.fillStyle = "#1a365d";
  ctx.fillText("Inventory time INV (zona·periode)", 0, 0);
  ctx.restore();
}
