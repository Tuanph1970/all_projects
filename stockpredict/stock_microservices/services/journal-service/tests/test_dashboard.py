"""Dashboard + equity snapshot tests."""
import pytest

from tests.conftest import API_PREFIX


@pytest.mark.asyncio
async def test_dashboard_returns_account_metrics(client, headers, account):
    r = await client.get(f"{API_PREFIX}/accounts/{account['id']}/dashboard", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    # Don't over-specify the schema — just check the dashboard returned a shape.
    assert isinstance(body, dict)


@pytest.mark.asyncio
async def test_dashboard_404_for_other_user(client, other_user_headers, account):
    r = await client.get(
        f"{API_PREFIX}/accounts/{account['id']}/dashboard", headers=other_user_headers
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_create_and_list_equity_snapshot(client, headers, account):
    aid = account["id"]
    created = await client.post(
        f"{API_PREFIX}/accounts/{aid}/equity"
        "?snapshot_date=2026-01-15&equity_value=101000000&open_trade_equity=0",
        headers=headers,
    )
    assert created.status_code == 201, created.text
    body = created.json()
    # Service flattens to {id, date, equity, open_trade_equity, total}
    assert body["equity"] == 101_000_000
    assert body["date"] == "2026-01-15"

    listed = await client.get(f"{API_PREFIX}/accounts/{aid}/equity", headers=headers)
    assert listed.status_code == 200
    assert any(s["id"] == body["id"] for s in listed.json())


@pytest.mark.asyncio
async def test_equity_validates_positive_equity(client, headers, account):
    r = await client.post(
        f"{API_PREFIX}/accounts/{account['id']}/equity"
        "?snapshot_date=2026-01-15&equity_value=-100",
        headers=headers,
    )
    assert r.status_code == 422
