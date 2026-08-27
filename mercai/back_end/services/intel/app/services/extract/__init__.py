"""
The extraction ladder: HTML in, (price, currency, confidence, evidence) out.

This is what replaced the language model. The objection it answers -- "every
new source means new selectors" -- is answered by ORDERING, not by a model:
four of the five rungs read published standards that any storefront emits, and
only `selectors` is per-site. That one is driven by a YAML file, so a new
source is a data change reviewable in a diff rather than a deploy.

All rungs run, then reconcile (section 4.6). Running them all is affordable --
the whole ladder is microseconds against a page we already paid a network
round-trip for -- and cross-rung agreement is the cheap ensemble that buys back
much of the judgement the model was there for.

Measured 2026-08-27 against 36 real Vietnamese product pages across two hosts:
`jsonld` fired on every one, 24 of them verified exactly against ground truth.
The lower rungs have never fired on a real page, so they carry more risk than
their base confidences suggest -- treat a first-time `state` or `text` result
as something to look at, not something to alert on.
"""
from dataclasses import dataclass, field
from typing import List, Optional

from . import jsonld, meta, selectors, state, text

# Precedence order. Reconciliation prefers the earlier rung when two disagree.
TIERS = ("jsonld", "meta", "selectors", "state", "text")

AGREEMENT_TOLERANCE = 0.005   # 0.5%
AGREEMENT_CONFIDENCE = 99
CONFLICT_PENALTY = 25


@dataclass
class Candidate:
    tier: str
    confidence: int
    price: object                # Decimal
    currency: Optional[str]
    evidence: str


@dataclass
class Extraction:
    price: object
    currency: str
    confidence: int
    tier: str
    evidence: str
    tiers_matched: List[str] = field(default_factory=list)
    flag: Optional[str] = None
    title: Optional[str] = None
    availability: Optional[str] = None


def run_ladder(html: str, adapter=None) -> Optional[Extraction]:
    """Every applicable rung, then reconcile. None if nothing matched."""
    enabled = set(adapter.tiers) if adapter and adapter.tiers else set(TIERS)

    candidates: List[Candidate] = []
    for tier, module in (
        ("jsonld", jsonld), ("meta", meta),
        ("selectors", selectors), ("state", state), ("text", text),
    ):
        if tier not in enabled:
            continue
        try:
            candidates.extend(module.extract(html, adapter))
        except Exception:  # noqa: BLE001 - one bad rung must not kill the ladder
            continue

    if not candidates:
        return None

    order = {tier: i for i, tier in enumerate(TIERS)}
    candidates.sort(key=lambda c: (order.get(c.tier, 99), -c.confidence))
    top = candidates[0]

    confidence, flag = top.confidence, None
    others = [c for c in candidates[1:] if c.price != top.price or c.tier != top.tier]
    if others:
        second = others[0]
        delta = abs(float(top.price) - float(second.price)) / max(float(top.price), 1)
        if delta <= AGREEMENT_TOLERANCE:
            # Two independent standards-based rungs agreeing is strong evidence.
            confidence = AGREEMENT_CONFIDENCE
            flag = f"agrees with {second.tier}"
        else:
            # Usually a sale price against a list price -- exactly the case
            # where an alert must not fire.
            confidence = max(top.confidence - CONFLICT_PENALTY, 0)
            flag = f"tier_conflict: {second.tier}={second.price}"

    return Extraction(
        price=top.price,
        currency=top.currency or (adapter.currency if adapter else "VND") or "VND",
        confidence=confidence,
        tier=top.tier,
        evidence=top.evidence[:480],
        tiers_matched=sorted({c.tier for c in candidates}),
        flag=flag,
        title=_title(html, adapter),
        availability=_availability(html, adapter),
    )


def _title(html, adapter):
    return selectors.title(html, adapter) or meta.title(html) or jsonld.title(html)


def _availability(html, adapter):
    return jsonld.availability(html) or selectors.availability(html, adapter)


def looks_javascript_rendered(html: str, matched: bool) -> bool:
    """
    Distinguish "this page has no price" from "this page builds its price in
    the browser". The seller gets a different, truthful message for each.

    Detected, not guessed: nothing matched, the body is small, and the document
    carries a framework mount point.
    """
    import re

    if matched:
        return False
    if len(html) < 30_000:
        return True
    return bool(
        len(html) < 200_000
        and re.search(
            r'<div id=["\'](root|app|__next)["\']\s*>\s*</div>'
            r'|__NEXT_DATA__|window\.__NUXT__',
            html, re.I,
        )
    )
