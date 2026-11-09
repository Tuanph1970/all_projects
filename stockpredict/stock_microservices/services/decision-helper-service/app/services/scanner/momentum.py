"""FR-SCAN-MOM — multi-horizon momentum, ranked cross-sectionally.

Qullamaggie's Step 1 ranks the universe by "mức tăng trưởng phần trăm lớn nhất"
over 1, 3 and 6 months. Two choices in here are not translations of that and are
worth stating.

HORIZONS ARE TRADING BARS, NOT CALENDAR MONTHS. 21 / 63 / 126 bars. Tết moves
every year and shifts a calendar month's session count by up to a week, so a
calendar window silently measures a different amount of trading depending on
where in the year it falls.

THE COMPOSITE RANKS PERCENTILES, NOT RETURNS. Averaging raw returns lets the
most volatile horizon dominate the score: over 126 bars a VN mid-cap's spread is
several times its 21-bar spread, so a raw mean is a 6-month ranking wearing a
three-horizon label. Ranking each horizon first puts all three on the same
scale, which is the only way the weights mean what they say.

Strictly causal (EC-S1): every function reads a bar sequence that the CALLER has
already cut at the scan date. Nothing in here looks at an index beyond the end
of what it is handed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from app.services.signal.base import OHLCVBar

#: Qullamaggie's 1 / 3 / 6 months, in trading bars.
DEFAULT_HORIZONS: Tuple[int, ...] = (21, 63, 126)

#: Decimals the composite is rounded to FOR ORDERING ONLY — the reported value
#: keeps full precision. See `order_key` for why this exists.
COMPOSITE_ORDERING_DECIMALS = 9


@dataclass(frozen=True)
class MomentumProfile:
    """One symbol's raw returns. `complete` is False when history is too short
    for any requested horizon — such a symbol is excluded from the ranking
    rather than ranked on a subset, because a percentile computed over a
    different horizon set is not comparable with the others."""
    symbol: str
    returns: Mapping[int, Optional[float]]   # lookback -> % return, None if short
    bars_used: int
    complete: bool


@dataclass(frozen=True)
class MomentumRank:
    """A ranked symbol. `ranked_universe` travels WITH the percentiles on
    purpose: a 0.95 over 93 names and a 0.95 over 1,600 are different claims and
    a reader given only the number cannot tell them apart (FR-SCAN-MOM)."""
    symbol: str
    returns: Mapping[int, float]
    percentiles: Mapping[int, float]         # 0..1, 1 = strongest in the universe
    composite: float                         # weighted mean of the percentiles
    ranked_universe: int


def order_key(rank: "MomentumRank") -> Tuple[float, str]:
    """Sort key: strongest composite first, then symbol.

    THE ROUNDING IS WHAT MAKES THE SYMBOL TIE-BREAK REACHABLE, and without it a
    genuine tie is settled by float noise. Measured on live data at 2024-03-31:
    DPG and VHC both scored 0.74329501915708..., differing only in the last
    place — 0.7432950191570881 against 0.7432950191570882. The funnel reading
    bars from a TSV put DPG 8th; the same funnel reading the same bars as JSON
    over HTTP put VHC 8th. The candidate SET was identical both times; only the
    order moved, because one ULP jumped the sort past the symbol clause.

    One ULP is not a disagreement about the market. At n = 88 the finest real
    distinction a percentile can draw is 1/87 — roughly 0.0115, seven orders of
    magnitude coarser than this tolerance, so nothing meaningful is merged. The
    persisted column is DECIMAL(6,4); ordering on more precision than is stored
    would mean the saved rank could not be re-derived from the saved score.
    """
    return (-round(rank.composite, COMPOSITE_ORDERING_DECIMALS), rank.symbol)


def horizon_return(bars: Sequence[OHLCVBar], lookback: int) -> Optional[float]:
    """Percent return of the last bar's close over `lookback` bars.

    Returns None when the window does not contain `lookback + 1` bars, or when
    the reference close is non-positive — a zero/negative price is a data fault,
    and dividing by it would manufacture an enormous return that would then sit
    at the top of the ranking.
    """
    if lookback <= 0:
        raise ValueError(f"lookback must be positive, got {lookback}")
    if len(bars) < lookback + 1:
        return None
    start = float(bars[-1 - lookback].close)
    end = float(bars[-1].close)
    if start <= 0:
        return None
    return (end / start - 1.0) * 100.0


def profile_momentum(
    symbol: str,
    bars: Sequence[OHLCVBar],
    horizons: Sequence[int] = DEFAULT_HORIZONS,
) -> MomentumProfile:
    """Every requested horizon for one symbol, with no ranking."""
    returns: Dict[int, Optional[float]] = {h: horizon_return(bars, h) for h in horizons}
    return MomentumProfile(
        symbol=symbol,
        returns=returns,
        bars_used=len(bars),
        complete=all(v is not None for v in returns.values()),
    )


def _percentiles(values: Mapping[str, float]) -> Dict[str, float]:
    """Cross-sectional percentile in 0..1, ties sharing the average rank.

    Ties matter more than they look: two symbols on identical returns must score
    identically, or the composite would order them by whatever the sort happened
    to do and VT-2 (determinism) would hold only by luck.

    A single-symbol universe has no cross-section, so everything scores 0.5 —
    the neutral reading — rather than 1.0, which would read as "strongest in the
    market" on the evidence of one stock.
    """
    n = len(values)
    if n == 0:
        return {}
    if n == 1:
        return {next(iter(values)): 0.5}

    ordered = sorted(values.items(), key=lambda kv: (kv[1], kv[0]))
    out: Dict[str, float] = {}
    i = 0
    while i < n:
        j = i
        while j + 1 < n and ordered[j + 1][1] == ordered[i][1]:
            j += 1
        shared = (i + j) / 2.0 / (n - 1)
        for k in range(i, j + 1):
            out[ordered[k][0]] = shared
        i = j + 1
    return out


def rank_cross_section(
    profiles: Sequence[MomentumProfile],
    weights: Optional[Mapping[int, float]] = None,
) -> List[MomentumRank]:
    """Rank complete profiles against each other, strongest first.

    Incomplete profiles are dropped here rather than filtered by the caller so
    that `ranked_universe` on every result is exactly the population the
    percentiles were computed over — the number and the thing it describes
    cannot drift apart.

    Ordering is `order_key` — composite desc then symbol asc, with the composite
    rounded before comparison so float noise cannot outrank the tie-break (VT-2).
    """
    complete = [p for p in profiles if p.complete]
    if not complete:
        return []

    horizons = sorted(complete[0].returns)
    for p in complete:
        if sorted(p.returns) != horizons:
            raise ValueError(
                f"{p.symbol} was profiled over {sorted(p.returns)}, the universe over "
                f"{horizons}; percentiles across different horizon sets are not comparable"
            )

    if weights is None:
        weights = {h: 1.0 for h in horizons}
    missing = [h for h in horizons if h not in weights]
    if missing:
        raise ValueError(f"no weight given for horizon(s) {missing}")
    total_w = sum(float(weights[h]) for h in horizons)
    if total_w <= 0:
        raise ValueError("horizon weights must sum to a positive number")

    pct_by_horizon = {
        h: _percentiles({p.symbol: float(p.returns[h]) for p in complete})
        for h in horizons
    }

    ranked = [
        MomentumRank(
            symbol=p.symbol,
            returns={h: float(p.returns[h]) for h in horizons},
            percentiles={h: pct_by_horizon[h][p.symbol] for h in horizons},
            composite=sum(
                pct_by_horizon[h][p.symbol] * float(weights[h]) for h in horizons
            ) / total_w,
            ranked_universe=len(complete),
        )
        for p in complete
    ]
    ranked.sort(key=order_key)
    return ranked
