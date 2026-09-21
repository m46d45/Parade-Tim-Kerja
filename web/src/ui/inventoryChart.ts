import {
  inventoryFillRateCurve,
  inventoryFillRateMetrics,
  type ParadeResult,
} from "../core";
import { bufferColor, shortTradeName } from "../theme";

export function drawInventoryChart(
  canvas: HTMLCanvasElement,
  result: ParadeResult,
  opts?: { cssHeight?: number },
): void {
  const dpr = window.devicePixelRatio || 1;
  const cssW = canvas.clientWidth || 640;
  const cssH = opts?.cssHeight ?? 320;
  canvas.width = Math.floor(cssW * dpr);
  canvas.height = Math.floor(cssH * dpr);
  canvas.style.height = `${cssH}px`;

  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

  const d = inventoryFillRateCurve(result);
  const pad = { l: 52, r: 18, t: 28, b: 44 };
  const plotW = cssW - pad.l - pad.r;
  const plotH = cssH - pad.t - pad.b;

  const order = d.fillRate.map((_, i) => i).sort((a, b) => d.fillRate[a] - d.fillRate[b]);
  const frs = order.map((i) => 100 * d.fillRate[i]);
  const invs = order.map((i) => d.inventory[i]);
  const maxInv = Math.max(
    1,
    ...invs,
    d.opInventory,
    ...d.interfaces.map((r) => r.avgInventory),
  );

  const xScale = (fr: number) => pad.l + (fr / 105) * plotW;
  const yScale = (inv: number) => pad.t + plotH - (inv / maxInv) * plotH;

  ctx.clearRect(0, 0, cssW, cssH);
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, cssW, cssH);

  ctx.font = "11px DM Sans, sans-serif";
  ctx.fillStyle = "#64748b";
  ctx.textAlign = "center";
  ctx.textBaseline = "bottom";
  ctx.fillText("Fill rate vs inventory (tradeoff service–persediaan)", pad.l + plotW / 2, pad.t - 8);

  for (const fr of [0, 25, 50, 75, 100]) {
    const x = xScale(fr);
    ctx.strokeStyle = fr === 100 ? "rgba(26,54,93,0.28)" : "rgba(26,54,93,0.1)";
    ctx.setLineDash(fr === 100 ? [4, 4] : []);
    ctx.beginPath();
    ctx.moveTo(x, pad.t);
    ctx.lineTo(x, pad.t + plotH);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = "#64748b";
    ctx.textBaseline = "top";
    ctx.fillText(`${fr}%`, x, pad.t + plotH + 8);
  }

  const yStep = maxInv <= 8 ? 1 : Math.ceil(maxInv / 6);
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  for (let z = 0; z <= maxInv; z += yStep) {
    const y = yScale(z);
    ctx.strokeStyle = "rgba(26,54,93,0.1)";
    ctx.beginPath();
    ctx.moveTo(pad.l, y);
    ctx.lineTo(pad.l + plotW, y);
    ctx.stroke();
    ctx.fillStyle = "#64748b";
    ctx.fillText(String(Math.round(z * 10) / 10), pad.l - 8, y);
  }

  // theoretical curve
  ctx.strokeStyle = "#0f766e";
  ctx.lineWidth = 2.2;
  ctx.beginPath();
  frs.forEach((fr, i) => {
    const X = xScale(fr);
    const Y = yScale(invs[i]);
    if (i === 0) ctx.moveTo(X, Y);
    else ctx.lineTo(X, Y);
  });
  ctx.stroke();

  // system operating point
  ctx.fillStyle = "#0f172a";
  ctx.beginPath();
  ctx.arc(xScale(100 * d.opFillRate), yScale(d.opInventory), 6, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = "#fff";
  ctx.lineWidth = 1.5;
  ctx.stroke();

  // interface diamonds
  d.interfaces.forEach((row, i) => {
    const color = bufferColor(i);
    const x = xScale(100 * row.fillRate);
    const y = yScale(row.avgInventory);
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.moveTo(x, y - 6);
    ctx.lineTo(x + 6, y);
    ctx.lineTo(x, y + 6);
    ctx.lineTo(x - 6, y);
    ctx.closePath();
    ctx.fill();
    ctx.strokeStyle = "#fff";
    ctx.lineWidth = 1.2;
    ctx.stroke();
  });

  ctx.fillStyle = "#1a365d";
  ctx.font = "12px DM Sans, sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "bottom";
  ctx.fillText("Fill rate (%)", pad.l + plotW / 2, cssH - 4);
  ctx.save();
  ctx.translate(14, pad.t + plotH / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.textAlign = "center";
  ctx.textBaseline = "top";
  ctx.fillText("Inventory / WIP buffer ⌀", 0, 0);
  ctx.restore();
}

export function buildInventoryLegend(
  result: ParadeResult,
): { color: string; text: string }[] {
  const fr = inventoryFillRateMetrics(result);
  return [
    {
      color: "#0f766e",
      text: "Kurva teoritis (base-stock)",
    },
    {
      color: "#0f172a",
      text: `Sistem FR=${(100 * fr.fillRateSystem).toFixed(1)}% · I̅=${fr.avgInventorySystem.toFixed(2)}`,
    },
    ...fr.interfaces.map((row, i) => ({
      color: bufferColor(i),
      text: `${row.buffer}: ${shortTradeName(row.from, 8)}→${shortTradeName(row.to, 8)} I̅=${row.avgInventory.toFixed(2)}`,
    })),
  ];
}
