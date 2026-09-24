"""WatchlistPusher — writes a TCBS call onto the operator's watchlist (FR-BM-CALLS).

The watchlist is per-user and lives in portfolio-service, so this forwards the caller's
own bearer token rather than minting one: the recommendation lands on the watchlist of
whoever pasted the mail, and news-service never holds a credential it could act with on
someone else's behalf.

Resilience follows EC-N7: a push that fails is reported back per symbol and never
unwinds the stored mail. The email is the record; the watchlist row is a convenience
that can be retried.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# What every call pasted from this mail is attributed to on the watch screen.
DEFAULT_PROPOSAL_BY = "TCB"


@dataclass
class PushResult:
    symbol: str
    ok: bool
    reco_id: Optional[int] = None
    error: Optional[str] = None


class WatchlistPusher:
    def __init__(
        self,
        portfolio_url: str,
        *,
        api_prefix: str = "stock_helper",
        client: Optional[httpx.Client] = None,
        timeout: float = 10.0,
    ):
        self._url = portfolio_url.rstrip("/")
        self._prefix = api_prefix
        self._client = client
        self._timeout = timeout

    def push(
        self,
        *,
        symbol: str,
        action: Optional[str],
        label_verbatim: str,
        session_date: date,
        rationale: Optional[str] = None,
        authorization: Optional[str] = None,
        proposal_by: str = DEFAULT_PROPOSAL_BY,
    ) -> PushResult:
        """Upsert one symbol onto the caller's watchlist, carrying the TCBS proposal."""
        url = f"{self._url}/{self._prefix}/api/v2/portfolio/watchlist"
        body = {
            "symbol": symbol.upper(),
            "proposal_by": proposal_by,
            "proposal_action": action,
            "proposal_label": label_verbatim,
            "proposal_date": session_date.isoformat(),
            # The rationale can run to a full paragraph; the column is sized for a note,
            # so send a readable prefix and leave the full text in tcb_news_reco.
            "proposal_note": (rationale or "")[:1000] or None,
        }
        headers = {"Authorization": authorization} if authorization else {}
        client = self._client or httpx.Client(timeout=self._timeout)
        try:
            resp = client.post(url, json=body, headers=headers)
            if resp.status_code >= 400:
                logger.warning("watchlist push %s -> %s %s", symbol, resp.status_code, resp.text[:200])
                return PushResult(symbol=symbol, ok=False,
                                  error=f"portfolio-service returned {resp.status_code}")
            return PushResult(symbol=symbol, ok=True)
        except Exception as exc:  # noqa: BLE001 — log-and-continue (EC-N7)
            logger.warning("watchlist push %s unavailable: %s", symbol, exc)
            return PushResult(symbol=symbol, ok=False, error=str(exc))
        finally:
            if self._client is None:
                client.close()
