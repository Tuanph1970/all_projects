"""Tests for app.services.stock_service.StockService.

Targets the repository-wrapper paths (where StockService just remaps
domain rows into response schemas), the pure pandas helpers, and a
handful of vnstock-mocked paths covering the live fallback flows that
fire when the database is empty.

The Vnstock client is mocked at the property level (`StockService.vnstock`)
so the tests never touch the real vendor SDK.
"""
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from app.models.domain import Company, Industry, MarketIndex, StockPrice
from app.services.stock_service import StockService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_company(id=1, symbol="VNM", name="Vinamilk", industry=None) -> Company:
    c = Company(
        id=id,
        symbol=symbol,
        name=name,
        name_en=None,
        exchange="HOSE",
        industry_id=1 if industry else None,
        listing_date=None,
        outstanding_shares=None,
        market_cap=None,
        website=None,
        description=None,
        is_active=True,
        is_tradeable=True,
    )
    if industry is not None:
        c.industry = industry
    return c


def _make_industry(id=1, code="FOOD", name="Food", level=2) -> Industry:
    return Industry(id=id, code=code, name=name, name_en=None, description=None, level=level)


def _make_price(date_=None, close=75000.0, change=1500.0, change_percent=2.0, volume=100000) -> StockPrice:
    return StockPrice(
        id=1,
        company_id=1,
        date=date_ or date(2026, 5, 1),
        open=74000.0,
        high=76000.0,
        low=73500.0,
        close=close,
        volume=volume,
        change=change,
        change_percent=change_percent,
    )


def _make_service(repo=None) -> StockService:
    """Build a StockService over a mocked repository. The vnstock client
    is not initialized until first property access — tests that don't
    exercise the live paths never construct one."""
    if repo is None:
        repo = MagicMock()
    return StockService(repo)


# ---------------------------------------------------------------------------
# get_all_companies — populated DB path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_all_companies_returns_remapped_response_from_db():
    """DB has rows → no vnstock call, response schema mirrors company fields."""
    repo = MagicMock()
    industry = _make_industry(name="Food & Beverage")
    company = _make_company(industry=industry)
    repo.get_all_companies = AsyncMock(return_value=([company], 1))

    svc = _make_service(repo)
    rows, total, total_pages = await svc.get_all_companies(page=1, page_size=10)

    assert total == 1
    assert total_pages == 1
    assert rows[0].symbol == "VNM"
    assert rows[0].industry_name == "Food & Beverage"


@pytest.mark.asyncio
async def test_get_all_companies_falls_back_to_live_when_db_empty():
    """Empty DB + no filters → fetch live from vnstock."""
    from app.models.schemas import CompanyListingResponse

    repo = MagicMock()
    repo.get_all_companies = AsyncMock(return_value=([], 0))

    svc = _make_service(repo)
    live_companies = [
        CompanyListingResponse(symbol="FPT", name="FPT Corp", exchange=None),
        CompanyListingResponse(symbol="VNM", name="Vinamilk", exchange=None),
    ]
    with patch.object(svc, "get_all_companies_live", AsyncMock(return_value=live_companies)):
        rows, total, total_pages = await svc.get_all_companies(page=1, page_size=10)

    assert total == 2
    assert {r.symbol for r in rows} == {"FPT", "VNM"}
    # Live companies are flagged id=0 (no DB row yet).
    assert all(r.id == 0 for r in rows)


@pytest.mark.asyncio
async def test_get_all_companies_with_filter_does_not_fall_back():
    """Exchange/industry filter explicitly requested → DB empty result is
    honored as "no matches"; we don't fall back to live."""
    repo = MagicMock()
    repo.get_all_companies = AsyncMock(return_value=([], 0))

    svc = _make_service(repo)
    with patch.object(svc, "get_all_companies_live", AsyncMock()) as live_mock:
        rows, total, _ = await svc.get_all_companies(page=1, page_size=10, exchange="HOSE")

    live_mock.assert_not_awaited()
    assert rows == []
    assert total == 0


# ---------------------------------------------------------------------------
# get_company_detail
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_company_detail_returns_none_when_missing():
    repo = MagicMock()
    repo.get_company_by_symbol = AsyncMock(return_value=None)
    svc = _make_service(repo)
    assert await svc.get_company_detail("ZZZ") is None


@pytest.mark.asyncio
async def test_get_company_detail_includes_latest_price_and_industry():
    industry = _make_industry()
    company = _make_company(industry=industry)
    price = _make_price()

    repo = MagicMock()
    repo.get_company_by_symbol = AsyncMock(return_value=company)
    repo.get_latest_price = AsyncMock(return_value=price)

    svc = _make_service(repo)
    out = await svc.get_company_detail("VNM")

    assert out is not None
    assert out.symbol == "VNM"
    assert out.industry is not None and out.industry.code == "FOOD"
    assert out.current_price == 75000.0
    assert out.change_percent == 2.0


# ---------------------------------------------------------------------------
# search_companies — exact symbol match scores higher
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_companies_scores_exact_symbol_match_higher():
    repo = MagicMock()
    industry = _make_industry()
    rows = [
        _make_company(id=1, symbol="VNM", name="Vinamilk", industry=industry),
        _make_company(id=2, symbol="VND", name="VNDirect", industry=industry),
    ]
    repo.search_companies = AsyncMock(return_value=rows)
    svc = _make_service(repo)

    out = await svc.search_companies("VNM")
    assert out[0].match_score == 1.0  # exact symbol match
    assert out[1].match_score == 0.5  # partial match


# ---------------------------------------------------------------------------
# Top gainers / losers / actives — DB path + live fallback
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_top_gainers_returns_remapped_db_rows():
    repo = MagicMock()
    pairs = [(_make_company(), _make_price(change_percent=5.0))]
    repo.get_top_gainers = AsyncMock(return_value=pairs)

    svc = _make_service(repo)
    out = await svc.get_top_gainers(limit=5)

    assert len(out) == 1
    assert out[0].symbol == "VNM"
    assert out[0].change_percent == 5.0


@pytest.mark.asyncio
async def test_get_top_gainers_falls_back_to_live_when_empty():
    repo = MagicMock()
    repo.get_top_gainers = AsyncMock(return_value=[])

    svc = _make_service(repo)
    with patch.object(svc, "_get_top_movers_live", AsyncMock(return_value=[])) as live_mock:
        await svc.get_top_gainers()
    live_mock.assert_awaited_once_with(limit=10, sort_by="gainers")


@pytest.mark.asyncio
async def test_get_top_losers_falls_back_with_losers_sort():
    repo = MagicMock()
    repo.get_top_losers = AsyncMock(return_value=[])
    svc = _make_service(repo)
    with patch.object(svc, "_get_top_movers_live", AsyncMock(return_value=[])) as live_mock:
        await svc.get_top_losers()
    live_mock.assert_awaited_once_with(limit=10, sort_by="losers")


@pytest.mark.asyncio
async def test_get_most_active_falls_back_with_volume_sort():
    repo = MagicMock()
    repo.get_top_volume = AsyncMock(return_value=[])
    svc = _make_service(repo)
    with patch.object(svc, "_get_top_movers_live", AsyncMock(return_value=[])) as live_mock:
        await svc.get_most_active()
    live_mock.assert_awaited_once_with(limit=10, sort_by="volume")


@pytest.mark.asyncio
async def test_get_most_active_returns_db_rows_when_present():
    repo = MagicMock()
    pairs = [(_make_company(), _make_price(volume=10_000_000))]
    repo.get_top_volume = AsyncMock(return_value=pairs)

    svc = _make_service(repo)
    out = await svc.get_most_active()
    assert out[0].volume == 10_000_000


# ---------------------------------------------------------------------------
# Industries
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_all_industries_uses_db_rows_when_present():
    repo = MagicMock()
    repo.get_all_industries = AsyncMock(
        return_value=[_make_industry(id=1, code="A1", name="A"), _make_industry(id=2, code="B2", name="B")]
    )
    svc = _make_service(repo)
    out = await svc.get_all_industries()
    assert [i.code for i in out] == ["A1", "B2"]


@pytest.mark.asyncio
async def test_get_all_industries_falls_back_to_live_when_empty():
    from app.models.schemas import IndustryResponse

    repo = MagicMock()
    repo.get_all_industries = AsyncMock(return_value=[])

    svc = _make_service(repo)
    live = [IndustryResponse(id=1, code="LIVE", name="Live", level=2)]
    with patch.object(svc, "get_all_industries_live", AsyncMock(return_value=live)):
        out = await svc.get_all_industries()
    assert out[0].code == "LIVE"


@pytest.mark.asyncio
async def test_get_companies_by_industry_remaps_rows():
    repo = MagicMock()
    repo.get_companies_by_industry = AsyncMock(
        return_value=[_make_company(id=7, symbol="ABC")]
    )
    svc = _make_service(repo)
    out = await svc.get_companies_by_industry(industry_id=1)
    assert len(out) == 1
    assert out[0].symbol == "ABC"


@pytest.mark.asyncio
async def test_get_companies_by_industry_code_db_hit_returns_paginated_response():
    industry = _make_industry()
    repo = MagicMock()
    repo.get_industry_by_code = AsyncMock(return_value=industry)
    repo.get_companies_by_industry = AsyncMock(
        return_value=[_make_company(id=1), _make_company(id=2, symbol="ABC")]
    )

    svc = _make_service(repo)
    out = await svc.get_companies_by_industry_code("FOOD", page=1, page_size=10)
    assert out.total == 2
    assert out.page == 1
    assert out.page_size == 10
    assert len(out.items) == 2


@pytest.mark.asyncio
async def test_get_companies_by_industry_code_falls_back_to_live_when_unknown():
    from app.models.schemas import PaginatedResponse, CompanyResponse

    repo = MagicMock()
    repo.get_industry_by_code = AsyncMock(return_value=None)

    svc = _make_service(repo)
    live = PaginatedResponse[CompanyResponse](
        items=[], total=0, page=1, page_size=10, total_pages=0
    )
    with patch.object(svc, "get_companies_by_industry_code_live", AsyncMock(return_value=live)) as live_mock:
        out = await svc.get_companies_by_industry_code("UNKNOWN")
    live_mock.assert_awaited_once()
    assert out.total == 0


# ---------------------------------------------------------------------------
# Market indices
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_market_indices_remaps_rows():
    repo = MagicMock()
    repo.get_market_indices = AsyncMock(
        return_value=[
            MarketIndex(
                id=1, code="VNINDEX", name="VN-Index",
                date=date(2026, 5, 1),
                open=1200.0, high=1210.0, low=1195.0,
                close=1205.0, volume=500_000_000,
                change=5.0, change_percent=0.4,
            )
        ]
    )
    svc = _make_service(repo)
    out = await svc.get_market_indices()
    assert len(out) == 1
    assert out[0].code == "VNINDEX"
    assert out[0].close == 1205.0


@pytest.mark.asyncio
async def test_get_latest_indices_remaps_rows():
    repo = MagicMock()
    repo.get_latest_indices = AsyncMock(
        return_value=[
            MarketIndex(
                id=1, code="VNINDEX", name="VN-Index",
                date=date(2026, 5, 1),
                close=1205.0, change=5.0, change_percent=0.4,
            )
        ]
    )
    svc = _make_service(repo)
    out = await svc.get_latest_indices()
    assert out[0].code == "VNINDEX"


# ---------------------------------------------------------------------------
# Historical data — DB path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_historical_data_uses_db_when_prices_present():
    company = _make_company()
    prices = [
        _make_price(date_=date(2026, 4, 30), close=74000.0),
        _make_price(date_=date(2026, 5, 1), close=75000.0),
    ]
    repo = MagicMock()
    repo.get_company_by_symbol = AsyncMock(return_value=company)
    repo.get_historical_prices = AsyncMock(return_value=prices)

    svc = _make_service(repo)
    out = await svc.get_historical_data("VNM")

    assert out is not None
    assert out.symbol == "VNM"
    assert out.count == 2
    # Sorted ascending.
    assert out.data[0].date == date(2026, 4, 30)
    assert out.data[1].close == 75000.0


@pytest.mark.asyncio
async def test_get_historical_data_falls_back_to_live_when_company_missing():
    repo = MagicMock()
    repo.get_company_by_symbol = AsyncMock(return_value=None)

    svc = _make_service(repo)
    with patch.object(svc, "_get_historical_data_live", AsyncMock(return_value=None)) as live_mock:
        out = await svc.get_historical_data("ZZZ")

    live_mock.assert_awaited_once()
    assert out is None


# ---------------------------------------------------------------------------
# vnstock-mocked live paths
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_all_companies_live_maps_vnstock_dataframe():
    svc = _make_service()
    fake_stock = MagicMock()
    fake_stock.listing.all_symbols.return_value = pd.DataFrame(
        {"symbol": ["FPT", "VNM"], "organ_name": ["FPT Corp", "Vinamilk"]}
    )
    fake_vnstock = MagicMock()
    fake_vnstock.stock.return_value = fake_stock

    with patch.object(type(svc), "vnstock", new_callable=lambda: property(lambda self: fake_vnstock)):
        out = await svc.get_all_companies_live()

    assert {c.symbol for c in out} == {"FPT", "VNM"}


@pytest.mark.asyncio
async def test_get_all_companies_live_returns_empty_on_exception():
    svc = _make_service()
    fake_stock = MagicMock()
    fake_stock.listing.all_symbols.side_effect = RuntimeError("vnstock down")
    fake_vnstock = MagicMock()
    fake_vnstock.stock.return_value = fake_stock

    with patch.object(type(svc), "vnstock", new_callable=lambda: property(lambda self: fake_vnstock)):
        out = await svc.get_all_companies_live()
    assert out == []


@pytest.mark.asyncio
async def test_get_all_companies_live_returns_empty_on_empty_dataframe():
    svc = _make_service()
    fake_stock = MagicMock()
    fake_stock.listing.all_symbols.return_value = pd.DataFrame()
    fake_vnstock = MagicMock()
    fake_vnstock.stock.return_value = fake_stock

    with patch.object(type(svc), "vnstock", new_callable=lambda: property(lambda self: fake_vnstock)):
        out = await svc.get_all_companies_live()
    assert out == []


@pytest.mark.asyncio
async def test_get_companies_by_group_live_maps_symbols_series():
    svc = _make_service()
    fake_stock = MagicMock()
    fake_stock.listing.symbols_by_group.return_value = ["FPT", "VNM", "VCB"]
    fake_vnstock = MagicMock()
    fake_vnstock.stock.return_value = fake_stock

    with patch.object(type(svc), "vnstock", new_callable=lambda: property(lambda self: fake_vnstock)):
        out = await svc.get_companies_by_group_live("hose")
    # exchange filled in for known groups
    assert all(c.exchange == "HOSE" for c in out)
    assert {c.symbol for c in out} == {"FPT", "VNM", "VCB"}


@pytest.mark.asyncio
async def test_get_companies_by_group_live_returns_empty_on_no_symbols():
    svc = _make_service()
    fake_stock = MagicMock()
    fake_stock.listing.symbols_by_group.return_value = []
    fake_vnstock = MagicMock()
    fake_vnstock.stock.return_value = fake_stock

    with patch.object(type(svc), "vnstock", new_callable=lambda: property(lambda self: fake_vnstock)):
        out = await svc.get_companies_by_group_live("VN30")
    assert out == []


@pytest.mark.asyncio
async def test_search_companies_live_filters_by_symbol_or_name():
    from app.models.schemas import CompanyListingResponse

    svc = _make_service()
    all_companies = [
        CompanyListingResponse(symbol="FPT", name="FPT Corp", exchange=None),
        CompanyListingResponse(symbol="VNM", name="Vinamilk", exchange=None),
        CompanyListingResponse(symbol="VND", name="VNDirect Securities", exchange=None),
    ]
    with patch.object(svc, "get_all_companies_live", AsyncMock(return_value=all_companies)):
        # Symbol match
        out = await svc.search_companies_live("vnm")
    assert [c.symbol for c in out] == ["VNM"]

    with patch.object(svc, "get_all_companies_live", AsyncMock(return_value=all_companies)):
        # Name substring match
        out = await svc.search_companies_live("Direct")
    assert [c.symbol for c in out] == ["VND"]


@pytest.mark.asyncio
async def test_search_companies_live_returns_empty_when_no_companies():
    svc = _make_service()
    with patch.object(svc, "get_all_companies_live", AsyncMock(return_value=[])):
        out = await svc.search_companies_live("FPT")
    assert out == []


# ---------------------------------------------------------------------------
# Pure helpers — DataFrame value extraction
# ---------------------------------------------------------------------------

class TestRatioValueHelpers:
    def test_get_ratio_value_finds_first_matching_name(self):
        svc = _make_service()
        row = pd.Series({"revenue": 100.0, "rev": 99.0})
        assert svc._get_ratio_value(row, ["rev", "revenue"]) == 99.0

    def test_get_ratio_value_returns_none_when_all_nan(self):
        svc = _make_service()
        row = pd.Series({"x": float("nan")})
        assert svc._get_ratio_value(row, ["x", "y"]) is None

    def test_get_ratio_value_returns_none_when_no_match(self):
        svc = _make_service()
        row = pd.Series({"x": 1.0})
        assert svc._get_ratio_value(row, ["y", "z"]) is None

    def test_get_ratio_value_skips_non_numeric(self):
        svc = _make_service()
        row = pd.Series({"x": "not-a-number", "y": 42.0})
        assert svc._get_ratio_value(row, ["x", "y"]) == 42.0


class TestSimpleValueHelpers:
    def test_get_simple_value_exact_match(self):
        svc = _make_service()
        row = pd.Series({"price": 100.0})
        assert svc._get_simple_value(row, "price") == 100.0

    def test_get_simple_value_partial_match_case_insensitive(self):
        svc = _make_service()
        row = pd.Series({"Closing Price (VND)": 75000.0})
        assert svc._get_simple_value(row, "closing price") == 75000.0

    def test_get_simple_value_returns_none_on_no_match(self):
        svc = _make_service()
        row = pd.Series({"foo": 1.0})
        assert svc._get_simple_value(row, "bar") is None


class TestMultilevelValueHelpers:
    def test_get_multilevel_value_from_tuple_column(self):
        svc = _make_service()
        # row.index contains a tuple — mimic what vnstock multi-level
        # DataFrames look like after .iloc.
        row = pd.Series({("Cashflow", "Net Income"): 250.0})
        assert svc._get_multilevel_value(row, "Net Income") == 250.0

    def test_get_multilevel_value_from_simple_column(self):
        svc = _make_service()
        row = pd.Series({"Revenue total": 1000.0})
        # 'Revenue' is a substring of the column name.
        assert svc._get_multilevel_value(row, "Revenue") == 1000.0

    def test_get_multilevel_value_returns_none_when_missing(self):
        svc = _make_service()
        row = pd.Series({"foo": 1.0})
        assert svc._get_multilevel_value(row, "Revenue") is None


def test_standardize_df_renames_columns_using_map():
    df = pd.DataFrame({"old1": [1, 2], "old2": [3, 4], "keep": [5, 6]})
    out = StockService._standardize_df(df, {"old1": "new1", "old2": "new2", "missing": "x"})
    assert "new1" in out.columns
    assert "new2" in out.columns
    assert "keep" in out.columns
    assert "missing" not in out.columns


def test_standardize_df_converts_millisecond_dates():
    # 2026-05-01 00:00 UTC in milliseconds.
    ms = 1777939200000
    df = pd.DataFrame({"public_date": [ms]})
    out = StockService._standardize_df(df, {}, convert_dates=True)
    # Converted to a YYYY-MM-DD string.
    assert isinstance(out["public_date"].iloc[0], str)
    assert out["public_date"].iloc[0].startswith("2026-05-")


def test_flexible_rename_partial_match():
    """_flexible_rename does substring-based mapping for resilient
    handling of vnstock column-name drift across versions."""
    df = pd.DataFrame({"Revenue (Bn. VND)": [100], "Net Income (Bn. VND)": [20]})
    out = StockService._flexible_rename(
        df,
        {"Revenue": "revenue", "Net Income": "net_income"},
    )
    assert "revenue" in out.columns
    assert "net_income" in out.columns
