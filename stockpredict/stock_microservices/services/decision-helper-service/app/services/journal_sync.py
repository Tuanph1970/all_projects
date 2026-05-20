"""F-170..F-173 — Journal-service sync client.

Fires-and-forgets trade creation/closure to journal-service when the
decision engine opens or closes a position.  All failures are silently
logged — journal sync NEVER blocks a recommendation response.

Internal journal API base:
    http://journal-service:8008/stock_helper/api/v2/journal
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Optional

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

_JOURNAL_PREFIX = "/stock_helper/api/v2/journal"


def _base() -> str:
    return get_settings().JOURNAL_SERVICE_URL + _JOURNAL_PREFIX


def _timeout() -> float:
    return get_settings().JOURNAL_SYNC_TIMEOUT_S


def _headers(jwt_token: str) -> dict:
    return {"Authorization": f"Bearer {jwt_token}", "Content-Type": "application/json"}


# ---------------------------------------------------------------------------
# Account discovery
# ---------------------------------------------------------------------------

async def get_first_account_id(jwt_token: str) -> Optional[int]:
    """Return the id of the user's first journal account, or None on any error."""
    try:
        async with httpx.AsyncClient(timeout=_timeout()) as client:
            resp = await client.get(
                f"{_base()}/accounts",
                headers=_headers(jwt_token),
            )
            resp.raise_for_status()
            accounts = resp.json()
            if isinstance(accounts, list) and accounts:
                return accounts[0].get("id")
            if isinstance(accounts, dict):
                items = accounts.get("accounts") or accounts.get("items") or []
                if items:
                    return items[0].get("id")
    except Exception as exc:
        logger.debug("journal_sync: get_first_account_id failed: %s", exc)
    return None


# ---------------------------------------------------------------------------
# Trade open
# ---------------------------------------------------------------------------

async def open_journal_trade(
    account_id: int,
    jwt_token: str,
    ticker: str,
    direction: str,           # "LONG" | "SHORT" (decision-helper convention)
    entry_date: date,
    entry_price: float,
    initial_stop: float,
    position_size: int,
    signal_kind: Optional[str] = None,
) -> Optional[int]:
    """Create a journal trade and return its id, or None on failure."""
    journal_direction = "Long" if direction == "LONG" else "Short"
    payload = {
        "entry_date": str(entry_date),
        "market_ticker": ticker,
        "direction": journal_direction,
        "entry_price": entry_price,
        "entry_type": "Market",
        "initial_stop": initial_stop,
        "position_size": float(position_size),
        "commission": 0.0,
        "entry_reason": f"Auto-sync from decision-helper ({signal_kind or 'signal'})",
    }
    try:
        async with httpx.AsyncClient(timeout=_timeout()) as client:
            resp = await client.post(
                f"{_base()}/accounts/{account_id}/trades",
                json=payload,
                headers=_headers(jwt_token),
            )
            resp.raise_for_status()
            data = resp.json()
            trade_id = data.get("id")
            logger.info(
                "journal_sync: opened trade %s for %s/%s (account=%s)",
                trade_id, ticker, entry_date, account_id,
            )
            return trade_id
    except Exception as exc:
        logger.warning("journal_sync: open_journal_trade failed for %s: %s", ticker, exc)
        return None


# ---------------------------------------------------------------------------
# Trade close
# ---------------------------------------------------------------------------

async def close_journal_trade(
    account_id: int,
    journal_trade_id: int,
    jwt_token: str,
    exit_price: float,
    exit_date: date,
    outcome: Optional[str] = None,
) -> bool:
    """Close a journal trade by id.  Returns True on success."""
    reason = f"Auto-sync: {outcome}" if outcome else "Auto-sync: position closed"
    try:
        async with httpx.AsyncClient(timeout=_timeout()) as client:
            resp = await client.post(
                f"{_base()}/accounts/{account_id}/trades/{journal_trade_id}/close",
                params={
                    "exit_price": exit_price,
                    "exit_date": str(exit_date),
                    "exit_reason": reason,
                },
                headers=_headers(jwt_token),
            )
            resp.raise_for_status()
            logger.info(
                "journal_sync: closed trade %s (account=%s, exit=%.4f)",
                journal_trade_id, account_id, exit_price,
            )
            return True
    except Exception as exc:
        logger.warning(
            "journal_sync: close_journal_trade %s failed: %s", journal_trade_id, exc
        )
        return False
