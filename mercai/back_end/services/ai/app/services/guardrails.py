"""
Feature flags, per-seller quotas, and output post-filters.

These are the enforcement half of docs/ai-features/02-listing-optimizer.md
section 7. The prompt asks the model to behave; this module assumes it did not.
"""
import hashlib
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from shared.cache import cache
from shared.config import settings

logger = logging.getLogger(__name__)

ALLOWLIST_KEY = "mercai:ai:allowlist:{feature}"
QUOTA_HOUR_KEY = "mercai:ai:quota:{feature}:{seller_id}:h"
QUOTA_DAY_KEY = "mercai:ai:quota:{feature}:{seller_id}:d"

_FLAG_SETTINGS = {
    "listing_optimizer": "AI_LISTING_OPTIMIZER_ENABLED",
    "chat_copilot": "AI_CHAT_COPILOT_ENABLED",
    "review_intelligence": "AI_REVIEW_INTELLIGENCE_ENABLED",
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

    prompt_version and model are part of the hash so that shipping a new prompt
    or switching models invalidates every cached suggestion automatically,
    rather than silently serving output from the old configuration.
    """
    blob = json.dumps(
        {"payload": payload, "prompt_version": prompt_version, "model": model},
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Output post-filters
# ---------------------------------------------------------------------------

# Ceramics carry genuine food-safety and lead-glaze considerations. A generated
# assurance here is a real-world harm, not a tone problem, so these are stripped
# regardless of what the seller's own text claims.
SAFETY_CLAIM_PATTERNS = [
    r"\bfood[\s-]?safe\b",
    r"\bfood[\s-]?grade\b",
    r"\bdishwasher[\s-]?safe\b",
    r"\bmicrowave[\s-]?safe\b",
    r"\boven[\s-]?safe\b",
    r"\bfreezer[\s-]?safe\b",
    r"\blead[\s-]?free\b",
    r"\bnon[\s-]?toxic\b",
    r"\bFDA[\s-]?approved\b",
]

# The optimizer must never touch commercial terms.
COMMERCIAL_CLAIM_PATTERNS = [
    r"\bfree shipping\b",
    r"\bdiscount\b",
    r"\b\d+%\s*off\b",
    r"\bsale price\b",
    r"\bmoney[\s-]?back guarantee\b",
    r"\brefund\b",
]

_SAFETY_RE = re.compile("|".join(SAFETY_CLAIM_PATTERNS), re.IGNORECASE)
_COMMERCIAL_RE = re.compile("|".join(COMMERCIAL_CLAIM_PATTERNS), re.IGNORECASE)


def find_blocked_claims(text: Optional[str]) -> List[str]:
    """Return the claims that must not appear in generated copy."""
    if not text:
        return []
    found = [m.group(0) for m in _SAFETY_RE.finditer(text)]
    found += [m.group(0) for m in _COMMERCIAL_RE.finditer(text)]
    return found


def strip_blocked_sentences(text: Optional[str]) -> Tuple[Optional[str], List[str]]:
    """
    Remove whole sentences containing a blocked claim.

    Sentence-level rather than word-level: deleting "food safe" from "This bowl
    is food safe" leaves "This bowl is", which reads as a bug and could still
    imply the claim. Dropping the sentence is the honest edit.
    """
    if not text:
        return text, []

    blocked = find_blocked_claims(text)
    if not blocked:
        return text, []

    sentences = re.split(r"(?<=[.!?])\s+", text)
    kept = [s for s in sentences if not find_blocked_claims(s)]
    cleaned = " ".join(kept).strip()
    return (cleaned or None), blocked

# ---------------------------------------------------------------------------
# Unsupported-claim detection (flag, not block)
# ---------------------------------------------------------------------------
#
# Two different problems need two different responses:
#
#   BLOCK  safety and commercial claims (above). Wrong ones cause real harm,
#          and no seller benefits from being asked about them.
#   FLAG   properties, uses and aesthetics the seller never mentioned. These
#          are usually fine and often true -- the seller just did not write
#          them down. Measured rate is roughly 1 in 4 on a near-empty listing
#          and near zero on a complete one, so blocking would fire mostly on
#          false positives and mangle legitimate rewording.
#
# Only the seller knows whether the bowl really is for everyday use, so the
# guard surfaces the sentence and lets them keep or cut it.
#
# This word set is not a guess: it is the denylist validated against a live
# model on 2026-08-19, which caught "crafted for everyday use" while ignoring
# connectives like "standing at 24cm" and "a capacity of 300ml".
# See docs/ai-features/02-listing-optimizer.md section 8b.

CLAIM_MARKERS = frozenset("""
everyday daily perfect ideal great beautiful stunning gorgeous lovely
elegant rustic modern minimalist contemporary traditional cozy warm inviting
charming unique special exquisite timeless
gift gifting present occasion wedding birthday housewarming christmas
kitchen dining table tableware coffee tea breakfast dinner lunch morning
evening serving centerpiece decor decorative display
durable sturdy robust hardy delicate fragile lightweight heavy
smooth matte glossy satin textured rough polished glazed glaze finish
sleek luxurious premium exclusive artisanal handcrafted bespoke heirloom
comfortable ergonomic versatile practical functional
""".split())


def _sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text or "") if s.strip()]


def _stem(word):
    """
    Crude suffix stripper, on purpose.

    The seller writing "glazed" and the model writing "glaze" is the same
    claim; exact matching would flag it as invented and teach sellers to
    ignore the warnings. A real stemmer is not worth a dependency here -- this
    only has to collapse the handful of endings that show up in product copy.
    """
    for suffix in ("ing", "ed", "es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            word = word[: -len(suffix)]
            break
    return word[:-1] if word.endswith("e") and len(word) > 3 else word


def _content_words(text):
    return {w for w in re.split(r"\W+", (text or "").lower()) if len(w) > 3}


def _content_stems(text):
    return {_stem(w) for w in _content_words(text)}


def find_unsupported_claims(text, supporting_text):
    """
    Return [{"sentence": str, "claims": [str, ...]}] for sentences asserting a
    property, use or quality absent from the seller's own text.

    Deliberately narrow. Connectives and measurement framing ("standing at
    24cm", "a capacity of 300ml") assert nothing new and are ignored, because
    an earlier naive "any unseen word" check flagged them and made the signal
    useless.
    """
    if not text:
        return []

    supported = _content_stems(supporting_text)
    findings = []

    for sentence in _sentences(text):
        claims = sorted(
            word
            for word in _content_words(sentence) & CLAIM_MARKERS
            if _stem(word) not in supported
        )
        if claims:
            findings.append({"sentence": sentence, "claims": claims})

    return findings
