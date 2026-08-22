"""
Fixtures for the AI service.

Anything importing from `app` must call `load_service(AI_SERVICE)` first --
every service exposes a top-level `app` package, so the loser of a sys.path
race resolves to the wrong module silently. See tests/conftest.py.

No test here reaches a real model: the Ollama client is always stubbed.
"""
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[2]
AI_SERVICE = BACKEND_ROOT / "services" / "ai"


@pytest.fixture()
def seller(db):
    from shared.models.user import User, UserRole

    user = User(
        email="seller@example.com", username="seller",
        hashed_password="not-a-real-hash", full_name="Test Seller",
        role=UserRole.SELLER,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture()
def other_seller(db):
    from shared.models.user import User, UserRole

    user = User(
        email="rival@example.com", username="rival",
        hashed_password="not-a-real-hash", full_name="Rival Seller",
        role=UserRole.SELLER,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture()
def product(db, seller):
    from shared.models.product import Product

    item = Product(
        name="blue vase",
        description="a nice stoneware vase, hand-thrown, 24cm tall",
        price=42, quantity_available=5, seller_id=seller.id, is_active=True,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


# A well-formed model response, used unless a test overrides it.
GOOD_MODEL_OUTPUT = {
    "name": {
        "proposed": "Cobalt Blue Stoneware Vase - 24cm Hand-Thrown",
        "rationale": "Adds material, size and technique buyers filter on.",
    },
    "description": {
        "proposed": "A hand-thrown stoneware vase standing 24cm tall.",
        "rationale": "Expands on form and finish.",
    },
    "tags": {
        "proposed": "vase,stoneware,hand-thrown,vase",
        "rationale": "Matches category vocabulary.",
    },
    "attributes": {
        "material": {"proposed": "stoneware", "rationale": "Stated in the description."},
        "technique": {"proposed": "hand-thrown", "rationale": "Stated in the description."},
        "color": {"proposed": None, "rationale": "", "ask_seller": "What colour is the glaze?"},
        "dimensions": {"proposed": "24cm", "rationale": "Stated in the description."},
    },
}


@pytest.fixture()
def stub_model(monkeypatch, load_service):
    """
    Replace the Ollama client with a controllable stub.

    Returns a setter so a test can install its own payload or raise a
    model-layer error without touching the network.
    """
    load_service(AI_SERVICE)
    import app.services.ollama_client as ollama_module
    import app.services.listing_optimizer as optimizer

    state = {"output": dict(GOOD_MODEL_OUTPUT), "error": None, "calls": 0}

    class StubClient:
        def is_available(self):
            return True

        def generate_json(self, prompt, **kwargs):
            state["calls"] += 1
            state["last_prompt"] = prompt
            if state["error"] is not None:
                raise state["error"]
            return state["output"]

    stub = StubClient()
    monkeypatch.setattr(optimizer, "ollama_client", stub)
    monkeypatch.setattr(ollama_module, "ollama_client", stub)
    return state


@pytest.fixture()
def client(session_factory, seller, stub_model, monkeypatch):
    """
    AI service app with `seller` authenticated and the feature flag on.

    Depends on `stub_model`, which has already called load_service(). Calling
    it again here would purge `app.*` from sys.modules and silently discard the
    stub -- the tests would then hit a real model host.
    """
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from shared.database import get_db
    from shared.security import get_current_user
    from shared.config import settings

    import app.routers.listing as listing_router
    import app.services.guardrails as guardrails

    monkeypatch.setattr(settings, "AI_LISTING_OPTIMIZER_ENABLED", True)
    # No Redis in tests: cache is a no-op, quotas fail open, allowlist absent.
    monkeypatch.setattr(guardrails, "check_quota", lambda *a, **k: (True, None))
    monkeypatch.setattr(guardrails, "consume_quota", lambda *a, **k: None)
    monkeypatch.setattr(listing_router, "check_quota", lambda *a, **k: (True, None))
    monkeypatch.setattr(listing_router, "consume_quota", lambda *a, **k: None)

    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    api = FastAPI()
    api.include_router(listing_router.router, prefix="/api/v1/ai")
    api.dependency_overrides[get_db] = override_get_db
    api.dependency_overrides[get_current_user] = lambda: seller

    return TestClient(api)
