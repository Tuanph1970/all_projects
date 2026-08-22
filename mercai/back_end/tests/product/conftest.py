"""
Fixtures for the product service.

Anything importing from `app` must call `load_service(PRODUCT_SERVICE)` first,
or it may get the seller service's modules (or the legacy monolith's) instead.
See tests/conftest.py.
"""
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[2]
PRODUCT_SERVICE = BACKEND_ROOT / "services" / "product"


@pytest.fixture()
def seller(db):
    """A seller who owns the seeded products."""
    from shared.models.user import User, UserRole

    user = User(
        email="seller@example.com",
        username="seller",
        hashed_password="not-a-real-hash",
        full_name="Test Seller",
        role=UserRole.SELLER,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture()
def products(db, seller):
    """Two active products to search against."""
    from shared.models.product import Product

    items = [
        Product(
            name="Blue stoneware vase",
            description="A tall handmade vase",
            price=42,
            quantity_available=5,
            material="stoneware",
            seller_id=seller.id,
            is_active=True,
        ),
        Product(
            name="Ceramic mug",
            description="A small handmade mug",
            price=12,
            quantity_available=3,
            material="porcelain",
            seller_id=seller.id,
            is_active=True,
        ),
    ]
    db.add_all(items)
    db.commit()
    for item in items:
        db.refresh(item)
    return items


@pytest.fixture()
def client(session_factory, monkeypatch, load_service):
    """
    TestClient for the product router, wired to the test database.

    `record_search` opens its own session rather than reusing the request's
    (FastAPI exits `yield` dependencies before background tasks run), so its
    SessionLocal has to be redirected separately from the get_db override.
    """
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from shared.database import get_db
    from shared.security import get_optional_current_user

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
    api.dependency_overrides[get_optional_current_user] = lambda: None

    return TestClient(api)
