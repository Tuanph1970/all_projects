"""Tests for PortfolioRepository — exercise the repo methods directly
with a mocked AsyncSession.

Each test wires the session.execute() return value to the shape the
repo expects (scalar_one_or_none / scalars().all() / rowcount / etc.)
and verifies the repo's branching + commit/refresh dance.
"""
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.domain import (
    AlertType,
    Portfolio,
    PortfolioHolding,
    PriceAlert,
    Transaction,
    TransactionType,
)
from app.repositories.portfolio_repository import PortfolioRepository


def _session_returning_scalar(value):
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    session.execute = AsyncMock(return_value=result)
    return session


def _session_returning_list(rows):
    session = AsyncMock()
    result = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = rows
    result.scalars.return_value = scalars
    session.execute = AsyncMock(return_value=result)
    return session


def _session_with_rowcount(rc):
    session = AsyncMock()
    result = MagicMock()
    result.rowcount = rc
    session.execute = AsyncMock(return_value=result)
    session.commit = AsyncMock()
    return session


def _portfolio(id=1, user_id=1, is_default=False) -> Portfolio:
    return Portfolio(
        id=id, user_id=user_id, name="P1", description=None,
        is_default=is_default,
        created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
    )


def _holding(id=1, portfolio_id=1, symbol="FPT", quantity=10) -> PortfolioHolding:
    return PortfolioHolding(
        id=id, portfolio_id=portfolio_id, symbol=symbol,
        quantity=quantity, average_price=100.0, total_cost=1000.0,
        is_watchlist_only=False,
        created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
    )


# ---------------------------------------------------------------------------
# Portfolio CRUD
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_portfolio_adds_commits_and_refreshes():
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    repo = PortfolioRepository(session)
    portfolio = await repo.create_portfolio(
        user_id=1, name="My Portfolio", description="d", is_default=True,
    )
    assert isinstance(portfolio, Portfolio)
    assert portfolio.is_default is True
    session.add.assert_called_once_with(portfolio)
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(portfolio)


@pytest.mark.asyncio
async def test_get_portfolio_by_id_returns_row_or_none():
    expected = _portfolio()
    session = _session_returning_scalar(expected)
    repo = PortfolioRepository(session)
    assert (await repo.get_portfolio_by_id(1, 1)) is expected

    none_session = _session_returning_scalar(None)
    assert (await PortfolioRepository(none_session).get_portfolio_by_id(99, 1)) is None


@pytest.mark.asyncio
async def test_get_portfolios_by_user_returns_rows():
    rows = [_portfolio(id=1), _portfolio(id=2)]
    session = _session_returning_list(rows)
    repo = PortfolioRepository(session)
    out = await repo.get_portfolios_by_user(user_id=1)
    assert [p.id for p in out] == [1, 2]


@pytest.mark.asyncio
async def test_get_default_portfolio_returns_row_or_none():
    expected = _portfolio(is_default=True)
    repo = PortfolioRepository(_session_returning_scalar(expected))
    assert (await repo.get_default_portfolio(user_id=1)) is expected


@pytest.mark.asyncio
async def test_update_portfolio_runs_update_then_refetch():
    """update_portfolio fires UPDATE then calls get_portfolio_by_id."""
    session = AsyncMock()
    update_result = MagicMock()
    fetch_result = MagicMock()
    refreshed = _portfolio(id=1)
    fetch_result.scalar_one_or_none.return_value = refreshed
    session.execute = AsyncMock(side_effect=[update_result, fetch_result])
    session.commit = AsyncMock()

    repo = PortfolioRepository(session)
    out = await repo.update_portfolio(1, 1, name="Renamed")
    assert out is refreshed
    assert session.execute.await_count == 2
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_portfolio_returns_true_when_row_deleted():
    session = _session_with_rowcount(1)
    repo = PortfolioRepository(session)
    assert (await repo.delete_portfolio(1, 1)) is True


@pytest.mark.asyncio
async def test_delete_portfolio_returns_false_when_no_rows_affected():
    session = _session_with_rowcount(0)
    repo = PortfolioRepository(session)
    assert (await repo.delete_portfolio(99, 1)) is False


# ---------------------------------------------------------------------------
# Holdings
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_add_holding_persists_with_uppercased_symbol():
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    repo = PortfolioRepository(session)
    h = await repo.add_holding(portfolio_id=1, symbol="fpt", quantity=10, average_price=100.0)
    assert h.symbol == "FPT"
    assert h.total_cost == 1000.0


@pytest.mark.asyncio
async def test_get_holding_uppercases_input():
    expected = _holding(symbol="FPT")
    session = _session_returning_scalar(expected)
    repo = PortfolioRepository(session)
    out = await repo.get_holding(portfolio_id=1, symbol="fpt")
    assert out is expected


@pytest.mark.asyncio
async def test_get_holdings_by_portfolio_with_watchlist_only_filter():
    rows = [_holding(id=1), _holding(id=2)]
    session = _session_returning_list(rows)
    repo = PortfolioRepository(session)
    out = await repo.get_holdings_by_portfolio(portfolio_id=1, watchlist_only=True)
    assert len(out) == 2


@pytest.mark.asyncio
async def test_delete_holding_returns_true_when_row_deleted():
    session = _session_with_rowcount(1)
    repo = PortfolioRepository(session)
    assert (await repo.delete_holding(holding_id=1)) is True


@pytest.mark.asyncio
async def test_delete_holding_returns_false_when_missing():
    session = _session_with_rowcount(0)
    repo = PortfolioRepository(session)
    assert (await repo.delete_holding(holding_id=999)) is False


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_transaction_persists_with_uppercase_symbol():
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    repo = PortfolioRepository(session)
    t = await repo.create_transaction(
        portfolio_id=1, symbol="fpt", transaction_type=TransactionType.BUY,
        quantity=10, price=100.0, fees=5.0,
    )
    assert t.symbol == "FPT"
    # total_value = quantity × price (without fees)
    assert t.total_value == 1000.0


@pytest.mark.asyncio
async def test_get_transaction_by_id_returns_row_or_none():
    expected = Transaction(
        id=1, portfolio_id=1, symbol="FPT",
        transaction_type=TransactionType.BUY,
        quantity=10, price=100.0, total_value=1000.0, fees=0,
        notes=None, transaction_date=datetime.utcnow(),
        created_at=datetime.utcnow(),
    )
    repo = PortfolioRepository(_session_returning_scalar(expected))
    assert (await repo.get_transaction_by_id(1)) is expected


@pytest.mark.asyncio
async def test_delete_transaction_returns_true_when_row_deleted():
    session = _session_with_rowcount(1)
    repo = PortfolioRepository(session)
    assert (await repo.delete_transaction(transaction_id=1)) is True


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_alert_persists_with_uppercase_symbol():
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    repo = PortfolioRepository(session)
    a = await repo.create_alert(
        user_id=1, symbol="fpt", alert_type=AlertType.ABOVE,
        target_price=110.0,
    )
    assert a.symbol == "FPT"


@pytest.mark.asyncio
async def test_get_alerts_by_user_filters_active():
    rows = [PriceAlert(
        id=1, user_id=1, symbol="FPT",
        alert_type=AlertType.ABOVE, target_price=110.0,
        is_active=True, is_triggered=False,
    )]
    session = _session_returning_list(rows)
    repo = PortfolioRepository(session)
    out = await repo.get_alerts_by_user(user_id=1, active_only=True)
    assert len(out) == 1


@pytest.mark.asyncio
async def test_get_alert_by_id_returns_row_or_none():
    expected = PriceAlert(
        id=7, user_id=1, symbol="FPT",
        alert_type=AlertType.ABOVE, target_price=110.0,
        is_active=True, is_triggered=False,
    )
    repo = PortfolioRepository(_session_returning_scalar(expected))
    assert (await repo.get_alert_by_id(7, 1)) is expected


@pytest.mark.asyncio
async def test_trigger_alert_returns_true_when_row_updated():
    session = _session_with_rowcount(1)
    repo = PortfolioRepository(session)
    assert (await repo.trigger_alert(alert_id=1)) is True


@pytest.mark.asyncio
async def test_delete_alert_returns_true_when_row_deleted():
    session = _session_with_rowcount(1)
    repo = PortfolioRepository(session)
    assert (await repo.delete_alert(alert_id=1, user_id=1)) is True
