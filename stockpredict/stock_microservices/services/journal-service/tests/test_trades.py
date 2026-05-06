"""Trade lifecycle tests, including Schwager's stop-tightening rule."""
import pytest

from tests.conftest import API_PREFIX


# ---------------------------------------------------------------------------
# Trade CRUD
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_trade_returns_enriched_response(client, headers, account, trade_payload):
    aid = account["id"]
    r = await client.post(
        f"{API_PREFIX}/accounts/{aid}/trades", json=trade_payload, headers=headers
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["market_ticker"] == "FPT"
    assert body["status"] == "Open"
    # Risk on a 5-point stop * 1000 shares = 5,000; 5,000 / 100,000,000 = 0.005%.
    assert body["risk_amount"] == pytest.approx(5000.0)
    assert body["risk_percent"] == pytest.approx(0.005, rel=1e-3)
    assert "warnings" in body
    assert body["cumulative_risk"]["open_trade_count"] == 1


@pytest.mark.asyncio
async def test_create_trade_blocked_when_cumulative_risk_too_high(client, headers, account):
    """A position big enough to exceed max_cumulative_risk * 1.4 should be rejected."""
    aid = account["id"]
    # 100% drawdown from this single trade — far past the 35% block threshold.
    huge = {
        "entry_date": "2026-01-15",
        "market_ticker": "OVERSIZE",
        "direction": "Long",
        "entry_price": 100.0,
        "entry_type": "Market",
        "initial_stop": 50.0,            # 50-point stop
        "position_size": 1_000_000,      # × 1M shares = 50M risk = 50% of 100M equity
        "commission": 0,
    }
    r = await client.post(f"{API_PREFIX}/accounts/{aid}/trades", json=huge, headers=headers)
    assert r.status_code == 400
    assert "tích lũy" in r.json()["detail"].lower() or "cumulative" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_trade_validates_payload(client, headers, account):
    aid = account["id"]
    r = await client.post(
        f"{API_PREFIX}/accounts/{aid}/trades",
        json={"market_ticker": "X"},  # missing required fields
        headers=headers,
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_trade_404_for_unknown_account(client, headers, trade_payload):
    r = await client.post(
        f"{API_PREFIX}/accounts/99999/trades", json=trade_payload, headers=headers
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_list_trades_with_filter(client, headers, account, trade, trade_payload):
    aid = account["id"]
    short_trade = dict(trade_payload, market_ticker="VIC", direction="Short",
                       entry_price=50.0, initial_stop=55.0)
    short_resp = await client.post(
        f"{API_PREFIX}/accounts/{aid}/trades", json=short_trade, headers=headers
    )
    assert short_resp.status_code == 201

    all_trades = await client.get(f"{API_PREFIX}/accounts/{aid}/trades", headers=headers)
    assert all_trades.status_code == 200
    body = all_trades.json()
    assert body["total"] == 2
    assert {t["market_ticker"] for t in body["trades"]} == {"FPT", "VIC"}

    longs = await client.get(
        f"{API_PREFIX}/accounts/{aid}/trades?direction=Long", headers=headers
    )
    assert longs.status_code == 200
    assert all(t["direction"] == "Long" for t in longs.json()["trades"])


@pytest.mark.asyncio
async def test_get_trade_404_for_other_user(client, headers, other_user_headers, account, trade):
    r = await client.get(
        f"{API_PREFIX}/accounts/{account['id']}/trades/{trade['id']}",
        headers=other_user_headers,
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_close_trade_via_query_params(client, headers, account, trade):
    aid, tid = account["id"], trade["id"]
    r = await client.post(
        f"{API_PREFIX}/accounts/{aid}/trades/{tid}/close"
        "?exit_price=110&exit_date=2026-01-20&exit_reason=Hit objective_1",
        headers=headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "Closed"
    assert body["exit_price"] == 110.0
    # net_pnl = (110-100) * 1000 - commission(50) = 9,950
    assert body["net_pnl"] == pytest.approx(9950.0)


@pytest.mark.asyncio
async def test_close_trade_rejects_already_closed(client, headers, account, trade):
    aid, tid = account["id"], trade["id"]
    first = await client.post(
        f"{API_PREFIX}/accounts/{aid}/trades/{tid}/close?exit_price=110", headers=headers,
    )
    assert first.status_code == 200

    second = await client.post(
        f"{API_PREFIX}/accounts/{aid}/trades/{tid}/close?exit_price=120", headers=headers,
    )
    assert second.status_code == 400


@pytest.mark.asyncio
async def test_delete_trade(client, headers, account, trade):
    aid, tid = account["id"], trade["id"]
    r = await client.delete(f"{API_PREFIX}/accounts/{aid}/trades/{tid}", headers=headers)
    assert r.status_code == 204
    follow = await client.get(f"{API_PREFIX}/accounts/{aid}/trades/{tid}", headers=headers)
    assert follow.status_code == 404


# ---------------------------------------------------------------------------
# Stop revision — Schwager: "stops only tighten"
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_long_stop_can_only_tighten_upward(client, headers, account, trade):
    """Long entry@100, stop@95. New stop@97 (tighter) is allowed; @93 (looser) is blocked."""
    aid, tid = account["id"], trade["id"]

    looser = await client.post(
        f"{API_PREFIX}/accounts/{aid}/trades/{tid}/stop",
        json={"new_stop": 93.0, "reason": "Trying to widen"},
        headers=headers,
    )
    assert looser.status_code == 400
    assert "thắt chặt" in looser.json()["detail"].lower() or "tighten" in looser.json()["detail"].lower()

    tighter = await client.post(
        f"{API_PREFIX}/accounts/{aid}/trades/{tid}/stop",
        json={"new_stop": 97.0, "reason": "Locking in profit"},
        headers=headers,
    )
    assert tighter.status_code == 200, tighter.text
    assert tighter.json()["revised_stop"] == 97.0


@pytest.mark.asyncio
async def test_short_stop_can_only_tighten_downward(client, headers, account, trade_payload):
    """For a short trade the relationship inverts: new stop must be <= current stop."""
    aid = (await client.post(
        f"{API_PREFIX}/accounts/{account['id']}/trades",
        json=dict(trade_payload, direction="Short", entry_price=50.0, initial_stop=55.0,
                  market_ticker="HPG"),
        headers=headers,
    )).json()
    tid = aid["id"]
    aid = account["id"]

    looser = await client.post(
        f"{API_PREFIX}/accounts/{aid}/trades/{tid}/stop",
        json={"new_stop": 60.0, "reason": "Should be rejected"},
        headers=headers,
    )
    assert looser.status_code == 400

    tighter = await client.post(
        f"{API_PREFIX}/accounts/{aid}/trades/{tid}/stop",
        json={"new_stop": 53.0, "reason": "Lock in"},
        headers=headers,
    )
    assert tighter.status_code == 200
    assert tighter.json()["revised_stop"] == 53.0


@pytest.mark.asyncio
async def test_stop_revision_rejected_on_closed_trade(client, headers, account, trade):
    aid, tid = account["id"], trade["id"]
    closed = await client.post(
        f"{API_PREFIX}/accounts/{aid}/trades/{tid}/close?exit_price=105", headers=headers,
    )
    assert closed.status_code == 200

    r = await client.post(
        f"{API_PREFIX}/accounts/{aid}/trades/{tid}/stop",
        json={"new_stop": 99.0},
        headers=headers,
    )
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# Risk info endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_risk_info_reflects_open_trades(client, headers, account, trade):
    r = await client.get(f"{API_PREFIX}/accounts/{account['id']}/risk", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["open_trade_count"] == 1
    assert body["max_risk_per_trade"] == account["max_risk_per_trade"]
    assert body["current_equity"] == account["current_equity"]
