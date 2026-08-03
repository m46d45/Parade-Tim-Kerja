"""Parade Tim Kerja – Streamlit app (model zone-flow untuk kelas)."""
from __future__ import annotations

import importlib
import tempfile
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

import matplotlib.pyplot as plt
import streamlit as st
import streamlit.components.v1 as components

import parade_of_trades_analysis as _a
import parade_of_trades_core as _c
import parade_of_trades_plots as _p

_c = importlib.reload(_c)
_p = importlib.reload(_p)
_a = importlib.reload(_a)

from parade_of_trades_analysis import (
    export_result_csv,
    export_result_excel,
    inventory_fill_rate_metrics,
    kingman_combined,
    kingman_metrics,
    littles_law_metrics,
    build_takt_plan,
    build_takt_plan_with_buffers,
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
    tommelein2020_scenarios,
)
from parade_of_trades_plots import (
    plot_buffer_profile,
    plot_comparison_buffers,
    plot_comparison_lob,
    plot_comparison_utilization,
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
)

_APP_BUILD = "2026-08-03-curve-plus5-v56"
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


def _metrics_row(result: ParadeResult) -> None:
    cols = st.columns(6)
    cols[0].metric("Durasi", f"{result.duration}")
    cols[1].metric("vs Ideal", f"{result.duration - result.ideal_duration:+.1f}")
    cols[2].metric("Throughput", f"{result.system_throughput:.3f}")
    cols[3].metric("Idle total", f"{result.total_idle_capacity}")
    cols[4].metric("Puncak WIP", f"{_peak_wip(result)}")
    cols[5].metric("Batch", f"{result.config.batch_size}")


def _starts_caption(result: ParadeResult) -> str:
    starts = [t.start_period for t in result.trade_metrics]
    return "Mulai periode: " + " · ".join(f"T{i + 1}=p{s}" for i, s in enumerate(starts))


def _trade_table(result: ParadeResult) -> None:
    rows = []
    for i, m in enumerate(result.trade_metrics):
        rows.append({
            "#": i + 1,
            "Tim": m.name,
            "Pace": result.config.trades[i].label(),
            "Produksi": m.total_production,
            "Idle": m.total_idle,
            "Mulai": m.start_period if m.start_period is not None else "—",
            "Selesai": m.periods_to_finish,
            "Waktu di lapangan": m.time_on_site,
        })
    st.dataframe(rows, use_container_width=True, hide_index=True)


def _fig_to_st(fig) -> None:
    st.pyplot(fig, clear_figure=True)
    plt.close(fig)


def _export_block(result: ParadeResult, key: str) -> None:
    st.markdown("##### Unduh data")
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        hist = td_path / "history.csv"
        xlsx = td_path / "run.xlsx"
        export_result_csv(result, hist, include_history=True)
        export_result_excel(result, xlsx)
        c1, c2 = st.columns(2)
        c1.download_button(
            "⬇ CSV riwayat", hist.read_bytes(), "parade_history.csv", "text/csv",
            key=f"{key}_csv", use_container_width=True,
        )
        c2.download_button(
            "⬇ Excel", xlsx.read_bytes(), "parade_run.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"{key}_xlsx", use_container_width=True,
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
    total_units = st.sidebar.number_input("Total zona", 1, 1000, 40, 5)
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
    return int(total_units), seed, 5


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
        _export_block(result, "single")


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

    if "cmp_multi" not in st.session_state:
        return

    results = st.session_state.cmp_multi
    meta = st.session_state.get("cmp_meta") or {}
    rows = []
    for name, r in results.items():
        m = meta.get(name, {})
        ll = littles_law_metrics(r)
        rows.append({
            "Skenario": name,
            "Variability": m.get("var_label", "—"),
            "Batch": r.config.batch_size,
            "Pace": m.get("pace", r.config.trades[0].label()),
            "Durasi": r.duration,
            "vs Ideal": round(r.duration - r.ideal_duration, 1),
            "Idle": r.total_idle_capacity,
            "Puncak WIP": _peak_wip(r),
            "TH": round(ll.throughput, 3),
            "WIP⌀": round(ll.avg_pipeline_wip, 2),
            "CT": round(ll.cycle_time_pipeline, 2),
            "T5 selesai": r.trade_metrics[-1].periods_to_finish,
        })
    st.divider()
    st.markdown("##### Ringkasan")
    st.dataframe(sorted(rows, key=lambda x: x["Durasi"]), use_container_width=True, hide_index=True)

    tab_lob, tab_buf, tab_util, tab_ll, tab_kg, tab_fr = st.tabs(
        ["Line of Balance", "Buffer / WIP", "Utilisasi", "Little's Law", "Kingman", "Inventory / FR"]
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
    """Takt plan: one-piece flow, zona utama, 3 buffer (kapasitas/waktu/inventory)."""
    st.subheader("Takt plan")
    st.caption(
        "Aliran **one-piece flow** (batch = 1). "
        "Variabel utama: **jumlah zona**. "
        "Buffer: **kapasitas**, **waktu**, **inventory**."
    )

    # --- Primary design: zones + capacity ---
    c1, c2 = st.columns(2)
    n_zones = int(c1.number_input(
        "Jumlah zona (variabel utama)",
        min_value=4, max_value=200, value=int(total_units), step=1,
        key="takt_zones",
        help="Berapa zonasi menentukan panjang train dan durasi rencana.",
    ))
    rate = float(c2.selectbox(
        "Kapasitas dasar (zona/periode)",
        options=[1.0 / 3.0, 0.5, 1.0, 2.0, 3.0],
        index=2,
        format_func=lambda x: (
            "Sangat rendah — 1/3" if abs(x - 1 / 3) < 1e-9
            else "Rendah — 0,5" if abs(x - 0.5) < 1e-9
            else "Normal — 1" if abs(x - 1.0) < 1e-9
            else "Tinggi — 2" if abs(x - 2.0) < 1e-9
            else "Sangat tinggi — 3"
        ),
        key="takt_rate_plan",
    ))

    mode = st.radio(
        "Mode desain waktu",
        ["Hitung durasi dari zona + buffer", "Target periode → cek kelayakan"],
        horizontal=True,
        key="takt_design_mode",
    )

    # --- Three buffers ---
    st.markdown("##### Sistem buffer (3 jenis)")
    b1, b2, b3 = st.columns(3)
    cap_buf_pct = int(b1.slider(
        "Buffer kapasitas (%)",
        min_value=0, max_value=100, value=0, step=5,
        key="takt_cap_buf",
        help="Cadangan kapasitas (standby/overtime). 20 = +20% kapasitas efektif.",
    ))
    cap_buf = cap_buf_pct / 100.0
    time_buf = int(b2.number_input(
        "Buffer waktu (periode/zona)",
        min_value=0, max_value=10, value=0, step=1,
        key="takt_time_buf",
        help="Slack waktu ditambahkan pada takt time tiap zona (jadwal longgar).",
    ))
    inv_buf = int(b3.number_input(
        "Buffer inventory (zona)",
        min_value=0, max_value=10, value=0, step=1,
        key="takt_inv_buf",
        help="Stok penyangga antar-tim. 0–1 = one-piece murni; ≥2 = lepas tiap N zona.",
    ))

    var_mode = st.selectbox(
        "Variability simulasi aktual",
        ["no_variability", "low", "medium", "high", "very_high"],
        format_func=lambda x: VAR_LABELS.get(x, x),
        key="takt_var_actual",
    )

    # Effective rates for plan
    rate_eff = rate * (1.0 + cap_buf)
    t_proc = 1.0 / max(rate_eff, 1e-9)
    t_plan = t_proc + float(time_buf)
    rate_plan = 1.0 / max(t_plan, 1e-9)
    batch = 1 if inv_buf <= 1 else inv_buf

    target_periods = None
    if mode.startswith("Target"):
        target_periods = int(st.number_input(
            "Target total periode",
            min_value=n_trades,
            max_value=5000,
            value=max(n_zones + n_trades, n_zones),
            step=1,
            key="takt_target_periods",
        ))
        req = required_rate_for_duration(
            n_trades, n_zones, batch, target_periods, rate_max=10.0,
        )
        # Compare needed rate to rate_plan (with buffers)
        if req["feasible"]:
            if rate_plan + 1e-9 >= req["rate"]:
                st.success(
                    f"Dengan buffer saat ini, kapasitas efektif rencana ≈ **{rate_plan:.3f}** "
                    f"zona/periode ≥ kebutuhan **{req['rate']:.3f}** untuk target {target_periods} p."
                )
            else:
                st.warning(
                    f"Butuh ≈ **{req['rate']:.3f}** zona/periode untuk target {target_periods} p; "
                    f"rencana saat ini hanya **{rate_plan:.3f}**. "
                    f"Naikkan kapasitas dasar, buffer kapasitas, atau longgarkan target/zona."
                )
        else:
            st.error(req["message"])

    # Buttons first (above charts)
    btn1, btn2, _ = st.columns([1, 1, 2])
    run = btn1.button("Jalankan simulasi", type="primary", use_container_width=True, key="takt_run")
    clear = btn2.button("Hapus hasil", use_container_width=True, key="takt_clear")
    if clear:
        for k in ("takt_result", "takt_rel", "takt_plan_snap"):
            st.session_state.pop(k, None)

    plan = build_takt_plan(
        n_trades=n_trades,
        n_zones=n_zones,
        batch_size=batch,
        rate=rate_plan,
        handoff_lag=1,
    )

    # Metrics
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Zona", f"{n_zones}")
    m2.metric("Aliran", "One-piece" if batch == 1 else f"Inv.buf={inv_buf}")
    m3.metric("Rate efektif", f"{rate_plan:.3g}")
    m4.metric("Takt time", f"{plan.takt_time:.3g} p")
    m5.metric("Durasi rencana", f"{plan.duration} p")

    # Buffer summary chips
    st.caption(
        f"Buffer → kapasitas **+{100 * cap_buf:.0f}%** · "
        f"waktu **+{time_buf} p/zona** · "
        f"inventory **{inv_buf} zona** "
        f"(dasar {rate:g} → efektif {rate_plan:.3g} zona/p)"
    )

    if run:
        pairs = [_pair_from_base_and_var(float(rate_plan), var_mode)] * n_trades
        try:
            res = ParadeOfTrades(
                _build_config_from_pairs(pairs, n_zones, seed, batch_size=batch)
            ).run()
            st.session_state["takt_result"] = res
            st.session_state["takt_rel"] = takt_plan_reliability(res, plan)
            st.session_state["takt_plan_snap"] = plan
        except RuntimeError as exc:
            st.error(str(exc))

    result = st.session_state.get("takt_result")
    rel = st.session_state.get("takt_rel")
    plan_snap = st.session_state.get("takt_plan_snap") or plan

    if result is not None and rel is not None:
        st.divider()
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Reliability", f"{100 * rel['reliability']:.1f}%")
        r2.metric("Durasi aktual", f"{rel['actual_duration']} p")
        r3.metric("vs rencana", f"{rel['actual_duration'] - rel['plan_duration']:+d} p")
        if target_periods is not None:
            r4.metric("vs target", f"{rel['actual_duration'] - int(target_periods):+d} p")
        else:
            r4.metric("One-piece", "ya" if batch == 1 else "inv.buffer")

        fig, ax = plt.subplots(figsize=(10, 5.2))
        plot_takt_plan(plan_snap, ax=ax, result=result,
                       title="Takt plan OPF · rencana vs aktual")
        fig.tight_layout()
        _fig_to_st(fig)

        fig, ax = plt.subplots(figsize=(10, 4.4))
        plot_takt_wagon_chart(plan_snap, ax=ax, max_zones=min(12, n_zones))
        fig.tight_layout()
        _fig_to_st(fig)

        with st.expander("Detail reliability per zona"):
            st.dataframe(rel["detail"][:100], use_container_width=True, hide_index=True)
    else:
        fig, ax = plt.subplots(figsize=(10, 5.0))
        plot_takt_plan(plan, ax=ax, result=None,
                       title="Takt plan ideal (one-piece + buffer)")
        fig.tight_layout()
        _fig_to_st(fig)

        fig, ax = plt.subplots(figsize=(10, 4.4))
        plot_takt_wagon_chart(plan, ax=ax, max_zones=min(12, n_zones))
        fig.tight_layout()
        _fig_to_st(fig)

    with st.expander("What-if: durasi vs jumlah zona (one-piece, tanpa buffer)"):
        rows = []
        for z in sorted(set([8, 12, 16, 20, 24, 30, 40, 50, 60, n_zones])):
            p = build_takt_plan(n_trades, int(z), batch_size=1, rate=rate)
            rows.append({
                "Zona": z,
                "Durasi rencana (OPF)": p.duration,
                "Takt time": round(p.takt_time, 3),
                "Kapasitas dasar": rate,
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)
        st.caption("Tanpa buffer: durasi ≈ f(zona) pada one-piece flow. Buffer mengubah rate efektif & inventory.")

    with st.expander("Teori singkat: 3 buffer"):
        st.markdown(
            """
| Buffer | Arti | Di app |
|--------|------|--------|
| **Kapasitas** | Cadangan produktivitas (standby, lembur, kru ekstra) | +% pada kapasitas dasar |
| **Waktu** | Slack di jadwal / takt time lebih longgar | +periode per zona pada takt time |
| **Inventory** | Stok zona di antara tim (decoupling) | 0–1 = OPF murni; ≥2 = lepas tiap N zona |

Takt plan konstruksi lean biasanya **one-piece flow**; **jumlah zona** menentukan panjang parade.  
Buffer dipakai agar irama tetap andal saat ada variability (lihat juga Tommelein 2020 — capacity buffer).
"""
        )

    st.divider()
    st.markdown("##### Tommelein (2020) — capacity buffer / standby")
    st.caption("S1 classic 4/6 · S2 takt 5 + standby 1 · S3 classic 5/7.")
    if st.button("Jalankan 3 skenario Tommelein 2020", key="takt_tommelein"):
        sc = tommelein2020_scenarios(total_units=min(n_zones, 50), seed=seed)
        rows = []
        results = {}
        for name, cfg in sc.items():
            try:
                results[name] = ParadeOfTrades(cfg).run()
                r = results[name]
                rows.append({
                    "Skenario": name,
                    "Durasi": r.duration,
                    "Idle": r.total_idle_capacity,
                    "TH": round(r.system_throughput, 3),
                    "Standby dipakai": r.total_standby_used,
                })
            except RuntimeError as exc:
                rows.append({
                    "Skenario": name, "Durasi": str(exc),
                    "Idle": "—", "TH": "—", "Standby dipakai": "—",
                })
        st.session_state["takt_tom_rows"] = rows
        st.session_state["takt_tom_res"] = results
    if "takt_tom_rows" in st.session_state:
        st.dataframe(st.session_state["takt_tom_rows"], use_container_width=True, hide_index=True)
        if st.session_state.get("takt_tom_res"):
            fig, ax = plt.subplots(figsize=(10, 4.8))
            plot_comparison_lob(
                st.session_state["takt_tom_res"], ax=ax,
                title="Tommelein 2020 — LOB (tim terakhir)", last_trade_only=True,
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


def main() -> None:
    total_units, seed, n_trades = render_sidebar()
    _render_header()
    tabs = st.tabs(["Simulasi", "Perbandingan", "Takt plan", "Manual"])
    with tabs[0]:
        tab_single_run(total_units, seed, n_trades)
    with tabs[1]:
        tab_compare(total_units, seed, n_trades)
    with tabs[2]:
        tab_takt(total_units, seed, n_trades)
    with tabs[3]:
        tab_manual()


if __name__ == "__main__":
    main()
