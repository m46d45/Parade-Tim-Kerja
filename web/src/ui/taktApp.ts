/**
 * Takt plan mode — Little's Takt Law + wagon chart (Streamlit tab_takt).
 */

import {
  TAKT_FLOOR,
  computeTaktClassroom,
  taktTzOptions,
} from "../core";
import { downloadCanvasPng } from "./download";
import { drawTaktWagonChart } from "./taktChart";

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

export function mountTakt(root: HTMLElement): void {
  root.replaceChildren();

  const tzOpts = taktTzOptions();
  let tz = tzOpts.includes(10) ? 10 : tzOpts[0];
  let nFloors = 1;
  let tPerFloor = 15;
  let capBay: number = TAKT_FLOOR.capDefault;

  const caption = el("p", { className: "note" }, [
    `Kasus: gedung bertingkat n lantai, tiap lantai ${TAKT_FLOOR.areaFloor} m², ` +
      `bay ${TAKT_FLOOR.bayM}×${TAKT_FLOOR.bayM} m (=${TAKT_FLOOR.bayArea} m²) → ` +
      `${TAKT_FLOOR.nBay} bay/lantai. Bay ≠ zona — jumlah zona di pengaturan. ` +
      `Train ${TAKT_FLOOR.tw} tim (OPF).`,
  ]);

  const floorsIn = el("input", {
    type: "number",
    id: "takt-floors",
    min: "1",
    max: "50",
    step: "1",
    value: String(nFloors),
  }) as HTMLInputElement;
  const tzSel = el("select", { id: "takt-tz" }) as HTMLSelectElement;
  for (const z of tzOpts) {
    const bays = TAKT_FLOOR.nBay / z;
    const area = TAKT_FLOOR.areaFloor / z;
    const opt = el("option", { value: String(z) }, [
      `${z} zona · ${bays} bay/zona · ${area.toFixed(0)} m²/zona`,
    ]);
    if (z === tz) opt.selected = true;
    tzSel.append(opt);
  }
  const daysIn = el("input", {
    type: "number",
    id: "takt-days",
    min: "0.5",
    max: "1000",
    step: "0.5",
    value: String(tPerFloor),
  }) as HTMLInputElement;
  const capIn = el("input", {
    type: "number",
    id: "takt-cap",
    min: "0.25",
    max: "20",
    step: "0.25",
    value: String(capBay),
  }) as HTMLInputElement;

  const mapMetrics = el("div", { className: "metrics" });
  const resultMetrics = el("div", { className: "metrics" });
  const formula = el("p", { className: "note" });
  const status = el("p", { className: "takt-status" });
  const chartWrap = el("div", { className: "chart-wrap" });
  const canvas = el("canvas", { id: "takt-wagon" }) as HTMLCanvasElement;
  chartWrap.append(canvas);

  const dlBar = el("div", { className: "download-bar" });
  const dlPng = el("button", { type: "button", className: "ghost" }, [
    "Unduh chart PNG",
  ]);
  dlBar.append(dlPng);

  const controls = el("div", { className: "takt-controls" }, [
    el("h3", { className: "subchart-title" }, ["Pengaturan"]),
    el("div", { className: "takt-grid" }, [
      field("Jumlah lantai (n)", "takt-floors", floorsIn),
      field("Jumlah zona / lantai (TZ)", "takt-tz", tzSel),
      field("Waktu tersedia per lantai (hari)", "takt-days", daysIn),
      field("Kapasitas (bay / hari / tim)", "takt-cap", capIn),
    ]),
  ]);

  root.append(
    el("div", { className: "panel mode-panel" }, [
      el("h2", {}, ["Takt plan"]),
      caption,
      controls,
      el("h3", { className: "subchart-title" }, ["Mapping bay → zona"]),
      mapMetrics,
      el("h3", { className: "subchart-title" }, ["Hasil (Little's Takt Law)"]),
      resultMetrics,
      formula,
      status,
      el("h3", { className: "subchart-title" }, ["Wagon chart (satu lantai)"]),
      dlBar,
      chartWrap,
    ]),
  );

  function render(): void {
    nFloors = Math.max(1, Number(floorsIn.value) || 1);
    tz = Math.max(1, Number(tzSel.value) || 10);
    tPerFloor = Math.max(0.5, Number(daysIn.value) || 15);
    capBay = Math.max(0.25, Number(capIn.value) || 4);
    void nFloors;

    const r = computeTaktClassroom({ tz, capBayPerDay: capBay, tPerFloor });
    mapMetrics.replaceChildren(
      metric("Bay / lantai", String(TAKT_FLOOR.nBay)),
      metric("Zona (TZ)", String(tz)),
      metric("Bay / zona", String(Math.round(r.baysPerZone))),
      metric("m² / zona", r.areaPerZone.toFixed(1)),
    );
    resultMetrics.replaceChildren(
      metric("tₑ (hari/zona)", r.te.toPrecision(3)),
      metric("T₀ (1 tim, 1 lantai)", `${r.t0.toFixed(2)} hari`),
      metric("TD / lantai", `${r.tdFloor.toFixed(2)} hari`),
      metric("Waktu / lantai", `${tPerFloor} hari`),
    );
    formula.textContent =
      `TD = (TW + TZ − 1) × tₑ = (${TAKT_FLOOR.tw} + ${tz} − 1) × ${r.te.toPrecision(4)} = ${r.tdFloor.toFixed(2)} hari/lantai. ` +
      `Waktu tersedia per lantai = ${tPerFloor} hari. ` +
      `${TAKT_FLOOR.nBay} bay ÷ ${tz} zona = ${Math.round(r.baysPerZone)} bay/zona ` +
      `(${r.areaPerZone.toFixed(0)} m²/zona). Kapasitas ${capBay} bay/hari = ${r.capZone.toPrecision(3)} zona/hari.`;

    status.className = r.ok ? "takt-status ok" : "takt-status warn";
    status.textContent = r.ok
      ? `Per lantai: TD ${r.tdFloor.toFixed(2)} ≤ ${tPerFloor} hari.`
      : `Per lantai: TD ${r.tdFloor.toFixed(2)} > ${tPerFloor} hari — naikkan kapasitas, ubah TZ, atau longgarkan waktu.`;

    drawTaktWagonChart(
      canvas,
      r.plan,
      `TZ=${tz} · ${r.baysPerZone.toFixed(1)} bay/zona · ${r.capZone.toPrecision(2)} z/hari · TD=${r.tdFloor.toFixed(1)}d`,
    );
  }

  dlPng.addEventListener("click", () => {
    downloadCanvasPng(canvas, `parade-takt-wagon-${fileStamp()}.png`);
  });
  floorsIn.addEventListener("change", render);
  tzSel.addEventListener("change", render);
  daysIn.addEventListener("change", render);
  daysIn.addEventListener("input", render);
  capIn.addEventListener("change", render);
  capIn.addEventListener("input", render);
  window.addEventListener("resize", render);
  render();
}
