"""Pydantic request/response models for the news read API (FR-NEWS-API)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class IngestRequest(BaseModel):
    """Manual ingest of one item — goes through the same dedup+store path as the poller
    (classification/notification then happen on the next poll tick, Phase B)."""
    source: str
    stream: str = "company"
    symbol: Optional[str] = None
    ts_utc: datetime
    title: str
    body: Optional[str] = None
    url: Optional[str] = None
    lang: Optional[str] = None
    raw_json: Optional[str] = None
    guid: Optional[str] = None


class IngestResponse(BaseModel):
    news_id: str
    stored: bool  # True iff newly inserted (False = already seen, EC-N2)
