import {
  bufferSeries,
  classroomConfig,
  computeCostMetrics,
  runParade,
  type CostMetrics,
  type ParadeResult,
  type VariabilityLevel,
} from "../core";
import { readDashboard, recordAppSession, recordSimRun } from "../stats";
import { shortTradeName, tradeColor } from "../theme";
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
import { buildUtilLegend, drawUtilChart } from "./utilChart";

type TabId = "lob" | "buffer" | "util" | "cost";

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

function fmtNum(n: number): string {
  return Math.round(n).toLocaleString("id-ID");
}

function renderCostTable(host: HTMLElement, cm: CostMetrics): void {
  host.replaceChildren();
  const table = el("table", { className: "data-table" });
  const thead = el("thead");
  thead.append(
    el("tr", {}, [
      el("th", {}, ["Tim"]),
      el("th", {}, ["Tarif"]),
      el("th", {}, ["Aktif"]),
      el("th", {}, ["Idle"]),
      el("th", {}, ["Biaya aktif"]),
      el("th", {}, ["Biaya idle"]),
      el("th", {}, ["Total"]),
    ]),
  );
  const tbody = el("tbody");
  for (const t of cm.trades) {
    tbody.append(
      el("tr", {}, [
        el("td", {}, [
          el("span", { className: "row-swatch" }, []),
          `T${t.tradeIndex + 1}: ${shortTradeName(t.name, 16)}`,
        ]),
        el("td", {}, [fmtNum(t.costPerPeriod)]),
        el("td", {}, [String(t.periodsActive)]),
        el("td", {}, [String(t.periodsIdle)]),
        el("td", {}, [fmtNum(t.costActive)]),
        el("td", {}, [fmtNum(t.costIdle)]),
        el("td", {}, [fmtNum(t.costTotal)]),
      ]),
    );
    const sw = tbody.lastElementChild?.querySelector(".row-swatch") as HTMLElement | null;
    if (sw) sw.style.background = tradeColor(t.tradeIndex);
  }
  table.append(thead, tbody);
  host.append(table);
  host.append(
    el("p", { className: "note table-note" }, [
      "Aktif = periode berproduksi setelah mulai · Idle = menunggu zona · Biaya = periode × tarif.",
    ]),
  );
}

function renderUtilTable(host: HTMLElement, result: ParadeResult): void {
  host.replaceChildren();
  const table = el("table", { className: "data-table" });
  const thead = el("thead");
  thead.append(
    el("tr", {}, [
      el("th", {}, ["Tim"]),
      el("th", {}, ["Produksi"]),
      el("th", {}, ["Idle"]),
      el("th", {}, ["Utilisasi"]),
    ]),
  );
  const tbody = el("tbody");
  for (let i = 0; i < result.tradeMetrics.length; i++) {
    const m = result.tradeMetrics[i];
    tbody.append(
      el("tr", {}, [
        el("td", {}, [
          el("span", { className: "row-swatch" }, []),
          `T${i + 1}: ${shortTradeName(m.name, 18)}`,
        ]),
        el("td", {}, [String(m.totalProduction)]),
        el("td", {}, [String(m.totalIdle)]),
        el("td", {}, [`${(100 * m.utilization).toFixed(1)}%`]),
      ]),
    );
    const sw = tbody.lastElementChild?.querySelector(".row-swatch") as HTMLElement | null;
    if (sw) sw.style.background = tradeColor(i);
  }
  table.append(thead, tbody);
  host.append(table);
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
  const tarif = el("input", {
    type: "number",
    id: "tarif",
    value: "100",
    min: "0",
    step: "10",
  });
  const runBtn = el("button", { className: "run", type: "button" }, [
    "Jalankan simulasi",
  ]);

  const metrics = el("div", { className: "metrics" });
  const legend = el("div", { className: "legend" });
  const title = el("h2", { id: "chart-title" }, ["Line of Balance"]);
  const tableHost = el("div", { className: "table-host hidden" });

  const tabDefs: { id: TabId; label: string }[] = [
    { id: "lob", label: "Line of Balance" },
    { id: "buffer", label: "Buffer / WIP" },
    { id: "util", label: "Utilisasi" },
    { id: "cost", label: "Biaya" },
  ];
  const tabBtns = new Map<TabId, HTMLButtonElement>();
  const tabs = el("div", { className: "tabs" });
  for (const t of tabDefs) {
    const btn = el(
      "button",
      {
        className: t.id === "lob" ? "tab active" : "tab",
        type: "button",
        "data-tab": t.id,
      },
      [t.label],
    ) as HTMLButtonElement;
    tabBtns.set(t.id, btn);
    tabs.append(btn);
  }

  const chartWrap = el("div", { className: "chart-wrap" });
  const canvas = el("canvas", { id: "chart" }) as HTMLCanvasElement;
  const tip = el("div", { className: "tooltip hidden", id: "tip" }, ["—"]);
  chartWrap.append(canvas, tip);

  const note = el("p", { className: "note" }, [
    "Palet Streamlit. Utilisasi & biaya mengikuti rumus Streamlit (aktif/idle × tarif). ",
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
    el("label", { for: "tarif" }, ["Tarif / periode (semua tim)"]),
    tarif,
    runBtn,
    statsLine,
  ]);

  const main = el("section", { className: "panel" }, [
    tabs,
    title,
    metrics,
    legend,
    chartWrap,
    tableHost,
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
  let lastCost: CostMetrics | null = null;
  let activeTab: TabId = "lob";
  let lobHits: LobHit[] = [];
  let bufHits: BufferHit[] = [];

  function rates(): number[] {
    const rate = Math.max(0, Number(tarif.value) || 100);
    return Array(5).fill(rate);
  }

  function setMetrics(r: ParadeResult, cm: CostMetrics): void {
    const buf = bufferSeries(r);
    const peak = buf.length
      ? Math.max(
          ...buf[0].map((_: number, t: number) =>
            buf.reduce((s: number, series: number[]) => s + series[t], 0),
          ),
        )
      : 0;
    const avgUtil =
      r.tradeMetrics.reduce((s, m) => s + m.utilization, 0) /
      Math.max(r.tradeMetrics.length, 1);

    if (activeTab === "cost") {
      metrics.replaceChildren(
        metric("Biaya aktif", fmtNum(cm.totalActive)),
        metric("Biaya idle", fmtNum(cm.totalIdle)),
        metric("Total biaya", fmtNum(cm.totalCost)),
        metric("Σ idle periode", String(cm.trades.reduce((s, t) => s + t.periodsIdle, 0))),
      );
      return;
    }
    if (activeTab === "util") {
      metrics.replaceChildren(
        metric("Utilisasi ⌀", `${(100 * avgUtil).toFixed(1)}%`),
        metric("Idle kapasitas", String(r.totalIdleCapacity)),
        metric("Throughput", r.systemThroughput.toFixed(3)),
        metric("Peak WIP", String(peak)),
      );
      return;
    }
    metrics.replaceChildren(
      metric("Durasi", String(r.duration)),
      metric("Ideal (tanpa var)", String(r.idealDuration)),
      metric("Delay", String(r.duration - r.idealDuration)),
      metric("Peak WIP", String(peak)),
    );
  }

  const titles: Record<TabId, string> = {
    lob: "Line of Balance",
    buffer: "Buffer / WIP",
    util: "Utilisasi",
    cost: "Biaya",
  };

  function setTab(tab: TabId): void {
    activeTab = tab;
    for (const [id, btn] of tabBtns) {
      btn.classList.toggle("active", id === tab);
    }
    title.textContent = titles[tab];
    if (lastResult && lastCost) setMetrics(lastResult, lastCost);
    redraw();
  }

  function redraw(): void {
    if (!lastResult || !lastCost) return;
    tip.classList.add("hidden");
    lobHits = [];
    bufHits = [];
    const showCanvas = activeTab === "lob" || activeTab === "buffer" || activeTab === "util";
    chartWrap.classList.toggle("hidden", !showCanvas && activeTab === "cost");
    // Cost still shows a small stacked summary via canvas? Use table only for cost.
    if (activeTab === "cost") {
      chartWrap.classList.add("hidden");
      tableHost.classList.remove("hidden");
      legend.replaceChildren();
      renderCostTable(tableHost, lastCost);
      return;
    }
    chartWrap.classList.remove("hidden");
    if (activeTab === "util") {
      tableHost.classList.remove("hidden");
      drawUtilChart(canvas, lastResult);
      renderLegendItems(legend, buildUtilLegend(lastResult));
      renderUtilTable(tableHost, lastResult);
      return;
    }
    tableHost.classList.add("hidden");
    tableHost.replaceChildren();
    if (activeTab === "lob") {
      lobHits = drawLobChart(canvas, lastResult);
      renderLegendItems(legend, buildLegendItems(lastResult));
    } else {
      bufHits = drawBufferChart(canvas, lastResult);
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
    lastCost = computeCostMetrics(lastResult, rates());
    setMetrics(lastResult, lastCost);
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
    if (activeTab === "buffer") {
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
      return;
    }
    tip.classList.add("hidden");
    canvas.style.cursor = "default";
  });
  canvas.addEventListener("mouseleave", () => tip.classList.add("hidden"));

  for (const [id, btn] of tabBtns) {
    btn.addEventListener("click", () => setTab(id));
  }
  runBtn.addEventListener("click", run);
  tarif.addEventListener("change", () => {
    if (!lastResult) return;
    lastCost = computeCostMetrics(lastResult, rates());
    setMetrics(lastResult, lastCost);
    if (activeTab === "cost") redraw();
  });
  window.addEventListener("resize", () => redraw());

  void (async () => {
    await recordAppSession();
    const dash = await readDashboard();
    statsLine.textContent = `Statistik (Counter): sim_runs=${dash.sim_runs ?? 0} · app_sessions=${dash.app_sessions ?? 0}`;
  })();

  run();
}
