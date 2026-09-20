import {
  bufferSeries,
  classroomConfig,
  cumulativeSeries,
  runParade,
  type ParadeResult,
} from "../core";
import { readDashboard, recordAppSession, recordSimRun } from "../stats";

const TRADE_COLORS = ["#2563eb", "#eab308", "#16a34a", "#dc2626", "#7c3aed"];

function el<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  attrs: Record<string, string> = {},
  children: (Node | string)[] = [],
): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "className") node.className = v;
    else node.setAttribute(k, v);
  }
  for (const c of children) {
    node.append(typeof c === "string" ? document.createTextNode(c) : c);
  }
  return node;
}

function drawLob(canvas: HTMLCanvasElement, result: ParadeResult): void {
  const dpr = window.devicePixelRatio || 1;
  const cssW = canvas.clientWidth || 640;
  const cssH = 320;
  canvas.width = Math.floor(cssW * dpr);
  canvas.height = Math.floor(cssH * dpr);
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  ctx.scale(dpr, dpr);

  const pad = { l: 44, r: 16, t: 16, b: 36 };
  const w = cssW - pad.l - pad.r;
  const h = cssH - pad.t - pad.b;
  const cum = cumulativeSeries(result);
  const maxX = Math.max(result.duration, result.idealLastTradeCumulative.length - 1, 1);
  const maxY = result.config.totalUnits;

  const xScale = (x: number) => pad.l + (x / maxX) * w;
  const yScale = (y: number) => pad.t + h - (y / maxY) * h;

  ctx.clearRect(0, 0, cssW, cssH);
  ctx.fillStyle = "rgba(255,255,255,0.04)";
  ctx.fillRect(0, 0, cssW, cssH);

  // grid Y (integer zones)
  ctx.strokeStyle = "rgba(148,163,184,0.25)";
  ctx.lineWidth = 1;
  for (let z = 0; z <= maxY; z++) {
    const yy = yScale(z);
    ctx.beginPath();
    ctx.moveTo(pad.l, yy);
    ctx.lineTo(pad.l + w, yy);
    ctx.stroke();
  }

  // ideal last trade
  const ideal = result.idealLastTradeCumulative;
  if (ideal.length > 1) {
    ctx.strokeStyle = "rgba(226,232,240,0.55)";
    ctx.setLineDash([5, 4]);
    ctx.beginPath();
    ideal.forEach((y: number, i: number) => {
      const X = xScale(i);
      const Y = yScale(y);
      if (i === 0) ctx.moveTo(X, Y);
      else ctx.lineTo(X, Y);
    });
    ctx.stroke();
    ctx.setLineDash([]);
  }

  // trades
  cum.forEach((series: number[], ti: number) => {
    ctx.strokeStyle = TRADE_COLORS[ti % TRADE_COLORS.length];
    ctx.lineWidth = 2.2;
    ctx.beginPath();
    series.forEach((y: number, i: number) => {
      const X = xScale(i);
      const Y = yScale(y);
      if (i === 0) ctx.moveTo(X, Y);
      else ctx.lineTo(X, Y);
    });
    ctx.stroke();
  });

  ctx.fillStyle = "#94a3b8";
  ctx.font = "12px DM Sans, sans-serif";
  ctx.fillText("Periode (0 = awal)", pad.l, cssH - 10);
  ctx.save();
  ctx.translate(14, pad.t + h / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText("Zona kumulatif (diskrit)", 0, 0);
  ctx.restore();
}

export function mountApp(root: HTMLElement): void {
  root.replaceChildren();

  const zones = el("input", { type: "number", id: "zones", value: "10", min: "1", max: "100" });
  const batch = el("select", { id: "batch" }, [
    el("option", { value: "1" }, ["1 — one-piece flow"]),
    el("option", { value: "4" }, ["4 — batch handoff"]),
  ]);
  (batch as HTMLSelectElement).value = "4";
  const speed = el("select", { id: "speed" }, [
    el("option", { value: "0.5" }, ["0.5 zona/periode"]),
    el("option", { value: "1" }, ["1 zona/periode"]),
    el("option", { value: "2" }, ["2 zona/periode"]),
  ]);
  (speed as HTMLSelectElement).value = "1";
  const runBtn = el("button", { className: "run", type: "button" }, ["Jalankan simulasi"]);
  const metrics = el("div", { className: "metrics" });
  const canvas = el("canvas", { id: "lob" }) as HTMLCanvasElement;
  const note = el("p", { className: "note" }, [
    "Prototype migrasi JS (Fase 1–2). Engine zone-flow di browser. ",
    el("a", { href: "https://parade-tim-kerja.streamlit.app/", target: "_blank", rel: "noopener" }, [
      "Streamlit lengkap",
    ]),
    " tetap tersedia selama cutover.",
  ]);
  const statsLine = el("p", { className: "note", id: "stats" }, ["Memuat statistik…"]);

  const sidebar = el("aside", { className: "panel" }, [
    el("h2", {}, ["Kontrol"]),
    el("label", { for: "zones" }, ["Total zona"]),
    zones,
    el("label", { for: "batch" }, ["Batch handoff"]),
    batch,
    el("label", { for: "speed" }, ["Kapasitas (tanpa var)"]),
    speed,
    runBtn,
    statsLine,
  ]);

  const main = el("section", { className: "panel" }, [
    el("h2", {}, ["Line of Balance"]),
    metrics,
    canvas,
    note,
  ]);

  root.append(
    el("div", { className: "wrap" }, [
      el("header", {}, [
        el("div", { className: "brand" }, ["Parade Tim Kerja"]),
        el("span", { className: "badge" }, ["JS · browser"]),
      ]),
      el("div", { className: "layout" }, [sidebar, main]),
    ]),
  );

  function setMetrics(r: ParadeResult): void {
    const buf = bufferSeries(r);
    const peak = buf.length
      ? Math.max(
          ...buf[0].map((_: number, t: number) =>
            buf.reduce((s: number, series: number[]) => s + series[t], 0),
          ),
        )
      : 0;
    metrics.replaceChildren(
      metric("Durasi", String(r.duration)),
      metric("Ideal (tanpa var)", String(r.idealDuration)),
      metric("Delay", String(r.duration - r.idealDuration)),
      metric("Peak WIP", String(peak)),
    );
  }

  function metric(label: string, value: string): HTMLElement {
    return el("div", { className: "metric" }, [
      el("span", {}, [label]),
      el("strong", {}, [value]),
    ]);
  }

  function run(): void {
    const cfg = classroomConfig({
      totalUnits: Math.max(1, Number(zones.value) || 10),
      batchSize: Math.max(1, Number(batch.value) || 4),
      baseSpeed: Number(speed.value) || 1,
      seed: 12345,
      deterministic: true,
    });
    const result = runParade(cfg);
    setMetrics(result);
    drawLob(canvas, result);
    void recordSimRun();
  }

  runBtn.addEventListener("click", run);
  window.addEventListener("resize", () => {
    // redraw last if any — simple: re-run with same inputs
  });

  void (async () => {
    await recordAppSession();
    const dash = await readDashboard();
    statsLine.textContent = `Statistik (Counter): sim_runs=${dash.sim_runs ?? 0} · app_sessions=${dash.app_sessions ?? 0}`;
  })();

  run();
}
