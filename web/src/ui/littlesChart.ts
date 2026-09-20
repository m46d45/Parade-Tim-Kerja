import { littlesLawSeries, type ParadeResult } from "../core";

const PIPE_COLOR = "#1a365d";
const BUF_COLOR = "#f59e0b";

export function drawLittlesChart(
  canvas: HTMLCanvasElement,
  result: ParadeResult,
  opts?: { cssHeight?: number },
): void {
  const dpr = window.devicePixelRatio || 1;
  const cssW = canvas.clientWidth || 640;
  const cssH = opts?.cssHeight ?? 300;
  canvas.width = Math.floor(cssW * dpr);
  canvas.height = Math.floor(cssH * dpr);
  canvas.style.height = `${cssH}px`;

  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  const g = ctx;
  g.setTransform(dpr, 0, 0, dpr, 0, 0);

  const series = littlesLawSeries(result);
  const maxX = Math.max(series.period.length - 1, 1);
  const maxY = Math.max(
    1,
    ...series.pipelineWip,
    ...series.bufferWip,
  );

  const pad = { l: 48, r: 18, t: 18, b: 48 };
  const plotW = cssW - pad.l - pad.r;
  const plotH = cssH - pad.t - pad.b;
  const xScale = (x: number) => pad.l + (x / maxX) * plotW;
  const yScale = (y: number) => pad.t + plotH - (y / maxY) * plotH;

  g.clearRect(0, 0, cssW, cssH);
  g.fillStyle = "#ffffff";
  g.fillRect(0, 0, cssW, cssH);

  const yStep = maxY <= 12 ? 1 : Math.ceil(maxY / 8);
  g.font = "11px DM Sans, sans-serif";
  g.textAlign = "right";
  g.textBaseline = "middle";
  for (let z = 0; z <= maxY; z += yStep) {
    const yy = yScale(z);
    g.strokeStyle = z === 0 ? "rgba(26,54,93,0.28)" : "rgba(26,54,93,0.1)";
    g.beginPath();
    g.moveTo(pad.l, yy);
    g.lineTo(pad.l + plotW, yy);
    g.stroke();
    g.fillStyle = "#64748b";
    g.fillText(String(z), pad.l - 8, yy);
  }

  const xStep = maxX <= 20 ? 2 : Math.ceil(maxX / 10);
  g.textAlign = "center";
  g.textBaseline = "top";
  for (let p = 0; p <= maxX; p += xStep) {
    const xx = xScale(p);
    g.strokeStyle = "rgba(26,54,93,0.08)";
    g.beginPath();
    g.moveTo(xx, pad.t);
    g.lineTo(xx, pad.t + plotH);
    g.stroke();
    g.fillStyle = "#64748b";
    g.fillText(String(p), xx, pad.t + plotH + 8);
  }

  function strokeLine(ys: number[], color: string, width: number): void {
    g.strokeStyle = color;
    g.lineWidth = width;
    g.beginPath();
    ys.forEach((y, i) => {
      const X = xScale(i);
      const Y = yScale(y);
      if (i === 0) g.moveTo(X, Y);
      else g.lineTo(X, Y);
    });
    g.stroke();
  }

  strokeLine(series.pipelineWip, PIPE_COLOR, 2.4);
  strokeLine(series.bufferWip, BUF_COLOR, 2);

  g.fillStyle = "#1a365d";
  g.font = "12px DM Sans, sans-serif";
  g.textAlign = "center";
  g.textBaseline = "bottom";
  g.fillText("Periode", pad.l + plotW / 2, cssH - 4);
  g.save();
  g.translate(14, pad.t + plotH / 2);
  g.rotate(-Math.PI / 2);
  g.textAlign = "center";
  g.textBaseline = "top";
  g.fillText("WIP (zona)", 0, 0);
  g.restore();
}

export function buildLittlesLegend(): { color: string; text: string }[] {
  return [
    { color: PIPE_COLOR, text: "WIP pipeline (T1−T5)" },
    { color: BUF_COLOR, text: "WIP buffer (Σ antar-tim)" },
  ];
}
