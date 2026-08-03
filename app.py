"""Parade of Trades – Streamlit app (zone-flow classroom model)."""
from __future__ import annotations

import importlib
import math
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import matplotlib.pyplot as plt
import streamlit as st

import parade_of_trades_analysis as _a
import parade_of_trades_core as _c
import parade_of_trades_plots as _p
_c = importlib.reload(_c)
_p = importlib.reload(_p)
_a = importlib.reload(_a)

from parade_of_trades_analysis import (
    compare_tommelein2020, export_result_csv, export_result_excel, run_replications,
)
from parade_of_trades_core import (
    CAPACITY_PRESETS, DEFAULT_TRADE_NAMES, ParadeConfig, ParadeOfTrades, ParadeResult,
    tommelein2020_scenarios,
)
from parade_of_trades_plots import (
    plot_buffer_profile, plot_comparison_buffers, plot_comparison_lob,
    plot_duration_histogram, plot_line_of_balance, plot_line_of_balance_detail,
    plot_replication_summary, plot_time_on_site_boxplot, plot_utilization,
)

_APP_BUILD = "2026-08-03-batch4-default-v8"
_APP_DIR = Path(__file__).resolve().parent
_ASSETS_DIR = _APP_DIR / "assets"
_HEADER_BANNER = _ASSETS_DIR / "header_banner.jpg"
_LOGO_ICON = _ASSETS_DIR / "logo_icon.jpg"
_MANUAL_PATH = _APP_DIR / "MANUAL.md"

st.set_page_config(
    page_title="Parade of Trades",
    page_icon=str(_LOGO_ICON) if _LOGO_ICON.exists() else "🏗️",
    layout="wide", initial_sidebar_state="expanded",
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
    "low": "Low — rate zona x0.75 atau x1.25",
    "medium": "Medium — rate zona x0.5 atau x1.5",
    "high": "High — rate zona x0.25 atau x1.75",
    "very_high": "Very high — rate zona x0.1 atau x1.9",
}
_SPEED_CHOICES = [
    ("Sangat lambat — 1 zona / 3 periode", 1.0 / 3.0),
    ("Lambat — 1 zona / 2 periode", 0.5),
    ("Normal — 1 zona / 1 periode", 1.0),
    ("Cepat — 2 zona / 1 periode", 2.0),
    ("Sangat cepat — 3 zona / 1 periode", 3.0),
]


def _trade_name(i: int) -> str:
    return DEFAULT_TRADE_NAMES[i] if i < len(DEFAULT_TRADE_NAMES) else f"Trade {i+1}"


def _pair_from_base_and_var(base_speed: float, variability: str) -> Tuple:
    """Per-zone rates: (lo, hi, p_high, base, deterministic)."""
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
            1/3: "1 zona/3 periode (tetap tiap zona)",
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


def _render_header() -> None:
    st.markdown(
        """<style>
        .pot-callout{background:linear-gradient(135deg,#f0f7ff,#eef9f3);border:1px solid #c5d9ec;
        border-radius:10px;padding:.75rem 1rem;margin:.4rem 0 .9rem;font-size:.92rem;color:#2d3748}
        .pot-field{background:#f7fafc;border-left:4px solid #2b6cb0;border-radius:0 8px 8px 0;
        padding:.65rem .9rem;margin:.35rem 0 .75rem;font-size:.9rem;color:#2d3748}
        </style>""",
        unsafe_allow_html=True,
    )
    if _HEADER_BANNER.exists():
        st.image(str(_HEADER_BANNER), use_container_width=True)
    if _LOGO_ICON.exists():
        c1, c2 = st.columns([1, 8], vertical_alignment="center")
        with c1:
            st.image(str(_LOGO_ICON), width=72)
        with c2:
            st.markdown("## Parade of Trades")
            st.caption("Zone-flow · one-piece/batch · kecepatan & variability per zona")
    else:
        st.title("Parade of Trades")


def _build_config_from_pairs(pairs, total_units, seed, takt_rate=None, standby_capacity=0) -> ParadeConfig:
    names = [_trade_name(i) for i in range(len(pairs))]
    batch_size = int(st.session_state.get("batch_size", 4))
    return ParadeConfig.from_pairs(
        pairs=list(pairs), trade_names=names, total_units=total_units, seed=seed,
        takt_rate=takt_rate, standby_capacity=standby_capacity,
        same_period_handoff=False, staggered_mobilization=False,
        zone_flow=True, batch_size=batch_size,
    )


def _capacity_setup(key_prefix: str, n_trades: int = 5,
                    default_var: str = "no_variability", default_base: float = 1.0) -> List[Tuple]:
    st.markdown("**Kecepatan dasar** + **variability (per zona)**")
    st.markdown(
        '<div class="pot-field">'
        "<strong>Kecepatan</strong> = progress pada <em>satu zona</em>. "
        "Tanpa variability: sama untuk setiap zona. "
        "Dengan variability: <em>setiap zona</em> mengundi kecepatannya sendiri "
        "(mis. medium: x0.5 atau x1.5), dikunci sampai zona selesai.<br/>"
        "<strong>Handoff</strong> = setelah batch penuh, zona dilepas ke trade hilir "
        "di periode berikutnya (LOB bergeser, tidak menumpuk). "
        "Batch=1 → one-piece flow."
        "</div>",
        unsafe_allow_html=True,
    )
    mode = st.radio(
        "Pengaturan trade",
        ["Seragam (semua trade sama)", "Per trade (dasar & variability bisa beda)"],
        horizontal=True, key=f"{key_prefix}_speed_mode",
    )
    def _vi(name):
        return PRESET_OPTIONS.index(name) if name in PRESET_OPTIONS else 0

    if mode.startswith("Seragam"):
        base = _base_speed_input(f"{key_prefix}_base", "Kecepatan dasar semua trade", default_base)
        var = st.selectbox(
            "Variability (semua trade)", PRESET_OPTIONS, index=_vi(default_var),
            format_func=lambda x: VAR_LABELS.get(x, x), key=f"{key_prefix}_var",
        )
        spec = _pair_from_base_and_var(base, var)
        st.info(f"Semua trade: **{_format_pair(spec)}** · {VAR_LABELS[var]}")
        return [spec] * n_trades

    pairs = []
    for i in range(n_trades):
        with st.expander(f"Trade {i+1}: {_trade_name(i)}", expanded=(i < 2)):
            base_i = _base_speed_input(f"{key_prefix}_base_t{i}", f"Kecepatan T{i+1}", default_base)
            var_i = st.selectbox(
                "Variability trade ini", PRESET_OPTIONS, index=_vi(default_var),
                format_func=lambda x: VAR_LABELS.get(x, x), key=f"{key_prefix}_var_t{i}",
            )
            spec = _pair_from_base_and_var(base_i, var_i)
            pairs.append(spec)
            st.caption(f"→ {_format_pair(spec)}")
    return pairs


def _metrics_row(result: ParadeResult) -> None:
    peak = max((sum(h.buffers) for h in result.history), default=0)
    cols = st.columns(5)
    cols[0].metric("Duration", f"{result.duration}")
    cols[1].metric("vs Ideal", f"{result.duration - result.ideal_duration:+.1f}")
    cols[2].metric("Throughput", f"{result.system_throughput:.3f}")
    cols[3].metric("Total Idle", f"{result.total_idle_capacity}")
    cols[4].metric("Peak WIP", f"{peak}")


def _trade_table(result: ParadeResult) -> None:
    rows = []
    for i, m in enumerate(result.trade_metrics):
        rows.append({
            "#": i + 1, "Trade": m.name, "Pace": result.config.trades[i].label(),
            "Production": m.total_production, "Idle": m.total_idle,
            "Start": m.start_period if m.start_period is not None else "—",
            "Finish": m.periods_to_finish, "Time on site": m.time_on_site,
        })
    st.dataframe(rows, use_container_width=True, hide_index=True)


def _fig_to_st(fig) -> None:
    st.pyplot(fig, clear_figure=True)
    plt.close(fig)


def _plot_single_result(result: ParadeResult) -> None:
    tab_lob, tab_buf, tab_util = st.tabs(["Line of Balance", "Buffer / WIP", "Utilization"])
    with tab_lob:
        st.caption(
            "Sumbu X = periode (mulai 0). Sumbu Y = zona kumulatif (mulai 0). "
            "One-piece: garis trade **bergeser**, tidak menumpuk. "
            "Variability: lonjakan/landai per zona, bukan bulk 0/3 zona sekaligus."
        )
        fig, ax = plt.subplots(figsize=(10, 4.5))
        plot_line_of_balance_detail(result, ax=ax, max_period=12)
        fig.tight_layout(); _fig_to_st(fig)
        st.caption("Detail 12 periode pertama (semua mulai dari 0). Seluruh proyek:")
        fig, ax = plt.subplots(figsize=(10, 5.8))
        plot_line_of_balance(result, ax=ax)
        fig.tight_layout(); _fig_to_st(fig)
        if result.history:
            rows = [{
                "Periode": rec.period,
                "T1 prod": rec.production[0], "T1 zona": rec.cumulative[0],
                "T2 zona": rec.cumulative[1], "T5 zona": rec.cumulative[-1],
            } for rec in result.history[:12]]
            st.dataframe(rows, use_container_width=True, hide_index=True)
    with tab_buf:
        c1, c2 = st.columns(2)
        with c1:
            fig, ax = plt.subplots(figsize=(6, 4))
            plot_buffer_profile(result, ax=ax, stacked=False)
            fig.tight_layout(); _fig_to_st(fig)
        with c2:
            fig, ax = plt.subplots(figsize=(6, 4))
            plot_buffer_profile(result, ax=ax, stacked=True, show_max=False)
            fig.tight_layout(); _fig_to_st(fig)
    with tab_util:
        fig, ax = plt.subplots(figsize=(8, 3.8))
        plot_utilization(result, ax=ax)
        fig.tight_layout(); _fig_to_st(fig)


def render_sidebar():
    if _LOGO_ICON.exists():
        a, b = st.sidebar.columns([1, 2.2])
        with a: st.image(str(_LOGO_ICON), width=64)
        with b:
            st.markdown("### Parade of Trades")
            st.caption("Zone-flow Indonesia")
    else:
        st.sidebar.title("Parade of Trades")
    st.sidebar.success(
        f"**Build {_APP_BUILD}** — one-piece/batch · var per zona · LOB bergeser. "
        "Refresh (Ctrl/Cmd+Shift+R) jika banner ini tidak ada."
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
        index=0,  # default: batch 5 (bukan one-piece)
        format_func=lambda b: (
            f"{b} — Handoff tiap {b} zona (standar)" if b == 4
            else f"{b} — Handoff tiap {b} zona" if b > 1
            else "1 — One-piece flow (zona per zona)"
        ),
        key="batch_size",
        help="Default batch 4: kumpulkan 5 zona dulu baru dilepas ke trade hilir. "
             "One-piece (1) ada di opsi paling bawah.",
    )
    st.sidebar.caption(
        "Kecepatan = progress per zona. Variability = undi rate **per zona**. "
        "Trade hilir mulai setelah batch dilepas."
    )
    return int(total_units), seed, 5


def tab_single_run(total_units, seed, n_trades):
    st.subheader("Single scenario")
    st.markdown(
        '<div class="pot-callout">'
        "<strong>Cek one-piece:</strong> semua Normal + No var, batch=1 → "
        "LOB 5 garis sejajar bergeser (T1 start p1, T2 p2, … T5 p5), semua mulai dari 0.<br/>"
        "<strong>Cek variability:</strong> T1 Normal + Medium, lain No var → "
        "T1 lonjak/landai per zona (bukan lompat +3 zona massal), T2–T5 tetap bergeser."
        "</div>",
        unsafe_allow_html=True,
    )
    col_cfg, col_ctrl = st.columns([1.1, 1.4])
    with col_cfg:
        pairs = _capacity_setup("single", n_trades, "no_variability", 1.0)
        st.markdown(
            '<div class="pot-field">'
            f"Batch handoff = <strong>{st.session_state.get('batch_size', 4)}</strong> "
            "(atur di sidebar)."
            "</div>",
            unsafe_allow_html=True,
        )
        st.caption("Parade: " + " → ".join(
            f"{_trade_name(i)[:10]} [{_format_pair(pairs[i])}]" for i in range(n_trades)
        ))
    with col_ctrl:
        b1, b2, b3 = st.columns(3)
        run_c = b1.button("Run", type="primary", use_container_width=True)
        reset_c = b2.button("Reset", use_container_width=True)
        if "single_result" not in st.session_state:
            st.session_state.single_result = None
        if reset_c:
            st.session_state.single_result = None
            st.success("Reset.")
        if run_c:
            cfg = _build_config_from_pairs(pairs, total_units, seed)
            res = ParadeOfTrades(cfg).run()
            st.session_state.single_result = res
            st.success(
                f"Selesai · Duration **{res.duration}** · batch={cfg.batch_size} · "
                f"starts={[t.start_period for t in res.trade_metrics]}"
            )

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
        # export
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "h.csv"
            export_result_csv(result, p, include_history=True)
            st.download_button("History CSV", p.read_bytes(), "parade_history.csv", "text/csv")


def tab_compare(total_units, seed, n_trades):
    st.subheader("Compare two scenarios")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### A")
        pa = _capacity_setup("cmp_a", n_trades, "no_variability", 1.0)
    with c2:
        st.markdown("### B")
        pb = _capacity_setup("cmp_b", n_trades, "medium", 1.0)
    if st.button("Run comparison", type="primary", key="run_cmp"):
        st.session_state.cmp = {
            "A": ParadeOfTrades(_build_config_from_pairs(pa, total_units, seed)).run(),
            "B": ParadeOfTrades(_build_config_from_pairs(pb, total_units, seed)).run(),
        }
    if "cmp" in st.session_state:
        m1, m2 = st.columns(2)
        with m1: st.markdown("**A**"); _metrics_row(st.session_state.cmp["A"])
        with m2: st.markdown("**B**"); _metrics_row(st.session_state.cmp["B"])
        fig, ax = plt.subplots(figsize=(8, 4.5))
        plot_comparison_lob(st.session_state.cmp, ax=ax)
        fig.tight_layout(); _fig_to_st(fig)


def tab_sweep(total_units, seed, n_trades):
    st.subheader("Variability sweep")
    base = _base_speed_input("sweep_base", "Kecepatan dasar", 1.0)
    selected = st.multiselect("Variability", PRESET_OPTIONS, default=PRESET_OPTIONS,
                              format_func=lambda x: VAR_LABELS.get(x, x))
    if st.button("Run sweep", type="primary", key="run_sweep") and selected:
        results = {}
        for p in selected:
            pairs = [_pair_from_base_and_var(base, p)] * n_trades
            results[p] = ParadeOfTrades(_build_config_from_pairs(pairs, total_units, seed)).run()
        st.session_state.sweep = results
    if "sweep" in st.session_state:
        rows = [{"Var": VAR_LABELS.get(k, k), "Duration": r.duration,
                 "Idle": r.total_idle_capacity} for k, r in st.session_state.sweep.items()]
        st.dataframe(rows, use_container_width=True, hide_index=True)
        fig, ax = plt.subplots(figsize=(8, 4.5))
        plot_comparison_lob(st.session_state.sweep, ax=ax)
        fig.tight_layout(); _fig_to_st(fig)


def tab_takt(total_units, seed):
    st.subheader("Takt 2020 (classic capacity model)")
    n_reps = int(st.number_input("Replications", 10, 500, 50, 10, key="takt_n"))
    sb = int(st.number_input("Seed base", 0, value=seed or 0, key="takt_s"))
    if st.button("Run Tommelein 2020", type="primary", key="run_takt"):
        st.session_state.takt = compare_tommelein2020(
            n_reps=n_reps, seed_base=sb, total_units=total_units,
            staggered=False, same_period_handoff=False, verbose=False,
        )
    if "takt" in st.session_state:
        st.dataframe(st.session_state.takt.summary_rows(), use_container_width=True, hide_index=True)


def tab_reps(total_units, seed, n_trades):
    st.subheader("Replications")
    pairs = _capacity_setup("rep", n_trades, "medium", 1.0)
    n = int(st.number_input("N", 5, 1000, 100, 10, key="rep_n"))
    sb = int(st.number_input("Seed base", 0, value=seed or 0, key="rep_s"))
    if st.button("Run replications", type="primary", key="run_reps"):
        cfg = _build_config_from_pairs(pairs, total_units, None)
        st.session_state.reps = {"main": run_replications(cfg, n_reps=n, seed_base=sb, verbose=False)}
    if "reps" in st.session_state:
        st.dataframe(st.session_state.reps["main"].summary_table(), use_container_width=True, hide_index=True)


def tab_manual():
    st.subheader("Manual")
    if _MANUAL_PATH.exists():
        st.markdown(_MANUAL_PATH.read_text(encoding="utf-8"))
    else:
        st.info("MANUAL.md tidak ada.")


def tab_about():
    st.subheader("Tentang model zone-flow")
    st.markdown(f"""
Build `{_APP_BUILD}`.

### Prinsip
1. **Kecepatan** = progress pada **satu zona** (bukan produksi massal banyak zona per undian).
2. **Tanpa variability** → kecepatan sama untuk setiap zona trade itu.
3. **Dengan variability** → **setiap zona** mengundi rate sendiri (dikunci sampai selesai).
4. **One-piece flow (batch=1)** → zona selesai dilepas ke trade hilir (periode berikutnya).
5. **Batch > 1** → kumpulkan N zona dulu baru lepas.
6. LOB **mulai dari 0**; trade **bergeser** (T1, T2, T3…), tidak menumpuk.

### Variability (faktor × dasar)
| Level | Faktor |
|-------|--------|
| No | ×1.0 tetap |
| Low | ×0.75 atau ×1.25 |
| Medium | ×0.5 atau ×1.5 |
| High | ×0.25 atau ×1.75 |
| Very high | ×0.1 atau ×1.9 |
""")


def main():
    total_units, seed, n_trades = render_sidebar()
    _render_header()
    tabs = st.tabs(["Single run", "Compare 2", "Sweep", "Takt 2020", "Replications", "Manual", "About"])
    with tabs[0]: tab_single_run(total_units, seed, n_trades)
    with tabs[1]: tab_compare(total_units, seed, n_trades)
    with tabs[2]: tab_sweep(total_units, seed, n_trades)
    with tabs[3]: tab_takt(total_units, seed)
    with tabs[4]: tab_reps(total_units, seed, n_trades)
    with tabs[5]: tab_manual()
    with tabs[6]: tab_about()


if __name__ == "__main__":
    main()
