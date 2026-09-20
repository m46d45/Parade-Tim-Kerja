/**
 * Shared canvas axis helpers — tick numbers + unit labels.
 */

export type Pad = { l: number; r: number; t: number; b: number };

export function niceStep(max: number, targetTicks = 6): number {
  if (max <= 0) return 1;
  if (max <= 8) return 1;
  if (max <= 16) return 2;
  if (max <= 40) return 5;
  if (max <= 80) return 10;
  if (max <= 200) return 20;
  if (max <= 500) return 50;
  const raw = max / targetTicks;
  const pow = 10 ** Math.floor(Math.log10(raw));
  const n = raw / pow;
  const nice = n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10;
  return nice * pow;
}

export function drawPlotFrame(
  ctx: CanvasRenderingContext2D,
  pad: Pad,
  plotW: number,
  plotH: number,
): void {
  ctx.strokeStyle = "rgba(26, 54, 93, 0.35)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(pad.l, pad.t);
  ctx.lineTo(pad.l, pad.t + plotH);
  ctx.lineTo(pad.l + plotW, pad.t + plotH);
  ctx.stroke();
}

/** Horizontal grid + Y tick labels for [0, maxY]. */
export function drawYAxis(
  ctx: CanvasRenderingContext2D,
  opts: {
    pad: Pad;
    plotW: number;
    plotH: number;
    maxY: number;
    label: string;
    format?: (v: number) => string;
    cssH: number;
  },
): (y: number) => number {
  const { pad, plotW, plotH, maxY, label } = opts;
  const yMax = Math.max(maxY, 1e-9);
  const yScale = (y: number) => pad.t + plotH - (y / yMax) * plotH;
  const step = niceStep(yMax);
  const fmt = opts.format ?? ((v: number) => String(Math.round(v * 1000) / 1000));

  for (let z = 0; z <= yMax + 1e-9; z += step) {
    const yy = yScale(z);
    ctx.strokeStyle =
      z === 0 || Math.abs(z - yMax) < 1e-9
        ? "rgba(26,54,93,0.28)"
        : "rgba(26,54,93,0.08)";
    ctx.beginPath();
    ctx.moveTo(pad.l, yy);
    ctx.lineTo(pad.l + plotW, yy);
    ctx.stroke();
    ctx.fillStyle = "#334155";
    ctx.font = "10px DM Sans, sans-serif";
    ctx.textAlign = "right";
    ctx.textBaseline = "middle";
    ctx.fillText(fmt(z), pad.l - 8, yy);
  }
  // ensure max tick if not on step
  if (yMax % step > 1e-6) {
    const yy = yScale(yMax);
    ctx.fillStyle = "#334155";
    ctx.font = "10px DM Sans, sans-serif";
    ctx.textAlign = "right";
    ctx.textBaseline = "middle";
    ctx.fillText(fmt(yMax), pad.l - 8, yy);
  }

  ctx.save();
  ctx.translate(14, pad.t + plotH / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.fillStyle = "#0f2744";
  ctx.font = "600 11px DM Sans, sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(label, 0, 0);
  ctx.restore();

  return yScale;
}

/** Vertical grid + X tick labels for [0, maxX]. */
export function drawXAxis(
  ctx: CanvasRenderingContext2D,
  opts: {
    pad: Pad;
    plotW: number;
    plotH: number;
    maxX: number;
    label: string;
    cssH: number;
    format?: (v: number) => string;
  },
): (x: number) => number {
  const { pad, plotW, plotH, maxX, label, cssH } = opts;
  const xMax = Math.max(maxX, 1e-9);
  const xScale = (x: number) => pad.l + (x / xMax) * plotW;
  const step = niceStep(xMax);
  const fmt = opts.format ?? ((v: number) => String(Math.round(v)));

  for (let p = 0; p <= xMax + 1e-9; p += step) {
    const xx = xScale(p);
    ctx.strokeStyle =
      p === 0 || Math.abs(p - xMax) < 1e-9
        ? "rgba(26,54,93,0.22)"
        : "rgba(26,54,93,0.07)";
    ctx.beginPath();
    ctx.moveTo(xx, pad.t);
    ctx.lineTo(xx, pad.t + plotH);
    ctx.stroke();
    ctx.fillStyle = "#334155";
    ctx.font = "10px DM Sans, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    ctx.fillText(fmt(p), xx, pad.t + plotH + 6);
  }
  if (xMax % step > 1e-6) {
    const xx = xScale(xMax);
    ctx.fillStyle = "#334155";
    ctx.font = "10px DM Sans, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    ctx.fillText(fmt(xMax), xx, pad.t + plotH + 6);
  }

  ctx.fillStyle = "#0f2744";
  ctx.font = "600 11px DM Sans, sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "bottom";
  ctx.fillText(label, pad.l + plotW / 2, cssH - 4);

  return xScale;
}

/** X axis for a numeric range [xMin, xMax] (not necessarily from 0). */
export function drawXAxisRange(
  ctx: CanvasRenderingContext2D,
  opts: {
    pad: Pad;
    plotW: number;
    plotH: number;
    xMin: number;
    xMax: number;
    label: string;
    cssH: number;
    format?: (v: number) => string;
    ticks?: number[];
  },
): (x: number) => number {
  const { pad, plotW, plotH, xMin, xMax, label, cssH } = opts;
  const span = Math.max(xMax - xMin, 1e-9);
  const xScale = (x: number) => pad.l + ((x - xMin) / span) * plotW;
  const fmt = opts.format ?? ((v: number) => String(Math.round(v * 100) / 100));
  const ticks =
    opts.ticks ??
    (() => {
      const step = niceStep(span);
      const out: number[] = [];
      const start = Math.ceil(xMin / step) * step;
      for (let v = start; v <= xMax + 1e-9; v += step) out.push(v);
      if (!out.includes(xMin)) out.unshift(xMin);
      if (!out.includes(xMax)) out.push(xMax);
      return out;
    })();

  for (const p of ticks) {
    const xx = xScale(p);
    ctx.strokeStyle = "rgba(26,54,93,0.08)";
    ctx.beginPath();
    ctx.moveTo(xx, pad.t);
    ctx.lineTo(xx, pad.t + plotH);
    ctx.stroke();
    ctx.fillStyle = "#475569";
    ctx.font = "10px DM Sans, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    ctx.fillText(fmt(p), xx, pad.t + plotH + 6);
  }

  ctx.fillStyle = "#1a365d";
  ctx.font = "11px DM Sans, sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "bottom";
  ctx.fillText(label, pad.l + plotW / 2, cssH - 4);
  return xScale;
}
