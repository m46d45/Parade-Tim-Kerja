import { bufferSeries, type ParadeResult } from "../core";
import { bufferColor, shortTradeName } from "../theme";

export type BufferHit = {
  iface: number;
  label: string;
  period: number;
  wip: number;
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

function xTickStep(maxX: number): number {
  if (maxX <= 16) return 1;
  if (maxX <= 32) return 2;
  if (maxX <= 60) return 5;
  return Math.ceil(maxX / 12);
}

function yTickStep(maxY: number): number {
  if (maxY <= 12) return 1;
  if (maxY <= 30) return 2;
  return Math.ceil(maxY / 10);
}

function buildLayout(cssW: number, cssH: number, maxX: number, maxY: number): Layout {
  const pad = { l: 52, r: 18, t: 18, b: 48 };
  const plotW = cssW - pad.l - pad.r;
  const plotH = cssH - pad.t - pad.b;
  const yMax = Math.max(maxY, 1);
  return {
    pad,
    cssW,
    cssH,
    plotW,
    plotH,
    maxX,
    maxY: yMax,
    xScale: (x) => pad.l + (x / Math.max(maxX, 1)) * plotW,
    yScale: (y) => pad.t + plotH - (y / yMax) * plotH,
  };
}

export function drawBufferChart(
  canvas: HTMLCanvasElement,
  result: ParadeResult,
  opts?: { cssHeight?: number },
): BufferHit[] {
  const dpr = window.devicePixelRatio || 1;
  const cssW = canvas.clientWidth || 640;
  const cssH = opts?.cssHeight ?? 320;
  canvas.width = Math.floor(cssW * dpr);
  canvas.height = Math.floor(cssH * dpr);
  canvas.style.height = `${cssH}px`;

  const ctx = canvas.getContext("2d");
  if (!ctx) return [];
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

  const series = bufferSeries(result);
  const hits: BufferHit[] = [];
  if (!series.length) {
    ctx.clearRect(0, 0, cssW, cssH);
    ctx.fillStyle = "#64748b";
    ctx.font = "13px DM Sans, sans-serif";
    ctx.fillText("Tidak ada buffer (satu tim)", 24, 40);
    return hits;
  }

  const maxX = Math.max(result.duration, series[0].length - 1, 1);
  const maxY = Math.max(
    1,
    ...series.map((s) => Math.max(...s)),
    ...result.maxBuffer,
  );
  const L = buildLayout(cssW, cssH, maxX, maxY);

  ctx.clearRect(0, 0, cssW, cssH);
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, cssW, cssH);

  const yStep = yTickStep(maxY);
  ctx.font = "11px DM Sans, sans-serif";
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  for (let z = 0; z <= maxY; z += yStep) {
    const yy = L.yScale(z);
    ctx.strokeStyle = z === 0 ? "rgba(26, 54, 93, 0.28)" : "rgba(26, 54, 93, 0.12)";
    ctx.beginPath();
    ctx.moveTo(L.pad.l, yy);
    ctx.lineTo(L.pad.l + L.plotW, yy);
    ctx.stroke();
    ctx.fillStyle = "#64748b";
    ctx.fillText(String(z), L.pad.l - 8, yy);
  }

  const xStep = xTickStep(maxX);
  ctx.textAlign = "center";
  ctx.textBaseline = "top";
  for (let p = 0; p <= maxX; p += xStep) {
    const xx = L.xScale(p);
    ctx.strokeStyle = "rgba(26, 54, 93, 0.1)";
    ctx.beginPath();
    ctx.moveTo(xx, L.pad.t);
    ctx.lineTo(xx, L.pad.t + L.plotH);
    ctx.stroke();
    ctx.fillStyle = "#64748b";
    ctx.fillText(String(p), xx, L.pad.t + L.plotH + 8);
  }

  series.forEach((ys, j) => {
    const color = bufferColor(j);
    const up = result.config.trades[j];
    const down = result.config.trades[j + 1];
    const label = `B${j + 1}: ${shortTradeName(up.name, 12)} → ${shortTradeName(down.name, 12)}`;
    ctx.strokeStyle = color;
    ctx.lineWidth = 2.2;
    ctx.beginPath();
    ys.forEach((y, i) => {
      const X = L.xScale(i);
      const Y = L.yScale(y);
      if (i === 0) ctx.moveTo(X, Y);
      else ctx.lineTo(X, Y);
    });
    ctx.stroke();

    // max dashed
    if (result.maxBuffer[j] > 0) {
      const yy = L.yScale(result.maxBuffer[j]);
      ctx.strokeStyle = color;
      ctx.globalAlpha = 0.45;
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(L.pad.l, yy);
      ctx.lineTo(L.pad.l + L.plotW, yy);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.globalAlpha = 1;
    }

    const markEvery = ys.length <= 40 ? 1 : Math.ceil(ys.length / 20);
    ys.forEach((y, i) => {
      if (i % markEvery !== 0) return;
      const X = L.xScale(i);
      const Y = L.yScale(y);
      ctx.fillStyle = color;
      ctx.strokeStyle = "#ffffff";
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.arc(X, Y, 3.6, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
      hits.push({ iface: j, label, period: i, wip: y, color });
    });
  });

  ctx.fillStyle = "#1a365d";
  ctx.font = "12px DM Sans, sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "bottom";
  ctx.fillText("Periode (0 = awal)", L.pad.l + L.plotW / 2, cssH - 4);
  ctx.save();
  ctx.translate(14, L.pad.t + L.plotH / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.textAlign = "center";
  ctx.textBaseline = "top";
  ctx.fillText("WIP buffer (zona)", 0, 0);
  ctx.restore();

  (canvas as HTMLCanvasElement & { __bufLayout?: Layout }).__bufLayout = L;
  return hits;
}

export function hitTestBuffer(
  canvas: HTMLCanvasElement,
  hits: BufferHit[],
  clientX: number,
  clientY: number,
  radiusPx = 10,
): BufferHit | null {
  const rect = canvas.getBoundingClientRect();
  const x = clientX - rect.left;
  const y = clientY - rect.top;
  const L = (canvas as HTMLCanvasElement & { __bufLayout?: Layout }).__bufLayout;
  if (!L || !hits.length) return null;
  let best: BufferHit | null = null;
  let bestD = radiusPx;
  for (const h of hits) {
    const hx = L.xScale(h.period);
    const hy = L.yScale(h.wip);
    const d = Math.hypot(hx - x, hy - y);
    if (d < bestD) {
      bestD = d;
      best = h;
    }
  }
  return best;
}

export function buildBufferLegend(
  result: ParadeResult,
): { color: string; text: string }[] {
  return result.config.trades.slice(0, -1).map((t, j) => {
    const down = result.config.trades[j + 1];
    const peak = result.maxBuffer[j] ?? 0;
    return {
      color: bufferColor(j),
      text: `B${j + 1}: ${shortTradeName(t.name, 10)}→${shortTradeName(down.name, 10)} (max ${peak})`,
    };
  });
}
