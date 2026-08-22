"""
Price history ledger (PR 2) -- see docs/ai-features/01-instrumentation.md.

Reliability class is LEDGER, so the invariant under test is stronger than for
telemetry: every price the product has ever held must be reconstructable from
these rows, and the ledger must never disagree with `products.price`.
"""
from decimal import Decimal
from pathlib import Path

import pytest

from shared.models.product import PriceHistory, Product

PRODUCT_SERVICE = Path(__file__).resolve().parents[2] / "services" / "product"


@pytest.fixture()
def authed_client(session_factory, monkeypatch, seller, load_service):
    """Product router with `seller` authenticated as the current user."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from shared.database import get_db
    from shared.security import get_current_user, get_optional_current_user

    load_service(PRODUCT_SERVICE)
    import app.services.search_logging as search_logging
    import app.routers.products as products_router

    monkeypatch.setattr(search_logging, "SessionLocal", session_factory)

    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    api = FastAPI()
    api.include_router(products_router.router, prefix="/api/v1/products")
    api.dependency_overrides[get_db] = override_get_db
    api.dependency_overrides[get_current_user] = lambda: seller
    api.dependency_overrides[get_optional_current_user] = lambda: seller

    return TestClient(api)


def history(db, product_id=None):
    query = db.query(PriceHistory)
    if product_id is not None:
        query = query.filter(PriceHistory.product_id == product_id)
    return query.order_by(PriceHistory.id).all()


NEW_PRODUCT = {
    "name": "Glazed bowl",
    "description": "A shallow bowl",
    "price": 25.00,
    "quantity_available": 4,
}


def test_create_product_writes_origin_row(authed_client, db, seller):
    response = authed_client.post("/api/v1/products/", json=NEW_PRODUCT)

    assert response.status_code == 200, response.text
    product_id = response.json()["id"]

    rows = history(db, product_id)
    assert len(rows) == 1
    assert rows[0].change_reason == "initial"
    assert rows[0].old_price == Decimal("25.00")
    assert rows[0].new_price == Decimal("25.00")
    assert rows[0].changed_by == seller.id


def test_price_change_is_recorded(authed_client, db, seller):
    product_id = authed_client.post("/api/v1/products/", json=NEW_PRODUCT).json()["id"]

    response = authed_client.put(
        f"/api/v1/products/{product_id}", json={"price": 30.50}
    )
    assert response.status_code == 200, response.text

    rows = history(db, product_id)
    assert len(rows) == 2
    change = rows[-1]
    assert change.change_reason == "seller_update"
    assert change.old_price == Decimal("25.00")
    assert change.new_price == Decimal("30.50")
    assert change.changed_by == seller.id


def test_non_price_update_writes_no_row(authed_client, db):
    """Editing a description is not a price change."""
    product_id = authed_client.post("/api/v1/products/", json=NEW_PRODUCT).json()["id"]

    authed_client.put(f"/api/v1/products/{product_id}", json={"name": "Renamed bowl"})

    assert len(history(db, product_id)) == 1  # the origin row only


def test_setting_the_same_price_writes_no_row(authed_client, db):
    """No-op updates must not pad the ledger with phantom changes."""
    product_id = authed_client.post("/api/v1/products/", json=NEW_PRODUCT).json()["id"]

    authed_client.put(f"/api/v1/products/{product_id}", json={"price": 25.00})

    assert len(history(db, product_id)) == 1


def test_successive_changes_reconstruct_the_price_series(authed_client, db):
    """The property the pricing model actually depends on."""
    product_id = authed_client.post("/api/v1/products/", json=NEW_PRODUCT).json()["id"]

    for price in (30.00, 27.50, 35.00):
        authed_client.put(f"/api/v1/products/{product_id}", json={"price": price})

    rows = history(db, product_id)
    assert [r.new_price for r in rows] == [
        Decimal("25.00"), Decimal("30.00"), Decimal("27.50"), Decimal("35.00")
    ]

    # Each row's old_price must be the previous row's new_price -- an unbroken
    # chain, with no gap where a change went unrecorded.
    for previous, current in zip(rows, rows[1:]):
        assert current.old_price == previous.new_price

    # And the ledger must agree with the product's current price.
    product = db.query(Product).filter(Product.id == product_id).one()
    assert product.price == rows[-1].new_price


def test_ledger_write_failure_rolls_back_the_price_change(
    authed_client, db, monkeypatch
):
    """
    The LEDGER contract: if history cannot be written, the price must not
    change either. Divergence is the one outcome that must be impossible.
    """
    product_id = authed_client.post("/api/v1/products/", json=NEW_PRODUCT).json()["id"]

    import app.routers.products as products_router

    class ExplodingPriceHistory:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("ledger unavailable")

    monkeypatch.setattr(products_router, "PriceHistory", ExplodingPriceHistory)

    with pytest.raises(RuntimeError):
        authed_client.put(f"/api/v1/products/{product_id}", json={"price": 99.00})

    db.expire_all()
    product = db.query(Product).filter(Product.id == product_id).one()
    assert product.price == Decimal("25.00")   # unchanged
    assert len(history(db, product_id)) == 1    # origin row only
