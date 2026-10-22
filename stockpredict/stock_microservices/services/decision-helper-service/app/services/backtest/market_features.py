"""Inline market-feature computations for the backtest harness.

The live orchestrator fetches regime / ATR / S/R / swings / RSI via HTTP.
The harness cannot make per-bar HTTP calls, so these functions replicate the
same concepts from raw bars — no I/O, no side effects.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from app.services.signal.base import OHLCVBar


# ---------------------------------------------------------------------------
# Regime (20-bar slope proxy)
# ---------------------------------------------------------------------------

def compute_regime(bars: List[OHLCVBar], fast: int = 20, slow: int = 50) -> str:
    if len(bars) < slow:
        return "UNDEFINED"
    closes = [b.close for b in bars]
    fast_ma = sum(closes[-fast:]) / fast
    slow_ma = sum(closes[-slow:]) / slow
    slope_pct = (fast_ma - slow_ma) / slow_ma if slow_ma else 0
    if slope_pct > 0.01:
        return "TREND_UP"
    if slope_pct < -0.01:
        return "TREND_DOWN"
    return "RANGE"


# ---------------------------------------------------------------------------
# ATR (Wilder's, period = 14)
# ---------------------------------------------------------------------------

def compute_atr(bars: List[OHLCVBar], period: int = 14) -> Optional[float]:
    if len(bars) < period + 1:
        return None
    tr_values: List[float] = []
    for i in range(1, len(bars)):
        h, l, pc = bars[i].high, bars[i].low, bars[i - 1].close
        tr_values.append(max(h - l, abs(h - pc), abs(l - pc)))
    return sum(tr_values[-period:]) / period


# ---------------------------------------------------------------------------
# RSI (simple, period = 14)
# ---------------------------------------------------------------------------

def compute_rsi(bars: List[OHLCVBar], period: int = 14) -> Optional[float]:
    if len(bars) < period + 1:
        return None
    closes = [b.close for b in bars]
    gains = [max(closes[i] - closes[i - 1], 0.0) for i in range(1, len(closes))]
    losses = [max(closes[i - 1] - closes[i], 0.0) for i in range(1, len(closes))]
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100.0 - 100.0 / (1.0 + rs), 2)


# ---------------------------------------------------------------------------
# Swing pivots (needed by stop_module)
# ---------------------------------------------------------------------------

def compute_swings(bars: List[OHLCVBar], window: int = 3) -> List[Dict[str, Any]]:
    pivots: List[Dict[str, Any]] = []
    n = len(bars)
    for i in range(window, n - window):
        hi = bars[i].high
        lo = bars[i].low
        if all(bars[j].high <= hi for j in range(i - window, i + window + 1) if j != i):
            pivots.append({"date": str(bars[i].date), "price": hi, "kind": "HIGH"})
        if all(bars[j].low >= lo for j in range(i - window, i + window + 1) if j != i):
            pivots.append({"date": str(bars[i].date), "price": lo, "kind": "LOW"})
    return pivots[-40:]  # last 40 pivots is enough for stop logic


# ---------------------------------------------------------------------------
# S/R levels (needed by signal engines and stop_module)
# ---------------------------------------------------------------------------

def compute_sr_levels(
    bars: List[OHLCVBar],
    window: int = 10,
    max_levels: int = 5,
) -> Dict[str, Any]:
    """Cluster swing highs → resistances, swing lows → supports."""
    n = len(bars)
    supports: List[Dict[str, Any]] = []
    resistances: List[Dict[str, Any]] = []

    for i in range(window, n - window):
        if all(bars[j].low >= bars[i].low for j in range(i - window, i + window + 1) if j != i):
            supports.append({"price": bars[i].low, "strength": 1})
        if all(bars[j].high <= bars[i].high for j in range(i - window, i + window + 1) if j != i):
            resistances.append({"price": bars[i].high, "strength": 1})

    # Keep only the most recent levels closest to current price
    current = bars[-1].close
    supports_sorted = sorted(supports, key=lambda x: abs(x["price"] - current))[:max_levels]
    resistances_sorted = sorted(resistances, key=lambda x: abs(x["price"] - current))[:max_levels]

    # EM-7 `FR-EM-T1`: each level carries whether it has been broken, which
    # is what makes a throwback entry expressible at all.
    series = atr_series(bars)
    for declared, group in (("support", supports_sorted), ("resistance", resistances_sorted)):
        for lvl in group:
            brk = detect_level_breaks(bars, float(lvl["price"]), role=declared,
                                      atr=series)
            lvl["breaks"] = brk
            lvl["effective_type"] = effective_level_type(declared, brk)
            if brk:
                lvl["broken_at"] = brk[-1]["bar_index"]
                lvl["break_direction"] = brk[-1]["direction"]

    return {"supports": supports_sorted, "resistances": resistances_sorted}


# ---------------------------------------------------------------------------
# EM-7 FR-EM-T1 — levels that remember being broken
# ---------------------------------------------------------------------------
#
# E&M Ch 13: "pattern resistance -- the mechanism explains the patterns."
# A broken support becomes resistance and a broken resistance becomes support,
# so a level has a ROLE and breaking it REVERSES that role.
#
# This is an in-process replica of `analysis-service`'s shipped
# `sr_volume.detect_breaks` (EM-2 `FR-EM-S3`). The duplication is not
# gratuitous: this module exists precisely because "the harness cannot make
# per-bar HTTP calls", and `H-T8` in tests/test_level_breaks.py asserts the
# two agree rather than trusting that they do -- EM-6 D1 found a study's
# private copy of the swing rule wrong on 906 of 5,672 bars.

#: The band a close must clear to count as a decisive penetration, in ATR
#: units. 0.5 is analysis-service's `BREAK_ATR_MULTIPLE`, kept identical so
#: the two never disagree about what "decisive" means. Read in the body, never
#: as a default argument, so a sweep over it is not a silent no-op (EM-1 S2,
#: #78, W1, #84, #87, EM-6 D1/D2 -- the eighth instance of that trap).
BREAK_ATR_MULTIPLE = 0.5

#: Wilder's period, matching analysis-service and `compute_atr` above.
BREAK_ATR_PERIOD = 14


def atr_series(bars: List[OHLCVBar], period: Optional[int] = None) -> List[Optional[float]]:
    """Wilder's ATR as a series aligned to `bars`, causal, warm-up masked.

    Deliberately the same formulation as analysis-service's `trailing_atr` --
    `ewm(alpha=1/period, adjust=False, min_periods=period)` -- so the break
    band means the same thing in both places.

    Note this is NOT `compute_atr` above, which returns a single simple
    average and is consumed by the stop module. Changing that one would alter
    shipped stop behaviour and needs its own measurement, so the two coexist
    and this docstring is the record of why.
    """
    p = BREAK_ATR_PERIOD if period is None else period
    n = len(bars)
    if n == 0 or p <= 0:
        return []

    out: List[Optional[float]] = [None] * n
    # TR[0] has no previous close, so it is the bar's own range -- which is
    # what pandas' max-with-NaN does in the reference implementation.
    tr = bars[0].high - bars[0].low
    ema = tr
    alpha = 1.0 / p
    for i in range(1, n):
        pc = bars[i - 1].close
        tr = max(bars[i].high - bars[i].low,
                 abs(bars[i].high - pc),
                 abs(bars[i].low - pc))
        ema += alpha * (tr - ema)
        if i >= p - 1:
            out[i] = ema
    return out


def detect_level_breaks(
    bars: List[OHLCVBar],
    level_price: float,
    *,
    role: str,
    first_bar: int = 0,
    atr: Optional[Sequence[Optional[float]]] = None,
    atr_multiple: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """Every decisive penetration of `level_price`, in order.

    A penetration is **against the level's current role**, and the role
    **alternates** as the level is broken. A *support* is penetrated when
    price closes decisively BELOW it -- price being above a support is simply
    where price lives, not a break. Once penetrated it acts as resistance, and
    the next thing that counts is a decisive close back ABOVE.

    Without the alternation a support reads as "broken upward" on every
    ordinary rally. EM-2's `S5` shipped that bug and a quiet fixture caught
    it; `H-T4` is that fixture here.

    Staying beyond records ONE break, not one per bar -- which falls out of
    the alternation itself: the same direction cannot fire twice in a row.

    Returns `[]` rather than raising when the frame is too short to form an
    ATR, because a zero or NaN band would make every crossing look infinitely
    decisive.
    """
    multiple = BREAK_ATR_MULTIPLE if atr_multiple is None else atr_multiple
    if not bars or level_price <= 0:
        return []

    series = atr_series(bars) if atr is None else atr
    if len(series) != len(bars):
        return []

    wanted = -1 if role == "support" else 1
    start = max(0, int(first_bar))
    out: List[Dict[str, Any]] = []

    for i in range(start, len(bars)):
        a = series[i]
        if a is None or not (a > 0) or a != a:        # None, <=0, or NaN
            continue
        band = a * multiple
        if band <= 0:
            continue
        close = bars[i].close
        beyond = (close >= level_price + band) if wanted > 0 else (close <= level_price - band)
        if not beyond:
            continue
        out.append({
            "direction": "up" if wanted > 0 else "down",
            "bar_index": i,
            "penetration_atr": round(abs(close - level_price) / a, 4),
        })
        wanted = -wanted                              # the role has flipped
    return out


def effective_level_type(declared: str, breaks: Sequence[Dict[str, Any]]) -> str:
    """The role the break history implies.

    The MOST RECENT penetration decides: broken downward, the level now sits
    above price and acts as resistance; broken upward, it acts as support.
    With no breaks the declared type stands.
    """
    if not breaks:
        return declared
    return "resistance" if breaks[-1]["direction"] == "down" else "support"
