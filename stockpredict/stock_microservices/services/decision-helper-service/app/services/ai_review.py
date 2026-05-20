"""F-190..F-193 — AI trade review generator.

Calls ai-insights-service POST /ai/ask to produce a short post-mortem when
a trade outcome is tagged.  Runs as a fire-and-forget background task;
failures are silently logged and never block the recommendation response.

Internal ai-insights API base:
    http://ai-insights-service:8005/stock_helper/api/v2/ai
"""
from __future__ import annotations

import logging
from typing import Optional

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

_AI_PREFIX = "/stock_helper/api/v2/ai"
_TIMEOUT_S = 15.0   # LLM inference can be slow


def _base() -> str:
    return get_settings().AI_INSIGHTS_SERVICE_URL + _AI_PREFIX


def _headers(jwt_token: str) -> dict:
    return {"Authorization": f"Bearer {jwt_token}", "Content-Type": "application/json"}


def _build_prompt(
    ticker: str,
    direction: str,        # LONG | SHORT
    signal_kind: Optional[str],
    regime: Optional[str],
    entry_price: Optional[float],
    stop_price: Optional[float],
    exit_price: Optional[float],
    outcome: Optional[str],
    r_multiple: Optional[float],
    bar_date: str,
    discipline_violations: Optional[list] = None,
) -> str:
    r_str = f"{r_multiple:+.2f}R" if r_multiple is not None else "unknown R"
    outcome_str = outcome or "UNKNOWN"
    violations_str = (
        ", ".join(discipline_violations) if discipline_violations else "none"
    )

    return (
        f"Provide a brief trade post-mortem (3-4 sentences) for this completed trade: "
        f"{ticker} {direction} entered {bar_date}. "
        f"Signal: {signal_kind or 'unknown'} in {regime or 'unknown'} regime. "
        f"Entry {entry_price or '?'}, stop {stop_price or '?'}, exit {exit_price or '?'}. "
        f"Result: {outcome_str} ({r_str}). "
        f"Discipline violations: {violations_str}. "
        f"Was the setup valid? Were trend-following rules respected? What is the key lesson?"
    )


async def generate_trade_review(
    ticker: str,
    direction: str,
    signal_kind: Optional[str],
    regime: Optional[str],
    entry_price: Optional[float],
    stop_price: Optional[float],
    exit_price: Optional[float],
    outcome: Optional[str],
    r_multiple: Optional[float],
    bar_date: str,
    jwt_token: str,
    discipline_violations: Optional[list] = None,
) -> Optional[str]:
    """Call ai-insights /ask and return the review text, or None on failure."""
    question = _build_prompt(
        ticker=ticker,
        direction=direction,
        signal_kind=signal_kind,
        regime=regime,
        entry_price=entry_price,
        stop_price=stop_price,
        exit_price=exit_price,
        outcome=outcome,
        r_multiple=r_multiple,
        bar_date=bar_date,
        discipline_violations=discipline_violations,
    )
    payload = {
        "question": question[:500],  # schema max_length=500
        "context": "trading performance review",
        "symbols": [ticker],
    }
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_S) as client:
            resp = await client.post(
                f"{_base()}/ask",
                json=payload,
                headers=_headers(jwt_token),
            )
            resp.raise_for_status()
            data = resp.json()
            review = data.get("answer", "").strip()
            if review:
                logger.info("ai_review: generated review for %s/%s", ticker, outcome)
                return review[:2000]
    except Exception as exc:
        logger.warning("ai_review: failed for %s: %s", ticker, exc)
    return None
