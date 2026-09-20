import {
  kingmanCombined,
  kingmanCurvePoints,
  kingmanMetrics,
  type ParadeResult,
} from "../core";
import { shortTradeName, tradeColor } from "../theme";

export function drawKingmanChart(
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

  const kg = kingmanMetrics(result);
  const comb = kingmanCombined(result);
  const curve = kingmanCurvePoints(result);

  ctx.clearRect(0, 0, cssW, cssH);
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, cssW, cssH);

  // Left: CT vs u curve | Right: per-station CT bars
  const mid = Math.floor(cssW * 0.52);
  const padL = { l: 44, r: 12, t: 28, b: 40 };
  const padR = { l: 12, r: 16, t: 28, b: 40 };

  // --- Curve panel ---
  const cW = mid - padL.l - padL.r;
  const cH = cssH - padL.t - padL.b;
  const maxCt = Math.max(
    2,
    ...curve.map((p) => p.ct),
    Number.isFinite(comb.ct) ? comb.ct : 0,
    ...kg.stations.map((s) =>
      Number.isFinite(s.ctKingman) ? s.ctKingman : 0,
    ),
    ...kg.stations.map((s) => s.ctObserved),
  );
  const ux = (u: number) => padL.l + u * cW;
  const cy = (ct: number) => padL.t + cH - (ct / maxCt) * cH;

  ctx.font = "11px DM Sans, sans-serif";
  ctx.fillStyle = "#64748b";
  ctx.textAlign = "center";
  ctx.textBaseline = "bottom";
  ctx.fillText("Kingman: CT vs u̅", padL.l + cW / 2, padL.t - 8);

  for (const u of [0, 0.25, 0.5, 0.75, 1]) {
    const x = ux(u);
    ctx.strokeStyle = "rgba(26,54,93,0.1)";
    ctx.beginPath();
    ctx.moveTo(x, padL.t);
    ctx.lineTo(x, padL.t + cH);
    ctx.stroke();
    ctx.fillStyle = "#64748b";
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    ctx.fillText(u.toFixed(2), x, padL.t + cH + 6);
  }

  ctx.strokeStyle = "#1a365d";
  ctx.lineWidth = 2.2;
  ctx.beginPath();
  curve.forEach((p, i) => {
    const X = ux(p.u);
    const Y = cy(p.ct);
    if (i === 0) ctx.moveTo(X, Y);
    else ctx.lineTo(X, Y);
  });
  ctx.stroke();

  // Operating point
  if (Number.isFinite(comb.ct)) {
    const ox = ux(Math.min(comb.uBar, 0.999));
    const oy = cy(comb.ct);
    ctx.fillStyle = "#ef4444";
    ctx.beginPath();
    ctx.arc(ox, oy, 5, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "#ef4444";
    ctx.font = "10px DM Sans, sans-serif";
    ctx.textAlign = "left";
    ctx.textBaseline = "bottom";
    ctx.fillText(`operasi u̅=${comb.uBar.toFixed(2)}`, ox + 6, oy - 4);
  }

  ctx.fillStyle = "#1a365d";
  ctx.font = "11px DM Sans, sans-serif";
  ctx.textAlign = "center";
  ctx.fillText("Utilisasi u", padL.l + cW / 2, cssH - 4);

  // --- Bars panel ---
  const n = kg.stations.length;
  const bx0 = mid + padR.l;
  const bW = cssW - mid - padR.l - padR.r;
  const bH = cssH - padR.t - padR.b;
  const groupW = bW / Math.max(n, 1);
  const barW = groupW * 0.32;

  ctx.fillStyle = "#64748b";
  ctx.textAlign = "center";
  ctx.textBaseline = "bottom";
  ctx.fillText("CT per tim", bx0 + bW / 2, padR.t - 8);

  const maxBar = Math.max(
    1,
    ...kg.stations.map((s) =>
      Math.max(
        Number.isFinite(s.ctKingman) ? s.ctKingman : 0,
        s.ctObserved,
      ),
    ),
  );
  const by = (v: number) => padR.t + bH - (v / maxBar) * bH;

  kg.stations.forEach((s, i) => {
    const cx0 = bx0 + groupW * i + groupW / 2;
    const ck = Number.isFinite(s.ctKingman) ? s.ctKingman : maxBar;
    const color = tradeColor(i);

    ctx.fillStyle = color;
    ctx.globalAlpha = 0.85;
    ctx.fillRect(cx0 - barW - 2, by(ck), barW, padR.t + bH - by(ck));
    ctx.globalAlpha = 0.45;
    ctx.fillRect(cx0 + 2, by(s.ctObserved), barW, padR.t + bH - by(s.ctObserved));
    ctx.globalAlpha = 1;

    ctx.fillStyle = "#64748b";
    ctx.font = "10px DM Sans, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    ctx.fillText(`T${i + 1}`, cx0, padR.t + bH + 6);
  });

  // mini legend
  ctx.font = "10px DM Sans, sans-serif";
  ctx.textAlign = "left";
  ctx.fillStyle = "#1a365d";
  ctx.fillRect(bx0, cssH - 16, 10, 3);
  ctx.fillText("Kingman", bx0 + 14, cssH - 18);
  ctx.globalAlpha = 0.45;
  ctx.fillRect(bx0 + 70, cssH - 16, 10, 3);
  ctx.globalAlpha = 1;
  ctx.fillText("Amati", bx0 + 84, cssH - 18);
}

export function buildKingmanLegend(
  result: ParadeResult,
): { color: string; text: string }[] {
  const comb = kingmanCombined(result);
  const kg = kingmanMetrics(result);
  return [
    {
      color: "#ef4444",
      text: `u̅=${comb.uBar.toFixed(3)} · V=${comb.v.toFixed(3)} · CT̅=${Number.isFinite(comb.ct) ? comb.ct.toFixed(2) : "∞"}`,
    },
    {
      color: "#1a365d",
      text: `Σ CT Kingman ${kg.sumCtKingman.toFixed(2)} · CT Little ${kg.systemCtLittle.toFixed(2)}`,
    },
    ...kg.stations.map((s) => ({
      color: tradeColor(s.tradeIndex),
      text: `T${s.tradeIndex + 1} ${shortTradeName(s.name, 10)} u=${s.utilization.toFixed(2)}`,
    })),
  ];
}
