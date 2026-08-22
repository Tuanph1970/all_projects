"""
Fixtures for the seller service.

Anything importing from `app` must call `load_service(SELLER_SERVICE)` first,
or it may get the product service's modules (or the legacy monolith's).
See tests/conftest.py.
"""
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[2]
SELLER_SERVICE = BACKEND_ROOT / "services" / "seller"


@pytest.fixture()
def seller(db):
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
def other_seller(db):
    """A second seller, to prove bulk updates cannot cross tenant boundaries."""
    from shared.models.user import User, UserRole

    user = User(
        email="rival@example.com",
        username="rival",
        hashed_password="not-a-real-hash",
        full_name="Rival Seller",
        role=UserRole.SELLER,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture()
def products(db, seller):
    from shared.models.product import Product

    items = [
        Product(name="Bowl", description="A bowl", price=20,
                quantity_available=5, seller_id=seller.id, is_active=True),
        Product(name="Plate", description="A plate", price=15,
                quantity_available=5, seller_id=seller.id, is_active=True),
    ]
    db.add_all(items)
    db.commit()
    for item in items:
        db.refresh(item)
    return items


@pytest.fixture()
def client(session_factory, seller, load_service):
    """Seller dashboard router with `seller` authenticated."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from shared.database import get_db
    from shared.security import get_current_user

    load_service(SELLER_SERVICE)
    import app.routers.dashboard as dashboard_router

    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    api = FastAPI()
    api.include_router(dashboard_router.router, prefix="/api/v1/seller")
    api.dependency_overrides[get_db] = override_get_db
    api.dependency_overrides[get_current_user] = lambda: seller

    return TestClient(api)
