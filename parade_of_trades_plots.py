"""
Parade of Trades – Visualization
================================

Matplotlib charts for results from ``parade_of_trades_core``:

  1. Line of Balance  – cumulative output per trade vs time
  2. Buffer / WIP profile – inventory between trades over time
  3. Scenario comparison – side-by-side LOB, buffers, and metrics

Typical usage
-------------
>>> from parade_of_trades_core import run_preset, compare_presets
>>> from parade_of_trades_plots import plot_run, plot_comparison
>>> result = run_preset("medium", seed=42, verbose=False)
>>> plot_run(result, show=True, save_path="output/medium.png")
>>> results = compare_presets(seed=42, verbose=False)
>>> plot_comparison(results, show=True, save_path="output/compare.png")
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple, Union

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from parade_of_trades_core import (
    CAPACITY_PRESETS,
    ParadeResult,
    compare_presets,
    run_preset,
)

# ---------------------------------------------------------------------------
# Style
# ---------------------------------------------------------------------------

# Distinct, colourblind-friendly palette for up to 7 trades
TRADE_COLORS: Tuple[str, ...] = (
    "#1f77b4",  # blue
    "#ff7f0e",  # orange
    "#2ca02c",  # green
    "#d62728",  # red
    "#9467bd",  # purple
    "#8c564b",  # brown
    "#e377c2",  # pink
)

BUFFER_COLORS: Tuple[str, ...] = (
    "#4c78a8",
    "#f58518",
    "#54a24b",
    "#e45756",
    "#b279a2",
    "#9d755d",
)

PRESET_COLORS: Dict[str, str] = {
    "no_variability": "#2ca02c",
    "low": "#1f77b4",
    "medium": "#ff7f0e",
    "high": "#d62728",
    "very_high": "#9467bd",
}

PRESET_DISPLAY: Dict[str, str] = {
    "no_variability": "No var (5/5)",
    "low": "Low (4/6)",
    "medium": "Medium (3/7)",
    "high": "High (2/8)",
    "very_high": "Very high (1/9)",
}


def _trade_color(i: int) -> str:
    return TRADE_COLORS[i % len(TRADE_COLORS)]


def _buffer_color(i: int) -> str:
    return BUFFER_COLORS[i % len(BUFFER_COLORS)]


def _short_name(name: str, max_len: int = 18) -> str:
    if len(name) <= max_len:
        return name
    return name[: max_len - 1] + "…"


def _apply_axes_style(ax: Axes) -> None:
    ax.grid(True, which="major", linestyle="--", alpha=0.45)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))


def _ensure_parent(path: Union[str, Path]) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _save_or_show(
    fig: Figure,
    show: bool = True,
    save_path: Optional[Union[str, Path]] = None,
    dpi: int = 140,
) -> Figure:
    if save_path is not None:
        path = _ensure_parent(save_path)
        fig.savefig(path, dpi=dpi, bbox_inches="tight", facecolor="white")
    if show:
        plt.show()
    else:
        plt.close(fig)
    return fig


# ---------------------------------------------------------------------------
# Single-run plots
# ---------------------------------------------------------------------------

def plot_line_of_balance(
    result: ParadeResult,
    ax: Optional[Axes] = None,
    title: Optional[str] = None,
    show_ideal: bool = True,
) -> Axes:
    """
    Line of Balance: cumulative zones vs period as **straight lines**.

    Slope of each line = speed (zona/periode). Deterministic paces use
    continuous progress so lambat (0.5) is a clean diagonal, not a staircase.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(9, 5.2))

    # Prefer continuous progress (straight pace); else integer cumulative
    if hasattr(result, "fractional_cumulative_series"):
        cum = result.fractional_cumulative_series()
    else:
        cum = result.cumulative_series()
    n = result.config.n_trades
    total = result.config.total_units
    periods = list(range(len(cum[0])))
    n_per = len(periods)
    mark_every = 1 if n_per <= 40 else max(1, n_per // 20)
    markers = ("o", "s", "^", "D", "v", "P", "X")
    for i in range(n):
        trade = result.config.trades[i]
        speed = trade.mean
        label = f"T{i + 1}: {_short_name(trade.name)} ({trade.label()})"
        if getattr(trade, "deterministic", False) and speed > 0:
            label += f" · slope {speed:g}"
        ax.plot(
            periods,
            cum[i],
            color=_trade_color(i),
            linewidth=2.4,
            linestyle="-",
            marker=markers[i % len(markers)],
            markersize=4.5 if n_per <= 40 else 3.5,
            markevery=mark_every,
            label=label,
            zorder=3 + i,
            alpha=0.95,
        )

    if show_ideal:
        mean_cap = min(t.mean for t in result.config.trades)
        if mean_cap > 0:
            ax.plot(
                [0, total / mean_cap], [0, total],
                color="0.45", linestyle=":", linewidth=1.6,
                label=f"Ideal (bottleneck {mean_cap:g} zona/periode)",
            )

    ax.axhline(total, color="0.7", linestyle="--", linewidth=1.0, alpha=0.8)
    ax.set_xlim(0, max(periods) if periods else 1)
    ax.set_ylim(0, total * 1.06)
    ax.set_xlabel("Periode (1, 2, 3, …)")
    ax.set_ylabel("Zona kumulatif (1, 2, 3, …)")
    ax.set_title(title or "Line of Balance — kemiringan = kecepatan")

    if n_per <= 50:
        ax.xaxis.set_major_locator(mticker.MultipleLocator(1 if n_per <= 24 else 2))
    else:
        ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True, nbins=16))
    if total <= 40:
        ax.yaxis.set_major_locator(mticker.MultipleLocator(1))
    else:
        ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True, nbins=12))
    ax.grid(True, which="major", linestyle="--", alpha=0.5)

    # Speed legend callout
    notes = []
    for i, trade in enumerate(result.config.trades):
        if getattr(trade, "deterministic", False):
            notes.append(f"T{i+1}: {trade.mean:g} zona/periode")
    if notes:
        ax.text(
            0.02, 0.98,
            "Kecepatan (kemiringan garis):\n" + " · ".join(notes[:5]),
            transform=ax.transAxes, va="top", ha="left", fontsize=8,
            color="#1a365d",
            bbox=dict(boxstyle="round,pad=0.35", facecolor="#ebf8ff",
                      edgecolor="#90cdf4", alpha=0.92), zorder=10,
        )

    ax.legend(loc="lower right", fontsize=7.5, framealpha=0.92)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    return ax


def plot_line_of_balance_detail(
    result: ParadeResult,
    ax: Optional[Axes] = None,
    max_period: int = 12,
    title: Optional[str] = None,
) -> Axes:
    """Early-period LOB with every period tick — straight pace lines."""
    if ax is None:
        _, ax = plt.subplots(figsize=(9, 4.2))
    if hasattr(result, "fractional_cumulative_series"):
        cum_full = result.fractional_cumulative_series()
    else:
        cum_full = result.cumulative_series()
    n = result.config.n_trades
    total = result.config.total_units
    end = min(max_period, len(cum_full[0]) - 1)
    periods = list(range(end + 1))
    markers = ("o", "s", "^", "D", "v", "P", "X")
    for i in range(n):
        trade = result.config.trades[i]
        ys = cum_full[i][: end + 1]
        ax.plot(
            periods, ys, color=_trade_color(i), linewidth=2.6,
            marker=markers[i % len(markers)], markersize=6.5, markevery=1,
            label=f"T{i + 1}: {_short_name(trade.name)} ({trade.label()})",
            zorder=3 + i,
        )
    ax.set_xlim(0, end)
    ymax = max(max(cum_full[i][end] for i in range(n)), 1)
    ax.set_ylim(0, min(total, ymax + 2) * 1.1)
    ax.set_xlabel("Periode")
    ax.set_ylabel("Zona (kumulatif)")
    ax.set_title(title or f"Detail LOB — periode 0–{end} (garis lurus = kecepatan konstan)")
    ax.xaxis.set_major_locator(mticker.MultipleLocator(1))
    ax.yaxis.set_major_locator(mticker.MultipleLocator(1))
    ax.grid(True, which="major", linestyle="--", alpha=0.55)
    ax.legend(loc="upper left", fontsize=8, framealpha=0.92)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    return ax


def plot_buffer_profile(
    result: ParadeResult,
    ax: Optional[Axes] = None,
    title: Optional[str] = None,
    show_max: bool = True,
    stacked: bool = False,
) -> Axes:
    """
    Buffer / WIP profile over time for each interface between trades.

    Parameters
    ----------
    show_max :
        Draw a dashed horizontal line at each interface's observed max WIP.
    stacked :
        If True, draw a stacked area chart of total WIP composition.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 5))

    buf = result.buffer_series()  # [interface][period], period 0 = 0
    n_if = result.config.n_interfaces
    if n_if == 0:
        ax.text(0.5, 0.5, "No interfaces (single trade)", ha="center", va="center")
        ax.set_axis_off()
        return ax

    periods = list(range(len(buf[0])))

    if stacked:
        # Stacked area of all buffers
        labels = []
        series = []
        for j in range(n_if):
            up = result.config.trades[j]
            down = result.config.trades[j + 1]
            labels.append(f"B{j + 1}: {_short_name(up.name, 12)}→{_short_name(down.name, 12)}")
            series.append(buf[j])
        ax.stackplot(
            periods,
            *series,
            labels=labels,
            colors=[_buffer_color(j) for j in range(n_if)],
            alpha=0.85,
        )
        ax.set_ylabel("WIP (zona, ditumpuk)")
    else:
        for j in range(n_if):
            up = result.config.trades[j]
            down = result.config.trades[j + 1]
            label = f"B{j + 1}: {_short_name(up.name, 14)} → {_short_name(down.name, 14)}"
            ax.plot(
                periods,
                buf[j],
                color=_buffer_color(j),
                linewidth=1.8,
                label=label,
            )
            if show_max and result.max_buffer[j] > 0:
                ax.axhline(
                    result.max_buffer[j],
                    color=_buffer_color(j),
                    linestyle="--",
                    linewidth=1.0,
                    alpha=0.55,
                )
        ax.set_ylabel("Isi buffer (zona)")

    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    ax.set_xlabel("Periode")
    ax.set_title(title or "Buffer / WIP antar tim")
    ax.legend(loc="upper right", fontsize=8, framealpha=0.92)
    _apply_axes_style(ax)
    return ax


def plot_utilization(
    result: ParadeResult,
    ax: Optional[Axes] = None,
    title: Optional[str] = None,
) -> Axes:
    """Horizontal bar chart of utilization and idle capacity per trade."""
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 4))

    metrics = result.trade_metrics
    names = [f"T{i + 1}: {_short_name(m.name, 20)}" for i, m in enumerate(metrics)]
    utils = [100.0 * m.utilization for m in metrics]
    colors = [_trade_color(i) for i in range(len(metrics))]
    y = list(range(len(metrics)))

    bars = ax.barh(y, utils, color=colors, height=0.65, edgecolor="white")
    ax.set_yticks(y)
    ax.set_yticklabels(names)
    ax.set_xlim(0, 105)
    ax.set_xlabel("Utilisasi (%)")
    ax.set_title(title or "Utilisasi kapasitas per tim")
    ax.axvline(100, color="0.6", linestyle="--", linewidth=1.0)

    for bar, m in zip(bars, metrics):
        util = 100.0 * m.utilization
        ax.text(
            min(util + 1.5, 98),
            bar.get_y() + bar.get_height() / 2,
            f"{util:.1f}%  (idle {m.total_idle})",
            va="center",
            ha="left",
            fontsize=8,
        )

    ax.invert_yaxis()
    _apply_axes_style(ax)
    ax.grid(False, axis="y")
    return ax


def plot_run(
    result: ParadeResult,
    *,
    title: Optional[str] = None,
    show: bool = True,
    save_path: Optional[Union[str, Path]] = None,
    figsize: Tuple[float, float] = (12, 10),
    dpi: int = 140,
) -> Figure:
    """
    Combined single-run figure: Line of Balance + Buffer profile + Utilization.

    Returns the matplotlib Figure.
    """
    fig = plt.figure(figsize=figsize, constrained_layout=True)
    gs = fig.add_gridspec(2, 2, height_ratios=[1.15, 1.0])

    ax_lob = fig.add_subplot(gs[0, :])
    ax_buf = fig.add_subplot(gs[1, 0])
    ax_util = fig.add_subplot(gs[1, 1])

    seed = result.config.seed
    pairs = ", ".join(t.label() for t in result.config.trades)
    header = title or (
        f"Parade of Trades  |  capacity [{pairs}]  |  "
        f"seed={seed}  |  duration={result.duration}  |  "
        f"throughput={result.system_throughput:.2f}"
    )
    fig.suptitle(header, fontsize=12, fontweight="semibold")

    plot_line_of_balance(result, ax=ax_lob, title="Line of Balance")
    plot_buffer_profile(result, ax=ax_buf, title="Buffer / WIP Profile")
    plot_utilization(result, ax=ax_util, title="Utilization & Idle Capacity")

    # Metrics strip as figure text
    peak_wip = max((sum(h.buffers) for h in result.history), default=0)
    fig.text(
        0.01,
        -0.01,
        (
            f"Ideal duration: {result.ideal_duration:.1f}  ·  "
            f"Delay: {result.duration - result.ideal_duration:+.1f}  ·  "
            f"Total idle: {result.total_idle_capacity}  ·  "
            f"Peak simultaneous WIP: {peak_wip}  ·  "
            f"Max buffer per interface: {result.max_buffer}"
        ),
        fontsize=8,
        color="0.35",
        ha="left",
        va="top",
        transform=fig.transFigure,
    )

    return _save_or_show(fig, show=show, save_path=save_path, dpi=dpi)


# ---------------------------------------------------------------------------
# Multi-scenario comparison
# ---------------------------------------------------------------------------

def plot_comparison_lob(
    results: Dict[str, ParadeResult],
    ax: Optional[Axes] = None,
    title: Optional[str] = None,
    last_trade_only: bool = True,
) -> Axes:
    """
    Overlay Line of Balance curves for several scenarios.

    By default only the *last* trade (project completion) is shown per
    scenario so the panel stays readable. Every series is forced to start
    at (period=0, zona=0).
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 5))

    first = next(iter(results.values()))
    total = max(r.config.total_units for r in results.values())
    mean_cap = min(float(t.mean) for t in first.config.trades)
    if mean_cap > 0:
        ax.plot(
            [0, total / mean_cap],
            [0, total],
            color="0.5",
            linestyle=":",
            linewidth=1.5,
            label=f"Ideal ({mean_cap:g}/periode) dari (0,0)",
        )

    # Distinct cycle if names are Skenario N (not in PRESET_COLORS)
    fallback_colors = ["#2563eb", "#ea580c", "#16a34a", "#dc2626", "#7c3aed", "#0891b2"]
    max_period = 0

    for idx, (name, result) in enumerate(results.items()):
        cum = result.cumulative_series()
        color = PRESET_COLORS.get(name, fallback_colors[idx % len(fallback_colors)])
        display = PRESET_DISPLAY.get(name, name)
        batch = getattr(result.config, "batch_size", None)
        batch_tag = f", batch={batch}" if batch is not None else ""

        if last_trade_only:
            series = list(cum[-1])
            # Force origin (0, 0)
            if not series or series[0] != 0:
                series = [0] + series
            periods = list(range(len(series)))
            max_period = max(max_period, periods[-1] if periods else 0)
            # Start marker at origin + line
            ax.plot(
                periods,
                series,
                color=color,
                linewidth=2.2,
                solid_capstyle="round",
                label=f"{display} (T={result.duration}{batch_tag})",
            )
            ax.plot(0, 0, marker="o", color=color, markersize=5, zorder=5)
            # Mark first production period (when curve leaves zero)
            for p, y in enumerate(series):
                if y > 0:
                    ax.plot(p, y, marker="o", color=color, markersize=4, zorder=5)
                    break
        else:
            for i, series in enumerate(cum):
                series = list(series)
                if not series or series[0] != 0:
                    series = [0] + series
                periods = list(range(len(series)))
                max_period = max(max_period, periods[-1] if periods else 0)
                ax.plot(
                    periods,
                    series,
                    color=color,
                    linewidth=1.4,
                    alpha=0.35 + 0.12 * i,
                    label=f"{display} T{i + 1}" if i == len(cum) - 1 else None,
                )

    ax.axhline(total, color="0.7", linestyle="--", linewidth=1.0, label=None)
    ax.set_xlim(0, max(max_period, 1) * 1.02)
    ax.set_ylim(0, total * 1.08)
    ax.set_xlabel("Periode (mulai 0)")
    ax.set_ylabel("Zona kumulatif tim terakhir (mulai 0)")
    ax.set_title(title or "Line of Balance — perbandingan skenario (dari 0,0)")
    ax.legend(loc="lower right", fontsize=8, framealpha=0.92)
    _apply_axes_style(ax)
    return ax


def plot_comparison_buffers(
    results: Dict[str, ParadeResult],
    ax: Optional[Axes] = None,
    title: Optional[str] = None,
) -> Axes:
    """Total WIP (sum of all interface buffers) over time, per scenario."""
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 5))

    fallback = ["#2563eb", "#ea580c", "#16a34a", "#dc2626", "#7c3aed", "#0891b2"]
    for idx, (name, result) in enumerate(results.items()):
        if result.config.n_interfaces == 0:
            continue
        buf = result.buffer_series()
        total_wip = [sum(buf[j][t] for j in range(len(buf))) for t in range(len(buf[0]))]
        color = PRESET_COLORS.get(name, fallback[idx % len(fallback)])
        display = PRESET_DISPLAY.get(name, name)
        peak = max(total_wip) if total_wip else 0
        ax.plot(
            list(range(len(total_wip))),
            total_wip,
            color=color,
            linewidth=1.9,
            label=f"{display} (puncak={peak})",
        )

    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    ax.set_xlabel("Periode")
    ax.set_ylabel("Total WIP (semua buffer)")
    ax.set_title(title or "Buffer / WIP — perbandingan skenario")
    ax.legend(loc="upper right", fontsize=8, framealpha=0.92)
    _apply_axes_style(ax)
    return ax


def plot_comparison_utilization(
    results: Dict[str, ParadeResult],
    ax: Optional[Axes] = None,
    title: Optional[str] = None,
) -> Axes:
    """
    Grouped bar chart: utilization (%) per trade, one group per scenario.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(10, 4.5))

    names = list(results.keys())
    if not names:
        return ax
    n_scen = len(names)
    n_trades = results[names[0]].config.n_trades
    fallback = ["#2563eb", "#ea580c", "#16a34a", "#dc2626", "#7c3aed", "#0891b2"]

    # x positions for trade groups
    import numpy as np
    x = np.arange(n_trades)
    width = min(0.8 / max(n_scen, 1), 0.18)
    offsets = (np.arange(n_scen) - (n_scen - 1) / 2.0) * width

    for i, name in enumerate(names):
        r = results[name]
        utils = [100.0 * m.utilization for m in r.trade_metrics]
        color = PRESET_COLORS.get(name, fallback[i % len(fallback)])
        display = PRESET_DISPLAY.get(name, name)
        ax.bar(
            x + offsets[i],
            utils,
            width=width * 0.92,
            color=color,
            edgecolor="white",
            linewidth=0.5,
            label=display,
        )

    ax.set_xticks(x)
    ax.set_xticklabels([f"T{i + 1}" for i in range(n_trades)])
    ax.set_ylim(0, 105)
    ax.set_ylabel("Utilisasi (%)")
    ax.set_xlabel("Tim")
    ax.set_title(title or "Utilisasi per tim — perbandingan skenario")
    ax.axhline(100, color="0.6", linestyle="--", linewidth=0.9)
    ax.legend(loc="lower right", fontsize=8, framealpha=0.92, ncol=min(n_scen, 3))
    _apply_axes_style(ax)
    return ax



def plot_comparison_costs(
    cost_by_scenario: Dict[str, dict],
    ax: Optional[Axes] = None,
    title: Optional[str] = None,
    *,
    mode: str = "total",
) -> Axes:
    """
    Bar chart biaya antar skenario.

    ``cost_by_scenario[name] = {"active": float, "idle": float, "total": float}``
    mode: "total" | "idle" | "stacked" (aktif+idle)
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(9.0, 4.2))
    names = list(cost_by_scenario.keys())
    if not names:
        return ax
    fallback = ["#2563eb", "#ea580c", "#16a34a", "#dc2626", "#7c3aed", "#0891b2"]
    import numpy as np
    x = np.arange(len(names))

    if mode == "stacked":
        act = [float(cost_by_scenario[n].get("active", 0) or 0) for n in names]
        idle = [float(cost_by_scenario[n].get("idle", 0) or 0) for n in names]
        # recompute total from parts (never trust a separate total field for stack)
        totals = [a + b for a, b in zip(act, idle)]
        bars_a = ax.bar(
            x, act, color="#2563eb", edgecolor="white", linewidth=0.6,
            label="Biaya aktif", width=0.62, zorder=2,
        )
        bars_i = ax.bar(
            x, idle, bottom=act, color="#f59e0b", edgecolor="white", linewidth=0.6,
            label="Biaya idle", width=0.62, zorder=2,
        )
        y_max = max(totals) if totals else 1.0
        for i in range(len(names)):
            # labels inside segments if large enough
            if act[i] > 0.04 * y_max:
                ax.text(i, act[i] / 2.0, f"{act[i]:,.0f}", ha="center", va="center",
                        fontsize=7, color="white", fontweight="bold", zorder=3)
            if idle[i] > 0.04 * y_max:
                ax.text(i, act[i] + idle[i] / 2.0, f"{idle[i]:,.0f}", ha="center", va="center",
                        fontsize=7, color="#1f2937", fontweight="bold", zorder=3)
            ax.text(i, totals[i], f"Σ {totals[i]:,.0f}", ha="center", va="bottom",
                    fontsize=8, color="#111827", zorder=3)
        ax.legend(loc="upper right", fontsize=8, framealpha=0.92)
        ax.set_ylabel("Biaya (aktif + idle)")
        ax.set_ylim(0, y_max * 1.18 if y_max > 0 else 1)
    elif mode == "grouped":
        act = [float(cost_by_scenario[n].get("active", 0) or 0) for n in names]
        idle = [float(cost_by_scenario[n].get("idle", 0) or 0) for n in names]
        w = 0.35
        ax.bar(x - w / 2, act, width=w, color="#2563eb", edgecolor="white", label="Aktif", zorder=2)
        ax.bar(x + w / 2, idle, width=w, color="#f59e0b", edgecolor="white", label="Idle", zorder=2)
        for i in range(len(names)):
            if act[i] > 0:
                ax.text(i - w / 2, act[i], f"{act[i]:,.0f}", ha="center", va="bottom", fontsize=6.5)
            if idle[i] > 0:
                ax.text(i + w / 2, idle[i], f"{idle[i]:,.0f}", ha="center", va="bottom", fontsize=6.5)
        ax.legend(loc="upper right", fontsize=8, framealpha=0.92)
        ax.set_ylabel("Biaya")
    elif mode == "idle":
        vals = [float(cost_by_scenario[n].get("idle", 0)) for n in names]
        colors = [fallback[i % len(fallback)] for i in range(len(names))]
        bars = ax.bar(x, vals, color=colors, edgecolor="white", width=0.65)
        for i, v in enumerate(vals):
            ax.text(i, v, f"{v:,.0f}", ha="center", va="bottom", fontsize=8)
        ax.set_ylabel("Biaya idle")
    else:
        vals = [float(cost_by_scenario[n].get("total", 0)) for n in names]
        colors = [fallback[i % len(fallback)] for i in range(len(names))]
        ax.bar(x, vals, color=colors, edgecolor="white", width=0.65)
        for i, v in enumerate(vals):
            ax.text(i, v, f"{v:,.0f}", ha="center", va="bottom", fontsize=8)
        ax.set_ylabel("Total biaya")

    ax.set_xticks(x)
    labels = [PRESET_DISPLAY.get(n, n) if "PRESET_DISPLAY" in dir() else n for n in names]
    try:
        labels = [PRESET_DISPLAY.get(n, n) for n in names]
    except Exception:
        labels = list(names)
    ax.set_xticklabels(labels, rotation=15, ha="right", fontsize=8)
    ax.set_xlabel("Skenario")
    ax.set_title(title or "Perbandingan biaya")
    ax.set_ylim(bottom=0)
    _apply_axes_style(ax)
    return ax


def plot_comparison_costs_by_trade(
    cost_rows_by_scenario: Dict[str, list],
    ax: Optional[Axes] = None,
    title: Optional[str] = None,
    *,
    which: str = "total",
) -> Axes:
    """
    Grouped bars: biaya per tim, satu grup per skenario.
    cost_rows_by_scenario[name] = list of TradeCostRow or dicts with cost_total/cost_idle.
    which: "total" | "idle" | "active"
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(10, 4.5))
    names = list(cost_rows_by_scenario.keys())
    if not names:
        return ax
    first = cost_rows_by_scenario[names[0]]
    n_trades = len(first)
    import numpy as np
    x = np.arange(n_trades)
    n_scen = len(names)
    width = min(0.8 / max(n_scen, 1), 0.18)
    offsets = (np.arange(n_scen) - (n_scen - 1) / 2.0) * width
    fallback = ["#2563eb", "#ea580c", "#16a34a", "#dc2626", "#7c3aed", "#0891b2"]
    key = {"total": "cost_total", "idle": "cost_idle", "active": "cost_active"}.get(which, "cost_total")

    for i, name in enumerate(names):
        rows = cost_rows_by_scenario[name]
        vals = []
        for row in rows:
            if hasattr(row, key):
                vals.append(float(getattr(row, key)))
            elif isinstance(row, dict):
                vals.append(float(row.get(key, row.get(which, 0))))
            else:
                vals.append(0.0)
        color = fallback[i % len(fallback)]
        try:
            label = PRESET_DISPLAY.get(name, name)
        except Exception:
            label = name
        ax.bar(x + offsets[i], vals, width=width * 0.92, color=color, edgecolor="white",
               linewidth=0.5, label=label)

    ax.set_xticks(x)
    ax.set_xticklabels([f"T{i+1}" for i in range(n_trades)])
    ylab = {"total": "Biaya total", "idle": "Biaya idle", "active": "Biaya aktif"}.get(which, "Biaya")
    ax.set_ylabel(ylab)
    ax.set_xlabel("Tim")
    ax.set_title(title or f"Biaya per tim — {which}")
    ax.legend(loc="upper right", fontsize=8, framealpha=0.92, ncol=min(n_scen, 3))
    ax.set_ylim(bottom=0)
    _apply_axes_style(ax)
    return ax


def plot_comparison_metrics(
    results: Dict[str, ParadeResult],
    axes: Optional[Sequence[Axes]] = None,
) -> List[Axes]:
    """
    Three metric bar charts: duration, total idle, peak WIP.

    If ``axes`` is None, creates a new 1×3 figure's axes (caller owns the fig).
    """
    names = list(results.keys())
    displays = [PRESET_DISPLAY.get(n, n) for n in names]
    colors = [PRESET_COLORS.get(n, "#7f7f7f") for n in names]

    durations = [results[n].duration for n in names]
    idles = [results[n].total_idle_capacity for n in names]
    peaks = [
        max((sum(h.buffers) for h in results[n].history), default=0) for n in names
    ]

    if axes is None:
        _, axes = plt.subplots(1, 3, figsize=(12, 3.8))
    axes = list(axes)

    specs = [
        (durations, "Duration (periods)", "Duration"),
        (idles, "Total idle capacity", "Idle Capacity"),
        (peaks, "Peak simultaneous WIP", "Peak WIP"),
    ]
    x = list(range(len(names)))
    for ax, (vals, ylabel, title) in zip(axes, specs):
        bars = ax.bar(x, vals, color=colors, edgecolor="white", width=0.7)
        ax.set_xticks(x)
        ax.set_xticklabels(displays, rotation=25, ha="right", fontsize=8)
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        for bar, v in zip(bars, vals):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                f"{v:g}" if isinstance(v, float) and not float(v).is_integer() else f"{int(v)}",
                ha="center",
                va="bottom",
                fontsize=8,
            )
        _apply_axes_style(ax)
        ax.set_ylim(bottom=0)

    return axes


def plot_comparison(
    results: Dict[str, ParadeResult],
    *,
    title: Optional[str] = None,
    show: bool = True,
    save_path: Optional[Union[str, Path]] = None,
    figsize: Tuple[float, float] = (13, 11),
    dpi: int = 140,
) -> Figure:
    """
    Full multi-scenario comparison figure:

      - LOB of last trade (all scenarios overlaid)
      - Total WIP over time
      - Duration / Idle / Peak WIP bar charts
    """
    fig = plt.figure(figsize=figsize, constrained_layout=True)
    gs = fig.add_gridspec(3, 3, height_ratios=[1.15, 1.05, 0.95])

    ax_lob = fig.add_subplot(gs[0, :])
    ax_buf = fig.add_subplot(gs[1, :])
    ax_d = fig.add_subplot(gs[2, 0])
    ax_i = fig.add_subplot(gs[2, 1])
    ax_w = fig.add_subplot(gs[2, 2])

    first = next(iter(results.values()))
    seed = first.config.seed
    total = first.config.total_units
    header = title or (
        f"Parade of Trades – Variability Comparison  |  "
        f"seed={seed}  |  total_units={total}"
    )
    fig.suptitle(header, fontsize=12, fontweight="semibold")

    plot_comparison_lob(results, ax=ax_lob)
    plot_comparison_buffers(results, ax=ax_buf)
    plot_comparison_metrics(results, axes=[ax_d, ax_i, ax_w])

    return _save_or_show(fig, show=show, save_path=save_path, dpi=dpi)


def plot_side_by_side_runs(
    results: Dict[str, ParadeResult],
    *,
    title: Optional[str] = None,
    show: bool = True,
    save_path: Optional[Union[str, Path]] = None,
    figsize: Optional[Tuple[float, float]] = None,
    dpi: int = 140,
) -> Figure:
    """
    Side-by-side LOB + buffer panels for each scenario (detailed view).

    Best with 2–5 scenarios.
    """
    names = list(results.keys())
    n = len(names)
    if n == 0:
        raise ValueError("results dict is empty")

    if figsize is None:
        figsize = (5.2 * n, 8.5)

    fig, axes = plt.subplots(
        2,
        n,
        figsize=figsize,
        squeeze=False,
        constrained_layout=True,
        sharey="row",
    )

    first = next(iter(results.values()))
    header = title or (
        f"Side-by-side runs  |  seed={first.config.seed}  |  "
        f"units={first.config.total_units}"
    )
    fig.suptitle(header, fontsize=12, fontweight="semibold")

    for col, name in enumerate(names):
        result = results[name]
        display = PRESET_DISPLAY.get(name, name)
        plot_line_of_balance(
            result,
            ax=axes[0, col],
            title=f"{display}\nT={result.duration}, thr={result.system_throughput:.2f}",
            show_ideal=True,
        )
        plot_buffer_profile(
            result,
            ax=axes[1, col],
            title="Buffer profile",
            show_max=True,
        )
        # Slim legends on multi-panel
        if n > 2:
            axes[0, col].legend(fontsize=6, loc="lower right")
            axes[1, col].legend(fontsize=6, loc="upper right")

    return _save_or_show(fig, show=show, save_path=save_path, dpi=dpi)


# ---------------------------------------------------------------------------
# Demo / CLI
# ---------------------------------------------------------------------------

def generate_demo_figures(
    output_dir: Union[str, Path] = "output",
    seed: int = 42,
    total_units: int = 100,
    show: bool = False,
) -> List[Path]:
    """
    Run classic scenarios and write a standard set of PNG figures.

    Returns list of written paths.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    written: List[Path] = []

    # 1) Individual runs for no_variability, medium, very_high
    for preset in ("no_variability", "medium", "very_high"):
        result = run_preset(
            preset, seed=seed, total_units=total_units, verbose=False
        )
        path = out / f"run_{preset}.png"
        plot_run(result, show=show, save_path=path)
        written.append(path)
        print(f"  wrote {path}")

    # 2) Full preset comparison
    results = compare_presets(
        presets=list(CAPACITY_PRESETS.keys()),
        seed=seed,
        total_units=total_units,
        verbose=False,
    )
    path = out / "comparison_all_presets.png"
    plot_comparison(results, show=show, save_path=path)
    written.append(path)
    print(f"  wrote {path}")

    # 3) Side-by-side detail (no / medium / very_high)
    subset = {
        k: results[k] for k in ("no_variability", "medium", "very_high")
    }
    path = out / "side_by_side_detail.png"
    plot_side_by_side_runs(subset, show=show, save_path=path)
    written.append(path)
    print(f"  wrote {path}")

    return written


# ---------------------------------------------------------------------------
# Replication / statistics plots (Phase 4)
# ---------------------------------------------------------------------------

def plot_duration_histogram(
    batches: Dict[str, "object"],
    ax: Optional[Axes] = None,
    title: Optional[str] = None,
    bins: Optional[int] = None,
) -> Axes:
    """Overlay duration histograms for named ReplicationBatch objects."""
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 4.5))

    colors = list(PRESET_COLORS.values()) + list(TRADE_COLORS)
    for i, (name, batch) in enumerate(batches.items()):
        durs = batch.durations  # type: ignore[attr-defined]
        color = PRESET_COLORS.get(name, colors[i % len(colors)])
        n_bins = bins or max(5, min(20, (max(durs) - min(durs) + 1) if durs else 10))
        ax.hist(
            durs,
            bins=n_bins,
            alpha=0.45,
            color=color,
            label=f"{name} (n={len(durs)})",
            edgecolor="white",
        )
    ax.set_xlabel("Project duration (periods)")
    ax.set_ylabel("Frequency")
    ax.set_title(title or "Duration distribution")
    ax.legend(fontsize=8, framealpha=0.92)
    _apply_axes_style(ax)
    return ax


def plot_time_on_site_boxplot(
    batches: Dict[str, "object"],
    ax: Optional[Axes] = None,
    title: Optional[str] = None,
) -> Axes:
    """
    Box plot of time-on-site by trade, grouped by scenario.

    Expects ReplicationBatch-like objects with ``time_on_site_by_trade()``
    and ``config.trades``.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(10, 5))

    # Collect: for each trade index, list of (scenario_label, values)
    first = next(iter(batches.values()))
    n_trades = first.config.n_trades  # type: ignore[attr-defined]
    trade_names = [t.name for t in first.config.trades]  # type: ignore[attr-defined]

    data = []
    positions = []
    colors_list = []
    tick_pos = []
    tick_labels = []
    scenario_names = list(batches.keys())
    n_sc = len(scenario_names)
    width = 0.8 / max(n_sc, 1)
    palette = list(PRESET_COLORS.values()) + list(TRADE_COLORS)

    for t_idx in range(n_trades):
        base = t_idx * (n_sc + 1)
        tick_pos.append(base + (n_sc - 1) / 2)
        tick_labels.append(f"T{t_idx + 1}")
        for s_idx, name in enumerate(scenario_names):
            batch = batches[name]
            series = batch.time_on_site_by_trade()[t_idx]  # type: ignore[attr-defined]
            data.append(series)
            positions.append(base + s_idx)
            colors_list.append(
                PRESET_COLORS.get(name, palette[s_idx % len(palette)])
            )

    bp = ax.boxplot(
        data,
        positions=positions,
        widths=width * 0.9,
        patch_artist=True,
        showfliers=True,
        flierprops=dict(marker="o", markersize=3, alpha=0.5),
    )
    for patch, color in zip(bp["boxes"], colors_list):
        patch.set_facecolor(color)
        patch.set_alpha(0.65)

    ax.set_xticks(tick_pos)
    ax.set_xticklabels(tick_labels)
    ax.set_ylabel("Time on site (periods)")
    ax.set_title(title or "Time on site by trade")
    # Legend proxies
    from matplotlib.patches import Patch
    handles = []
    for s_idx, name in enumerate(scenario_names):
        c = PRESET_COLORS.get(name, palette[s_idx % len(palette)])
        handles.append(Patch(facecolor=c, alpha=0.65, label=name))
    ax.legend(handles=handles, fontsize=8, framealpha=0.92, loc="upper left")
    _apply_axes_style(ax)
    return ax


def plot_replication_summary(
    batches: Dict[str, "object"],
    *,
    title: Optional[str] = None,
    show: bool = True,
    save_path: Optional[Union[str, Path]] = None,
    figsize: Tuple[float, float] = (12, 9),
    dpi: int = 140,
) -> Figure:
    """Duration histogram + time-on-site boxplot + metric bar means."""
    fig = plt.figure(figsize=figsize, constrained_layout=True)
    gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 1.1])
    ax_hist = fig.add_subplot(gs[0, 0])
    ax_bar = fig.add_subplot(gs[0, 1])
    ax_box = fig.add_subplot(gs[1, :])

    fig.suptitle(
        title or "Replication statistics",
        fontsize=12,
        fontweight="semibold",
    )
    plot_duration_histogram(batches, ax=ax_hist)
    plot_time_on_site_boxplot(batches, ax=ax_box)

    # Mean duration / idle bars
    names = list(batches.keys())
    means_d = [batches[n].stats()["duration"].mean for n in names]  # type: ignore
    means_i = [batches[n].stats()["total_idle"].mean for n in names]  # type: ignore
    x = list(range(len(names)))
    w = 0.35
    colors = [
        PRESET_COLORS.get(n, TRADE_COLORS[i % len(TRADE_COLORS)])
        for i, n in enumerate(names)
    ]
    ax_bar.bar([xi - w / 2 for xi in x], means_d, width=w, color=colors, label="Duration μ")
    ax_bar.bar(
        [xi + w / 2 for xi in x],
        means_i,
        width=w,
        color=colors,
        alpha=0.45,
        label="Idle μ",
    )
    ax_bar.set_xticks(x)
    ax_bar.set_xticklabels(names, rotation=20, ha="right", fontsize=8)
    ax_bar.set_ylabel("Mean value")
    ax_bar.set_title("Mean duration & idle")
    ax_bar.legend(fontsize=8)
    _apply_axes_style(ax_bar)

    return _save_or_show(fig, show=show, save_path=save_path, dpi=dpi)


def _demo() -> None:
    print("Generating Parade of Trades visualization demos → ./output/")
    paths = generate_demo_figures(output_dir="output", seed=42, show=False)
    print(f"Done. {len(paths)} figures written.")


if __name__ == "__main__":
    _demo()

def plot_littles_law_wip(
    result: ParadeResult,
    ax: Optional[Axes] = None,
    title: Optional[str] = None,
) -> Axes:
    """Pipeline WIP and interface buffer WIP over time (Little's Law context)."""
    if ax is None:
        _, ax = plt.subplots(figsize=(9, 4.2))
    from parade_of_trades_analysis import littles_law_series, littles_law_metrics

    s = littles_law_series(result)
    m = littles_law_metrics(result)
    periods = s["period"]
    ax.plot(periods, s["pipeline_wip"], color="#1a365d", linewidth=2.0, label="WIP pipeline (T1−T5)")
    ax.plot(periods, s["buffer_wip"], color="#dd6b20", linewidth=1.8, label="WIP buffer (jumlah antrian)")
    ax.axhline(m.avg_pipeline_wip, color="#1a365d", linestyle="--", linewidth=1.0, alpha=0.7,
               label=f"Rata-rata pipeline={m.avg_pipeline_wip:.2f}")
    ax.axhline(m.avg_buffer_wip, color="#dd6b20", linestyle=":", linewidth=1.0, alpha=0.7,
               label=f"Rata-rata buffer={m.avg_buffer_wip:.2f}")
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    ax.set_xlabel("Periode")
    ax.set_ylabel("WIP (zona)")
    ax.set_title(title or "Little's Law — jejak WIP")
    ax.legend(loc="upper right", fontsize=8, framealpha=0.92)
    _apply_axes_style(ax)
    return ax

def plot_kingman_stations(
    result: ParadeResult,
    ax: Optional[Axes] = None,
    title: Optional[str] = None,
) -> Axes:
    """Grouped bars: CT Kingman vs CT observed per trade."""
    if ax is None:
        _, ax = plt.subplots(figsize=(9, 4.2))
    from parade_of_trades_analysis import kingman_metrics
    import numpy as np

    k = kingman_metrics(result)
    names = [f"T{s.trade_index + 1}" for s in k.stations]
    ct_k = [s.ct_kingman if __import__("math").isfinite(s.ct_kingman) else 0 for s in k.stations]
    ct_o = [s.ct_observed for s in k.stations]
    x = np.arange(len(names))
    w = 0.36
    ax.bar(x - w / 2, ct_k, width=w, color="#2b6cb0", edgecolor="white", label="CT Kingman")
    ax.bar(x + w / 2, ct_o, width=w, color="#dd6b20", edgecolor="white", label="CT amati")
    ax.set_xticks(x)
    ax.set_xticklabels(names)
    ax.set_ylabel("Cycle time (periode / zona)")
    ax.set_xlabel("Tim")
    ax.set_title(title or "Kingman (VUT) vs CT teramati per stasiun")
    ax.set_ylim(bottom=0)
    ax.legend(loc="upper right", fontsize=8, framealpha=0.92)
    _apply_axes_style(ax)
    return ax

def plot_kingman_vut_curve(
    result: ParadeResult,
    ax: Optional[Axes] = None,
    title: Optional[str] = None,
) -> Axes:
    """
    Classic Kingman chart: cycle time vs utilization (system / combined).

    Curves for several variability factors V = (c_a²+c_e²)/2; process time
    t_e is the mean station process time (average across trades).
    Operating point = combined utilization (mean of trade utils) on the
    curve that matches this run's average V.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(9, 4.5))
    import numpy as np
    from parade_of_trades_analysis import kingman_metrics, kingman_ct

    k = kingman_metrics(result)
    # Combined utilization = average u across trades (gabungan)
    us = [s.utilization for s in k.stations]
    u_comb = float(sum(us) / len(us)) if us else 0.0
    # Combined t_e and V: average station t_e; V from mean c_a,c_e
    t_e = float(sum(s.t_e for s in k.stations) / len(k.stations))
    c_a_m = float(sum(s.c_a for s in k.stations) / len(k.stations))
    c_e_m = float(sum(s.c_e for s in k.stations) / len(k.stations))
    v_run = 0.5 * (c_a_m ** 2 + c_e_m ** 2)

    u_grid = np.linspace(0.01, 0.97, 200)
    # Family of V curves for teaching
    v_curves = [
        (0.0, "V=0 (tanpa var)", "#94a3b8", "--"),
        (0.125, "V=0,125 (var rendah)", "#38bdf8", "-"),
        (0.25, "V=0,25 (var sedang)", "#f59e0b", "-"),
        (0.5, "V=0,5 (var tinggi)", "#ef4444", "-"),
        (1.0, "V=1,0 (sangat tinggi)", "#7c3aed", "-"),
    ]
    for v, lab, color, ls in v_curves:
        ct = []
        for u in u_grid:
            # wait = V * u/(1-u) * t_e ; CT = wait + t_e
            # equivalent kingman with ca^2+ce^2 = 2V
            w = v * (u / (1.0 - u)) * t_e
            ct.append(w + t_e)
        ax.plot(u_grid, ct, color=color, linestyle=ls, linewidth=1.7, label=lab)

    # Operating point on run's V
    u_pt = min(max(u_comb, 0.0), 0.97)
    w_pt = v_run * (u_pt / (1.0 - u_pt)) * t_e if u_pt < 1 else float("inf")
    ct_pt = w_pt + t_e
    ax.scatter(
        [u_pt], [ct_pt],
        s=90, zorder=5, color="#0f172a", edgecolors="white", linewidths=1.2,
        label=f"Titik operasi (u̅={u_comb:.2f}, V≈{v_run:.2f})",
    )
    ax.axvline(u_pt, color="#0f172a", linestyle=":", linewidth=1.0, alpha=0.5)

    ax.set_xlim(0, 1.0)
    ax.set_ylim(bottom=0)
    # sensible top
    ymax = max(ct_pt * 1.4, t_e * 8, 2.0)
    # avoid insane scale
    sample_hi = v_curves[-1][0] * (0.9 / 0.1) * t_e + t_e
    ax.set_ylim(0, min(max(ymax, t_e * 3), sample_hi * 0.35 + t_e * 2))
    ax.set_xlabel("Utilisasi gabungan  u̅  (rata-rata semua tim)")
    ax.set_ylabel("Cycle time Kingman  (periode / zona)")
    ax.set_title(title or "Kingman: CT vs utilisasi (kurva VUT)")
    ax.legend(loc="upper left", fontsize=7.5, framealpha=0.92)
    _apply_axes_style(ax)
    return ax

def plot_wip_th_ct(
    result: ParadeResult,
    ax: Optional[Axes] = None,
    title: Optional[str] = None,
    conwip_level: Optional[float] = None,
) -> Axes:
    """
    Dual-axis operations chart with WIP landmarks:

      X  = WIP
      YL = Throughput (TH)
      YR = Cycle time (CT)

    - Best-case envelope (no var, bottleneck)
    - Actual curve (with variability)
    - **W_min (W0)**: WIP minimal/kritis — WIP terkecil (kasus terbaik) untuk
      mencapai TH_max
    - **W_opt**: WIP optimal (ajaran) — WIP di kurva aktual di mana TH ≈ 95%
      TH_max (butuh ≥ W_min jika ada variability)
    - **CONWIP**: batas WIP konstan (Constant WIP); default = W_opt
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(9.5, 5.2))
    from parade_of_trades_analysis import littles_operations_curve

    d = littles_operations_curve(result)
    color_th = "#2563eb"
    color_ct = "#dc2626"
    color_bc_th = "#93c5fd"
    color_bc_ct = "#fca5a5"

    ax2 = ax.twinx()

    bc_w = d.get("bc_wip") or []
    bc_th = d.get("bc_th") or []
    bc_ct = d.get("bc_ct") or []
    th_max = float(d.get("th_max") or 1.0)
    t0 = float(d.get("t0") or 1.0)
    w_min = float(d.get("w_min") or d.get("w0") or 1.0)
    w_opt = float(d.get("w_opt") or w_min)
    conwip = float(conwip_level) if conwip_level is not None else float(d.get("conwip") or w_opt)

    line_bc_th = line_bc_ct = None
    if bc_w and bc_th:
        line_bc_th, = ax.plot(
            bc_w, bc_th, color=color_bc_th, linewidth=2.2,
            label=f"TH batas (no var, TH_max={th_max:.2f})",
        )
        ax.fill_between(bc_w, bc_th, alpha=0.10, color=color_bc_th)
    if bc_w and bc_ct:
        line_bc_ct, = ax2.plot(
            bc_w, bc_ct, color=color_bc_ct, linewidth=2.2,
            label=f"CT batas (T0={t0:.2f})",
        )

    ax.axhline(th_max, color=color_bc_th, linestyle=":", linewidth=1.0, alpha=0.85)
    ax2.axhline(t0, color=color_bc_ct, linestyle=":", linewidth=1.0, alpha=0.85)

    # Actual curves
    wip, th, ct = d["wip"], d["th"], d["ct"]
    line_th = line_ct = None
    if wip:
        order = sorted(range(len(wip)), key=lambda i: wip[i])
        wip_s = [wip[i] for i in order]
        th_s = [th[i] for i in order]
        ct_s = [ct[i] for i in order]
        line_th, = ax.plot(wip_s, th_s, color=color_th, linewidth=2.2, label="TH aktual (var)")
        line_ct, = ax2.plot(wip_s, ct_s, color=color_ct, linewidth=2.2, linestyle="--", label="CT aktual (var)")

    # --- Landmarks: W_min, W_opt, CONWIP ---
    op_w, op_th, op_ct = float(d["op_wip"]), float(d["op_th"]), float(d["op_ct"])

    # Axis: curves end ~ max(W_opt, CONWIP, operasi) + 5
    x_right = max(
        bc_w[-1] if bc_w else 0.0,
        max(wip) if wip else 0.0,
        w_opt + 5.0,
        float(conwip) + 5.0,
        op_w + 5.0,
        w_min + 5.0,
        8.0,
    )
    ymax_th = max(th_max * 1.15, op_th * 1.25, max(th) if th else 0.0, 0.5) * 1.05

    ax.axvline(w_min, color="#15803d", linestyle="--", linewidth=1.6, alpha=0.9)
    ax.axvline(w_opt, color="#c2410c", linestyle="--", linewidth=1.6, alpha=0.9)
    ax.axvline(conwip, color="#7c3aed", linestyle="-", linewidth=2.0, alpha=0.85)
    ax.axvspan(min(w_min, conwip), max(w_min, conwip), color="#7c3aed", alpha=0.06, zorder=0)

    ax.text(w_min, ymax_th * 0.92, f" W_min={w_min:.1f}", color="#15803d", fontsize=8, va="top")
    ax.text(w_opt, ymax_th * 0.80, f" W_opt={w_opt:.1f}", color="#c2410c", fontsize=8, va="top")
    ax.text(conwip, ymax_th * 0.68, f" CONWIP={conwip:.1f}", color="#7c3aed", fontsize=8, va="top")

    # Operating point
    ax.scatter([op_w], [op_th], s=100, color=color_th, zorder=6, edgecolors="white", linewidths=1.2)
    ax2.scatter([op_w], [op_ct], s=100, color=color_ct, zorder=6, edgecolors="white",
                linewidths=1.2, marker="s")

    ax.set_xlabel("WIP (zona)")
    ax.set_ylabel("Throughput TH (zona / periode)", color=color_th)
    ax.tick_params(axis="y", labelcolor=color_th)
    ax2.set_ylabel("Cycle time CT (periode)", color=color_ct)
    ax2.tick_params(axis="y", labelcolor=color_ct)
    ax.set_xlim(0, x_right)
    ax.set_ylim(0, ymax_th)
    # CT scale: show extended branch (batas + aktual) without crushing low end too much
    ct_peak = 0.0
    if bc_ct:
        ct_peak = max(ct_peak, max(bc_ct))
    if ct:
        ct_peak = max(ct_peak, max(ct))
    ymax_ct = max(t0 * 2.0, op_ct * 1.4, ct_peak * 1.05, 1.0)
    ax2.set_ylim(0, ymax_ct)

    ax.set_title(
        title
        or (
            f"WIP–TH–CT · W_min={w_min:.1f} · W_opt={w_opt:.1f} · CONWIP={conwip:.1f} · "
            f"operasi WIP={op_w:.2f}"
        )
    )

    lines = [x for x in (line_bc_th, line_th, line_bc_ct, line_ct) if x is not None]
    labels = [l.get_label() for l in lines]
    # landmark proxies for legend
    from matplotlib.lines import Line2D
    extra = [
        Line2D([0], [0], color="#15803d", linestyle="--", label="W_min (WIP minimal/kritis)"),
        Line2D([0], [0], color="#c2410c", linestyle="--", label="W_opt (WIP optimal)"),
        Line2D([0], [0], color="#7c3aed", linestyle="-", linewidth=2, label="CONWIP (batas WIP)"),
    ]
    ax.legend(lines + extra, labels + [e.get_label() for e in extra],
              loc="center right", fontsize=7.2, framealpha=0.92)

    _apply_axes_style(ax)
    ax2.grid(False)
    return ax



def plot_inventory_fill_rate(
    result: ParadeResult,
    ax: Optional[Axes] = None,
    title: Optional[str] = None,
) -> Axes:
    """
    Fill rate (X) vs inventory (Y) — service–inventory tradeoff.

    Curve: theoretical base-stock / normal-loss (inventory rises as FR → 100%).
    Point: system operating point; diamonds = per-buffer interfaces.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(9, 4.6))
    from parade_of_trades_analysis import inventory_fill_rate_curve

    d = inventory_fill_rate_curve(result)
    inv, fr = d["inventory"], d["fill_rate"]
    # sort by fill rate for a clean curve left→right
    order = sorted(range(len(fr)), key=lambda i: fr[i])
    fr_s = [100 * fr[i] for i in order]
    inv_s = [inv[i] for i in order]

    ax.plot(fr_s, inv_s, color="#0f766e", linewidth=2.2,
            label="Kurva teoritis (base-stock)")
    ax.scatter(
        [100 * d["op_fill_rate"]], [d["op_inventory"]],
        s=100, zorder=5, color="#0f172a", edgecolors="white", linewidths=1.2,
        label=f"Sistem (FR={100*d['op_fill_rate']:.1f}%, I̅={d['op_inventory']:.2f})",
    )
    colors = ["#2563eb", "#ea580c", "#16a34a", "#dc2626"]
    for i, row in enumerate(d.get("interfaces") or []):
        ax.scatter(
            [100 * row["fill_rate"]], [row["avg_inventory"]],
            s=70, zorder=4, color=colors[i % len(colors)],
            edgecolors="white", marker="D",
            label=f"{row['buffer']} I̅={row['avg_inventory']:.2f}",
        )

    ax.set_xlabel("Fill rate (%)")
    ax.set_ylabel("Inventory / WIP buffer (zona, rata-rata)")
    ax.set_xlim(0, 105)
    ax.set_ylim(bottom=0)
    ax.axvline(100, color="0.75", linestyle="--", linewidth=0.9)
    ax.set_title(title or "Fill rate vs inventory (tradeoff service–persediaan)")
    ax.legend(loc="upper left", fontsize=7.5, framealpha=0.92)
    _apply_axes_style(ax)
    return ax

def plot_takt_plan(
    plan,
    ax: Optional[Axes] = None,
    title: Optional[str] = None,
    result: Optional[ParadeResult] = None,
) -> Axes:
    """
    Takt plan as LOB-style diagonals (planned) + optional actual cumulative.

    X = periode, Y = zona kumulatif (0..N). Each trade = one planned staircase.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(10, 5.2))
    colors = [_trade_color(i) for i in range(plan.n_trades)]
    # Build planned cumulative: at end of each period how many zones done
    for i in range(plan.n_trades):
        cells = [c for c in plan.cells if c.trade_index == i]
        cells = sorted(cells, key=lambda c: c.zone)
        xs = [0]
        ys = [0]
        for c in cells:
            # finish of zone c.zone at period_end → cum = c.zone
            xs.append(c.period_end)
            ys.append(c.zone)
        ax.plot(xs, ys, color=colors[i], linewidth=2.0, linestyle="--",
                label=f"Rencana T{i + 1}", alpha=0.85)
        ax.scatter(xs[1:], ys[1:], color=colors[i], s=18, zorder=3)

    if result is not None and result.history:
        for i in range(min(result.config.n_trades, plan.n_trades)):
            xs = [0] + [rec.period for rec in result.history]
            ys = [0] + [rec.cumulative[i] for rec in result.history]
            ax.plot(xs, ys, color=colors[i], linewidth=2.2, label=f"Aktual T{i + 1}")

    ax.set_xlabel("Periode")
    ax.set_ylabel("Zona kumulatif")
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0, top=plan.n_zones * 1.05)
    ax.set_title(
        title
        or (
            f"Takt plan · batch={plan.batch_size} · rate={plan.rate:g} · "
            f"T0/zona={plan.takt_time:g} · durasi rencana={plan.duration}"
        )
    )
    ax.legend(loc="upper left", fontsize=7.5, framealpha=0.92, ncol=2)
    _apply_axes_style(ax)
    return ax


def plot_takt_wagon_chart(
    plan,
    ax: Optional[Axes] = None,
    title: Optional[str] = None,
    max_zones: Optional[int] = None,
    *,
    compact: bool = True,
) -> Axes:
    """
    Takt train / wagon chart (period 0-based).

    Bars use continuous time: width = period_end - period_start.
    Axis ticks every 1 unit for readability.
    """
    n_all = int(plan.n_zones)
    n_show = n_all if max_zones is None else min(n_all, int(max_zones))

    tmax = 0.0
    for c in plan.cells:
        if 1 <= c.zone <= n_show:
            tmax = max(tmax, float(c.period_end))
    tmax = max(tmax, float(getattr(plan, "duration", 0) or 0), 1e-6)

    if ax is None:
        if compact:
            w = max(5.5, min(9.0, 0.14 * tmax + 2.5))
            h = max(3.2, min(8.5, 0.12 * n_show + 1.6))
        else:
            w, h = 10.0, max(4.0, min(12.0, 0.2 * n_show + 2))
        _, ax = plt.subplots(figsize=(w, h))

    colors = [_trade_color(i) for i in range(plan.n_trades)]
    # Label T1..Tn on each wagon; no separate legend
    show_text = n_show <= 16 and tmax <= 30
    fs = 5.5 if compact else 7

    for c in plan.cells:
        if c.zone < 1 or c.zone > n_show:
            continue
        left = float(c.period_start)
        width = max(float(c.period_end) - left, 1e-6)
        lab = f"T{c.trade_index + 1}"
        ax.barh(
            y=float(c.zone),
            width=width,
            left=left,
            height=0.92,
            color=colors[c.trade_index % len(colors)],
            edgecolor="white",
            linewidth=0.35,
            align="center",
            zorder=2,
        )
        if show_text:
            ax.text(
                left + width / 2.0, float(c.zone), lab,
                ha="center", va="center", fontsize=fs,
                color="white", fontweight="bold", zorder=3,
            )

    ax.set_xlim(0, tmax)
    ax.set_ylim(n_show + 0.5, 0.5)
    ax.set_xlabel("Periode")
    ax.set_ylabel("Zona")
    ax.xaxis.set_major_locator(mticker.MultipleLocator(1))
    ax.yaxis.set_major_locator(mticker.MultipleLocator(1))
    ax.xaxis.set_major_formatter(mticker.FormatStrFormatter("%d"))
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%d"))
    ax.grid(True, which="major", linestyle="-", alpha=0.22, linewidth=0.45, zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    for lab in ax.get_xticklabels():
        lab.set_fontsize(5 if tmax > 50 else (6 if tmax > 30 else 7))
    for lab in ax.get_yticklabels():
        lab.set_fontsize(5 if n_show > 50 else (6 if n_show > 30 else 7))
    ax.set_title(
        title or f"Takt plan (wagon) · {n_show} zona · {tmax:.1f} p",
        fontsize=10 if compact else 11,
    )
    ax.set_axisbelow(True)
    return ax



def plot_tommelein_scenario_lobs(
    results: Dict[str, ParadeResult],
    title: Optional[str] = None,
) -> "plt.Figure":
    """
    One LOB panel per Tommelein scenario: all trades + planned takt line.

    Planned line: constant rate = takt_rate if set, else trade mean capacity.
    """
    n = len(results)
    fig, axes = plt.subplots(1, n, figsize=(4.2 * n, 4.4), sharey=True)
    if n == 1:
        axes = [axes]
    colors = [_trade_color(i) for i in range(8)]
    for ax, (name, result) in zip(axes, results.items()):
        cum = result.cumulative_series()
        total = result.config.total_units
        for i, series in enumerate(cum):
            series = list(series)
            periods = list(range(len(series)))
            ax.plot(
                periods, series,
                color=colors[i % len(colors)],
                linewidth=1.8,
                label=f"T{i + 1}",
            )
        # Planned / takt rate line (ideal constant pace from origin for last trade lag)
        tr = result.config.trades[0]
        if result.config.takt_enabled and result.config.takt_rate:
            rate = float(result.config.takt_rate)
            plan_label = f"Rencana takt={result.config.takt_rate}"
        else:
            rate = float(tr.mean) if tr.mean else (float(tr.low) + float(tr.high)) / 2.0
            plan_label = f"Rencana mean={rate:g}"
        # Ideal last-trade with next-period handoff: start after (n-1) lags
        n_tr = result.config.n_trades
        lag = 0 if result.config.same_period_handoff else (n_tr - 1)
        if rate > 0:
            t_end = lag + total / rate
            ax.plot(
                [lag, t_end], [0, total],
                color="0.35", linestyle="--", linewidth=1.4,
                label=plan_label,
            )
        ax.axhline(total, color="0.75", linestyle=":", linewidth=0.9)
        ax.set_xlim(left=0)
        ax.set_ylim(0, total * 1.08)
        ax.set_xlabel("Periode")
        ax.set_title(name, fontsize=10)
        ax.legend(loc="lower right", fontsize=7, framealpha=0.9, ncol=2)
        _apply_axes_style(ax)
    axes[0].set_ylabel("Zona kumulatif")
    fig.suptitle(title or "Tommelein (2020) — LOB per skenario (semua tim)", fontsize=11, y=1.02)
    fig.tight_layout()
    return fig


def plot_tommelein_last_trade_lob(
    results: Dict[str, ParadeResult],
    ax: Optional[Axes] = None,
    title: Optional[str] = None,
) -> Axes:
    """Overlay last-trade LOB for Tommelein scenarios with per-scenario plan lines."""
    if ax is None:
        _, ax = plt.subplots(figsize=(9.5, 4.8))
    fallback = ["#2563eb", "#ea580c", "#16a34a", "#dc2626", "#7c3aed"]
    total = next(iter(results.values())).config.total_units
    max_p = 1
    for idx, (name, result) in enumerate(results.items()):
        color = fallback[idx % len(fallback)]
        series = list(result.cumulative_series()[-1])
        periods = list(range(len(series)))
        max_p = max(max_p, periods[-1] if periods else 1)
        ax.plot(
            periods, series, color=color, linewidth=2.2,
            label=f"{name} (T={result.duration})",
        )
        ax.plot(0, 0, marker="o", color=color, markersize=5, zorder=5)
    ax.axhline(total, color="0.7", linestyle="--", linewidth=1.0)
    ax.set_xlim(0, max_p * 1.05)
    ax.set_ylim(0, total * 1.08)
    ax.set_xlabel("Periode (mulai 0)")
    ax.set_ylabel("Zona kumulatif tim terakhir")
    ax.set_title(title or "Tommelein (2020) — LOB tim terakhir")
    ax.legend(loc="lower right", fontsize=8, framealpha=0.92)
    _apply_axes_style(ax)
    return ax


def plot_single_scenario_lob(
    result: ParadeResult,
    ax: Optional[Axes] = None,
    title: Optional[str] = None,
) -> Axes:
    """Full LOB (all trades) for one scenario, origin (0,0)."""
    if ax is None:
        _, ax = plt.subplots(figsize=(8.5, 4.6))
    cum = result.cumulative_series()
    total = result.config.total_units
    colors = [_trade_color(i) for i in range(result.config.n_trades)]
    for i, series in enumerate(cum):
        series = list(series)
        periods = list(range(len(series)))
        ax.plot(periods, series, color=colors[i], linewidth=2.0, label=f"T{i + 1}")
    # planned rate line for last trade
    tr = result.config.trades[0]
    if result.config.takt_enabled and result.config.takt_rate:
        rate = float(result.config.takt_rate)
        plan_label = f"Rencana takt={result.config.takt_rate}"
    else:
        rate = float(tr.mean) if tr.mean else (float(tr.low) + float(tr.high)) / 2.0
        plan_label = f"Rencana mean={rate:g}"
    n_tr = result.config.n_trades
    lag = 0 if result.config.same_period_handoff else (n_tr - 1)
    if rate > 0:
        t_end = lag + total / rate
        ax.plot([lag, t_end], [0, total], color="0.35", linestyle="--",
                linewidth=1.4, label=plan_label)
    ax.axhline(total, color="0.75", linestyle=":", linewidth=0.9)
    ax.set_xlim(left=0)
    ax.set_ylim(0, total * 1.08)
    ax.set_xlabel("Periode")
    ax.set_ylabel("Zona kumulatif")
    ax.set_title(title or "Line of Balance")
    ax.legend(loc="lower right", fontsize=8, framealpha=0.92, ncol=2)
    _apply_axes_style(ax)
    return ax


# Iris-style time-inventory buffer scatter (duration vs time-on-site / inventory-time)
_DIE_STYLE = {
    "no_variability": {"color": "#2563eb", "marker": "s", "label": "Waktu di lapangan · tanpa var"},
    "low": {"color": "#06b6d4", "marker": "o", "label": "Waktu di lapangan · sedang"},
    "medium": {"color": "#7c3aed", "marker": "D", "label": "Waktu di lapangan · tinggi"},
    "5-5": {"color": "#2563eb", "marker": "s", "label": "Waktu di lapangan · tanpa var"},
    "4-6": {"color": "#06b6d4", "marker": "o", "label": "Waktu di lapangan · sedang"},
    "3-7": {"color": "#7c3aed", "marker": "D", "label": "Waktu di lapangan · tinggi"},
}
_DIE_INV_STYLE = {
    "no_variability": {"color": "#f59e0b", "marker": "s", "label": "Inventory time · tanpa var"},
    "low": {"color": "#ea580c", "marker": "o", "label": "Inventory time · sedang"},
    "medium": {"color": "#dc2626", "marker": "D", "label": "Inventory time · tinggi"},
    "5-5": {"color": "#f59e0b", "marker": "s", "label": "Inventory time · tanpa var"},
    "4-6": {"color": "#ea580c", "marker": "o", "label": "Inventory time · sedang"},
    "3-7": {"color": "#dc2626", "marker": "D", "label": "Inventory time · tinggi"},
}


def _bin_means(xs: Sequence[float], ys: Sequence[float]) -> Tuple[List[float], List[float]]:
    buckets: Dict[float, List[float]] = {}
    for x, y in zip(xs, ys):
        buckets.setdefault(float(x), []).append(float(y))
    mx = sorted(buckets)
    my = [sum(buckets[x]) / len(buckets[x]) for x in mx]
    return mx, my



def _poly_equation(coef, yname: str, xname: str = "D") -> str:
    c = [float(v) for v in coef]
    n = len(c) - 1
    parts: List[str] = []
    for i, v in enumerate(c):
        p = n - i
        if abs(v) < 5e-5:
            continue
        av = abs(v)
        if p == 0:
            term = f"{av:.3f}"
        elif p == 1:
            term = f"{av:.4f}{xname}" if abs(av - 1.0) > 0.02 else xname
        elif p == 2:
            term = f"{av:.5f}{xname}²"
        else:
            term = f"{av:.5f}{xname}^{p}"
        if not parts:
            parts.append(f"−{term}" if v < 0 else term)
        else:
            parts.append((" − " if v < 0 else " + ") + term)
    if not parts:
        parts = ["0"]
    return f"{yname} = {''.join(parts)}"


def _r2_aic(y, yhat, k: int):
    import numpy as np
    y = np.asarray(y, dtype=float)
    yhat = np.asarray(yhat, dtype=float)
    n = max(1, len(y))
    ss_res = float(np.sum((y - yhat) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 if ss_tot < 1e-12 else 1.0 - ss_res / ss_tot
    aic = n * float(np.log(max(ss_res, 1e-18) / n)) + 2.0 * k
    return r2, aic



TOS_FLOOR = 100.0


def predict_buffer_curve(fit: dict, x):
    import numpy as np
    x = np.asarray(x, dtype=float)
    kind = fit.get("kind", "poly")
    c = fit.get("coef") or []
    floor = float(fit.get("tos_floor") or TOS_FLOOR)
    if kind == "poly":
        return np.polyval(c, x)
    if kind == "const":
        return np.full_like(x, floor if not c else float(c[0]), dtype=float)
    if kind == "floor_inv":
        return floor + float(c[0]) / np.maximum(x, 1e-9)
    if kind == "floor_exp":
        return floor + float(c[0]) * np.exp(-float(c[1]) * x)
    if kind == "hyp_tos":
        return float(c[0]) + float(c[1]) / np.maximum(x - floor, 1e-3)
    if kind == "log":
        return c[0] + c[1] * np.log(np.maximum(x, 1e-9))
    if kind == "power":
        return c[0] * np.power(np.maximum(x, 1e-9), c[1])
    if kind == "inv":
        return c[0] + c[1] / np.maximum(x, 1e-9)
    if kind == "exp":
        return c[0] + c[1] * np.exp(c[2] * x)
    return np.full_like(x, float(np.mean(fit.get("y_mean") or [0.0])))


def _pack_fit(name, kind, coef, y, yhat, mx, my, eq, extra=None):
    r2, aic = _r2_aic(y, yhat, max(1, len(coef)))
    d = {
        "model": name,
        "kind": kind,
        "coef": [float(v) for v in coef],
        "eq": eq,
        "r2": r2,
        "aic": aic,
        "k": len(coef),
        "degree": max(1, len(coef) - 1),
        "x_mean": list(mx),
        "y_mean": list(my),
    }
    if extra:
        d.update(extra)
    return d


def _fit_tos_theory(mx, my, tos_floor: float) -> dict:
    """TOS = lantai + surplus. Surplus ~ B/D or A e^{-λD}."""
    import numpy as np
    x = np.asarray(mx, dtype=float)
    y = np.asarray(my, dtype=float)
    floor = float(tos_floor)
    excess = y - floor
    extra = {"tos_floor": floor}
    cands = []

    invx = 1.0 / np.maximum(x, 1e-9)
    denom = float(np.dot(invx, invx)) or 1.0
    B = max(0.0, float(np.dot(invx, excess) / denom))
    yhat = floor + B * invx
    cands.append(
        _pack_fit(
            f"Invers ke {floor:g}",
            "floor_inv",
            [B],
            y, yhat, mx, my,
            f"TOS = {floor:g} + {B:.3f}/D",
            extra=extra,
        )
    )

    best_sse, best = None, None
    for lam in np.linspace(0.015, 0.55, 90):
        z = np.exp(-lam * x)
        zz = float(np.dot(z, z)) or 1.0
        A = max(0.0, float(np.dot(z, excess) / zz))
        yhat = floor + A * z
        sse = float(np.sum((y - yhat) ** 2))
        if best_sse is None or sse < best_sse:
            best_sse, best = sse, (A, lam, yhat)
    if best is not None:
        A, lam, yhat = best
        cands.append(
            _pack_fit(
                f"Exp ke {floor:g}",
                "floor_exp",
                [A, lam],
                y, yhat, mx, my,
                f"TOS = {floor:g} + {A:.3f}·e^(-{lam:.4f} D)",
                extra=extra,
            )
        )
    cands.sort(key=lambda d: (-d["r2"], d["aic"]))
    return cands[0]


def _fit_inv_linear(mx, my) -> dict:
    """Inventory ~ linier terhadap durasi (tunda × mean kapasitas)."""
    import numpy as np
    x = np.asarray(mx, dtype=float)
    y = np.asarray(my, dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    if slope < 0:
        slope = 0.0
        intercept = float(np.mean(y))
    coef = [slope, intercept]
    yhat = np.polyval(coef, x)
    return _pack_fit(
        "Linier (teori tunda)",
        "poly",
        coef,
        y, yhat, mx, my,
        _poly_equation(coef, "INV", "D"),
    )


def _infer_tos_floor(rows: Sequence[dict]) -> float:
    for r in rows:
        if r.get("tos_floor"):
            return float(r["tos_floor"])
    stables = [
        float(r["time_on_site"])
        for r in rows
        if str(r.get("die")) in ("no_variability", "5-5", "tanpa")
    ]
    if stables:
        return float(min(stables))
    return float(TOS_FLOOR)


def fit_buffer_trends(rows: Sequence[dict]) -> List[dict]:
    """Kurva teori: tanpa var = lantai proses; TOS ≥ lantai; INV linier vs D."""
    import numpy as np
    by_die: Dict[str, List[dict]] = {}
    for row in rows:
        by_die.setdefault(str(row["die"]), []).append(row)
    floor = _infer_tos_floor(rows)

    out: List[dict] = []
    for die, group in by_die.items():
        xs = [float(r["duration"]) for r in group]
        tos = [float(r["time_on_site"]) for r in group]
        inv = [float(r["inventory_time"]) for r in group]
        mx_t, my_t = _bin_means(xs, tos)
        mx_i, my_i = _bin_means(xs, inv)
        extra = {"tos_floor": floor}

        if die in ("no_variability", "5-5", "tanpa") or float(np.std(my_t)) < 1e-6:
            yhat = np.full(len(mx_t), floor)
            fit_t = _pack_fit(
                "Lantai proses",
                "const",
                [floor],
                np.asarray(my_t), yhat, mx_t, my_t,
                f"TOS = {floor:g}",
                extra=extra,
            )
        else:
            fit_t = _fit_tos_theory(mx_t, my_t, floor)
        fit_t.update({"die": die, "metric": "time_on_site"})
        out.append(fit_t)

        fit_i = _fit_inv_linear(mx_i, my_i)
        fit_i.update({"die": die, "metric": "inventory_time", "tos_floor": floor})
        out.append(fit_i)
    return out


_MOB_SHORT = {
    "0-1-2-3-4": "rapat",
    "0-2-4-6-8": "tengah",
    "0-3-6-9-12": "longgar",
}


def plot_time_inventory_pareto(
    rows: Sequence[dict],
    ax: Optional[Axes] = None,
    highlight: Optional[str] = None,
) -> Axes:
    """Rata-rata TOS/INV vs durasi; kurva teori per keluarga variability."""
    import numpy as np

    if ax is None:
        _, ax = plt.subplots(figsize=(9.2, 5.2))
    ax_r = ax.twinx()

    by_die: Dict[str, List[dict]] = {}
    for row in rows:
        by_die.setdefault(str(row["die"]), []).append(row)

    fits = {(f["die"], f["metric"]): f for f in fit_buffer_trends(rows)}
    order = [d for d in ("no_variability", "low", "medium") if d in by_die] + [
        d for d in by_die if d not in ("no_variability", "low", "medium")
    ]
    plotted_tos: set = set()
    plotted_inv: set = set()

    for die in order:
        group = by_die[die]
        stl = _DIE_STYLE.get(die, {"color": "#334155", "marker": "o", "label": die})
        invs = _DIE_INV_STYLE.get(die, {"color": "#92400e", "marker": "o", "label": die})
        xs = [float(r["duration"]) for r in group]
        y_tos = [float(r["time_on_site"]) for r in group]
        y_inv = [float(r["inventory_time"]) for r in group]

        fit_t = fits.get((die, "time_on_site"))
        fit_i = fits.get((die, "inventory_time"))
        if fit_t:
            xmin, xmax = min(fit_t["x_mean"]), max(fit_t["x_mean"])
            span = max(2.0, xmax - xmin)
            xg = np.linspace(xmin, xmax + 0.35 * span, 120)
            ax.plot(
                xg, predict_buffer_curve(fit_t, xg),
                color=stl["color"], linestyle="--", linewidth=1.9, zorder=3,
                label=stl["label"] if die not in plotted_tos else None,
            )
            plotted_tos.add(die)
        if fit_i:
            xmin, xmax = min(fit_i["x_mean"]), max(fit_i["x_mean"])
            xg = np.linspace(xmin, xmax, 100)
            ax_r.plot(
                xg, predict_buffer_curve(fit_i, xg),
                color=invs["color"], linestyle="--", linewidth=1.9, zorder=3,
                label=invs["label"] if die not in plotted_inv else None,
            )
            plotted_inv.add(die)

        for r, x, y1, y2 in zip(group, xs, y_tos, y_inv):
            lab = str(r["label"])
            is_anchor = bool(r.get("anchor")) or (
                highlight is not None and lab == highlight
            )
            s = 88 if is_anchor else 28
            ax.scatter(
                [x], [y1], c=stl["color"], marker=stl["marker"], s=s,
                zorder=5, edgecolors="white", linewidths=0.6, alpha=0.95,
            )
            ax_r.scatter(
                [x], [y2], c=invs["color"], marker=invs["marker"], s=s,
                zorder=4, edgecolors="white", linewidths=0.6, alpha=0.9,
            )
            if is_anchor:
                short = _MOB_SHORT.get(str(r.get("mobilization")), "")
                if short:
                    ax.annotate(
                        short, (x, y1), textcoords="offset points", xytext=(5, 5),
                        fontsize=7.2, color=stl["color"], fontweight="medium",
                    )

    ax.set_xlabel("Durasi  D")
    ax.set_ylabel("Waktu di lapangan  TOS", color="#1d4ed8")
    ax_r.set_ylabel("Inventory time  INV", color="#c2410c")
    ax.tick_params(axis="y", colors="#1d4ed8")
    ax_r.tick_params(axis="y", colors="#c2410c")
    ax.grid(True, linestyle="--", alpha=0.35)
    ax.spines["top"].set_visible(False)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax_r.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=7.4, framealpha=0.94)
    return ax


# Iris pairing: Inventory time (Y) vs Time on site (X)
_IRIS_PAIR = {
    "no_variability": {"color": "#16a34a", "marker": "s", "label": "Tanpa var"},
    "low": {"color": "#ca8a04", "marker": "o", "label": "Sedang"},
    "medium": {"color": "#dc2626", "marker": "D", "label": "Tinggi"},
    "5-5": {"color": "#16a34a", "marker": "s", "label": "Tanpa var"},
    "4-6": {"color": "#ca8a04", "marker": "o", "label": "Sedang"},
    "3-7": {"color": "#dc2626", "marker": "D", "label": "Tinggi"},
}


def fit_inv_vs_tos(rows: Sequence[dict]) -> List[dict]:
    """INV vs TOS. 5-5 vertikal. Variasi: INV = a + b/(TOS−100), b≥0."""
    import numpy as np

    by_die: Dict[str, List[dict]] = {}
    for row in rows:
        by_die.setdefault(str(row["die"]), []).append(row)
    out: List[dict] = []
    for die, group in by_die.items():
        tos = [float(r["time_on_site"]) for r in group]
        inv = [float(r["inventory_time"]) for r in group]
        mx, my = _bin_means(tos, inv)
        floor = _infer_tos_floor(rows)
        if die in ("no_variability", "5-5", "tanpa") or float(np.std(mx)) < 1e-6:
            out.append(
                {
                    "die": die,
                    "eq": f"TOS = {floor:g}  (vertikal; INV mengikuti tunda)",
                    "r2": 1.0,
                    "model": "Vertikal",
                    "vertical": True,
                    "kind": "const",
                    "tos0": floor,
                    "tos_floor": floor,
                    "inv_min": float(min(inv)),
                    "inv_max": float(max(inv)),
                    "x_mean": mx,
                    "y_mean": my,
                    "coef": [floor],
                }
            )
            continue
        x = np.asarray(mx, dtype=float)
        y = np.asarray(my, dtype=float)
        z = 1.0 / np.maximum(x - floor, 0.35)
        A = np.column_stack([np.ones(len(x)), z])
        co, *_ = np.linalg.lstsq(A, y, rcond=None)
        a, b = float(co[0]), float(co[1])
        if b < 0:
            b = 0.0
            a = float(np.mean(y))
        yhat = a + b * z
        fit = _pack_fit(
            "Hiperbola (I vs T)",
            "hyp_tos",
            [a, b],
            y, yhat, mx, my,
            f"INV = {a:.1f} + {b:.1f}/(TOS − {floor:g})",
            extra={"tos_floor": floor},
        )
        fit.update({"die": die, "vertical": False})
        out.append(fit)
    return out


def plot_inventory_vs_tos(
    rows: Sequence[dict],
    ax: Optional[Axes] = None,
    highlight: Optional[str] = None,
) -> Axes:
    """Iris slide: Y = inventory time, X = time on site. Families separate."""
    import numpy as np

    if ax is None:
        _, ax = plt.subplots(figsize=(9.0, 5.4))

    by_die: Dict[str, List[dict]] = {}
    for row in rows:
        by_die.setdefault(str(row["die"]), []).append(row)
    fits = {f["die"]: f for f in fit_inv_vs_tos(rows)}
    order = [d for d in ("no_variability", "low", "medium") if d in by_die]

    for die in order:
        group = by_die[die]
        stl = _IRIS_PAIR.get(die, {"color": "#334155", "marker": "o", "label": die})
        fit = fits.get(die)
        xs = [float(r["time_on_site"]) for r in group]
        ys = [float(r["inventory_time"]) for r in group]

        if fit and fit.get("vertical"):
            ax.plot(
                [fit["tos0"], fit["tos0"]],
                [fit["inv_min"], fit["inv_max"]],
                color=stl["color"], linestyle="--", linewidth=2.0, zorder=3,
                label=f"Tanpa var  TOS tetap",
            )
        elif fit and not fit.get("vertical"):
            xg = np.linspace(min(fit["x_mean"]), max(fit["x_mean"]), 100)
            ax.plot(
                xg, predict_buffer_curve(fit, xg),
                color=stl["color"], linestyle="--", linewidth=2.0, zorder=3,
                label=stl["label"],
            )

        labeled = False
        for r, x, y in zip(group, xs, ys):
            lab = str(r["label"])
            is_anchor = bool(r.get("anchor")) or (
                highlight is not None and lab == highlight
            )
            ax.scatter(
                [x], [y], c=stl["color"], marker=stl["marker"],
                s=120 if is_anchor else 22,
                zorder=5 if is_anchor else 4,
                edgecolors="white", linewidths=0.7 if is_anchor else 0.25,
                alpha=0.95 if is_anchor else 0.28,
                label=stl["label"] if not labeled else None,
            )
            labeled = True
            if is_anchor:
                short = _MOB_SHORT.get(str(r.get("mobilization")), "")
                if short:
                    ax.annotate(
                        short, (x, y), textcoords="offset points", xytext=(6, 4),
                        fontsize=7.2, color=stl["color"], fontweight="medium",
                    )
        if fit:
            ax.scatter(
                fit["x_mean"], fit["y_mean"],
                c=stl["color"], marker=stl["marker"], s=42,
                zorder=5, edgecolors="white", linewidths=0.6, alpha=0.9,
            )

    ax.set_xlabel("Waktu di lapangan  TOS")
    ax.set_ylabel("Inventory time  INV")
    ax.set_title("Inventory time vs waktu di lapangan")
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(loc="upper right", fontsize=8, framealpha=0.94)
    return ax
