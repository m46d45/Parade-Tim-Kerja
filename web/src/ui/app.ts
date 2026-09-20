import {
  bufferSeries,
  classroomConfig,
  computeCostMetrics,
  DEFAULT_TRADE_NAMES,
  evaluateAtWip,
  inventoryFillRateMetrics,
  kingmanCombined,
  kingmanMetrics,
  littlesLawMetrics,
  littlesOperationsCurve,
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
  drawBufferStackedChart,
  hitTestBuffer,
  type BufferHit,
} from "./bufferChart";
import {
  downloadCanvasPng,
  downloadText,
  resultWorkbookCsv,
} from "./download";
import { buildInventoryLegend, drawInventoryChart } from "./inventoryChart";
import { buildKingmanLegend, drawKingmanChart } from "./kingmanChart";
import {
  buildLegendItems,
  drawLobChart,
  hitTestLob,
  type LobHit,
} from "./lobChart";
import { buildLittlesLegend, drawLittlesChart } from "./littlesChart";
import { drawOperationsChart, snapConwip } from "./operationsChart";
import { buildUtilLegend, drawUtilChart } from "./utilChart";
import { mountCompare } from "./compareApp";
import { mountManual } from "./manualApp";
import { bumpSessionRuns, mountStats } from "./statsApp";
import { mountTakt } from "./taktApp";
import { mountTimeBuffer } from "./timeBufferApp";

function fileStamp(): string {
  const d = new Date();
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}`;
}

type TabId =
  | "lob"
  | "buffer"
  | "util_cost"
  | "little"
  | "kingman"
  | "inventory";

type AppMode = "sim" | "compare" | "takt" | "buffer" | "stats" | "manual";

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

function fmtF(n: number, d = 2): string {
  if (!Number.isFinite(n)) return "∞";
  return n.toFixed(d);
}

function paintSwatches(tbody: HTMLElement): void {
  tbody.querySelectorAll("tr").forEach((tr, i) => {
    const sw = tr.querySelector(".row-swatch") as HTMLElement | null;
    if (sw) sw.style.background = tradeColor(i);
  });
}

function renderUtilCostTables(
  host: HTMLElement,
  result: ParadeResult,
  cm: CostMetrics,
): void {
  host.replaceChildren();
  const utilTable = el("table", { className: "data-table" });
  utilTable.append(
    el("thead", {}, [
      el("tr", {}, [
        el("th", {}, ["Tim"]),
        el("th", {}, ["Produksi"]),
        el("th", {}, ["Kap. efektif"]),
        el("th", {}, ["Idle kap."]),
        el("th", {}, ["Utilisasi"]),
        el("th", {}, ["Mulai"]),
        el("th", {}, ["Selesai"]),
      ]),
    ]),
  );
  const utilBody = el("tbody");
  for (let i = 0; i < result.tradeMetrics.length; i++) {
    const m = result.tradeMetrics[i];
    utilBody.append(
      el("tr", {}, [
        el("td", {}, [
          el("span", { className: "row-swatch" }, []),
          `T${i + 1}: ${shortTradeName(m.name, 16)}`,
        ]),
        el("td", {}, [String(m.totalProduction)]),
        el("td", {}, [String(m.totalEffectiveCapacity)]),
        el("td", {}, [String(m.totalIdle)]),
        el("td", {}, [`${(100 * m.utilization).toFixed(1)}%`]),
        el("td", {}, [m.startPeriod == null ? "—" : String(m.startPeriod)]),
        el("td", {}, [String(m.periodsToFinish)]),
      ]),
    );
  }
  paintSwatches(utilBody);
  utilTable.append(utilBody);

  const costTable = el("table", { className: "data-table" });
  costTable.append(
    el("thead", {}, [
      el("tr", {}, [
        el("th", {}, ["Tim"]),
        el("th", {}, ["Tarif"]),
        el("th", {}, ["Aktif"]),
        el("th", {}, ["Idle"]),
        el("th", {}, ["Biaya aktif"]),
        el("th", {}, ["Biaya idle"]),
        el("th", {}, ["Total"]),
      ]),
    ]),
  );
  const costBody = el("tbody");
  for (const t of cm.trades) {
    costBody.append(
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
  }
  paintSwatches(costBody);
  costTable.append(costBody);

  host.append(
    el("h3", { className: "subchart-title" }, ["Utilisasi per tim"]),
    utilTable,
    el("h3", { className: "subchart-title" }, ["Biaya per tim"]),
    costTable,
    el("p", { className: "note table-note" }, [
      "Aktif = periode berproduksi setelah mulai · Idle = menunggu zona · Biaya = periode × tarif.",
    ]),
  );
}

function renderBufferPeakTable(host: HTMLElement, result: ParadeResult): void {
  host.replaceChildren();
  const table = el("table", { className: "data-table" });
  table.append(
    el("thead", {}, [
      el("tr", {}, [el("th", {}, ["Buffer"]), el("th", {}, ["Puncak WIP"])]),
    ]),
  );
  const tbody = el("tbody");
  result.config.trades.slice(0, -1).forEach((t, j) => {
    const down = result.config.trades[j + 1];
    tbody.append(
      el("tr", {}, [
        el("td", {}, [
          el("span", { className: "row-swatch" }, []),
          `B${j + 1}: ${shortTradeName(t.name, 12)} → ${shortTradeName(down.name, 12)}`,
        ]),
        el("td", {}, [String(result.maxBuffer[j] ?? 0)]),
      ]),
    );
  });
  paintSwatches(tbody);
  table.append(tbody);
  host.append(table);
}

function renderLittlesTable(host: HTMLElement, result: ParadeResult): void {
  const ll = littlesLawMetrics(result);
  host.replaceChildren();
  const rows: [string, string, string][] = [
    ["Throughput (TH)", fmtF(ll.throughput, 3), "zona / periode"],
    ["WIP pipeline ⌀", fmtF(ll.avgPipelineWip), "zona · T1−T5"],
    ["WIP buffer ⌀", fmtF(ll.avgBufferWip), "zona · Σ buffer"],
    ["CT pipeline", fmtF(ll.cycleTimePipeline), "periode · WIP÷TH"],
    ["CT buffer", fmtF(ll.cycleTimeBuffer), "periode"],
    ["TH × CT (cek)", fmtF(ll.checkPipeline), "≈ WIP pipeline"],
    ["WIP puncak pipeline", fmtF(ll.peakPipelineWip), "zona"],
    ["WIP puncak buffer", fmtF(ll.peakBufferWip), "zona"],
  ];
  const table = el("table", { className: "data-table" });
  table.append(
    el("thead", {}, [
      el("tr", {}, [
        el("th", {}, ["Metrik"]),
        el("th", {}, ["Nilai"]),
        el("th", {}, ["Keterangan"]),
      ]),
    ]),
  );
  const tbody = el("tbody");
  for (const [a, b, c] of rows) {
    tbody.append(el("tr", {}, [el("td", {}, [a]), el("td", {}, [b]), el("td", {}, [c])]));
  }
  table.append(tbody);
  host.append(table);
}

function renderKingmanTable(host: HTMLElement, result: ParadeResult): void {
  const kg = kingmanMetrics(result);
  host.replaceChildren();
  const table = el("table", { className: "data-table" });
  table.append(
    el("thead", {}, [
      el("tr", {}, [
        el("th", {}, ["Tim"]),
        el("th", {}, ["u"]),
        el("th", {}, ["tₑ"]),
        el("th", {}, ["cₑ"]),
        el("th", {}, ["cₐ"]),
        el("th", {}, ["V"]),
        el("th", {}, ["U"]),
        el("th", {}, ["Wait"]),
        el("th", {}, ["CT Kingman"]),
        el("th", {}, ["CT amati"]),
      ]),
    ]),
  );
  const tbody = el("tbody");
  for (const s of kg.stations) {
    tbody.append(
      el("tr", {}, [
        el("td", {}, [
          el("span", { className: "row-swatch" }, []),
          `T${s.tradeIndex + 1}: ${shortTradeName(s.name, 12)}`,
        ]),
        el("td", {}, [fmtF(s.utilization, 3)]),
        el("td", {}, [fmtF(s.tE, 3)]),
        el("td", {}, [fmtF(s.cE, 3)]),
        el("td", {}, [fmtF(s.cA, 3)]),
        el("td", {}, [fmtF(s.vFactor, 3)]),
        el("td", {}, [fmtF(s.uFactor, 3)]),
        el("td", {}, [fmtF(s.waitKingman)]),
        el("td", {}, [fmtF(s.ctKingman)]),
        el("td", {}, [fmtF(s.ctObserved)]),
      ]),
    );
  }
  paintSwatches(tbody);
  table.append(tbody);
  host.append(table);
  host.append(el("p", { className: "note table-note" }, [kg.note]));
}

function renderInventoryTable(host: HTMLElement, result: ParadeResult): void {
  const fr = inventoryFillRateMetrics(result);
  host.replaceChildren();
  const table = el("table", { className: "data-table" });
  table.append(
    el("thead", {}, [
      el("tr", {}, [
        el("th", {}, ["Buffer"]),
        el("th", {}, ["Dari"]),
        el("th", {}, ["Ke"]),
        el("th", {}, ["Inventory ⌀"]),
        el("th", {}, ["Puncak"]),
        el("th", {}, ["Fill rate %"]),
        el("th", {}, ["Idle hilir"]),
      ]),
    ]),
  );
  const tbody = el("tbody");
  fr.interfaces.forEach((row) => {
    tbody.append(
      el("tr", {}, [
        el("td", {}, [el("span", { className: "row-swatch" }, []), row.buffer]),
        el("td", {}, [shortTradeName(row.from, 16)]),
        el("td", {}, [shortTradeName(row.to, 16)]),
        el("td", {}, [fmtF(row.avgInventory, 3)]),
        el("td", {}, [String(row.peakInventory)]),
        el("td", {}, [fmtF(100 * row.fillRate, 1)]),
        el("td", {}, [String(row.downstreamIdle)]),
      ]),
    );
  });
  paintSwatches(tbody);
  table.append(tbody);
  host.append(table);
  host.append(
    el("p", { className: "note table-note" }, [
      "Fill rate ≈ produksi / (produksi+idle) tim hilir. Kurva = base-stock teoritis.",
    ]),
  );
}

export function mountApp(root: HTMLElement): void {
  root.replaceChildren();

  const zones = el("input", {
    type: "range",
    id: "zones",
    min: "1",
    max: "40",
    step: "1",
    value: "10",
  }) as HTMLInputElement;
  const zonesVal = el("span", { className: "slider-val" }, ["10"]);
  const batch = el("select", { id: "batch" }, [
    el("option", { value: "4" }, ["4 — tiap 4 zona (standar)"]),
    el("option", { value: "5" }, ["5 — tiap 5 zona"]),
    el("option", { value: "3" }, ["3 — tiap 3 zona"]),
    el("option", { value: "2" }, ["2 — tiap 2 zona"]),
    el("option", { value: "1" }, ["1 — one-piece flow"]),
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
    el("option", { value: "low" }, ["Rendah (±25%)"]),
    el("option", { value: "medium" }, ["Sedang (±50%)"]),
    el("option", { value: "high" }, ["Tinggi (±75%)"]),
    el("option", { value: "very_high" }, ["Sangat tinggi (±90%)"]),
  ]);
  (variability as HTMLSelectElement).value = "none";
  const seed = el("input", { type: "number", id: "seed", value: "12345", step: "1" });

  const tarifSliders: HTMLInputElement[] = [];
  const tarifVals: HTMLElement[] = [];
  const tarifBlock = el("div", { className: "tarif-block" }, [
    el("label", {}, ["Tarif / periode per tim"]),
    el("p", { className: "note sidebar-note" }, [
      "Biaya = (periode aktif + idle) × tarif, per tim.",
    ]),
  ]);
  for (let i = 0; i < 5; i++) {
    const slider = el("input", {
      type: "range",
      id: `tarif-t${i + 1}`,
      min: "0",
      max: "500",
      step: "10",
      value: "100",
    }) as HTMLInputElement;
    const val = el("span", { className: "slider-val" }, ["100"]);
    tarifSliders.push(slider);
    tarifVals.push(val);
    const row = el("div", { className: "slider-row" }, [
      el("span", { className: "slider-label", title: `T${i + 1} ${DEFAULT_TRADE_NAMES[i]}` }, [
        DEFAULT_TRADE_NAMES[i],
      ]),
      slider,
      val,
    ]);
    const sw = row.querySelector(".slider-label") as HTMLElement;
    sw.style.color = tradeColor(i);
    tarifBlock.append(row);
  }

  const runBtn = el("button", { className: "run", type: "button" }, ["Jalankan simulasi"]);

  const metrics = el("div", { className: "metrics" });
  const metrics2 = el("div", { className: "metrics hidden" });
  const legend = el("div", { className: "legend" });
  const title = el("h2", { id: "chart-title" }, ["Location-based Schedule"]);
  const tableHost = el("div", { className: "table-host hidden" });
  const littleControls = el("div", { className: "little-controls hidden" });
  const conwipLabel = el("label", { for: "conwip" }, ["CONWIP — batas WIP konstan"]);
  const conwip = el("input", {
    type: "range",
    id: "conwip",
    min: "0.5",
    max: "40",
    step: "0.5",
    value: "5",
  }) as HTMLInputElement;
  const conwipVal = el("span", { className: "conwip-val" }, ["5.0"]);
  const conwipPred = el("div", { className: "metrics conwip-pred" });
  const conwipCaption = el("p", { className: "note" }, [""]);
  littleControls.append(
    conwipLabel,
    el("div", { className: "conwip-row" }, [conwip, conwipVal]),
    conwipPred,
    conwipCaption,
  );

  const tabDefs: { id: TabId; label: string }[] = [
    { id: "lob", label: "Location-based Schedule" },
    { id: "buffer", label: "Buffer / WIP" },
    { id: "util_cost", label: "Utilisasi & Biaya" },
    { id: "little", label: "Little's Law" },
    { id: "kingman", label: "Kingman" },
    { id: "inventory", label: "Inventory / FR" },
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

  const chartWrap2 = el("div", { className: "chart-wrap hidden" });
  const canvas2 = el("canvas", { id: "chart2" }) as HTMLCanvasElement;
  const subTitle = el("h3", { className: "subchart-title hidden" }, [""]);
  chartWrap2.append(canvas2);

  const note = el("p", { className: "note" }, [
    "Parity Streamlit: Simulasi, Perbandingan, Takt plan, Buffer waktu–inventory, Statistik, Manual. ",
    el(
      "a",
      {
        href: "https://parade-tim-kerja.streamlit.app/",
        target: "_blank",
        rel: "noopener",
      },
      ["Streamlit (jaring pengaman)"],
    ),
    " · cutover Vercel belum.",
  ]);
  const statsLine = el("p", { className: "note", id: "stats" }, ["Memuat statistik…"]);

  const chips = el("div", { className: "chips" });
  for (let i = 0; i < 5; i++) {
    const c = el("span", { className: i === 1 ? "chip t2" : "chip" }, [
      `T${i + 1} ${DEFAULT_TRADE_NAMES[i]}`,
    ]);
    c.style.background = tradeColor(i);
    chips.append(c);
  }

  const dlBar = el("div", { className: "download-bar" });
  const dlCsv = el("button", { type: "button", className: "ghost" }, [
    "Unduh CSV (Excel)",
  ]);
  const dlPng = el("button", { type: "button", className: "ghost" }, [
    "Unduh chart PNG",
  ]);
  const dlPng2 = el("button", { type: "button", className: "ghost hidden" }, [
    "Unduh chart 2 PNG",
  ]);
  dlBar.append(dlCsv, dlPng, dlPng2);

  const sidebar = el("aside", { className: "panel" }, [
    el("h2", {}, ["Papan Kendali"]),
    chips,
    el("label", { for: "zones" }, ["Total zona"]),
    el("div", { className: "slider-row" }, [zones, zonesVal]),
    el("label", { for: "batch" }, ["Batch handoff"]),
    batch,
    el("label", { for: "speed" }, ["Kapasitas dasar"]),
    speed,
    el("label", { for: "var" }, ["Variability"]),
    variability,
    el("label", { for: "seed" }, ["Seed"]),
    seed,
    tarifBlock,
    runBtn,
    statsLine,
  ]);

  const main = el("section", { className: "panel" }, [
    tabs,
    title,
    metrics,
    metrics2,
    littleControls,
    legend,
    dlBar,
    subTitle,
    chartWrap,
    chartWrap2,
    tableHost,
    note,
  ]);

  const simLayout = el("div", { className: "layout" }, [sidebar, main]);
  const compareHost = el("div", { className: "compare-host hidden" });
  const taktHost = el("div", { className: "mode-host hidden" });
  const bufferHost = el("div", { className: "mode-host hidden" });
  const statsHost = el("div", { className: "mode-host hidden" });
  const manualHost = el("div", { className: "mode-host hidden" });

  const modeDefs: { id: AppMode; label: string; btn: HTMLButtonElement }[] = [
    { id: "sim", label: "Simulasi", btn: el("button", { className: "mode-tab active", type: "button" }, ["Simulasi"]) as HTMLButtonElement },
    { id: "compare", label: "Perbandingan", btn: el("button", { className: "mode-tab", type: "button" }, ["Perbandingan"]) as HTMLButtonElement },
    { id: "takt", label: "Takt plan", btn: el("button", { className: "mode-tab", type: "button" }, ["Takt plan"]) as HTMLButtonElement },
    { id: "buffer", label: "Buffer", btn: el("button", { className: "mode-tab", type: "button" }, ["Buffer"]) as HTMLButtonElement },
  ];
  const modeTabs = el("div", { className: "mode-tabs" }, modeDefs.map((m) => m.btn));

  const headerStats = el("button", { className: "header-link", type: "button" }, ["Statistik"]);
  const headerManual = el("button", { className: "header-link", type: "button" }, ["Manual"]);
  const headerNav = el("div", { className: "header-nav" }, [headerStats, headerManual]);

  const brandBlock = el("div", { className: "brand-block" }, [
    el("img", {
      className: "brand-logo",
      src: "/assets/logo_icon.png",
      alt: "Parade Tim Kerja",
      width: "48",
      height: "48",
    }),
    el("div", { className: "brand-text" }, [
      el("div", { className: "brand" }, ["Parade Tim Kerja"]),
      el("div", { className: "brand-sub" }, [
        "Simulasi Aliran Tim Kerja pada Pekerjaan Lantai Beton Bertulang",
      ]),
    ]),
  ]);

  root.append(
    el("div", { className: "wrap" }, [
      el("header", { className: "app-header" }, [brandBlock, headerNav]),
      modeTabs,
      simLayout,
      compareHost,
      taktHost,
      bufferHost,
      statsHost,
      manualHost,
    ]),
  );

  const sharedZonesSeed = {
    getZones: () => Math.max(1, Number(zones.value) || 10),
    getSeed: () => Number(seed.value) || 12345,
    getRates: () =>
      tarifSliders.map((s) => Math.max(0, Number(s.value) || 0)),
    getTarif: () => Math.max(0, Number(tarifSliders[0]?.value) || 100),
    getDefaultBatch: () => Math.max(1, Number(batch.value) || 4),
  };

  const mounted: Record<Exclude<AppMode, "sim">, boolean> = {
    compare: false,
    takt: false,
    buffer: false,
    stats: false,
    manual: false,
  };

  function showMode(mode: AppMode): void {
    for (const m of modeDefs) m.btn.classList.toggle("active", m.id === mode);
    headerStats.classList.toggle("active", mode === "stats");
    headerManual.classList.toggle("active", mode === "manual");
    simLayout.classList.toggle("hidden", mode !== "sim");
    compareHost.classList.toggle("hidden", mode !== "compare");
    taktHost.classList.toggle("hidden", mode !== "takt");
    bufferHost.classList.toggle("hidden", mode !== "buffer");
    statsHost.classList.toggle("hidden", mode !== "stats");
    manualHost.classList.toggle("hidden", mode !== "manual");

    if (mode === "compare" && !mounted.compare) {
      mountCompare(compareHost, sharedZonesSeed);
      mounted.compare = true;
    }
    if (mode === "takt" && !mounted.takt) {
      mountTakt(taktHost);
      mounted.takt = true;
    }
    if (mode === "buffer" && !mounted.buffer) {
      mountTimeBuffer(bufferHost, sharedZonesSeed);
      mounted.buffer = true;
    }
    if (mode === "stats" && !mounted.stats) {
      mountStats(statsHost);
      mounted.stats = true;
    }
    if (mode === "manual" && !mounted.manual) {
      mountManual(manualHost);
      mounted.manual = true;
    }
  }
  for (const m of modeDefs) {
    m.btn.addEventListener("click", () => showMode(m.id));
  }
  headerStats.addEventListener("click", () => showMode("stats"));
  headerManual.addEventListener("click", () => showMode("manual"));

  let lastResult: ParadeResult | null = null;
  let lastCost: CostMetrics | null = null;
  let activeTab: TabId = "lob";
  let lobHits: LobHit[] = [];
  let bufHits: BufferHit[] = [];
  let conwipLevel = 5;

  function rates(): number[] {
    return tarifSliders.map((s) => Math.max(0, Number(s.value) || 0));
  }

  function syncConwipBounds(r: ParadeResult): void {
    const d = littlesOperationsCurve(r);
    const cmin = 0.5;
    const cmax = Math.max(r.config.totalUnits, d.wOpt * 4, d.wMin * 4, 20);
    conwip.min = String(cmin);
    conwip.max = String(cmax);
    conwipLevel = snapConwip(Math.min(cmax, Math.max(cmin, d.conwip)));
    conwip.value = String(conwipLevel);
    conwipVal.textContent = conwipLevel.toFixed(1);
  }

  function renderConwipPred(r: ParadeResult): void {
    const pred = evaluateAtWip(r, conwipLevel);
    const d = littlesOperationsCurve(r);
    conwipPred.replaceChildren(
      metric("TH @ CONWIP", fmtF(pred.th, 3)),
      metric("CT @ CONWIP", fmtF(pred.ct)),
      metric("Δ WIP", fmtF(pred.dWip)),
      metric("TH batas @ WIP", fmtF(pred.thBest, 3)),
    );
    if (pred.dWip < -0.25) {
      conwipCaption.textContent =
        `CONWIP di bawah operasi (${d.opWip.toFixed(1)}): inventory lebih ketat → CT cenderung turun, TH bisa turun jika jauh di bawah W_opt (${d.wOpt.toFixed(1)}).`;
    } else if (pred.dWip > 0.25) {
      conwipCaption.textContent =
        `CONWIP di atas operasi (${d.opWip.toFixed(1)}): lebih longgar → CT cenderung naik, TH mendekati plafon (TH_max=${d.thMax.toFixed(2)}).`;
    } else {
      conwipCaption.textContent =
        `CONWIP ≈ WIP operasi (${d.opWip.toFixed(1)}): prediksi dekat hasil run (TH=${d.opTh.toFixed(3)}, CT=${d.opCt.toFixed(2)}).`;
    }
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
    metrics2.classList.add("hidden");
    metrics2.replaceChildren();

    if (activeTab === "util_cost") {
      metrics.replaceChildren(
        metric("Utilisasi ⌀", `${(100 * avgUtil).toFixed(1)}%`),
        metric("Biaya aktif", fmtNum(cm.totalActive)),
        metric("Biaya idle", fmtNum(cm.totalIdle)),
        metric("Total biaya", fmtNum(cm.totalCost)),
      );
      return;
    }
    if (activeTab === "little") {
      const ll = littlesLawMetrics(r);
      const d = littlesOperationsCurve(r);
      metrics.replaceChildren(
        metric("Throughput (TH)", fmtF(ll.throughput, 3)),
        metric("WIP pipeline ⌀", fmtF(ll.avgPipelineWip)),
        metric("CT pipeline", fmtF(ll.cycleTimePipeline)),
        metric("WIP buffer ⌀", fmtF(ll.avgBufferWip)),
        metric("CT buffer", fmtF(ll.cycleTimeBuffer)),
        metric("TH × CT (cek)", fmtF(ll.checkPipeline)),
      );
      metrics2.classList.remove("hidden");
      metrics2.replaceChildren(
        metric("W_min (kritis)", fmtF(d.wMin)),
        metric("W_opt", fmtF(d.wOpt)),
        metric("WIP operasi", fmtF(d.opWip)),
        metric("V (var factor)", fmtF(d.vFactor, 3)),
      );
      return;
    }
    if (activeTab === "kingman") {
      const comb = kingmanCombined(r);
      const kg = kingmanMetrics(r);
      metrics.replaceChildren(
        metric("u̅ gabungan", fmtF(comb.uBar, 3)),
        metric("V gabungan", fmtF(comb.v, 3)),
        metric("CT Kingman (u̅)", fmtF(comb.ct)),
        metric("CT Little", fmtF(kg.systemCtLittle)),
      );
      return;
    }
    if (activeTab === "inventory") {
      const fr = inventoryFillRateMetrics(r);
      metrics.replaceChildren(
        metric("Inventory ⌀ (buffer)", fmtF(fr.avgInventorySystem)),
        metric("Fill rate sistem", `${(100 * fr.fillRateSystem).toFixed(1)}%`),
        metric("Fill rate T1", `${(100 * fr.fillRateT1).toFixed(1)}%`),
        metric("Puncak Σ buffer", String(fr.peakBufferTotal)),
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
    lob: "Location-based Schedule",
    buffer: "Buffer / WIP",
    util_cost: "Utilisasi & Biaya",
    little: "Little's Law",
    kingman: "Kingman (VUT)",
    inventory: "Inventory / Fill Rate",
  };

  function setTab(tab: TabId): void {
    activeTab = tab;
    for (const [id, btn] of tabBtns) btn.classList.toggle("active", id === tab);
    title.textContent = titles[tab];
    if (lastResult && lastCost) setMetrics(lastResult, lastCost);
    redraw();
  }

  function syncDownloadBar(): void {
    const dual = !chartWrap2.classList.contains("hidden");
    dlPng2.classList.toggle("hidden", !dual);
  }

  function redraw(): void {
    if (!lastResult || !lastCost) return;
    tip.classList.add("hidden");
    lobHits = [];
    bufHits = [];
    littleControls.classList.add("hidden");
    chartWrap2.classList.add("hidden");
    subTitle.classList.add("hidden");

    chartWrap.classList.remove("hidden");
    tableHost.classList.remove("hidden");

    if (activeTab === "lob") {
      lobHits = drawLobChart(canvas, lastResult, { cssHeight: 380 });
      renderLegendItems(legend, buildLegendItems(lastResult));
      tableHost.classList.add("hidden");
      tableHost.replaceChildren();
      syncDownloadBar();
      return;
    }

    if (activeTab === "buffer") {
      subTitle.classList.remove("hidden");
      subTitle.textContent = "Garis per buffer · lalu stacked";
      chartWrap2.classList.remove("hidden");
      bufHits = drawBufferChart(canvas, lastResult, { cssHeight: 280 });
      drawBufferStackedChart(canvas2, lastResult, { cssHeight: 260 });
      renderLegendItems(legend, buildBufferLegend(lastResult));
      renderBufferPeakTable(tableHost, lastResult);
      syncDownloadBar();
      return;
    }

    if (activeTab === "util_cost") {
      drawUtilChart(canvas, lastResult);
      renderLegendItems(legend, buildUtilLegend(lastResult));
      renderUtilCostTables(tableHost, lastResult, lastCost);
      syncDownloadBar();
      return;
    }

    if (activeTab === "little") {
      littleControls.classList.remove("hidden");
      renderConwipPred(lastResult);
      subTitle.classList.remove("hidden");
      subTitle.textContent = "Kurva operasi · lalu WIP pipeline/buffer vs waktu";
      chartWrap2.classList.remove("hidden");
      drawOperationsChart(canvas, lastResult, conwipLevel, { cssHeight: 340 });
      drawLittlesChart(canvas2, lastResult, { cssHeight: 280 });
      renderLegendItems(legend, buildLittlesLegend());
      renderLittlesTable(tableHost, lastResult);
      const d = littlesOperationsCurve(lastResult);
      const noteEl = el("p", { className: "note table-note" }, [
        `W_min=W0=TH_max×T0=${d.wMin.toFixed(2)} · W_opt=${d.wOpt.toFixed(2)} (V=${d.vFactor.toFixed(3)}) · CONWIP=${conwipLevel.toFixed(1)} · TH_max=${d.thMax.toFixed(3)} · T0=${d.t0.toFixed(2)}.`,
      ]);
      if (Math.abs(d.wOpt - d.wMin) < 1e-6) {
        tableHost.append(
          el("p", { className: "note table-note" }, [
            "W_min = W_opt karena variability ≈ 0 (deterministik). Naikkan variability agar W_opt > W_min.",
          ]),
        );
      }
      tableHost.append(noteEl);
      syncDownloadBar();
      return;
    }

    if (activeTab === "kingman") {
      drawKingmanChart(canvas, lastResult, { cssHeight: 340 });
      renderLegendItems(legend, buildKingmanLegend(lastResult));
      renderKingmanTable(tableHost, lastResult);
      syncDownloadBar();
      return;
    }

    if (activeTab === "inventory") {
      drawInventoryChart(canvas, lastResult, { cssHeight: 340 });
      renderLegendItems(legend, buildInventoryLegend(lastResult));
      renderInventoryTable(tableHost, lastResult);
      syncDownloadBar();
      return;
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
    syncConwipBounds(lastResult);
    setMetrics(lastResult, lastCost);
    redraw();
    void recordSimRun();
    bumpSessionRuns();
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
  dlCsv.addEventListener("click", () => {
    if (!lastResult) return;
    downloadText(
      `parade-simulasi-${fileStamp()}.csv`,
      resultWorkbookCsv(lastResult, rates()),
    );
  });
  dlPng.addEventListener("click", () => {
    if (!lastResult) return;
    downloadCanvasPng(canvas, `parade-${activeTab}-${fileStamp()}.png`);
  });
  dlPng2.addEventListener("click", () => {
    if (!lastResult || chartWrap2.classList.contains("hidden")) return;
    downloadCanvasPng(canvas2, `parade-${activeTab}-2-${fileStamp()}.png`);
  });
  runBtn.addEventListener("click", run);
  zones.addEventListener("input", () => {
    zonesVal.textContent = String(zones.value);
  });
  for (let i = 0; i < tarifSliders.length; i++) {
    tarifSliders[i].addEventListener("input", () => {
      tarifVals[i].textContent = String(tarifSliders[i].value);
      if (!lastResult) return;
      lastCost = computeCostMetrics(lastResult, rates());
      setMetrics(lastResult, lastCost);
      if (activeTab === "util_cost") redraw();
    });
  }
  conwip.addEventListener("input", () => {
    conwipLevel = snapConwip(Number(conwip.value) || 5);
    conwipVal.textContent = conwipLevel.toFixed(1);
    if (lastResult && activeTab === "little") {
      renderConwipPred(lastResult);
      setMetrics(lastResult, lastCost!);
      redraw();
    }
  });
  window.addEventListener("resize", () => redraw());

  void (async () => {
    await recordAppSession();
    const dash = await readDashboard();
    statsLine.textContent = `Statistik (Counter): sim_runs=${dash.sim_runs ?? 0} · compare_runs=${dash.compare_runs ?? 0} · app_sessions=${dash.app_sessions ?? 0}`;
  })();

  run();
}
