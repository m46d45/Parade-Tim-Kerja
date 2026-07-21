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
    Line of Balance: cumulative units completed by each trade vs period.

    Includes a reference ideal line (slope = bottleneck mean capacity) when
    ``show_ideal`` is True.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 5))

    cum = result.cumulative_series()  # [trade][period], period 0 = 0
    n = result.config.n_trades
    total = result.config.total_units
    periods = list(range(len(cum[0])))

    for i in range(n):
        trade = result.config.trades[i]
        label = f"T{i + 1}: {_short_name(trade.name)} ({trade.label()})"
        ax.plot(
            periods,
            cum[i],
            color=_trade_color(i),
            linewidth=2.0,
            marker="o",
            markersize=3.0,
            markevery=max(1, len(periods) // 20),
            label=label,
        )

    if show_ideal:
        mean_cap = min(t.mean for t in result.config.trades)
        if mean_cap > 0:
            ideal_t = [0, total / mean_cap]
            ideal_y = [0, total]
            ax.plot(
                ideal_t,
                ideal_y,
                color="0.45",
                linestyle=":",
                linewidth=1.6,
                label=f"Ideal ({mean_cap:g}/period)",
            )

    ax.axhline(total, color="0.7", linestyle="--", linewidth=1.0, alpha=0.8)
    ax.set_xlim(left=0)
    ax.set_ylim(0, total * 1.05)
    ax.set_xlabel("Period")
    ax.set_ylabel("Cumulative units completed")
    ax.set_title(title or "Line of Balance")
    ax.legend(loc="lower right", fontsize=8, framealpha=0.92)
    _apply_axes_style(ax)
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
        ax.set_ylabel("WIP (stacked units)")
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
        ax.set_ylabel("Buffer size (units)")

    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    ax.set_xlabel("Period")
    ax.set_title(title or "Buffer / WIP Profile")
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
    ax.set_xlabel("Utilization (%)")
    ax.set_title(title or "Trade Utilization")
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
    scenario so the panel stays readable.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 5))

    # Use first result for total / ideal reference
    first = next(iter(results.values()))
    total = first.config.total_units
    mean_cap = min(t.mean for t in first.config.trades)
    if mean_cap > 0:
        ax.plot(
            [0, total / mean_cap],
            [0, total],
            color="0.5",
            linestyle=":",
            linewidth=1.5,
            label=f"Ideal ({mean_cap:g}/period)",
        )

    for name, result in results.items():
        cum = result.cumulative_series()
        color = PRESET_COLORS.get(name, None)
        display = PRESET_DISPLAY.get(name, name)
        if last_trade_only:
            series = cum[-1]
            periods = list(range(len(series)))
            ax.plot(
                periods,
                series,
                color=color,
                linewidth=2.2,
                label=f"{display} (T={result.duration})",
            )
        else:
            for i, series in enumerate(cum):
                periods = list(range(len(series)))
                ax.plot(
                    periods,
                    series,
                    color=color,
                    linewidth=1.4,
                    alpha=0.35 + 0.12 * i,
                    label=f"{display} T{i + 1}" if i == len(cum) - 1 else None,
                )

    ax.axhline(total, color="0.7", linestyle="--", linewidth=1.0)
    ax.set_xlim(left=0)
    ax.set_ylim(0, total * 1.05)
    ax.set_xlabel("Period")
    ax.set_ylabel("Cumulative units (last trade)")
    ax.set_title(title or "Line of Balance – Scenario Comparison")
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

    for name, result in results.items():
        if result.config.n_interfaces == 0:
            continue
        buf = result.buffer_series()
        total_wip = [sum(buf[j][t] for j in range(len(buf))) for t in range(len(buf[0]))]
        color = PRESET_COLORS.get(name, None)
        display = PRESET_DISPLAY.get(name, name)
        peak = max(total_wip) if total_wip else 0
        ax.plot(
            list(range(len(total_wip))),
            total_wip,
            color=color,
            linewidth=1.9,
            label=f"{display} (peak={peak})",
        )

    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    ax.set_xlabel("Period")
    ax.set_ylabel("Total WIP (all interfaces)")
    ax.set_title(title or "Total Buffer / WIP – Scenario Comparison")
    ax.legend(loc="upper right", fontsize=8, framealpha=0.92)
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
