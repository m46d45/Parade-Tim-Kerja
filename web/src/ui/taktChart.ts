/** Takt wagon chart — port of plot_takt_wagon_chart. */

import type { TaktPlan } from "../core";
import { tradeColor } from "../theme";

export function drawTaktWagonChart(
  canvas: HTMLCanvasElement,
  plan: TaktPlan,
  title?: string,
): void {
  const dpr = Math.max(1, window.devicePixelRatio || 1);
  const nShow = plan.nZones;
  let tmax = 0;
  for (const c of plan.cells) {
    if (c.zone >= 1 && c.zone <= nShow) tmax = Math.max(tmax, c.periodEnd);
  }
  tmax = Math.max(tmax, plan.duration || 0, 1e-6);

  const cssW = Math.max(320, canvas.clientWidth || 640);
  const cssH = Math.max(
    220,
    Math.min(520, Math.round(0.16 * nShow * 28 + 120)),
  );
  canvas.width = Math.round(cssW * dpr);
  canvas.height = Math.round(cssH * dpr);
  canvas.style.height = `${cssH}px`;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

  const pad = { l: 44, r: 16, t: title ? 36 : 16, b: 40 };
  const plotW = cssW - pad.l - pad.r;
  const plotH = cssH - pad.t - pad.b;
  const xScale = (x: number) => pad.l + (x / tmax) * plotW;
  const yScale = (z: number) => pad.t + ((z - 0.5) / nShow) * plotH;
  const barH = (plotH / nShow) * 0.92;

  ctx.clearRect(0, 0, cssW, cssH);
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, cssW, cssH);

  // grid
  ctx.strokeStyle = "rgba(100,116,139,0.22)";
  ctx.lineWidth = 0.45;
  const xStep = tmax <= 20 ? 1 : tmax <= 40 ? 2 : 5;
  for (let x = 0; x <= tmax + 1e-9; x += xStep) {
    const px = xScale(x);
    ctx.beginPath();
    ctx.moveTo(px, pad.t);
    ctx.lineTo(px, pad.t + plotH);
    ctx.stroke();
  }
  for (let z = 1; z <= nShow; z++) {
    const py = yScale(z);
    ctx.beginPath();
    ctx.moveTo(pad.l, py);
    ctx.lineTo(pad.l + plotW, py);
    ctx.stroke();
  }

  const showText = nShow <= 16 && tmax <= 30;
  for (const c of plan.cells) {
    if (c.zone < 1 || c.zone > nShow) continue;
    const left = xScale(c.periodStart);
    const right = xScale(c.periodEnd);
    const w = Math.max(right - left, 1);
    const cy = yScale(c.zone);
    const color = tradeColor(c.tradeIndex);
    ctx.fillStyle = color;
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 0.8;
    const top = cy - barH / 2;
    ctx.beginPath();
    ctx.rect(left, top, w, barH);
    ctx.fill();
    ctx.stroke();
    if (showText) {
      ctx.fillStyle = "#ffffff";
      ctx.font = "bold 10px DM Sans, system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(`T${c.tradeIndex + 1}`, left + w / 2, cy);
    }
  }

  // axes
  ctx.fillStyle = "#1a202c";
  ctx.font = "11px DM Sans, system-ui, sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "top";
  for (let x = 0; x <= tmax + 1e-9; x += xStep) {
    ctx.fillText(String(Math.round(x)), xScale(x), pad.t + plotH + 8);
  }
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  const yStep = nShow <= 20 ? 1 : nShow <= 40 ? 2 : 5;
  for (let z = 1; z <= nShow; z += yStep) {
    ctx.fillText(String(z), pad.l - 8, yScale(z));
  }
  ctx.textAlign = "center";
  ctx.textBaseline = "bottom";
  ctx.fillStyle = "#64748b";
  ctx.font = "11px DM Sans, system-ui, sans-serif";
  ctx.fillText("Periode", pad.l + plotW / 2, cssH - 4);
  ctx.save();
  ctx.translate(12, pad.t + plotH / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText("Zona", 0, 0);
  ctx.restore();

  if (title) {
    ctx.fillStyle = "#1a365d";
    ctx.font = "600 12px DM Sans, system-ui, sans-serif";
    ctx.textAlign = "left";
    ctx.textBaseline = "top";
    ctx.fillText(title, pad.l, 10);
  }
}
