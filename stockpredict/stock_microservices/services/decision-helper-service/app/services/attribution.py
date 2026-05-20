"""F-210..F-213 — Performance attribution engine.

Breaks down tagged trade outcomes (WIN / LOSS / BREAKEVEN) across four
dimensions so the trader can see where their edge lives and where it
doesn't:

  by_signal       — MA_CROSS, BREAKOUT, STOCH_REVERSAL, …
  by_regime       — TREND_UP, TREND_DOWN, RANGE, UNDEFINED
  by_weekday      — Monday … Friday (entry bar weekday)
  by_hold_duration — 1d · 2-3d · 4-7d · 8-14d · 15d+

All computations are done in Python over the small result set returned by
the DB query; no GROUP BY SQL to keep the implementation testable without a
live database.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Dict, List, Optional, Tuple

_WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


# ---------------------------------------------------------------------------
# Hold-duration bucketing
# ---------------------------------------------------------------------------

def _hold_bucket(entry_date: date, exit_date: Optional[date]) -> str:
    if exit_date is None or entry_date is None:
        return "unknown"
    days = max(0, (exit_date - entry_date).days)
    if days <= 1:
        return "1d"
    if days <= 3:
        return "2-3d"
    if days <= 7:
        return "4-7d"
    if days <= 14:
        return "8-14d"
    return "15d+"


_HOLD_ORDER = ["1d", "2-3d", "4-7d", "8-14d", "15d+", "unknown"]


# ---------------------------------------------------------------------------
# Core aggregation
# ---------------------------------------------------------------------------

def _stats(outcomes: List[Tuple[str, Optional[float]]]) -> dict:
    """Compute win_rate, avg_r, expectancy from a list of (outcome, r_multiple)."""
    total = len(outcomes)
    if total == 0:
        return {"count": 0, "wins": 0, "losses": 0, "breakevens": 0,
                "win_rate": 0.0, "avg_r": None, "expectancy": None}

    wins = sum(1 for o, _ in outcomes if o == "WIN")
    losses = sum(1 for o, _ in outcomes if o == "LOSS")
    beven = sum(1 for o, _ in outcomes if o == "BREAKEVEN")

    rs = [r for _, r in outcomes if r is not None]
    avg_r = round(sum(rs) / len(rs), 4) if rs else None
    expectancy = avg_r  # per-trade expectancy = avg_r when we have a symmetric sample

    return {
        "count": total,
        "wins": wins,
        "losses": losses,
        "breakevens": beven,
        "win_rate": round(wins / total, 4),
        "avg_r": avg_r,
        "expectancy": expectancy,
    }


def compute_attribution(
    records: List[dict],  # dicts with keys: outcome, r_multiple, signal_kind, regime, bar_date, exit_bar_date
) -> dict:
    """Group records by each dimension and return attribution buckets.

    Each record must have:
        outcome        : "WIN" | "LOSS" | "BREAKEVEN"
        r_multiple     : float | None
        signal_kind    : str | None
        regime         : str | None
        bar_date       : date
        exit_bar_date  : date | None
    """
    by_signal: Dict[str, List] = defaultdict(list)
    by_regime: Dict[str, List] = defaultdict(list)
    by_weekday: Dict[str, List] = defaultdict(list)
    by_hold: Dict[str, List] = defaultdict(list)

    for rec in records:
        pair = (rec["outcome"], rec.get("r_multiple"))

        sig = rec.get("signal_kind") or "UNKNOWN"
        by_signal[sig].append(pair)

        reg = rec.get("regime") or "UNDEFINED"
        by_regime[reg].append(pair)

        bd = rec.get("bar_date")
        wd = _WEEKDAY_NAMES[bd.weekday()] if bd else "Unknown"
        by_weekday[wd].append(pair)

        bucket = _hold_bucket(rec.get("bar_date"), rec.get("exit_bar_date"))
        by_hold[bucket].append(pair)

    def _rows(groups: Dict[str, List], order: Optional[List[str]] = None) -> List[dict]:
        keys = order if order else sorted(groups.keys())
        result = []
        for k in keys:
            if k not in groups:
                continue
            s = _stats(groups[k])
            result.append({"label": k, **s})
        # append any keys not in the order list
        if order:
            for k in sorted(groups.keys()):
                if k not in order:
                    s = _stats(groups[k])
                    result.append({"label": k, **s})
        return result

    weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

    return {
        "by_signal": _rows(by_signal),
        "by_regime": _rows(by_regime),
        "by_weekday": _rows(by_weekday, weekday_order),
        "by_hold_duration": _rows(by_hold, _HOLD_ORDER),
    }
