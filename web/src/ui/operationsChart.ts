import {
  evaluateAtWip,
  littlesOperationsCurve,
  type ParadeResult,
} from "../core";
import { niceStep } from "./chartAxis";

const COLOR_TH = "#2563eb";
const COLOR_CT = "#dc2626";
const COLOR_BC_TH = "#93c5fd";
const COLOR_BC_CT = "#fca5a5";
const COLOR_CONWIP = "#7c3aed";

export function drawOperationsChart(
  canvas: HTMLCanvasElement,
  result: ParadeResult,
  conwipLevel: number,
  opts?: { cssHeight?: number },
): void {
  const dpr = window.devicePixelRatio || 1;
  const cssW = canvas.clientWidth || 640;
  const cssH = opts?.cssHeight ?? 340;
  canvas.width = Math.floor(cssW * dpr);
  canvas.height = Math.floor(cssH * dpr);
  canvas.style.height = `${cssH}px`;

  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  const g = ctx;
  g.setTransform(dpr, 0, 0, dpr, 0, 0);

  const d = littlesOperationsCurve(result);
  const conwip = conwipLevel;
  const pad = { l: 52, r: 52, t: 28, b: 52 };
  const plotW = cssW - pad.l - pad.r;
  const plotH = cssH - pad.t - pad.b;

  const xRight = Math.max(
    d.bcWip[d.bcWip.length - 1] ?? 0,
    d.wip.length ? Math.max(...d.wip) : 0,
    d.wOpt + 5,
    conwip + 5,
    d.opWip + 5,
    d.wMin + 5,
    10,
  );
  const maxTh = Math.max(d.thMax * 1.15, ...(d.th.length ? d.th : [1]), ...(d.bcTh.length ? d.bcTh : [1]));
  const maxCt = Math.max(
    d.t0 * 1.5,
    ...(d.ct.length ? d.ct : [1]),
    ...(d.bcCt.length ? d.bcCt : [1]),
    d.opCt,
  );

  const xScale = (w: number) => pad.l + (w / xRight) * plotW;
  const yTh = (th: number) => pad.t + plotH - (th / maxTh) * plotH;
  const yCt = (ct: number) => pad.t + plotH - (ct / maxCt) * plotH;

  g.clearRect(0, 0, cssW, cssH);
  g.fillStyle = "#ffffff";
  g.fillRect(0, 0, cssW, cssH);

  g.font = "11px DM Sans, sans-serif";
  g.fillStyle = "#64748b";
  g.textAlign = "center";
  g.textBaseline = "bottom";
  g.fillText("Kurva operasi WIP–TH–CT (Little + Kingman)", pad.l + plotW / 2, pad.t - 8);

  // Y ticks (left = TH)
  const thStep = niceStep(maxTh);
  for (let v = 0; v <= maxTh + 1e-9; v += thStep) {
    const y = yTh(v);
    g.strokeStyle = v === 0 ? "rgba(26,54,93,0.28)" : "rgba(26,54,93,0.08)";
    g.beginPath();
    g.moveTo(pad.l, y);
    g.lineTo(pad.l + plotW, y);
    g.stroke();
    g.fillStyle = COLOR_TH;
    g.font = "10px DM Sans, sans-serif";
    g.textAlign = "right";
    g.textBaseline = "middle";
    g.fillText(v.toFixed(2), pad.l - 8, y);
  }
  // Y ticks right = CT
  const ctStep = niceStep(maxCt);
  for (let v = 0; v <= maxCt + 1e-9; v += ctStep) {
    const y = yCt(v);
    g.fillStyle = COLOR_CT;
    g.font = "10px DM Sans, sans-serif";
    g.textAlign = "left";
    g.textBaseline = "middle";
    g.fillText(v.toFixed(1), pad.l + plotW + 8, y);
  }
  // X ticks
  const xStep = niceStep(xRight);
  for (let v = 0; v <= xRight + 1e-9; v += xStep) {
    const x = xScale(v);
    g.strokeStyle = "rgba(26,54,93,0.07)";
    g.beginPath();
    g.moveTo(x, pad.t);
    g.lineTo(x, pad.t + plotH);
    g.stroke();
    g.fillStyle = "#475569";
    g.font = "10px DM Sans, sans-serif";
    g.textAlign = "center";
    g.textBaseline = "top";
    g.fillText(String(Math.round(v)), x, pad.t + plotH + 6);
  }
  g.strokeStyle = "rgba(26,54,93,0.35)";
  g.beginPath();
  g.moveTo(pad.l, pad.t);
  g.lineTo(pad.l, pad.t + plotH);
  g.lineTo(pad.l + plotW, pad.t + plotH);
  g.stroke();

  function strokeXY(
    xs: number[],
    ys: number[],
    yFn: (v: number) => number,
    color: string,
    width: number,
    dash?: number[],
  ): void {
    if (!xs.length) return;
    g.strokeStyle = color;
    g.lineWidth = width;
    g.setLineDash(dash ?? []);
    g.beginPath();
    xs.forEach((x, i) => {
      const X = xScale(x);
      const Y = yFn(ys[i]);
      if (i === 0) g.moveTo(X, Y);
      else g.lineTo(X, Y);
    });
    g.stroke();
    g.setLineDash([]);
  }

  // best-case fill
  if (d.bcWip.length && d.bcTh.length) {
    g.fillStyle = "rgba(147,197,253,0.18)";
    g.beginPath();
    d.bcWip.forEach((w, i) => {
      const X = xScale(w);
      const Y = yTh(d.bcTh[i]);
      if (i === 0) g.moveTo(X, Y);
      else g.lineTo(X, Y);
    });
    g.lineTo(xScale(d.bcWip[d.bcWip.length - 1]), yTh(0));
    g.lineTo(xScale(d.bcWip[0]), yTh(0));
    g.closePath();
    g.fill();
  }

  strokeXY(d.bcWip, d.bcTh, yTh, COLOR_BC_TH, 2);
  strokeXY(d.bcWip, d.bcCt, yCt, COLOR_BC_CT, 2);

  if (d.wip.length) {
    const order = d.wip.map((_, i) => i).sort((a, b) => d.wip[a] - d.wip[b]);
    const ws = order.map((i) => d.wip[i]);
    const ths = order.map((i) => d.th[i]);
    const cts = order.map((i) => d.ct[i]);
    strokeXY(ws, ths, yTh, COLOR_TH, 2.2);
    strokeXY(ws, cts, yCt, COLOR_CT, 2.2, [5, 4]);
  }

  // landmarks
  function vline(w: number, color: string, label: string): void {
    const x = xScale(w);
    g.strokeStyle = color;
    g.lineWidth = 1.4;
    g.setLineDash([3, 3]);
    g.beginPath();
    g.moveTo(x, pad.t);
    g.lineTo(x, pad.t + plotH);
    g.stroke();
    g.setLineDash([]);
    g.fillStyle = color;
    g.font = "10px DM Sans, sans-serif";
    g.textAlign = "center";
    g.textBaseline = "top";
    g.fillText(label, x, pad.t + 2);
  }

  vline(d.wMin, "#64748b", `W_min=${d.wMin.toFixed(1)}`);
  if (Math.abs(d.wOpt - d.wMin) > 0.05) {
    vline(d.wOpt, "#0f766e", `W_opt=${d.wOpt.toFixed(1)}`);
  }
  vline(conwip, COLOR_CONWIP, `CONWIP=${conwip.toFixed(1)}`);

  // purple band W_min → CONWIP
  const x0 = xScale(Math.min(d.wMin, conwip));
  const x1 = xScale(Math.max(d.wMin, conwip));
  g.fillStyle = "rgba(124,58,237,0.08)";
  g.fillRect(x0, pad.t, Math.max(x1 - x0, 1), plotH);

  // operating point
  g.fillStyle = "#0f172a";
  g.beginPath();
  g.arc(xScale(d.opWip), yTh(d.opTh), 5, 0, Math.PI * 2);
  g.fill();
  g.fillStyle = COLOR_CT;
  g.beginPath();
  g.arc(xScale(d.opWip), yCt(d.opCt), 4, 0, Math.PI * 2);
  g.fill();

  // CONWIP predicted
  const pred = evaluateAtWip(result, conwip);
  if (Number.isFinite(pred.th)) {
    g.strokeStyle = COLOR_CONWIP;
    g.lineWidth = 1.5;
    g.beginPath();
    g.arc(xScale(conwip), yTh(pred.th), 6, 0, Math.PI * 2);
    g.stroke();
  }

  g.fillStyle = COLOR_TH;
  g.font = "11px DM Sans, sans-serif";
  g.textAlign = "left";
  g.textBaseline = "middle";
  g.fillText("TH (zona/periode)", 6, pad.t + 12);
  g.fillStyle = COLOR_CT;
  g.textAlign = "right";
  g.fillText("CT (periode)", cssW - 6, pad.t + 12);

  g.fillStyle = "#1a365d";
  g.textAlign = "center";
  g.textBaseline = "bottom";
  g.fillText("WIP (zona)", pad.l + plotW / 2, cssH - 4);
}

export function snapConwip(x: number): number {
  return Math.round(x * 2) / 2;
}
