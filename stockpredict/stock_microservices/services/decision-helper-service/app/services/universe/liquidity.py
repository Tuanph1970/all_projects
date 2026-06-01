"""s1_universe — Liquidity filter helper (Schwager Ch 16: market selection).

Pre-screens a ticker's recent OHLCV history for tradeable liquidity before the
decision pipeline spends work on it.  ``assess_liquidity`` is a pure function
over an ``OHLCVBar`` sequence and is strictly causal: it reads only the most
recent ``lookback`` bars, so it can be called with whatever history is
available at decision time.

``screen_watchlist`` is the async integration seam used by the daily scheduler:
it fetches a short window per ticker and returns a per-ticker verdict.  The
filter is opt-in — when both thresholds are 0 the caller should skip screening
entirely (see ``filter_enabled``) so behaviour is unchanged by default.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence

from app.services.signal.base import OHLCVBar

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LiquidityResult:
    ticker: str
    avg_daily_value: float     # mean(close * volume) over the lookback window
    avg_daily_volume: float    # mean(volume) over the lookback window
    lookback: int              # number of bars actually used
    passed: bool
    reason: str


def filter_enabled(min_avg_value: float, min_avg_volume: float) -> bool:
    """True when at least one liquidity threshold is configured (> 0)."""
    return min_avg_value > 0 or min_avg_volume > 0


def assess_liquidity(
    bars: Sequence[OHLCVBar],
    *,
    ticker: str = "",
    lookback: int = 20,
    min_avg_value: float = 0.0,
    min_avg_volume: float = 0.0,
) -> LiquidityResult:
    """Judge whether ``ticker`` is liquid enough to trade.

    Uses only the most recent ``lookback`` bars.  A series with fewer than
    ``lookback`` bars fails conservatively — we would rather skip a thinly
    observed name than recommend on unreliable averages.
    """
    window = list(bars)[-lookback:] if lookback > 0 else list(bars)
    n = len(window)
    if n == 0:
        return LiquidityResult(ticker, 0.0, 0.0, 0, False, "no bars")

    avg_value = sum(b.close * b.volume for b in window) / n
    avg_volume = sum(b.volume for b in window) / n

    if lookback > 0 and n < lookback:
        return LiquidityResult(
            ticker, avg_value, avg_volume, n, False,
            f"insufficient history ({n}/{lookback} bars)",
        )
    if avg_value < min_avg_value:
        return LiquidityResult(
            ticker, avg_value, avg_volume, n, False,
            f"avg value {avg_value:,.0f} < min {min_avg_value:,.0f}",
        )
    if avg_volume < min_avg_volume:
        return LiquidityResult(
            ticker, avg_value, avg_volume, n, False,
            f"avg volume {avg_volume:,.0f} < min {min_avg_volume:,.0f}",
        )

    return LiquidityResult(ticker, avg_value, avg_volume, n, True, "ok")


async def screen_watchlist(
    client: Any,
    tickers: Sequence[str],
    *,
    lookback: int = 20,
    min_avg_value: float = 0.0,
    min_avg_volume: float = 0.0,
    end_date: Any = None,
) -> Dict[str, LiquidityResult]:
    """Assess each ticker's liquidity via ``client.fetch_ohlcv``.

    Fetches a window comfortably larger than ``lookback`` (to absorb non-trading
    days) and returns ``{ticker: LiquidityResult}``.  Never raises — a fetch
    failure surfaces as a non-passing result for that ticker.
    """
    fetch_days = max(lookback * 2, 40)
    results: Dict[str, LiquidityResult] = {}
    for ticker in tickers:
        try:
            raw = await client.fetch_ohlcv(ticker, days=fetch_days, end_date=end_date)
            bars = [OHLCVBar.from_dict(b) for b in raw]
        except Exception as exc:  # defensive: screening must not break the run
            logger.warning("liquidity screen fetch failed for %s: %s", ticker, exc)
            bars = []
        results[ticker] = assess_liquidity(
            bars, ticker=ticker, lookback=lookback,
            min_avg_value=min_avg_value, min_avg_volume=min_avg_volume,
        )
    return results
