"""Parade of Trades – Streamlit app (zone-flow classroom model)."""
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
)
from parade_of_trades_core import (
    CAPACITY_PRESETS,
    DEFAULT_TRADE_NAMES,
    ParadeConfig,
    ParadeOfTrades,
    ParadeResult,
)
from parade_of_trades_plots import (
    plot_buffer_profile,
    plot_comparison_lob,
    plot_line_of_balance,
    plot_line_of_balance_detail,
    plot_utilization,
)

_APP_BUILD = "2026-08-03-sim-silent-v19"
_APP_DIR = Path(__file__).resolve().parent
_ASSETS_DIR = _APP_DIR / "assets"
_HEADER_BANNER = _ASSETS_DIR / "header_banner.jpg"
_LOGO_ICON = _ASSETS_DIR / "logo_icon.jpg"
_MANUAL_PATH = _APP_DIR / "MANUAL.md"

st.set_page_config(
    page_title="Parade of Trades",
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
    "no_variability": "No variability — kecepatan sama tiap zona",
    "low": "Low — rate zona ×0.75 atau ×1.25",
    "medium": "Medium — rate zona ×0.5 atau ×1.5",
    "high": "High — rate zona ×0.25 atau ×1.75",
    "very_high": "Very high — rate zona ×0.1 atau ×1.9",
}
_BATCH_OPTIONS = [4, 5, 3, 2, 1]

_SPEED_CHOICES = [
    ("Sangat lambat — 1 zona / 3 periode", 1.0 / 3.0),
    ("Lambat — 1 zona / 2 periode", 0.5),
    ("Normal — 1 zona / 1 periode", 1.0),
    ("Cepat — 2 zona / 1 periode", 2.0),
    ("Sangat cepat — 3 zona / 1 periode", 3.0),
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


def _base_speed_input(key: str, label: str = "Kecepatan dasar", default: float = 1.0) -> float:
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
    """Accurate one-piece parade: 5 zones × 5 teams, step timeline, then loop."""
    # Full HTML+JS so positions snap to CSS grid cells (not free-floating %).
    html = r"""
<!DOCTYPE html>
<html><head><meta charset="utf-8"/>
<style>
  :root {
    --t1:#3b82f6; --t2:#f59e0b; --t3:#10b981; --t4:#ef4444; --t5:#8b5cf6;
    --done:#94a3b8; --bg0:#0f2744; --bg1:#1a365d;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; font-family: system-ui, -apple-system, Segoe UI, sans-serif;
    background: transparent; color: #e8eef7;
  }
  .wrap {
    background: linear-gradient(135deg, var(--bg0) 0%, var(--bg1) 55%, #234e76 100%);
    border-radius: 14px; padding: 12px 12px 10px;
    box-shadow: 0 8px 28px rgba(15,39,68,.28);
  }
  .head { margin-bottom: 10px; }
  .title { font-weight: 700; font-size: 16px; }
  .sub { font-size: 12.5px; opacity: .9; margin-top: 3px; line-height: 1.4; }
  .grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 8px;
  }
  .zone {
    background: rgba(255,255,255,.07);
    border: 1px dashed rgba(255,255,255,.32);
    border-radius: 10px;
    min-height: 88px;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 6px 4px 8px;
    transition: background .25s, border-color .25s;
  }
  .zone.done {
    background: rgba(148,163,184,.18);
    border-style: solid;
    border-color: rgba(148,163,184,.55);
  }
  .zone-label {
    font-size: 11px; font-weight: 700; letter-spacing: .03em;
    color: rgba(255,255,255,.8); margin-bottom: 6px;
  }
  .slot {
    flex: 1; width: 100%;
    display: flex; align-items: center; justify-content: center;
    min-height: 56px;
  }
  .chip {
    display: none;
    width: 92%;
    max-width: 112px;
    padding: 8px 6px;
    border-radius: 10px;
    text-align: center;
    font-weight: 800;
    font-size: 13px;
    line-height: 1.15;
    box-shadow: 0 4px 12px rgba(0,0,0,.3);
  }
  .chip small { display:block; font-weight:600; font-size:10px; opacity:.92; margin-top:2px; }
  .chip.show { display: block; animation: pop .28s ease; }
  .chip.t1 { background: var(--t1); color:#fff; }
  .chip.t2 { background: var(--t2); color:#1a1200; }
  .chip.t3 { background: var(--t3); color:#fff; }
  .chip.t4 { background: var(--t4); color:#fff; }
  .chip.t5 { background: var(--t5); color:#fff; }
  .chip.done-block {
    background: linear-gradient(180deg, #e2e8f0, #cbd5e1);
    color: #0f172a;
    border: 1px solid rgba(15,23,42,.12);
  }
  @keyframes pop {
    from { transform: scale(.85); opacity: 0; }
    to   { transform: scale(1); opacity: 1; }
  }
  .meta {
    display: flex; flex-wrap: wrap; gap: 8px 14px;
    margin-top: 10px; font-size: 11.5px; opacity: .92;
    align-items: center;
  }
  .period {
    background: rgba(255,255,255,.1);
    border-radius: 999px; padding: 3px 10px; font-weight: 700;
  }
  .hint { opacity: .85; }
  @media (max-width: 560px) {
    .chip small { display: none; }
    .zone { min-height: 78px; }
    .title { font-size: 14px; }
  }
</style>
</head>
<body>
<div class="wrap">
  <div class="grid" id="grid">
    <!-- zones filled by JS -->
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
  const STEP_MS = 900;
  const HOLD_END_MS = 1600;
  const grid = document.getElementById("grid");

  // Build 5 zone columns
  for (let z = 1; z <= N; z++) {
    const zone = document.createElement("div");
    zone.className = "zone";
    zone.id = "zone-" + z;
    zone.innerHTML = '<div class="slot" id="slot-' + z + '"></div>';
    grid.appendChild(zone);
  }

  function clearSlots() {
    for (let z = 1; z <= N; z++) {
      const slot = document.getElementById("slot-" + z);
      slot.innerHTML = "";
      document.getElementById("zone-" + z).classList.remove("done");
    }
  }

  function putTeam(zone, team) {
    const slot = document.getElementById("slot-" + zone);
    const chip = document.createElement("div");
    chip.className = "chip show " + team.cls;
    chip.innerHTML = "<span>" + team.name + "</span>";
    slot.appendChild(chip);
  }

  function putDone(zone) {
    const slot = document.getElementById("slot-" + zone);
    const chip = document.createElement("div");
    chip.className = "chip show done-block";
    chip.innerHTML = "<span>✓</span>";
    slot.appendChild(chip);
    document.getElementById("zone-" + zone).classList.add("done");
  }

  /*
    Discrete one-piece state for period p (1-based):
      Team t is in zone (p - t + 1) if that zone is in 1..5.
      Zone z is fully done when period > z + 4  (T5 finished z at period z+4).
    Period 0: empty
    Period 1: T1@1
    Period 5: T1@5,T2@4,T3@3,T4@2,T5@1
    Period 6: T2@5,...,T5@2; Z1 done (T5 left Z1)
    Period 9: T5@5; Z1..Z4 done
    Period 10: all done
  */
  function renderPeriodFixed(p) {
    clearSlots();
    if (p === 0) return;

    for (let z = 1; z <= N; z++) {
      if (p >= z + 5) {
        putDone(z);
      }
    }

    for (let t = 1; t <= N; t++) {
      const z = p - t + 1;
      if (z >= 1 && z <= N) {
        const slot = document.getElementById("slot-" + z);
        slot.innerHTML = "";
        document.getElementById("zone-" + z).classList.remove("done");
        putTeam(z, TEAMS[t - 1]);
      }
    }
  }

  let p = 0;
  const MAX_P = 10; // 0 empty … 10 all done

  function tick() {
    renderPeriodFixed(p);
    if (p >= MAX_P) {
      // hold full complete, then reset to empty and restart
      setTimeout(function () {
        p = 0;
        renderPeriodFixed(0);
        setTimeout(function () {
          p = 1;
          schedule();
        }, 700);
      }, HOLD_END_MS);
      return;
    }
    p += 1;
    schedule();
  }

  function schedule() {
    setTimeout(tick, STEP_MS);
  }

  // start: brief empty, then period 1
  renderPeriodFixed(0);
  setTimeout(function () {
    p = 1;
    tick();
  }, 600);
})();
</script>
</body></html>
"""
    components.html(html, height=140, scrolling=False)


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
        c1, c2 = st.columns([1, 8], vertical_alignment="center")
        with c1:
            st.image(str(_LOGO_ICON), width=64)
        with c2:
            st.markdown("## Parade of Trades")
            st.caption("Zone-flow · batch/one-piece · kecepatan & variability **per zona**")
    else:
        st.title("Parade of Trades")


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
    show_help: bool = True,
) -> List[Tuple]:
    st.markdown("**Kecepatan dasar** + **variability (per zona)**")
    if show_help:
        st.markdown(
            '<div class="pot-field">'
            "<strong>Kecepatan</strong> = progress pada <em>satu zona</em>. "
            "Tanpa var: rate sama tiap zona. Dengan var: undi rate <em>per zona</em> "
            "(mis. medium ×0.5 / ×1.5).<br/>"
            f"<strong>Batch handoff</strong> (sidebar) = <strong>{_batch_size()}</strong> — "
            "zona dilepas ke trade hilir setelah batch penuh (periode berikutnya)."
            "</div>",
            unsafe_allow_html=True,
        )
    mode = st.radio(
        "Pengaturan trade",
        ["Seragam (semua trade sama)", "Per trade (dasar & variability bisa beda)"],
        horizontal=True,
        key=f"{key_prefix}_speed_mode",
    )

    def _vi(name: str) -> int:
        return PRESET_OPTIONS.index(name) if name in PRESET_OPTIONS else 0

    if mode.startswith("Seragam"):
        base = _base_speed_input(f"{key_prefix}_base", "Kecepatan dasar semua trade", default_base)
        var = st.selectbox(
            "Variability (semua trade)",
            PRESET_OPTIONS,
            index=_vi(default_var),
            format_func=lambda x: VAR_LABELS.get(x, x),
            key=f"{key_prefix}_var",
        )
        spec = _pair_from_base_and_var(base, var)
        st.info(f"Semua trade: **{_format_pair(spec)}** · {VAR_LABELS[var]}")
        return [spec] * n_trades

    pairs: List[Tuple] = []
    for i in range(n_trades):
        with st.expander(f"Trade {i + 1}: {_trade_name(i)}", expanded=(i < 2)):
            base_i = _base_speed_input(f"{key_prefix}_base_t{i}", f"Kecepatan T{i + 1}", default_base)
            var_i = st.selectbox(
                "Variability trade ini",
                PRESET_OPTIONS,
                index=_vi(default_var),
                format_func=lambda x: VAR_LABELS.get(x, x),
                key=f"{key_prefix}_var_t{i}",
            )
            spec = _pair_from_base_and_var(base_i, var_i)
            pairs.append(spec)
            st.caption(f"→ {_format_pair(spec)}")
    return pairs


def _peak_wip(result: ParadeResult) -> int:
    return max((sum(h.buffers) for h in result.history), default=0)


def _metrics_row(result: ParadeResult) -> None:
    cols = st.columns(6)
    cols[0].metric("Duration", f"{result.duration}")
    cols[1].metric("vs Ideal", f"{result.duration - result.ideal_duration:+.1f}")
    cols[2].metric("Throughput", f"{result.system_throughput:.3f}")
    cols[3].metric("Total Idle", f"{result.total_idle_capacity}")
    cols[4].metric("Peak WIP", f"{_peak_wip(result)}")
    cols[5].metric("Batch", f"{result.config.batch_size}")


def _starts_caption(result: ParadeResult) -> str:
    starts = [t.start_period for t in result.trade_metrics]
    return "Start periode: " + " · ".join(f"T{i + 1}=p{s}" for i, s in enumerate(starts))


def _trade_table(result: ParadeResult) -> None:
    rows = []
    for i, m in enumerate(result.trade_metrics):
        rows.append({
            "#": i + 1,
            "Trade": m.name,
            "Pace": result.config.trades[i].label(),
            "Production": m.total_production,
            "Idle": m.total_idle,
            "Start": m.start_period if m.start_period is not None else "—",
            "Finish": m.periods_to_finish,
            "Time on site": m.time_on_site,
        })
    st.dataframe(rows, use_container_width=True, hide_index=True)


def _fig_to_st(fig) -> None:
    st.pyplot(fig, clear_figure=True)
    plt.close(fig)


def _export_block(result: ParadeResult, key: str) -> None:
    st.markdown("##### Export")
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        hist = td_path / "history.csv"
        xlsx = td_path / "run.xlsx"
        export_result_csv(result, hist, include_history=True)
        export_result_excel(result, xlsx)
        c1, c2 = st.columns(2)
        c1.download_button(
            "⬇ History CSV", hist.read_bytes(), "parade_history.csv", "text/csv",
            key=f"{key}_csv", use_container_width=True,
        )
        c2.download_button(
            "⬇ Excel", xlsx.read_bytes(), "parade_run.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"{key}_xlsx", use_container_width=True,
        )


def _plot_single_result(result: ParadeResult) -> None:
    tab_lob, tab_buf, tab_util = st.tabs(["Line of Balance", "Buffer / WIP", "Utilization"])
    with tab_lob:
        st.caption(
            "Sumbu X = periode (dari 0). Sumbu Y = zona kumulatif (dari 0). "
            f"Batch={result.config.batch_size}: trade hilir mulai setelah handoff batch. "
            "Garis **bergeser**, tidak menumpuk."
        )
        fig, ax = plt.subplots(figsize=(10, 4.5))
        plot_line_of_balance_detail(result, ax=ax, max_period=min(16, result.duration + 1))
        fig.tight_layout()
        _fig_to_st(fig)
        st.caption("↑ Detail awal · ↓ Seluruh proyek")
        fig, ax = plt.subplots(figsize=(10, 5.8))
        plot_line_of_balance(result, ax=ax)
        fig.tight_layout()
        _fig_to_st(fig)
        st.caption(_starts_caption(result))
        if result.history:
            rows = [{
                "Periode": rec.period,
                "T1 prod": rec.production[0],
                "T1 zona": rec.cumulative[0],
                "T2 zona": rec.cumulative[1],
                "T5 zona": rec.cumulative[-1],
            } for rec in result.history[:16]]
            st.dataframe(rows, use_container_width=True, hide_index=True)
    with tab_buf:
        c1, c2 = st.columns(2)
        with c1:
            fig, ax = plt.subplots(figsize=(6, 4))
            plot_buffer_profile(result, ax=ax, stacked=False)
            fig.tight_layout()
            _fig_to_st(fig)
        with c2:
            fig, ax = plt.subplots(figsize=(6, 4))
            plot_buffer_profile(result, ax=ax, stacked=True, show_max=False)
            fig.tight_layout()
            _fig_to_st(fig)
    with tab_util:
        fig, ax = plt.subplots(figsize=(8, 3.8))
        plot_utilization(result, ax=ax)
        fig.tight_layout()
        _fig_to_st(fig)


def render_sidebar():
    if _LOGO_ICON.exists():
        a, b = st.sidebar.columns([1, 2.2])
        with a:
            st.image(str(_LOGO_ICON), width=64)
        with b:
            st.markdown("### Parade of Trades")
            st.caption("Zone-flow Indonesia")
    else:
        st.sidebar.title("Parade of Trades")
    st.sidebar.success(
        f"**Build {_APP_BUILD}** — zone-flow · batch default 4 · var per zona. "
        "Refresh (Ctrl/Cmd+Shift+R) jika banner tidak muncul."
    )
    st.sidebar.divider()
    total_units = st.sidebar.number_input("Total zona", 1, 1000, 20, 5)
    use_seed = st.sidebar.checkbox("Fix random seed", True)
    seed = int(st.sidebar.number_input("Seed", 0, 10_000_000, 42, 1)) if use_seed else None
    st.sidebar.markdown("**Jumlah trade:** 5 (tetap)")
    st.sidebar.caption("1 Bekisting · 2 Tulangan · 3 Cor · 4 Bongkar · 5 Finishing")
    st.sidebar.divider()
    st.sidebar.markdown("**Batch / one-piece flow**")
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
        help="Default 4: kumpulkan 4 zona dulu baru dilepas ke trade hilir. "
             "1 = one-piece flow.",
    )
    st.sidebar.caption(
        "Batch dipakai di **Single run** dan **Comparison**."
    )
    return int(total_units), seed, 5


# ----- Tabs -----------------------------------------------------------------

def tab_single_run(total_units: int, seed: Optional[int], n_trades: int) -> None:
    st.subheader("Single scenario (zone-flow)")
    st.markdown(
        '<div class="pot-callout">'
        f"<strong>Default batch = {_batch_size()}</strong> (sidebar). "
        "Semua Normal + No var → T2 mulai setelah T1 melepas batch; LOB dari 0 dan bergeser.<br/>"
        "Ubah batch ke <strong>1</strong> untuk one-piece. "
        "T1 Medium → rate diundi per zona (bukan lompat massal +3 zona)."
        "</div>",
        unsafe_allow_html=True,
    )
    col_cfg, col_ctrl = st.columns([1.1, 1.4])
    with col_cfg:
        pairs = _capacity_setup("single", n_trades, "no_variability", 1.0)
        st.caption(
            "Parade: "
            + " → ".join(f"{_trade_name(i)[:10]} [{_format_pair(pairs[i])}]" for i in range(n_trades))
        )
    with col_ctrl:
        b1, b2 = st.columns(2)
        run_c = b1.button("Run", type="primary", use_container_width=True, key="single_run")
        reset_c = b2.button("Reset", use_container_width=True, key="single_reset")
        if "single_result" not in st.session_state:
            st.session_state.single_result = None
        if reset_c:
            st.session_state.single_result = None
            st.success("Reset.")
        if run_c:
            cfg = _build_config_from_pairs(pairs, total_units, seed)
            try:
                res = ParadeOfTrades(cfg).run()
                st.session_state.single_result = res
                st.success(
                    f"Selesai · Duration **{res.duration}** · batch={cfg.batch_size} · "
                    f"{_starts_caption(res)}"
                )
            except RuntimeError as exc:
                st.error(f"Simulasi gagal: {exc}")

    st.divider()
    result = st.session_state.get("single_result")
    if not result or not result.history:
        st.info("Atur kapasitas → **Run**.")
        return
    _metrics_row(result)
    left, right = st.columns([1.25, 1])
    with left:
        _plot_single_result(result)
    with right:
        st.markdown("##### Trade metrics")
        _trade_table(result)
        _export_block(result, "single")


def _batch_label(b: int) -> str:
    if b == 1:
        return "1 — One-piece"
    if b == 4:
        return "4 — Standar"
    return f"{b} — Handoff tiap {b}"


def tab_compare(total_units: int, seed: Optional[int], n_trades: int) -> None:
    st.subheader("Comparison (2–5 skenario, zone-flow)")
    st.markdown(
        '<div class="pot-callout">'
        "Bandingkan <strong>2 sampai 5</strong> skenario. "
        "Tiap skenario punya <strong>kecepatan</strong>, <strong>variability</strong>, "
        "dan <strong>batch handoff</strong> sendiri — cocok membandingkan "
        "level variability <em>atau</em> one-piece vs batch besar."
        "</div>",
        unsafe_allow_html=True,
    )

    default_vars = list(PRESET_OPTIONS)
    sidebar_batch = _batch_size()

    # --- Quick-fill BEFORE widgets ---
    c1, c2, c3, c4 = st.columns(4)
    fill_five = c1.button(
        "5× variability", key="cmp_fill_five", use_container_width=True,
        help="5 skenario: Skenario 1–5 = No→Very high, batch = sidebar",
    )
    fill_two = c2.button("No vs Medium", key="cmp_fill_two", use_container_width=True)
    fill_batch = c3.button(
        "Batch 1 vs 4", key="cmp_fill_batch", use_container_width=True,
        help="Skenario 1 = one-piece, Skenario 2 = batch 4 (No var)",
    )
    clear_res = c4.button("Hapus hasil", key="cmp_clear", use_container_width=True)

    if clear_res:
        st.session_state.pop("cmp_multi", None)

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

    n_scen = int(
        st.slider(
            "Jumlah skenario",
            min_value=2,
            max_value=5,
            key="cmp_n_scen",
            help="2–5 skenario.",
        )
    )

    st.caption(
        f"Zona = **{total_units}** · Seed = **{seed}** (sama). "
        f"Batch di sidebar (**{sidebar_batch}**) hanya default; "
        "setiap skenario bisa beda batch di kolom di bawah."
    )

    scenarios_cfg = []
    cols = st.columns(n_scen)
    for i in range(n_scen):
        with cols[i]:
            st.markdown(f"##### Skenario {i + 1}")
            label = f"Skenario {i + 1}"
            # keep label key in state for fills; no free-text name field
            st.session_state[f"cmp_s{i}_label"] = label
            base = _base_speed_input(f"cmp_s{i}", "Kecepatan", 1.0)
            var = st.selectbox(
                "Variability",
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
                    help="1 = one-piece flow; 4 = standar kelas.",
                )
            )
            spec = _pair_from_base_and_var(base, var)
            st.caption(f"{_format_pair(spec)} · batch **{batch_i}**")
            scenarios_cfg.append((label.strip() or f"S{i + 1}", spec, var, batch_i))

    if st.button("Run comparison", type="primary", key="run_cmp", use_container_width=True):
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
            batches = [meta[n]["batch"] for n in results]
            st.success(f"Selesai · **{len(results)}** skenario · batch = {batches}")

    if "cmp_multi" not in st.session_state:
        st.info("Atur skenario → **Run comparison**. Coba tombol **Batch 1 vs 4** atau **5× variability**.")
        return

    results = st.session_state.cmp_multi
    meta = st.session_state.get("cmp_meta") or {}
    rows = []
    for name, r in results.items():
        m = meta.get(name, {})
        rows.append({
            "Skenario": name,
            "Variability": m.get("var_label", "—"),
            "Batch": r.config.batch_size,
            "Pace": m.get("pace", r.config.trades[0].label()),
            "Duration": r.duration,
            "vs Ideal": round(r.duration - r.ideal_duration, 1),
            "Idle": r.total_idle_capacity,
            "Peak WIP": _peak_wip(r),
            "Throughput": round(r.system_throughput, 3),
            "T5 finish": r.trade_metrics[-1].periods_to_finish,
        })
    st.markdown("##### Ringkasan (duration naik)")
    st.dataframe(sorted(rows, key=lambda x: x["Duration"]), use_container_width=True, hide_index=True)

    fig, ax = plt.subplots(figsize=(10, 5.5))
    plot_comparison_lob(
        results,
        ax=ax,
        title="LOB skenario — mulai (0,0) · trade terakhir · batch bisa beda",
        last_trade_only=True,
    )
    fig.tight_layout()
    _fig_to_st(fig)
    st.caption(
        "Semua kurva **mulai dari (periode 0, zona 0)**. "
        "Garis = kumulatif **trade terakhir** (proyek selesai). "
        "Batch=1 (one-piece): trade terakhir mulai paling awal. "
        "Batch besar: trade terakhir mulai lebih lambat (tunggu handoff)."
    )

    with st.expander("Detail trade satu skenario"):
        pick = st.selectbox("Skenario", list(results.keys()), key="cmp_detail_pick")
        st.caption(f"Batch skenario ini = **{results[pick].config.batch_size}**")
        _trade_table(results[pick])
        st.caption(_starts_caption(results[pick]))



def tab_manual() -> None:
    st.subheader("📖 Manual & tentang model")
    st.markdown(
        '<div class="pot-field">'
        "Panduan zone-flow untuk kelas. Ringkas: tiga tab saja — "
        "<strong>Single run</strong> (eksperimen), <strong>Comparison</strong> (2–5 skenario), "
        "<strong>Manual</strong> (panduan)."
        "</div>",
        unsafe_allow_html=True,
    )
    if _MANUAL_PATH.exists():
        st.download_button(
            "⬇ Unduh MANUAL.md",
            data=_MANUAL_PATH.read_text(encoding="utf-8").encode("utf-8"),
            file_name="Parade_of_Trades_Manual_ZoneFlow.md",
            mime="text/markdown",
            key="manual_dl",
        )
        st.markdown(_MANUAL_PATH.read_text(encoding="utf-8"))
    else:
        st.warning("MANUAL.md tidak ditemukan di repo.")

    st.divider()
    st.markdown(f"""
### Tentang build
| | |
|---|---|
| Build | `{_APP_BUILD}` |
| Model | **Zone-flow** (kecepatan & var **per zona**) |
| Batch default | **4** (sidebar) |
| Trade | 5 (floor cycle Indonesia) |

**Tab yang dipakai**
1. **Single run** — satu skenario, LOB / buffer / utilization  
2. **Comparison** — 2–5 skenario (var & **batch** bisa beda)  
3. **Manual** — panduan belajar + tentang  

Referensi: Tommelein, Riley & Howell (1999); Choo & Tommelein (1999); Tommelein (2020).
""")


def main() -> None:
    total_units, seed, n_trades = render_sidebar()
    _render_header()
    tabs = st.tabs(["Single run", "Comparison", "Manual"])
    with tabs[0]:
        tab_single_run(total_units, seed, n_trades)
    with tabs[1]:
        tab_compare(total_units, seed, n_trades)
    with tabs[2]:
        tab_manual()


if __name__ == "__main__":
    main()
