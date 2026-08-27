"""
Where a seller's price sits against comparable listings.

Two sources of prices, combined by rung 1 of the fallback ladder:

  * Mercai's own catalogue, which is already a multi-seller market and needs no
    fetching at all;
  * external listings a seller pasted, once phase 2 has read them.

External prices only join the statistics when they are trusted -- high
confidence, recent, and successfully read. A tier-5 guess or a three-week-old
reading is still shown to the seller, with a caveat, but it must not move a
median they might act on.

See docs/ai-features/05-price-intelligence.md section 8.
"""
import logging
from decimal import Decimal
from typing import Dict, List, Optional, Sequence

from sqlalchemy.orm import Session

from shared.models.product import Category, PriceHistory, Product

logger = logging.getLogger(__name__)

# Never compute a market statistic from fewer than this many listings.
#
# Not a tuning knob, and not really about statistics. With three listings the
# median is noise -- but worse, in a thin category "the market median" over two
# competitors DISCLOSES a specific competitor's price to anyone who can work
# out whose it is. That is why it is a hard floor rather than a warning.
MIN_COMPARABLE_N = 5

# Which rung of the fallback ladder produced the numbers. The client renders
# different copy for each, because "the market for your category" and "the
# market for the broader category" are different claims.
BASIS_OWN_CATEGORY = "own_category"
BASIS_PARENT_CATEGORY = "parent_category"
BASIS_NONE = "none"

POSITION_BELOW = "below_market"
POSITION_IN_RANGE = "in_range"
POSITION_ABOVE = "above_market"

# How many comparable listings to hand back alongside the aggregate. Enough for
# a seller to sanity-check that the comparison is fair, few enough that the
# response is not a ranked targeting list.
SAMPLE_SIZE = 8


def quantile(values: Sequence[float], q: float) -> Optional[float]:
    """
    Linear-interpolated quantile over a sorted sequence.

    Computed here rather than in SQL on purpose: MySQL 8.0.46 has no
    PERCENTILE_CONT (verified -- it is a syntax error), and neither does the
    SQLite the test suite runs on. A SQL implementation would need two
    dialect-specific paths and could not be unit-tested where everything else
    is. A category holds tens of rows, so there is nothing to optimise.
    """
    if not values:
        return None
    if len(values) == 1:
        return float(values[0])

    pos = (len(values) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(values) - 1)
    if lo == hi:
        return float(values[lo])
    return float(values[lo]) + (float(values[hi]) - float(values[lo])) * (pos - lo)


def _broader_category_ids(db: Session, category_id: Optional[int]) -> List[int]:
    """
    The category ids one rung up: every sibling under the same parent.

    If the product sits directly on a top-level category, "broader" means that
    category plus its children -- otherwise a product filed on the parent would
    have no fallback at all, which is the case most likely to produce an empty
    screen.
    """
    if category_id is None:
        return []

    category = db.query(Category).filter(Category.id == category_id).first()
    if category is None:
        return []

    root_id = category.parent_id or category.id
    ids = {root_id}
    ids.update(
        row[0] for row in db.query(Category.id).filter(Category.parent_id == root_id).all()
    )
    return sorted(ids)


def _gather(
    db: Session,
    category_ids: Sequence[int],
    exclude_seller_id: int,
    exclude_product_id: Optional[int],
) -> List[Product]:
    """
    Active listings from OTHER sellers in the given categories.

    The seller's own listings are excluded deliberately. A seller holding most
    of a thin category would otherwise be compared largely against themselves,
    and the median would drift toward their own price every time they changed
    it -- a feedback loop that looks like market movement and is not.
    """
    if not category_ids:
        return []

    query = (
        db.query(Product)
        .filter(
            Product.category_id.in_(category_ids),
            Product.is_active.is_(True),
            Product.seller_id != exclude_seller_id,
            Product.price > 0,
        )
    )
    if exclude_product_id is not None:
        query = query.filter(Product.id != exclude_product_id)
    return query.all()


def _summarise(products: Sequence[Product], own_price: Decimal, external=()) -> Dict:
    prices = sorted(
        [float(p.price) for p in products] + [float(o.price) for o in external]
    )
    p25 = quantile(prices, 0.25)
    median = quantile(prices, 0.50)
    p75 = quantile(prices, 0.75)

    own = float(own_price)
    if own < p25:
        label = POSITION_BELOW
    elif own > p75:
        label = POSITION_ABOVE
    else:
        label = POSITION_IN_RANGE

    # Quartiles, never the mean. One 8,000,000d display piece should not drag
    # a whole category's average and mislabel every other seller in it.
    return {
        "position": label,
        "comparable_count": len(prices),
        "p25": p25,
        "median": median,
        "p75": p75,
        "min": prices[0],
        "max": prices[-1],
    }


def _sample(products: Sequence[Product], external=()) -> List[Dict]:
    """
    A few of the listings behind the number, cheapest first.

    Seller identity is deliberately omitted. These products are publicly
    browsable, so their prices are not secret -- but returning them keyed by
    shop would turn a market summary into a ranked list of who to undercut,
    which is a different product and a worse one.
    """
    rows = [
        {"product_id": p.id, "name": p.name, "price": float(p.price), "source": "mercai"}
        for p in products
    ] + [
        {"product_id": None, "name": (o.title_seen or "External listing"),
         "price": float(o.price), "source": "external"}
        for o in external
    ]
    ordered = sorted(rows, key=lambda r: r["price"])
    if len(ordered) <= SAMPLE_SIZE:
        chosen = ordered
    else:
        # Spread the sample across the range rather than showing the cheapest
        # eight, which would make every category look cheaper than it is.
        step = (len(ordered) - 1) / (SAMPLE_SIZE - 1)
        chosen = [ordered[round(i * step)] for i in range(SAMPLE_SIZE)]

    return chosen


def _external_prices(db: Session, product_id: int):
    """
    Trusted external observations, one per comparable.

    Imported lazily: position.py is the one module in this service that must
    keep working with no network stack at all, and `comparables` pulls in the
    fetcher.
    """
    try:
        from app.services.comparables import trusted_prices
    except Exception:  # pragma: no cover - defensive
        return []
    try:
        return trusted_prices(db, product_id)
    except Exception:
        logger.warning("Could not read external comparables", exc_info=True)
        return []


def price_trend(db: Session, product_id: int, limit: int = 50) -> List[Dict]:
    """
    The seller's own price history -- exact, from the ledger.

    Unlike anything that will come from an external site, this is a complete
    record: every change is written in the same transaction as the change
    itself (docs/ai-features/01-instrumentation.md PR 2). It can be drawn as a
    real line.
    """
    rows = (
        db.query(PriceHistory)
        .filter(PriceHistory.product_id == product_id)
        .order_by(PriceHistory.created_at.asc(), PriceHistory.id.asc())
        .limit(limit)
        .all()
    )
    return [
        {
            "at": row.created_at.isoformat() if row.created_at else None,
            "price": float(row.new_price),
            "reason": row.change_reason,
        }
        for row in rows
    ]


def compute_position(db: Session, product: Product) -> Dict:
    """
    The whole screen payload for one product.

    Walks the fallback ladder and stops at the first rung with enough
    listings. The last rung is a real state with real content, not an error:
    genuine one-off pieces frequently have no comparable, and a blank screen
    would teach those sellers the feature is broken.
    """
    own_price = float(product.price)
    base = {
        "product_id": product.id,
        "product_name": product.name,
        "own_price": own_price,
        "currency": "VND",
        "min_comparable_n": MIN_COMPARABLE_N,
        "trend": price_trend(db, product.id),
    }

    external = _external_prices(db, product.id)

    # Rung 1 -- the seller's own category, plus any external listings they
    # pasted. Both are comparables; where the price came from changes how much
    # we trust it, not whether it counts.
    if product.category_id is not None or external:
        peers = (
            _gather(db, [product.category_id], product.seller_id, product.id)
            if product.category_id is not None else []
        )
        if len(peers) + len(external) >= MIN_COMPARABLE_N:
            category = (
                db.query(Category).filter(Category.id == product.category_id).first()
                if product.category_id else None
            )
            return {
                **base,
                "basis": BASIS_OWN_CATEGORY,
                "basis_label": category.name if category else None,
                "external_count": len(external),
                **_summarise(peers, product.price, external),
                "comparables": _sample(peers, external),
            }

    # Rung 2 -- one category up, labelled as the broader benchmark it is.
    broader = _broader_category_ids(db, product.category_id)
    if broader:
        peers = _gather(db, broader, product.seller_id, product.id)
        if len(peers) >= MIN_COMPARABLE_N:
            root = db.query(Category).filter(
                Category.id == (broader[0] if broader else None)
            ).first()
            parent = None
            if product.category_id:
                cat = db.query(Category).filter(Category.id == product.category_id).first()
                if cat is not None and cat.parent_id:
                    parent = db.query(Category).filter(Category.id == cat.parent_id).first()
                else:
                    parent = cat
            return {
                **base,
                "basis": BASIS_PARENT_CATEGORY,
                "basis_label": (parent or root).name if (parent or root) else None,
                "external_count": len(external),
                **_summarise(peers, product.price, external),
                "comparables": _sample(peers, external),
            }

    # Rung 3 -- no market view. Normal for a genuine one-off, not an error.
    return {
        **base,
        "basis": BASIS_NONE,
        "basis_label": None,
        "external_count": len(external),
        "position": None,
        "comparable_count": len(
            _gather(db, [product.category_id] if product.category_id else [],
                    product.seller_id, product.id)
        ),
        "p25": None, "median": None, "p75": None, "min": None, "max": None,
        "comparables": [],
    }
