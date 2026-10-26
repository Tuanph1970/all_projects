"""Routes for broker-mail intake, phase E1 (FR-BM-INTAKE, FR-BM-BACKFILL).

Two operator endpoints and nothing else, because E1 captures and does not parse:

    POST /news/broker/poll      force an intake tick; `since` makes it the backfill
    GET  /news/broker/intake    how much is captured, over what span (the E1 gate)

The read deliberately returns counts and timestamps only — never a subject or a body
(EC-B8). The one-shot backfill of FR-BM-BACKFILL is this same POST with `since`, rather
than a separate command, so there is one code path to be idempotent and one to trust.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.broker_schemas import IntakeRunResponse, IntakeStatsResponse
from app.config import get_settings
from app.deps import get_broker_mail_repo, get_broker_mail_source

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


@router.post("/broker/poll", response_model=IntakeRunResponse,
             summary="Capture broker mail now — with `since`, the one-shot backfill")
async def poll_broker_mail(
    since: Optional[date] = Query(
        default=None,
        description="Walk the mailbox from this date (FR-BM-BACKFILL). Omit for the "
                    "normal recent window. Idempotent either way — re-running captures "
                    "nothing it already holds.",
    ),
    source=Depends(get_broker_mail_source),
):
    """Never returns an error for a mailbox problem.

    A 5xx here would say "the service is broken" when the truth is "the mailbox was
    unreachable this minute", and the operator's next move differs completely between
    those two. An unreachable mailbox comes back 200 with `failed: true` and a reason —
    including "not configured", which the mailbox factory reports as itself rather than
    letting imaplib dial an empty host and hand back a misleading "Connection refused".
    """
    if since is not None:
        return source.backfill(since=since)
    return await source.tick()


@router.get("/broker/intake", response_model=IntakeStatsResponse,
            summary="Intake state — the E1 phase gate as numbers")
def broker_intake_stats(repo=Depends(get_broker_mail_repo)):
    """`stored == distinct_message_ids` is the zero-duplicates check the E1 gate asks
    for; `earliest_received` answers whether the history backfill actually ran."""
    stats = repo.stats()
    return IntakeStatsResponse(
        enabled=settings.ENABLE_EMAIL,
        configured=settings.broker_mail_configured,
        **stats,
    )
