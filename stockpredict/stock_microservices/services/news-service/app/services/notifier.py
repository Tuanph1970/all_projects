"""services/ Notifier — emits the news.company event (FR-NEWS-NOTIFY, emit side).

Thin wrapper over the stock-common EventBus. Emits a SYMBOL-scoped event with no user
identity (EC-N10); portfolio-service consumes it and fans out per user (N7). Only good/bad
items reach here — the gate lives in the poller (EC-N8).
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from stock_common.events.models import Event

logger = logging.getLogger(__name__)

ROUTING_KEY = "news.company"


class Notifier:
    def __init__(self, bus, *, source_service: str = "news-service"):
        # `bus` is anything with `async publish(event, routing_key=...)` — the stock-common
        # EventBus in prod, a fake in tests.
        self._bus = bus
        self._source = source_service

    async def emit_news_company(
        self,
        *,
        news_id: str,
        symbol: str,
        title: str,
        url: Optional[str],
        ts_utc: datetime,
        sentiment: str,
        category: str,
        sentiment_score: float,
    ) -> None:
        event = Event(
            event_type=ROUTING_KEY,
            payload={
                "news_id": news_id,
                "symbol": symbol,
                "sentiment": sentiment,
                "category": category,
                "title": title,
                "url": url,
                "ts_utc": ts_utc.isoformat() if isinstance(ts_utc, datetime) else ts_utc,
                "sentiment_score": sentiment_score,
            },
        )
        await self._bus.publish(event, routing_key=ROUTING_KEY)
        logger.info("emitted news.company for %s (%s)", symbol, sentiment)
