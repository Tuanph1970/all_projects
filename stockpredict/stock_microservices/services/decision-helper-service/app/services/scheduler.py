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
from app.config import get_settings
from app.models.domain import HelperWatchlist
from app.services.alert_broker import alert_broker
from app.services.decision.orchestrator import run_recommendation
from app.services.market.client import get_market_client
from app.services.universe.liquidity import filter_enabled, screen_watchlist

logger = logging.getLogger(__name__)

_ALERT_ACTIONS = {"BUY", "SELL_SHORT"}


async def run_for_user(user_id: int, bar_date: date | None = None) -> None:
    """Run scheduled recommendations for one user's entire watchlist.

    When the liquidity filter is configured (s1_universe), illiquid tickers are
    pre-screened out before the pipeline runs, saving work and avoiding
    recommendations on thinly-traded names.
    """
    today = bar_date or date.today()
    client = get_market_client()
    settings = get_settings()

    async with async_session_factory() as session:
        result = await session.execute(
            select(HelperWatchlist).where(
                HelperWatchlist.user_id == user_id,
                HelperWatchlist.active.is_(True),
            )
        )
        entries = result.scalars().all()

    # ── s1_universe: liquidity pre-screen (opt-in) ───────────────────────
    if filter_enabled(settings.MIN_AVG_DAILY_VALUE, settings.MIN_AVG_DAILY_VOLUME):
        verdicts = await screen_watchlist(
            client,
            [e.ticker for e in entries],
            lookback=settings.LIQUIDITY_LOOKBACK_DAYS,
            min_avg_value=settings.MIN_AVG_DAILY_VALUE,
            min_avg_volume=settings.MIN_AVG_DAILY_VOLUME,
            end_date=today,
        )
        kept = []
        for entry in entries:
            v = verdicts.get(entry.ticker)
            if v is not None and not v.passed:
                logger.info(
                    "Liquidity filter skipped [user=%d ticker=%s]: %s",
                    user_id, entry.ticker, v.reason,
                )
                continue
            kept.append(entry)
        entries = kept

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
                await alert_broker.publish(user_id, {
                    "ticker": entry.ticker,
                    "action": rec.action,
                    "bar_date": str(today),
                    "regime": rec.regime,
                    "confidence": rec.confidence,
                    "stop_price": rec.stop_price,
                    "target_price": rec.target_price,
                })
            elif getattr(rec, "exit_reason", None) in ("STOP_HIT", "TARGET_HIT"):
                # decision.stop.triggered / decision.target.hit — a tracked
                # position closed on its stop or target; notify the user.
                logger.info(
                    "EXIT ALERT [user=%d ticker=%s date=%s action=%s reason=%s]",
                    user_id, entry.ticker, today, rec.action, rec.exit_reason,
                )
                await alert_broker.publish(user_id, {
                    "ticker": entry.ticker,
                    "action": rec.action,
                    "bar_date": str(today),
                    "exit_reason": rec.exit_reason,
                    "regime": rec.regime,
                    "confidence": rec.confidence,
                    "stop_price": rec.stop_price,
                    "target_price": rec.target_price,
                })
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


# ---------------------------------------------------------------------------
# FR-SCAN-SCHED — nightly momentum scan (S-3)
# ---------------------------------------------------------------------------

async def run_momentum_scan_job(bar_date: date | None = None) -> None:
    """One market-wide discovery scan per trading day, persisted.

    SEQUENCED AFTER THE RECOMMENDATION RUN, NOT BEFORE. Both read
    stock-data-service, and that service's own nightly price refresh and
    Backlog #119 seam sweep run earlier still — scanning before the sweep would
    rank a universe whose seams have not yet been repaired, and a seam distorts
    a 126-bar return for six months (SRS 2.4).

    The VT-4 null rate is computed here and stored on the run, because C4/EC-S5
    require the candidate list to be reported beside it and the nightly job is
    the one place that can afford the work (SRS 12.4). It costs seconds.

    Failure is logged and swallowed: a scan is a daily convenience, and killing
    the scheduler would also stop the recommendation job that users depend on.
    """
    from app.services.scanner.runner import run_momentum_scan

    today = bar_date or date.today()
    try:
        async with async_session_factory() as session:
            report, run = await run_momentum_scan(
                session, get_market_client(),
                as_of=today, trigger="SCHEDULED", with_null_fpr=True,
            )
        logger.info(
            "Momentum scan %s: %d candidates from %d ranked of %d universe",
            today, len(report.candidates), report.ranked_universe,
            report.universe_total,
        )
        if not report.candidates:
            # An empty list is a VALID output of this method (#135). Logged as
            # INFO with its reason so a quiet screen is never mistaken for a
            # broken pipeline — the mistake that gets a working filter loosened.
            logger.info(
                "Momentum scan %s found nothing: %s", today, report.accounting()
            )
    except Exception as exc:
        logger.warning("Momentum scan failed for %s: %s", today, exc, exc_info=True)
