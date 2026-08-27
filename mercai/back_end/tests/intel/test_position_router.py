"""
The endpoint's authorization surface.

Separate from test_position.py on purpose: that file covers whether the numbers
are right, this one covers who is allowed to see them. Both matter, and the
second is the one that turns a reporting feature into a competitive-intelligence
leak if it is wrong.
"""
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from shared.models.product import Category, Product
from shared.models.user import User, UserRole

SERVICE = Path(__file__).resolve().parents[2] / "services" / "intel"


@pytest.fixture()
def world(db):
    parent = Category(name="Gốm sứ", is_active=True)
    db.add(parent)
    db.flush()
    bowls = Category(name="Bát đĩa", parent_id=parent.id, is_active=True)
    db.add(bowls)
    db.flush()

    def mk_user(username, role):
        u = User(username=username, email=f"{username}@e.com", full_name=username,
                 hashed_password="x", role=role, is_active=True)
        db.add(u)
        db.flush()
        return u

    mine = mk_user("mine", UserRole.SELLER)
    rival = mk_user("rival", UserRole.SELLER)
    buyer = mk_user("buyer", UserRole.CUSTOMER)

    def mk_product(seller, price):
        p = Product(name=f"p{price}", description="d", price=Decimal(price),
                    quantity_available=1, seller_id=seller.id,
                    category_id=bowls.id, is_active=True)
        db.add(p)
        db.flush()
        return p

    mine_product = mk_product(mine, 115_000)
    for price in (100_000, 110_000, 120_000, 130_000, 140_000):
        mk_product(rival, price)
    db.commit()
    return {"mine": mine, "rival": rival, "buyer": buyer, "product": mine_product}


def make_client(load_service, session_factory, monkeypatch, as_user, flag=True):
    load_service(SERVICE)

    from shared.config import settings
    from shared.database import get_db
    from shared.security import get_current_user
    import app.routers.position as position_router
    import app.services.guardrails as guardrails

    monkeypatch.setattr(settings, "INTEL_PRICE_ENABLED", flag)
    # No Redis in tests: the cache is a no-op, so every call recomputes.
    monkeypatch.setattr(position_router.cache, "get", lambda *a, **k: None)
    monkeypatch.setattr(position_router.cache, "set", lambda *a, **k: None)
    monkeypatch.setattr(guardrails.cache, "_client", None, raising=False)

    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    api = FastAPI()
    api.include_router(position_router.router, prefix="/api/v1/intel")
    api.dependency_overrides[get_db] = override_get_db
    api.dependency_overrides[get_current_user] = lambda: as_user
    return TestClient(api)


def test_seller_sees_their_own_position(load_service, session_factory, monkeypatch, world):
    client = make_client(load_service, session_factory, monkeypatch, world["mine"])
    response = client.get(f"/api/v1/intel/products/{world['product'].id}/price-position")
    assert response.status_code == 200
    body = response.json()
    assert body["position"] == "in_range"
    assert body["comparable_count"] == 5


def test_another_seller_is_refused(load_service, session_factory, monkeypatch, world):
    """
    The rival owns comparable listings, which is exactly why this must fail:
    the same numbers handed to a competitor are a different feature.
    """
    client = make_client(load_service, session_factory, monkeypatch, world["rival"])
    response = client.get(f"/api/v1/intel/products/{world['product'].id}/price-position")
    assert response.status_code == 403


def test_a_customer_is_refused(load_service, session_factory, monkeypatch, world):
    client = make_client(load_service, session_factory, monkeypatch, world["buyer"])
    response = client.get(f"/api/v1/intel/products/{world['product'].id}/price-position")
    assert response.status_code == 403


def test_a_disabled_feature_returns_404_not_403(load_service, session_factory, monkeypatch, world):
    """
    A disabled feature should not advertise its existence -- 403 would confirm
    the endpoint is there and merely switched off.
    """
    client = make_client(load_service, session_factory, monkeypatch, world["mine"], flag=False)
    response = client.get(f"/api/v1/intel/products/{world['product'].id}/price-position")
    assert response.status_code == 404


def test_a_missing_product_is_404(load_service, session_factory, monkeypatch, world):
    client = make_client(load_service, session_factory, monkeypatch, world["mine"])
    assert client.get("/api/v1/intel/products/999999/price-position").status_code == 404


def test_the_response_never_carries_seller_identity(load_service, session_factory,
                                                    monkeypatch, world):
    client = make_client(load_service, session_factory, monkeypatch, world["mine"])
    body = client.get(f"/api/v1/intel/products/{world['product'].id}/price-position").json()
    blob = str(body)
    assert "rival" not in blob
    for row in body["comparables"]:
        assert set(row) == {"product_id", "name", "price", "source"}
        assert not any(k in row for k in ("seller", "seller_id", "shop", "shop_name"))
