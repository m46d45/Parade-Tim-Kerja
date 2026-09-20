import {
  bufferSeries,
  classroomConfig,
  runParade,
  type ParadeResult,
} from "../core";
import { readDashboard, recordAppSession, recordSimRun } from "../stats";
import { tradeColor } from "../theme";
import {
  buildLegendItems,
  drawLobChart,
  hitTestLob,
  type LobHit,
} from "./lobChart";

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

function metric(label: string, value: string): HTMLElement {
  return el("div", { className: "metric" }, [
    el("span", {}, [label]),
    el("strong", {}, [value]),
  ]);
}

function renderLegend(host: HTMLElement, result: ParadeResult): void {
  host.replaceChildren();
  for (const item of buildLegendItems(result)) {
    const swatch = el("span", {
      className: item.dashed ? "swatch dashed" : "swatch",
    });
    swatch.style.setProperty("--sw", item.color);
    host.append(
      el("div", { className: "legend-item" }, [swatch, el("span", {}, [item.text])]),
    );
  }
}

export function mountApp(root: HTMLElement): void {
  root.replaceChildren();

  const zones = el("input", {
    type: "number",
    id: "zones",
    value: "10",
    min: "1",
    max: "100",
  });
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
  const runBtn = el("button", { className: "run", type: "button" }, [
    "Jalankan simulasi",
  ]);
  const metrics = el("div", { className: "metrics" });
  const legend = el("div", { className: "legend" });
  const chartWrap = el("div", { className: "chart-wrap" });
  const canvas = el("canvas", { id: "lob" }) as HTMLCanvasElement;
  const tip = el("div", { className: "tooltip hidden", id: "tip" }, ["—"]);
  chartWrap.append(canvas, tip);

  const note = el("p", { className: "note" }, [
    "Warna T1–T5 sama dengan grafik Streamlit. Arahkan kursor ke titik untuk lihat periode & zona. ",
    el(
      "a",
      {
        href: "https://parade-tim-kerja.streamlit.app/",
        target: "_blank",
        rel: "noopener",
      },
      ["Streamlit lengkap"],
    ),
    " tetap tersedia selama migrasi.",
  ]);
  const statsLine = el("p", { className: "note", id: "stats" }, [
    "Memuat statistik…",
  ]);

  // Color chips matching Streamlit palette
  const chips = el("div", { className: "chips" });
  for (let i = 0; i < 5; i++) {
    const c = el("span", { className: "chip" }, [`T${i + 1}`]);
    c.style.background = tradeColor(i);
    chips.append(c);
  }

  const sidebar = el("aside", { className: "panel" }, [
    el("h2", {}, ["Kontrol"]),
    chips,
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
    legend,
    chartWrap,
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

  let lastResult: ParadeResult | null = null;
  let hits: LobHit[] = [];

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

  function redraw(): void {
    if (!lastResult) return;
    hits = drawLobChart(canvas, lastResult);
    renderLegend(legend, lastResult);
  }

  function run(): void {
    const cfg = classroomConfig({
      totalUnits: Math.max(1, Number(zones.value) || 10),
      batchSize: Math.max(1, Number(batch.value) || 4),
      baseSpeed: Number(speed.value) || 1,
      seed: 12345,
      deterministic: true,
    });
    lastResult = runParade(cfg);
    setMetrics(lastResult);
    redraw();
    void recordSimRun();
  }

  canvas.addEventListener("mousemove", (ev) => {
    const hit = hitTestLob(canvas, hits, ev.clientX, ev.clientY);
    if (!hit) {
      tip.classList.add("hidden");
      canvas.style.cursor = "default";
      return;
    }
    canvas.style.cursor = "crosshair";
    tip.classList.remove("hidden");
    tip.replaceChildren();
    const row1 = el("div", { className: "tip-title" }, [hit.label]);
    row1.style.color = hit.color;
    tip.append(
      row1,
      el("div", {}, [`Periode: ${hit.period}`]),
      el("div", {}, [`Zona kumulatif: ${hit.zone}`]),
    );
    const wrapRect = chartWrap.getBoundingClientRect();
    const x = ev.clientX - wrapRect.left + 12;
    const y = ev.clientY - wrapRect.top + 12;
    tip.style.left = `${Math.min(x, wrapRect.width - 180)}px`;
    tip.style.top = `${Math.min(y, wrapRect.height - 70)}px`;
  });
  canvas.addEventListener("mouseleave", () => tip.classList.add("hidden"));

  runBtn.addEventListener("click", run);
  window.addEventListener("resize", () => redraw());

  void (async () => {
    await recordAppSession();
    const dash = await readDashboard();
    statsLine.textContent = `Statistik (Counter): sim_runs=${dash.sim_runs ?? 0} · app_sessions=${dash.app_sessions ?? 0}`;
  })();

  run();
}
