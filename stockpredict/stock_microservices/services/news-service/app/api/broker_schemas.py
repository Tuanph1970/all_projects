"""Response models for broker-mail intake, phase E1 (FR-BM-INTAKE).

Nothing here carries message content. EC-B8 makes TCBS research subscriber material that
may be stored and shown to the operator but never republished through the application's
surfaces, so intake reports *counts and timestamps only* — no bodies, no subjects. The
raw archive is reachable from the database by someone with database access, which is the
intended audience for it.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class IntakeRunResponse(BaseModel):
    """What one intake pass did (POST /news/broker/poll)."""

    considered: int = Field(description="Messages the mailbox offered for the window")
    captured: int = Field(description="Newly stored (FR-BM-DEDUP: first sighting)")
    duplicates: int = Field(description="Already held — a no-op, not an error")
    rejected: int = Field(description="Failed the sender allow-list (EC-B1); ignored")
    errors: int = Field(description="Messages skipped individually; the batch continued")
    failed: bool = Field(description="The pass itself could not run (network/auth)")
    detail: str = Field(default="", description="Why it could not run, when failed")
    senders_rejected: list[str] = Field(
        default_factory=list,
        description="Distinct rejected senders, capped — so a misdirected forward "
                    "rule is diagnosable without exposing any message content",
    )


class IntakeStatsResponse(BaseModel):
    """The E1 phase gate as numbers: a week of mail landing, zero duplicates, history
    backfilled. `stored == distinct_message_ids` is the zero-duplicates assertion."""

    enabled: bool = Field(description="ENABLE_EMAIL — is the scheduled loop wanted")
    configured: bool = Field(description="Is the ingestion mailbox addressable at all")
    stored: int
    distinct_message_ids: int
    earliest_received: Optional[datetime] = None
    latest_received: Optional[datetime] = None
    unextracted: int = Field(description="Captured but not yet parsed — E2's queue")
