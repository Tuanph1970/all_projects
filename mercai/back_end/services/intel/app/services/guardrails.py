"""
Feature flags, per-seller quotas, and input hashing.

Everything here is model-agnostic, which is why it survived the removal of the
Ollama client -- it governs *whether a seller may run an expensive operation*,
not what the operation is. Price intelligence reuses it unchanged.

The generated-copy post-filters that used to live here (find_blocked_claims,
strip_blocked_sentences, find_unsupported_claims) went with the listing
optimizer: they only ever made sense against text a model wrote. See
docs/ai-features/05-price-intelligence.md section 2.1.
"""
import hashlib
import json
import logging
from typing import Any, Dict, Optional, Tuple

from shared.cache import cache
from shared.config import settings

logger = logging.getLogger(__name__)

ALLOWLIST_KEY = "mercai:intel:allowlist:{feature}"
QUOTA_HOUR_KEY = "mercai:intel:quota:{feature}:{seller_id}:h"
QUOTA_DAY_KEY = "mercai:intel:quota:{feature}:{seller_id}:d"

_FLAG_SETTINGS = {
    "price_intel": "INTEL_PRICE_ENABLED",
}


# ---------------------------------------------------------------------------
# Feature flags
# ---------------------------------------------------------------------------

def feature_enabled(feature: str, seller_id: Optional[int] = None) -> bool:
    """
    Two-stage flag: a global env-var kill switch, then an optional per-seller
    Redis allowlist for staged rollout.

    An EMPTY allowlist means "everyone", not "no one" -- otherwise flipping the
    global flag on would appear to do nothing and invite someone to remove the
    check entirely.
    """
    setting_name = _FLAG_SETTINGS.get(feature)
    if setting_name is None or not getattr(settings, setting_name, False):
        return False

    if seller_id is None:
        return True

    try:
        client = cache.client
        if client is None:
            return True  # Redis down: fall back to the global flag alone.
        key = ALLOWLIST_KEY.format(feature=feature)
        if not client.exists(key):
            return True
        return bool(client.sismember(key, str(seller_id)))
    except Exception:
        logger.warning("Allowlist check failed; falling back to global flag", exc_info=True)
        return True


# ---------------------------------------------------------------------------
# Quotas
# ---------------------------------------------------------------------------

def check_quota(feature: str, seller_id: int) -> Tuple[bool, Optional[int]]:
    """
    Returns (allowed, retry_after_seconds).

    Fails OPEN when Redis is unavailable: a cache outage should degrade cost
    control, not block sellers from a working feature.
    """
    client = cache.client
    if client is None:
        return True, None

    try:
        hour_key = QUOTA_HOUR_KEY.format(feature=feature, seller_id=seller_id)
        day_key = QUOTA_DAY_KEY.format(feature=feature, seller_id=seller_id)

        hour_used = int(client.get(hour_key) or 0)
        if hour_used >= settings.AI_QUOTA_PER_HOUR:
            return False, int(client.ttl(hour_key) or 3600)

        day_used = int(client.get(day_key) or 0)
        if day_used >= settings.AI_QUOTA_PER_DAY:
            return False, int(client.ttl(day_key) or 86400)

        return True, None
    except Exception:
        logger.warning("Quota check failed; allowing request", exc_info=True)
        return True, None


def consume_quota(feature: str, seller_id: int) -> None:
    """Count one generation. Only called on a real model call, not a cache hit."""
    client = cache.client
    if client is None:
        return
    try:
        for key, ttl in (
            (QUOTA_HOUR_KEY.format(feature=feature, seller_id=seller_id), 3600),
            (QUOTA_DAY_KEY.format(feature=feature, seller_id=seller_id), 86400),
        ):
            if client.incr(key) == 1:
                client.expire(key, ttl)
    except Exception:
        logger.warning("Quota increment failed", exc_info=True)


# ---------------------------------------------------------------------------
# Input hashing
# ---------------------------------------------------------------------------

def input_hash(payload: Dict[str, Any], prompt_version: str, model: str) -> str:
    """
    Stable hash of the generation input.

    The two version fields are part of the hash so that changing how a result
    is produced invalidates every cached entry automatically, rather than
    silently serving output from the old configuration. For price intelligence
    these carry the ruleset version and the literal string "rules"; they kept
    their original names because `ai_suggestions` still uses those columns.
    """
    blob = json.dumps(
        {"payload": payload, "prompt_version": prompt_version, "model": model},
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()
