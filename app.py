"""
Parade of Trades – Interactive Streamlit App
=============================================

Lean Construction simulation (Tommelein, Riley & Howell 1999).

Run:
    streamlit run app.py
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import matplotlib.pyplot as plt
import streamlit as st

from parade_of_trades_analysis import (
    compare_scenarios,
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
    TradeConfig,
    tommelein2020_scenarios,
)
from parade_of_trades_plots import (
    PRESET_DISPLAY,
    plot_buffer_profile,
    plot_comparison_buffers,
    plot_comparison_lob,
    plot_duration_histogram,
    plot_line_of_balance,
    plot_replication_summary,
    plot_time_on_site_boxplot,
    plot_utilization,
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

# Asset paths (relative to this file)
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
PRESET_LABELS = {
    "no_variability": "No variability (5/5)",
    "low": "Low (4/6)",
    "medium": "Medium (3/7)",
    "high": "High (2/8)",
    "very_high": "Very high (1/9)",
    "custom": "Custom pair…",
}


def _render_header() -> None:
    """Top banner + title strip inspired by classic Parade of Trades imagery."""
    if _HEADER_BANNER.exists():
        st.markdown(
            """
            <style>
            /* Soften Streamlit top padding under banner */
            div[data-testid="stAppViewContainer"] > .main > div:first-child {
                padding-top: 0.5rem;
            }
            .pot-header-caption {
                text-align: center;
                color: #5a6a7a;
                font-size: 0.85rem;
                margin: 0.15rem 0 0.6rem 0;
            }
            .pot-title-row {
                display: flex;
                align-items: center;
                gap: 0.85rem;
                margin: 0.4rem 0 0.2rem 0;
            }
            .pot-title-row h1 {
                margin: 0;
                padding: 0;
                font-size: 1.85rem;
                line-height: 1.2;
            }
            .pot-subtitle {
                color: #4a5568;
                font-size: 0.95rem;
                margin: 0 0 0.75rem 0;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        st.image(str(_HEADER_BANNER), use_container_width=True)
        st.markdown(
            '<p class="pot-header-caption">'
            "Parade lima trade floor cycle beton Indonesia — "
            "bekisting → tulangan → cor → bongkar → finishing · "
            "homage ke Parade of Trades (Tommelein)"
            "</p>",
            unsafe_allow_html=True,
        )

    # Title row with optional logo
    if _LOGO_ICON.exists():
        c_logo, c_text = st.columns([1, 8], vertical_alignment="center")
        with c_logo:
            st.image(str(_LOGO_ICON), width=72)
        with c_text:
            st.markdown("## Parade of Trades")
            st.caption(
                "Simulasi Lean Construction · floor cycle beton Indonesia · "
                "berdasarkan Tommelein (UC Berkeley)"
            )
    else:
        st.title("Parade of Trades")
        st.caption(
            "Simulasi Lean Construction · floor cycle beton Indonesia · "
            "berdasarkan Tommelein (UC Berkeley)"
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pair_from_preset(preset: str) -> Tuple[int, int]:
    return CAPACITY_PRESETS[preset]


def _format_metric(value, fmt: str = "{:.2f}") -> str:
    if isinstance(value, float):
        return fmt.format(value)
    return str(value)


def _build_config_from_pairs(
    pairs: Sequence[Tuple[int, int]],
    total_units: int,
    seed: Optional[int],
    trade_names: Optional[Sequence[str]] = None,
    takt_rate: Optional[int] = None,
    standby_capacity: int = 0,
    same_period_handoff: bool = False,
    staggered_mobilization: bool = False,
) -> ParadeConfig:
    return ParadeConfig.from_pairs(
        pairs=list(pairs),
        trade_names=trade_names,
        total_units=total_units,
        seed=seed,
        takt_rate=takt_rate,
        standby_capacity=standby_capacity,
        same_period_handoff=same_period_handoff,
        staggered_mobilization=staggered_mobilization,
    )


def _run_config(cfg: ParadeConfig) -> ParadeResult:
    sim = ParadeOfTrades(cfg)
    return sim.run()


def _trade_selector(
    key_prefix: str,
    n_trades: int = 5,
    default_preset: str = "medium",
    uniform: bool = True,
) -> List[Tuple[int, int]]:
    """
    UI block: choose capacity pair for each trade (or one uniform preset).

    Returns list of (low, high) pairs.
    """
    if uniform:
        choice = st.selectbox(
            "Capacity distribution (all trades)",
            options=PRESET_OPTIONS + ["custom"],
            index=PRESET_OPTIONS.index(default_preset)
            if default_preset in PRESET_OPTIONS
            else 2,
            format_func=lambda x: PRESET_LABELS.get(x, x),
            key=f"{key_prefix}_uniform_preset",
        )
        if choice == "custom":
            c1, c2 = st.columns(2)
            low = c1.number_input(
                "Low capacity", min_value=0, max_value=50, value=3, key=f"{key_prefix}_u_low"
            )
            high = c2.number_input(
                "High capacity", min_value=0, max_value=50, value=7, key=f"{key_prefix}_u_high"
            )
            if low > high:
                st.warning("Low must be ≤ high — swapping.")
                low, high = high, low
            return [(int(low), int(high))] * n_trades
        return [_pair_from_preset(choice)] * n_trades

    # Per-trade
    pairs: List[Tuple[int, int]] = []
    for i in range(n_trades):
        name = DEFAULT_TRADE_NAMES[i] if i < len(DEFAULT_TRADE_NAMES) else f"Trade {i + 1}"
        with st.expander(f"Trade {i + 1}: {name}", expanded=(i == 0)):
            choice = st.selectbox(
                "Preset",
                options=PRESET_OPTIONS + ["custom"],
                index=PRESET_OPTIONS.index(default_preset)
                if default_preset in PRESET_OPTIONS
                else 2,
                format_func=lambda x: PRESET_LABELS.get(x, x),
                key=f"{key_prefix}_t{i}_preset",
            )
            if choice == "custom":
                c1, c2 = st.columns(2)
                low = c1.number_input(
                    "Low", min_value=0, max_value=50, value=3, key=f"{key_prefix}_t{i}_low"
                )
                high = c2.number_input(
                    "High", min_value=0, max_value=50, value=7, key=f"{key_prefix}_t{i}_high"
                )
                if low > high:
                    low, high = high, low
                pairs.append((int(low), int(high)))
            else:
                pairs.append(_pair_from_preset(choice))
    return pairs


def _metrics_row(result: ParadeResult) -> None:
    peak_wip = max((sum(h.buffers) for h in result.history), default=0)
    delay = result.duration - result.ideal_duration
    cols = st.columns(6 if result.config.takt_enabled else 5)
    cols[0].metric("Duration", f"{result.duration}", help="Periods until last trade finishes")
    cols[1].metric(
        "vs Ideal",
        f"{delay:+.1f}",
        delta=f"ideal {result.ideal_duration:.0f}",
        delta_color="inverse",
    )
    cols[2].metric("Throughput", f"{result.system_throughput:.3f}", help="Units / period")
    cols[3].metric("Total Idle", f"{result.total_idle_capacity}", help="Wasted capacity unit-periods")
    cols[4].metric("Peak WIP", f"{peak_wip}", help="Peak simultaneous total buffer")
    if result.config.takt_enabled:
        cols[5].metric(
            "Standby used",
            f"{result.total_standby_used}",
            help="Capacity-buffer unit-periods deployed",
        )


def _trade_table(result: ParadeResult) -> None:
    rows = []
    for i, m in enumerate(result.trade_metrics):
        row = {
            "#": i + 1,
            "Trade": m.name,
            "Capacity": f"{m.capacity_pair[0]}/{m.capacity_pair[1]}",
            "Executions": m.executions,
            "Production": m.total_production,
            "Idle": m.total_idle,
            "Utilization %": round(100 * m.utilization, 1),
            "Start": m.start_period if m.start_period is not None else "—",
            "Finish": m.periods_to_finish,
            "Time on site": m.time_on_site,
        }
        if result.config.takt_enabled:
            row["Standby used"] = m.total_standby_used
        rows.append(row)
    st.dataframe(rows, use_container_width=True, hide_index=True)

    if result.max_buffer:
        buf_rows = []
        for j, mx in enumerate(result.max_buffer):
            up = result.config.trades[j].name
            down = result.config.trades[j + 1].name
            buf_rows.append(
                {
                    "Buffer": j + 1,
                    "From": up,
                    "To": down,
                    "Max WIP": mx,
                }
            )
        st.caption("Max WIP at each interface")
        st.dataframe(buf_rows, use_container_width=True, hide_index=True)


def _flow_controls(
    key_prefix: str = "flow",
) -> Tuple[bool, bool]:
    """
    Zone sequence / handoff controls.

    Returns (same_period_handoff, staggered_mobilization).
    Default: next-period handoff (each zone waits 1 period between trades).
    """
    mode = st.radio(
        "Alur zona antar trade",
        options=[
            "Sekuens zona (disarankan): T1 selesai dulu → baru T2 di periode berikutnya",
            "Hand-off langsung (classic game): output T1 bisa diambil T2 di periode yang sama",
        ],
        index=0,
        key=f"{key_prefix}_handoff",
        help=(
            "Mode sekuens: setiap unit/zona dikerjakan trade demi trade dengan jeda "
            "minimal 1 periode. Line of Balance akan bergeser jelas per trade."
        ),
    )
    same_period = mode.startswith("Hand-off langsung")
    if same_period:
        st.caption(
            "Classic computer game: buffer di-update sekuensial dalam satu periode "
            "(trade hilir bisa langsung memakai output hulu hari yang sama)."
        )
        staggered = st.checkbox(
            "Tambah mobilisasi berjenjang (T_i mulai periode i)",
            value=False,
            key=f"{key_prefix}_stag",
        )
    else:
        st.caption(
            "Per zona: Bekisting (periode t) → Tulangan (t+1) → Cor (t+2) → … "
            "Beberapa zona bisa dikerjakan paralel di tahap berbeda (parade)."
        )
        staggered = False
    return same_period, staggered


def _takt_controls(key_prefix: str = "takt") -> Tuple[Optional[int], int]:
    """Takt planning controls. Returns (takt_rate|None, standby)."""
    enable = st.checkbox(
        "Enable takt planning + capacity buffer (Tommelein 2020)",
        value=False,
        key=f"{key_prefix}_enable",
        help="Commit to a minimum hand-off rate; use standby capacity when the die is low",
    )
    if not enable:
        return None, 0
    c1, c2 = st.columns(2)
    takt_rate = int(
        c1.number_input(
            "Takt rate (units/period)",
            min_value=1,
            max_value=50,
            value=5,
            key=f"{key_prefix}_rate",
        )
    )
    standby = int(
        c2.number_input(
            "Standby capacity",
            min_value=0,
            max_value=20,
            value=1,
            key=f"{key_prefix}_stby",
            help="Max extra units deployed when die < takt",
        )
    )
    st.caption(
        f"Mode: takt={takt_rate}, standby={standby} — "
        "jika die < takt, standby menutup shortfall (bila pekerjaan tersedia)."
    )
    return takt_rate, standby


def _export_buttons(result: ParadeResult, key_prefix: str) -> None:
    """Download CSV / Excel for a single result."""
    st.markdown("##### Export")
    c1, c2 = st.columns(2)
    # Build files in-memory
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        hist_path = td_path / "history.csv"
        xlsx_path = td_path / "run.xlsx"
        export_result_csv(result, hist_path, include_history=True)
        export_result_excel(result, xlsx_path)
        summary_path = hist_path.with_name(hist_path.stem + "_summary.csv")
        with c1:
            st.download_button(
                "⬇ History CSV",
                data=hist_path.read_bytes(),
                file_name="parade_history.csv",
                mime="text/csv",
                key=f"{key_prefix}_dl_hist",
                use_container_width=True,
            )
            if summary_path.exists():
                st.download_button(
                    "⬇ Summary CSV",
                    data=summary_path.read_bytes(),
                    file_name="parade_summary.csv",
                    mime="text/csv",
                    key=f"{key_prefix}_dl_sum",
                    use_container_width=True,
                )
        with c2:
            st.download_button(
                "⬇ Excel workbook",
                data=xlsx_path.read_bytes(),
                file_name="parade_run.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"{key_prefix}_dl_xlsx",
                use_container_width=True,
            )


def _fig_to_st(fig) -> None:
    """Render a matplotlib figure in Streamlit and close it."""
    st.pyplot(fig, clear_figure=True)
    plt.close(fig)


def _plot_single_result(result: ParadeResult, key_suffix: str = "") -> None:
    tab_lob, tab_buf, tab_util = st.tabs(
        ["📈 Line of Balance", "📦 Buffer / WIP", "⚙️ Utilization"]
    )
    with tab_lob:
        fig, ax = plt.subplots(figsize=(9, 4.5))
        plot_line_of_balance(result, ax=ax)
        fig.tight_layout()
        _fig_to_st(fig)
    with tab_buf:
        c_left, c_right = st.columns(2)
        with c_left:
            fig, ax = plt.subplots(figsize=(6, 4))
            plot_buffer_profile(result, ax=ax, stacked=False)
            fig.tight_layout()
            _fig_to_st(fig)
        with c_right:
            fig, ax = plt.subplots(figsize=(6, 4))
            plot_buffer_profile(result, ax=ax, stacked=True, show_max=False)
            fig.tight_layout()
            _fig_to_st(fig)
    with tab_util:
        fig, ax = plt.subplots(figsize=(8, 3.8))
        plot_utilization(result, ax=ax)
        fig.tight_layout()
        _fig_to_st(fig)


def _period_detail(result: ParadeResult) -> None:
    """Expandable period-by-period history table."""
    if not result.history:
        st.info("No history yet — run or step the simulation.")
        return
    names = [t.name for t in result.config.trades]
    rows = []
    for rec in result.history:
        row = {"Period": rec.period}
        for i, name in enumerate(names):
            short = name if len(name) <= 16 else name[:15] + "…"
            row[f"{short} cap"] = rec.capacity[i]
            row[f"{short} prod"] = rec.production[i]
            row[f"{short} cum"] = rec.cumulative[i]
        for j, b in enumerate(rec.buffers):
            row[f"Buf{j + 1}"] = b
        rows.append(row)
    st.dataframe(rows, use_container_width=True, hide_index=True, height=320)


# ---------------------------------------------------------------------------
# Session-state helpers (step mode)
# ---------------------------------------------------------------------------

def _init_step_state() -> None:
    if "step_sim" not in st.session_state:
        st.session_state.step_sim = None
    if "step_cfg_sig" not in st.session_state:
        st.session_state.step_cfg_sig = None


def _cfg_signature(
    pairs: Sequence[Tuple[int, int]], total_units: int, seed: Optional[int]
) -> tuple:
    return (tuple(pairs), total_units, seed)


def _ensure_step_sim(
    pairs: Sequence[Tuple[int, int]], total_units: int, seed: Optional[int]
) -> ParadeOfTrades:
    sig = _cfg_signature(pairs, total_units, seed)
    if (
        st.session_state.step_sim is None
        or st.session_state.step_cfg_sig != sig
    ):
        cfg = _build_config_from_pairs(pairs, total_units, seed)
        st.session_state.step_sim = ParadeOfTrades(cfg)
        st.session_state.step_cfg_sig = sig
    return st.session_state.step_sim


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

def render_sidebar() -> Tuple[int, Optional[int], int]:
    if _LOGO_ICON.exists():
        sc1, sc2 = st.sidebar.columns([1, 2.2])
        with sc1:
            st.image(str(_LOGO_ICON), width=64)
        with sc2:
            st.markdown("### Parade of Trades")
            st.caption("Floor cycle Indonesia")
    else:
        st.sidebar.title("🏗️ Parade of Trades")
    st.sidebar.markdown(
        "Simulasi Lean Construction: dampak **variability** + "
        "**sequential dependence** terhadap throughput, duration, dan waste."
    )
    st.sidebar.divider()

    total_units = st.sidebar.number_input(
        "Total work units (zona)",
        min_value=1,
        max_value=1000,
        value=100,
        step=10,
        help="Default classic game: 100 poker chips / zona kerja",
    )
    use_seed = st.sidebar.checkbox("Fix random seed", value=True)
    seed: Optional[int] = None
    if use_seed:
        seed = int(
            st.sidebar.number_input(
                "Seed", min_value=0, max_value=10_000_000, value=42, step=1
            )
        )

    n_trades = st.sidebar.slider(
        "Number of trades",
        min_value=2,
        max_value=7,
        value=5,
        help="Default floor cycle: 5 stages",
    )

    st.sidebar.divider()
    st.sidebar.markdown("📖 Tab **Manual** = panduan belajar mahasiswa.")
    if _MANUAL_PATH.exists():
        st.sidebar.download_button(
            "⬇ Unduh manual belajar",
            data=_MANUAL_PATH.read_text(encoding="utf-8").encode("utf-8"),
            file_name="Parade_of_Trades_Manual_Belajar.md",
            mime="text/markdown",
            use_container_width=True,
            key="sidebar_manual_dl",
        )
    st.sidebar.caption(
        "Tommelein, Riley & Howell (1999) · Choo & Tommelein (1999) · "
        "UC Berkeley P2SL"
    )
    st.sidebar.caption(
        "Mean capacity of classic presets is always **5**. "
        "Only the spread (variability) changes."
    )
    return int(total_units), seed, int(n_trades)


# ---------------------------------------------------------------------------
# Tab 1 – Single run
# ---------------------------------------------------------------------------

def tab_single_run(total_units: int, seed: Optional[int], n_trades: int) -> None:
    st.subheader("Single scenario")
    st.markdown(
        "Atur distribusi capacity, lalu **Run** (otomatis sampai selesai) "
        "atau **Step** (satu periode per klik)."
    )

    col_cfg, col_ctrl = st.columns([1.1, 1.4])

    with col_cfg:
        st.markdown("##### Capacity setup")
        mode = st.radio(
            "Assignment mode",
            options=["Uniform (all trades same)", "Per trade"],
            horizontal=True,
            key="single_mode",
        )
        uniform = mode.startswith("Uniform")
        pairs = _trade_selector(
            key_prefix="single",
            n_trades=n_trades,
            default_preset="medium",
            uniform=uniform,
        )
        same_period, staggered = _flow_controls("single")
        takt_rate, standby = _takt_controls("single_takt")

        # Preview pairs
        labels = [
            DEFAULT_TRADE_NAMES[i] if i < len(DEFAULT_TRADE_NAMES) else f"Trade {i + 1}"
            for i in range(n_trades)
        ]
        preview = " → ".join(f"{labels[i][:12]} ({pairs[i][0]}/{pairs[i][1]})" for i in range(n_trades))
        st.caption(f"Parade: {preview}")
        if not same_period:
            st.caption(
                "Urutan per zona: "
                + " → ".join(f"T{i+1}(p+{i})" for i in range(n_trades))
            )

    with col_ctrl:
        st.markdown("##### Controls")
        b1, b2, b3, b4 = st.columns(4)
        run_clicked = b1.button("▶ Run", type="primary", use_container_width=True)
        step_clicked = b2.button("⏭ Step", use_container_width=True)
        reset_clicked = b3.button("↺ Reset", use_container_width=True)
        finish_clicked = b4.button("⏩ Finish", use_container_width=True, help="Step until complete")

        _init_step_state()
        full_sig = (
            tuple(pairs), total_units, seed, takt_rate, standby,
            same_period, staggered,
        )

        def _make_cfg() -> ParadeConfig:
            return _build_config_from_pairs(
                pairs, total_units, seed,
                takt_rate=takt_rate,
                standby_capacity=standby,
                same_period_handoff=same_period,
                staggered_mobilization=staggered,
            )

        if reset_clicked:
            cfg = _make_cfg()
            st.session_state.step_sim = ParadeOfTrades(cfg)
            st.session_state.step_cfg_sig = full_sig
            st.session_state.single_result = None
            st.success("Simulation reset.")

        if run_clicked:
            cfg = _make_cfg()
            sim = ParadeOfTrades(cfg)
            result = sim.run()
            st.session_state.single_result = result
            st.session_state.step_sim = sim
            st.session_state.step_cfg_sig = full_sig

        if step_clicked:
            if (
                st.session_state.step_sim is None
                or st.session_state.step_cfg_sig != full_sig
            ):
                st.session_state.step_sim = ParadeOfTrades(_make_cfg())
                st.session_state.step_cfg_sig = full_sig
            sim = st.session_state.step_sim
            if sim.is_complete:
                st.warning("Already complete — Reset to run again.")
            else:
                sim.step()
                st.session_state.single_result = sim.get_result()

        if finish_clicked:
            if (
                st.session_state.step_sim is None
                or st.session_state.step_cfg_sig != full_sig
            ):
                st.session_state.step_sim = ParadeOfTrades(_make_cfg())
                st.session_state.step_cfg_sig = full_sig
            sim = st.session_state.step_sim
            if sim.is_complete:
                st.warning("Already complete — Reset to run again.")
            else:
                while not sim.is_complete:
                    sim.step()
                st.session_state.single_result = sim.get_result()

        # Live status from step sim if present
        sim = st.session_state.get("step_sim")
        if sim is not None and st.session_state.step_cfg_sig == full_sig:
            progress = sim.cumulative[-1] / total_units if total_units else 0
            st.progress(
                min(1.0, progress),
                text=(
                    f"Period {sim.period} · finished {sim.cumulative[-1]}/{total_units} "
                    + ("· ✅ COMPLETE" if sim.is_complete else "")
                ),
            )
            # Mini buffer strip
            if sim.buffers:
                st.caption(
                    "Buffers now: "
                    + " | ".join(f"B{j + 1}={b}" for j, b in enumerate(sim.buffers))
                    + f"  ·  raw left={sim.raw_remaining}"
                )

    st.divider()

    result: Optional[ParadeResult] = st.session_state.get("single_result")
    # Also accept in-progress step sim with history
    if result is None:
        sim = st.session_state.get("step_sim")
        if sim is not None and sim.history:
            result = sim.get_result()

    if result is None or not result.history:
        st.info("Pilih capacity, lalu tekan **Run** atau **Step** untuk memulai.")
        return

    _metrics_row(result)

    left, right = st.columns([1.2, 1])
    with left:
        _plot_single_result(result)
    with right:
        st.markdown("##### Trade metrics")
        _trade_table(result)
        with st.expander("Period-by-period history", expanded=False):
            _period_detail(result)
        _export_buttons(result, "single")


# ---------------------------------------------------------------------------
# Tab 2 – Compare two scenarios
# ---------------------------------------------------------------------------

def tab_compare(total_units: int, seed: Optional[int], n_trades: int) -> None:
    st.subheader("Compare two scenarios")
    st.markdown(
        "Bandingkan dua konfigurasi variability secara berdampingan "
        "(seed & total units sama dari sidebar)."
    )

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("### Scenario A")
        mode_a = st.radio(
            "Mode A",
            ["Uniform", "Per trade"],
            horizontal=True,
            key="cmp_mode_a",
        )
        pairs_a = _trade_selector(
            key_prefix="cmp_a",
            n_trades=n_trades,
            default_preset="no_variability",
            uniform=mode_a == "Uniform",
        )
        st.caption(" → ".join(f"{p[0]}/{p[1]}" for p in pairs_a))

    with col_b:
        st.markdown("### Scenario B")
        mode_b = st.radio(
            "Mode B",
            ["Uniform", "Per trade"],
            horizontal=True,
            key="cmp_mode_b",
        )
        pairs_b = _trade_selector(
            key_prefix="cmp_b",
            n_trades=n_trades,
            default_preset="very_high",
            uniform=mode_b == "Uniform",
        )
        st.caption(" → ".join(f"{p[0]}/{p[1]}" for p in pairs_b))

    same_period, staggered = _flow_controls("cmp")
    run_cmp = st.button("▶ Run comparison", type="primary", key="run_cmp")

    if run_cmp or st.session_state.get("cmp_results"):
        def _label(tag: str, pairs: Sequence[Tuple[int, int]]) -> str:
            # Compact label e.g. "A: 5/5" or "A: mixed"
            uniq = set(pairs)
            if len(uniq) == 1:
                lo, hi = next(iter(uniq))
                return f"{tag}: {lo}/{hi}"
            return f"{tag}: mixed"

        if run_cmp:
            cfg_a = _build_config_from_pairs(
                pairs_a, total_units, seed,
                same_period_handoff=same_period,
                staggered_mobilization=staggered,
            )
            cfg_b = _build_config_from_pairs(
                pairs_b, total_units, seed,
                same_period_handoff=same_period,
                staggered_mobilization=staggered,
            )
            # Each scenario gets its own RNG from the same seed (fair settings compare)
            res_a = _run_config(cfg_a)
            res_b = _run_config(cfg_b)
            label_a = _label("A", pairs_a)
            label_b = _label("B", pairs_b)
            st.session_state.cmp_results = {
                label_a: res_a,
                label_b: res_b,
            }
            st.session_state.cmp_labels = (label_a, label_b)

        results: Dict[str, ParadeResult] = st.session_state.cmp_results
        label_a, label_b = st.session_state.get(
            "cmp_labels", tuple(results.keys())[:2]
        )
        res_a = results[label_a]
        res_b = results[label_b]

        st.divider()
        st.markdown("##### Metrics head-to-head")
        m1, m2 = st.columns(2)
        with m1:
            st.markdown("**Scenario A**")
            _metrics_row(res_a)
        with m2:
            st.markdown("**Scenario B**")
            _metrics_row(res_b)

        # Delta summary
        d_dur = res_b.duration - res_a.duration
        d_idle = res_b.total_idle_capacity - res_a.total_idle_capacity
        peak_a = max((sum(h.buffers) for h in res_a.history), default=0)
        peak_b = max((sum(h.buffers) for h in res_b.history), default=0)
        d_wip = peak_b - peak_a
        st.info(
            f"**B − A:** duration {d_dur:+d} periods · "
            f"idle {d_idle:+d} · peak WIP {d_wip:+d}"
        )

        # Overlay charts
        st.markdown("##### Overlay charts")
        c1, c2 = st.columns(2)
        with c1:
            fig, ax = plt.subplots(figsize=(7, 4.2))
            plot_comparison_lob(results, ax=ax, title="Line of Balance (last trade)")
            fig.tight_layout()
            _fig_to_st(fig)
        with c2:
            fig, ax = plt.subplots(figsize=(7, 4.2))
            plot_comparison_buffers(results, ax=ax, title="Total WIP over time")
            fig.tight_layout()
            _fig_to_st(fig)

        # Side detail
        st.markdown("##### Detail per scenario")
        d1, d2 = st.columns(2)
        with d1:
            st.markdown("**A – trades**")
            _trade_table(res_a)
            fig, ax = plt.subplots(figsize=(6, 3.5))
            plot_line_of_balance(res_a, ax=ax, title="A – Line of Balance")
            fig.tight_layout()
            _fig_to_st(fig)
            fig, ax = plt.subplots(figsize=(6, 3.2))
            plot_buffer_profile(res_a, ax=ax, title="A – Buffers")
            fig.tight_layout()
            _fig_to_st(fig)
        with d2:
            st.markdown("**B – trades**")
            _trade_table(res_b)
            fig, ax = plt.subplots(figsize=(6, 3.5))
            plot_line_of_balance(res_b, ax=ax, title="B – Line of Balance")
            fig.tight_layout()
            _fig_to_st(fig)
            fig, ax = plt.subplots(figsize=(6, 3.2))
            plot_buffer_profile(res_b, ax=ax, title="B – Buffers")
            fig.tight_layout()
            _fig_to_st(fig)


# ---------------------------------------------------------------------------
# Tab 3 – Multi-preset sweep
# ---------------------------------------------------------------------------

def tab_sweep(total_units: int, seed: Optional[int], n_trades: int) -> None:
    st.subheader("Preset sweep")
    st.markdown(
        "Jalankan semua (atau sebagian) preset classic Tommelein dengan "
        "seed yang sama — cocok untuk demo di kelas."
    )

    selected = st.multiselect(
        "Presets to run",
        options=PRESET_OPTIONS,
        default=PRESET_OPTIONS,
        format_func=lambda x: PRESET_LABELS.get(x, x),
    )
    same_period, staggered = _flow_controls("sweep")
    run = st.button("▶ Run sweep", type="primary", key="run_sweep")

    if not selected:
        st.warning("Pilih minimal satu preset.")
        return

    if run or st.session_state.get("sweep_results"):
        if run:
            results: Dict[str, ParadeResult] = {}
            progress = st.progress(0.0, text="Running…")
            for i, p in enumerate(selected):
                pairs = [_pair_from_preset(p)] * n_trades
                cfg = _build_config_from_pairs(
                    pairs, total_units, seed,
                    same_period_handoff=same_period,
                    staggered_mobilization=staggered,
                )
                results[p] = _run_config(cfg)
                progress.progress((i + 1) / len(selected), text=f"Done: {p}")
            st.session_state.sweep_results = results
            progress.empty()

        results = st.session_state.sweep_results
        # Filter to currently selected if keys still match
        results = {k: v for k, v in results.items() if k in selected} or results

        # Summary table
        rows = []
        for name, r in results.items():
            peak = max((sum(h.buffers) for h in r.history), default=0)
            avg_util = sum(m.utilization for m in r.trade_metrics) / len(r.trade_metrics)
            rows.append(
                {
                    "Preset": PRESET_LABELS.get(name, name),
                    "Duration": r.duration,
                    "Throughput": round(r.system_throughput, 3),
                    "Total idle": r.total_idle_capacity,
                    "Peak WIP": peak,
                    "Avg util %": round(100 * avg_util, 1),
                    "Delay vs ideal": round(r.duration - r.ideal_duration, 1),
                }
            )
        st.dataframe(rows, use_container_width=True, hide_index=True)

        c1, c2 = st.columns(2)
        with c1:
            fig, ax = plt.subplots(figsize=(8, 4.5))
            plot_comparison_lob(results, ax=ax)
            fig.tight_layout()
            _fig_to_st(fig)
        with c2:
            fig, ax = plt.subplots(figsize=(8, 4.5))
            plot_comparison_buffers(results, ax=ax)
            fig.tight_layout()
            _fig_to_st(fig)

        # Metric bars via comparison figure pieces
        from parade_of_trades_plots import plot_comparison_metrics

        fig, axes = plt.subplots(1, 3, figsize=(11, 3.6))
        plot_comparison_metrics(results, axes=axes)
        fig.suptitle("Duration · Idle · Peak WIP", fontsize=11)
        fig.tight_layout()
        _fig_to_st(fig)


# ---------------------------------------------------------------------------
# Tab 4 – Takt (Tommelein 2020)
# ---------------------------------------------------------------------------

def tab_takt(total_units: int, seed: Optional[int]) -> None:
    st.subheader("Takt planning + capacity buffer")
    st.markdown(
        """
Bandingkan tiga skenario **Tommelein (2020) IGLC28**:

| # | Skenario | Die | Buffer |
|---|----------|-----|--------|
| S1 | Classic | 4/6 | — |
| S2 | **Takted** | 4/6 | standby=1 untuk memenuhi takt=5 |
| S3 | Add capacity | 5/7 | — (menambah kapasitas, bukan standby) |

**Insight:** S2 ≈ produksi 5/6 die, tetapi lebih *reliable* (variabilitas teredam)
dibanding S3 yang mean lebih tinggi tapi std dev lebih besar.
        """
    )

    c1, c2, c3 = st.columns(3)
    n_reps = int(
        c1.number_input("Replications", min_value=10, max_value=500, value=50, step=10,
                        key="takt_nreps")
    )
    seed_base = int(
        c2.number_input("Seed base", min_value=0, value=seed if seed is not None else 0,
                        key="takt_seedbase")
    )
    same_period = c3.checkbox(
        "Hand-off same-period (classic)",
        value=False,
        key="takt_same_period",
        help="Jika off (default): sekuens zona next-period",
    )

    run = st.button("▶ Run Tommelein 2020 comparison", type="primary", key="run_takt2020")

    if run:
        with st.spinner(f"Running {n_reps} replications × 3 scenarios…"):
            cmp = compare_tommelein2020(
                n_reps=n_reps,
                seed_base=seed_base,
                total_units=total_units,
                staggered=False,
                same_period_handoff=same_period,
                verbose=False,
            )
            st.session_state.takt2020 = cmp

    if "takt2020" not in st.session_state:
        st.info("Tekan **Run** untuk mereplikasi S1 / S2 / S3.")
        return

    cmp = st.session_state.takt2020
    st.dataframe(cmp.summary_rows(), use_container_width=True, hide_index=True)

    batches = cmp.batches
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    plot_duration_histogram(batches, ax=axes[0], title="Duration distribution")
    # mean bars
    names = list(batches.keys())
    means = [batches[n].stats()["duration"].mean for n in names]
    stds = [batches[n].stats()["duration"].std for n in names]
    axes[1].bar(range(len(names)), means, yerr=stds, capsize=4,
                color=["#d62728", "#1f77b4", "#8c564b"], edgecolor="white")
    axes[1].set_xticks(range(len(names)))
    axes[1].set_xticklabels(names, rotation=15, ha="right", fontsize=8)
    axes[1].set_ylabel("Duration (mean ± std)")
    axes[1].set_title("Mean project duration")
    axes[1].grid(True, axis="y", linestyle="--", alpha=0.4)
    fig.tight_layout()
    _fig_to_st(fig)

    fig, ax = plt.subplots(figsize=(11, 4.5))
    plot_time_on_site_boxplot(batches, ax=ax)
    fig.tight_layout()
    _fig_to_st(fig)

    # Single-run illustration of S2 vs S1 for the given seed
    st.markdown("##### Single-run illustration (same seed)")
    configs = tommelein2020_scenarios(
        total_units=total_units, seed=seed if seed is not None else seed_base,
        staggered=staggered,
    )
    single_results = {name: ParadeOfTrades(cfg).run() for name, cfg in configs.items()}
    c1, c2 = st.columns(2)
    with c1:
        fig, ax = plt.subplots(figsize=(6, 3.8))
        plot_comparison_lob(single_results, ax=ax, title="LOB – one seed")
        fig.tight_layout()
        _fig_to_st(fig)
    with c2:
        fig, ax = plt.subplots(figsize=(6, 3.8))
        plot_comparison_buffers(single_results, ax=ax, title="Total WIP – one seed")
        fig.tight_layout()
        _fig_to_st(fig)

    # Export comparison
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        xlsx = Path(td) / "tommelein2020.xlsx"
        cmp.export_excel(xlsx)
        st.download_button(
            "⬇ Export comparison Excel",
            data=xlsx.read_bytes(),
            file_name="tommelein2020_comparison.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="takt_dl_xlsx",
        )


# ---------------------------------------------------------------------------
# Tab 5 – Replications
# ---------------------------------------------------------------------------

def tab_replications(total_units: int, seed: Optional[int], n_trades: int) -> None:
    st.subheader("Multiple replications + statistics")
    st.markdown(
        "Jalankan banyak replikasi independen untuk mendapatkan distribusi "
        "duration, idle, WIP, dan time-on-site (bukan satu seed saja)."
    )

    col_l, col_r = st.columns([1, 1])
    with col_l:
        mode = st.radio(
            "Assignment",
            ["Uniform", "Per trade"],
            horizontal=True,
            key="rep_mode",
        )
        pairs = _trade_selector(
            key_prefix="rep",
            n_trades=n_trades,
            default_preset="medium",
            uniform=mode == "Uniform",
        )
        same_period, staggered = _flow_controls("rep")
        takt_rate, standby = _takt_controls("rep_takt")

    with col_r:
        n_reps = int(
            st.number_input("Number of replications", min_value=5, max_value=1000,
                            value=100, step=10, key="rep_n")
        )
        seed_base = int(
            st.number_input(
                "Seed base",
                min_value=0,
                value=seed if seed is not None else 0,
                key="rep_seedbase",
                help="Seeds used: base, base+1, …, base+n-1",
            )
        )
        also_compare = st.checkbox(
            "Also run no_variability + very_high for comparison",
            value=True,
            key="rep_also",
        )
        run = st.button("▶ Run replications", type="primary", key="run_reps")

    if run:
        with st.spinner(f"Running replications…"):
            main_cfg = _build_config_from_pairs(
                pairs, total_units, None,
                takt_rate=takt_rate,
                standby_capacity=standby,
                same_period_handoff=same_period,
                staggered_mobilization=staggered,
            )
            batches = {
                "main": run_replications(
                    main_cfg, n_reps=n_reps, seed_base=seed_base, verbose=False
                )
            }
            if also_compare:
                for label, preset in [
                    ("no_variability", "no_variability"),
                    ("very_high", "very_high"),
                ]:
                    cfg = ParadeConfig.from_preset(
                        preset, n_trades=n_trades, total_units=total_units,
                        takt_rate=takt_rate, standby_capacity=standby,
                        same_period_handoff=same_period,
                        staggered_mobilization=staggered,
                    )
                    batches[label] = run_replications(
                        cfg, n_reps=n_reps, seed_base=seed_base, verbose=False
                    )
            st.session_state.rep_batches = batches

    if "rep_batches" not in st.session_state:
        st.info("Atur capacity & tekan **Run replications**.")
        return

    batches = st.session_state.rep_batches
    main = batches["main"]

    st.markdown("##### Summary statistics (main scenario)")
    st.dataframe(main.summary_table(), use_container_width=True, hide_index=True)

    tos = [s.as_dict() for s in main.trade_time_on_site_stats()]
    st.caption("Time on site by trade")
    st.dataframe(tos, use_container_width=True, hide_index=True)

    fig = plot_replication_summary(
        batches, title=f"Replications (n={main.n_reps}, seed_base={main.seed_base})",
        show=False,
    )
    _fig_to_st(fig)

    # Downloads
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        xlsx = td_path / "reps.xlsx"
        csv_path = td_path / "reps.csv"
        main.export_excel(xlsx)
        main.export_csv(csv_path)
        c1, c2 = st.columns(2)
        c1.download_button(
            "⬇ Main scenario Excel",
            data=xlsx.read_bytes(),
            file_name="replications.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="rep_dl_xlsx",
            use_container_width=True,
        )
        c2.download_button(
            "⬇ Main scenario CSV",
            data=csv_path.read_bytes(),
            file_name="replications.csv",
            mime="text/csv",
            key="rep_dl_csv",
            use_container_width=True,
        )


# ---------------------------------------------------------------------------
# Tab – Manual
# ---------------------------------------------------------------------------

def _load_manual_text() -> str:
    if _MANUAL_PATH.exists():
        return _MANUAL_PATH.read_text(encoding="utf-8")
    return (
        "# Manual tidak ditemukan\n\n"
        "File `MANUAL.md` tidak ada di folder proyek. "
        "Pastikan file tersebut berada di root aplikasi."
    )


def tab_manual() -> None:
    st.subheader("📖 Manual belajar")
    st.caption(
        "Panduan untuk mahasiswa: konsep Parade of Trades, cara memakai situs, "
        "latihan terarah, membaca grafik, dan refleksi — tanpa perlu coding."
    )

    manual_text = _load_manual_text()

    # Quick jump + download
    top_l, top_r = st.columns([3, 1])
    with top_l:
        section = st.selectbox(
            "Lompat ke bagian",
            options=[
                "(tampilkan semua)",
                "1. Tujuan pembelajaran",
                "2. Apa itu Parade of Trades?",
                "3. Cara membuka simulasi",
                "4. Mengenal tampilan situs",
                "5. Aturan main (cara kerja model)",
                "6. Pilihan capacity (dadu virtual)",
                "7. Cara memakai setiap tab",
                "8. Cara membaca metrik & grafik",
                "9. Latihan terarah (ikuti urutan ini)",
                "10. Takt planning & capacity buffer",
                "11. Replikasi: kenapa satu run tidak cukup?",
                "12. Menyimpan & melaporkan hasil",
                "13. Pertanyaan diskusi & refleksi",
                "14. FAQ mahasiswa",
                "15. Glosarium singkat",
                "16. Referensi untuk dibaca lanjut",
            ],
            key="manual_jump",
        )
    with top_r:
        st.download_button(
            "⬇ Unduh manual belajar",
            data=manual_text.encode("utf-8"),
            file_name="Parade_of_Trades_Manual_Belajar.md",
            mime="text/markdown",
            use_container_width=True,
            key="manual_dl",
        )

    # Optional section filter (by markdown heading)
    display = manual_text
    if section != "(tampilkan semua)":
        # Extract from chosen "## N. ..." until next "## " at same level
        marker = f"## {section}"
        # Headings in file are like "## 1. Apa itu..."
        start = manual_text.find(marker)
        if start < 0:
            # try without exact match noise
            num = section.split(".", 1)[0]
            for line in manual_text.splitlines():
                if line.startswith(f"## {num}."):
                    start = manual_text.find(line)
                    marker = line
                    break
        if start >= 0:
            rest = manual_text[start + len(marker) :]
            # find next ## heading
            next_h = rest.find("\n## ")
            if next_h >= 0:
                display = marker + rest[: next_h]
            else:
                display = marker + rest
        else:
            st.warning("Bagian tidak ditemukan; menampilkan seluruh manual.")
            display = manual_text

    st.divider()
    st.markdown(display)


# ---------------------------------------------------------------------------
# Tab – About
# ---------------------------------------------------------------------------

def tab_about() -> None:
    st.subheader("Tentang simulasi")
    st.markdown(
        """
**Parade of Trades** (juga disebut *Parade Game* / *Dice Game*) adalah alat
edukasi Lean Construction yang memperlihatkan dampak **variability** dan
**ketergantungan sekuensial** antar trade pada:

- **Duration** proyek
- **Throughput** (laju penyelesaian)
- **WIP / buffer** antar trade
- **Waste** berupa *idle capacity* (kapasitas terbuang karena menunggu)

Proses default: **floor cycle beton Indonesia**
(bekisting → tulangan → cor → bongkar → finishing), 100 zona, mean capacity 5.

### Aturan singkat
1. Trade berurutan me-roll capacity 50/50 (*low/high*) tiap periode.
2. Produksi aktual = `min(capacity, buffer upstream, sisa pekerjaan)`.
3. Buffer di-update **sekuensial** dalam periode yang sama.
4. Selesai saat trade terakhir menyelesaikan semua unit.

### Insight
Menaikkan variability (mean tetap 5) → duration ↑, idle ↑, WIP ↑, util hilir ↓.  
**Takt + standby** meredam reverberasi variability → schedule lebih prediktif.

### Preset capacity (mean = 5)
| Preset | Pair |
|--------|------|
| No variability | 5/5 |
| Low | 4/6 |
| Medium | 3/7 |
| High | 2/8 |
| Very high | 1/9 |

### Referensi
- Tommelein, Riley & Howell (1999), *ASCE J. Constr. Eng. Manage.*
- Choo & Tommelein (1999), Technical Report 99-1, UC Berkeley
- Tommelein (2020), *Takting the Parade of Trades*, IGLC28  
  doi:10.24928/2020/0076

👉 **Panduan belajar mahasiswa** (latihan, cara baca grafik, diskusi) ada di tab **📖 Manual**.
        """
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    total_units, seed, n_trades = render_sidebar()

    _render_header()

    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(
        [
            "🎮 Single run",
            "⚖️ Compare 2",
            "📊 Preset sweep",
            "⏱️ Takt 2020",
            "🔁 Replications",
            "📖 Manual",
            "ℹ️ About",
        ]
    )
    with tab1:
        tab_single_run(total_units, seed, n_trades)
    with tab2:
        tab_compare(total_units, seed, n_trades)
    with tab3:
        tab_sweep(total_units, seed, n_trades)
    with tab4:
        tab_takt(total_units, seed)
    with tab5:
        tab_replications(total_units, seed, n_trades)
    with tab6:
        tab_manual()
    with tab7:
        tab_about()


if __name__ == "__main__":
    main()
