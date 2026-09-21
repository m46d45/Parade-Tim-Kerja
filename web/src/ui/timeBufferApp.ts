/**
 * Buffer waktu–inventory mode (Streamlit tab_buffer).
 */

import {
  BUFFER_VAR_PRESETS,
  BUF_VAR_LABEL,
  BUF_VAR_SHORT,
  IRIS_MOBILIZATION,
  fitBufferTrends,
  fitInvVsTos,
  irisBufferSweep,
  runTimeInventoryBuffer,
  type BufferSweepRow,
  type ParadeResult,
} from "../core";
import { drawLobChart } from "./lobChart";
import { downloadCanvasPng } from "./download";
import {
  drawInventoryVsTos,
  drawTimeInventoryPareto,
} from "./timeBufferCharts";

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

function field(
  labelText: string,
  forId: string,
  control: HTMLElement,
): HTMLElement {
  return el("div", { className: "field" }, [
    el("label", { for: forId }, [labelText]),
    control,
  ]);
}

function fileStamp(): string {
  const d = new Date();
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}`;
}

export function mountTimeBuffer(
  root: HTMLElement,
  shared: { getZones: () => number; getSeed: () => number },
): void {
  root.replaceChildren();

  let oneResult: ParadeResult | null = null;
  let oneLabel = "";
  let mapRows: BufferSweepRow[] | null = null;

  const varSel = el("select", { id: "buf-var" }) as HTMLSelectElement;
  for (const v of BUFFER_VAR_PRESETS) {
    varSel.append(
      el("option", { value: v }, [BUF_VAR_LABEL[v] ?? v]),
    );
  }
  const mobSel = el("select", { id: "buf-mob" }) as HTMLSelectElement;
  for (const k of Object.keys(IRIS_MOBILIZATION)) {
    mobSel.append(el("option", { value: k }, [k]));
  }

  const runOne = el("button", { type: "button", className: "primary" }, [
    "Jalankan",
  ]);
  const runMap = el("button", { type: "button" }, ["Peta tren"]);
  const err = el("p", { className: "note warn-text" });

  const oneHost = el("div", { className: "buf-one hidden" });
  const oneMetrics = el("div", { className: "metrics" });
  const oneTitle = el("h3", { className: "subchart-title" }, ["Hasil"]);
  const oneDl = el("div", { className: "download-bar" });
  const oneDlPng = el("button", { type: "button", className: "ghost" }, [
    "Unduh chart PNG",
  ]);
  oneDl.append(oneDlPng);
  const lobWrap = el("div", { className: "chart-wrap" });
  const lobCanvas = el("canvas", { id: "buf-lob" }) as HTMLCanvasElement;
  lobWrap.append(lobCanvas);
  oneHost.append(oneTitle, oneMetrics, oneDl, lobWrap);

  const mapHost = el("div", { className: "buf-map hidden" });
  const mapCap = el("p", { className: "note" });
  const mapDl = el("div", { className: "download-bar" });
  const mapDlPareto = el("button", { type: "button", className: "ghost" }, [
    "Unduh pareto PNG",
  ]);
  const mapDlPair = el("button", { type: "button", className: "ghost" }, [
    "Unduh INV vs TOS PNG",
  ]);
  mapDl.append(mapDlPareto, mapDlPair);
  const paretoWrap = el("div", { className: "chart-wrap" });
  const paretoCanvas = el("canvas", { id: "buf-pareto" }) as HTMLCanvasElement;
  paretoWrap.append(paretoCanvas);
  const fitTable = el("div", { className: "table-wrap" });
  const pairCap = el("p", { className: "note" });
  const pairWrap = el("div", { className: "chart-wrap" });
  const pairCanvas = el("canvas", { id: "buf-pair" }) as HTMLCanvasElement;
  pairWrap.append(pairCanvas);
  const pairTable = el("div", { className: "table-wrap" });
  const scenTable = el("div", { className: "table-wrap" });
  mapHost.append(
    el("h3", { className: "subchart-title" }, [
      "Waktu di lapangan & inventory vs durasi",
    ]),
    mapCap,
    mapDl,
    paretoWrap,
    fitTable,
    el("h3", { className: "subchart-title" }, [
      "Inventory time vs waktu di lapangan",
    ]),
    pairCap,
    pairWrap,
    pairTable,
    el("h3", { className: "subchart-title" }, ["Tabel semua skenario"]),
    scenTable,
  );

  root.append(
    el("div", { className: "panel mode-panel" }, [
      el("h2", {}, ["Buffer"]),
      el("p", { className: "note" }, [
        "Buffer waktu–inventory pada parade tim kerja. Kapasitas normal ",
        "(1 zona/periode), batch 1. Yang diubah: kapan tim masuk dan tingkat ",
        "variability. Analog kuliah Iris (5–5 / 4–6 / 3–7), tanpa dadu.",
      ]),
      el("div", { className: "takt-grid" }, [
        field("Variability (per zona)", "buf-var", varSel),
        field("Buffer waktu (tunda masuk T1…T5)", "buf-mob", mobSel),
      ]),
      el("div", { className: "btn-row" }, [runOne, runMap]),
      err,
      oneHost,
      mapHost,
    ]),
  );

  function renderOne(): void {
    if (!oneResult) {
      oneHost.classList.add("hidden");
      return;
    }
    oneHost.classList.remove("hidden");
    oneTitle.textContent = `Hasil \`${oneLabel}\``;
    oneMetrics.replaceChildren(
      metric("Durasi", String(oneResult.duration)),
      metric("Waktu di lapangan", String(oneResult.totalTimeOnSite)),
      metric("Inventory time", String(oneResult.totalInventoryTime)),
    );
    drawLobChart(lobCanvas, oneResult);
  }

  function tableHtml(
    headers: string[],
    rows: string[][],
  ): HTMLElement {
    const table = el("table");
    const thead = el("thead");
    const hr = el("tr");
    for (const h of headers) hr.append(el("th", {}, [h]));
    thead.append(hr);
    const tbody = el("tbody");
    for (const row of rows) {
      const tr = el("tr");
      for (const cell of row) tr.append(el("td", {}, [cell]));
      tbody.append(tr);
    }
    table.append(thead, tbody);
    return table;
  }

  function renderMap(): void {
    if (!mapRows) {
      mapHost.classList.add("hidden");
      return;
    }
    mapHost.classList.remove("hidden");
    const nTrades = 5;
    const zones = shared.getZones();
    const floor = nTrades * zones;
    mapCap.textContent =
      `Rata-rata 12 seed. Tiga pola tunda (rapat / tengah / longgar). ` +
      `TOS ≥ ${floor} (${nTrades} tim × ${zones} zona). ` +
      `Tanpa var = lantai. Variasi: TOS turun ke lantai jika tunda longgar. INV naik linier.`;

    drawTimeInventoryPareto(paretoCanvas, mapRows, oneLabel || null);
    const fits = fitBufferTrends(mapRows);
    fitTable.replaceChildren(
      tableHtml(
        ["Variability", "Metrik", "Model", "Rumus", "R²"],
        fits.map((f) => [
          BUF_VAR_SHORT[f.die] ?? f.die,
          f.metric === "time_on_site" ? "Waktu di lapangan" : "Inventory time",
          f.model,
          f.eq,
          f.r2.toFixed(3),
        ]),
      ),
    );

    pairCap.textContent =
      `Trade-off I vs T: tanpa var vertikal di TOS=${floor}. ` +
      `Variasi: INV = a + b/(TOS − lantai).`;
    drawInventoryVsTos(pairCanvas, mapRows, oneLabel || null);
    pairTable.replaceChildren(
      tableHtml(
        ["Variability", "Model", "Rumus", "R²"],
        fitInvVsTos(mapRows).map((f) => [
          BUF_VAR_SHORT[f.die] ?? f.die,
          f.model,
          f.eq,
          f.r2.toFixed(3),
        ]),
      ),
    );
    scenTable.replaceChildren(
      tableHtml(
        ["Skenario", "Durasi", "Waktu di lapangan", "Inventory time"],
        mapRows.map((r) => {
          const short = BUF_VAR_SHORT[r.die] ?? r.die;
          return [
            `${short} ${r.mobilization}`,
            r.duration.toFixed(2),
            r.time_on_site.toFixed(2),
            r.inventory_time.toFixed(2),
          ];
        }),
      ),
    );
  }

  oneDlPng.addEventListener("click", () => {
    if (!oneResult) return;
    downloadCanvasPng(lobCanvas, `parade-buffer-lbs-${fileStamp()}.png`);
  });
  mapDlPareto.addEventListener("click", () => {
    if (!mapRows) return;
    downloadCanvasPng(paretoCanvas, `parade-buffer-pareto-${fileStamp()}.png`);
  });
  mapDlPair.addEventListener("click", () => {
    if (!mapRows) return;
    downloadCanvasPng(pairCanvas, `parade-buffer-inv-tos-${fileStamp()}.png`);
  });

  runOne.addEventListener("click", () => {
    err.textContent = "";
    try {
      const varKey = varSel.value;
      const mob = mobSel.value;
      oneResult = runTimeInventoryBuffer({
        die: varKey,
        mobilization: mob,
        totalUnits: shared.getZones(),
        seed: shared.getSeed(),
        nTrades: 5,
      });
      oneLabel = `${BUF_VAR_SHORT[varKey] ?? varKey} ${mob}`;
      renderOne();
      if (mapRows) renderMap();
    } catch (e) {
      err.textContent = e instanceof Error ? e.message : String(e);
    }
  });

  runMap.addEventListener("click", () => {
    err.textContent = "";
    try {
      runMap.disabled = true;
      runMap.textContent = "Menghitung…";
      // yield so UI updates
      setTimeout(() => {
        try {
          const raw = irisBufferSweep({
            totalUnits: shared.getZones(),
            seed: shared.getSeed(),
            nTrades: 5,
            nReps: 12,
          });
          mapRows = raw.map((r) => ({
            ...r,
            label: `${BUF_VAR_SHORT[r.die] ?? r.die} ${r.mobilization}`,
          }));
          renderMap();
        } catch (e) {
          err.textContent = e instanceof Error ? e.message : String(e);
        } finally {
          runMap.disabled = false;
          runMap.textContent = "Peta tren";
        }
      }, 20);
    } catch (e) {
      err.textContent = e instanceof Error ? e.message : String(e);
      runMap.disabled = false;
      runMap.textContent = "Peta tren";
    }
  });

  window.addEventListener("resize", () => {
    renderOne();
    renderMap();
  });
}
