"""Push-subscription management endpoints.

The frontend registers a service worker, asks the browser for a
PushSubscription, then POSTs the (endpoint, keys) tuple here. The
push_consumer reads from this table when an alert fires.

Endpoints are mounted under /portfolio/push so the public URLs are:
  GET    /stock_helper/api/v2/portfolio/push/vapid-public-key
  POST   /stock_helper/api/v2/portfolio/push/subscribe
  DELETE /stock_helper/api/v2/portfolio/push/subscribe
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db
from app.config import get_settings
from app.models.domain import PushSubscription
from app.models.schemas import (
    PushSubscriptionCreate,
    PushSubscriptionResponse,
    VapidPublicKeyResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/push/vapid-public-key", response_model=VapidPublicKeyResponse)
async def get_vapid_public_key():
    """Return the VAPID public key so the frontend can pass it to
    PushManager.subscribe(). Public by design — there's nothing secret
    about a VAPID public key.

    503 if VAPID isn't configured for this deployment; the frontend
    should disable the push toggle in that case.
    """
    settings = get_settings()
    if not settings.VAPID_PUBLIC_KEY:
        raise HTTPException(
            status_code=503, detail="Web push is not configured on this server"
        )
    return VapidPublicKeyResponse(public_key=settings.VAPID_PUBLIC_KEY)


@router.post(
    "/push/subscribe",
    response_model=PushSubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def subscribe_push(
    body: PushSubscriptionCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Register (or refresh) a browser push subscription for the current user.

    Endpoint is unique — re-POSTing from the same browser updates the
    keys + ownership rather than creating a duplicate row. This is the
    expected flow when a user logs into a different account in the same
    browser.
    """
    user_id = current_user["user_id"]

    existing = (
        await db.execute(
            select(PushSubscription).where(
                PushSubscription.endpoint == body.endpoint
            )
        )
    ).scalar_one_or_none()

    user_agent = body.user_agent or request.headers.get("user-agent")

    if existing is not None:
        existing.user_id = user_id
        existing.p256dh_key = body.keys.p256dh
        existing.auth_key = body.keys.auth
        if user_agent:
            existing.user_agent = user_agent[:255]
        await db.commit()
        await db.refresh(existing)
        return existing

    sub = PushSubscription(
        user_id=user_id,
        endpoint=body.endpoint,
        p256dh_key=body.keys.p256dh,
        auth_key=body.keys.auth,
        user_agent=(user_agent or "")[:255] or None,
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    return sub


@router.delete(
    "/push/subscribe",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def unsubscribe_push(
    endpoint: str = Query(..., max_length=500),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Remove a browser push subscription.

    Scoped to the current user so one user can't drop another user's
    subscriptions even if they somehow learned the endpoint URL.
    """
    user_id = current_user["user_id"]
    await db.execute(
        delete(PushSubscription).where(
            PushSubscription.endpoint == endpoint,
            PushSubscription.user_id == user_id,
        )
    )
    await db.commit()
