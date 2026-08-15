"""Usage counters for Parade Tim Kerja (no personal data).

Shared namespace so landing (Vercel) and Streamlit app show the same totals.
Primary store: public Counter API. Fallback: local JSON (ephemeral on Cloud).
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, Optional

NS = "parade-tim-kerja.app"
API = "https://counterapi.com/api"
TIMEOUT = 3.5

# Counter keys (shared with landing JS)
KEY_LANDING_VISITS = "landing_visits"
KEY_LANDING_UNIQUE = "landing_unique"
KEY_APP_VISITS = "app_visits"
KEY_APP_SESSIONS = "app_sessions"
KEY_SIM_RUNS = "sim_runs"
KEY_COMPARE_RUNS = "compare_runs"

ALL_KEYS = (
    KEY_LANDING_VISITS,
    KEY_LANDING_UNIQUE,
    KEY_APP_VISITS,
    KEY_APP_SESSIONS,
    KEY_SIM_RUNS,
    KEY_COMPARE_RUNS,
)

_LOCAL = Path(__file__).resolve().parent / "output" / "usage_stats.json"


def _url(key: str, *, read_only: bool) -> str:
    q = urllib.parse.urlencode({"readOnly": "true"}) if read_only else ""
    base = f"{API}/{NS}/view/{urllib.parse.quote(key, safe='')}"
    return f"{base}?{q}" if q else base


def _parse_value(raw: bytes) -> Optional[int]:
    try:
        data = json.loads(raw.decode("utf-8"))
        if isinstance(data, dict) and "value" in data:
            return int(data["value"])
    except (ValueError, TypeError, UnicodeDecodeError):
        return None
    return None


def _http_get(url: str) -> Optional[int]:
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "ParadeTimKerja/1"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return _parse_value(resp.read())
    except (urllib.error.URLError, TimeoutError, OSError):
        return None


def _local_load() -> Dict[str, int]:
    if not _LOCAL.exists():
        return {k: 0 for k in ALL_KEYS}
    try:
        data = json.loads(_LOCAL.read_text(encoding="utf-8"))
        return {k: int(data.get(k, 0) or 0) for k in ALL_KEYS}
    except (OSError, ValueError, TypeError):
        return {k: 0 for k in ALL_KEYS}


def _local_save(data: Dict[str, int]) -> None:
    try:
        _LOCAL.parent.mkdir(parents=True, exist_ok=True)
        _LOCAL.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError:
        pass


def increment(key: str) -> int:
    """Increment a counter; return new value (best-effort)."""
    if key not in ALL_KEYS:
        raise ValueError(key)
    remote = _http_get(_url(key, read_only=False))
    local = _local_load()
    if remote is not None:
        local[key] = max(int(remote), int(local.get(key, 0)))
        _local_save(local)
        return int(local[key])
    local[key] = int(local.get(key, 0)) + 1
    _local_save(local)
    return int(local[key])


def read_all() -> Dict[str, int]:
    """Read all counters (remote preferred, merged with local)."""
    local = _local_load()
    out: Dict[str, int] = {}
    for k in ALL_KEYS:
        remote = _http_get(_url(k, read_only=True))
        if remote is not None:
            out[k] = max(int(remote), int(local.get(k, 0)))
        else:
            out[k] = int(local.get(k, 0))
    return out


def totals(stats: Optional[Dict[str, int]] = None) -> Dict[str, int]:
    s = stats if stats is not None else read_all()
    sim = int(s.get(KEY_SIM_RUNS, 0))
    cmp_ = int(s.get(KEY_COMPARE_RUNS, 0))
    return {
        **s,
        "total_simulations": sim + cmp_,
        "total_visits": int(s.get(KEY_LANDING_VISITS, 0)) + int(s.get(KEY_APP_VISITS, 0)),
    }
