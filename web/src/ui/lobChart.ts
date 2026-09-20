import { cumulativeSeries, type ParadeResult, type TradeConfig } from "../core";
import { IDEAL_COLOR, shortTradeName, tradeColor } from "../theme";

export type LobHit = {
  tradeIndex: number; // -1 = ideal
  label: string;
  period: number;
  zone: number;
  color: string;
};

type Layout = {
  pad: { l: number; r: number; t: number; b: number };
  cssW: number;
  cssH: number;
  plotW: number;
  plotH: number;
  maxX: number;
  maxY: number;
  xScale: (x: number) => number;
  yScale: (y: number) => number;
};

function buildLayout(cssW: number, cssH: number, maxX: number, maxY: number): Layout {
  const pad = { l: 52, r: 18, t: 18, b: 48 };
  const plotW = cssW - pad.l - pad.r;
  const plotH = cssH - pad.t - pad.b;
  return {
    pad,
    cssW,
    cssH,
    plotW,
    plotH,
    maxX,
    maxY,
    xScale: (x) => pad.l + (x / Math.max(maxX, 1)) * plotW,
    yScale: (y) => pad.t + plotH - (y / Math.max(maxY, 1)) * plotH,
  };
}

function drawMarker(
  ctx: CanvasRenderingContext2D,
  kind: string,
  x: number,
  y: number,
  color: string,
  size = 4.2,
): void {
  ctx.fillStyle = color;
  ctx.strokeStyle = "#0c1222";
  ctx.lineWidth = 1;
  ctx.beginPath();
  if (kind === "s") {
    ctx.rect(x - size, y - size, size * 2, size * 2);
  } else if (kind === "^") {
    ctx.moveTo(x, y - size);
    ctx.lineTo(x + size, y + size);
    ctx.lineTo(x - size, y + size);
    ctx.closePath();
  } else if (kind === "D") {
    ctx.moveTo(x, y - size);
    ctx.lineTo(x + size, y);
    ctx.lineTo(x, y + size);
    ctx.lineTo(x - size, y);
    ctx.closePath();
  } else if (kind === "v") {
    ctx.moveTo(x, y + size);
    ctx.lineTo(x + size, y - size);
    ctx.lineTo(x - size, y - size);
    ctx.closePath();
  } else {
    ctx.arc(x, y, size, 0, Math.PI * 2);
  }
  ctx.fill();
  ctx.stroke();
}

function xTickStep(maxX: number): number {
  if (maxX <= 16) return 1;
  if (maxX <= 32) return 2;
  if (maxX <= 60) return 5;
  return Math.ceil(maxX / 12);
}

/**
 * Draw LoB with integer zone grid, labeled ticks, markers, and ideal baseline.
 * Returns hit-test points for hover tooltips.
 */
export function drawLobChart(
  canvas: HTMLCanvasElement,
  result: ParadeResult,
  opts?: { cssHeight?: number },
): LobHit[] {
  const dpr = window.devicePixelRatio || 1;
  const cssW = canvas.clientWidth || 640;
  const cssH = opts?.cssHeight ?? 380;
  canvas.width = Math.floor(cssW * dpr);
  canvas.height = Math.floor(cssH * dpr);
  canvas.style.height = `${cssH}px`;

  const ctx = canvas.getContext("2d");
  if (!ctx) return [];
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

  const cum = cumulativeSeries(result);
  const ideal = result.idealLastTradeCumulative;
  const maxX = Math.max(result.duration, ideal.length - 1, 1);
  const maxY = result.config.totalUnits;
  const L = buildLayout(cssW, cssH, maxX, maxY);
  const hits: LobHit[] = [];

  // background
  ctx.clearRect(0, 0, cssW, cssH);
  ctx.fillStyle = "rgba(255,255,255,0.035)";
  ctx.fillRect(0, 0, cssW, cssH);

  // Y grid + labels (every zone)
  ctx.font = "11px DM Sans, sans-serif";
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  for (let z = 0; z <= maxY; z++) {
    const yy = L.yScale(z);
    ctx.strokeStyle = z === 0 || z === maxY ? "rgba(148,163,184,0.45)" : "rgba(148,163,184,0.22)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(L.pad.l, yy);
    ctx.lineTo(L.pad.l + L.plotW, yy);
    ctx.stroke();
    ctx.fillStyle = "#94a3b8";
    ctx.fillText(String(z), L.pad.l - 8, yy);
  }

  // X grid + labels
  const xStep = xTickStep(maxX);
  ctx.textAlign = "center";
  ctx.textBaseline = "top";
  for (let p = 0; p <= maxX; p += xStep) {
    const xx = L.xScale(p);
    ctx.strokeStyle = "rgba(148,163,184,0.18)";
    ctx.beginPath();
    ctx.moveTo(xx, L.pad.t);
    ctx.lineTo(xx, L.pad.t + L.plotH);
    ctx.stroke();
    ctx.fillStyle = "#94a3b8";
    ctx.fillText(String(p), xx, L.pad.t + L.plotH + 8);
  }
  // minor period ticks (no label) when major > 1
  if (xStep > 1) {
    for (let p = 0; p <= maxX; p++) {
      if (p % xStep === 0) continue;
      const xx = L.xScale(p);
      ctx.strokeStyle = "rgba(148,163,184,0.10)";
      ctx.beginPath();
      ctx.moveTo(xx, L.pad.t + L.plotH);
      ctx.lineTo(xx, L.pad.t + L.plotH + 4);
      ctx.stroke();
    }
  }

  // Ideal (last trade baseline)
  if (ideal.length > 1) {
    ctx.strokeStyle = IDEAL_COLOR;
    ctx.lineWidth = 1.8;
    ctx.setLineDash([6, 4]);
    ctx.beginPath();
    ideal.forEach((y: number, i: number) => {
      const X = L.xScale(i);
      const Y = L.yScale(y);
      if (i === 0) ctx.moveTo(X, Y);
      else ctx.lineTo(X, Y);
      hits.push({
        tradeIndex: -1,
        label: `Ideal (tanpa var, batch=${result.config.batchSize})`,
        period: i,
        zone: y,
        color: IDEAL_COLOR,
      });
    });
    ctx.stroke();
    ctx.setLineDash([]);
  }

  // Trade series
  const markerKinds = ["o", "s", "^", "D", "v"];
  cum.forEach((series: number[], ti: number) => {
    const color = tradeColor(ti);
    const trade = result.config.trades[ti];
    const label = `T${ti + 1}: ${shortTradeName(trade.name)}`;
    ctx.strokeStyle = color;
    ctx.lineWidth = 2.4;
    ctx.beginPath();
    series.forEach((y: number, i: number) => {
      const X = L.xScale(i);
      const Y = L.yScale(y);
      if (i === 0) ctx.moveTo(X, Y);
      else ctx.lineTo(X, Y);
    });
    ctx.stroke();

    const markEvery = series.length <= 40 ? 1 : Math.ceil(series.length / 20);
    series.forEach((y: number, i: number) => {
      if (i % markEvery !== 0) return;
      const X = L.xScale(i);
      const Y = L.yScale(y);
      drawMarker(ctx, markerKinds[ti % markerKinds.length], X, Y, color);
      hits.push({
        tradeIndex: ti,
        label,
        period: i,
        zone: y,
        color,
      });
    });
  });

  // Axis titles
  ctx.fillStyle = "#cbd5e1";
  ctx.font = "12px DM Sans, sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "bottom";
  ctx.fillText("Periode (0 = awal)", L.pad.l + L.plotW / 2, cssH - 4);
  ctx.save();
  ctx.translate(14, L.pad.t + L.plotH / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.textAlign = "center";
  ctx.textBaseline = "top";
  ctx.fillText("Zona kumulatif (diskrit)", 0, 0);
  ctx.restore();

  // store layout for hit testing via canvas dataset
  (canvas as HTMLCanvasElement & { __lobLayout?: Layout }).__lobLayout = L;
  return hits;
}

export function hitTestLob(
  canvas: HTMLCanvasElement,
  hits: LobHit[],
  clientX: number,
  clientY: number,
  radiusPx = 10,
): LobHit | null {
  const rect = canvas.getBoundingClientRect();
  const x = clientX - rect.left;
  const y = clientY - rect.top;
  const L = (canvas as HTMLCanvasElement & { __lobLayout?: Layout }).__lobLayout;
  if (!L || !hits.length) return null;

  let best: LobHit | null = null;
  let bestD = radiusPx;
  for (const h of hits) {
    const hx = L.xScale(h.period);
    const hy = L.yScale(h.zone);
    const d = Math.hypot(hx - x, hy - y);
    // Prefer trade points over ideal when equally close
    const score = d + (h.tradeIndex < 0 ? 0.4 : 0);
    if (score < bestD) {
      bestD = score;
      best = h;
    }
  }
  return best;
}

export function buildLegendItems(
  result: ParadeResult,
): { color: string; text: string; dashed?: boolean }[] {
  const items: { color: string; text: string; dashed?: boolean }[] =
    result.config.trades.map((t: TradeConfig, i: number) => ({
      color: tradeColor(i),
      text: `T${i + 1}: ${shortTradeName(t.name)} (${t.baseSpeed})`,
    }));
  items.push({
    color: IDEAL_COLOR,
    text: `Ideal (tanpa var, batch=${result.config.batchSize})`,
    dashed: true,
  });
  return items;
}
