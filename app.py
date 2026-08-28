"""Parade Tim Kerja – Streamlit app (model zone-flow untuk kelas)."""
from __future__ import annotations

import importlib
import math
import tempfile
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

import matplotlib.pyplot as plt
import streamlit as st
import streamlit.components.v1 as components

import parade_of_trades_analysis as _a
import parade_of_trades_core as _c
import parade_of_trades_plots as _p
import usage_stats as _stats

_c = importlib.reload(_c)
_p = importlib.reload(_p)
_a = importlib.reload(_a)

from parade_of_trades_analysis import (
    compute_cost_metrics,
    export_result_csv,
    export_result_excel,
export_comparison_excel,
export_comparison_csv,
export_takt_excel,
export_takt_csv,
    inventory_fill_rate_metrics,
    kingman_combined,
    kingman_metrics,
    littles_law_metrics,
    evaluate_at_wip,
    build_takt_plan,
    zone_rate_for_work,
    littles_takt_duration,
    takt_plan_from_lob_result,
    required_rate_for_duration,
    takt_design_table,
    takt_plan_reliability,
        )
from parade_of_trades_core import (
    CAPACITY_PRESETS,
    DEFAULT_TRADE_NAMES,
    ParadeConfig,
    ParadeOfTrades,
    ParadeResult,
    IRIS_DICE,
    IRIS_MOBILIZATION,
    run_time_inventory_buffer,
    iris_buffer_sweep,
    )
from parade_of_trades_plots import (
    plot_buffer_profile,
    plot_comparison_buffers,
    plot_comparison_lob,
    plot_comparison_utilization,
    plot_comparison_costs,
    plot_comparison_costs_by_trade,
    plot_kingman_stations,
    plot_inventory_fill_rate,
    plot_kingman_vut_curve,
    plot_line_of_balance,
    plot_line_of_balance_detail,
    plot_littles_law_wip,
    plot_takt_plan,
    plot_takt_wagon_chart,
                plot_wip_th_ct,
    plot_utilization,
    plot_time_inventory_pareto,
    fit_buffer_trends,
)

_APP_BUILD = "2026-08-28-buffer-ols-v108"
_APP_DIR = Path(__file__).resolve().parent
_ASSETS_DIR = _APP_DIR / "assets"
_HEADER_BANNER = _ASSETS_DIR / "header_banner.jpg"
_LOGO_ICON = _ASSETS_DIR / "logo_icon.jpg"
_MANUAL_PATH = _APP_DIR / "MANUAL.md"

st.set_page_config(
    page_title="Parade Tim Kerja",
    page_icon=str(_LOGO_ICON) if _LOGO_ICON.exists() else "🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

PRESET_OPTIONS = list(CAPACITY_PRESETS.keys())
VAR_FACTORS = {
    "no_variability": (1.0, 1.0),
    "low": (0.75, 1.25),
    "medium": (0.5, 1.5),
    "high": (0.25, 1.75),
    "very_high": (0.1, 1.9),
}
VAR_LABELS = {
    "no_variability": "Tanpa variability — kapasitas tetap tiap zona",
    "low": "Rendah — kapasitas zona ×0,75 atau ×1,25 (±25%)",
    "medium": "Sedang — kapasitas zona ×0,5 atau ×1,5 (±50%)",
    "high": "Tinggi — kapasitas zona ×0,25 atau ×1,75 (±75%)",
    "very_high": "Sangat tinggi — kapasitas zona ×0,1 atau ×1,9 (±90%)",
}
_BATCH_OPTIONS = [4, 5, 3, 2, 1]

_SPEED_CHOICES = [
    ("Sangat rendah — 1 zona / 3 periode", 1.0 / 3.0),
    ("Rendah — 1 zona / 2 periode", 0.5),
    ("Normal — 1 zona / 1 periode", 1.0),
    ("Tinggi — 2 zona / 1 periode", 2.0),
    ("Sangat tinggi — 3 zona / 1 periode", 3.0),
]


def _trade_name(i: int) -> str:
    return DEFAULT_TRADE_NAMES[i] if i < len(DEFAULT_TRADE_NAMES) else f"Trade {i + 1}"


def _batch_size() -> int:
    return int(st.session_state.get("batch_size", 4))


def _pair_from_base_and_var(base_speed: float, variability: str) -> Tuple:
    b = float(base_speed)
    f_lo, f_hi = VAR_FACTORS[variability]
    lo, hi = max(1e-9, b * f_lo), max(1e-9, b * f_hi)
    if abs(f_lo - f_hi) < 1e-12:
        return (lo, hi, 0.5, b, True)
    return (lo, hi, 0.5, b, False)


def _format_pair(spec: Tuple) -> str:
    b = float(spec[3]) if len(spec) >= 4 else 1.0
    det = bool(spec[4]) if len(spec) >= 5 else False
    lo, hi = float(spec[0]), float(spec[1])
    if det:
        mapping = {
            1 / 3: "1 zona/3 periode (tetap tiap zona)",
            0.5: "1 zona/2 periode (tetap tiap zona)",
            1.0: "1 zona/1 periode (tetap tiap zona)",
            2.0: "2 zona/1 periode (tetap tiap zona)",
            3.0: "3 zona/1 periode (tetap tiap zona)",
        }
        for k, lab in mapping.items():
            if abs(b - k) < 1e-9:
                return lab
        return f"{b:g} zona/periode (tetap tiap zona)"
    return f"rate zona {lo:g}–{hi:g} (var per zona)"


def _base_speed_input(key: str, label: str = "Kapasitas produksi (zona/periode)", default: float = 1.0) -> float:
    labels = [c[0] for c in _SPEED_CHOICES]
    values = {c[0]: c[1] for c in _SPEED_CHOICES}
    default_label = "Normal — 1 zona / 1 periode"
    best = 1e9
    for lab, val in _SPEED_CHOICES:
        if abs(val - default) < best:
            best, default_label = abs(val - default), lab
    choice = st.selectbox(label, labels, index=labels.index(default_label), key=f"{key}_profile")
    return float(values[choice])


def _render_parade_sim_banner() -> None:
    """One-piece parade: teams *slide* between zones; done blocks stay solid."""
    html = r"""
<!DOCTYPE html>
<html><head><meta charset="utf-8"/>
<style>
  :root {
    --t1:#3b82f6; --t2:#f59e0b; --t3:#10b981; --t4:#ef4444; --t5:#8b5cf6;
    --bg0:#0f2744; --bg1:#1a365d;
    --slide: 0.55s;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    font-family: system-ui, -apple-system, Segoe UI, sans-serif;
    background: transparent; color: #e8eef7;
  }
  .wrap {
    background: linear-gradient(135deg, var(--bg0) 0%, var(--bg1) 55%, #234e76 100%);
    border-radius: 14px; padding: 12px;
    box-shadow: 0 8px 28px rgba(15,39,68,.28);
  }
  .board {
    position: relative;
    border-radius: 12px;
    background: rgba(0,0,0,.14);
    padding: 8px 6px 10px;
  }
  .labels {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 8px;
    margin-bottom: 4px;
  }
  .labels span {
    text-align: center;
    font-size: 11px; font-weight: 700;
    color: rgba(255,255,255,.82);
    letter-spacing: .03em;
  }
  .lanes {
    position: relative;
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 8px;
    min-height: 92px;
  }
  .cell {
    border: 1px dashed rgba(255,255,255,.32);
    border-radius: 10px;
    background: rgba(255,255,255,.06);
    min-height: 92px;
    transition: background .3s, border-color .3s;
    position: relative;
  }
  .cell.done {
    background: rgba(148,163,184,.18);
    border-style: solid;
    border-color: rgba(148,163,184,.55);
  }
  /* Done badge sits inside cell, no animation loop */
  .done-badge {
    position: absolute;
    left: 50%; top: 50%;
    transform: translate(-50%, -50%);
    width: 88%; max-width: 112px;
    padding: 8px 6px;
    border-radius: 10px;
    text-align: center;
    font-weight: 800; font-size: 13px;
    background: linear-gradient(180deg, #e2e8f0, #cbd5e1);
    color: #0f172a;
    border: 1px solid rgba(15,23,42,.12);
    box-shadow: 0 4px 12px rgba(0,0,0,.2);
    opacity: 0;
    pointer-events: none;
    transition: opacity .35s ease;
  }
  .done-badge.on { opacity: 1; }

  /* Teams layer — slide via left% */
  .actors {
    position: absolute;
    left: 6px; right: 6px;
    top: 28px; /* below labels */
    height: 92px;
    pointer-events: none;
  }
  .team {
    position: absolute;
    top: 50%;
    width: calc(20% - 10px);
    max-width: 112px;
    transform: translate(-50%, -50%);
    padding: 8px 6px;
    border-radius: 10px;
    text-align: center;
    font-weight: 800; font-size: 13px;
    line-height: 1.15;
    box-shadow: 0 4px 14px rgba(0,0,0,.32);
    opacity: 0;
    left: 10%;
    transition:
      left var(--slide) cubic-bezier(.4,.0,.2,1),
      opacity .3s ease;
    will-change: left, opacity;
  }
  .team small {
    display: block; font-weight: 600; font-size: 10px;
    opacity: .92; margin-top: 2px;
  }
  .team.t1 { background: var(--t1); color:#fff; }
  .team.t2 { background: var(--t2); color:#1a1200; }
  .team.t3 { background: var(--t3); color:#fff; }
  .team.t4 { background: var(--t4); color:#fff; }
  .team.t5 { background: var(--t5); color:#fff; }
  .team.visible { opacity: 1; }

  @media (max-width: 560px) {
    .team small { display: none; }
    .lanes, .actors { min-height: 76px; height: 76px; }
    .cell { min-height: 76px; }
    .team { font-size: 12px; }
  }
</style>
</head>
<body>
<div class="wrap">
  <div class="board" id="board">
    <div class="labels">
      <span>Zona 1</span><span>Zona 2</span><span>Zona 3</span>
      <span>Zona 4</span><span>Zona 5</span>
    </div>
    <div class="lanes" id="lanes">
      <div class="cell" data-z="1"><div class="done-badge" id="done-1">✓ Selesai</div></div>
      <div class="cell" data-z="2"><div class="done-badge" id="done-2">✓ Selesai</div></div>
      <div class="cell" data-z="3"><div class="done-badge" id="done-3">✓ Selesai</div></div>
      <div class="cell" data-z="4"><div class="done-badge" id="done-4">✓ Selesai</div></div>
      <div class="cell" data-z="5"><div class="done-badge" id="done-5">✓ Selesai</div></div>
    </div>
    <div class="actors" id="actors"></div>
  </div>
</div>
<script>
(function () {
  const TEAMS = [
    { id: 1, name: "T1", job: "Bekisting", cls: "t1" },
    { id: 2, name: "T2", job: "Tulangan", cls: "t2" },
    { id: 3, name: "T3", job: "Cor", cls: "t3" },
    { id: 4, name: "T4", job: "Bongkar", cls: "t4" },
    { id: 5, name: "T5", job: "Finishing", cls: "t5" },
  ];
  const N = 5;
  const STEP_MS = 1000;
  const HOLD_END_MS = 1600;
  // Center of each zone column (of actors width)
  const ZONE_LEFT = { 1: "10%", 2: "30%", 3: "50%", 4: "70%", 5: "90%" };
  const OFF_LEFT = "-12%";
  const OFF_RIGHT = "112%";

  const actors = document.getElementById("actors");
  const teamEls = {};

  TEAMS.forEach(function (t) {
    const el = document.createElement("div");
    el.className = "team " + t.cls;
    el.id = "team-" + t.id;
    el.innerHTML = "<span>" + t.name + "</span><small>" + t.job + "</small>";
    el.style.left = OFF_LEFT;
    actors.appendChild(el);
    teamEls[t.id] = el;
  });

  function placeTeam(id, zone, visible) {
    const el = teamEls[id];
    if (!visible || zone < 1 || zone > N) {
      // Leave to the right if had been on board past Z5, else stay off-left
      if (el.dataset.zone && parseInt(el.dataset.zone, 10) === N) {
        el.style.left = OFF_RIGHT;
      } else if (!el.classList.contains("visible")) {
        el.style.left = OFF_LEFT;
      } else {
        // finished mid/end: slide out right if was on last, else fade off
        const z = parseInt(el.dataset.zone || "0", 10);
        if (z >= N) el.style.left = OFF_RIGHT;
        else if (z >= 1) {
          // slide out right after last zone only; for T1 after Z5
          el.style.left = OFF_RIGHT;
        }
      }
      el.classList.remove("visible");
      delete el.dataset.zone;
      return;
    }
    el.style.left = ZONE_LEFT[zone];
    el.classList.add("visible");
    el.dataset.zone = String(zone);
  }

  function setDone(z, on) {
    const badge = document.getElementById("done-" + z);
    const cell = document.querySelector('.cell[data-z="' + z + '"]');
    if (on) {
      badge.classList.add("on");
      cell.classList.add("done");
    } else {
      badge.classList.remove("on");
      cell.classList.remove("done");
    }
  }

  /*
    Period p (0 empty):
      team t in zone z = p - t + 1 (if 1..5)
      zone z done when p >= z + 5
  */
  function render(p) {
    for (let t = 1; t <= N; t++) {
      const z = p - t + 1;
      if (p > 0 && z >= 1 && z <= N) {
        placeTeam(t, z, true);
      } else {
        // hide: if previously active, slide out right when leaving after Z5
        const el = teamEls[t];
        const was = parseInt(el.dataset.zone || "0", 10);
        if (was > 0) {
          el.style.left = OFF_RIGHT;
          el.classList.remove("visible");
          // after transition, park off-left for next loop without flash
          setTimeout(function () {
            if (!el.classList.contains("visible")) {
              el.style.transition = "none";
              el.style.left = OFF_LEFT;
              // force reflow
              void el.offsetWidth;
              el.style.transition = "";
            }
          }, 560);
          delete el.dataset.zone;
        } else {
          placeTeam(t, 0, false);
        }
      }
    }
    for (let z = 1; z <= N; z++) {
      setDone(z, p >= z + 5);
    }
  }

  let p = 0;
  const MAX_P = 10;

  function tick() {
    render(p);
    if (p >= MAX_P) {
      setTimeout(function () {
        // reset teams quietly to off-left
        for (let t = 1; t <= N; t++) {
          const el = teamEls[t];
          el.classList.remove("visible");
          el.style.transition = "none";
          el.style.left = OFF_LEFT;
          void el.offsetWidth;
          el.style.transition = "";
          delete el.dataset.zone;
        }
        for (let z = 1; z <= N; z++) setDone(z, false);
        p = 0;
        render(0);
        setTimeout(function () {
          p = 1;
          schedule();
        }, 500);
      }, HOLD_END_MS);
      return;
    }
    p += 1;
    schedule();
  }

  function schedule() {
    setTimeout(tick, STEP_MS);
  }

  render(0);
  setTimeout(function () {
    p = 1;
    tick();
  }, 500);
})();
</script>
</body></html>
"""
    components.html(html, height=168, scrolling=False)


def _render_header() -> None:
    st.markdown(
        """<style>
        .pot-callout{background:linear-gradient(135deg,#f0f7ff,#eef9f3);border:1px solid #c5d9ec;
        border-radius:10px;padding:.75rem 1rem;margin:.4rem 0 .9rem;font-size:.92rem;color:#2d3748}
        .pot-field{background:#f7fafc;border-left:4px solid #2b6cb0;border-radius:0 8px 8px 0;
        padding:.65rem .9rem;margin:.35rem 0 .75rem;font-size:.9rem;color:#2d3748}
        .pot-warn{background:#fffaf0;border-left:4px solid #dd6b20;border-radius:0 8px 8px 0;
        padding:.65rem .9rem;margin:.35rem 0 .75rem;font-size:.9rem;color:#2d3748}
        </style>""",
        unsafe_allow_html=True,
    )
    # Animated parade sim replaces static photo banner
    _render_parade_sim_banner()
    if _LOGO_ICON.exists():
        c1, c2 = st.columns([1.6, 5], vertical_alignment="center")
        with c1:
            st.image(str(_LOGO_ICON), width=168)
        with c2:
            st.markdown("## Parade Tim Kerja")
            st.caption("Simulasi Parade Tim Kerja Pekerjaan Pengecoran Lantai Beton")
    else:
        st.title("Parade Tim Kerja")


def _build_config_from_pairs(
    pairs: Sequence[Tuple],
    total_units: int,
    seed: Optional[int],
    takt_rate=None,
    standby_capacity: int = 0,
    batch_size: Optional[int] = None,
) -> ParadeConfig:
    names = [_trade_name(i) for i in range(len(pairs))]
    bs = int(batch_size) if batch_size is not None else _batch_size()
    return ParadeConfig.from_pairs(
        pairs=list(pairs),
        trade_names=names,
        total_units=total_units,
        seed=seed,
        takt_rate=takt_rate,
        standby_capacity=standby_capacity,
        same_period_handoff=False,
        staggered_mobilization=False,
        zone_flow=True,
        batch_size=max(1, bs),
    )


def _capacity_setup(
    key_prefix: str,
    n_trades: int = 5,
    default_var: str = "no_variability",
    default_base: float = 1.0,
    show_help: bool = False,
) -> List[Tuple]:
    """UI pengaturan tim: seragam atau per tim (kapasitas + variability)."""
    mode = st.radio(
        "Pengaturan tim",
        ["Seragam (semua tim sama)", "Per tim (bisa berbeda)"],
        horizontal=True,
        key=f"{key_prefix}_speed_mode",
    )

    def _vi(name: str) -> int:
        return PRESET_OPTIONS.index(name) if name in PRESET_OPTIONS else 0

    if mode.startswith("Seragam"):
        base = _base_speed_input(f"{key_prefix}_base", "Kapasitas produksi (zona/periode)", default_base)
        var = st.selectbox(
            "Variability (perubahan kapasitas per zona)",
            PRESET_OPTIONS,
            index=_vi(default_var),
            format_func=lambda x: VAR_LABELS.get(x, x),
            key=f"{key_prefix}_var",
        )
        return [_pair_from_base_and_var(base, var)] * n_trades

    pairs: List[Tuple] = []
    for i in range(n_trades):
        with st.expander(f"Tim {i + 1}: {_trade_name(i)}", expanded=(i < 2)):
            base_i = _base_speed_input(f"{key_prefix}_base_t{i}", "Kapasitas produksi (zona/periode)", default_base)
            var_i = st.selectbox(
                "Variability (perubahan kapasitas per zona)",
                PRESET_OPTIONS,
                index=_vi(default_var),
                format_func=lambda x: VAR_LABELS.get(x, x),
                key=f"{key_prefix}_var_t{i}",
            )
            pairs.append(_pair_from_base_and_var(base_i, var_i))
    return pairs


def _peak_wip(result: ParadeResult) -> int:
    return max((sum(h.buffers) for h in result.history), default=0)



def _trade_costs(n_trades: int = 5) -> list:
    c = st.session_state.get("trade_costs")
    if not c or len(c) < n_trades:
        return [100.0] * n_trades
    return [float(x) for x in c[:n_trades]]


def _render_cost_block(result: ParadeResult, key: str = "cost") -> None:
    """Tampilkan biaya aktif / idle / total."""
    costs = _trade_costs(result.config.n_trades)
    cm = compute_cost_metrics(result, costs)
    st.markdown("##### Biaya")
    c1, c2, c3 = st.columns(3)
    c1.metric("Biaya aktif", f"{cm.total_active:,.0f}")
    c2.metric("Biaya idle", f"{cm.total_idle:,.0f}")
    c3.metric("Total biaya", f"{cm.total_cost:,.0f}")
    st.dataframe(cm.as_rows(), use_container_width=True, hide_index=True)
    st.caption(
        "Aktif = periode berproduksi setelah mulai · "
        "Idle = periode tanpa produksi (setelah mulai, sebelum selesai) · "
        "Biaya = periode × tarif/periode (sidebar)."
    )
    st.session_state[f"{key}_cost_metrics"] = cm


def _metrics_row(result: ParadeResult) -> None:
    cm = compute_cost_metrics(result, _trade_costs(result.config.n_trades))
    p_act = sum(t.periods_active for t in cm.trades)
    p_idle = sum(t.periods_idle for t in cm.trades)
    cols = st.columns(6)
    cols[0].metric(
        "Durasi proyek",
        f"{result.duration}",
        help="Kalender sampai tim terakhir selesai. Bukan jumlah periode aktif semua tim.",
    )
    cols[1].metric("Throughput", f"{result.system_throughput:.3f}")
    cols[2].metric(
        "Σ periode aktif",
        f"{p_act}",
        help="Jumlah periode-tim saat berproduksi (bisa > durasi karena 5 tim tumpang-tindih).",
    )
    cols[3].metric(
        "Σ periode idle",
        f"{p_idle}",
        help="Jumlah periode-tim menunggu zona (mulai…selesai kerja sendiri, prod=0).",
    )
    cols[4].metric("Biaya idle", f"{cm.total_idle:,.0f}")
    cols[5].metric("Total biaya", f"{cm.total_cost:,.0f}")


def _starts_caption(result: ParadeResult) -> str:
    starts = [t.start_period for t in result.trade_metrics]
    return "Mulai periode: " + " · ".join(f"T{i + 1}=p{s}" for i, s in enumerate(starts))


def _trade_table(result: ParadeResult) -> None:
    cm = compute_cost_metrics(result, _trade_costs(result.config.n_trades))
    rows = []
    for i, m in enumerate(result.trade_metrics):
        tc = cm.trades[i]
        tos = tc.periods_active + tc.periods_idle
        rows.append({
            "#": i + 1,
            "Tim": m.name,
            "Pace": result.config.trades[i].label(),
            "Mulai": m.start_period if m.start_period is not None else "—",
            "Selesai kerja": m.periods_to_finish,
            "Waktu lapangan": tos,
            "Periode aktif": tc.periods_active,
            "Periode idle": tc.periods_idle,
            "Tarif": tc.cost_per_period,
            "Biaya aktif": round(tc.cost_active, 0),
            "Biaya idle": round(tc.cost_idle, 0),
            "Biaya total": round(tc.cost_total, 0),
        })
    st.dataframe(rows, use_container_width=True, hide_index=True)


def _fig_to_st(fig) -> None:
    st.pyplot(fig, clear_figure=True)
    plt.close(fig)


def _export_block(result: ParadeResult, key: str, prefix: str = "parade_simulasi") -> None:
    """Unduh CSV + Excel hasil satu run (untuk presentasi / arsip)."""
    st.markdown("##### Unduh data")
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        hist = td_path / "history.csv"
        xlsx = td_path / "run.xlsx"
        export_result_csv(result, hist, include_history=True)
        export_result_excel(result, xlsx)
        summary = hist.with_name(hist.stem + "_summary.csv")
        c1, c2, c3 = st.columns(3)
        c1.download_button(
            "⬇ CSV riwayat",
            hist.read_bytes(),
            f"{prefix}_riwayat.csv",
            "text/csv",
            key=f"{key}_csv",
            use_container_width=True,
        )
        if summary.exists():
            c2.download_button(
                "⬇ CSV ringkasan",
                summary.read_bytes(),
                f"{prefix}_ringkasan.csv",
                "text/csv",
                key=f"{key}_csv_sum",
                use_container_width=True,
            )
        c3.download_button(
            "⬇ Excel lengkap",
            xlsx.read_bytes(),
            f"{prefix}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"{key}_xlsx",
            use_container_width=True,
        )


def _export_comparison_block(
    results: dict,
    meta: Optional[dict],
    key: str = "cmp",
) -> None:
    st.markdown("##### Unduh data perbandingan")
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        xlsx = td_path / "compare.xlsx"
        csv_path = td_path / "compare.csv"
        export_comparison_excel(results, xlsx, meta=meta)
        export_comparison_csv(results, csv_path, meta=meta)
        c1, c2 = st.columns(2)
        c1.download_button(
            "⬇ CSV ringkasan",
            csv_path.read_bytes(),
            "parade_perbandingan.csv",
            "text/csv",
            key=f"{key}_csv",
            use_container_width=True,
        )
        c2.download_button(
            "⬇ Excel lengkap",
            xlsx.read_bytes(),
            "parade_perbandingan.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"{key}_xlsx",
            use_container_width=True,
        )


def _export_takt_block(
    result: ParadeResult,
    plan,
    rel: Optional[dict],
    duration_plan: Optional[int] = None,
    buffers_info: Optional[dict] = None,
    key: str = "takt",
) -> None:
    st.markdown("##### Unduh data takt")
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        xlsx = td_path / "takt.xlsx"
        csv_path = td_path / "takt_cells.csv"
        export_takt_excel(
            result, plan, xlsx,
            reliability=rel,
            duration_plan=duration_plan,
            buffers_info=buffers_info,
        )
        export_takt_csv(result, plan, csv_path, reliability=rel)
        hist = csv_path.with_name(csv_path.stem + "_history.csv")
        c1, c2, c3 = st.columns(3)
        c1.download_button(
            "⬇ CSV sel takt",
            csv_path.read_bytes(),
            "parade_takt_sel.csv",
            "text/csv",
            key=f"{key}_csv",
            use_container_width=True,
        )
        if hist.exists():
            c2.download_button(
                "⬇ CSV riwayat",
                hist.read_bytes(),
                "parade_takt_riwayat.csv",
                "text/csv",
                key=f"{key}_csv_hist",
                use_container_width=True,
            )
        c3.download_button(
            "⬇ Excel lengkap",
            xlsx.read_bytes(),
            "parade_takt.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"{key}_xlsx",
            use_container_width=True,
        )


def _plot_single_result(result: ParadeResult) -> None:
    tab_lob, tab_buf, tab_util, tab_ll, tab_kg, tab_fr = st.tabs(
        ["Line of Balance", "Buffer / WIP", "Utilisasi", "Little's Law", "Kingman", "Inventory / FR"]
    )
    with tab_lob:
        fig, ax = plt.subplots(figsize=(10, 4.5))
        plot_line_of_balance_detail(result, ax=ax, max_period=min(16, result.duration + 1))
        fig.tight_layout()
        _fig_to_st(fig)
        fig, ax = plt.subplots(figsize=(10, 5.8))
        plot_line_of_balance(result, ax=ax)
        fig.tight_layout()
        _fig_to_st(fig)
    with tab_buf:
        c1, c2 = st.columns(2)
        with c1:
            fig, ax = plt.subplots(figsize=(6.2, 4.2))
            plot_buffer_profile(result, ax=ax, stacked=False)
            fig.tight_layout()
            _fig_to_st(fig)
        with c2:
            fig, ax = plt.subplots(figsize=(6.2, 4.2))
            plot_buffer_profile(result, ax=ax, stacked=True, show_max=False)
            fig.tight_layout()
            _fig_to_st(fig)
        # Peak WIP per interface
        peak_rows = [
            {
                "Buffer": f"B{j + 1}: {result.config.trades[j].name} → {result.config.trades[j + 1].name}",
                "Puncak WIP": result.max_buffer[j],
            }
            for j in range(result.config.n_interfaces)
        ]
        st.dataframe(peak_rows, use_container_width=True, hide_index=True)
    with tab_util:
        fig, ax = plt.subplots(figsize=(8, 3.8))
        plot_utilization(result, ax=ax)
        fig.tight_layout()
        _fig_to_st(fig)
        util_rows = []
        for i, m in enumerate(result.trade_metrics):
            util_rows.append({
                "Tim": m.name,
                "Produksi": m.total_production,
                "Kapasitas efektif": m.total_effective_capacity,
                "Idle": m.total_idle,
                "Utilisasi %": round(100.0 * m.utilization, 1),
            })
        st.dataframe(util_rows, use_container_width=True, hide_index=True)
    with tab_ll:
        ll = littles_law_metrics(result)
        c1, c2, c3 = st.columns(3)
        c1.metric("Throughput (TH)", f"{ll.throughput:.3f}", help="zona / periode")
        c2.metric("WIP pipeline ⌀", f"{ll.avg_pipeline_wip:.2f}", help="zona")
        c3.metric("CT pipeline", f"{ll.cycle_time_pipeline:.2f}", help="periode · WIP÷TH")
        d1, d2, d3 = st.columns(3)
        d1.metric("WIP buffer ⌀", f"{ll.avg_buffer_wip:.2f}")
        d2.metric("CT buffer", f"{ll.cycle_time_buffer:.2f}")
        d3.metric("TH × CT (cek)", f"{ll.check_pipeline:.2f}",
                  help="Harus ≈ WIP pipeline rata-rata")
        from parade_of_trades_analysis import littles_operations_curve as _loc
        _d = _loc(result)
        w_min = float(_d["w_min"])
        w_opt = float(_d["w_opt"])
        e1, e2, e3, e4 = st.columns(4)
        e1.metric("W_min (kritis)", f"{w_min:.2f}", help="W0 = TH_max × T0 — WIP minimal kasus terbaik")
        e2.metric("W_opt", f"{w_opt:.2f}", help="WIP optimal praktis (naik jika V>0): α·W0·(1+V·α/(1-α))")
        e3.metric("WIP operasi", f"{_d['op_wip']:.2f}")
        e4.metric("V (var factor)", f"{float(_d.get('v_factor', _d.get('v', 0))):.3f}")
        if abs(w_opt - w_min) < 1e-6:
            st.caption(
                "W_min = W_opt karena **variability ≈ 0** (kasus deterministik). "
                "Naikkan variability di Simulasi agar W_opt > W_min."
            )
        else:
            st.caption(
                f"W_opt > W_min karena ada variability (V={float(_d.get('v_factor', 0)):.3f}). "
                f"Butuh lebih banyak WIP untuk menjaga throughput tinggi."
            )

        # Slider CONWIP: fixed bounds + session state only (no value=) agar tidak error
        # saat digeser / saat metrik run berubah.
        conwip_default = float(_d["conwip"])
        _ck = "ll_conwip_level"
        _cmin = 0.5
        _cmax = float(max(float(result.config.total_units), w_opt * 4.0, w_min * 4.0, 20.0))
        # snap to 0.5 steps
        def _snap05(x: float) -> float:
            return round(float(x) * 2.0) / 2.0

        if _ck not in st.session_state:
            st.session_state[_ck] = _snap05(max(conwip_default, w_min))
        # clamp if out of range (e.g. after new run with different scale)
        try:
            cur = float(st.session_state[_ck])
        except (TypeError, ValueError):
            cur = conwip_default
        st.session_state[_ck] = _snap05(min(_cmax, max(_cmin, cur)))

        conwip_lvl = st.slider(
            "CONWIP — batas WIP konstan",
            min_value=_cmin,
            max_value=_cmax,
            step=0.5,
            key=_ck,
            help="Constant Work-In-Process: geser untuk memindahkan garis ungu di grafik.",
        )

        # Dampak CONWIP pada TH & CT (prediksi dari kurva operasi)
        _cw = evaluate_at_wip(result, float(conwip_lvl))
        st.markdown("**Prediksi jika CONWIP = {:.1f}**".format(float(conwip_lvl)))
        p1, p2, p3, p4 = st.columns(4)
        p1.metric(
            "TH @ CONWIP",
            f"{_cw['th']:.3f}",
            delta=f"{_cw['d_th']:+.3f} vs operasi",
            help="Throughput prediksi di batas CONWIP (kurva aktual)",
        )
        p2.metric(
            "CT @ CONWIP",
            f"{_cw['ct']:.2f}",
            delta=f"{_cw['d_ct']:+.2f} vs operasi",
            delta_color="inverse",
            help="Cycle time prediksi (periode). Naik = lebih lambat.",
        )
        p3.metric(
            "Δ WIP",
            f"{_cw['d_wip']:+.2f}",
            help="CONWIP − WIP operasi saat ini",
        )
        p4.metric(
            "TH batas @ WIP",
            f"{_cw['th_best']:.3f}",
            help="Throughput kasus terbaik (tanpa var) di WIP yang sama",
        )
        # short interpretation
        if _cw["d_wip"] < -0.25:
            st.caption(
                f"CONWIP **di bawah** operasi ({_cw['op_wip']:.1f}): inventory lebih ketat → "
                f"biasanya **CT turun** ({_cw['ct']:.2f} vs {_cw['op_ct']:.2f}), "
                f"TH bisa turun jika jauh di bawah W_opt ({_cw['w_opt']:.1f})."
            )
        elif _cw["d_wip"] > 0.25:
            st.caption(
                f"CONWIP **di atas** operasi ({_cw['op_wip']:.1f}): lebih longgar → "
                f"CT cenderung **naik** ({_cw['ct']:.2f}), TH mendekati plafon "
                f"(TH_max={_cw['th_max']:.2f}) tanpa banyak tambahan jika sudah jenuh."
            )
        else:
            st.caption(
                f"CONWIP ≈ WIP operasi ({_cw['op_wip']:.1f}): prediksi dekat dengan hasil run "
                f"(TH={_cw['op_th']:.3f}, CT={_cw['op_ct']:.2f})."
            )

        fig, ax = plt.subplots(figsize=(9.5, 5.2))
        plot_wip_th_ct(result, ax=ax, conwip_level=float(conwip_lvl))
        fig.tight_layout()
        _fig_to_st(fig)
        st.caption(
            f"**W_min**=W0=TH_max×T0={w_min:.2f} · "
            f"**W_opt**={w_opt:.2f} (V={float(_d.get('v_factor', 0)):.3f}) · "
            f"**CONWIP**={float(conwip_lvl):.1f} · "
            f"TH_max={_d['th_max']:.3f} · T0={_d['t0']:.2f}. "
            f"Pita ungu: W_min→CONWIP."
        )
        fig, ax = plt.subplots(figsize=(9, 4.0))
        plot_littles_law_wip(result, ax=ax)
        fig.tight_layout()
        _fig_to_st(fig)
        st.dataframe(ll.as_rows(), use_container_width=True, hide_index=True)

    with tab_kg:
        kg = kingman_metrics(result)
        comb = kingman_combined(result)
        a1, a2, a3, a4 = st.columns(4)
        a1.metric("u̅ gabungan", f"{comb['u_bar']:.3f}", help="Rata-rata utilisasi semua tim")
        a2.metric("V gabungan", f"{comb['v']:.3f}", help="(c_a²+c_e²)/2 rata-rata")
        a3.metric("CT Kingman (u̅)", f"{comb['ct']:.2f}", help="CT pada utilisasi gabungan")
        a4.metric("CT Little", f"{kg.system_ct_little:.2f}")
        # Main teaching chart: CT vs u
        fig, ax = plt.subplots(figsize=(9, 4.6))
        plot_kingman_vut_curve(result, ax=ax)
        fig.tight_layout()
        _fig_to_st(fig)
        # Per-station comparison
        fig, ax = plt.subplots(figsize=(9, 3.8))
        plot_kingman_stations(result, ax=ax)
        fig.tight_layout()
        _fig_to_st(fig)
        st.dataframe(kg.as_rows(), use_container_width=True, hide_index=True)
    with tab_fr:
        fr = inventory_fill_rate_metrics(result)
        b1, b2, b3 = st.columns(3)
        b1.metric("Inventory ⌀ (buffer)", f"{fr['avg_inventory_system']:.2f}", help="Rata-rata WIP di semua buffer")
        b2.metric("Fill rate sistem", f"{100 * fr['fill_rate_system']:.1f}%",
                  help="produksi / (produksi+idle) tim hilir")
        b3.metric("Fill rate T1", f"{100 * fr['fill_rate_t1']:.1f}%")
        fig, ax = plt.subplots(figsize=(9, 4.6))
        plot_inventory_fill_rate(result, ax=ax)
        fig.tight_layout()
        _fig_to_st(fig)
        rows = []
        for row in fr["interfaces"]:
            rows.append({
                "Buffer": row["buffer"],
                "Dari": row["from"][:18],
                "Ke": row["to"][:18],
                "Inventory ⌀": round(row["avg_inventory"], 3),
                "Puncak": row["peak_inventory"],
                "Fill rate %": round(100 * row["fill_rate"], 1),
                "Idle hilir": row["downstream_idle"],
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)


def render_sidebar():
    if _LOGO_ICON.exists():
        st.sidebar.image(str(_LOGO_ICON), use_container_width=True)
        st.sidebar.markdown("### Parade Tim Kerja")
        st.sidebar.caption("Simulasi parade tim kerja konstruksi")
    else:
        st.sidebar.title("Parade Tim Kerja")
        st.sidebar.caption("Simulasi parade tim kerja konstruksi")
    st.sidebar.divider()
    total_units = st.sidebar.number_input("Total zona", 1, 1000, 10, 1)
    use_seed = st.sidebar.checkbox("Kunci seed acak", True)
    seed = int(st.sidebar.number_input("Seed", 0, 10_000_000, 12345, 1)) if use_seed else None
    st.sidebar.divider()
    st.sidebar.selectbox(
        "Ukuran batch handoff",
        options=[4, 5, 3, 2, 1],
        index=0,
        format_func=lambda b: (
            f"{b} — Handoff tiap {b} zona (standar)" if b == 4
            else f"{b} — Handoff tiap {b} zona" if b > 1
            else "1 — One-piece flow (zona per zona)"
        ),
        key="batch_size",
        help="Default 4: kumpulkan 4 zona dulu baru dilepas ke tim hilir. "
             "1 = one-piece flow.",
    )
    st.sidebar.divider()
    st.sidebar.markdown("##### Biaya per periode")
    st.sidebar.caption("Tarif/periode · biaya = (periode aktif + periode idle) × tarif, per tim.")
    n_tr = 5
    names = list(DEFAULT_TRADE_NAMES[:n_tr]) if len(DEFAULT_TRADE_NAMES) >= n_tr else [f"Tim {i+1}" for i in range(n_tr)]
    costs = []
    for i, name in enumerate(names):
        short = name if len(name) <= 28 else name[:26] + "…"
        costs.append(float(st.sidebar.number_input(
            f"T{i+1} · {short}",
            min_value=0.0, max_value=1_000_000.0, value=100.0, step=10.0,
            key=f"cost_t{i}",
        )))
    st.session_state["trade_costs"] = costs
    _render_sidebar_stats()
    return int(total_units), seed, 5


def _cached_totals(*, force: bool = False) -> dict:
    import time
    now = time.time()
    if (
        not force
        and st.session_state.get("_stats_cache")
        and now - float(st.session_state.get("_stats_ts", 0)) < 45
    ):
        return st.session_state["_stats_cache"]
    s = _stats.totals()
    st.session_state["_stats_cache"] = s
    st.session_state["_stats_ts"] = now
    return s


def _track_app_visit() -> None:
    if st.session_state.get("_visit_logged"):
        return
    st.session_state["_visit_logged"] = True
    try:
        _stats.increment(_stats.KEY_APP_VISITS)
        _stats.increment(_stats.KEY_APP_SESSIONS)
        st.session_state.pop("_stats_cache", None)
    except Exception:
        pass


def _track_sim_run(kind: str = "sim") -> None:
    key = _stats.KEY_COMPARE_RUNS if kind == "compare" else _stats.KEY_SIM_RUNS
    try:
        _stats.increment(key)
        st.session_state["_sess_runs"] = int(st.session_state.get("_sess_runs", 0)) + 1
        st.session_state.pop("_stats_cache", None)
    except Exception:
        pass


def _render_sidebar_stats() -> None:
    s = _cached_totals()
    st.sidebar.divider()
    st.sidebar.markdown("##### Penggunaan")
    c1, c2 = st.sidebar.columns(2)
    c1.metric("Kunjungan", f"{s['total_visits']}")
    c2.metric("Simulasi", f"{s['total_simulations']}")
    st.sidebar.caption("Total kunjungan (landing + app) dan jumlah simulasi yang dijalankan.")


def tab_stats() -> None:
    st.subheader("Statistik penggunaan")
    st.caption(
        "Angka bersifat agregat (tanpa data pribadi). "
        "Kunjungan landing dihitung per buka halaman; unik landing = per perangkat (browser). "
        "Sesi aplikasi = setiap buka tab Streamlit. Simulasi = tombol Jalankan yang berhasil."
    )
    s = _cached_totals()
    a, b, c, d = st.columns(4)
    a.metric("Kunjungan landing", f"{s.get('landing_visits', 0)}")
    b.metric("Pengunjung landing (unik)", f"{s.get('landing_unique', 0)}")
    c.metric("Kunjungan aplikasi", f"{s.get('app_visits', 0)}")
    d.metric("Sesi aplikasi", f"{s.get('app_sessions', 0)}")
    e, f, g = st.columns(3)
    e.metric("Simulasi (tab Simulasi)", f"{s.get('sim_runs', 0)}")
    f.metric("Perbandingan", f"{s.get('compare_runs', 0)}")
    g.metric("Total simulasi dijalankan", f"{s['total_simulations']}")

    sess = int(st.session_state.get("_sess_runs", 0))
    st.caption(f"Simulasi di sesi Anda saat ini: **{sess}**.")

    rows = [
        {"Metrik": "Kunjungan landing", "Jumlah": s.get("landing_visits", 0)},
        {"Metrik": "Pengunjung unik (landing, per perangkat)", "Jumlah": s.get("landing_unique", 0)},
        {"Metrik": "Kunjungan aplikasi Streamlit", "Jumlah": s.get("app_visits", 0)},
        {"Metrik": "Sesi aplikasi", "Jumlah": s.get("app_sessions", 0)},
        {"Metrik": "Run tab Simulasi", "Jumlah": s.get("sim_runs", 0)},
        {"Metrik": "Run tab Perbandingan", "Jumlah": s.get("compare_runs", 0)},
        {"Metrik": "Total run simulasi", "Jumlah": s["total_simulations"]},
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)
    if st.button("Muat ulang angka", key="stats_refresh"):
        _cached_totals(force=True)
        st.rerun()



# ----- Tabs -----------------------------------------------------------------

def tab_single_run(total_units: int, seed: Optional[int], n_trades: int) -> None:
    st.subheader("Simulasi")
    pairs = _capacity_setup("single", n_trades, "no_variability", 1.0)
    b1, b2, _ = st.columns([1, 1, 2])
    run_c = b1.button("Jalankan", type="primary", use_container_width=True, key="single_run")
    reset_c = b2.button("Atur ulang", use_container_width=True, key="single_reset")
    if "single_result" not in st.session_state:
        st.session_state.single_result = None
    if reset_c:
        st.session_state.single_result = None
    if run_c:
        cfg = _build_config_from_pairs(pairs, total_units, seed)
        try:
            st.session_state.single_result = ParadeOfTrades(cfg).run()
            _track_sim_run("sim")
        except RuntimeError as exc:
            st.error(f"Simulasi gagal: {exc}")

    result = st.session_state.get("single_result")
    if not result or not result.history:
        return
    st.divider()
    _metrics_row(result)
    left, right = st.columns([1.25, 1])
    with left:
        _plot_single_result(result)
    with right:
        st.markdown("##### Metrik per tim")
        _trade_table(result)
        _render_cost_block(result, key="single")
        _export_block(result, "single", prefix="parade_simulasi")


def _batch_label(b: int) -> str:
    if b == 1:
        return "1 — One-piece"
    if b == 4:
        return "4 — Standar"
    return f"{b} — Handoff tiap {b} zona"


def tab_compare(total_units: int, seed: Optional[int], n_trades: int) -> None:
    st.subheader("Perbandingan")

    default_vars = list(PRESET_OPTIONS)
    sidebar_batch = _batch_size()

    # Quick-fill BEFORE widgets (mutate session_state first)
    c1, c2, c3, c4 = st.columns(4)
    fill_five = c1.button("5× variability", key="cmp_fill_five", use_container_width=True)
    fill_two = c2.button("Tanpa var vs Sedang", key="cmp_fill_two", use_container_width=True)
    fill_batch = c3.button("Batch 1 vs 4", key="cmp_fill_batch", use_container_width=True)
    clear_res = c4.button("Hapus hasil", key="cmp_clear", use_container_width=True)

    if clear_res:
        st.session_state.pop("cmp_multi", None)
        st.session_state.pop("cmp_meta", None)

    if fill_five:
        st.session_state["cmp_n_scen"] = 5
        for i, v in enumerate(default_vars):
            st.session_state[f"cmp_s{i}_label"] = f"Skenario {i + 1}"
            st.session_state[f"cmp_s{i}_var"] = v
            st.session_state[f"cmp_s{i}_profile"] = "Normal — 1 zona / 1 periode"
            st.session_state[f"cmp_s{i}_batch"] = sidebar_batch

    if fill_two:
        st.session_state["cmp_n_scen"] = 2
        st.session_state["cmp_s0_label"] = "Skenario 1"
        st.session_state["cmp_s0_var"] = "no_variability"
        st.session_state["cmp_s0_profile"] = "Normal — 1 zona / 1 periode"
        st.session_state["cmp_s0_batch"] = sidebar_batch
        st.session_state["cmp_s1_label"] = "Skenario 2"
        st.session_state["cmp_s1_var"] = "medium"
        st.session_state["cmp_s1_profile"] = "Normal — 1 zona / 1 periode"
        st.session_state["cmp_s1_batch"] = sidebar_batch

    if fill_batch:
        st.session_state["cmp_n_scen"] = 2
        st.session_state["cmp_s0_label"] = "Skenario 1"
        st.session_state["cmp_s0_var"] = "no_variability"
        st.session_state["cmp_s0_profile"] = "Normal — 1 zona / 1 periode"
        st.session_state["cmp_s0_batch"] = 1
        st.session_state["cmp_s1_label"] = "Skenario 2"
        st.session_state["cmp_s1_var"] = "no_variability"
        st.session_state["cmp_s1_profile"] = "Normal — 1 zona / 1 periode"
        st.session_state["cmp_s1_batch"] = 4

    st.session_state.setdefault("cmp_n_scen", 5)
    for i in range(5):
        dv = default_vars[i] if i < len(default_vars) else "no_variability"
        st.session_state.setdefault(f"cmp_s{i}_label", f"Skenario {i + 1}")
        st.session_state.setdefault(f"cmp_s{i}_var", dv)
        st.session_state.setdefault(f"cmp_s{i}_batch", sidebar_batch)

    n_scen = int(st.slider("Jumlah skenario", min_value=2, max_value=5, key="cmp_n_scen"))

    scenarios_cfg = []
    cols = st.columns(n_scen)
    for i in range(n_scen):
        with cols[i]:
            st.markdown(f"##### Skenario {i + 1}")
            label = f"Skenario {i + 1}"
            st.session_state[f"cmp_s{i}_label"] = label
            base = _base_speed_input(f"cmp_s{i}", "Kapasitas produksi (zona/periode)", 1.0)
            var = st.selectbox(
                "Variability (perubahan kapasitas per zona)",
                PRESET_OPTIONS,
                format_func=lambda x: VAR_LABELS.get(x, x),
                key=f"cmp_s{i}_var",
            )
            batch_i = int(
                st.selectbox(
                    "Batch handoff",
                    options=_BATCH_OPTIONS,
                    format_func=_batch_label,
                    key=f"cmp_s{i}_batch",
                )
            )
            spec = _pair_from_base_and_var(base, var)
            scenarios_cfg.append((label, spec, var, batch_i))

    if st.button("Jalankan perbandingan", type="primary", key="run_cmp", use_container_width=True):
        results = {}
        meta = {}
        errors = []
        for idx, (label, spec, var, batch_i) in enumerate(scenarios_cfg):
            name = f"Skenario {idx + 1}"
            pairs = [spec] * n_trades
            try:
                results[name] = ParadeOfTrades(
                    _build_config_from_pairs(pairs, total_units, seed, batch_size=batch_i)
                ).run()
                meta[name] = {
                    "label": label,
                    "var": var,
                    "var_label": VAR_LABELS.get(var, var),
                    "batch": batch_i,
                    "pace": _format_pair(spec),
                }
            except RuntimeError as exc:
                errors.append(f"{name}: {exc}")
        if errors:
            st.error("Gagal menjalankan:\n- " + "\n- ".join(errors))
        if results:
            st.session_state.cmp_multi = results
            st.session_state.cmp_meta = meta
            _track_sim_run("compare")

    if "cmp_multi" not in st.session_state:
        return

    results = st.session_state.cmp_multi
    meta = st.session_state.get("cmp_meta") or {}
    rows = []
    for name, r in results.items():
        m = meta.get(name, {})
        ll = littles_law_metrics(r)
        cm = compute_cost_metrics(r, _trade_costs(n_trades))
        rows.append({
            "Skenario": name,
            "Variability": m.get("var_label", "—"),
            "Batch": r.config.batch_size,
            "Pace": m.get("pace", r.config.trades[0].label()),
            "Durasi proyek": r.duration,
            "Σ periode aktif": sum(t.periods_active for t in cm.trades),
            "Σ periode idle": sum(t.periods_idle for t in cm.trades),
            "Biaya aktif": round(cm.total_active, 0),
            "Biaya idle": round(cm.total_idle, 0),
            "Total biaya": round(cm.total_cost, 0),
            "Idle cap. (unit)": r.total_idle_capacity,
            "Puncak WIP": _peak_wip(r),
            "TH": round(ll.throughput, 3),
            "T5 selesai": r.trade_metrics[-1].periods_to_finish,
        })
    st.divider()
    st.markdown("##### Ringkasan")
    st.dataframe(sorted(rows, key=lambda x: x["Durasi proyek"]), use_container_width=True, hide_index=True)
    _export_comparison_block(results, meta, key="cmp")

    # Precompute costs for charts
    cost_map = {}
    cost_rows_map = {}
    rates = _trade_costs(n_trades)
    for name, r in results.items():
        cm = compute_cost_metrics(r, rates)
        cost_map[name] = {
            "active": cm.total_active,
            "idle": cm.total_idle,
            "total": cm.total_cost,
        }
        cost_rows_map[name] = cm.trades

    tab_lob, tab_buf, tab_util, tab_cost, tab_ll, tab_kg, tab_fr = st.tabs(
        ["Line of Balance", "Buffer / WIP", "Utilisasi", "Biaya", "Little's Law", "Kingman", "Inventory / FR"]
    )
    with tab_lob:
        fig, ax = plt.subplots(figsize=(10, 5.5))
        plot_comparison_lob(
            results,
            ax=ax,
            title="Line of Balance — perbandingan skenario",
            last_trade_only=True,
        )
        fig.tight_layout()
        _fig_to_st(fig)
    with tab_buf:
        fig, ax = plt.subplots(figsize=(10, 5.0))
        plot_comparison_buffers(
            results,
            ax=ax,
            title="Buffer / WIP — perbandingan skenario",
        )
        fig.tight_layout()
        _fig_to_st(fig)
    with tab_util:
        fig, ax = plt.subplots(figsize=(10, 4.8))
        plot_comparison_utilization(
            results,
            ax=ax,
            title="Utilisasi per tim — perbandingan skenario",
        )
        fig.tight_layout()
        _fig_to_st(fig)
    with tab_cost:
        # verification table
        vrows = []
        for name, d in cost_map.items():
            a, i_, t = d["active"], d["idle"], d["total"]
            vrows.append({
                "Skenario": name,
                "Biaya aktif": round(a, 0),
                "Biaya idle": round(i_, 0),
                "Aktif+Idle": round(a + i_, 0),
                "Total": round(t, 0),
                "Cek": "OK" if abs((a + i_) - t) < 0.01 else "MISMATCH",
            })
        st.dataframe(vrows, use_container_width=True, hide_index=True)

        st.markdown("**Aktif vs idle (berdampingan)**")
        fig, ax = plt.subplots(figsize=(9.0, 4.0))
        plot_comparison_costs(cost_map, ax=ax, mode="grouped", title="Biaya aktif vs idle per skenario")
        fig.tight_layout()
        _fig_to_st(fig)

        st.caption("Durasi proyek ≠ Σ periode aktif (tim tumpang-tindih). Biaya memakai periode aktif/idle per tim.")
        st.markdown("**Aktif + idle (stacked) = total biaya**")
        fig, ax = plt.subplots(figsize=(9.0, 4.2))
        plot_comparison_costs(
            cost_map, ax=ax, mode="stacked",
            title="Stacked: biru=aktif, oranye=idle · Σ = total biaya",
        )
        fig.tight_layout()
        _fig_to_st(fig)

        c1, c2 = st.columns(2)
        with c1:
            fig, ax = plt.subplots(figsize=(5.5, 3.6))
            plot_comparison_costs(cost_map, ax=ax, mode="total", title="Total biaya per skenario")
            fig.tight_layout()
            _fig_to_st(fig)
        with c2:
            fig, ax = plt.subplots(figsize=(5.5, 3.6))
            plot_comparison_costs(cost_map, ax=ax, mode="idle", title="Biaya idle per skenario")
            fig.tight_layout()
            _fig_to_st(fig)

        st.markdown("**Per tim**")
        c3, c4 = st.columns(2)
        with c3:
            fig, ax = plt.subplots(figsize=(5.5, 3.8))
            plot_comparison_costs_by_trade(cost_rows_map, ax=ax, which="total", title="Biaya total per tim")
            fig.tight_layout()
            _fig_to_st(fig)
        with c4:
            fig, ax = plt.subplots(figsize=(5.5, 3.8))
            plot_comparison_costs_by_trade(cost_rows_map, ax=ax, which="idle", title="Biaya idle per tim")
            fig.tight_layout()
            _fig_to_st(fig)
    with tab_ll:
        from parade_of_trades_analysis import littles_operations_curve as _loc
        ll_rows = []
        for name, r in results.items():
            ll = littles_law_metrics(r)
            d = _loc(r)
            ll_rows.append({
                "Skenario": name,
                "TH": round(ll.throughput, 4),
                "WIP⌀": round(ll.avg_pipeline_wip, 3),
                "CT": round(ll.cycle_time_pipeline, 3),
                "W_min": round(d["w_min"], 2),
                "W_opt": round(d["w_opt"], 2),
                "CONWIP★": round(d["conwip"], 2),
                "WIP vs W_opt": round(ll.avg_pipeline_wip - d["w_opt"], 2),
            })
        st.dataframe(ll_rows, use_container_width=True, hide_index=True)
        st.caption(
            "W_min = W0 kritis (tanpa var). W_opt = α·W0·(1+V·α/(1-α)) — naik jika variability naik. "
            "Bila V=0 maka W_min=W_opt (bukan error). CONWIP★ ≈ W_opt."
        )
        # Dual-axis operating points: X=WIP, YL=TH, YR=CT
        import numpy as np
        names = list(results.keys())
        colors = ["#2563eb", "#ea580c", "#16a34a", "#dc2626", "#7c3aed"]
        fig, ax = plt.subplots(figsize=(9.5, 4.8))
        ax2 = ax.twinx()
        # reference landmarks from first scenario
        _d0 = _loc(results[names[0]])
        ax.axvline(_d0["w_min"], color="#15803d", linestyle="--", linewidth=1.2, alpha=0.8, label="W_min")
        ax.axvline(_d0["w_opt"], color="#c2410c", linestyle="--", linewidth=1.2, alpha=0.8, label="W_opt")
        ax.axvline(_d0["conwip"], color="#7c3aed", linestyle="-", linewidth=1.5, alpha=0.75, label="CONWIP★")
        for i, name in enumerate(names):
            ll = littles_law_metrics(results[name])
            c = colors[i % len(colors)]
            ax.scatter([ll.avg_pipeline_wip], [ll.throughput], s=90, color=c,
                       edgecolors="white", zorder=5, label=f"{name} TH")
            ax2.scatter([ll.avg_pipeline_wip], [ll.cycle_time_pipeline], s=90, color=c,
                        marker="s", edgecolors="white", zorder=5, alpha=0.85)
        ax.set_xlabel("WIP pipeline ⌀ (zona)")
        ax.set_ylabel("Throughput TH (zona/periode)", color="#2563eb")
        ax2.set_ylabel("Cycle time CT (periode)", color="#dc2626")
        ax.set_xlim(left=0)
        ax.set_ylim(bottom=0)
        ax2.set_ylim(bottom=0)
        ax.set_title("Titik operasi · X=WIP · Yₖᵢᵣᵢ=TH · Yₖₐₙₐₙ=CT (bandingkan ke W_min/W_opt di Simulasi)")
        ax.legend(loc="upper left", fontsize=7.5, framealpha=0.92)
        fig.tight_layout()
        _fig_to_st(fig)
        # bars secondary
        wips = [littles_law_metrics(results[n]).avg_pipeline_wip for n in names]
        cts = [littles_law_metrics(results[n]).cycle_time_pipeline for n in names]
        fig, axes = plt.subplots(1, 2, figsize=(10, 3.6))
        x = np.arange(len(names))
        axes[0].bar(x, wips, color="#1a365d", edgecolor="white")
        axes[0].set_xticks(x)
        axes[0].set_xticklabels(names, rotation=20, ha="right", fontsize=8)
        axes[0].set_ylabel("WIP pipeline ⌀")
        axes[0].set_title("WIP")
        axes[1].bar(x, cts, color="#2b6cb0", edgecolor="white")
        axes[1].set_xticks(x)
        axes[1].set_xticklabels(names, rotation=20, ha="right", fontsize=8)
        axes[1].set_ylabel("CT")
        axes[1].set_title("Cycle time")
        for a in axes:
            a.set_ylim(bottom=0)
        fig.tight_layout()
        _fig_to_st(fig)

    with tab_kg:
        kg_rows = []
        for name, r in results.items():
            kg = kingman_metrics(r)
            comb = kingman_combined(r)
            kg_rows.append({
                "Skenario": name,
                "u̅": round(comb["u_bar"], 3),
                "V": round(comb["v"], 3),
                "CT@u̅": round(comb["ct"], 3),
                "Σ CT Kingman": round(kg.sum_ct_kingman, 3),
                "CT Little": round(kg.system_ct_little, 3),
            })
        st.dataframe(kg_rows, use_container_width=True, hide_index=True)
        # Overlay operating points of each scenario on CT–u plane
        import numpy as np
        fig, ax = plt.subplots(figsize=(9, 4.6))
        t_e_ref = 1.0
        u_grid = np.linspace(0.01, 0.97, 200)
        for v, lab, color in [
            (0.0, "V=0", "#94a3b8"),
            (0.25, "V=0,25", "#f59e0b"),
            (0.5, "V=0,5", "#ef4444"),
            (1.0, "V=1,0", "#7c3aed"),
        ]:
            ct = [v * (u / (1 - u)) * t_e_ref + t_e_ref for u in u_grid]
            ax.plot(u_grid, ct, color=color, linewidth=1.4, label=lab)
        colors = ["#2563eb", "#ea580c", "#16a34a", "#dc2626", "#7c3aed"]
        for i, (name, r) in enumerate(results.items()):
            comb = kingman_combined(r)
            # scale: chart uses t_e=1 reference; plot actual CT and u
            ax.scatter(
                [min(comb["u_bar"], 0.97)],
                [comb["ct"]],
                s=80, zorder=5, color=colors[i % len(colors)],
                edgecolors="white", label=name,
            )
        ax.set_xlim(0, 1)
        ax.set_ylim(bottom=0)
        ax.set_xlabel("Utilisasi gabungan u̅")
        ax.set_ylabel("CT Kingman (periode/zona)")
        ax.set_title("Kingman: titik operasi skenario (CT vs u̅)")
        ax.legend(loc="upper left", fontsize=7.5, framealpha=0.92)
        fig.tight_layout()
        _fig_to_st(fig)
    with tab_fr:
        fr_rows = []
        for name, r in results.items():
            fr = inventory_fill_rate_metrics(r)
            fr_rows.append({
                "Skenario": name,
                "Inventory ⌀": round(fr["avg_inventory_system"], 3),
                "Fill rate %": round(100 * fr["fill_rate_system"], 1),
                "FR T1 %": round(100 * fr["fill_rate_t1"], 1),
            })
        st.dataframe(fr_rows, use_container_width=True, hide_index=True)
        import numpy as np
        fig, ax = plt.subplots(figsize=(9, 4.6))
        # theoretical curve from first scenario as backdrop
        first = next(iter(results.values()))
        plot_inventory_fill_rate(first, ax=ax, title="Fill rate vs inventory — titik skenario")
        colors = ["#2563eb", "#ea580c", "#16a34a", "#dc2626", "#7c3aed"]
        # re-scatter all scenarios on top
        for i, (name, r) in enumerate(results.items()):
            fr = inventory_fill_rate_metrics(r)
            ax.scatter(
                [100 * fr["fill_rate_system"]], [fr["avg_inventory_system"]],
                s=100, zorder=6, color=colors[i % len(colors)],
                edgecolors="white", label=name,
            )
        ax.legend(loc="upper left", fontsize=7.5, framealpha=0.92)
        fig.tight_layout()
        _fig_to_st(fig)

    with st.expander("Detail tim satu skenario"):
        pick = st.selectbox("Skenario", list(results.keys()), key="cmp_detail_pick")
        _trade_table(results[pick])




def tab_takt(total_units: int, seed: Optional[int], n_trades: int) -> None:
    """Takt: 360 m² / 40 bay fix; TZ bisa diubah (default 10); waktu/lantai default 15."""
    st.subheader("Takt plan")

    BAY_M = 3.0
    BAY_AREA = 9.0
    AREA_FLOOR = 360.0
    N_BAY = int(AREA_FLOOR / BAY_AREA)  # 40
    TW = 5
    CAP_DEFAULT = 4.0  # bay/hari/tim

    st.caption(
        f"Kasus: gedung bertingkat **n lantai**, tiap lantai **{AREA_FLOOR:g} m²**, "
        f"bay **{BAY_M:g}×{BAY_M:g} m** (={BAY_AREA:g} m²) → **{N_BAY} bay**/lantai. "
        f"**Bay ≠ zona** — jumlah zona ditetapkan di pengaturan. Train **{TW} tim** (fix)."
    )

    st.markdown("##### Pengaturan")
    c1, c2, c3, c4 = st.columns(4)
    n_floors = int(c1.number_input(
        "Jumlah lantai (n)",
        min_value=1, max_value=50, value=1, step=1,
        key="takt_n_floors",
    ))
    _tz_opts = [d for d in (1, 5, 10, 20, 40) if N_BAY % d == 0]
    tz = int(c2.selectbox(
        "Jumlah zona / lantai (TZ)",
        options=_tz_opts,
        index=_tz_opts.index(10) if 10 in _tz_opts else 0,
        format_func=lambda z: f"{z} zona · {N_BAY // z} bay/zona · {AREA_FLOOR / z:.0f} m²/zona",
        key="takt_tz",
        help=f"Hanya pembagi {N_BAY} bay agar bay/zona bilangan bulat: {_tz_opts}.",
    ))
    t_per_floor = float(c3.number_input(
        "Waktu tersedia per lantai (hari)",
        min_value=0.5, max_value=1_000.0, value=15.0, step=0.5,
        key="takt_days_per_floor",
    ))
    cap_bay = float(c4.number_input(
        "Kapasitas (bay / hari / tim)",
        min_value=0.25, max_value=20.0, value=CAP_DEFAULT, step=0.25,
        key="takt_cap_bay_day",
        help="Default Normal = 4 bay/hari.",
    ))

    bays_per_zone = N_BAY / max(tz, 1)
    area_per_zone = AREA_FLOOR / max(tz, 1)
    # zona/hari = (bay/hari) / (bay/zona)
    cap_zone = cap_bay / max(bays_per_zone, 1e-9)
    te = 1.0 / max(cap_zone, 1e-9)
    t0 = tz * te
    tw = TW
    td_floor = float(littles_takt_duration(tw, tz, te))
    rate = float(cap_zone)

    st.markdown("##### Mapping bay → zona")
    g1, g2, g3, g4 = st.columns(4)
    g1.metric("Bay / lantai", f"{N_BAY}")
    g2.metric("Zona (TZ)", f"{tz}")
    g3.metric("Bay / zona", f"{int(round(bays_per_zone))}")
    g4.metric("m² / zona", f"{area_per_zone:.1f}")

    st.caption(
        f"{N_BAY} bay ÷ {tz} zona = **{int(round(bays_per_zone))} bay/zona** "
        f"(**{area_per_zone:.0f} m²**/zona). "
        f"Kapasitas {cap_bay:g} bay/hari = **{cap_zone:.3g} zona/hari**."
    )

    st.markdown("##### Hasil (Little's Takt Law)")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("tₑ (hari/zona)", f"{te:.3g}")
    m2.metric("T₀ (1 tim, 1 lantai)", f"{t0:.2f} hari")
    m3.metric("TD / lantai", f"{td_floor:.2f} hari")
    m4.metric("Waktu / lantai", f"{t_per_floor:g} hari")

    st.caption(
        f"**TD = (TW + TZ − 1) × tₑ = ({tw} + {tz} − 1) × {te:.4g} = {td_floor:.2f}** hari/lantai.  \n"
        f"Waktu tersedia per lantai = **{t_per_floor:g}** hari."
    )

    if td_floor <= t_per_floor + 1e-9:
        st.success(f"Per lantai: TD **{td_floor:.2f}** ≤ **{t_per_floor:g}** hari.")
    else:
        st.warning(
            f"Per lantai: TD **{td_floor:.2f}** > **{t_per_floor:g}** hari — "
            "naikkan kapasitas, ubah TZ, atau longgarkan waktu."
        )

    st.markdown("##### Wagon chart (satu lantai)")
    plan = build_takt_plan(tw, tz, 1, rate, 1, total_work=None)
    fig_w = max(5.5, min(9.0, 0.15 * max(td_floor, 1) + 3.0))
    fig_h = max(3.0, min(7.0, 0.16 * tz + 1.8))
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    plot_takt_wagon_chart(
        plan, ax=ax, max_zones=None, compact=True,
        title=f"TZ={tz} · {bays_per_zone:.1f} bay/zona · {cap_zone:.2g} z/hari · TD={td_floor:.1f}d",
    )
    fig.tight_layout()
    _fig_to_st(fig)



def tab_manual() -> None:
    st.subheader("📖 Manual")
    if _MANUAL_PATH.exists():
        st.download_button(
            "⬇ Unduh MANUAL.md",
            data=_MANUAL_PATH.read_text(encoding="utf-8").encode("utf-8"),
            file_name="Parade_Tim_Kerja_Manual.md",
            mime="text/markdown",
            key="manual_dl",
        )
        st.markdown(_MANUAL_PATH.read_text(encoding="utf-8"))
    else:
        st.warning("MANUAL.md tidak ditemukan di repo.")

    st.divider()
    st.caption(f"Build `{_APP_BUILD}` · zone-flow · 5 tim · batch default 4")


def tab_buffer(seed: Optional[int]) -> None:
    """Time–inventory buffer lab (Iris). Mean capacity fixed; no extra crews."""
    st.subheader("Buffer")
    st.caption(
        "Simulasi **time–inventory buffer**. Kapasitas rata-rata tetap (mean 5). "
        "Yang diubah: kapan tim masuk. Inventory buffer muncul sebagai akibat."
    )
    left, right = st.columns([1.15, 1])
    with left:
        die = st.selectbox(
            "Dadu (mean 5)",
            list(IRIS_DICE.keys()),
            index=0,
            format_func=lambda d: {
                "5-5": "5–5 — tanpa variasi",
                "4-6": "4–6 — variasi rendah",
                "3-7": "3–7 — variasi lebih tinggi",
            }.get(d, d),
            key="buf_die",
        )
        mob = st.selectbox(
            "Buffer waktu (mobilisasi T1…T5)",
            list(IRIS_MOBILIZATION.keys()),
            index=0,
            key="buf_mob",
        )
        b1, b2 = st.columns(2)
        run_one = b1.button("Jalankan", type="primary", use_container_width=True, key="buf_run")
        run_map = b2.button("Peta tren", use_container_width=True, key="buf_map_btn")

    if run_one:
        try:
            st.session_state.buffer_one_result = run_time_inventory_buffer(
                die=die, mobilization=mob, total_units=100, seed=seed
            )
            st.session_state.buffer_one_label = f"{die} {mob}"
        except RuntimeError as exc:
            st.error(str(exc))
    if run_map:
        try:
            raw = iris_buffer_sweep(total_units=100, seed=seed)
            st.session_state.buffer_map_rows = [
                {k: v for k, v in r.items() if k != "result"} for r in raw
            ]
        except RuntimeError as exc:
            st.error(str(exc))

    one = st.session_state.get("buffer_one_result")
    if one is not None:
        st.divider()
        st.markdown(f"##### Hasil `{st.session_state.get('buffer_one_label', '')}`")
        c1, c2, c3 = st.columns(3)
        c1.metric("Durasi", f"{one.duration}")
        c2.metric("Time on site", f"{one.total_time_on_site}")
        c3.metric("Inventory time", f"{one.total_inventory_time}")
        fig, ax = plt.subplots(figsize=(8.5, 3.8))
        plot_line_of_balance(one, ax=ax, title="Line of Balance")
        fig.tight_layout()
        _fig_to_st(fig)

    rows = st.session_state.get("buffer_map_rows")
    if rows:
        st.divider()
        st.markdown("##### Peta time–inventory (kapasitas tetap)")
        st.caption(
            "Titik redup = semua pola. Titik sedang = rata-rata per durasi. "
            "Garis putus-putus = rumus regresi pada rata-rata itu "
            "(5–5 linier; 4–6 dan 3–7 kuadratik)."
        )
        fig, ax = plt.subplots(figsize=(9.2, 5.0))
        plot_time_inventory_pareto(
            rows, ax=ax, highlight=st.session_state.get("buffer_one_label")
        )
        fig.tight_layout()
        _fig_to_st(fig)
        fits = fit_buffer_trends(rows)
        eq_rows = [
            {
                "Dadu": f["die"],
                "Metrik": "Time on site" if f["metric"] == "time_on_site" else "Inventory time",
                "Model": "Linier" if f["degree"] == 1 else "Kuadratik",
                "Rumus": f["eq"],
                "R²": round(f["r2"], 3),
            }
            for f in fits
        ]
        st.dataframe(eq_rows, use_container_width=True, hide_index=True)
        with st.expander("Tabel semua skenario"):
            table = [
                {
                    "Skenario": r["label"],
                    "Durasi": r["duration"],
                    "Time on site": r["time_on_site"],
                    "Inventory time": r["inventory_time"],
                }
                for r in rows
            ]
            st.dataframe(table, use_container_width=True, hide_index=True)


def main() -> None:
    _track_app_visit()
    total_units, seed, n_trades = render_sidebar()
    _render_header()
    tabs = st.tabs(["Simulasi", "Perbandingan", "Takt plan", "Buffer", "Statistik", "Manual"])
    with tabs[0]:
        tab_single_run(total_units, seed, n_trades)
    with tabs[1]:
        tab_compare(total_units, seed, n_trades)
    with tabs[2]:
        tab_takt(total_units, seed, n_trades)
    with tabs[3]:
        tab_buffer(seed)
    with tabs[4]:
        tab_stats()
    with tabs[5]:
        tab_manual()


if __name__ == "__main__":
    main()
