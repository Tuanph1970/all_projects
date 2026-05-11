"""Tests for app.repositories.stock_repository.

Each test wires a mock AsyncSession + mock query result so we verify
the repository builds the right query shape (filters, ordering, limits)
and unwraps results correctly. Database engine is never touched — that's
covered by integration tests.
"""
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.domain import Company, Industry, StockPrice
from app.repositories.stock_repository import StockRepository


def _mock_session_with_scalars(rows):
    """Build a session whose execute() returns a result whose
    scalars().all() yields `rows`."""
    session = AsyncMock()
    result = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = rows
    result.scalars.return_value = scalars
    session.execute = AsyncMock(return_value=result)
    return session


def _mock_session_with_single_scalar(value):
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    result.scalar.return_value = value
    session.execute = AsyncMock(return_value=result)
    return session


# ---------------------------------------------------------------------------
# Companies
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_all_companies_returns_rows_and_count():
    """get_all_companies fires two SELECTs (count + paginated rows) and
    returns the tuple."""
    session = AsyncMock()

    # 1st execute → count, 2nd → list rows
    count_result = MagicMock()
    count_result.scalar.return_value = 5

    list_result = MagicMock()
    list_scalars = MagicMock()
    companies = [Company(id=1, symbol="FPT", name="FPT"), Company(id=2, symbol="VNM", name="VNM")]
    list_scalars.all.return_value = companies
    list_result.scalars.return_value = list_scalars

    session.execute = AsyncMock(side_effect=[count_result, list_result])

    repo = StockRepository(session)
    rows, total = await repo.get_all_companies(skip=0, limit=10)
    assert rows == companies
    assert total == 5


@pytest.mark.asyncio
async def test_get_company_by_symbol_uppercases_input():
    expected = Company(id=1, symbol="FPT", name="FPT")
    session = _mock_session_with_single_scalar(expected)
    repo = StockRepository(session)
    out = await repo.get_company_by_symbol("fpt")
    assert out is expected
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_company_by_id_returns_none_when_missing():
    session = _mock_session_with_single_scalar(None)
    repo = StockRepository(session)
    assert await repo.get_company_by_id(999) is None


@pytest.mark.asyncio
async def test_search_companies_returns_list():
    rows = [Company(id=1, symbol="FPT", name="FPT Corp"), Company(id=2, symbol="FPT.B", name="FPT B")]
    session = _mock_session_with_scalars(rows)
    repo = StockRepository(session)
    out = await repo.search_companies("FPT", limit=5)
    assert out == rows


@pytest.mark.asyncio
async def test_create_company_persists_and_refreshes():
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    repo = StockRepository(session)

    out = await repo.create_company(symbol="ABC", name="ABC Corp")
    session.add.assert_called_once()
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once()
    assert isinstance(out, Company)
    assert out.symbol == "ABC"


# ---------------------------------------------------------------------------
# Stock prices
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_historical_prices_returns_rows():
    rows = [StockPrice(id=1, company_id=1, date=date(2026, 5, 1), close=100.0)]
    session = _mock_session_with_scalars(rows)
    repo = StockRepository(session)
    out = await repo.get_historical_prices(company_id=1)
    assert out == rows


@pytest.mark.asyncio
async def test_get_latest_price_returns_single_or_none():
    expected = StockPrice(id=1, company_id=1, date=date(2026, 5, 1), close=100.0)
    session = _mock_session_with_single_scalar(expected)
    repo = StockRepository(session)
    assert await repo.get_latest_price(1) is expected

    session2 = _mock_session_with_single_scalar(None)
    repo2 = StockRepository(session2)
    assert await repo2.get_latest_price(999) is None


@pytest.mark.asyncio
async def test_save_prices_returns_count():
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    repo = StockRepository(session)
    prices = [
        StockPrice(company_id=1, date=date(2026, 5, 1), close=100.0),
        StockPrice(company_id=1, date=date(2026, 5, 2), close=102.0),
    ]
    n = await repo.save_prices(prices)
    assert n == 2
    assert session.add.call_count == 2
    session.commit.assert_awaited_once()


# ---------------------------------------------------------------------------
# Top movers — short-circuit when there's no latest date
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_top_gainers_returns_empty_when_no_prices():
    """No prices yet → first execute returns scalar None → return []."""
    session = AsyncMock()
    result = MagicMock()
    result.scalar.return_value = None
    session.execute = AsyncMock(return_value=result)

    repo = StockRepository(session)
    assert await repo.get_top_gainers() == []
    # Only the latest-date probe runs; second SELECT skipped.
    assert session.execute.await_count == 1


@pytest.mark.asyncio
async def test_get_top_gainers_returns_company_price_pairs():
    """Happy path: latest date probed, then companies+prices joined."""
    session = AsyncMock()
    latest_result = MagicMock()
    latest_result.scalar.return_value = date(2026, 5, 1)
    pairs_result = MagicMock()
    pairs_result.all.return_value = [
        (Company(id=1, symbol="FPT", name="FPT"), StockPrice(company_id=1, date=date(2026, 5, 1), change_percent=5.0)),
    ]
    session.execute = AsyncMock(side_effect=[latest_result, pairs_result])

    repo = StockRepository(session)
    out = await repo.get_top_gainers(limit=10)
    assert len(out) == 1
    assert out[0][0].symbol == "FPT"
    assert out[0][1].change_percent == 5.0


@pytest.mark.asyncio
async def test_get_top_losers_returns_empty_when_no_prices():
    session = AsyncMock()
    result = MagicMock()
    result.scalar.return_value = None
    session.execute = AsyncMock(return_value=result)
    repo = StockRepository(session)
    assert await repo.get_top_losers() == []
