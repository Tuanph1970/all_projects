"""HTTP-level tests for app/api/routes.py.

The existing per-phase test files exercise the underlying services but
skip the route layer, leaving app/api/routes.py at ~14% coverage.  This
file drives every route via httpx.AsyncClient + ASGITransport with the
DB and external dependencies mocked.

Conventions:
- mock_db is an AsyncMock that returns a MagicMock from .execute().
  Callers configure execute.return_value or execute.side_effect to
  shape the SQL response.
- _scalar_one_or_none / _scalars_all / _scalar_one helpers wrap the
  SQLAlchemy result API so test bodies stay readable.
- get_current_user / get_current_user_optional are overridden to a
  static dict so the JWT middleware never fires.
"""
from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta
from typing import Any, Iterable, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.api.dependencies import (
    get_current_user,
    get_current_user_optional,
    get_db,
)
from app.main import app


PREFIX = "/stock_helper/api/v2/helper"
USER = {"user_id": 1, "email": "u@x.io"}


# ---------------------------------------------------------------------------
# Result-shape helpers
# ---------------------------------------------------------------------------


def _scalar_one_or_none(value):
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    return r


def _scalars_all(rows: Iterable):
    r = MagicMock()
    scal = MagicMock()
    scal.all.return_value = list(rows)
    r.scalars.return_value = scal
    return r


def _scalar_one(value):
    r = MagicMock()
    r.scalar_one.return_value = value
    return r


def _all_rows(rows: Iterable):
    r = MagicMock()
    r.all.return_value = list(rows)
    return r


def _mappings_all(rows: Iterable):
    r = MagicMock()
    m = MagicMock()
    m.all.return_value = list(rows)
    r.mappings.return_value = m
    return r


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def mock_db():
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    return db


@pytest_asyncio.fixture
async def client(mock_db):
    async def _db():
        yield mock_db

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user] = lambda: dict(USER)
    app.dependency_overrides[get_current_user_optional] = lambda: dict(USER)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()


def _pos(**overrides) -> Any:
    """Build a MagicMock that quacks like a PositionState row."""
    base = dict(
        id=1, user_id=1, ticker="VCB", state="LONG",
        entry_bar_date=date(2026, 5, 1), entry_price=80.0,
        position_size=100, current_stop=78.0, current_target=85.0,
        entry_signal_kind="ma_cross_up",
        journal_trade_id=None, last_decision_run_id=None,
    )
    base.update(overrides)
    m = MagicMock(**base)
    return m


def _run(**overrides) -> Any:
    """Build a MagicMock that quacks like a DecisionRun row."""
    base = dict(
        id=10, user_id=1, ticker="VCB", bar_date=date(2026, 5, 20),
        trigger="ON_DEMAND", regime="TREND_UP", signal_kind="ma_cross_up",
        signal_confirmed=True, action="BUY",
        state_before="FLAT", state_after="LONG",
        entry_price=80.0, stop_price=78.0, target_price=85.0,
        position_size=100, confidence=0.82, latency_ms=150,
        created_at=datetime(2026, 5, 20, 12, 0),
        outcome=None, r_multiple=None, exit_run_id=None,
        exit_price=None, ai_review=None,
    )
    base.update(overrides)
    m = MagicMock(**base)
    return m


# ---------------------------------------------------------------------------
# /capabilities and basic health (already covered by test_health.py — sanity)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_capabilities_lists_features(client: AsyncClient):
    r = await client.get(f"{PREFIX}/capabilities")
    assert r.status_code == 200
    body = r.json()
    assert body["service"] == "decision-helper-service"
    assert "scanner" in body["features"]


# ---------------------------------------------------------------------------
# /risk-prefs — GET + PUT
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_risk_prefs_404_when_unset(client: AsyncClient, mock_db):
    mock_db.execute.return_value = _scalar_one_or_none(None)
    r = await client.get(f"{PREFIX}/risk-prefs")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_risk_prefs_returns_existing(client: AsyncClient, mock_db):
    prefs = MagicMock(
        user_id=1, account_equity=100000.0, risk_per_trade_pct=1.0,
        max_concurrent_positions=5, max_correlation=0.7,
        loss_streak_size_cut=0.5, loss_streak_threshold=3,
        journal_account_id=None, updated_at=datetime(2026, 5, 1),
    )
    mock_db.execute.return_value = _scalar_one_or_none(prefs)
    r = await client.get(f"{PREFIX}/risk-prefs")
    assert r.status_code == 200
    assert r.json()["account_equity"] == 100000.0


@pytest.mark.asyncio
async def test_upsert_risk_prefs_creates_new_when_absent(client: AsyncClient, mock_db):
    """First time the user sets prefs — handler builds a new row and adds it.

    The mock for db.refresh needs to populate updated_at because the real
    DB sets it via server_default=func.now() and the response schema
    requires it.
    """
    mock_db.execute.return_value = _scalar_one_or_none(None)

    async def _refresh(obj):
        # Mirror what SQLAlchemy refresh would populate after commit.
        if obj.updated_at is None:
            obj.updated_at = datetime(2026, 5, 20, 12, 0)

    mock_db.refresh.side_effect = _refresh

    body = {
        "account_equity": 50000.0, "risk_per_trade_pct": 1.5,
        "max_concurrent_positions": 3, "max_correlation": 0.5,
        "loss_streak_size_cut": 0.4, "loss_streak_threshold": 2,
        "journal_account_id": 9,
    }
    r = await client.put(f"{PREFIX}/risk-prefs", json=body)
    assert r.status_code == 200, r.text
    mock_db.add.assert_called_once()
    mock_db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_upsert_risk_prefs_updates_when_present(client: AsyncClient, mock_db):
    """Existing row → handler mutates it instead of adding."""
    prefs = MagicMock(
        user_id=1, account_equity=10000.0, risk_per_trade_pct=1.0,
        max_concurrent_positions=5, max_correlation=0.7,
        loss_streak_size_cut=0.5, loss_streak_threshold=3,
        journal_account_id=None, updated_at=datetime(2026, 5, 1),
    )
    mock_db.execute.return_value = _scalar_one_or_none(prefs)

    body = {
        "account_equity": 75000.0, "risk_per_trade_pct": 2.0,
        "max_concurrent_positions": 4, "max_correlation": 0.6,
        "loss_streak_size_cut": 0.3, "loss_streak_threshold": 4,
    }
    r = await client.put(f"{PREFIX}/risk-prefs", json=body)
    assert r.status_code == 200
    mock_db.add.assert_not_called()
    mock_db.commit.assert_awaited()


# ---------------------------------------------------------------------------
# /positions — list + get + update_stop
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_open_positions_returns_only_non_flat(client: AsyncClient, mock_db):
    rows = [_pos(state="LONG"), _pos(ticker="HPG", state="SHORT", entry_price=20)]
    mock_db.execute.return_value = _scalars_all(rows)
    r = await client.get(f"{PREFIX}/positions")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2
    states = {p["state"] for p in body["positions"]}
    assert states == {"LONG", "SHORT"}


@pytest.mark.asyncio
async def test_get_position_returns_flat_when_missing(client: AsyncClient, mock_db):
    mock_db.execute.return_value = _scalar_one_or_none(None)
    r = await client.get(f"{PREFIX}/positions/vcb")
    assert r.status_code == 200
    body = r.json()
    assert body["state"] == "FLAT"
    assert body["ticker"] == "VCB"


@pytest.mark.asyncio
async def test_get_position_returns_existing(client: AsyncClient, mock_db):
    mock_db.execute.return_value = _scalar_one_or_none(_pos())
    r = await client.get(f"{PREFIX}/positions/VCB")
    assert r.status_code == 200
    body = r.json()
    assert body["state"] == "LONG"
    assert body["entry_price"] == 80.0


@pytest.mark.asyncio
async def test_update_position_stop_404_when_no_open_position(client: AsyncClient, mock_db):
    mock_db.execute.return_value = _scalar_one_or_none(None)
    r = await client.put(f"{PREFIX}/positions/VCB/stop", json={"current_stop": 79.0})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_update_position_stop_success(client: AsyncClient, mock_db):
    pos = _pos()
    mock_db.execute.return_value = _scalar_one_or_none(pos)

    async def _refresh(obj):
        # Simulate SQLAlchemy refresh — keep the attribute that was just set.
        pass
    mock_db.refresh.side_effect = _refresh

    r = await client.put(f"{PREFIX}/positions/VCB/stop", json={"current_stop": 79.5})
    assert r.status_code == 200
    # The handler mutates pos.current_stop before commit.
    assert pos.current_stop == 79.5
    mock_db.commit.assert_awaited()


# ---------------------------------------------------------------------------
# /watchlist CRUD
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_watchlist_returns_active_only(client: AsyncClient, mock_db):
    rows = [MagicMock(
        id=1, user_id=1, ticker="VCB", active=True, note="hot",
        created_at=datetime(2026, 5, 1),
    )]
    mock_db.execute.return_value = _scalars_all(rows)
    r = await client.get(f"{PREFIX}/watchlist")
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["ticker"] == "VCB"


@pytest.mark.asyncio
async def test_add_watchlist_creates_new(client: AsyncClient, mock_db):
    mock_db.execute.return_value = _scalar_one_or_none(None)

    captured: list = []

    def _add(obj):
        captured.append(obj)

    mock_db.add.side_effect = _add

    async def _refresh(obj):
        obj.id = 99
        obj.created_at = datetime(2026, 5, 20)
        obj.active = True
    mock_db.refresh.side_effect = _refresh

    r = await client.post(f"{PREFIX}/watchlist", json={"ticker": "vcb", "note": "n"})
    assert r.status_code == 201
    body = r.json()
    assert body["ticker"] == "VCB"
    assert body["note"] == "n"


@pytest.mark.asyncio
async def test_add_watchlist_reactivates_existing(client: AsyncClient, mock_db):
    """An existing soft-deleted entry must be reactivated, not duplicated."""
    existing = MagicMock(
        id=5, user_id=1, ticker="VCB", active=False, note="old",
        created_at=datetime(2026, 4, 1),
    )
    mock_db.execute.return_value = _scalar_one_or_none(existing)

    async def _refresh(obj):
        pass
    mock_db.refresh.side_effect = _refresh

    r = await client.post(f"{PREFIX}/watchlist", json={"ticker": "VCB", "note": "new"})
    assert r.status_code == 201
    assert existing.active is True
    assert existing.note == "new"
    mock_db.add.assert_not_called()


@pytest.mark.asyncio
async def test_remove_watchlist_404_when_missing(client: AsyncClient, mock_db):
    mock_db.execute.return_value = _scalar_one_or_none(None)
    r = await client.delete(f"{PREFIX}/watchlist/VCB")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_remove_watchlist_soft_deletes(client: AsyncClient, mock_db):
    entry = MagicMock(active=True, ticker="VCB", user_id=1)
    mock_db.execute.return_value = _scalar_one_or_none(entry)
    r = await client.delete(f"{PREFIX}/watchlist/VCB")
    assert r.status_code == 204
    assert entry.active is False
    mock_db.commit.assert_awaited()


# ---------------------------------------------------------------------------
# /scheduled-runs and /watchlist/run-all
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scheduled_runs_returns_total_and_runs(client: AsyncClient, mock_db):
    # First execute = COUNT(), second = SELECT rows
    mock_db.execute.side_effect = [
        _scalar_one(7),
        _scalars_all([_run(action="BUY", confidence=0.85)]),
    ]
    r = await client.get(f"{PREFIX}/scheduled-runs?limit=10")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 7
    assert body["runs"][0]["action"] == "BUY"
    assert body["runs"][0]["is_alert"] is True


@pytest.mark.asyncio
async def test_scheduled_runs_alerts_only(client: AsyncClient, mock_db):
    """alerts_only=true narrows the SQL to BUY/SELL_SHORT."""
    mock_db.execute.side_effect = [_scalar_one(0), _scalars_all([])]
    r = await client.get(f"{PREFIX}/scheduled-runs?alerts_only=true")
    assert r.status_code == 200
    assert r.json()["total"] == 0


@pytest.mark.asyncio
async def test_watchlist_run_all_returns_accepted(client: AsyncClient):
    """The handler enqueues `run_for_user(user_id)` via asyncio.create_task.

    Patching scheduler.run_for_user to a no-op AsyncMock means the awaited
    coroutine returns immediately; we still verify the route returned 202.
    """
    with patch(
        "app.services.scheduler.run_for_user",
        new=AsyncMock(return_value=None),
    ):
        r = await client.post(f"{PREFIX}/watchlist/run-all")
        # Give the background task a chance to run (it's a no-op now).
        await asyncio.sleep(0)
    assert r.status_code == 202
    assert r.json()["status"] == "accepted"


# ---------------------------------------------------------------------------
# /alerts (list)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_alerts_list_returns_recent_actionable(client: AsyncClient, mock_db):
    mock_db.execute.return_value = _scalars_all([_run(action="BUY")])
    r = await client.get(f"{PREFIX}/alerts?limit=5")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["alerts"][0]["ticker"] == "VCB"


# ---------------------------------------------------------------------------
# /analytics
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_analytics_zero_data(client: AsyncClient, mock_db):
    """All six queries return empty → response renders with zeros."""
    empty_rows = _all_rows([])
    empty_scalars = MagicMock()
    empty_scalars_inner = MagicMock()
    empty_scalars_inner.all.return_value = []
    empty_scalars.scalars.return_value = empty_scalars_inner

    mock_db.execute.side_effect = [
        empty_rows,      # action_breakdown
        empty_rows,      # regime_breakdown
        empty_rows,      # signal_breakdown
        empty_rows,      # daily_actionable
        empty_rows,      # top_tickers
        empty_scalars,   # confidence histogram
    ]

    r = await client.get(f"{PREFIX}/analytics?days=30")
    assert r.status_code == 200
    body = r.json()
    assert body["total_decisions"] == 0
    assert body["actionable_count"] == 0
    # Histogram still has 10 buckets, all with 0 counts.
    assert len(body["confidence_histogram"]) == 10


@pytest.mark.asyncio
async def test_analytics_with_data(client: AsyncClient, mock_db):
    """Realistic data shape — verify the percentage / aggregation math."""
    action_rows = _all_rows([
        MagicMock(action="BUY", cnt=3),
        MagicMock(action="WAIT", cnt=7),
        MagicMock(action="SELL_SHORT", cnt=2),
    ])
    regime_rows = _all_rows([
        MagicMock(regime="TREND_UP", total=8, buy_c=3, ss_c=0, hw_c=5),
        MagicMock(regime="RANGE", total=4, buy_c=0, ss_c=2, hw_c=2),
    ])
    signal_rows = _all_rows([
        MagicMock(signal_kind="ma_cross_up", fire_count=3,
                  conf_c=2, avg_conf=0.75),
    ])
    daily_rows = _all_rows([
        MagicMock(bar_date=date(2026, 5, 20), cnt=2),
    ])
    ticker_rows = _all_rows([
        MagicMock(ticker="VCB", total=5, buy_c=3, ss_c=0),
    ])
    conf_scalars = MagicMock()
    conf_scalars_inner = MagicMock()
    conf_scalars_inner.all.return_value = [0.82, 0.55, 0.91]
    conf_scalars.scalars.return_value = conf_scalars_inner

    mock_db.execute.side_effect = [
        action_rows, regime_rows, signal_rows,
        daily_rows, ticker_rows, conf_scalars,
    ]

    r = await client.get(f"{PREFIX}/analytics?days=90")
    assert r.status_code == 200
    body = r.json()
    assert body["total_decisions"] == 12
    assert body["actionable_count"] == 5
    # Action breakdown is sorted by count desc; WAIT is biggest.
    assert body["action_breakdown"][0]["action"] == "WAIT"
    # Signal breakdown has confirmation_rate ≈ 0.667
    sb = body["signal_breakdown"][0]
    assert sb["confirmation_rate"] == pytest.approx(0.667, rel=1e-2)
    # Confidence histogram bucketed 3 values: 80-90, 50-60, 90-100 (clamped to 90-100)
    buckets = {b["bucket"]: b["count"] for b in body["confidence_histogram"]}
    assert buckets["80-90%"] == 1
    assert buckets["50-60%"] == 1
    assert buckets["90-100%"] == 1


# ---------------------------------------------------------------------------
# /outcomes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_outcomes_summarizes_wins_losses(client: AsyncClient, mock_db):
    rows = [
        _run(action="BUY", outcome="WIN", r_multiple=1.5, exit_price=85.0),
        _run(action="BUY", outcome="LOSS", r_multiple=-1.0, exit_price=77.0),
        _run(action="SELL_SHORT", outcome="WIN", r_multiple=2.0, exit_price=18.0),
    ]
    mock_db.execute.return_value = _scalars_all(rows)
    r = await client.get(f"{PREFIX}/outcomes?days=30")
    assert r.status_code == 200
    body = r.json()
    s = body["summary"]
    assert s["total_tagged"] == 3
    assert s["wins"] == 2
    assert s["losses"] == 1
    assert s["win_rate"] == pytest.approx(0.667, rel=1e-2)


@pytest.mark.asyncio
async def test_outcomes_handles_empty(client: AsyncClient, mock_db):
    mock_db.execute.return_value = _scalars_all([])
    r = await client.get(f"{PREFIX}/outcomes")
    body = r.json()
    assert body["summary"]["total_tagged"] == 0
    assert body["summary"]["avg_r"] is None
    assert body["summary"]["expectancy"] is None


# ---------------------------------------------------------------------------
# /attribution
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_attribution_empty_returns_zero_rows(client: AsyncClient, mock_db):
    mock_db.execute.return_value = _scalars_all([])
    r = await client.get(f"{PREFIX}/attribution?days=30")
    assert r.status_code == 200
    body = r.json()
    assert body["total_tagged"] == 0


@pytest.mark.asyncio
async def test_attribution_with_data(client: AsyncClient, mock_db):
    """One entry run with no exit run — breakdown still computes."""
    entry = _run(
        action="BUY", outcome="WIN", r_multiple=2.0,
        signal_kind="ma_cross_up", regime="TREND_UP",
        bar_date=date(2026, 5, 1), exit_run_id=None,
    )
    mock_db.execute.return_value = _scalars_all([entry])
    r = await client.get(f"{PREFIX}/attribution?days=30")
    assert r.status_code == 200
    body = r.json()
    assert body["total_tagged"] == 1
    # by_signal should have at least one row
    assert len(body["by_signal"]) >= 1


# ---------------------------------------------------------------------------
# /outcomes/{run_id}/review — AI trade review
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_review_404_when_run_missing(client: AsyncClient, mock_db):
    mock_db.execute.return_value = _scalar_one_or_none(None)
    r = await client.post(f"{PREFIX}/outcomes/999/review")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_review_422_when_no_outcome(client: AsyncClient, mock_db):
    """Run exists but outcome not tagged yet → 422."""
    run = _run(outcome=None)
    mock_db.execute.return_value = _scalar_one_or_none(run)
    r = await client.post(f"{PREFIX}/outcomes/{run.id}/review")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_review_returns_cached_when_present(client: AsyncClient, mock_db):
    run = _run(outcome="WIN", ai_review="cached review text")
    mock_db.execute.return_value = _scalar_one_or_none(run)
    r = await client.post(f"{PREFIX}/outcomes/{run.id}/review")
    assert r.status_code == 200
    body = r.json()
    assert body["generated"] is False
    assert body["ai_review"] == "cached review text"


@pytest.mark.asyncio
async def test_review_generates_when_missing(client: AsyncClient, mock_db):
    run = _run(outcome="WIN", ai_review=None)
    mock_db.execute.return_value = _scalar_one_or_none(run)
    with patch(
        "app.services.ai_review.generate_trade_review",
        new=AsyncMock(return_value="fresh review"),
    ):
        r = await client.post(f"{PREFIX}/outcomes/{run.id}/review")
    assert r.status_code == 200
    body = r.json()
    assert body["generated"] is True
    assert body["ai_review"] == "fresh review"


@pytest.mark.asyncio
async def test_review_returns_none_when_llm_fails(client: AsyncClient, mock_db):
    run = _run(outcome="WIN", ai_review=None)
    mock_db.execute.return_value = _scalar_one_or_none(run)
    with patch(
        "app.services.ai_review.generate_trade_review",
        new=AsyncMock(return_value=None),
    ):
        r = await client.post(f"{PREFIX}/outcomes/{run.id}/review")
    assert r.status_code == 200
    body = r.json()
    assert body["generated"] is False
    assert body["ai_review"] is None


# ---------------------------------------------------------------------------
# /risk-overview
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_risk_overview_no_positions(client: AsyncClient, mock_db):
    """First execute = prefs lookup, second = positions list."""
    mock_db.execute.side_effect = [
        _scalar_one_or_none(MagicMock(account_equity=100000.0)),
        _scalars_all([]),
    ]
    r = await client.get(f"{PREFIX}/risk-overview")
    assert r.status_code == 200
    body = r.json()
    assert body["total_positions"] == 0
    assert body["total_risk_amount"] == 0.0


@pytest.mark.asyncio
async def test_risk_overview_with_long_and_short(client: AsyncClient, mock_db):
    prefs = MagicMock(account_equity=100000.0)
    positions = [
        _pos(state="LONG", entry_price=80.0, current_stop=78.0, position_size=100),
        _pos(state="SHORT", ticker="HPG", entry_price=20.0, current_stop=21.0,
             position_size=200, entry_bar_date=date(2026, 4, 15)),
    ]
    mock_db.execute.side_effect = [
        _scalar_one_or_none(prefs),
        _scalars_all(positions),
    ]
    r = await client.get(f"{PREFIX}/risk-overview")
    assert r.status_code == 200
    body = r.json()
    assert body["total_positions"] == 2
    assert body["long_count"] == 1
    assert body["short_count"] == 1
    # Long: |80-78| × 100 = 200; Short: |20-21| × 200 = 200; total = 400
    assert body["total_risk_amount"] == pytest.approx(400.0)


@pytest.mark.asyncio
async def test_risk_overview_no_account_equity_pct_falls_back_to_zero(
    client: AsyncClient, mock_db
):
    """If account_equity is None, the %-of-equity figures are 0."""
    mock_db.execute.side_effect = [
        _scalar_one_or_none(None),  # no prefs row at all
        _scalars_all([_pos(state="LONG", entry_price=80, current_stop=78, position_size=10)]),
    ]
    r = await client.get(f"{PREFIX}/risk-overview")
    assert r.status_code == 200
    body = r.json()
    assert body["account_equity"] is None
    assert body["total_risk_pct"] == 0.0


# ---------------------------------------------------------------------------
# /correlation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_correlation_returns_empty_when_fewer_than_two_positions(
    client: AsyncClient, mock_db
):
    mock_db.execute.side_effect = [
        _scalar_one_or_none(MagicMock(max_correlation=0.7)),
        _scalars_all([_pos(ticker="VCB")]),
    ]
    r = await client.get(f"{PREFIX}/correlation")
    assert r.status_code == 200
    body = r.json()
    assert body["tickers"] == ["VCB"]
    assert body["pairs"] == []
    assert body["any_breach"] is False


@pytest.mark.asyncio
async def test_correlation_computes_pairs_and_flags_breach(client: AsyncClient, mock_db):
    mock_db.execute.side_effect = [
        _scalar_one_or_none(MagicMock(max_correlation=0.7)),
        _scalars_all([_pos(ticker="VCB"), _pos(ticker="TCB")]),
    ]
    matrix = {"VCB": {"TCB": 0.85}, "TCB": {"VCB": 0.85}}
    with patch(
        "app.services.correlation.compute_correlation_matrix",
        new=AsyncMock(return_value=matrix),
    ):
        r = await client.get(f"{PREFIX}/correlation")
    assert r.status_code == 200
    body = r.json()
    assert body["any_breach"] is True
    assert len(body["pairs"]) == 1
    assert body["pairs"][0]["breaches_limit"] is True


# ---------------------------------------------------------------------------
# /discipline/summary + /discipline/validate-plan
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_discipline_summary_no_prefs(client: AsyncClient, mock_db):
    """No prefs row → defaults kick in (loss_streak_threshold=3)."""
    mock_db.execute.side_effect = [
        _scalar_one_or_none(None),       # prefs
        _scalars_all(["WAIT", "HOLD"]),  # last 10 actions
    ]
    r = await client.get(f"{PREFIX}/discipline/summary")
    assert r.status_code == 200
    body = r.json()
    assert body["loss_streak_threshold"] == 3
    assert body["recent_losses"] == 0
    assert body["streak_active"] is False


@pytest.mark.asyncio
async def test_discipline_summary_streak_active(client: AsyncClient, mock_db):
    """Three consecutive SELL actions trigger streak_active."""
    mock_db.execute.side_effect = [
        _scalar_one_or_none(MagicMock(
            loss_streak_threshold=3, account_equity=100000.0,
        )),
        _scalars_all(["SELL", "SELL", "SELL", "BUY"]),
    ]
    r = await client.get(f"{PREFIX}/discipline/summary")
    body = r.json()
    assert body["recent_losses"] == 3
    assert body["streak_active"] is True


@pytest.mark.asyncio
async def test_validate_plan_blocks_when_stop_missing(client: AsyncClient, mock_db):
    """No stop → discipline_check returns a BLOCK violation; is_valid=False."""
    mock_db.execute.side_effect = [
        _scalar_one_or_none(None),                 # prefs
        _scalar_one_or_none(None),                 # position
        _scalars_all([]),                          # losses
    ]
    body = {
        "ticker": "VCB", "action": "BUY",
        "entry_price": 80.0, "stop_price": None, "target_price": 85.0,
        "direction": "LONG",
    }
    r = await client.post(f"{PREFIX}/discipline/validate-plan", json=body)
    assert r.status_code == 200
    out = r.json()
    assert out["is_valid"] is False
    block_ids = [v["rule_id"] for v in out["violations"] if v["severity"] == "BLOCK"]
    assert block_ids


@pytest.mark.asyncio
async def test_validate_plan_accepts_complete_plan(client: AsyncClient, mock_db):
    mock_db.execute.side_effect = [
        _scalar_one_or_none(None),
        _scalar_one_or_none(None),
        _scalars_all([]),
    ]
    body = {
        "ticker": "VCB", "action": "BUY",
        "entry_price": 80.0, "stop_price": 78.0, "target_price": 85.0,
        "direction": "LONG", "regime": "TREND_UP",
    }
    r = await client.post(f"{PREFIX}/discipline/validate-plan", json=body)
    assert r.status_code == 200
    assert r.json()["is_valid"] is True


# ---------------------------------------------------------------------------
# /signal-analysis (POST)
# ---------------------------------------------------------------------------


def _bars(n: int = 60, start_date: date = date(2026, 4, 1)) -> list[dict]:
    out = []
    for i in range(n):
        d = start_date + timedelta(days=i)
        out.append({
            "date": d.isoformat(),
            "open": 80.0 + i * 0.1, "high": 81.0 + i * 0.1,
            "low": 79.0 + i * 0.1, "close": 80.5 + i * 0.1,
            "volume": 1000 + i,
        })
    return out


@pytest.mark.asyncio
async def test_signal_analysis_404_when_no_ohlcv(client: AsyncClient):
    mc = MagicMock()
    mc.fetch_ohlcv = AsyncMock(return_value=[])
    with patch("app.api.routes.get_market_client", return_value=mc), \
         patch("app.api.routes.classify_regime",
               new=AsyncMock(return_value=MagicMock(
                   regime="TREND_UP", confidence=0.8, features={},
               ))):
        r = await client.post(f"{PREFIX}/signal-analysis", json={
            "ticker": "VCB", "bar_date": "2026-05-20",
        })
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_signal_analysis_422_when_bar_date_missing_from_series(client: AsyncClient):
    mc = MagicMock()
    mc.fetch_ohlcv = AsyncMock(return_value=_bars(30, date(2026, 1, 1)))
    mc.fetch_technical = AsyncMock(return_value=None)
    mc.fetch_sr_levels = AsyncMock(return_value=None)
    with patch("app.api.routes.get_market_client", return_value=mc), \
         patch("app.api.routes.classify_regime",
               new=AsyncMock(return_value=MagicMock(
                   regime="TREND_UP", confidence=0.8, features={},
               ))):
        r = await client.post(f"{PREFIX}/signal-analysis", json={
            "ticker": "VCB", "bar_date": "2099-01-01",
        })
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_signal_analysis_returns_response(client: AsyncClient):
    """Happy path through the trend branch (TREND_UP regime)."""
    bars = _bars(60, date(2026, 3, 1))
    bar_date_iso = bars[-5]["date"]   # pick a date that's in the series
    mc = MagicMock()
    mc.fetch_ohlcv = AsyncMock(return_value=bars)
    mc.fetch_technical = AsyncMock(return_value={
        "indicators": [{"name": "RSI", "value": 55.0}],
    })
    mc.fetch_sr_levels = AsyncMock(return_value=None)
    with patch("app.api.routes.get_market_client", return_value=mc), \
         patch("app.api.routes.classify_regime",
               new=AsyncMock(return_value=MagicMock(
                   regime="TREND_UP", confidence=0.8, features={},
               ))):
        r = await client.post(f"{PREFIX}/signal-analysis", json={
            "ticker": "VCB", "bar_date": bar_date_iso,
        })
    assert r.status_code == 200
    body = r.json()
    assert body["ticker"] == "VCB"
    assert body["regime"] == "TREND_UP"
    assert "signals" in body


@pytest.mark.asyncio
async def test_signal_analysis_range_branch(client: AsyncClient):
    """RANGE regime routes to S/R bounce/breakout detector."""
    bars = _bars(60, date(2026, 3, 1))
    bar_date_iso = bars[-5]["date"]
    mc = MagicMock()
    mc.fetch_ohlcv = AsyncMock(return_value=bars)
    mc.fetch_technical = AsyncMock(return_value=None)
    mc.fetch_sr_levels = AsyncMock(return_value={
        "support": [{"price": 79.0}], "resistance": [{"price": 85.0}],
    })
    with patch("app.api.routes.get_market_client", return_value=mc), \
         patch("app.api.routes.classify_regime",
               new=AsyncMock(return_value=MagicMock(
                   regime="RANGE", confidence=0.7, features={},
               ))):
        r = await client.post(f"{PREFIX}/signal-analysis", json={
            "ticker": "VCB", "bar_date": bar_date_iso,
        })
    assert r.status_code == 200
    assert r.json()["regime"] == "RANGE"


# ---------------------------------------------------------------------------
# /recommend — orchestrator wrapper (correlation + journal + AI-review side effects)
# ---------------------------------------------------------------------------


def _rec(**overrides) -> Any:
    """Build a RecommendationResponse-shaped MagicMock."""
    from app.models.schemas import RecommendationResponse
    base = dict(
        user_id=1, ticker="VCB", bar_date=date(2026, 5, 20),
        trigger="ON_DEMAND", regime="TREND_UP",
        action="BUY", state_before="FLAT", state_after="LONG",
        entry_price=80.0, stop_price=78.0, target_price=85.0,
        position_size=100, confidence=0.82,
        signal_kind="ma_cross_up", signal_confirmed=True,
        reason_chain=[], discipline_violations=[], rule_advisories=[],
        latency_ms=100, generated_at=datetime(2026, 5, 20),
    )
    base.update(overrides)
    return RecommendationResponse(**base)


@pytest.mark.asyncio
async def test_recommend_happy_path_no_jwt_header(client: AsyncClient, mock_db):
    """Without an Authorization header the journal-sync block is skipped."""
    rec = _rec()
    with patch("app.api.routes.run_recommendation",
               new=AsyncMock(return_value=rec)), \
         patch("app.api.routes.get_market_client", return_value=MagicMock()):
        r = await client.post(f"{PREFIX}/recommend", json={
            "ticker": "VCB", "bar_date": "2026-05-20", "trigger": "ON_DEMAND",
        })
    assert r.status_code == 200
    body = r.json()
    assert body["action"] == "BUY"


@pytest.mark.asyncio
async def test_recommend_correlation_block_downgrades_to_wait(
    client: AsyncClient, mock_db
):
    """When adding the ticker would breach max_correlation, action -> WAIT."""
    rec = _rec(action="BUY")
    # Inside the correlation block:
    # 1. prefs lookup -> max_correlation=0.5
    # 2. open positions -> one ticker "HPG"
    mock_db.execute.side_effect = [
        _scalar_one_or_none(MagicMock(max_correlation=0.5)),
        _scalars_all([_pos(ticker="HPG")]),
        # Journal-sync block runs next; we make prefs missing so it's a no-op.
        _scalar_one_or_none(None),
    ]
    matrix = {"VCB": {"HPG": 0.85}, "HPG": {"VCB": 0.85}}
    with patch("app.api.routes.run_recommendation",
               new=AsyncMock(return_value=rec)), \
         patch("app.api.routes.get_market_client", return_value=MagicMock()), \
         patch("app.services.correlation.compute_correlation_matrix",
               new=AsyncMock(return_value=matrix)):
        r = await client.post(
            f"{PREFIX}/recommend",
            json={"ticker": "VCB", "bar_date": "2026-05-20"},
            headers={"Authorization": "Bearer fake-jwt"},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["action"] == "WAIT"
    violations = body["discipline_violations"]
    assert any(v["rule_id"] == "RULE_CORR_001" for v in violations)


@pytest.mark.asyncio
async def test_recommend_correlation_no_existing_positions_skipped(
    client: AsyncClient, mock_db
):
    """No open positions besides the target ticker → correlation check is
    skipped entirely (no matrix call)."""
    rec = _rec(action="BUY")
    mock_db.execute.side_effect = [
        _scalar_one_or_none(MagicMock(max_correlation=0.5)),
        _scalars_all([]),                 # no open positions
        _scalar_one_or_none(None),        # no journal prefs
    ]
    with patch("app.api.routes.run_recommendation",
               new=AsyncMock(return_value=rec)), \
         patch("app.api.routes.get_market_client", return_value=MagicMock()), \
         patch("app.services.correlation.compute_correlation_matrix",
               new=AsyncMock(side_effect=AssertionError("should not call"))):
        r = await client.post(
            f"{PREFIX}/recommend",
            json={"ticker": "VCB", "bar_date": "2026-05-20"},
            headers={"Authorization": "Bearer fake-jwt"},
        )
    assert r.status_code == 200
    assert r.json()["action"] == "BUY"


@pytest.mark.asyncio
async def test_recommend_journal_sync_skipped_when_no_account(client: AsyncClient, mock_db):
    """User has no linked journal account → journal_sync field stays None."""
    rec = _rec(action="HOLD")  # HOLD bypasses the correlation block
    mock_db.execute.side_effect = [
        _scalar_one_or_none(None),  # journal prefs missing
    ]
    with patch("app.api.routes.run_recommendation",
               new=AsyncMock(return_value=rec)), \
         patch("app.api.routes.get_market_client", return_value=MagicMock()):
        r = await client.post(
            f"{PREFIX}/recommend",
            json={"ticker": "VCB", "bar_date": "2026-05-20"},
            headers={"Authorization": "Bearer fake-jwt"},
        )
    assert r.status_code == 200
    assert r.json()["journal_sync"] is None


@pytest.mark.asyncio
async def test_recommend_journal_sync_open_for_buy(client: AsyncClient, mock_db):
    """BUY + journal_account_id → background task spawned, journal_sync.action = 'open'."""
    rec = _rec(action="BUY")
    mock_db.execute.side_effect = [
        _scalar_one_or_none(MagicMock(max_correlation=0.7)),
        _scalars_all([]),                                       # no other positions
        _scalar_one_or_none(MagicMock(journal_account_id=9)),   # journal account linked
        _scalar_one_or_none(_pos(state="FLAT", ticker="VCB")),  # current position
    ]

    captured_tasks = []

    def _fake_create_task(coro):
        captured_tasks.append(coro)
        coro.close()
        return MagicMock()

    with patch("app.api.routes.run_recommendation",
               new=AsyncMock(return_value=rec)), \
         patch("app.api.routes.get_market_client", return_value=MagicMock()), \
         patch("asyncio.create_task", side_effect=_fake_create_task):
        r = await client.post(
            f"{PREFIX}/recommend",
            json={"ticker": "VCB", "bar_date": "2026-05-20"},
            headers={"Authorization": "Bearer fake-jwt"},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["journal_sync"]["action"] == "open"
    assert len(captured_tasks) >= 1


@pytest.mark.asyncio
async def test_recommend_journal_sync_close_for_sell(client: AsyncClient, mock_db):
    rec = _rec(action="SELL", entry_price=85.0, stop_price=None, target_price=None,
               state_before="LONG", state_after="FLAT")
    mock_db.execute.side_effect = [
        _scalar_one_or_none(MagicMock(journal_account_id=9)),       # prefs
        _scalar_one_or_none(_pos(state="LONG", journal_trade_id=42)),  # current position
    ]

    captured_tasks = []

    def _fake_create_task(coro):
        captured_tasks.append(coro)
        coro.close()
        return MagicMock()

    with patch("app.api.routes.run_recommendation",
               new=AsyncMock(return_value=rec)), \
         patch("app.api.routes.get_market_client", return_value=MagicMock()), \
         patch("asyncio.create_task", side_effect=_fake_create_task):
        r = await client.post(
            f"{PREFIX}/recommend",
            json={"ticker": "VCB", "bar_date": "2026-05-20"},
            headers={"Authorization": "Bearer fake-jwt"},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["journal_sync"]["action"] == "close"
    assert body["journal_sync"]["journal_trade_id"] == 42


# ---------------------------------------------------------------------------
# /scan
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scan_empty_watchlist(client: AsyncClient, mock_db):
    mock_db.execute.return_value = _scalars_all([])
    r = await client.post(f"{PREFIX}/scan", json={})
    assert r.status_code == 200
    body = r.json()
    assert body["ticker_count"] == 0
    assert body["results"] == []


@pytest.mark.asyncio
async def test_scan_with_watchlist_ranks_actionable_first(client: AsyncClient, mock_db):
    """Two watchlist tickers — one BUY, one WAIT — verify ranking."""
    mock_db.execute.return_value = _scalars_all([
        MagicMock(ticker="VCB"), MagicMock(ticker="HPG"),
    ])

    async def _fake_rec(user_id, ticker, bar_date, trigger, db, client):
        if ticker == "VCB":
            return _rec(action="BUY", ticker="VCB", confidence=0.8)
        return _rec(action="WAIT", ticker="HPG", confidence=0.3,
                    signal_kind=None, signal_confirmed=False)

    with patch("app.api.routes.run_recommendation", new=AsyncMock(side_effect=_fake_rec)), \
         patch("app.api.routes.get_market_client", return_value=MagicMock()), \
         patch("app.api.dependencies.async_session_factory") as factory:
        # async_session_factory() returns an async-context-manager session.
        session_cm = AsyncMock()
        session_cm.__aenter__ = AsyncMock(return_value=mock_db)
        session_cm.__aexit__ = AsyncMock(return_value=False)
        factory.return_value = session_cm
        r = await client.post(f"{PREFIX}/scan", json={})
    assert r.status_code == 200
    body = r.json()
    assert body["ticker_count"] == 2
    assert body["actionable_count"] == 1
    # BUY ranks first.
    assert body["results"][0]["action"] == "BUY"


@pytest.mark.asyncio
async def test_scan_captures_per_ticker_failures(client: AsyncClient, mock_db):
    """An exception in run_recommendation for one ticker → that ticker's
    item carries an `error` field but the scan still completes."""
    mock_db.execute.return_value = _scalars_all([MagicMock(ticker="VCB")])

    async def _fake_rec(*args, **kwargs):
        raise RuntimeError("upstream down")

    with patch("app.api.routes.run_recommendation", new=AsyncMock(side_effect=_fake_rec)), \
         patch("app.api.routes.get_market_client", return_value=MagicMock()), \
         patch("app.api.dependencies.async_session_factory") as factory:
        session_cm = AsyncMock()
        session_cm.__aenter__ = AsyncMock(return_value=mock_db)
        session_cm.__aexit__ = AsyncMock(return_value=False)
        factory.return_value = session_cm
        r = await client.post(f"{PREFIX}/scan", json={})
    body = r.json()
    assert body["ticker_count"] == 1
    assert body["actionable_count"] == 0
    assert body["results"][0]["error"] == "upstream down"


# ---------------------------------------------------------------------------
# /backtest
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_backtest_404_when_no_bars(client: AsyncClient):
    mc = MagicMock()
    mc.fetch_ohlcv = AsyncMock(return_value=[])
    with patch("app.api.routes.get_market_client", return_value=mc):
        r = await client.post(f"{PREFIX}/backtest", json={
            "ticker": "VCB",
            "start_date": "2026-01-01", "end_date": "2026-03-01",
        })
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_backtest_happy_path(client: AsyncClient):
    """Drive the route through to BacktestResultSchema construction.  We
    stub run_backtest_on_bars / walk-forward so the response shape is
    deterministic."""
    mc = MagicMock()
    mc.fetch_ohlcv = AsyncMock(return_value=_bars(120, date(2025, 12, 1)))

    fake_result = MagicMock()
    fake_result.ticker = "VCB"
    fake_result.start_date = date(2026, 1, 1)
    fake_result.end_date = date(2026, 3, 1)
    fake_result.config = {"fast_ma": 10}
    fake_result.trade_ledger = []
    fake_result.equity_curve = []
    fake_stats = MagicMock()
    # Provide BacktestStatsSchema-shaped data via vars(stats).
    fake_stats.__dict__.update(dict(
        num_trades=0, num_wins=0, win_rate=0.0, total_gross_pnl=0.0,
        total_commission=0.0, total_net_pnl=0.0, max_drawdown_pct=0.0,
        expectancy=0.0, sharpe_ratio=None, profit_factor=None,
    ))
    fake_result.stats = fake_stats

    with patch("app.api.routes.get_market_client", return_value=mc), \
         patch("app.services.backtest.harness.run_backtest_on_bars",
               return_value=fake_result):
        r = await client.post(f"{PREFIX}/backtest", json={
            "ticker": "VCB",
            "start_date": "2026-01-01", "end_date": "2026-03-01",
        })
    assert r.status_code == 200
    body = r.json()
    assert body["ticker"] == "VCB"
    assert body["stats"]["num_trades"] == 0


@pytest.mark.asyncio
async def test_backtest_with_sensitivity_report(client: AsyncClient):
    """F-053 — sensitivity=true attaches a SensitivityReport to the response."""
    from app.services.backtest.harness import BacktestStats
    from app.services.backtest.sensitivity import ParamVariant, SensitivityReport

    mc = MagicMock()
    mc.fetch_ohlcv = AsyncMock(return_value=_bars(120, date(2025, 12, 1)))

    fake_result = MagicMock()
    fake_result.ticker = "VCB"
    fake_result.start_date = date(2026, 1, 1)
    fake_result.end_date = date(2026, 3, 1)
    fake_result.config = {}
    fake_result.trade_ledger = []
    fake_result.equity_curve = []
    stats = BacktestStats(
        num_trades=0, num_wins=0, win_rate=0.0, total_gross_pnl=0.0,
        total_commission=0.0, total_net_pnl=0.0, max_drawdown_pct=0.0,
        expectancy=0.0, sharpe_ratio=None, profit_factor=None,
    )
    fake_result.stats = stats

    report = SensitivityReport(
        metric_name="total_net_pnl", base_metric=100.0,
        variants=[ParamVariant("base", {}, 100.0, stats)],
        mean=100.0, std=0.0, cv=0.0, min=100.0, max=100.0,
        fragile=False, reason="stable",
    )

    with patch("app.api.routes.get_market_client", return_value=mc), \
         patch("app.services.backtest.harness.run_backtest_on_bars",
               return_value=fake_result), \
         patch("app.services.backtest.sensitivity.run_param_sensitivity",
               return_value=report):
        r = await client.post(f"{PREFIX}/backtest", json={
            "ticker": "VCB",
            "start_date": "2026-01-01", "end_date": "2026-03-01",
            "sensitivity": True,
        })
    assert r.status_code == 200
    body = r.json()
    assert body["sensitivity"]["fragile"] is False
    assert body["sensitivity"]["metric_name"] == "total_net_pnl"
    assert body["sensitivity"]["variants"][0]["label"] == "base"


@pytest.mark.asyncio
async def test_backtest_no_sensitivity_by_default(client: AsyncClient):
    """Without the flag, the sensitivity field stays null."""
    mc = MagicMock()
    mc.fetch_ohlcv = AsyncMock(return_value=_bars(120, date(2025, 12, 1)))
    fake_result = MagicMock()
    fake_result.ticker = "VCB"
    fake_result.start_date = date(2026, 1, 1)
    fake_result.end_date = date(2026, 3, 1)
    fake_result.config = {}
    fake_result.trade_ledger = []
    fake_result.equity_curve = []
    fake_stats = MagicMock()
    fake_stats.__dict__.update(dict(
        num_trades=0, num_wins=0, win_rate=0.0, total_gross_pnl=0.0,
        total_commission=0.0, total_net_pnl=0.0, max_drawdown_pct=0.0,
        expectancy=0.0, sharpe_ratio=None, profit_factor=None,
    ))
    fake_result.stats = fake_stats

    with patch("app.api.routes.get_market_client", return_value=mc), \
         patch("app.services.backtest.harness.run_backtest_on_bars",
               return_value=fake_result):
        r = await client.post(f"{PREFIX}/backtest", json={
            "ticker": "VCB", "start_date": "2026-01-01", "end_date": "2026-03-01",
        })
    assert r.status_code == 200
    assert r.json()["sensitivity"] is None
