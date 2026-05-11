"""Browser web-push delivery for portfolio-service notifications.

Sends VAPID-signed push messages to browser endpoints (FCM, Mozilla
autopush, Apple push) via pywebpush. The actual encryption happens
inside pywebpush in a worker thread.

Same shape as email_service / format_alert_email so push payloads stay
aligned with the bell-icon and email channels — users see the same
wording everywhere.

Dev fallback: when VAPID_PRIVATE_KEY is unset we log the would-be
payload instead of sending. Keeps local dev unblocked without VAPID
keys provisioned.
"""
import asyncio
import json
import logging
from typing import Iterable, Optional

from app.config import get_settings

logger = logging.getLogger(__name__)

# Standard expiry codes the push services return when a subscription is
# dead (user uninstalled the browser, revoked permission, etc.) — callers
# delete the row on these codes so we don't keep retrying.
EXPIRED_STATUS_CODES = frozenset({404, 410})


def format_alert_push(payload: dict) -> dict:
    """Build the JSON payload the service worker will receive.

    Keep the keys deliberately small/explicit — the service worker reads
    {title, body, tag, data} to build a Notification. tag dedupes
    duplicate notifications for the same alert at the browser level.
    """
    symbol = payload.get("symbol", "?")
    alert_type = payload.get("alert_type", "")
    target_price = payload.get("target_price")
    target_percent = payload.get("target_percent")
    trigger_price = payload.get("trigger_price")

    if alert_type == "above":
        title = f"{symbol} crossed above {target_price}"
        body = f"Price reached {trigger_price}, hitting your above-{target_price} alert."
    elif alert_type == "below":
        title = f"{symbol} crossed below {target_price}"
        body = f"Price dropped to {trigger_price}, hitting your below-{target_price} alert."
    elif alert_type == "change_percent":
        title = f"{symbol} moved {target_percent}%+"
        body = f"Price hit {trigger_price} — change exceeded {target_percent}%."
    else:
        title = f"Alert triggered for {symbol}"
        body = f"Price hit {trigger_price}."

    return {
        "title": title,
        "body": body,
        # Same alert_id → same tag → browser collapses repeated notifs.
        "tag": f"alert-{payload.get('alert_id', symbol)}",
        "data": {
            "alert_id": payload.get("alert_id"),
            "symbol": symbol,
            "trigger_price": trigger_price,
        },
    }


def _send_sync(subscription_info: dict, payload_json: str, vapid_private_key: str, vapid_subject: str):
    """Run the actual pywebpush call. Imported lazily so unit tests that
    monkeypatch send_push_to_subscription don't need the library."""
    from pywebpush import webpush  # type: ignore

    return webpush(
        subscription_info=subscription_info,
        data=payload_json,
        vapid_private_key=vapid_private_key,
        vapid_claims={"sub": vapid_subject},
    )


async def send_push_to_subscription(
    *,
    endpoint: str,
    p256dh: str,
    auth: str,
    payload: dict,
) -> tuple[bool, Optional[int]]:
    """Deliver a push payload to one browser subscription.

    Returns (delivered, status_code). status_code is None on success or
    on local dev-fallback; populated on HTTP failure so callers can
    decide whether to delete an expired subscription (404/410).
    """
    settings = get_settings()
    if not settings.VAPID_PRIVATE_KEY:
        logger.warning(
            "VAPID not configured (VAPID_PRIVATE_KEY unset); push to %s skipped.",
            endpoint,
        )
        logger.info("Push body (would-be sent): %s", payload)
        return False, None

    subscription_info = {
        "endpoint": endpoint,
        "keys": {"p256dh": p256dh, "auth": auth},
    }
    payload_json = json.dumps(payload)

    try:
        await asyncio.to_thread(
            _send_sync,
            subscription_info,
            payload_json,
            settings.VAPID_PRIVATE_KEY,
            settings.VAPID_SUBJECT,
        )
        logger.info("Sent push to %s", endpoint)
        return True, None
    except Exception as e:
        status_code = getattr(getattr(e, "response", None), "status_code", None)
        logger.warning(
            "Push send failed for %s (status=%s): %s", endpoint, status_code, e
        )
        return False, status_code


async def send_push_to_subscriptions(
    subscriptions: Iterable,
    payload: dict,
) -> list[tuple[int, bool, Optional[int]]]:
    """Fan out a push payload to every subscription for one user.

    Each subscription is a row from PushSubscription (or a dict-like
    object with .id / .endpoint / .p256dh_key / .auth_key — duck-typed
    so tests can use simple namespaces).

    Returns a list of (subscription_id, delivered, status_code) tuples
    so callers can prune expired rows.
    """
    results: list[tuple[int, bool, Optional[int]]] = []
    for sub in subscriptions:
        delivered, status = await send_push_to_subscription(
            endpoint=sub.endpoint,
            p256dh=sub.p256dh_key,
            auth=sub.auth_key,
            payload=payload,
        )
        results.append((sub.id, delivered, status))
    return results
