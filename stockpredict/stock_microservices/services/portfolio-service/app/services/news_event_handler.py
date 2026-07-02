"""Consume news.company events and fan them out to affected users (FR-NEWS-NOTIFY).

news-service emits a SYMBOL-scoped `news.company` event (no user identity — EC-N10).
This consumer owns the user↔ticker mapping: it resolves every user who owns or watches
the symbol and creates one in-app Notification per user, deduped by (user_id, news_id) so
a DLQ retry / republish never double-inserts (EC-N2). When SMTP is configured it also
emails each newly-notified user, reusing the existing email service.

Best-effort and idempotent, mirroring the alert consumers: RabbitMQ unavailable at boot
returns None (service still serves CRUD); handler errors are logged, not raised.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select

from stock_common.config import RabbitMQConfig
from stock_common.events import Event, EventBus

from app.api.dependencies import async_session_factory  # type: ignore
from app.config import get_settings
from app.models.domain import Notification, NotificationType
from app.repositories.portfolio_repository import PortfolioRepository
from app.services.email_consumer import _lookup_user_email
from app.services.email_service import send_email

logger = logging.getLogger(__name__)

NEWS_COMPANY_EVENT = "news.company"

_event_bus: Optional[EventBus] = None


async def start_news_consumer(service_name: str = "portfolio-service") -> Optional[EventBus]:
    """Subscribe to news.company. Returns None on RabbitMQ failure rather than
    blocking boot (the CRUD API and other consumers are unaffected)."""
    global _event_bus
    try:
        bus = EventBus(RabbitMQConfig(), service_name=service_name)
        await bus.connect()
        await bus.subscribe(
            event_pattern=NEWS_COMPANY_EVENT,
            handler=_handle_news_company,
            queue_name=f"{service_name}.notifications.news_company",
            durable=True,
        )
        _event_bus = bus
        logger.info("News consumer subscribed to %s", NEWS_COMPANY_EVENT)
        return bus
    except Exception as e:  # noqa: BLE001
        logger.warning("Could not start news consumer (RabbitMQ unavailable?): %s", e)
        _event_bus = None
        return None


async def stop_news_consumer() -> None:
    global _event_bus
    if _event_bus is not None:
        try:
            await _event_bus.disconnect()
        except Exception as e:  # noqa: BLE001
            logger.warning("News consumer disconnect raised: %s", e)
        _event_bus = None


def _format_news(payload: dict) -> tuple[str, str, dict]:
    symbol = payload.get("symbol", "?")
    sentiment = payload.get("sentiment", "")
    category = payload.get("category", "other")
    headline = payload.get("title", "")
    tone = {"good": "Good", "bad": "Bad"}.get(sentiment, "").strip()
    title = f"{tone} news for {symbol}".strip() if tone else f"News for {symbol}"
    body = headline or f"New {category} news for {symbol}."
    meta = {
        "symbol": symbol,
        "sentiment": sentiment,
        "category": category,
        "url": payload.get("url"),
        "sentiment_score": payload.get("sentiment_score"),
        "news_id": payload.get("news_id"),
    }
    return title, body, meta


def _email_enabled() -> bool:
    return bool(getattr(get_settings(), "SMTP_HOST", None))


async def _handle_news_company(event: Event) -> None:
    """Fan one news.company event out to per-user notifications (+ optional email)."""
    payload = event.payload or {}
    symbol = payload.get("symbol")
    news_id = payload.get("news_id")
    if not symbol or not news_id:
        logger.debug("Skipping news.company with no symbol/news_id: %s", payload)
        return

    title, body, meta = _format_news(payload)
    meta_json = json.dumps(meta)
    new_user_ids: list[int] = []

    try:
        async with async_session_factory() as session:
            repo = PortfolioRepository(session)
            user_ids = await repo.get_user_ids_for_symbol(symbol)
            if not user_ids:
                return
            for uid in user_ids:
                existing = await session.execute(
                    select(Notification.id).where(
                        Notification.source_event_id == news_id,
                        Notification.user_id == uid,
                    )
                )
                if existing.scalar_one_or_none() is not None:
                    continue  # per-user dedup (EC-N2)
                session.add(
                    Notification(
                        user_id=uid,
                        type=NotificationType.NEWS_COMPANY,
                        title=title,
                        body=body,
                        metadata_json=meta_json,
                        source_event_id=news_id,
                        created_at=datetime.utcnow(),
                    )
                )
                new_user_ids.append(uid)
            await session.commit()
            logger.info(
                "news.company %s fanned to %d user(s) (%d new)",
                news_id, len(user_ids), len(new_user_ids),
            )
    except Exception as e:  # noqa: BLE001 — never nack into the DLQ
        logger.error("Error persisting news notifications for %s: %s", news_id, e)
        return

    # Email only the users we just notified (so a republish doesn't re-email), and only
    # when SMTP is configured (EC-N9). Best-effort per user.
    if not (_email_enabled() and new_user_ids):
        return
    subject = title
    for uid in new_user_ids:
        try:
            email = await _lookup_user_email(uid)
            if not email:
                continue
            url = meta.get("url") or ""
            text_body = f"{body}\n\n{url}".strip()
            html_body = f"<p>{body}</p>" + (f'<p><a href="{url}">{url}</a></p>' if url else "")
            await send_email(to_email=email, subject=subject, text_body=text_body, html_body=html_body)
        except Exception as e:  # noqa: BLE001
            logger.warning("news email failed for user %s: %s", uid, e)
