"""
Listing optimizer.

Orchestrates: gather context -> build prompt -> call model -> validate and
filter -> persist as a proposal. It never writes to `products`; applying a
suggestion is the client's job via the existing product API, which keeps that
service's validation, ownership checks and cache invalidation intact.
"""
import logging
import re
import time
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from shared.models.product import Product, Category
from shared.models.seller_profile import SellerProfile

from app.prompts.listing import PROMPT_VERSION, build_listing_prompt
from app.services.guardrails import find_unsupported_claims, strip_blocked_sentences
from app.services.image_report import build_image_report
from app.services.ollama_client import ollama_client

logger = logging.getLogger(__name__)


class DraftProduct:
    """
    Duck-types the Product attributes the optimizer reads, for a listing that
    has not been saved yet. Deliberately not a Product instance -- nothing here
    should ever be persisted by accident.
    """

    id = None
    images = ()

    def __init__(self, draft, seller_id):
        self.seller_id = seller_id
        self.name = draft.name
        self.description = draft.description
        self.tags = draft.tags
        self.material = draft.material
        self.color = draft.color
        self.technique = draft.technique
        self.dimensions = draft.dimensions
        self.weight = None
        self.category_id = draft.category_id

PEER_SAMPLE_SIZE = 20
MIN_PEERS_FOR_VOCABULARY = 5

# Fields the model may propose. `price` is absent by design: pricing is a
# separate feature with a different risk profile, and the optimizer must not
# be able to touch commercial terms.
ALLOWED_FIELDS = ("name", "description", "tags")
ALLOWED_ATTRIBUTES = ("material", "color", "technique", "dimensions")

MAX_NAME_LENGTH = 255
MAX_TAGS_LENGTH = 500


def gather_peer_vocabulary(db: Session, product: Product) -> Dict[str, List[str]]:
    """Sample sibling listings so the model uses this marketplace's words."""
    if not product.category_id:
        return {}

    query = db.query(Product).filter(
        Product.category_id == product.category_id,
        Product.is_active.is_(True),
    )
    # A draft has no id yet. `Product.id != None` renders as SQL `!= NULL`,
    # which matches nothing -- so only exclude self when there is a self.
    if getattr(product, "id", None) is not None:
        query = query.filter(Product.id != product.id)
    peers = query.limit(PEER_SAMPLE_SIZE).all()
    if len(peers) < MIN_PEERS_FOR_VOCABULARY:
        return {}

    def collect(attr: str) -> List[str]:
        values = {
            (getattr(p, attr) or "").strip()
            for p in peers
            if (getattr(p, attr) or "").strip()
        }
        return sorted(values)[:15]

    tags: set = set()
    for p in peers:
        for tag in (p.tags or "").split(","):
            tag = tag.strip().lower()
            if tag:
                tags.add(tag)

    return {
        "materials": collect("material"),
        "techniques": collect("technique"),
        "colors": collect("color"),
        "common_tags": sorted(tags)[:25],
    }


def _supporting_text(product: Product) -> str:
    """Everything the seller actually wrote, for the anti-fabrication check."""
    return " ".join(
        str(v) for v in [
            product.name, product.description, product.tags,
            product.material, product.color, product.technique,
            product.dimensions,
        ] if v
    ).lower()


def _attribute_is_supported(
    value: str, supporting: str, vocabulary: Dict[str, List[str]], key: str
) -> bool:
    """
    An attribute may be proposed only if the seller's own text supports it, or
    it is established vocabulary in this category.

    A marketplace that silently auto-fills the wrong material is worse than one
    with empty fields: buyers filter on it and the seller never sees the lie.
    """
    v = value.strip().lower()
    if not v:
        return False
    if v in supporting:
        return True
    # Multi-word values count as supported if every word appears in the text.
    words = [w for w in re.split(r"\W+", v) if len(w) > 2]
    if words and all(w in supporting for w in words):
        return True
    vocab_key = {"material": "materials", "technique": "techniques", "color": "colors"}.get(key)
    if vocab_key and v in [x.lower() for x in vocabulary.get(vocab_key, [])]:
        return v in supporting  # in-vocabulary still requires seller support
    return False


def validate_and_filter(
    raw: Dict[str, Any], product: Product, vocabulary: Dict[str, List[str]]
) -> Dict[str, Any]:
    """
    Turn raw model output into a suggestion that is safe to show.

    Everything here assumes the model ignored its instructions: unsupported
    attributes are dropped, blocked claims are stripped, and lengths are capped
    to the column limits so an accepted suggestion cannot fail to save.
    """
    suggestions: Dict[str, Any] = {}
    supporting = _supporting_text(product)
    filtered: List[str] = []

    for field in ALLOWED_FIELDS:
        block = raw.get(field)
        if not isinstance(block, dict):
            continue
        proposed = block.get("proposed")
        if not isinstance(proposed, str) or not proposed.strip():
            continue

        proposed, blocked = strip_blocked_sentences(proposed.strip())
        if blocked:
            filtered.extend(blocked)
        if not proposed:
            continue

        if field == "name":
            proposed = proposed[:MAX_NAME_LENGTH]
        elif field == "tags":
            tags = [t.strip().lower() for t in proposed.split(",") if t.strip()]
            proposed = ",".join(dict.fromkeys(tags))[:MAX_TAGS_LENGTH]

        current = getattr(product, field, None)
        if proposed == (current or ""):
            continue  # no change is not a suggestion

        entry = {
            "current": current,
            "proposed": proposed,
            "rationale": str(block.get("rationale") or "")[:500],
        }

        # Flag, do not remove. The seller is the only one who knows whether an
        # unmentioned property is actually true of their own piece, so the
        # sentence is surfaced for review rather than silently rewritten.
        unsupported = find_unsupported_claims(proposed, supporting)
        if unsupported:
            entry["unsupported"] = unsupported
            logger.info(
                "Listing suggestion flagged %d unsupported sentence(s) in %s",
                len(unsupported), field,
            )

        suggestions[field] = entry

    attributes: Dict[str, Any] = {}
    raw_attrs = raw.get("attributes") if isinstance(raw.get("attributes"), dict) else {}
    for key in ALLOWED_ATTRIBUTES:
        block = raw_attrs.get(key)
        if not isinstance(block, dict):
            continue

        current = getattr(product, key, None)
        proposed = block.get("proposed")
        ask = block.get("ask_seller")

        if isinstance(proposed, str) and proposed.strip():
            if _attribute_is_supported(proposed, supporting, vocabulary, key):
                if proposed.strip() != (current or ""):
                    attributes[key] = {
                        "current": current,
                        "proposed": proposed.strip()[:100],
                        "rationale": str(block.get("rationale") or "")[:500],
                    }
                continue
            # Unsupported: convert the guess into a question.
            filtered.append(f"{key}={proposed}")
            ask = ask or f"What {key} is this piece?"

        if isinstance(ask, str) and ask.strip() and not current:
            attributes[key] = {
                "current": current,
                "proposed": None,
                "ask_seller": ask.strip()[:200],
            }

    if attributes:
        suggestions["attributes"] = attributes

    if filtered:
        logger.info("Listing suggestion post-filter removed: %s", filtered)

    return suggestions


def generate_suggestion(
    db: Session, product: Product, fields: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Run the full pipeline. Raises OllamaError subclasses on model failure."""
    seller_profile = (
        db.query(SellerProfile).filter(SellerProfile.user_id == product.seller_id).first()
    )
    category_name = None
    if product.category_id:
        category = db.query(Category).filter(Category.id == product.category_id).first()
        category_name = category.name if category else None

    vocabulary = gather_peer_vocabulary(db, product)

    prompt = build_listing_prompt(
        product,
        seller_profile=seller_profile,
        category_name=category_name,
        peer_vocabulary=vocabulary,
        fields=fields,
    )

    started = time.monotonic()
    raw = ollama_client.generate_json(prompt, temperature=0.4, max_tokens=900)
    latency_ms = int((time.monotonic() - started) * 1000)

    # A draft's photos are still local to the device, so there is nothing to
    # inspect. Reporting "no images" there would be misleading, not helpful.
    if getattr(product, "id", None) is None:
        image_report = {"score": "not_applicable", "findings": [], "inspected": 0}
    else:
        image_report = build_image_report(list(product.images or []))

    return {
        "suggestions": validate_and_filter(raw, product, vocabulary),
        "image_report": image_report,
        "latency_ms": latency_ms,
    }
