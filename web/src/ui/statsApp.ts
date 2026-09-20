/**
 * Statistik penggunaan — Counter API (NS parade-tim-kerja.app).
 */

import { KEYS, readDashboard } from "../stats";

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

const SESS_KEY = "parade_tim_kerja_sess_runs";

export function bumpSessionRuns(): void {
  try {
    const n = Number(sessionStorage.getItem(SESS_KEY) || "0") + 1;
    sessionStorage.setItem(SESS_KEY, String(n));
  } catch {
    /* ignore */
  }
}

export function getSessionRuns(): number {
  try {
    return Number(sessionStorage.getItem(SESS_KEY) || "0");
  } catch {
    return 0;
  }
}

export function mountStats(root: HTMLElement): void {
  root.replaceChildren();

  const metrics1 = el("div", { className: "metrics" });
  const metrics2 = el("div", { className: "metrics" });
  const sessCap = el("p", { className: "note" });
  const tableHost = el("div", { className: "table-wrap" });
  const refresh = el("button", { type: "button" }, ["Muat ulang angka"]);
  const status = el("p", { className: "note" }, ["Memuat…"]);

  root.append(
    el("div", { className: "panel mode-panel" }, [
      el("h2", {}, ["Statistik penggunaan"]),
      el("p", { className: "note" }, [
        "Angka bersifat agregat (tanpa data pribadi). ",
        "Kunjungan landing dihitung per buka halaman; unik landing = per perangkat (browser). ",
        "Sesi aplikasi = setiap buka tab. Simulasi = tombol Jalankan yang berhasil.",
      ]),
      metrics1,
      metrics2,
      sessCap,
      tableHost,
      el("div", { className: "btn-row" }, [refresh]),
      status,
    ]),
  );

  async function load(): Promise<void> {
    status.textContent = "Memuat…";
    const dash = await readDashboard();
    const landing = dash[KEYS.landingVisits] ?? 0;
    const landingU = dash[KEYS.landingUnique] ?? 0;
    const appV = dash[KEYS.appVisits] ?? 0;
    const appS = dash[KEYS.appSessions] ?? 0;
    const sim = dash[KEYS.simRuns] ?? 0;
    const cmp = dash[KEYS.compareRuns] ?? 0;
    const totalSim = sim + cmp;

    metrics1.replaceChildren(
      metric("Kunjungan landing", String(landing)),
      metric("Pengunjung landing (unik)", String(landingU)),
      metric("Kunjungan aplikasi", String(appV)),
      metric("Sesi aplikasi", String(appS)),
    );
    metrics2.replaceChildren(
      metric("Simulasi (tab Simulasi)", String(sim)),
      metric("Perbandingan", String(cmp)),
      metric("Total simulasi dijalankan", String(totalSim)),
    );
    sessCap.innerHTML = `Simulasi di sesi Anda saat ini: <strong>${getSessionRuns()}</strong>.`;

    const rows = [
      ["Kunjungan landing", landing],
      ["Pengunjung unik (landing, per perangkat)", landingU],
      ["Kunjungan aplikasi", appV],
      ["Sesi aplikasi", appS],
      ["Run tab Simulasi", sim],
      ["Run tab Perbandingan", cmp],
      ["Total run simulasi", totalSim],
    ];
    const table = el("table");
    const thead = el("thead");
    const hr = el("tr");
    hr.append(el("th", {}, ["Metrik"]), el("th", {}, ["Jumlah"]));
    thead.append(hr);
    const tbody = el("tbody");
    for (const [m, n] of rows) {
      const tr = el("tr");
      tr.append(el("td", {}, [String(m)]), el("td", {}, [String(n)]));
      tbody.append(tr);
    }
    table.append(thead, tbody);
    tableHost.replaceChildren(table);
    status.textContent = `Namespace Counter: parade-tim-kerja.app · ${new Date().toLocaleTimeString("id-ID")}`;
  }

  refresh.addEventListener("click", () => void load());
  void load();
}
