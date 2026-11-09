"""FR-SCAN-TREND — the trend template.

Qullamaggie's setup context: *"nằm trên các đường trung bình động lớn như MA50 và
MA200... tốt nhất là đã tăng từ 30% - 100% trước đó"*. Four clauses.

EVERY CLAUSE IS REPORTED, PASS OR FAIL. The template could return one boolean;
it does not, because the whole operational value of a scanner is explaining why
a name you expected is absent. A symbol one percent under its MA200 and a symbol
in a downtrend both fail — collapsing them to False throws away the only
difference that matters to the person reading the list (NFR-S3).

Strictly causal (EC-S1): reads only the bars it is handed, which the caller has
already cut at the scan date.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from app.services.signal.base import OHLCVBar

#: The long averages the setup is defined against.
SMA_FAST = 50
SMA_SLOW = 200

#: "đã tăng từ 30% - 100% trước đó" — the floor only. The upper end is not a
#: rejection: a name up 150% in six months is not disqualified by the method,
#: it is simply more extended, and FR-SCAN-BASE (S-2) is what judges that.
DEFAULT_MIN_PRIOR_ADVANCE_PCT = 30.0

#: Window the prior advance is measured over — the same 126 bars as the longest
#: momentum horizon, so "the advance" and "the 6-month return" describe the same
#: stretch of history rather than two overlapping ones.
DEFAULT_ADVANCE_LOOKBACK = 126


@dataclass(frozen=True)
class TrendClause:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class TrendTemplate:
    symbol: str
    passed: bool
    clauses: Tuple[TrendClause, ...]
    close: Optional[float]
    sma_fast: Optional[float]
    sma_slow: Optional[float]
    prior_advance_pct: Optional[float]
    advance_low: Optional[float]

    def failed_clauses(self) -> Tuple[str, ...]:
        return tuple(c.name for c in self.clauses if not c.passed)


def sma_at(bars: Sequence[OHLCVBar], period: int) -> Optional[float]:
    """The simple moving average on the LAST bar handed in, or None during
    warm-up. Same definition as `signal.base._sma`, evaluated at one point —
    duplicated as a value rather than imported as a private, and kept to one
    line so the two cannot disagree."""
    if period <= 0:
        raise ValueError(f"period must be positive, got {period}")
    if len(bars) < period:
        return None
    return sum(float(b.close) for b in bars[-period:]) / period


def required_bars(
    advance_lookback: int = DEFAULT_ADVANCE_LOOKBACK,
    sma_slow: int = SMA_SLOW,
) -> int:
    """Bars needed before the template can be evaluated at all.

    SMA200 is the binding constraint, and it binds harder than the SRS's
    `MIN_BARS = 150` default suggests: a universe admitted at 150 bars would
    fail `close_above_sma200` for want of history, not for want of trend, and
    the exclusion would be invisible in the counts. The scanner therefore takes
    the max of the two rather than trusting the configured floor.
    """
    return max(sma_slow, advance_lookback + 1)


def assess_trend(
    symbol: str,
    bars: Sequence[OHLCVBar],
    *,
    min_prior_advance_pct: float = DEFAULT_MIN_PRIOR_ADVANCE_PCT,
    advance_lookback: int = DEFAULT_ADVANCE_LOOKBACK,
) -> TrendTemplate:
    """Evaluate the four clauses at the last bar handed in."""
    clauses: List[TrendClause] = []

    need = required_bars(advance_lookback)
    if len(bars) < need:
        clauses.append(TrendClause(
            "sufficient_history", False,
            f"{len(bars)} bars, need {need} (SMA{SMA_SLOW} / {advance_lookback}-bar advance)",
        ))
        return TrendTemplate(symbol, False, tuple(clauses), None, None, None, None, None)

    close = float(bars[-1].close)
    fast = sma_at(bars, SMA_FAST)
    slow = sma_at(bars, SMA_SLOW)
    assert fast is not None and slow is not None  # guaranteed by `need` above

    window = bars[-advance_lookback:]
    low = min(float(b.close) for b in window)
    advance = (close / low - 1.0) * 100.0 if low > 0 else None

    clauses.append(TrendClause(
        "close_above_sma50", close > fast, f"close {close:.2f} vs SMA50 {fast:.2f}"))
    clauses.append(TrendClause(
        "close_above_sma200", close > slow, f"close {close:.2f} vs SMA200 {slow:.2f}"))
    clauses.append(TrendClause(
        "sma50_above_sma200", fast > slow, f"SMA50 {fast:.2f} vs SMA200 {slow:.2f}"))
    clauses.append(TrendClause(
        "prior_advance",
        advance is not None and advance >= min_prior_advance_pct,
        f"{advance:.1f}% off the {advance_lookback}-bar low {low:.2f}, need {min_prior_advance_pct:.0f}%"
        if advance is not None else f"non-positive {advance_lookback}-bar low",
    ))

    return TrendTemplate(
        symbol=symbol,
        passed=all(c.passed for c in clauses),
        clauses=tuple(clauses),
        close=close,
        sma_fast=fast,
        sma_slow=slow,
        prior_advance_pct=advance,
        advance_low=low,
    )
