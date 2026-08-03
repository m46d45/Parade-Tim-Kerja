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
    total = first.config.total_units
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
    max_zones: int = 12,
) -> Axes:
    """
    Compact wagon / train view: rows = zones (subset), color bars = trades in time.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(10, 4.8))
    colors = [_trade_color(i) for i in range(plan.n_trades)]
    n_show = min(plan.n_zones, max_zones)
    for z in range(1, n_show + 1):
        for c in plan.cells:
            if c.zone != z:
                continue
            ax.barh(
                y=z,
                width=c.period_end - c.period_start + 1,
                left=c.period_start,
                height=0.7,
                color=colors[c.trade_index],
                edgecolor="white",
                linewidth=0.5,
                label=f"T{c.trade_index + 1}" if z == 1 else None,
            )
    ax.set_xlabel("Periode")
    ax.set_ylabel("Zona")
    ax.set_ylim(0.3, n_show + 0.7)
    ax.invert_yaxis()
    ax.set_xlim(left=0)
    ax.set_title(title or f"Takt wagons (zona 1–{n_show}) · batch={plan.batch_size}")
    # unique legend
    handles, labels = ax.get_legend_handles_labels()
    uniq = dict(zip(labels, handles))
    ax.legend(uniq.values(), uniq.keys(), loc="lower right", fontsize=8, framealpha=0.92, ncol=plan.n_trades)
    _apply_axes_style(ax)
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

