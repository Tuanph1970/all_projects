"""
Undercut alerts.

Every test here is a way a false alert gets raised. That is the failure mode
worth guarding: an alert says a competitor moved under you, and a seller may
cut a real price because of it. A missed alert costs an opportunity; a false
one costs margin.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from shared.models.intel import ComparableObservation, TrackedComparable

SERVICE = Path(__file__).resolve().parents[2] / "services" / "intel"


@pytest.fixture()
def alerts(load_service):
    load_service(SERVICE)
    import app.services.alerts as module
    return module


@pytest.fixture()
def comparable(db):
    row = TrackedComparable(
        seller_id=1, product_id=1, url="https://tiki.vn/x",
        url_hash="h" * 64, source_host="tiki.vn", is_active=True,
    )
    db.add(row)
    db.flush()
    return row


def observe(db, comparable, price, *, hours_ago=1, confidence=99, status="ok"):
    row = ComparableObservation(
        comparable_id=comparable.id,
        observed_at=datetime.now(timezone.utc) - timedelta(hours=hours_ago),
        status=status,
        price=Decimal(price) if price is not None else None,
        confidence=confidence,
    )
    db.add(row)
    db.flush()
    return row


# --------------------------------------------------------------------------
# The happy path
# --------------------------------------------------------------------------

def test_two_confident_recent_low_readings_raise_an_alert(alerts, db, comparable):
    observe(db, comparable, 150_000, hours_ago=5)
    observe(db, comparable, 148_000, hours_ago=1)
    db.commit()

    found = alerts.evaluate(db, product_id=1, own_price=200_000)
    assert len(found) == 1
    assert found[0]["type"] == "undercut"
    assert found[0]["their_price"] == 148_000
    assert found[0]["gap_percent"] == 26.0
    # The seller must not be left thinking something watches continuously.
    assert found[0]["evaluated"] == "when you opened this screen"


# --------------------------------------------------------------------------
# Each condition, on its own
# --------------------------------------------------------------------------

def test_one_low_reading_is_not_enough(alerts, db, comparable):
    """One reading is a flash sale, a voucher price, or a misparse."""
    observe(db, comparable, 150_000, hours_ago=1)
    db.commit()
    assert alerts.evaluate(db, product_id=1, own_price=200_000) == []


def test_a_low_reading_after_a_normal_one_is_not_enough(alerts, db, comparable):
    """The two most recent must BOTH be low, not just the latest."""
    observe(db, comparable, 205_000, hours_ago=5)   # above the seller
    observe(db, comparable, 150_000, hours_ago=1)   # a single dip
    db.commit()
    assert alerts.evaluate(db, product_id=1, own_price=200_000) == []


def test_a_gap_under_five_percent_is_noise(alerts, db, comparable):
    observe(db, comparable, 196_000, hours_ago=5)   # 2% below
    observe(db, comparable, 195_000, hours_ago=1)
    db.commit()
    assert alerts.evaluate(db, product_id=1, own_price=200_000) == []


def test_exactly_five_percent_qualifies(alerts, db, comparable):
    observe(db, comparable, 190_000, hours_ago=5)
    observe(db, comparable, 190_000, hours_ago=1)
    db.commit()
    assert len(alerts.evaluate(db, product_id=1, own_price=200_000)) == 1


def test_a_stale_reading_does_not_alert(alerts, db, comparable):
    """A price from last week is not news about today."""
    observe(db, comparable, 150_000, hours_ago=80)
    observe(db, comparable, 150_000, hours_ago=72)
    db.commit()
    assert alerts.evaluate(db, product_id=1, own_price=200_000) == []


def test_a_low_confidence_reading_never_alerts(alerts, db, comparable):
    """
    Tier 5 and unconfigured tier-3 walks are displayed with a caveat and must
    never drive an alert -- that is the entire point of the confidence bar.
    """
    observe(db, comparable, 150_000, hours_ago=5, confidence=55)
    observe(db, comparable, 150_000, hours_ago=1, confidence=55)
    db.commit()
    assert alerts.evaluate(db, product_id=1, own_price=200_000) == []


def test_a_confident_reading_backed_by_a_guess_is_one_reading_not_two(alerts, db, comparable):
    observe(db, comparable, 150_000, hours_ago=5, confidence=55)   # a guess
    observe(db, comparable, 150_000, hours_ago=1, confidence=99)   # confident
    db.commit()
    assert alerts.evaluate(db, product_id=1, own_price=200_000) == []


def test_failed_fetches_are_skipped_not_treated_as_evidence(alerts, db, comparable):
    """
    A competitor's site being down for a day should not reset the evidence that
    they cut their price.
    """
    observe(db, comparable, 150_000, hours_ago=6)
    observe(db, comparable, None, hours_ago=4, status="http_error", confidence=None)
    observe(db, comparable, 149_000, hours_ago=1)
    db.commit()
    assert len(alerts.evaluate(db, product_id=1, own_price=200_000)) == 1


def test_an_inactive_comparable_is_ignored(alerts, db, comparable):
    observe(db, comparable, 150_000, hours_ago=5)
    observe(db, comparable, 150_000, hours_ago=1)
    comparable.is_active = False
    db.commit()
    assert alerts.evaluate(db, product_id=1, own_price=200_000) == []


def test_a_higher_priced_competitor_never_alerts(alerts, db, comparable):
    observe(db, comparable, 260_000, hours_ago=5)
    observe(db, comparable, 255_000, hours_ago=1)
    db.commit()
    assert alerts.evaluate(db, product_id=1, own_price=200_000) == []


# --------------------------------------------------------------------------
# Degenerate inputs
# --------------------------------------------------------------------------

def test_no_own_price_yields_nothing(alerts, db, comparable):
    observe(db, comparable, 150_000, hours_ago=1)
    observe(db, comparable, 150_000, hours_ago=5)
    db.commit()
    assert alerts.evaluate(db, product_id=1, own_price=None) == []
    assert alerts.evaluate(db, product_id=1, own_price=0) == []


def test_a_product_with_no_comparables_yields_nothing(alerts, db):
    assert alerts.evaluate(db, product_id=999, own_price=200_000) == []


def test_alerts_are_ordered_by_severity(alerts, db):
    """The biggest undercut first — that is the one worth reading."""
    for host, price in (("tiki.vn", 180_000), ("fptshop.com.vn", 120_000)):
        row = TrackedComparable(
            seller_id=1, product_id=1, url=f"https://{host}/x",
            url_hash=host.ljust(64, "z"), source_host=host, is_active=True,
        )
        db.add(row)
        db.flush()
        observe(db, row, price, hours_ago=5)
        observe(db, row, price, hours_ago=1)
    db.commit()

    found = alerts.evaluate(db, product_id=1, own_price=200_000)
    assert [a["source_host"] for a in found] == ["fptshop.com.vn", "tiki.vn"]
    assert found[0]["gap_percent"] > found[1]["gap_percent"]
