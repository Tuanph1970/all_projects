"""F-071 — Daily recommendation scheduler.

Fires after VN market close (08:30 UTC = 15:30 ICT) for every active
HelperWatchlist entry.  Also exposed as `run_for_user()` so the
POST /watchlist/run-all endpoint can trigger a manual run.
"""
from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import async_session_factory
from app.models.domain import HelperWatchlist
from app.services.decision.orchestrator import run_recommendation
from app.services.market.client import get_market_client

logger = logging.getLogger(__name__)

_ALERT_ACTIONS = {"BUY", "SELL_SHORT"}


async def run_for_user(user_id: int, bar_date: date | None = None) -> None:
    """Run scheduled recommendations for one user's entire watchlist."""
    today = bar_date or date.today()
    client = get_market_client()

    async with async_session_factory() as session:
        result = await session.execute(
            select(HelperWatchlist).where(
                HelperWatchlist.user_id == user_id,
                HelperWatchlist.active.is_(True),
            )
        )
        entries = result.scalars().all()

    for entry in entries:
        try:
            async with async_session_factory() as session:
                rec = await run_recommendation(
                    user_id=user_id,
                    ticker=entry.ticker,
                    bar_date=today,
                    trigger="SCHEDULED",
                    db=session,
                    client=client,
                )
            if rec.action in _ALERT_ACTIONS:
                logger.info(
                    "ALERT [user=%d ticker=%s date=%s action=%s]",
                    user_id, entry.ticker, today, rec.action,
                )
        except Exception as exc:
            logger.warning(
                "Scheduled run skipped [user=%d ticker=%s]: %s",
                user_id, entry.ticker, exc,
            )


async def run_all_users(bar_date: date | None = None) -> None:
    """Run scheduled recommendations for ALL active watchlist entries."""
    today = bar_date or date.today()
    client = get_market_client()  # noqa: F841 — warm up connection pool

    async with async_session_factory() as session:
        result = await session.execute(
            select(HelperWatchlist.user_id).where(
                HelperWatchlist.active.is_(True)
            ).distinct()
        )
        user_ids = list(result.scalars().all())

    logger.info("Scheduled daily run for %d users on %s", len(user_ids), today)
    for uid in user_ids:
        try:
            await run_for_user(uid, bar_date=today)
        except Exception as exc:
            logger.error("Scheduler failed for user=%d: %s", uid, exc)
