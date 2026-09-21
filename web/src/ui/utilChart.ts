import type { ParadeResult } from "../core";
import { shortTradeName, tradeColor } from "../theme";

export function drawUtilChart(
  canvas: HTMLCanvasElement,
  result: ParadeResult,
  opts?: { cssHeight?: number },
): void {
  const dpr = window.devicePixelRatio || 1;
  const cssW = canvas.clientWidth || 640;
  const n = result.tradeMetrics.length;
  const cssH = opts?.cssHeight ?? Math.max(220, 48 + n * 42);
  canvas.width = Math.floor(cssW * dpr);
  canvas.height = Math.floor(cssH * dpr);
  canvas.style.height = `${cssH}px`;

  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

  const pad = { l: 150, r: 90, t: 18, b: 36 };
  const plotW = cssW - pad.l - pad.r;
  const plotH = cssH - pad.t - pad.b;
  const barH = Math.min(28, (plotH / Math.max(n, 1)) * 0.7);
  const gap = plotH / Math.max(n, 1);

  ctx.clearRect(0, 0, cssW, cssH);
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, cssW, cssH);

  // 0–100% grid
  ctx.font = "11px DM Sans, sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "top";
  for (const pct of [0, 25, 50, 75, 100]) {
    const x = pad.l + (pct / 100) * plotW;
    ctx.strokeStyle =
      pct === 100 ? "rgba(26, 54, 93, 0.35)" : "rgba(26, 54, 93, 0.1)";
    ctx.setLineDash(pct === 100 ? [4, 4] : []);
    ctx.beginPath();
    ctx.moveTo(x, pad.t);
    ctx.lineTo(x, pad.t + plotH);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = "#64748b";
    ctx.fillText(`${pct}%`, x, pad.t + plotH + 8);
  }

  result.tradeMetrics.forEach((m, i) => {
    const util = Math.max(0, Math.min(1, m.utilization)) * 100;
    const y = pad.t + gap * i + gap / 2;
    const color = tradeColor(i);
    const barW = (util / 100) * plotW;

    ctx.fillStyle = color;
    ctx.beginPath();
    const r = 4;
    const x0 = pad.l;
    const y0 = y - barH / 2;
    ctx.moveTo(x0 + r, y0);
    ctx.arcTo(x0 + barW, y0, x0 + barW, y0 + barH, Math.min(r, barW / 2));
    ctx.arcTo(x0 + barW, y0 + barH, x0, y0 + barH, Math.min(r, barW / 2));
    ctx.arcTo(x0, y0 + barH, x0, y0, r);
    ctx.arcTo(x0, y0, x0 + barW, y0, r);
    ctx.closePath();
    ctx.fill();

    ctx.fillStyle = "#1a202c";
    ctx.font = "12px DM Sans, sans-serif";
    ctx.textAlign = "right";
    ctx.textBaseline = "middle";
    ctx.fillText(`T${i + 1}: ${shortTradeName(m.name, 14)}`, pad.l - 10, y);

    ctx.fillStyle = "#1a365d";
    ctx.textAlign = "left";
    ctx.fillText(
      `${util.toFixed(1)}%  (idle ${m.totalIdle})`,
      pad.l + Math.min(barW + 8, plotW + 4),
      y,
    );
  });

  ctx.fillStyle = "#1a365d";
  ctx.font = "12px DM Sans, sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "bottom";
  ctx.fillText("Utilisasi kapasitas (%)", pad.l + plotW / 2, cssH - 2);
}

export function buildUtilLegend(
  result: ParadeResult,
): { color: string; text: string }[] {
  return result.tradeMetrics.map((m, i) => ({
    color: tradeColor(i),
    text: `T${i + 1}: ${(100 * m.utilization).toFixed(0)}% · idle ${m.totalIdle}`,
  }));
}
