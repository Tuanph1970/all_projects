"""F-200..F-203 — Correlation engine for open positions.

Computes rolling 60-day return correlation between every pair of tickers in
the current user's open position set.  Result is used by two callers:

  1. GET /helper/correlation — visualised on the Risk Dashboard.
  2. /recommend — blocks a BUY/SELL_SHORT when the incoming ticker would push
     any pair above `UserRiskPrefs.max_correlation`.

Price data is fetched from stock-data-service via the existing market client.
Correlation is computed on daily log-returns over the last `window` trading
days (default 60).  Pairs with fewer than `min_obs` overlapping non-NaN
observations are reported as NaN (not enough data) rather than raised.
"""
from __future__ import annotations

import logging
import math
from typing import Dict, List, Optional, Tuple

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

_CORRELATION_LOOKBACK_DAYS = 90   # calendar days fetched (yields ~60 trading days)
_CORRELATION_MIN_OBS = 20         # minimum overlapping observations
_CORRELATION_TIMEOUT = 5.0        # seconds per price fetch


# ── Price fetch ───────────────────────────────────────────────────────────────

async def _fetch_closes(ticker: str, jwt_token: str) -> Optional[List[float]]:
    """Fetch the last ~60 trading days of closing prices for `ticker`.

    Returns a list of floats (oldest first) or None if the upstream call fails.
    """
    cfg = get_settings()
    url = (
        f"{cfg.STOCK_DATA_SERVICE_URL}/stock_helper/api/v2/stocks"
        f"/{ticker}/history?days={_CORRELATION_LOOKBACK_DAYS}"
    )
    headers = {}
    if jwt_token:
        headers["Authorization"] = f"Bearer {jwt_token}"
    try:
        async with httpx.AsyncClient(timeout=_CORRELATION_TIMEOUT) as client:
            resp = await client.get(url, headers=headers)
        if resp.status_code != 200:
            return None
        data = resp.json()
        # history endpoint returns {"data": [{"close": ..., "date": ...}, ...]}
        rows = data.get("data") or data.get("history") or []
        closes = [float(r["close"]) for r in rows if r.get("close") is not None]
        return closes if len(closes) >= 2 else None
    except Exception as exc:  # noqa: BLE001
        logger.warning("correlation: price fetch failed for %s: %s", ticker, exc)
        return None


# ── Return series + correlation math ─────────────────────────────────────────

def _log_returns(closes: List[float]) -> List[Optional[float]]:
    """Convert a price series to daily log-returns.  First element is None
    (no prior bar).  Skips zero or negative prices gracefully."""
    out: List[Optional[float]] = [None]
    for i in range(1, len(closes)):
        p0, p1 = closes[i - 1], closes[i]
        if p0 > 0 and p1 > 0:
            out.append(math.log(p1 / p0))
        else:
            out.append(None)
    return out


def _pearson(rx: List[Optional[float]], ry: List[Optional[float]]) -> Optional[float]:
    """Pearson correlation of two return series aligned by index.

    Returns None when fewer than `_CORRELATION_MIN_OBS` valid pairs exist.
    """
    pairs = [(x, y) for x, y in zip(rx, ry) if x is not None and y is not None]
    n = len(pairs)
    if n < _CORRELATION_MIN_OBS:
        return None

    mx = sum(x for x, _ in pairs) / n
    my = sum(y for _, y in pairs) / n

    cov = sum((x - mx) * (y - my) for x, y in pairs)
    vx = sum((x - mx) ** 2 for x, _ in pairs)
    vy = sum((y - my) ** 2 for _, y in pairs)

    denom = math.sqrt(vx * vy)
    if denom < 1e-12:
        return None
    return round(cov / denom, 4)


# ── Public API ────────────────────────────────────────────────────────────────

async def compute_correlation_matrix(
    tickers: List[str],
    jwt_token: str,
) -> Dict[str, Dict[str, Optional[float]]]:
    """Compute a pairwise correlation matrix for the given tickers.

    Returns a dict-of-dicts: matrix[A][B] == matrix[B][A] == pearson(A, B).
    Diagonal is 1.0.  Missing pairs (insufficient data) are None.
    """
    # Fetch all price series concurrently via individual calls (httpx has no
    # native gather API — we call sequentially but within the timeout budget).
    series: Dict[str, List[Optional[float]]] = {}
    for ticker in tickers:
        closes = await _fetch_closes(ticker, jwt_token)
        if closes:
            series[ticker] = _log_returns(closes)
        else:
            series[ticker] = []

    matrix: Dict[str, Dict[str, Optional[float]]] = {}
    for t in tickers:
        matrix[t] = {}
        for u in tickers:
            if t == u:
                matrix[t][u] = 1.0
            elif u in matrix and t in matrix[u]:
                matrix[t][u] = matrix[u][t]
            else:
                rx, ry = series.get(t, []), series.get(u, [])
                if not rx or not ry:
                    matrix[t][u] = None
                else:
                    # Align to the shorter series (tail-aligned: most-recent bars)
                    min_len = min(len(rx), len(ry))
                    matrix[t][u] = _pearson(rx[-min_len:], ry[-min_len:])

    return matrix


def would_breach_max_correlation(
    matrix: Dict[str, Dict[str, Optional[float]]],
    new_ticker: str,
    max_correlation: float,
) -> Optional[Tuple[str, float]]:
    """Check whether adding `new_ticker` to the portfolio would create a pair
    that exceeds `max_correlation`.

    Returns (existing_ticker, correlation) for the first violating pair, or
    None if no breach occurs (or if data is insufficient for a pair).

    Note: `new_ticker` must already appear in `matrix` (caller builds the
    matrix with the candidate ticker included).
    """
    if new_ticker not in matrix:
        return None
    for other, corr in matrix[new_ticker].items():
        if other == new_ticker:
            continue
        if corr is not None and corr > max_correlation:
            return (other, corr)
    return None
