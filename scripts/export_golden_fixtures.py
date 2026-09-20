#!/usr/bin/env python3
"""Export golden JSON fixtures from Python engine for JS parity tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from parade_of_trades_core import (  # noqa: E402
    DEFAULT_TRADE_NAMES,
    ParadeConfig,
    ParadeOfTrades,
    TradeConfig,
)

OUT = ROOT / "web" / "fixtures"


def _trade(name: str, speed: float) -> TradeConfig:
    return TradeConfig(
        name=name,
        low=speed,
        high=speed,
        deterministic=True,
        base_speed=speed,
    )


def _run(batch: int, speed: float, n: int, seed: int = 12345) -> dict:
    trades = [_trade(DEFAULT_TRADE_NAMES[i], speed) for i in range(5)]
    cfg = ParadeConfig(
        trades=trades,
        total_units=n,
        seed=seed,
        zone_flow=True,
        batch_size=batch,
    )
    r = ParadeOfTrades(cfg).run()
    return {
        "meta": {
            "zone_flow": True,
            "batch_size": batch,
            "base_speed": speed,
            "total_units": n,
            "seed": seed,
            "deterministic": True,
        },
        "duration": r.duration,
        "ideal_duration": r.ideal_duration,
        "system_throughput": r.system_throughput,
        "max_buffer": list(r.max_buffer),
        "starts": [m.start_period for m in r.trade_metrics],
        "finishes": [m.periods_to_finish for m in r.trade_metrics],
        "cumulative": r.cumulative_series(),
        "buffers": r.buffer_series(),
        "ideal_last_trade_cumulative": list(r.ideal_last_trade_cumulative),
        "production_history": [list(h.production) for h in r.history],
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    cases = [
        ("zf_novar_batch1_z10", dict(batch=1, speed=1.0, n=10)),
        ("zf_novar_batch4_z10", dict(batch=4, speed=1.0, n=10)),
        ("zf_novar_batch1_speed05_z6", dict(batch=1, speed=0.5, n=6)),
    ]
    index = []
    for name, kw in cases:
        data = _run(**kw)
        path = OUT / f"{name}.json"
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        index.append({"name": name, "file": path.name, "duration": data["duration"]})
        print(f"wrote {path} duration={data['duration']} ideal={data['ideal_duration']}")
    (OUT / "index.json").write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
