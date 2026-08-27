"""
Parade of Trades – Core Simulation Engine
==========================================

Lean Construction educational simulation based on:

    Tommelein, I.D., Riley, D., and Howell, G.A. (1999).
    "Parade Game: Impact of Work Flow Variability on Trade Performance."
    ASCE Journal of Construction Engineering and Management, 125(5), 304–310.

    Choo, H.J. and Tommelein, I.D. (1999).
    "Parade of Trades: A Computer Game for Understanding Variability and Dependence."
    Technical Report 99-1, UC Berkeley.

The model demonstrates how *variability* combined with *sequential dependence*
reduces throughput, increases project duration, builds WIP buffers, and wastes
production capacity — even when every trade has the same mean capacity.

Default process (Indonesian concrete floor cycle, 5 trades):
    1. Pemasangan Bekisting
    2. Pemasangan Tulangan
    3. Pengecoran Beton
    4. Pembongkaran Bekisting
    5. Finishing Lantai

Mechanics (one period):
    - Each active trade draws capacity from a low/high pair (classic 50/50; weighted when mean is fractional e.g. ⅓× speed).
    - Actual production = min(capacity, available upstream buffer, remaining work).
    - Handoff modes:
        * next-period / field sequence (recommended in UI): zones finished by
          trade i in period t become available to trade i+1 in period t+1
          (T1 moves on; T2 starts those zones next period). No-var LOB shows
          staggered straight lines — the classic parade.
        * same-period (classic computer game): upstream output may be taken
          by downstream within the same period; no-var LOB lines collapse.
    - Simulation ends when the last trade has completed all work units.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Sequence, Tuple, Union
import math
import random
import json


# ---------------------------------------------------------------------------
# Capacity presets (mean = 5 for all classic pairs)
# ---------------------------------------------------------------------------

CAPACITY_PRESETS: Dict[str, Tuple[int, int]] = {
    "no_variability": (5, 5),
    "low": (4, 6),
    "medium": (3, 7),
    "high": (2, 8),
    "very_high": (1, 9),
}

DEFAULT_TRADE_NAMES: Tuple[str, ...] = (
    "Pemasangan Bekisting",
    "Pemasangan Tulangan",
    "Pengecoran Beton",
    "Pembongkaran Bekisting",
    "Finishing Lantai",
)

DEFAULT_TOTAL_UNITS = 100
DEFAULT_MEAN_CAPACITY = 5


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class TradeConfig:
    """Capacity for a single trade.

    Classic Tommelein dice: integer ``low``/``high`` with ``p_high`` (default 50/50).

    Classroom base speeds without variability use ``deterministic=True`` and
    ``base_speed`` (zones per period). Fractional rates accumulate until a
    whole zone is completed, e.g. base_speed=0.5 → exactly 1 zone every 2
    periods (LOB steps every other period).
    """

    name: str
    low: float
    high: float
    p_high: float = 0.5  # probability of rolling ``high`` (else ``low``)
    base_speed: Optional[float] = None  # target zones/period; default = mean
    deterministic: bool = False  # True: pace accumulator (no random die)

    def __post_init__(self) -> None:
        if self.low < 0 or self.high < 0:
            raise ValueError(f"Capacity must be non-negative: {self.name}")
        if self.low > self.high:
            raise ValueError(
                f"low ({self.low}) must be <= high ({self.high}) for {self.name}"
            )
        if not 0.0 <= float(self.p_high) <= 1.0:
            raise ValueError(
                f"p_high must be in [0, 1] for {self.name}, got {self.p_high}"
            )
        self.p_high = float(self.p_high)
        if self.base_speed is None:
            if self.low == self.high:
                self.base_speed = float(self.low)
            else:
                self.base_speed = (
                    (1.0 - self.p_high) * self.low + self.p_high * self.high
                )
        else:
            self.base_speed = float(self.base_speed)
        if self.base_speed < 0:
            raise ValueError(f"base_speed must be non-negative: {self.name}")

    @property
    def mean(self) -> float:
        return float(self.base_speed) if self.base_speed is not None else 0.0

    @property
    def pair(self) -> Tuple[float, float]:
        return (float(self.low), float(self.high))

    def label(self) -> str:
        b = self.mean
        if self.deterministic:
            # Classroom labels for fixed paces
            if abs(b - 1.0 / 3.0) < 1e-9:
                return "1 zona/3 per"
            if abs(b - 0.5) < 1e-9:
                return "1 zona/2 per"
            if abs(b - 1.0) < 1e-9:
                return "1 zona/per"
            if abs(b - 2.0) < 1e-9:
                return "2 zona/per"
            if abs(b - 3.0) < 1e-9:
                return "3 zona/per"
            return f"{b:g} zona/per"
        if self.low == self.high:
            return f"{self.low}/{self.high}"
        if abs(self.p_high - 0.5) < 1e-9:
            return f"{self.low}/{self.high}"
        return f"{self.low}/{self.high} (E≈{self.mean:g})"


@dataclass
class ParadeConfig:
    """Full configuration for a Parade of Trades run.

    Takt planning (Tommelein 2020)
    --------------------------------
    When ``takt_rate`` is set, each trade commits to passing *at least*
    that many units per period when work is available. If the die roll
    falls short, up to ``standby_capacity`` units of standby (capacity
    buffer) are deployed to cover the shortfall. Passing *more* than the
    takt when the die allows is still permitted.

    Example (paper Scenario 2): die 4/6, takt_rate=5, standby_capacity=1
    → effective capacity is 5 or 6 (equivalent production to a 5/6 die),
    while standby usage is tracked separately.
    """

    trades: List[TradeConfig]
    total_units: int = DEFAULT_TOTAL_UNITS
    seed: Optional[int] = None
    # Takt / capacity-buffer options (None takt_rate ⇒ classic Parade)
    takt_rate: Optional[int] = None
    standby_capacity: int = 0
    # Handoff between trades:
    #   False (default) = "next period": output of trade i becomes available to
    #     trade i+1 only in the *following* period. Each zone therefore flows
    #     T1 → (wait) → T2 → (wait) → … so LOB lines are clearly sequenced.
    #   True = "same period": classic computer-game rule where upstream output
    #     may be taken by downstream in the same period (sequential update).
    same_period_handoff: bool = False
    # Optional extra gate: trade i may not work before period (i+1).
    staggered_mobilization: bool = False
    # 0-based start delays (Iris): e.g. (0, 1, 2, 3, 4) or (0, 3, 6, 9, 12).
    # Trade i may work when period >= offset[i] + 1 (period is 1-indexed).
    # If set, this overrides the boolean staggered_mobilization pattern.
    mobilization_offsets: Optional[Tuple[int, ...]] = None
    # Classroom zone-flow model (app default): work zone-by-zone (or batch),
    # variability is per-zone speed, not bulk multi-zone dice.
    zone_flow: bool = False
    batch_size: int = 1  # 1 = one-piece flow; 3 = hand off every 3 zones

    def __post_init__(self) -> None:
        if not self.trades:
            raise ValueError("At least one trade is required")
        if self.total_units <= 0:
            raise ValueError("total_units must be positive")
        if self.takt_rate is not None and self.takt_rate <= 0:
            raise ValueError("takt_rate must be positive when set")
        if self.standby_capacity < 0:
            raise ValueError("standby_capacity must be non-negative")
        if self.batch_size < 1:
            raise ValueError("batch_size must be >= 1")
        if self.mobilization_offsets is not None:
            offs = tuple(int(x) for x in self.mobilization_offsets)
            if len(offs) != self.n_trades:
                raise ValueError(
                    f"mobilization_offsets length {len(offs)} != n_trades {self.n_trades}"
                )
            if any(x < 0 for x in offs):
                raise ValueError("mobilization_offsets must be non-negative")
            self.mobilization_offsets = offs

    @property
    def n_trades(self) -> int:
        return len(self.trades)

    @property
    def n_interfaces(self) -> int:
        """Number of WIP buffers between consecutive trades."""
        return max(0, self.n_trades - 1)

    @property
    def takt_enabled(self) -> bool:
        return self.takt_rate is not None

    @property
    def zone_sequence_lag(self) -> bool:
        """True when each zone waits one period between consecutive trades."""
        return not self.same_period_handoff

    def mode_label(self) -> str:
        parts = []
        if self.same_period_handoff:
            parts.append("handoff=same_period")
        else:
            parts.append("handoff=next_period")
        if self.staggered_mobilization:
            parts.append("staggered")
        if self.mobilization_offsets is not None:
            parts.append("mob=" + "-".join(str(x) for x in self.mobilization_offsets))
        if self.takt_enabled:
            parts.append(f"takt={self.takt_rate}")
            parts.append(f"standby={self.standby_capacity}")
        return ", ".join(parts) if parts else "classic"

    @classmethod
    def from_preset(
        cls,
        preset: Union[str, Sequence[str]] = "medium",
        n_trades: int = 5,
        trade_names: Optional[Sequence[str]] = None,
        total_units: int = DEFAULT_TOTAL_UNITS,
        seed: Optional[int] = None,
        takt_rate: Optional[int] = None,
        standby_capacity: int = 0,
        same_period_handoff: bool = False,
        staggered_mobilization: bool = False,
        mobilization_offsets: Optional[Sequence[int]] = None,
    ) -> "ParadeConfig":
        """
        Build config from named variability preset(s).

        Default handoff is *next period*: each zone finishes trade *i* in one
        period and only then becomes available to trade *i+1* next period.
        """
        if isinstance(preset, str):
            if preset not in CAPACITY_PRESETS:
                raise ValueError(
                    f"Unknown preset '{preset}'. "
                    f"Choose from: {list(CAPACITY_PRESETS)}"
                )
            pairs = [CAPACITY_PRESETS[preset]] * n_trades
            preset_labels = [preset] * n_trades
        else:
            pairs = []
            preset_labels = list(preset)
            for p in preset:
                if p not in CAPACITY_PRESETS:
                    raise ValueError(
                        f"Unknown preset '{p}'. "
                        f"Choose from: {list(CAPACITY_PRESETS)}"
                    )
                pairs.append(CAPACITY_PRESETS[p])
            n_trades = len(pairs)

        names = _resolve_trade_names(n_trades, trade_names)
        trades = [
            TradeConfig(name=names[i], low=pairs[i][0], high=pairs[i][1])
            for i in range(n_trades)
        ]
        cfg = cls(
            trades=trades,
            total_units=total_units,
            seed=seed,
            takt_rate=takt_rate,
            standby_capacity=standby_capacity,
            same_period_handoff=same_period_handoff,
            staggered_mobilization=staggered_mobilization,
            mobilization_offsets=(
                tuple(int(x) for x in mobilization_offsets)
                if mobilization_offsets is not None
                else None
            ),
        )
        cfg._preset_labels = preset_labels  # type: ignore[attr-defined]
        return cfg

    @classmethod
    def from_pairs(
        cls,
        pairs: Sequence[Tuple[int, int]],
        trade_names: Optional[Sequence[str]] = None,
        total_units: int = DEFAULT_TOTAL_UNITS,
        seed: Optional[int] = None,
        takt_rate: Optional[int] = None,
        standby_capacity: int = 0,
        same_period_handoff: bool = False,
        staggered_mobilization: bool = False,
        mobilization_offsets: Optional[Sequence[int]] = None,
        zone_flow: bool = False,
        batch_size: int = 1,
    ) -> "ParadeConfig":
        """Build config from explicit (low, high) capacity pairs per trade."""
        if not pairs:
            raise ValueError("At least one capacity pair is required")
        names = _resolve_trade_names(len(pairs), trade_names)
        trades = []
        for i, p in enumerate(pairs):
            if len(p) == 2:
                lo, hi = float(p[0]), float(p[1])
                trades.append(TradeConfig(name=names[i], low=lo, high=hi))
            elif len(p) == 3:
                lo, hi, ph = float(p[0]), float(p[1]), float(p[2])
                trades.append(
                    TradeConfig(name=names[i], low=lo, high=hi, p_high=ph)
                )
            elif len(p) >= 5:
                lo, hi, ph = float(p[0]), float(p[1]), float(p[2])
                bspd = float(p[3])
                det = bool(p[4])
                trades.append(
                    TradeConfig(
                        name=names[i],
                        low=lo,
                        high=hi,
                        p_high=ph,
                        base_speed=bspd,
                        deterministic=det,
                    )
                )
            elif len(p) == 4:
                lo, hi, ph, bspd = float(p[0]), float(p[1]), float(p[2]), float(p[3])
                trades.append(
                    TradeConfig(
                        name=names[i], low=lo, high=hi, p_high=ph, base_speed=bspd
                    )
                )
            else:
                raise ValueError(
                    "Capacity pair must be (low, high), (low, high, p_high), "
                    "or (low, high, p_high, base_speed, deterministic); "
                    f"got {p!r}"
                )
        return cls(
            trades=trades,
            total_units=total_units,
            seed=seed,
            takt_rate=takt_rate,
            standby_capacity=standby_capacity,
            same_period_handoff=same_period_handoff,
            staggered_mobilization=staggered_mobilization,
            mobilization_offsets=(
                tuple(int(x) for x in mobilization_offsets)
                if mobilization_offsets is not None
                else None
            ),
            zone_flow=zone_flow,
            batch_size=batch_size,
        )


def _resolve_trade_names(
    n: int, trade_names: Optional[Sequence[str]]
) -> List[str]:
    if trade_names is not None:
        if len(trade_names) != n:
            raise ValueError(
                f"Expected {n} trade names, got {len(trade_names)}"
            )
        return list(trade_names)
    names: List[str] = []
    for i in range(n):
        if i < len(DEFAULT_TRADE_NAMES):
            names.append(DEFAULT_TRADE_NAMES[i])
        else:
            names.append(f"Trade {i + 1}")
    return names


# ---------------------------------------------------------------------------
# Per-period and aggregate results
# ---------------------------------------------------------------------------

@dataclass
class PeriodRecord:
    """Snapshot of one simulation period after all trades have acted."""

    period: int
    # length = n_trades
    capacity: List[int]  # die outcome (base capacity)
    production: List[int]
    idle_capacity: List[int]  # effective_capacity - production
    cumulative: List[int]
    # length = n_interfaces (WIP after each trade except the last)
    buffers: List[int]
    # raw remaining at start of parade (not yet processed by trade 0)
    raw_remaining: int
    # Takt / standby (same length as trades; 0 when classic / inactive)
    effective_capacity: List[int] = field(default_factory=list)
    standby_used: List[int] = field(default_factory=list)
    # Continuous progress for LOB (cum + partial zone). Shows straight pace lines.
    fractional_cumulative: List[float] = field(default_factory=list)


@dataclass
class TradeMetrics:
    """Aggregate metrics for one trade after a completed run."""

    name: str
    capacity_pair: Tuple[int, int]
    mean_capacity: float
    executions: int
    total_capacity: int  # sum of die rolls while active
    total_production: int
    total_idle: int  # sum(effective - production)
    utilization: float  # production / effective_capacity (0..1); idle = starvation
    periods_to_finish: int  # first period where cumulative == total_units
    total_standby_used: int = 0
    total_effective_capacity: int = 0
    time_on_site: int = 0  # periods from mobilize to finish (inclusive)
    start_period: Optional[int] = None


@dataclass
class ParadeResult:
    """Full output of a completed (or mid-run) simulation."""

    config: ParadeConfig
    duration: int
    history: List[PeriodRecord]
    trade_metrics: List[TradeMetrics]
    max_buffer: List[int]  # max WIP observed at each interface
    total_idle_capacity: int
    system_throughput: float  # total_units / duration
    ideal_duration: float  # total_units / mean_capacity of bottleneck (same mean)
    total_standby_used: int = 0
    total_inventory_time: int = 0  # Σ_t Σ_interfaces WIP(t)
    total_time_on_site: int = 0  # Σ_trades time_on_site

    def to_dict(self) -> dict:
        """JSON-serialisable summary (history included)."""
        return {
            "seed": self.config.seed,
            "total_units": self.config.total_units,
            "mode": self.config.mode_label(),
            "takt_rate": self.config.takt_rate,
            "standby_capacity": self.config.standby_capacity,
            "same_period_handoff": self.config.same_period_handoff,
            "staggered_mobilization": self.config.staggered_mobilization,
            "mobilization_offsets": (
                list(self.config.mobilization_offsets)
                if self.config.mobilization_offsets is not None
                else None
            ),
            "trades": [
                {
                    "name": t.name,
                    "low": t.low,
                    "high": t.high,
                    "label": t.label(),
                }
                for t in self.config.trades
            ],
            "duration": self.duration,
            "system_throughput": self.system_throughput,
            "ideal_duration": self.ideal_duration,
            "total_idle_capacity": self.total_idle_capacity,
            "total_standby_used": self.total_standby_used,
            "total_inventory_time": self.total_inventory_time,
            "total_time_on_site": self.total_time_on_site,
            "max_buffer": self.max_buffer,
            "trade_metrics": [asdict(m) for m in self.trade_metrics],
            "history": [asdict(h) for h in self.history],
        }

    def cumulative_series(self) -> List[List[int]]:
        """Return list-of-series: series[trade][period] = cumulative output.

        Index 0 of each series is period 0 (all zeros) for convenient plotting.
        """
        n = self.config.n_trades
        series: List[List[int]] = [[0] for _ in range(n)]
        for rec in self.history:
            for i in range(n):
                series[i].append(rec.cumulative[i])
        return series

    def fractional_cumulative_series(self) -> List[List[float]]:
        """Continuous cumulative for LOB (straight pace lines).

        Uses fractional_cumulative when present (deterministic paces); falls
        back to integer cumulative otherwise. Index 0 = period 0 (zeros).
        """
        n = self.config.n_trades
        series: List[List[float]] = [[0.0] for _ in range(n)]
        for rec in self.history:
            frac = rec.fractional_cumulative
            for i in range(n):
                if frac and i < len(frac):
                    series[i].append(float(frac[i]))
                else:
                    series[i].append(float(rec.cumulative[i]))
        return series

    def buffer_series(self) -> List[List[int]]:
        """Return list-of-series: series[interface][period] = buffer size.

        Index 0 of each series is period 0 (all zeros).
        """
        n_if = self.config.n_interfaces
        series: List[List[int]] = [[0] for _ in range(n_if)]
        for rec in self.history:
            for i in range(n_if):
                series[i].append(rec.buffers[i])
        return series

    def production_series(self) -> List[List[int]]:
        """Return list-of-series: series[trade][period-1] = period production."""
        n = self.config.n_trades
        series: List[List[int]] = [[] for _ in range(n)]
        for rec in self.history:
            for i in range(n):
                series[i].append(rec.production[i])
        return series


# ---------------------------------------------------------------------------
# Simulation engine
# ---------------------------------------------------------------------------

class ParadeOfTrades:
    """
    Discrete-period Parade of Trades simulator.

    Usage
    -----
    >>> cfg = ParadeConfig.from_preset("medium", seed=42)
    >>> sim = ParadeOfTrades(cfg)
    >>> result = sim.run()
    >>> sim.print_summary()

    Stepping (interactive / UI):
    >>> sim = ParadeOfTrades(cfg)
    >>> while not sim.is_complete:
    ...     rec = sim.step()
    >>> result = sim.get_result()
    """

    def __init__(self, config: ParadeConfig) -> None:
        self.config = config
        self._rng = random.Random(config.seed)
        self.reset()

    # -- lifecycle ----------------------------------------------------------

    def reset(self) -> None:
        """Return the simulation to the initial state (keeps seed stream only
        if a new seed is supplied via ``reseed``)."""
        n = self.config.n_trades
        n_if = self.config.n_interfaces
        self.period: int = 0
        self.cumulative: List[int] = [0] * n
        self.buffers: List[int] = [0] * n_if  # WIP after trade i (i = 0..n-2)
        self.raw_remaining: int = self.config.total_units
        self.max_buffer: List[int] = [0] * n_if
        self.history: List[PeriodRecord] = []
        # Fractional zone progress for deterministic (classroom) paces
        self._progress: List[float] = [0.0] * n
        # Zone-flow state (one-piece / batch)
        self._zone_progress: List[float] = [0.0] * n  # 0..1 on current zone
        self._zone_rate: List[Optional[float]] = [None] * n  # speed locked for current zone
        self._batch_done: List[int] = [0] * n  # zones completed toward current batch
        self._working: List[bool] = [False] * n
        # running sums for metrics
        self._total_capacity: List[int] = [0] * n
        self._total_effective: List[int] = [0] * n
        self._total_production: List[int] = [0] * n
        self._total_idle: List[int] = [0] * n
        self._total_standby: List[int] = [0] * n
        self._executions: List[int] = [0] * n
        self._finish_period: List[Optional[int]] = [None] * n
        self._start_period: List[Optional[int]] = [None] * n
        self._result: Optional[ParadeResult] = None

    def reseed(self, seed: Optional[int] = None) -> None:
        """Set a new RNG seed and reset state."""
        self.config.seed = seed
        self._rng = random.Random(seed)
        self.reset()

    # -- queries ------------------------------------------------------------

    @property
    def is_complete(self) -> bool:
        """True when the last trade has finished all work units."""
        return self.cumulative[-1] >= self.config.total_units

    @property
    def n_trades(self) -> int:
        return self.config.n_trades

    # -- core step ----------------------------------------------------------

    def _roll_capacity(self, trade_idx: int) -> int:
        """Draw capacity between low and high (weighted by ``p_high``)."""
        t = self.config.trades[trade_idx]
        if t.low == t.high:
            return t.low
        if self._rng.random() < t.p_high:
            return t.high
        return t.low

    def _apply_standby(self, base_capacity: int) -> Tuple[int, int]:
        """
        Apply capacity buffer (standby) toward the takt commitment.

        Returns (effective_capacity, standby_used).
        """
        takt = self.config.takt_rate
        standby = self.config.standby_capacity
        if takt is None or standby <= 0:
            return base_capacity, 0
        shortfall = max(0, takt - base_capacity)
        used = min(standby, shortfall)
        return base_capacity + used, used

    def _is_mobilized(self, trade_idx: int) -> bool:
        """Whether trade may work this period (time buffer / delayed start)."""
        offs = self.config.mobilization_offsets
        if offs is not None:
            delay = int(offs[trade_idx]) if trade_idx < len(offs) else 0
            return self.period >= delay + 1
        if not self.config.staggered_mobilization:
            return True
        return self.period >= (trade_idx + 1)

    def step(self) -> PeriodRecord:
        """
        Execute one period for all trades.

        Handoff modes
        -------------
        *next period* (default, ``same_period_handoff=False``):
            Each trade pulls only from inventory present at the *start* of the
            period. Production is released to the next trade at period end.
            Therefore every zone waits at least one full period between
            consecutive trades (T1 → T2 → T3 …) — the correct parade sequence.

        *same period* (``same_period_handoff=True``):
            Classic computer-game rule: upstream production may be taken by
            the next trade within the same period (sequential update).

        With takt enabled, standby capacity covers shortfalls below takt_rate.
        """
        if self.is_complete:
            raise RuntimeError("Simulation already complete; call reset()")

        if self.config.zone_flow:
            return self._step_zone_flow()

        self.period += 1
        n = self.config.n_trades
        total = self.config.total_units
        same_period = self.config.same_period_handoff

        capacities = [0] * n
        effectives = [0] * n
        standbys = [0] * n
        productions = [0] * n
        idles = [0] * n

        # Working inventories for this period
        if same_period:
            raw = self.raw_remaining
            bufs = list(self.buffers)
        else:
            # Snapshot start-of-period stock; new production not usable until next period
            raw = self.raw_remaining
            bufs = list(self.buffers)

        for i in range(n):
            remaining_for_trade = total - self.cumulative[i]

            if remaining_for_trade <= 0 or not self._is_mobilized(i):
                capacities[i] = 0
                effectives[i] = 0
                standbys[i] = 0
                productions[i] = 0
                idles[i] = 0
                continue

            if i == 0:
                available = raw
            else:
                available = bufs[i - 1]

            # Not yet on this zone's parade position: no input and never produced
            # → skip without rolling (crew has not "arrived" for this work yet).
            # Once started, empty buffer counts as starvation (idle capacity).
            already_started = self.cumulative[i] > 0
            if available <= 0 and not already_started:
                capacities[i] = 0
                effectives[i] = 0
                standbys[i] = 0
                productions[i] = 0
                idles[i] = 0
                continue

            trade_cfg = self.config.trades[i]
            if trade_cfg.deterministic:
                # Classroom pace: accumulate base_speed only when work is available
                # so LOB fractional progress is a straight line at constant speed.
                # Lambat (0.5): slope 0.5 zona/periode. Normal: slope 1. etc.
                if available > 0 and remaining_for_trade > 0:
                    self._progress[i] += float(trade_cfg.base_speed or 0.0)
                potential = int(math.floor(self._progress[i] + 1e-12))
                base = potential
                effective, standby_used = self._apply_standby(base)
                actual = min(effective, available, remaining_for_trade)
                self._progress[i] -= actual
            else:
                base = self._roll_capacity(i)
                effective, standby_used = self._apply_standby(base)
                actual = min(effective, available, remaining_for_trade)

            # Consume from this period's working stock
            if i == 0:
                raw -= actual
            else:
                bufs[i - 1] -= actual

            if same_period and i < n - 1:
                # Immediate handoff: output available to next trade this period
                bufs[i] += actual

            productions[i] = actual
            capacities[i] = base
            effectives[i] = effective
            standbys[i] = standby_used
            idles[i] = effective - actual

            if actual > 0 and self._start_period[i] is None:
                self._start_period[i] = self.period

            self.cumulative[i] += actual
            self._executions[i] += 1
            self._total_capacity[i] += base
            self._total_effective[i] += effective
            self._total_production[i] += actual
            self._total_idle[i] += idles[i]
            self._total_standby[i] += standby_used

            if self.cumulative[i] >= total and self._finish_period[i] is None:
                self._finish_period[i] = self.period

        # Commit inventories at period end
        self.raw_remaining = raw
        if same_period:
            self.buffers = bufs
        else:
            # Leftover start-stock after pulls + this period's production
            for i in range(self.config.n_interfaces):
                self.buffers[i] = bufs[i] + productions[i]

        for j in range(self.config.n_interfaces):
            if self.buffers[j] > self.max_buffer[j]:
                self.max_buffer[j] = self.buffers[j]

        # Continuous LOB y = finished zones + partial progress (straight pace line)
        fractional = [
            min(float(total), float(self.cumulative[i]) + float(self._progress[i]))
            for i in range(n)
        ]
        rec = PeriodRecord(
            period=self.period,
            capacity=capacities,
            production=productions,
            idle_capacity=idles,
            cumulative=list(self.cumulative),
            buffers=list(self.buffers),
            raw_remaining=self.raw_remaining,
            effective_capacity=effectives,
            standby_used=standbys,
            fractional_cumulative=fractional,
        )
        self.history.append(rec)
        return rec


    # -- zone-flow step (classroom one-piece / batch) -----------------------


    def _draw_zone_rate(self, trade_idx: int) -> float:
        """Speed for one zone (progress per period), locked until that zone is done.

        No variability → constant base_speed.
        With variability → one low/high draw **per zone** (not bulk multi-zone dice).
        """
        t = self.config.trades[trade_idx]
        if t.deterministic or t.low == t.high:
            return max(1e-9, float(t.base_speed if t.base_speed is not None else t.mean))
        rate = float(t.high if self._rng.random() < t.p_high else t.low)
        return max(1e-9, rate)

    def _step_zone_flow(self) -> "PeriodRecord":
        """
        Zone-centric parade (one-piece flow when batch_size=1).

        - Each trade works **zone by zone** (speed = progress on current zone).
        - Variability draws a speed **once per zone**.
        - Finished zones accumulate into a batch; when ``batch_size`` is reached
          they are released to the next trade for the **next period**.
        - That lag keeps LOB lines staggered (T2≠T3≠T4≠T5 when speeds equal).
        """
        self.period += 1
        n = self.config.n_trades
        total = self.config.total_units
        batch_size = max(1, int(self.config.batch_size))

        capacities = [0] * n
        effectives = [0] * n
        standbys = [0] * n
        productions = [0] * n
        idles = [0] * n
        released = [0] * n

        # Inbound at start of period (handoff from previous period only)
        available = [self.raw_remaining] + list(self.buffers)

        for i in range(n):
            if self.cumulative[i] >= total or not self._is_mobilized(i):
                continue

            tcfg = self.config.trades[i]
            base_rate = float(
                tcfg.base_speed if tcfg.base_speed is not None else tcfg.mean
            )
            # Crew-period capacity unit (int): at least 1 when active
            def _crew_cap(rate: float) -> int:
                if rate + 1e-12 >= 1.0:
                    return max(1, int(round(rate)))
                return 1

            rate_applied = 0.0
            has_started = self._start_period[i] is not None

            # --- Starvation: already on site, no zone to work ---
            # (matches classic parade: once started, empty buffer = idle capacity)
            if not self._working[i] and available[i] <= 0:
                if has_started and self.cumulative[i] < total:
                    cap = _crew_cap(base_rate)
                    capacities[i] = cap
                    effectives[i] = cap
                    productions[i] = 0
                    idles[i] = cap
                    self._executions[i] += 1
                    self._total_capacity[i] += cap
                    self._total_effective[i] += cap
                    self._total_idle[i] += cap
                continue

            # Start a zone if idle and inbound exists
            if not self._working[i]:
                available[i] -= 1
                self._working[i] = True
                self._zone_progress[i] = 0.0
                self._zone_rate[i] = self._draw_zone_rate(i)
                if self._start_period[i] is None:
                    self._start_period[i] = self.period

            rate = float(self._zone_rate[i] or 0.0)
            rate_applied = rate
            self._zone_progress[i] += rate

            # Complete as many zones as progress allows (fast trades / high rate)
            while self._zone_progress[i] + 1e-12 >= 1.0 and self.cumulative[i] < total:
                self._zone_progress[i] -= 1.0
                self.cumulative[i] += 1
                productions[i] += 1
                self._batch_done[i] += 1
                self._working[i] = False

                if self._batch_done[i] >= batch_size:
                    released[i] += self._batch_done[i]
                    self._batch_done[i] = 0

                if self.cumulative[i] >= total:
                    self._zone_progress[i] = 0.0
                    if self._finish_period[i] is None:
                        self._finish_period[i] = self.period
                    break

                # Only pull another zone same period if leftover progress remains
                if self._zone_progress[i] > 1e-12:
                    if available[i] > 0:
                        available[i] -= 1
                        self._working[i] = True
                        self._zone_rate[i] = self._draw_zone_rate(i)
                    else:
                        # leftover capacity blocked by missing inbound = idle
                        self._zone_progress[i] = 0.0
                        break
                else:
                    break

            # Flush partial batch when this trade finished all zones
            if self.cumulative[i] >= total and self._batch_done[i] > 0:
                released[i] += self._batch_done[i]
                self._batch_done[i] = 0

            # Capacity / idle while working
            # - rate >= 1: offered ≈ rate; idle if production < capacity
            #   (e.g. finished a zone mid-period then no inbound left)
            # - rate < 1: count capacity only when a zone completes so a fully
            #   busy slow crew stays ~100% util (not 50% for 0.5 rate)
            if rate_applied + 1e-12 >= 1.0:
                cap = max(productions[i], _crew_cap(rate_applied))
                idle = max(0, cap - productions[i])
            else:
                cap = productions[i]
                idle = 0

            capacities[i] = cap
            effectives[i] = cap
            idles[i] = idle

            # Count execution when working or producing (partial zone still "on tool")
            if productions[i] > 0 or self._working[i] or idle > 0:
                self._executions[i] += 1
            self._total_capacity[i] += capacities[i]
            self._total_effective[i] += effectives[i]
            self._total_production[i] += productions[i]
            self._total_idle[i] += idles[i]

        # Next-period handoff: unconsumed inbound + newly released batches
        self.raw_remaining = available[0]
        new_buffers = [0] * self.config.n_interfaces
        for j in range(self.config.n_interfaces):
            new_buffers[j] = available[j + 1] + released[j]
            if new_buffers[j] > self.max_buffer[j]:
                self.max_buffer[j] = new_buffers[j]
        self.buffers = new_buffers

        fractional = [
            min(
                float(total),
                float(self.cumulative[i])
                + (float(self._zone_progress[i]) if self._working[i] else 0.0),
            )
            for i in range(n)
        ]
        rec = PeriodRecord(
            period=self.period,
            capacity=capacities,
            production=productions,
            idle_capacity=idles,
            cumulative=list(self.cumulative),
            buffers=list(self.buffers),
            raw_remaining=self.raw_remaining,
            effective_capacity=effectives,
            standby_used=standbys,
            fractional_cumulative=fractional,
        )
        self.history.append(rec)
        return rec

    def run(self, max_periods: Optional[int] = None) -> ParadeResult:
        """
        Run until completion (or ``max_periods`` safety limit).

        Parameters
        ----------
        max_periods :
            Optional hard stop. Default is a generous bound based on
            total_units and minimum capacity so pathological configs
            cannot hang forever.
        """
        if max_periods is None:
            min_cap = min(float(t.low) for t in self.config.trades)
            # Zone-flow with fractional rates needs more periods (e.g. rate 0.1).
            if self.config.zone_flow:
                min_rate = min(max(float(t.low), 1e-6) for t in self.config.trades)
                max_periods = max(
                    int(self.config.total_units / min_rate * self.config.n_trades * 4)
                    + self.config.batch_size * self.config.n_trades * 2
                    + 100,
                    self.config.total_units * self.config.n_trades * 5,
                    500,
                )
            else:
                max_periods = max(
                    self.config.total_units * self.config.n_trades * 5,
                    self.config.total_units * 10,
                    1,
                )
            if min_cap == 0:
                # zero capacity can never finish – still bound the loop
                max_periods = self.config.total_units * 20

        while not self.is_complete:
            if self.period >= max_periods:
                raise RuntimeError(
                    f"Simulation exceeded max_periods={max_periods}. "
                    "Check capacity configuration (zero capacity?)."
                )
            self.step()

        self._result = self._build_result()
        return self._result

    def get_result(self) -> ParadeResult:
        """Return result for the current state (complete or partial)."""
        return self._build_result()

    def _build_result(self) -> ParadeResult:
        total = self.config.total_units
        metrics: List[TradeMetrics] = []
        for i, t in enumerate(self.config.trades):
            base_cap = self._total_capacity[i]
            eff_cap = self._total_effective[i]
            prod = self._total_production[i]
            denom = eff_cap if eff_cap > 0 else base_cap
            util = (prod / denom) if denom > 0 else 0.0
            finish = self._finish_period[i]
            if finish is None and self.cumulative[i] >= total:
                finish = self.period
            start = self._start_period[i]
            if finish is not None and start is not None:
                time_on_site = finish - start + 1
            else:
                time_on_site = self._executions[i]
            metrics.append(
                TradeMetrics(
                    name=t.name,
                    capacity_pair=t.pair,
                    mean_capacity=t.mean,
                    executions=self._executions[i],
                    total_capacity=base_cap,
                    total_production=prod,
                    total_idle=self._total_idle[i],
                    utilization=util,
                    periods_to_finish=finish if finish is not None else self.period,
                    total_standby_used=self._total_standby[i],
                    total_effective_capacity=eff_cap,
                    time_on_site=time_on_site,
                    start_period=start,
                )
            )

        # Ideal: with takt, use effective mean ≈ max(mean_die, takt) when standby
        # covers shortfall to takt; else classic bottleneck mean.
        if self.config.takt_enabled and self.config.standby_capacity > 0:
            # Approximate expected effective capacity under 50/50 die
            eff_means = []
            for t in self.config.trades:
                # E[effective] = 0.5 * (max(low+standby_cover, low) + high)
                lo_eff = t.low + min(
                    self.config.standby_capacity,
                    max(0, (self.config.takt_rate or 0) - t.low),
                )
                hi_eff = t.high + min(
                    self.config.standby_capacity,
                    max(0, (self.config.takt_rate or 0) - t.high),
                )
                eff_means.append(0.5 * (lo_eff + hi_eff))
            bottleneck_mean = min(eff_means) if eff_means else DEFAULT_MEAN_CAPACITY
        else:
            means = [t.mean for t in self.config.trades]
            bottleneck_mean = min(means) if means else DEFAULT_MEAN_CAPACITY

        ideal = total / bottleneck_mean if bottleneck_mean > 0 else float("inf")
        # Pipeline fill: last trade cannot finish until first units have passed
        # every upstream handoff lag (next-period) and/or staggered starts.
        pipeline_lags = 0
        if not self.config.same_period_handoff:
            pipeline_lags = max(pipeline_lags, self.config.n_trades - 1)
        if self.config.staggered_mobilization:
            pipeline_lags = max(pipeline_lags, self.config.n_trades - 1)
        ideal += pipeline_lags

        duration = self.period
        throughput = total / duration if duration > 0 else 0.0
        inv_time = sum(sum(rec.buffers) for rec in self.history)
        tos = sum(m.time_on_site for m in metrics)

        return ParadeResult(
            config=self.config,
            duration=duration,
            history=list(self.history),
            trade_metrics=metrics,
            max_buffer=list(self.max_buffer),
            total_idle_capacity=sum(self._total_idle),
            system_throughput=throughput,
            ideal_duration=ideal,
            total_standby_used=sum(self._total_standby),
            total_inventory_time=int(inv_time),
            total_time_on_site=int(tos),
        )

    # -- reporting ----------------------------------------------------------

    def print_summary(self, result: Optional[ParadeResult] = None) -> None:
        """Pretty-print key metrics to stdout."""
        r = result if result is not None else self.get_result()
        cfg = r.config
        sep = "=" * 72
        thin = "-" * 72

        print(sep)
        print("PARADE OF TRADES – Simulation Summary")
        print(sep)
        print(f"  Total work units : {cfg.total_units}")
        print(f"  Number of trades : {cfg.n_trades}")
        print(f"  Seed             : {cfg.seed}")
        print(f"  Mode             : {cfg.mode_label()}")
        print(f"  Duration         : {r.duration} periods")
        print(f"  Ideal duration   : {r.ideal_duration:.1f} periods "
              f"(total / min mean capacity)")
        print(f"  Delay vs ideal   : {r.duration - r.ideal_duration:+.1f} periods")
        print(f"  Throughput       : {r.system_throughput:.3f} units/period")
        print(f"  Total idle cap.  : {r.total_idle_capacity} unit-periods")
        if cfg.takt_enabled:
            print(f"  Total standby    : {r.total_standby_used} unit-periods deployed")
        print(thin)

        # Trade table
        hdr = (
            f"{'#':>2}  {'Trade':<28}  {'Cap':>5}  {'Exec':>5}  "
            f"{'Prod':>5}  {'Idle':>5}  {'Util%':>6}  {'Finish':>6}  "
            f"{'OnSite':>6}  {'Stby':>5}"
        )
        print(hdr)
        print(thin)
        for i, m in enumerate(r.trade_metrics):
            pair = f"{m.capacity_pair[0]}/{m.capacity_pair[1]}"
            print(
                f"{i + 1:>2}  {m.name:<28}  {pair:>5}  {m.executions:>5}  "
                f"{m.total_production:>5}  {m.total_idle:>5}  "
                f"{100 * m.utilization:>5.1f}%  {m.periods_to_finish:>6}  "
                f"{m.time_on_site:>6}  {m.total_standby_used:>5}"
            )
        print(thin)

        # Buffer maxima
        if r.max_buffer:
            print("  Max WIP (buffer) at each interface:")
            for i, mx in enumerate(r.max_buffer):
                up = cfg.trades[i].name
                down = cfg.trades[i + 1].name
                print(f"    Buffer {i + 1} ({up} → {down}): {mx}")
            print(f"  Peak total WIP (sum of maxes, not simultaneous): "
                  f"{sum(r.max_buffer)}")
            # simultaneous peak from history
            if r.history:
                peak_sim = max(sum(rec.buffers) for rec in r.history)
                print(f"  Peak simultaneous total WIP: {peak_sim}")
        print(sep)

    def export_history_rows(self) -> List[dict]:
        """Flat list of dicts suitable for CSV / pandas."""
        rows: List[dict] = []
        names = [t.name for t in self.config.trades]
        for rec in self.history:
            row: dict = {"period": rec.period, "raw_remaining": rec.raw_remaining}
            for i, name in enumerate(names):
                row[f"cap_{i + 1}"] = rec.capacity[i]
                row[f"prod_{i + 1}"] = rec.production[i]
                row[f"idle_{i + 1}"] = rec.idle_capacity[i]
                row[f"cum_{i + 1}"] = rec.cumulative[i]
                if rec.effective_capacity:
                    row[f"eff_{i + 1}"] = rec.effective_capacity[i]
                if rec.standby_used:
                    row[f"stby_{i + 1}"] = rec.standby_used[i]
            for j, b in enumerate(rec.buffers):
                row[f"buffer_{j + 1}"] = b
            rows.append(row)
        return rows


def tommelein2020_scenarios(
    total_units: int = DEFAULT_TOTAL_UNITS,
    seed: Optional[int] = None,
    staggered: bool = False,
    same_period_handoff: bool = False,
) -> Dict[str, ParadeConfig]:
    """
    The three scenarios from Tommelein (2020) IGLC28:

      S1 classic 4/6
      S2 takted 4/6 + standby 1 to meet takt 5  (≡ production of 5/6 die)
      S3 classic 5/7  (add capacity outright — more variability)
    """
    n = 5
    kw = dict(
        total_units=total_units,
        seed=seed,
        staggered_mobilization=staggered,
        same_period_handoff=same_period_handoff,
    )
    return {
        "S1_classic_4/6": ParadeConfig.from_pairs([(4, 6)] * n, **kw),
        "S2_takt_4/6+stby1": ParadeConfig.from_pairs(
            [(4, 6)] * n, takt_rate=5, standby_capacity=1, **kw
        ),
        "S3_classic_5/7": ParadeConfig.from_pairs([(5, 7)] * n, **kw),
    }


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------

def run_preset(
    preset: Union[str, Sequence[str]] = "medium",
    seed: Optional[int] = 42,
    total_units: int = DEFAULT_TOTAL_UNITS,
    n_trades: int = 5,
    verbose: bool = True,
    takt_rate: Optional[int] = None,
    standby_capacity: int = 0,
    same_period_handoff: bool = False,
    staggered_mobilization: bool = False,
) -> ParadeResult:
    """One-liner: configure, run, optionally print, return result."""
    cfg = ParadeConfig.from_preset(
        preset=preset,
        n_trades=n_trades,
        total_units=total_units,
        seed=seed,
        takt_rate=takt_rate,
        standby_capacity=standby_capacity,
        same_period_handoff=same_period_handoff,
        staggered_mobilization=staggered_mobilization,
    )
    sim = ParadeOfTrades(cfg)
    result = sim.run()
    if verbose:
        sim.print_summary(result)
    return result


# Iris time-inventory buffer experiment (capacity mean fixed at 5)
IRIS_DICE: Dict[str, Tuple[int, int]] = {
    "5-5": (5, 5),
    "4-6": (4, 6),
    "3-7": (3, 7),
}
IRIS_MOBILIZATION: Dict[str, Tuple[int, ...]] = {
    "0-1-2-3-4": (0, 1, 2, 3, 4),
    "0-2-4-6-8": (0, 2, 4, 6, 8),
    "0-3-6-9-12": (0, 3, 6, 9, 12),
}


def run_time_inventory_buffer(
    die: str = "5-5",
    mobilization: str = "0-1-2-3-4",
    total_units: int = DEFAULT_TOTAL_UNITS,
    seed: Optional[int] = 42,
    n_trades: int = 5,
) -> ParadeResult:
    """Classic unit-flow run: fixed mean capacity, time-buffer via start delays."""
    if die not in IRIS_DICE:
        raise ValueError(f"Unknown die '{die}'. Choose from {list(IRIS_DICE)}")
    if mobilization not in IRIS_MOBILIZATION:
        raise ValueError(
            f"Unknown mobilization '{mobilization}'. Choose from {list(IRIS_MOBILIZATION)}"
        )
    lo, hi = IRIS_DICE[die]
    offs = IRIS_MOBILIZATION[mobilization]
    if n_trades != 5:
        step = offs[1] - offs[0] if len(offs) > 1 else 1
        offs = tuple(i * step for i in range(n_trades))
    cfg = ParadeConfig.from_pairs(
        [(lo, hi)] * n_trades,
        total_units=total_units,
        seed=seed,
        same_period_handoff=False,
        mobilization_offsets=offs,
        zone_flow=False,
        batch_size=1,
    )
    return ParadeOfTrades(cfg).run()


def iris_buffer_sweep(
    total_units: int = DEFAULT_TOTAL_UNITS,
    seed: Optional[int] = 42,
) -> List[Dict[str, object]]:
    """3 dice × 3 mobilization patterns (mean capacity fixed)."""
    rows: List[Dict[str, object]] = []
    for die in IRIS_DICE:
        for mob in IRIS_MOBILIZATION:
            r = run_time_inventory_buffer(
                die=die, mobilization=mob, total_units=total_units, seed=seed
            )
            rows.append(
                {
                    "die": die,
                    "mobilization": mob,
                    "label": f"{die} {mob}",
                    "duration": r.duration,
                    "time_on_site": r.total_time_on_site,
                    "inventory_time": r.total_inventory_time,
                    "result": r,
                }
            )
    return rows


def compare_presets(
    presets: Optional[Sequence[str]] = None,
    seed: int = 42,
    total_units: int = DEFAULT_TOTAL_UNITS,
    verbose: bool = True,
) -> Dict[str, ParadeResult]:
    """
    Run several variability presets with the same seed and compare.

    Returns a dict mapping preset name → ParadeResult.
    """
    if presets is None:
        presets = list(CAPACITY_PRESETS.keys())

    results: Dict[str, ParadeResult] = {}
    for p in presets:
        results[p] = run_preset(
            preset=p, seed=seed, total_units=total_units, verbose=False
        )

    if verbose:
        sep = "=" * 72
        print(sep)
        print("PARADE OF TRADES – Preset Comparison")
        print(f"  seed={seed}, total_units={total_units}")
        print(sep)
        hdr = (
            f"{'Preset':<16}  {'Duration':>8}  {'Throughput':>10}  "
            f"{'Idle':>6}  {'MaxWIP':>6}  {'Util(avg)':>9}"
        )
        print(hdr)
        print("-" * 72)
        for p, r in results.items():
            avg_util = (
                sum(m.utilization for m in r.trade_metrics) / len(r.trade_metrics)
            )
            peak_wip = max((sum(h.buffers) for h in r.history), default=0)
            print(
                f"{p:<16}  {r.duration:>8}  {r.system_throughput:>10.3f}  "
                f"{r.total_idle_capacity:>6}  {peak_wip:>6}  {100 * avg_util:>8.1f}%"
            )
        print(sep)

    return results


# ---------------------------------------------------------------------------
# CLI demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    print("\n>>> Demo 1: No variability (5/5) — ideal flow\n")
    run_preset("no_variability", seed=42)

    print("\n>>> Demo 2: Medium variability (3/7)\n")
    run_preset("medium", seed=42)

    print("\n>>> Demo 3: Very high variability (1/9)\n")
    run_preset("very_high", seed=42)

    print("\n>>> Demo 4: Side-by-side preset comparison (same seed)\n")
    compare_presets(seed=42)

    print("\n>>> Demo 5: Mixed variability across trades\n")
    run_preset(
        preset=["no_variability", "low", "medium", "high", "very_high"],
        seed=7,
    )


if __name__ == "__main__":
    _demo()
