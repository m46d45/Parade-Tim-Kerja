"""Parade of Trades – Streamlit app (zone-flow classroom model)."""
from __future__ import annotations

import importlib
import tempfile
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

import matplotlib.pyplot as plt
import streamlit as st

import parade_of_trades_analysis as _a
import parade_of_trades_core as _c
import parade_of_trades_plots as _p

_c = importlib.reload(_c)
_p = importlib.reload(_p)
_a = importlib.reload(_a)

from parade_of_trades_analysis import (
    compare_tommelein2020,
    export_result_csv,
    export_result_excel,
    run_replications,
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
    plot_duration_histogram,
    plot_line_of_balance,
    plot_line_of_balance_detail,
    plot_replication_summary,
    plot_utilization,
)

_APP_BUILD = "2026-08-03-tabs-zoneflow-v9"
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
    if _HEADER_BANNER.exists():
        st.image(str(_HEADER_BANNER), use_container_width=True)
    if _LOGO_ICON.exists():
        c1, c2 = st.columns([1, 8], vertical_alignment="center")
        with c1:
            st.image(str(_LOGO_ICON), width=72)
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
) -> ParadeConfig:
    names = [_trade_name(i) for i in range(len(pairs))]
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
        batch_size=_batch_size(),
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
        "Batch dipakai di **Single / Compare / Sweep / Replications** (zone-flow). "
        "Tab Takt 2020 = model klasik paper (terpisah)."
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
            res = ParadeOfTrades(cfg).run()
            st.session_state.single_result = res
            st.success(
                f"Selesai · Duration **{res.duration}** · batch={cfg.batch_size} · "
                f"{_starts_caption(res)}"
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
        _export_block(result, "single")


def tab_compare(total_units: int, seed: Optional[int], n_trades: int) -> None:
    st.subheader("Compare 2 (zone-flow)")
    st.markdown(
        '<div class="pot-callout">'
        "Bandingkan dua setup zone-flow dengan <strong>batch yang sama</strong> (sidebar). "
        "Contoh: A = No variability, B = Medium — lihat duration, idle, start trade, dan LOB."
        "</div>",
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### Skenario A")
        pa = _capacity_setup("cmp_a", n_trades, "no_variability", 1.0)
    with c2:
        st.markdown("### Skenario B")
        pb = _capacity_setup("cmp_b", n_trades, "medium", 1.0)

    if st.button("Run comparison", type="primary", key="run_cmp"):
        ra = ParadeOfTrades(_build_config_from_pairs(pa, total_units, seed)).run()
        rb = ParadeOfTrades(_build_config_from_pairs(pb, total_units, seed)).run()
        st.session_state.cmp = {"A": ra, "B": rb}

    if "cmp" not in st.session_state:
        st.info("Atur A & B → **Run comparison**.")
        return

    results = st.session_state.cmp
    m1, m2 = st.columns(2)
    with m1:
        st.markdown("**A**")
        _metrics_row(results["A"])
        st.caption(_starts_caption(results["A"]))
    with m2:
        st.markdown("**B**")
        _metrics_row(results["B"])
        st.caption(_starts_caption(results["B"]))

    # Delta table
    da, db = results["A"].duration, results["B"].duration
    st.markdown("##### Ringkasan selisih")
    st.dataframe(
        [{
            "Metrik": "Duration",
            "A": da,
            "B": db,
            "B − A": db - da,
        }, {
            "Metrik": "Total idle",
            "A": results["A"].total_idle_capacity,
            "B": results["B"].total_idle_capacity,
            "B − A": results["B"].total_idle_capacity - results["A"].total_idle_capacity,
        }, {
            "Metrik": "Peak WIP",
            "A": _peak_wip(results["A"]),
            "B": _peak_wip(results["B"]),
            "B − A": _peak_wip(results["B"]) - _peak_wip(results["A"]),
        }],
        use_container_width=True,
        hide_index=True,
    )

    fig, ax = plt.subplots(figsize=(9, 5))
    plot_comparison_lob(
        {"A (zone-flow)": results["A"], "B (zone-flow)": results["B"]},
        ax=ax,
        title=f"LOB Compare — batch {_batch_size()}",
    )
    fig.tight_layout()
    _fig_to_st(fig)

    t1, t2 = st.tabs(["Metrics A", "Metrics B"])
    with t1:
        _trade_table(results["A"])
    with t2:
        _trade_table(results["B"])


def tab_sweep(total_units: int, seed: Optional[int], n_trades: int) -> None:
    st.subheader("Variability sweep (zone-flow)")
    st.markdown(
        '<div class="pot-callout">'
        "Satu <strong>kecepatan dasar</strong> untuk semua trade; jalankan beberapa level "
        "<strong>variability per zona</strong>. Batch dari sidebar. "
        "Bandingkan duration & idle — variability biasanya menambah delay & waste."
        "</div>",
        unsafe_allow_html=True,
    )
    base = _base_speed_input("sweep_base", "Kecepatan dasar semua trade", 1.0)
    selected = st.multiselect(
        "Level variability",
        PRESET_OPTIONS,
        default=PRESET_OPTIONS,
        format_func=lambda x: VAR_LABELS.get(x, x),
        key="sweep_vars",
    )
    st.caption(f"Batch handoff = **{_batch_size()}** · Total zona = **{total_units}** · Seed = **{seed}**")

    if st.button("Run sweep", type="primary", key="run_sweep") and selected:
        results = {}
        for p in selected:
            pairs = [_pair_from_base_and_var(base, p)] * n_trades
            results[p] = ParadeOfTrades(_build_config_from_pairs(pairs, total_units, seed)).run()
        st.session_state.sweep = results

    if "sweep" not in st.session_state:
        st.info("Pilih level variability → **Run sweep**.")
        return

    results = st.session_state.sweep
    rows = []
    for name, r in results.items():
        rows.append({
            "Variability": VAR_LABELS.get(name, name),
            "Duration": r.duration,
            "vs Ideal": round(r.duration - r.ideal_duration, 1),
            "Idle": r.total_idle_capacity,
            "Peak WIP": _peak_wip(r),
            "Throughput": round(r.system_throughput, 3),
            "T1 start": r.trade_metrics[0].start_period,
            "T5 start": r.trade_metrics[-1].start_period,
            "T5 finish": r.trade_metrics[-1].periods_to_finish,
        })
    rows_sorted = sorted(rows, key=lambda x: x["Duration"])
    st.markdown("##### Hasil (diurutkan duration naik)")
    st.dataframe(rows_sorted, use_container_width=True, hide_index=True)

    fig, ax = plt.subplots(figsize=(9, 5))
    # short labels for legend
    short = {k: k.replace("_", " ") for k in results}
    plot_comparison_lob(
        {short[k]: v for k, v in results.items()},
        ax=ax,
        title=f"Sweep LOB — base speed · batch {_batch_size()}",
    )
    fig.tight_layout()
    _fig_to_st(fig)


def tab_takt(total_units: int, seed: Optional[int]) -> None:
    st.subheader("Takt 2020 — model klasik (literatur)")
    st.markdown(
        '<div class="pot-warn">'
        "<strong>Tab ini berbeda dari zone-flow.</strong> "
        "Ini replikasi skenario <em>Tommelein (2020)</em>: dadu capacity klasik + "
        "takt rate + standby (capacity buffer). "
        "Batch sidebar <em>tidak</em> dipakai di sini. "
        "Gunakan untuk diskusi paper / takt planning — bukan pengganti Single run kelas."
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        """
**Apa yang dijalankan**
- Beberapa skenario paper (die + takt + standby)
- Banyak replikasi → ringkasan duration / standby usage
- Handoff model klasik paper (`same_period_handoff` sesuai fungsi analisis)
"""
    )
    c1, c2, c3 = st.columns(3)
    n_reps = int(c1.number_input("Replications", 10, 500, 50, 10, key="takt_n"))
    sb = int(c2.number_input("Seed base", 0, value=seed or 0, key="takt_s"))
    units = int(c3.number_input("Total units (paper)", 1, 1000, min(total_units, 100), 5, key="takt_u"))

    if st.button("Run Tommelein 2020", type="primary", key="run_takt"):
        with st.spinner("Menjalankan skenario paper…"):
            st.session_state.takt = compare_tommelein2020(
                n_reps=n_reps,
                seed_base=sb,
                total_units=units,
                staggered=False,
                same_period_handoff=False,
                verbose=False,
            )

    if "takt" not in st.session_state:
        st.info("Atur replikasi → **Run Tommelein 2020**.")
        return

    cmp = st.session_state.takt
    st.markdown("##### Ringkasan skenario")
    st.dataframe(cmp.summary_rows(), use_container_width=True, hide_index=True)

    try:
        fig, ax = plt.subplots(figsize=(9, 4.5))
        plot_duration_histogram(cmp.batches, ax=ax)
        fig.tight_layout()
        _fig_to_st(fig)
    except Exception as exc:
        st.warning(f"Histogram tidak tersedia: {exc}")

    st.caption(
        "Interpretasi: takt + standby menstabilkan workflow vs dadu murni — "
        "lihat paper Tommelein (2020) / materi P2SL."
    )


def tab_reps(total_units: int, seed: Optional[int], n_trades: int) -> None:
    st.subheader("Replications (zone-flow)")
    st.markdown(
        '<div class="pot-callout">'
        "Banyak run acak pada setup zone-flow yang sama (seed berbeda). "
        "Penting bila ada variability: satu run bisa beruntung/sial. "
        f"Batch = <strong>{_batch_size()}</strong> dari sidebar."
        "</div>",
        unsafe_allow_html=True,
    )
    pairs = _capacity_setup("rep", n_trades, "medium", 1.0)
    c1, c2 = st.columns(2)
    n = int(c1.number_input("Jumlah replikasi", 5, 1000, 100, 10, key="rep_n"))
    sb = int(c2.number_input("Seed base", 0, value=seed or 0, key="rep_s"))

    if st.button("Run replications", type="primary", key="run_reps"):
        cfg = _build_config_from_pairs(pairs, total_units, None)
        with st.spinner(f"Menjalankan {n} replikasi zone-flow…"):
            batch = run_replications(cfg, n_reps=n, seed_base=sb, verbose=False)
        st.session_state.reps = {"main": batch}
        st.session_state.reps_cfg_note = (
            f"batch={cfg.batch_size}, zone_flow={cfg.zone_flow}, n={n}, seed_base={sb}"
        )

    if "reps" not in st.session_state:
        st.info("Atur setup → **Run replications**.")
        return

    main = st.session_state.reps["main"]
    st.caption(st.session_state.get("reps_cfg_note", ""))
    st.markdown("##### Ringkasan statistik")
    st.dataframe(main.summary_table(), use_container_width=True, hide_index=True)

    try:
        fig = plot_replication_summary(st.session_state.reps, show=False)
        _fig_to_st(fig)
    except Exception as exc:
        st.warning(f"Plot ringkasan: {exc}")
        try:
            fig, ax = plt.subplots(figsize=(8, 4))
            plot_duration_histogram({"main": main}, ax=ax)
            fig.tight_layout()
            _fig_to_st(fig)
        except Exception as exc2:
            st.caption(f"Histogram fallback gagal: {exc2}")


def tab_manual() -> None:
    st.subheader("📖 Manual belajar")
    st.markdown(
        '<div class="pot-field">'
        "Panduan zone-flow untuk kelas: kecepatan & variability per zona, "
        "batch/one-piece, cara baca LOB, latihan terarah."
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


def tab_about() -> None:
    st.subheader("Tentang aplikasi")
    st.markdown(
        f"""
**Parade of Trades** — simulasi Lean Construction untuk floor cycle Indonesia.

| | |
|---|---|
| Build | `{_APP_BUILD}` |
| Model utama | **Zone-flow** (kelas) |
| Batch default | **4 zona** (sidebar) |
| Trade | 5 (Bekisting → … → Finishing) |
| Deploy | Streamlit Cloud + repo GitHub |

### Prinsip zone-flow
1. **Kecepatan** = progress pada **satu zona** (bukan bulk multi-zona per undian).
2. **Tanpa variability** → rate sama untuk setiap zona trade itu.
3. **Dengan variability** → rate diundi **sekali per zona** (faktor × dasar).
4. **Batch N** → kumpulkan N zona, lepas ke trade hilir di periode berikutnya.
5. **One-piece (N=1)** → lepas tiap zona.
6. LOB **mulai dari 0**; garis trade **bergeser** (tidak menumpuk).

### Variability (× dasar)
| Level | Faktor |
|-------|--------|
| No | ×1.0 tetap |
| Low | ×0.75 / ×1.25 |
| Medium | ×0.5 / ×1.5 |
| High | ×0.25 / ×1.75 |
| Very high | ×0.1 / ×1.9 |

### Tab
| Tab | Model |
|-----|--------|
| Single run | Zone-flow |
| Compare 2 | Zone-flow A vs B |
| Sweep | Zone-flow × level var |
| Takt 2020 | **Klasik paper** (dadu + takt/standby) |
| Replications | Zone-flow Monte Carlo |
| Manual / About | Dokumentasi |

### Referensi
Tommelein, Riley & Howell (1999); Choo & Tommelein (1999); Tommelein (2020) / P2SL UC Berkeley.
"""
    )


def main() -> None:
    total_units, seed, n_trades = render_sidebar()
    _render_header()
    tabs = st.tabs([
        "Single run",
        "Compare 2",
        "Sweep",
        "Takt 2020",
        "Replications",
        "Manual",
        "About",
    ])
    with tabs[0]:
        tab_single_run(total_units, seed, n_trades)
    with tabs[1]:
        tab_compare(total_units, seed, n_trades)
    with tabs[2]:
        tab_sweep(total_units, seed, n_trades)
    with tabs[3]:
        tab_takt(total_units, seed)
    with tabs[4]:
        tab_reps(total_units, seed, n_trades)
    with tabs[5]:
        tab_manual()
    with tabs[6]:
        tab_about()


if __name__ == "__main__":
    main()
