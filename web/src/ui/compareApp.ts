/**
 * Top-level Perbandingan mode — multi-scenario runs + overlay charts.
 * Mirrors Streamlit tab_compare (app.py).
 */

import {
  classroomConfig,
  computeCostMetrics,
  inventoryFillRateMetrics,
  littlesLawMetrics,
  runParade,
  shortVariabilityLabel,
  VARIABILITY_LEVELS,
  type ParadeResult,
  type VariabilityLevel,
} from "../core";
import { recordCompareRun } from "../stats";
import { scenarioColor } from "../theme";
import {
  buildCompareLegend,
  drawCompareBuffers,
  drawCompareCosts,
  drawCompareLob,
  drawCompareMetricsBars,
  drawCompareUtil,
  type NamedResult,
} from "./compareCharts";

type CmpTab =
  | "lob"
  | "buffer"
  | "util_cost"
  | "little"
  | "kingman"
  | "inventory";

type ScenarioDraft = {
  variability: VariabilityLevel;
  batch: number;
  speed: number;
};

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

function fmtNum(n: number): string {
  return Math.round(n).toLocaleString("id-ID");
}

function peakWip(r: ParadeResult): number {
  let peak = 0;
  for (const rec of r.history) {
    const s = rec.buffers.reduce((a, b) => a + b, 0);
    if (s > peak) peak = s;
  }
  return peak;
}

function defaultDrafts(n: number, batch: number): ScenarioDraft[] {
  const vars: VariabilityLevel[] = [
    "none",
    "low",
    "medium",
    "high",
    "very_high",
  ];
  return Array.from({ length: n }, (_, i) => ({
    variability: vars[i] ?? "none",
    batch,
    speed: 1,
  }));
}

export function mountCompare(
  root: HTMLElement,
  shared: {
    getZones: () => number;
    getSeed: () => number;
    getRates?: () => number[];
    getTarif: () => number;
    getDefaultBatch: () => number;
  },
): void {
  root.replaceChildren();

  let nScen = 5;
  let drafts = defaultDrafts(nScen, shared.getDefaultBatch());
  let results: NamedResult[] | null = null;
  let activeTab: CmpTab = "lob";

  const quick = el("div", { className: "cmp-quick" });
  const btnFive = el("button", { type: "button", className: "ghost" }, ["5× variability"]);
  const btnTwo = el("button", { type: "button", className: "ghost" }, ["Tanpa var vs Sedang"]);
  const btnBatch = el("button", { type: "button", className: "ghost" }, ["Batch 1 vs 4"]);
  const btnClear = el("button", { type: "button", className: "ghost" }, ["Hapus hasil"]);
  quick.append(btnFive, btnTwo, btnBatch, btnClear);

  const nLabel = el("label", { for: "cmp-n" }, ["Jumlah skenario"]);
  const nInput = el("input", {
    type: "range",
    id: "cmp-n",
    min: "2",
    max: "5",
    step: "1",
    value: String(nScen),
  }) as HTMLInputElement;
  const nVal = el("span", { className: "conwip-val" }, [String(nScen)]);
  const nRow = el("div", { className: "conwip-row" }, [nInput, nVal]);

  const cards = el("div", { className: "cmp-cards" });
  const runBtn = el("button", { className: "run", type: "button" }, [
    "Jalankan perbandingan",
  ]);

  const summaryHost = el("div", { className: "table-host hidden" });
  const tabs = el("div", { className: "tabs hidden" });
  const legend = el("div", { className: "legend" });
  const chartWrap = el("div", { className: "chart-wrap hidden" });
  const canvas = el("canvas", { id: "cmp-chart" }) as HTMLCanvasElement;
  chartWrap.append(canvas);
  const chartWrap2 = el("div", { className: "chart-wrap hidden" });
  const canvas2 = el("canvas", { id: "cmp-chart2" }) as HTMLCanvasElement;
  chartWrap2.append(canvas2);
  const detailHost = el("div", { className: "table-host hidden" });
  const note = el("p", { className: "note" }, [
    "Perbandingan multi-skenario (parity Streamlit). Seed & zona mengikuti sidebar Simulasi yang sama di atas. ",
  ]);

  const tabDefs: { id: CmpTab; label: string }[] = [
    { id: "lob", label: "Line of Balance" },
    { id: "buffer", label: "Buffer / WIP" },
    { id: "util_cost", label: "Utilisasi & Biaya" },
    { id: "little", label: "Little's Law" },
    { id: "kingman", label: "Kingman" },
    { id: "inventory", label: "Inventory / FR" },
  ];
  const tabBtns = new Map<CmpTab, HTMLButtonElement>();
  for (const t of tabDefs) {
    const btn = el(
      "button",
      {
        className: t.id === "lob" ? "tab active" : "tab",
        type: "button",
      },
      [t.label],
    ) as HTMLButtonElement;
    tabBtns.set(t.id, btn);
    tabs.append(btn);
    btn.addEventListener("click", () => {
      activeTab = t.id;
      for (const [id, b] of tabBtns) b.classList.toggle("active", id === t.id);
      redrawCharts();
    });
  }

  root.append(
    el("div", { className: "panel" }, [
      el("h2", {}, ["Perbandingan"]),
      quick,
      nLabel,
      nRow,
      cards,
      runBtn,
      summaryHost,
      tabs,
      legend,
      chartWrap,
      chartWrap2,
      detailHost,
      note,
    ]),
  );

  function rates(): number[] {
    if (shared.getRates) return shared.getRates();
    return Array(5).fill(Math.max(0, shared.getTarif() || 100));
  }

  function renderCards(): void {
    cards.replaceChildren();
    for (let i = 0; i < nScen; i++) {
      const d = drafts[i];
      const varSel = el("select", { id: `cmp-var-${i}` }) as HTMLSelectElement;
      for (const v of VARIABILITY_LEVELS) {
        varSel.append(el("option", { value: v }, [shortVariabilityLabel(v)]));
      }
      varSel.value = d.variability;

      const batchSel = el("select", { id: `cmp-batch-${i}` }) as HTMLSelectElement;
      for (const b of [4, 5, 3, 2, 1]) {
        batchSel.append(
          el("option", { value: String(b) }, [
            b === 1
              ? "1 — One-piece"
              : b === 4
                ? "4 — Standar"
                : `${b} — Handoff tiap ${b} zona`,
          ]),
        );
      }
      batchSel.value = String(d.batch);

      const speedSel = el("select", { id: `cmp-speed-${i}` }) as HTMLSelectElement;
      for (const [lab, val] of [
        ["Sangat rendah — 1/3", "0.333"],
        ["Rendah — 0.5", "0.5"],
        ["Normal — 1", "1"],
        ["Tinggi — 2", "2"],
        ["Sangat tinggi — 3", "3"],
      ] as const) {
        speedSel.append(el("option", { value: val }, [lab]));
      }
      // snap to closest
      const speeds = [1 / 3, 0.5, 1, 2, 3];
      let best = speeds[0];
      let bestD = Infinity;
      for (const s of speeds) {
        const dd = Math.abs(s - d.speed);
        if (dd < bestD) {
          bestD = dd;
          best = s;
        }
      }
      speedSel.value = String(best === 1 / 3 ? 0.333 : best);

      const sw = el("span", { className: "row-swatch" });
      sw.style.background = scenarioColor(i);

      const card = el("div", { className: "cmp-card" }, [
        el("div", { className: "cmp-card-title" }, [sw, `Skenario ${i + 1}`]),
        el("label", {}, ["Variability"]),
        varSel,
        el("label", {}, ["Batch handoff"]),
        batchSel,
        el("label", {}, ["Kapasitas"]),
        speedSel,
      ]);
      cards.append(card);

      varSel.addEventListener("change", () => {
        drafts[i].variability = varSel.value as VariabilityLevel;
      });
      batchSel.addEventListener("change", () => {
        drafts[i].batch = Number(batchSel.value) || 4;
      });
      speedSel.addEventListener("change", () => {
        drafts[i].speed = Number(speedSel.value) || 1;
      });
    }
  }

  function renderSummary(): void {
    if (!results?.length) {
      summaryHost.classList.add("hidden");
      return;
    }
    summaryHost.classList.remove("hidden");

    const enriched = results.map((it, i) => {
      const r = it.result;
      const cm = computeCostMetrics(r, rates());
      const ll = littlesLawMetrics(r);
      const fr = inventoryFillRateMetrics(r);
      return {
        name: it.name,
        varLabel: shortVariabilityLabel(drafts[i]?.variability ?? "none"),
        batch: r.config.batchSize,
        duration: r.duration,
        active: cm.trades.reduce((s, t) => s + t.periodsActive, 0),
        idle: cm.trades.reduce((s, t) => s + t.periodsIdle, 0),
        costActive: cm.totalActive,
        costIdle: cm.totalIdle,
        costTotal: cm.totalCost,
        peak: peakWip(r),
        th: ll.throughput,
        fr: fr.fillRateSystem,
        t5: r.tradeMetrics[r.tradeMetrics.length - 1].periodsToFinish,
      };
    });
    enriched.sort((a, b) => a.duration - b.duration);

    summaryHost.replaceChildren();
    summaryHost.append(el("h3", { className: "subchart-title" }, ["Ringkasan"]));
    const table = el("table", { className: "data-table" });
    table.append(
      el("thead", {}, [
        el("tr", {}, [
          el("th", {}, ["Skenario"]),
          el("th", {}, ["Variability"]),
          el("th", {}, ["Batch"]),
          el("th", {}, ["Durasi"]),
          el("th", {}, ["Σ aktif"]),
          el("th", {}, ["Σ idle"]),
          el("th", {}, ["Biaya aktif"]),
          el("th", {}, ["Biaya idle"]),
          el("th", {}, ["Total biaya"]),
          el("th", {}, ["Peak WIP"]),
          el("th", {}, ["TH"]),
          el("th", {}, ["FR %"]),
          el("th", {}, ["T5 selesai"]),
        ]),
      ]),
    );
    const tbody = el("tbody");
    for (const row of enriched) {
      const idx = results!.findIndex((r) => r.name === row.name);
      tbody.append(
        el("tr", {}, [
          el("td", {}, [
            el("span", { className: "row-swatch" }, []),
            row.name,
          ]),
          el("td", {}, [row.varLabel]),
          el("td", {}, [String(row.batch)]),
          el("td", {}, [String(row.duration)]),
          el("td", {}, [String(row.active)]),
          el("td", {}, [String(row.idle)]),
          el("td", {}, [fmtNum(row.costActive)]),
          el("td", {}, [fmtNum(row.costIdle)]),
          el("td", {}, [fmtNum(row.costTotal)]),
          el("td", {}, [String(row.peak)]),
          el("td", {}, [row.th.toFixed(3)]),
          el("td", {}, [(100 * row.fr).toFixed(1)]),
          el("td", {}, [String(row.t5)]),
        ]),
      );
      const sw = tbody.lastElementChild?.querySelector(".row-swatch") as HTMLElement | null;
      if (sw) sw.style.background = scenarioColor(idx < 0 ? 0 : idx);
    }
    table.append(tbody);
    summaryHost.append(table);
  }

  function redrawCharts(): void {
    if (!results?.length) {
      tabs.classList.add("hidden");
      chartWrap.classList.add("hidden");
      chartWrap2.classList.add("hidden");
      detailHost.classList.add("hidden");
      legend.replaceChildren();
      return;
    }
    tabs.classList.remove("hidden");
    chartWrap.classList.remove("hidden");
    chartWrap2.classList.add("hidden");
    detailHost.classList.add("hidden");
    detailHost.replaceChildren();

    legend.replaceChildren();
    for (const item of buildCompareLegend(results)) {
      const sw = el("span", { className: "swatch" });
      sw.style.setProperty("--sw", item.color);
      legend.append(
        el("div", { className: "legend-item" }, [sw, el("span", {}, [item.text])]),
      );
    }

    const r = rates();
    if (activeTab === "lob") {
      drawCompareLob(canvas, results);
    } else if (activeTab === "buffer") {
      drawCompareBuffers(canvas, results);
    } else if (activeTab === "util_cost") {
      drawCompareUtil(canvas, results);
      chartWrap2.classList.remove("hidden");
      drawCompareCosts(canvas2, results, r, { cssHeight: 240 });
      detailHost.classList.remove("hidden");
      const table = el("table", { className: "data-table" });
      table.append(
        el("thead", {}, [
          el("tr", {}, [
            el("th", {}, ["Skenario"]),
            el("th", {}, ["Aktif"]),
            el("th", {}, ["Idle"]),
            el("th", {}, ["Aktif+Idle"]),
            el("th", {}, ["Total"]),
            el("th", {}, ["Cek"]),
          ]),
        ]),
      );
      const tbody = el("tbody");
      results.forEach((it, i) => {
        const cm = computeCostMetrics(it.result, r);
        const sum = cm.totalActive + cm.totalIdle;
        tbody.append(
          el("tr", {}, [
            el("td", {}, [
              el("span", { className: "row-swatch" }, []),
              it.name,
            ]),
            el("td", {}, [fmtNum(cm.totalActive)]),
            el("td", {}, [fmtNum(cm.totalIdle)]),
            el("td", {}, [fmtNum(sum)]),
            el("td", {}, [fmtNum(cm.totalCost)]),
            el("td", {}, [Math.abs(sum - cm.totalCost) < 0.01 ? "OK" : "MISMATCH"]),
          ]),
        );
        const sw = tbody.lastElementChild?.querySelector(".row-swatch") as HTMLElement | null;
        if (sw) sw.style.background = scenarioColor(i);
      });
      table.append(tbody);
      detailHost.append(table);
    } else if (activeTab === "little") {
      drawCompareMetricsBars(canvas, results, "duration", r);
      chartWrap2.classList.remove("hidden");
      drawCompareMetricsBars(canvas2, results, "th", r, { cssHeight: 220 });
    } else if (activeTab === "kingman") {
      // Show duration + util as proxy teaching; util already elsewhere
      drawCompareUtil(canvas, results, { cssHeight: 300 });
    } else if (activeTab === "inventory") {
      drawCompareMetricsBars(canvas, results, "fr", r);
      chartWrap2.classList.remove("hidden");
      drawCompareBuffers(canvas2, results, { cssHeight: 240 });
    }
  }

  function runCompare(): void {
    const zones = shared.getZones();
    const seed = shared.getSeed();
    const out: NamedResult[] = [];
    for (let i = 0; i < nScen; i++) {
      const d = drafts[i];
      const cfg = classroomConfig({
        totalUnits: zones,
        batchSize: d.batch,
        baseSpeed: d.speed,
        seed,
        variability: d.variability,
      });
      out.push({ name: `Skenario ${i + 1}`, result: runParade(cfg) });
    }
    results = out;
    activeTab = "lob";
    for (const [id, b] of tabBtns) b.classList.toggle("active", id === "lob");
    renderSummary();
    redrawCharts();
    void recordCompareRun();
  }

  function applyN(n: number): void {
    nScen = n;
    nInput.value = String(n);
    nVal.textContent = String(n);
    const next = defaultDrafts(n, shared.getDefaultBatch());
    for (let i = 0; i < Math.min(drafts.length, n); i++) next[i] = { ...drafts[i] };
    drafts = next;
    renderCards();
  }

  btnFive.addEventListener("click", () => {
    applyN(5);
    drafts = defaultDrafts(5, shared.getDefaultBatch());
    renderCards();
  });
  btnTwo.addEventListener("click", () => {
    applyN(2);
    drafts = [
      { variability: "none", batch: shared.getDefaultBatch(), speed: 1 },
      { variability: "medium", batch: shared.getDefaultBatch(), speed: 1 },
    ];
    renderCards();
  });
  btnBatch.addEventListener("click", () => {
    applyN(2);
    drafts = [
      { variability: "none", batch: 1, speed: 1 },
      { variability: "none", batch: 4, speed: 1 },
    ];
    renderCards();
  });
  btnClear.addEventListener("click", () => {
    results = null;
    summaryHost.classList.add("hidden");
    summaryHost.replaceChildren();
    redrawCharts();
  });
  nInput.addEventListener("input", () => applyN(Number(nInput.value) || 2));
  runBtn.addEventListener("click", runCompare);
  window.addEventListener("resize", () => {
    if (results) redrawCharts();
  });

  renderCards();
}
