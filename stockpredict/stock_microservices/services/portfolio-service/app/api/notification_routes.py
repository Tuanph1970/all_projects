"""User-facing notification endpoints.

The producer side (event consumer) lives in
app/services/notification_consumer.py — it persists
portfolio.alert.triggered events into the notifications table. These
endpoints are the read/dismiss surface the frontend bell-icon uses.
"""
import json
import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db
from app.models.domain import Notification
from app.models.schemas import (
    MarkReadResponse,
    NotificationListResponse,
    NotificationResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _to_response(n: Notification) -> NotificationResponse:
    metadata = None
    if n.metadata_json:
        try:
            metadata = json.loads(n.metadata_json)
        except (TypeError, ValueError):
            metadata = None
    return NotificationResponse(
        id=n.id,
        type=n.type.value,
        title=n.title,
        body=n.body,
        metadata=metadata,
        read=n.read_at is not None,
        created_at=n.created_at,
        read_at=n.read_at,
    )


@router.get("/notifications", response_model=NotificationListResponse)
async def list_notifications(
    unread_only: bool = Query(False, description="Return only unread notifications"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List notifications for the current user, newest first.

    The total + unread counts always reflect the user's full set so the
    frontend can render a "5 unread" badge even when paging.
    """
    user_id = current_user["user_id"]

    where = [Notification.user_id == user_id]
    if unread_only:
        where.append(Notification.read_at.is_(None))

    rows_q = (
        select(Notification)
        .where(*where)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .limit(limit)
        .offset(offset)
    )
    rows_result = await db.execute(rows_q)
    items = rows_result.scalars().all()

    total = (
        await db.execute(
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == user_id)
        )
    ).scalar_one()
    unread = (
        await db.execute(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.read_at.is_(None),
            )
        )
    ).scalar_one()

    return NotificationListResponse(
        items=[_to_response(n) for n in items],
        total=total,
        unread=unread,
    )


@router.post("/notifications/{notif_id}/read", response_model=NotificationResponse)
async def mark_read(
    notif_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Mark a single notification as read.
    Returns 404 if the notification belongs to another user.
    """
    user_id = current_user["user_id"]

    result = await db.execute(
        select(Notification).where(
            Notification.id == notif_id,
            Notification.user_id == user_id,
        )
    )
    notif = result.scalar_one_or_none()
    if notif is None:
        raise HTTPException(status_code=404, detail="Notification not found")

    if notif.read_at is None:
        notif.read_at = datetime.utcnow()
        await db.commit()
        await db.refresh(notif)

    return _to_response(notif)


@router.post("/notifications/read-all", response_model=MarkReadResponse)
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Mark every unread notification for the current user as read."""
    user_id = current_user["user_id"]
    now = datetime.utcnow()
    result = await db.execute(
        update(Notification)
        .where(
            Notification.user_id == user_id,
            Notification.read_at.is_(None),
        )
        .values(read_at=now)
    )
    await db.commit()
    return MarkReadResponse(updated=result.rowcount or 0)


@router.delete(
    "/notifications/{notif_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_notification(
    notif_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Delete a single notification."""
    user_id = current_user["user_id"]
    result = await db.execute(
        select(Notification).where(
            Notification.id == notif_id,
            Notification.user_id == user_id,
        )
    )
    notif = result.scalar_one_or_none()
    if notif is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    await db.delete(notif)
    await db.commit()
