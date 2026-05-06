"""Accounts + trading rules — auth, ownership, CRUD."""
import pytest
from httpx import AsyncClient

from tests.conftest import API_PREFIX


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_account_endpoints_require_auth(client: AsyncClient, account_payload):
    r = await client.get(f"{API_PREFIX}/accounts")
    # FastAPI's HTTPBearer returns 403 when no Authorization header is present.
    assert r.status_code in (401, 403)

    r = await client.post(f"{API_PREFIX}/accounts", json=account_payload)
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_account_endpoints_reject_invalid_token(client: AsyncClient):
    r = await client.get(
        f"{API_PREFIX}/accounts",
        headers={"Authorization": "Bearer not-a-real-jwt"},
    )
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# Account CRUD
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_account(client: AsyncClient, headers, account_payload):
    r = await client.post(f"{API_PREFIX}/accounts", json=account_payload, headers=headers)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["account_name"] == account_payload["account_name"]
    assert body["starting_equity"] == account_payload["starting_equity"]
    # Service should mirror starting equity into current equity.
    assert body["current_equity"] == account_payload["starting_equity"]
    assert body["currency"] == "VND"
    assert "id" in body


@pytest.mark.asyncio
async def test_create_account_validates_input(client: AsyncClient, headers):
    bad = {"account_name": "x", "starting_equity": -1, "currency": "VND"}
    r = await client.post(f"{API_PREFIX}/accounts", json=bad, headers=headers)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_list_accounts_only_returns_own(client, headers, other_user_headers, account_payload):
    a = await client.post(f"{API_PREFIX}/accounts", json=account_payload, headers=headers)
    assert a.status_code == 201

    other = dict(account_payload, account_name="Someone else's account")
    b = await client.post(f"{API_PREFIX}/accounts", json=other, headers=other_user_headers)
    assert b.status_code == 201

    r = await client.get(f"{API_PREFIX}/accounts", headers=headers)
    assert r.status_code == 200
    names = [a["account_name"] for a in r.json()]
    assert account_payload["account_name"] in names
    assert "Someone else's account" not in names


@pytest.mark.asyncio
async def test_get_account_404_when_other_users(client, headers, other_user_headers, account):
    r = await client.get(f"{API_PREFIX}/accounts/{account['id']}", headers=other_user_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_update_account(client, headers, account):
    r = await client.put(
        f"{API_PREFIX}/accounts/{account['id']}",
        json={"account_name": "Renamed", "max_risk_per_trade": 1.5},
        headers=headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["account_name"] == "Renamed"
    assert body["max_risk_per_trade"] == 1.5


@pytest.mark.asyncio
async def test_update_account_404_for_unknown(client, headers):
    r = await client.put(
        f"{API_PREFIX}/accounts/99999",
        json={"account_name": "Whatever"},
        headers=headers,
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_account(client, headers, account):
    r = await client.delete(f"{API_PREFIX}/accounts/{account['id']}", headers=headers)
    assert r.status_code == 204
    follow = await client.get(f"{API_PREFIX}/accounts/{account['id']}", headers=headers)
    assert follow.status_code == 404


# ---------------------------------------------------------------------------
# Trading rules
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_rule(client, headers, account):
    r = await client.post(
        f"{API_PREFIX}/accounts/{account['id']}/rules",
        json={
            "rule_text": "Never risk more than 2% per trade",
            "category": "Risk",
            "sort_order": 1,
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["rule_text"].startswith("Never risk")
    assert body["category"] == "Risk"
    assert body["is_active"] is True


@pytest.mark.asyncio
async def test_list_rules_filters_active(client, headers, account):
    aid = account["id"]
    r1 = await client.post(
        f"{API_PREFIX}/accounts/{aid}/rules",
        json={"rule_text": "Active rule", "category": "Risk"},
        headers=headers,
    )
    rule_id = r1.json()["id"]
    r2 = await client.post(
        f"{API_PREFIX}/accounts/{aid}/rules",
        json={"rule_text": "Will deactivate", "category": "Entry"},
        headers=headers,
    )
    other_id = r2.json()["id"]

    deactivated = await client.put(
        f"{API_PREFIX}/accounts/{aid}/rules/{other_id}",
        json={"is_active": False},
        headers=headers,
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False

    all_rules = await client.get(f"{API_PREFIX}/accounts/{aid}/rules", headers=headers)
    active_only = await client.get(
        f"{API_PREFIX}/accounts/{aid}/rules?active_only=true", headers=headers,
    )
    all_ids = {r["id"] for r in all_rules.json()}
    active_ids = {r["id"] for r in active_only.json()}
    assert rule_id in all_ids and other_id in all_ids
    assert rule_id in active_ids and other_id not in active_ids


@pytest.mark.asyncio
async def test_delete_rule(client, headers, account):
    aid = account["id"]
    created = await client.post(
        f"{API_PREFIX}/accounts/{aid}/rules",
        json={"rule_text": "Drop me", "category": "General"},
        headers=headers,
    )
    rid = created.json()["id"]
    r = await client.delete(f"{API_PREFIX}/accounts/{aid}/rules/{rid}", headers=headers)
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_rule_404_for_other_users_account(client, headers, other_user_headers, account):
    r = await client.post(
        f"{API_PREFIX}/accounts/{account['id']}/rules",
        json={"rule_text": "Cross-tenant rule", "category": "Risk"},
        headers=other_user_headers,
    )
    assert r.status_code == 404
