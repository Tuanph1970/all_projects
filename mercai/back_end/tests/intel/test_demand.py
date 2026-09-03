"""
The adapter worklist: what we record when we turn a seller away.

The behaviour under test is easy to state and easy to lose in a refactor -- a
422 that writes nothing looks correct from the endpoint's side, and the signal
it discards is invisible until someone asks "which source should we add next?"
and has nothing to answer with. So the endpoint-level tests here assert the
side effect of a REFUSAL, which is the unusual shape worth pinning down.
"""
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from shared.models.intel import (
    ComparableObservation, RejectedHostRequest, TrackedComparable,
)
from shared.models.product import Category, Product
from shared.models.user import User, UserRole

SERVICE = Path(__file__).resolve().parents[2] / "services" / "intel"


@pytest.fixture()
def demand(load_service):
    load_service(SERVICE)
    import app.services.demand as module

    return module


@pytest.fixture()
def world(db):
    category = Category(name="Gốm sứ", is_active=True)
    db.add(category)
    db.flush()

    def mk_user(username):
        u = User(username=username, email=f"{username}@e.com", full_name=username,
                 hashed_password="x", role=UserRole.SELLER, is_active=True)
        db.add(u)
        db.flush()
        return u

    mine = mk_user("mine")
    other = mk_user("other")
    product = Product(name="Bát", description="d", price=Decimal(115_000),
                      quantity_available=1, seller_id=mine.id,
                      category_id=category.id, is_active=True)
    db.add(product)
    db.commit()
    return {"mine": mine, "other": other, "product": product}


# ---------------------------------------------------------------------------
# recording
# ---------------------------------------------------------------------------

def test_a_rejected_host_is_recorded(demand, db, world):
    demand.record_rejection(db, seller_id=world["mine"].id,
                            url="https://shopee.vn/product-i.123.456")
    row = db.query(RejectedHostRequest).one()
    assert row.host == "shopee.vn"
    assert row.attempts == 1
    assert row.sample_url == "https://shopee.vn/product-i.123.456"


def test_the_same_seller_asking_twice_increments_rather_than_duplicates(demand, db, world):
    for url in ("https://shopee.vn/a-i.1.1", "https://shopee.vn/b-i.2.2"):
        demand.record_rejection(db, seller_id=world["mine"].id, url=url)

    row = db.query(RejectedHostRequest).one()
    assert row.attempts == 2
    # The newest URL wins: an adapter is tested against a page, and the most
    # recent one is the most likely to still exist.
    assert row.sample_url == "https://shopee.vn/b-i.2.2"


def test_www_and_bare_host_are_one_entry(demand, db, world):
    """
    Otherwise the list a human reads to pick the next adapter has the same site
    twice, each with half the demand, and it ranks below a site with less.
    """
    demand.record_rejection(db, seller_id=world["mine"].id, url="https://www.sendo.vn/x")
    demand.record_rejection(db, seller_id=world["mine"].id, url="https://sendo.vn/y")

    row = db.query(RejectedHostRequest).one()
    assert row.host == "sendo.vn"
    assert row.attempts == 2


def test_different_sellers_get_different_rows(demand, db, world):
    demand.record_rejection(db, seller_id=world["mine"].id, url="https://sendo.vn/x")
    demand.record_rejection(db, seller_id=world["other"].id, url="https://sendo.vn/y")
    assert db.query(RejectedHostRequest).count() == 2


def test_ip_literals_and_internal_names_never_reach_the_worklist(demand, db, world):
    """
    check_url runs the allowlist BEFORE the address check, so an SSRF probe
    arrives with the same status as a real marketplace. Without this filter the
    report a human works down would suggest allowlisting `db`.
    """
    for url in ("http://169.254.169.254/latest/meta-data/",
                "http://127.0.0.1/",
                "http://[::1]/",
                "http://db:3306/",
                "http://traefik:8080/api/",
                "http://localhost/"):
        demand.record_rejection(db, seller_id=world["mine"].id, url=url)
    assert db.query(RejectedHostRequest).count() == 0


def test_a_junk_url_is_dropped_not_raised(demand, db, world):
    """Telemetry must never be the thing that fails a request."""
    for url in ("", "not a url", "javascript:alert(1)", None):
        demand.record_rejection(db, seller_id=world["mine"].id, url=url)
    assert db.query(RejectedHostRequest).count() == 0


# ---------------------------------------------------------------------------
# ranking
# ---------------------------------------------------------------------------

def test_breadth_of_demand_outranks_volume(demand, db, world):
    """
    The ordering rule, and the reason the grain is (host, seller).

    One determined seller pasting a site repeatedly is one seller's problem.
    Two sellers asking for the same site is a market, and it is the one that
    should be at the top of the list a human works down.
    """
    for _ in range(40):
        demand.record_rejection(db, seller_id=world["mine"].id, url="https://shopee.vn/x")
    demand.record_rejection(db, seller_id=world["mine"].id, url="https://sendo.vn/x")
    demand.record_rejection(db, seller_id=world["other"].id, url="https://sendo.vn/y")

    ranked = demand.unsupported_demand(db)
    assert [r["host"] for r in ranked] == ["sendo.vn", "shopee.vn"]
    assert ranked[0]["sellers"] == 2 and ranked[0]["attempts"] == 2
    assert ranked[1]["sellers"] == 1 and ranked[1]["attempts"] == 40


def test_failing_supported_hosts_are_grouped_by_status(demand, db, world):
    comparable = TrackedComparable(
        seller_id=world["mine"].id, product_id=world["product"].id,
        url="https://tiki.vn/p", url_hash="h" * 64, source_host="tiki.vn",
        is_active=True,
    )
    db.add(comparable)
    db.flush()
    for status in ("ok", "js_required", "js_required", "no_price_found"):
        db.add(ComparableObservation(comparable_id=comparable.id, status=status))
    db.commit()

    rows = {r["status"]: r["count"] for r in demand.failing_supported_hosts(db)}
    assert rows == {"js_required": 2, "no_price_found": 1}, "ok must not appear"


# ---------------------------------------------------------------------------
# the endpoint
# ---------------------------------------------------------------------------

def make_client(load_service, session_factory, monkeypatch, as_user):
    load_service(SERVICE)

    from shared.config import settings
    from shared.database import get_db
    from shared.security import get_current_user
    import app.routers.comparables as comparables_router
    import app.services.guardrails as guardrails

    monkeypatch.setattr(settings, "INTEL_PRICE_ENABLED", True)
    monkeypatch.setattr(guardrails.cache, "_client", None, raising=False)

    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    api = FastAPI()
    api.include_router(comparables_router.router, prefix="/api/v1/intel")
    api.dependency_overrides[get_db] = override_get_db
    api.dependency_overrides[get_current_user] = lambda: as_user
    return TestClient(api)


def test_adding_an_unsupported_host_still_422s_and_now_counts_it(
        load_service, session_factory, monkeypatch, db, world):
    client = make_client(load_service, session_factory, monkeypatch, world["mine"])
    response = client.post("/api/v1/intel/comparables", json={
        "product_id": world["product"].id,
        "url": "https://shopee.vn/bat-gom-i.123.456",
    })

    assert response.status_code == 422
    assert "shopee.vn" in response.json()["detail"]
    # No comparable row: one we can never fetch is worse than none.
    assert db.query(TrackedComparable).count() == 0
    row = db.query(RejectedHostRequest).one()
    assert row.host == "shopee.vn" and row.seller_id == world["mine"].id


def test_a_private_address_is_refused_without_being_counted(
        load_service, session_factory, monkeypatch, db, world):
    """
    An SSRF probe is not a request for a new source, and putting it on the
    worklist would invite someone to allowlist it.
    """
    client = make_client(load_service, session_factory, monkeypatch, world["mine"])
    response = client.post("/api/v1/intel/comparables", json={
        "product_id": world["product"].id,
        "url": "http://169.254.169.254/latest/meta-data/",
    })

    assert response.status_code == 422
    assert db.query(RejectedHostRequest).count() == 0
