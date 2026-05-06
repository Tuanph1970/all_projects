"""Daily plan + weekly review tests."""
import pytest

from tests.conftest import API_PREFIX


# ---------------------------------------------------------------------------
# Daily plans
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_daily_plan(client, headers, account):
    aid = account["id"]
    r = await client.post(
        f"{API_PREFIX}/accounts/{aid}/plans",
        json={
            "plan_date": "2026-01-15",
            "market_review": "VNINDEX in uptrend, banking sector weak.",
            "new_trade_ideas": "FPT pullback to 50-day MA.",
            "emotional_checkin": "Calm, focused.",
        },
        headers=headers,
    )
    assert r.status_code in (200, 201), r.text
    body = r.json()
    assert body["plan_date"] == "2026-01-15"
    assert body["account_id"] == aid


@pytest.mark.asyncio
async def test_daily_plan_is_one_per_date(client, headers, account):
    """POST is documented as get-or-create; calling twice should return same row."""
    aid = account["id"]
    payload = {"plan_date": "2026-02-01", "market_review": "first"}
    a = await client.post(f"{API_PREFIX}/accounts/{aid}/plans", json=payload, headers=headers)
    b = await client.post(f"{API_PREFIX}/accounts/{aid}/plans", json=payload, headers=headers)
    assert a.status_code in (200, 201)
    assert b.status_code in (200, 201)
    assert a.json()["id"] == b.json()["id"]


@pytest.mark.asyncio
async def test_get_and_update_daily_plan(client, headers, account):
    aid = account["id"]
    created = await client.post(
        f"{API_PREFIX}/accounts/{aid}/plans",
        json={"plan_date": "2026-02-02", "market_review": "draft"},
        headers=headers,
    )
    pid = created.json()["id"]

    fetched = await client.get(f"{API_PREFIX}/accounts/{aid}/plans/{pid}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["id"] == pid

    updated = await client.put(
        f"{API_PREFIX}/accounts/{aid}/plans/{pid}",
        json={"market_review": "Refined view: VNINDEX consolidating."},
        headers=headers,
    )
    assert updated.status_code == 200
    assert "Refined view" in updated.json()["market_review"]


@pytest.mark.asyncio
async def test_delete_daily_plan(client, headers, account):
    aid = account["id"]
    created = await client.post(
        f"{API_PREFIX}/accounts/{aid}/plans",
        json={"plan_date": "2026-02-03"},
        headers=headers,
    )
    pid = created.json()["id"]
    r = await client.delete(f"{API_PREFIX}/accounts/{aid}/plans/{pid}", headers=headers)
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_plan_404_for_other_users_account(client, other_user_headers, account):
    r = await client.get(
        f"{API_PREFIX}/accounts/{account['id']}/plans", headers=other_user_headers
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Weekly reviews
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_weekly_review_auto_computes_stats(client, headers, account):
    """trades_taken / trades_won / weekly_pnl come from the trade table."""
    aid = account["id"]
    r = await client.post(
        f"{API_PREFIX}/accounts/{aid}/reviews",
        json={
            "week_start": "2026-01-12",
            "what_went_well": "Disciplined entries",
            "what_went_wrong": "Took one revenge trade Friday",
            "key_adjustments": "Stop trading after 2 losses",
        },
        headers=headers,
    )
    assert r.status_code in (200, 201), r.text
    body = r.json()
    assert body["account_id"] == aid
    # Stats should always be present (zero is fine — no trades in this fixture).
    assert "trades_taken" in body
    assert "trades_won" in body
    assert "weekly_pnl" in body


@pytest.mark.asyncio
async def test_update_weekly_review(client, headers, account):
    aid = account["id"]
    created = await client.post(
        f"{API_PREFIX}/accounts/{aid}/reviews",
        json={"week_start": "2026-01-19", "what_went_well": "draft"},
        headers=headers,
    )
    rid = created.json()["id"]
    r = await client.put(
        f"{API_PREFIX}/accounts/{aid}/reviews/{rid}",
        json={"what_went_well": "Stuck to plan", "key_adjustments": "Tighter stops"},
        headers=headers,
    )
    assert r.status_code == 200
    assert "Stuck to plan" in r.json()["what_went_well"]


@pytest.mark.asyncio
async def test_recalculate_weekly_stats(client, headers, account):
    aid = account["id"]
    created = await client.post(
        f"{API_PREFIX}/accounts/{aid}/reviews",
        json={"week_start": "2026-01-26"},
        headers=headers,
    )
    rid = created.json()["id"]
    r = await client.post(
        f"{API_PREFIX}/accounts/{aid}/reviews/{rid}/recalculate", headers=headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert "trades_taken" in body and "weekly_pnl" in body


@pytest.mark.asyncio
async def test_delete_weekly_review(client, headers, account):
    aid = account["id"]
    created = await client.post(
        f"{API_PREFIX}/accounts/{aid}/reviews",
        json={"week_start": "2026-02-02"},
        headers=headers,
    )
    rid = created.json()["id"]
    r = await client.delete(f"{API_PREFIX}/accounts/{aid}/reviews/{rid}", headers=headers)
    assert r.status_code == 204
