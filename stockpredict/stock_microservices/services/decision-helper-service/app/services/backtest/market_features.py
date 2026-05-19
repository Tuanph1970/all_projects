"""Inline market-feature computations for the backtest harness.

The live orchestrator fetches regime / ATR / S/R / swings / RSI via HTTP.
The harness cannot make per-bar HTTP calls, so these functions replicate the
same concepts from raw bars — no I/O, no side effects.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

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

    return {"supports": supports_sorted, "resistances": resistances_sorted}
