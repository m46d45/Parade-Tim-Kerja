import {
  bufferSeries,
  classroomConfig,
  runParade,
  type ParadeResult,
  type VariabilityLevel,
} from "../core";
import { readDashboard, recordAppSession, recordSimRun } from "../stats";
import { tradeColor } from "../theme";
import {
  buildBufferLegend,
  drawBufferChart,
  hitTestBuffer,
  type BufferHit,
} from "./bufferChart";
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

function renderLegendItems(
  host: HTMLElement,
  items: { color: string; text: string; dashed?: boolean }[],
): void {
  host.replaceChildren();
  for (const item of items) {
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
  const variability = el("select", { id: "var" }, [
    el("option", { value: "none" }, ["Tanpa variability"]),
    el("option", { value: "low" }, ["Sedang (±25%)"]),
    el("option", { value: "medium" }, ["Tinggi (±50%)"]),
  ]);
  (variability as HTMLSelectElement).value = "none";
  const seed = el("input", {
    type: "number",
    id: "seed",
    value: "12345",
    step: "1",
  });
  const runBtn = el("button", { className: "run", type: "button" }, [
    "Jalankan simulasi",
  ]);

  const metrics = el("div", { className: "metrics" });
  const legend = el("div", { className: "legend" });
  const title = el("h2", { id: "chart-title" }, ["Line of Balance"]);

  const tabLob = el("button", { className: "tab active", type: "button", "data-tab": "lob" }, [
    "Line of Balance",
  ]);
  const tabBuf = el("button", { className: "tab", type: "button", "data-tab": "buffer" }, [
    "Buffer / WIP",
  ]);
  const tabs = el("div", { className: "tabs" }, [tabLob, tabBuf]);

  const chartWrap = el("div", { className: "chart-wrap" });
  const canvas = el("canvas", { id: "chart" }) as HTMLCanvasElement;
  const tip = el("div", { className: "tooltip hidden", id: "tip" }, ["—"]);
  chartWrap.append(canvas, tip);

  const note = el("p", { className: "note" }, [
    "Palet Streamlit. Tab Buffer menampilkan WIP antar-tim. Variability memakai seed (ulang = hasil sama di browser). ",
    el(
      "a",
      {
        href: "https://parade-tim-kerja.streamlit.app/",
        target: "_blank",
        rel: "noopener",
      },
      ["Streamlit lengkap"],
    ),
    ".",
  ]);
  const statsLine = el("p", { className: "note", id: "stats" }, [
    "Memuat statistik…",
  ]);

  const chips = el("div", { className: "chips" });
  for (let i = 0; i < 5; i++) {
    const c = el("span", { className: i === 1 ? "chip t2" : "chip" }, [`T${i + 1}`]);
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
    el("label", { for: "speed" }, ["Kapasitas dasar"]),
    speed,
    el("label", { for: "var" }, ["Variability"]),
    variability,
    el("label", { for: "seed" }, ["Seed"]),
    seed,
    runBtn,
    statsLine,
  ]);

  const main = el("section", { className: "panel" }, [
    tabs,
    title,
    metrics,
    legend,
    chartWrap,
    note,
  ]);

  root.append(
    el("div", { className: "wrap" }, [
      el("header", { className: "app-header" }, [
        el("div", { className: "brand" }, ["Parade Tim Kerja"]),
        el("span", { className: "badge" }, ["JS · browser"]),
      ]),
      el("div", { className: "layout" }, [sidebar, main]),
    ]),
  );

  let lastResult: ParadeResult | null = null;
  let activeTab: "lob" | "buffer" = "lob";
  let lobHits: LobHit[] = [];
  let bufHits: BufferHit[] = [];

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

  function setTab(tab: "lob" | "buffer"): void {
    activeTab = tab;
    tabLob.classList.toggle("active", tab === "lob");
    tabBuf.classList.toggle("active", tab === "buffer");
    title.textContent = tab === "lob" ? "Line of Balance" : "Buffer / WIP";
    redraw();
  }

  function redraw(): void {
    if (!lastResult) return;
    tip.classList.add("hidden");
    if (activeTab === "lob") {
      lobHits = drawLobChart(canvas, lastResult);
      bufHits = [];
      renderLegendItems(legend, buildLegendItems(lastResult));
    } else {
      bufHits = drawBufferChart(canvas, lastResult);
      lobHits = [];
      renderLegendItems(legend, buildBufferLegend(lastResult));
    }
  }

  function run(): void {
    const cfg = classroomConfig({
      totalUnits: Math.max(1, Number(zones.value) || 10),
      batchSize: Math.max(1, Number(batch.value) || 4),
      baseSpeed: Number(speed.value) || 1,
      seed: Number(seed.value) || 12345,
      variability: (variability as HTMLSelectElement).value as VariabilityLevel,
    });
    lastResult = runParade(cfg);
    setMetrics(lastResult);
    redraw();
    void recordSimRun();
  }

  function showTip(
    titleText: string,
    color: string,
    lines: string[],
    ev: MouseEvent,
  ): void {
    tip.classList.remove("hidden");
    tip.replaceChildren();
    const row1 = el("div", { className: "tip-title" }, [titleText]);
    row1.style.color = color;
    tip.append(row1, ...lines.map((t) => el("div", {}, [t])));
    const wrapRect = chartWrap.getBoundingClientRect();
    const x = ev.clientX - wrapRect.left + 12;
    const y = ev.clientY - wrapRect.top + 12;
    tip.style.left = `${Math.min(x, wrapRect.width - 180)}px`;
    tip.style.top = `${Math.min(y, wrapRect.height - 70)}px`;
  }

  canvas.addEventListener("mousemove", (ev) => {
    if (activeTab === "lob") {
      const hit = hitTestLob(canvas, lobHits, ev.clientX, ev.clientY);
      if (!hit) {
        tip.classList.add("hidden");
        canvas.style.cursor = "default";
        return;
      }
      canvas.style.cursor = "crosshair";
      showTip(hit.label, hit.color, [
        `Periode: ${hit.period}`,
        `Zona kumulatif: ${hit.zone}`,
      ], ev);
      return;
    }
    const hit = hitTestBuffer(canvas, bufHits, ev.clientX, ev.clientY);
    if (!hit) {
      tip.classList.add("hidden");
      canvas.style.cursor = "default";
      return;
    }
    canvas.style.cursor = "crosshair";
    showTip(hit.label, hit.color, [
      `Periode: ${hit.period}`,
      `WIP: ${hit.wip} zona`,
    ], ev);
  });
  canvas.addEventListener("mouseleave", () => tip.classList.add("hidden"));

  tabLob.addEventListener("click", () => setTab("lob"));
  tabBuf.addEventListener("click", () => setTab("buffer"));
  runBtn.addEventListener("click", run);
  window.addEventListener("resize", () => redraw());

  void (async () => {
    await recordAppSession();
    const dash = await readDashboard();
    statsLine.textContent = `Statistik (Counter): sim_runs=${dash.sim_runs ?? 0} · app_sessions=${dash.app_sessions ?? 0}`;
  })();

  run();
}
