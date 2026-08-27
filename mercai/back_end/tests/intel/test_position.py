"""
Price position: the statistics, the fallback ladder, and the privacy floor.

Built against fixtures rather than the seeded catalogue so the arithmetic is
checkable by hand -- but the shapes mirror what scripts/seed_catalogue.py
creates, so a failure here means the seeded box is wrong too.
"""
from decimal import Decimal

import pytest

from shared.models.product import Category, PriceHistory, Product
from shared.models.user import User, UserRole


@pytest.fixture()
def pos(load_service):
    from pathlib import Path

    load_service(Path(__file__).resolve().parents[2] / "services" / "intel")
    import app.services.position as position

    return position


def _seller(db, username):
    user = User(
        username=username, email=f"{username}@example.com",
        full_name=username, hashed_password="x", role=UserRole.SELLER,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def _product(db, seller, category, price, name=None):
    product = Product(
        name=name or f"{category.name} {price}",
        description="d",
        price=Decimal(price),
        quantity_available=1,
        seller_id=seller.id,
        category_id=category.id,
        is_active=True,
    )
    db.add(product)
    db.flush()
    return product


@pytest.fixture()
def world(db):
    """Two sellers, a parent category with two children."""
    parent = Category(name="Gốm sứ", is_active=True)
    db.add(parent)
    db.flush()
    bowls = Category(name="Bát đĩa", parent_id=parent.id, is_active=True)
    cups = Category(name="Ấm chén", parent_id=parent.id, is_active=True)
    db.add_all([bowls, cups])
    db.flush()
    return {
        "parent": parent, "bowls": bowls, "cups": cups,
        "mine": _seller(db, "mine"), "rival": _seller(db, "rival"),
        "third": _seller(db, "third"),
    }


# --------------------------------------------------------------------------
# quantile
# --------------------------------------------------------------------------

def test_quantile_interpolates(pos):
    values = [100, 200, 300, 400, 500]
    assert pos.quantile(values, 0.0) == 100
    assert pos.quantile(values, 0.5) == 300
    assert pos.quantile(values, 1.0) == 500
    assert pos.quantile(values, 0.25) == 200


def test_quantile_on_an_even_count_interpolates_between_neighbours(pos):
    assert pos.quantile([100, 200, 300, 400], 0.5) == 250


def test_quantile_handles_degenerate_inputs(pos):
    assert pos.quantile([], 0.5) is None
    assert pos.quantile([42], 0.5) == 42


def test_quantiles_match_the_seeded_catalogue(pos):
    """The exact figures recorded in the design doc for Bát đĩa."""
    prices = [85_000, 120_000, 145_000, 165_000, 185_000, 220_000, 280_000, 450_000]
    assert pos.quantile(prices, 0.25) == 138_750
    assert pos.quantile(prices, 0.50) == 175_000
    assert pos.quantile(prices, 0.75) == 235_000


# --------------------------------------------------------------------------
# The privacy floor
# --------------------------------------------------------------------------

def test_four_comparables_is_not_a_market(pos, db, world):
    """
    MIN_COMPARABLE_N is a hard floor. Four rivals in the category and no
    broader one to fall back to must yield no market view -- not a median over
    four, which would be noise and would leak a specific competitor's price.
    """
    for price in (100_000, 110_000, 120_000, 130_000):
        _product(db, world["rival"], world["bowls"], price)
    mine = _product(db, world["mine"], world["bowls"], 115_000)
    db.commit()

    result = pos.compute_position(db, mine)
    assert result["basis"] == pos.BASIS_NONE
    assert result["position"] is None
    assert result["median"] is None
    assert result["comparables"] == []


def test_five_comparables_is_a_market(pos, db, world):
    for price in (100_000, 110_000, 120_000, 130_000, 140_000):
        _product(db, world["rival"], world["bowls"], price)
    mine = _product(db, world["mine"], world["bowls"], 115_000)
    db.commit()

    result = pos.compute_position(db, mine)
    assert result["basis"] == pos.BASIS_OWN_CATEGORY
    assert result["comparable_count"] == 5
    assert result["median"] == 120_000


# --------------------------------------------------------------------------
# The fallback ladder
# --------------------------------------------------------------------------

def test_falls_back_to_the_parent_category(pos, db, world):
    """
    Two rivals in the seller's own category is below the floor, but the parent
    has enough across its children. This is the case a genuine sub-category
    hits constantly, and it is why rung 2 exists.
    """
    for price in (300_000, 320_000):
        _product(db, world["rival"], world["cups"], price)
    for price in (100_000, 120_000, 140_000, 160_000):
        _product(db, world["third"], world["bowls"], price)
    mine = _product(db, world["mine"], world["cups"], 310_000)
    db.commit()

    result = pos.compute_position(db, mine)
    assert result["basis"] == pos.BASIS_PARENT_CATEGORY
    assert result["basis_label"] == "Gốm sứ"
    assert result["comparable_count"] == 6


def test_no_comparables_at_all_is_a_state_not_an_error(pos, db, world):
    """A genuine one-off. The screen still has content: price and trend."""
    mine = _product(db, world["mine"], world["bowls"], 900_000)
    db.add(PriceHistory(
        product_id=mine.id, old_price=Decimal(900_000), new_price=Decimal(900_000),
        change_reason="initial", changed_by=world["mine"].id,
    ))
    db.commit()

    result = pos.compute_position(db, mine)
    assert result["basis"] == pos.BASIS_NONE
    assert result["own_price"] == 900_000
    assert len(result["trend"]) == 1


# --------------------------------------------------------------------------
# Labelling
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "own_price,expected",
    [
        (50_000, "below_market"),    # under p25
        (120_000, "in_range"),
        (900_000, "above_market"),   # over p75
    ],
)
def test_position_labels_use_quartiles(pos, db, world, own_price, expected):
    for price in (100_000, 110_000, 120_000, 130_000, 140_000):
        _product(db, world["rival"], world["bowls"], price)
    mine = _product(db, world["mine"], world["bowls"], own_price)
    db.commit()

    assert pos.compute_position(db, mine)["position"] == expected


def test_one_extreme_listing_does_not_drag_the_label(pos, db, world):
    """
    Quartiles, never the mean. With a single 8m outlier the mean is ~1.4m --
    a 120k listing would read as far below "average" and be mislabelled. The
    median is unmoved.
    """
    for price in (100_000, 110_000, 120_000, 130_000, 8_000_000):
        _product(db, world["rival"], world["bowls"], price)
    mine = _product(db, world["mine"], world["bowls"], 120_000)
    db.commit()

    result = pos.compute_position(db, mine)
    assert result["median"] == 120_000
    assert result["position"] == "in_range"


# --------------------------------------------------------------------------
# Who counts as a comparable
# --------------------------------------------------------------------------

def test_the_sellers_own_listings_are_excluded(pos, db, world):
    """
    Otherwise a seller holding most of a thin category is compared against
    themselves, and the median follows their own price around.
    """
    for price in (100_000, 200_000, 300_000, 400_000, 500_000):
        _product(db, world["mine"], world["bowls"], price)
    mine = _product(db, world["mine"], world["bowls"], 250_000)
    db.commit()

    assert pos.compute_position(db, mine)["basis"] == pos.BASIS_NONE


def test_inactive_and_zero_priced_listings_are_excluded(pos, db, world):
    for price in (100_000, 110_000, 120_000, 130_000, 140_000):
        _product(db, world["rival"], world["bowls"], price)
    dead = _product(db, world["rival"], world["bowls"], 999_000)
    dead.is_active = False
    free = _product(db, world["rival"], world["bowls"], 0)
    mine = _product(db, world["mine"], world["bowls"], 115_000)
    db.commit()

    result = pos.compute_position(db, mine)
    assert result["comparable_count"] == 5
    assert result["max"] == 140_000


# Widened in phase 2 to carry `source`, and asserted as an allowlist rather
# than an equality so that adding a field is a deliberate act: any NEW key has
# to be added here, which is the moment to ask whether it identifies a seller.
COMPARABLE_FIELDS = {"product_id", "name", "price", "source"}


def test_comparables_never_name_the_seller(pos, db, world):
    """A market summary, not a ranked list of who to undercut."""
    for price in (100_000, 110_000, 120_000, 130_000, 140_000):
        _product(db, world["rival"], world["bowls"], price)
    mine = _product(db, world["mine"], world["bowls"], 115_000)
    db.commit()

    for row in pos.compute_position(db, mine)["comparables"]:
        assert set(row) == COMPARABLE_FIELDS
        assert not any(k in row for k in ("seller", "seller_id", "shop", "shop_name"))


def test_the_sample_spans_the_range_rather_than_the_cheap_end(pos, db, world):
    """Showing the cheapest N would make every category look cheaper than it is."""
    for price in range(100_000, 100_000 + 20 * 10_000, 10_000):
        _product(db, world["rival"], world["bowls"], price)
    mine = _product(db, world["mine"], world["bowls"], 150_000)
    db.commit()

    sample = pos.compute_position(db, mine)["comparables"]
    assert len(sample) == pos.SAMPLE_SIZE
    assert sample[0]["price"] == 100_000
    assert sample[-1]["price"] == 290_000


# --------------------------------------------------------------------------
# Trend
# --------------------------------------------------------------------------

def test_trend_is_ordered_and_carries_the_reason(pos, db, world):
    mine = _product(db, world["mine"], world["bowls"], 185_000)
    db.add_all([
        PriceHistory(product_id=mine.id, old_price=Decimal(165_000),
                     new_price=Decimal(165_000), change_reason="initial"),
        PriceHistory(product_id=mine.id, old_price=Decimal(165_000),
                     new_price=Decimal(185_000), change_reason="seller_update"),
    ])
    db.commit()

    trend = pos.price_trend(db, mine.id)
    assert [p["price"] for p in trend] == [165_000, 185_000]
    assert trend[0]["reason"] == "initial"


def test_trend_is_scoped_to_the_product(pos, db, world):
    mine = _product(db, world["mine"], world["bowls"], 100_000)
    other = _product(db, world["rival"], world["bowls"], 200_000)
    db.add_all([
        PriceHistory(product_id=mine.id, old_price=Decimal(100_000),
                     new_price=Decimal(100_000), change_reason="initial"),
        PriceHistory(product_id=other.id, old_price=Decimal(200_000),
                     new_price=Decimal(200_000), change_reason="initial"),
    ])
    db.commit()

    assert len(pos.price_trend(db, mine.id)) == 1
