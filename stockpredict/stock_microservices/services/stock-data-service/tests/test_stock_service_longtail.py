"""Tests for the long-tail vnstock-dependent methods of StockService.

These are the methods that wrap vnstock SDK calls (company.overview,
finance.income_statement, quote.history, etc.) and shape the returned
DataFrames into the API response schemas. Each test mocks the vnstock
client at the property level so no real SDK is touched.

Covers:
- get_company_news_data / events / dividends / profile_data
- get_financial_statement (success + unknown-type + exception)
- get_company_profile_cached + get_financial_statement_cached
  (cache hit / cache miss → live fallback)
- is_company_data_stale (count=0, oldest=None, stale, fresh)
- get_all_industries_live (industries_icb primary + symbols_by_industries
  fallback + empty)
- _get_historical_data_live (success + empty df + exception)
- _get_top_movers_live (gainers / losers / volume sort branches +
  empty data + exception)
- fetch_and_save_historical_data (company-missing raises +
  happy path saves + updates timestamp)
"""
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from app.models.domain import Company, StockPrice
from app.services.stock_service import StockService


def _make_service(repo=None) -> StockService:
    return StockService(repo if repo is not None else MagicMock())


def _patch_vnstock(svc: StockService, fake_vnstock):
    """Replace the cached vnstock property by patching the type — the
    decorator-based vnstock property would otherwise rebuild a real
    client. Using a closure to capture fake_vnstock keeps each test
    isolated."""
    return patch.object(
        type(svc),
        "vnstock",
        new_callable=lambda: property(lambda self: fake_vnstock),
    )


def _make_company(id=1, symbol="VNM", name="Vinamilk", last_synced_at=None) -> Company:
    c = Company(
        id=id,
        symbol=symbol,
        name=name,
        exchange="HOSE",
        is_active=True,
        is_tradeable=True,
    )
    c.last_synced_at = last_synced_at
    return c


# ---------------------------------------------------------------------------
# get_company_news_data / events / dividends
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_company_news_data_maps_columns_and_computes_change():
    """News response renames columns via NEWS_COLUMN_MAP and computes
    change = price - referencePrice from the renamed fields."""
    df = pd.DataFrame({
        "ticker": ["FPT"],
        "news_title": ["Earnings beat"],
        "close_price": [100.0],
        "ref_price": [98.0],
    })
    fake_stock = MagicMock()
    fake_stock.company.news = lambda: df
    fake_vnstock = MagicMock()
    fake_vnstock.stock.return_value = fake_stock

    svc = _make_service()
    with _patch_vnstock(svc, fake_vnstock):
        out = await svc.get_company_news_data("FPT")
    assert len(out) == 1
    assert out[0]["symbol"] == "FPT"
    assert out[0]["title"] == "Earnings beat"
    assert out[0]["price"] == 100.0
    assert out[0]["referencePrice"] == 98.0
    assert out[0]["change"] == 2.0


@pytest.mark.asyncio
async def test_get_company_news_data_returns_empty_on_empty_df():
    fake_stock = MagicMock()
    fake_stock.company.news = lambda: pd.DataFrame()
    fake_vnstock = MagicMock()
    fake_vnstock.stock.return_value = fake_stock
    svc = _make_service()
    with _patch_vnstock(svc, fake_vnstock):
        assert await svc.get_company_news_data("FPT") == []


@pytest.mark.asyncio
async def test_get_company_news_data_swallows_exception():
    fake_stock = MagicMock()
    fake_stock.company.news.side_effect = RuntimeError("vnstock down")
    fake_vnstock = MagicMock()
    fake_vnstock.stock.return_value = fake_stock
    svc = _make_service()
    with _patch_vnstock(svc, fake_vnstock):
        assert await svc.get_company_news_data("FPT") == []


@pytest.mark.asyncio
async def test_get_company_events_data_maps_columns():
    df = pd.DataFrame({
        "ticker": ["FPT"],
        "event_title": ["Dividend announcement"],
        "event_list_name": ["DIV"],
    })
    fake_stock = MagicMock()
    fake_stock.company.events = lambda: df
    fake_vnstock = MagicMock()
    fake_vnstock.stock.return_value = fake_stock

    svc = _make_service()
    with _patch_vnstock(svc, fake_vnstock):
        out = await svc.get_company_events_data("FPT")
    assert out[0]["symbol"] == "FPT"
    assert out[0]["title"] == "Dividend announcement"
    assert out[0]["eventType"] == "DIV"


@pytest.mark.asyncio
async def test_get_company_events_data_swallows_exception():
    fake_stock = MagicMock()
    fake_stock.company.events.side_effect = RuntimeError("down")
    fake_vnstock = MagicMock()
    fake_vnstock.stock.return_value = fake_stock
    svc = _make_service()
    with _patch_vnstock(svc, fake_vnstock):
        assert await svc.get_company_events_data("FPT") == []


@pytest.mark.asyncio
async def test_get_company_dividends_data_returns_records_when_source_supports_it():
    """data_source has a `dividends` attr → call through, return records."""
    df = pd.DataFrame({"exercise_date": ["2026-05-01"], "value": [1000.0]})

    fake_stock = MagicMock()
    # Make data_source.dividends a callable so hasattr(... , 'dividends') is True.
    fake_stock.company.data_source.dividends = lambda: None
    fake_stock.company.dividends = lambda: df
    fake_vnstock = MagicMock()
    fake_vnstock.stock.return_value = fake_stock

    svc = _make_service()
    with _patch_vnstock(svc, fake_vnstock):
        out = await svc.get_company_dividends_data("FPT")
    assert len(out) == 1
    assert out[0]["value"] == 1000.0


@pytest.mark.asyncio
async def test_get_company_dividends_data_returns_empty_when_source_lacks_support():
    """VCI doesn't expose dividends — hasattr returns False, no SDK call."""
    fake_stock = MagicMock(spec=["company"])
    fake_stock.company = MagicMock()
    # Strip the dividends attr from data_source.
    fake_stock.company.data_source = MagicMock(spec=[])
    fake_vnstock = MagicMock()
    fake_vnstock.stock.return_value = fake_stock

    svc = _make_service()
    with _patch_vnstock(svc, fake_vnstock):
        out = await svc.get_company_dividends_data("FPT")
    assert out == []


# ---------------------------------------------------------------------------
# get_company_profile_data — overview + enrichment
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_company_profile_data_enriches_with_trading_stats_and_shareholders():
    overview_df = pd.DataFrame({
        "symbol": ["FPT"],
        "company_profile": ["Profile text"],
        "issue_share": [1_000_000],
    })
    trading_df = pd.DataFrame({
        "current_holding_ratio": [0.3],
        "foreign_holding_room": [300_000],
    })
    shareholders_df = pd.DataFrame({"name": ["A", "B", "C"]})

    fake_stock = MagicMock()
    fake_stock.company.overview = lambda: overview_df
    fake_stock.company.trading_stats = lambda: trading_df
    fake_stock.company.shareholders = lambda: shareholders_df
    fake_vnstock = MagicMock()
    fake_vnstock.stock.return_value = fake_stock

    svc = _make_service()
    with _patch_vnstock(svc, fake_vnstock):
        out = await svc.get_company_profile_data("FPT")
    assert len(out) == 1
    rec = out[0]
    assert rec.get("ticker") == "FPT"  # symbol renamed
    assert rec.get("foreignPercent") == 0.3
    # outstanding = foreign_holding_room / current_holding_ratio = 1_000_000
    assert rec.get("outstandingShare") == 1_000_000
    assert rec.get("noShareholders") == 3


@pytest.mark.asyncio
async def test_get_company_profile_data_returns_empty_on_no_overview():
    fake_stock = MagicMock()
    fake_stock.company.overview = lambda: pd.DataFrame()
    fake_vnstock = MagicMock()
    fake_vnstock.stock.return_value = fake_stock
    svc = _make_service()
    with _patch_vnstock(svc, fake_vnstock):
        assert await svc.get_company_profile_data("FPT") == []


@pytest.mark.asyncio
async def test_get_company_profile_data_swallows_enrichment_failures():
    """trading_stats / shareholders failing must not break the base overview."""
    overview_df = pd.DataFrame({"symbol": ["FPT"], "company_profile": ["x"], "issue_share": [100]})

    fake_stock = MagicMock()
    fake_stock.company.overview = lambda: overview_df
    fake_stock.company.trading_stats.side_effect = RuntimeError("ts down")
    fake_stock.company.shareholders.side_effect = RuntimeError("sh down")
    fake_vnstock = MagicMock()
    fake_vnstock.stock.return_value = fake_stock

    svc = _make_service()
    with _patch_vnstock(svc, fake_vnstock):
        out = await svc.get_company_profile_data("FPT")
    assert len(out) == 1
    assert out[0].get("ticker") == "FPT"


# ---------------------------------------------------------------------------
# get_financial_statement
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_financial_statement_returns_empty_for_unknown_type():
    fake_stock = MagicMock()
    fake_stock.finance = MagicMock(spec=[])  # no income_statement / cash_flow / etc.
    fake_vnstock = MagicMock()
    fake_vnstock.stock.return_value = fake_stock

    svc = _make_service()
    with _patch_vnstock(svc, fake_vnstock):
        out = await svc.get_financial_statement("FPT", "made_up_type")
    assert out == []


@pytest.mark.asyncio
async def test_get_financial_statement_returns_records_for_income_statement():
    df = pd.DataFrame({
        "yearReport": [2026, 2025],
        "Revenue (Bn. VND)": [100, 80],
    })

    fake_stock = MagicMock()
    # Real method that returns the dataframe (signature accepts period+lang kwargs).
    fake_stock.finance.income_statement = lambda period, lang: df
    fake_vnstock = MagicMock()
    fake_vnstock.stock.return_value = fake_stock

    svc = _make_service()
    with _patch_vnstock(svc, fake_vnstock):
        out = await svc.get_financial_statement("FPT", "income_statement")
    assert len(out) == 2
    # Columns renamed via _flexible_rename.
    assert out[0].get("report_year") == 2026
    assert out[0].get("revenue") == 100


@pytest.mark.asyncio
async def test_get_financial_statement_swallows_exception():
    fake_stock = MagicMock()
    def boom(**_kw): raise RuntimeError("down")
    fake_stock.finance.income_statement = boom
    fake_vnstock = MagicMock()
    fake_vnstock.stock.return_value = fake_stock

    svc = _make_service()
    with _patch_vnstock(svc, fake_vnstock):
        assert await svc.get_financial_statement("FPT", "income_statement") == []


# ---------------------------------------------------------------------------
# Cached variants — DB hit vs fall-through to live
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_company_profile_cached_hit_skips_vnstock():
    profile = MagicMock(
        ticker="FPT",
        company_profile="bio",
        history="hist",
        industry="Tech",
        industry_l2=None,
        industry_l3=None,
        charter_capital=1e10,
        issue_share=1e6,
        outstanding_share=1e6,
        foreign_percent=0.3,
        free_float_rate=0.5,
        no_shareholders=100,
        no_employees=20000,
    )
    repo = MagicMock()
    repo.get_company_profile = AsyncMock(return_value=profile)
    svc = _make_service(repo)

    with patch.object(svc, "get_company_profile_data", AsyncMock()) as live_mock:
        out = await svc.get_company_profile_cached("FPT")

    live_mock.assert_not_awaited()
    assert out[0]["ticker"] == "FPT"
    assert out[0]["industry"] == "Tech"


@pytest.mark.asyncio
async def test_get_company_profile_cached_miss_falls_back_to_live():
    repo = MagicMock()
    repo.get_company_profile = AsyncMock(return_value=None)
    svc = _make_service(repo)

    live = [{"ticker": "FPT", "live": True}]
    with patch.object(svc, "get_company_profile_data", AsyncMock(return_value=live)) as live_mock:
        out = await svc.get_company_profile_cached("FPT")
    live_mock.assert_awaited_once_with("FPT")
    assert out == live


@pytest.mark.asyncio
async def test_get_financial_statement_cached_hit_parses_json_rows():
    rows = [MagicMock(id=1, data='{"report_year": 2026, "revenue": 100}')]
    repo = MagicMock()
    repo.get_financial_statements = AsyncMock(return_value=rows)
    svc = _make_service(repo)

    out = await svc.get_financial_statement_cached("FPT", "income_statement")
    assert out == [{"report_year": 2026, "revenue": 100}]


@pytest.mark.asyncio
async def test_get_financial_statement_cached_skips_bad_json_rows():
    rows = [
        MagicMock(id=1, data='{"good": 1}'),
        MagicMock(id=2, data='{not valid json'),
        MagicMock(id=3, data='{"good": 2}'),
    ]
    repo = MagicMock()
    repo.get_financial_statements = AsyncMock(return_value=rows)
    svc = _make_service(repo)

    out = await svc.get_financial_statement_cached("FPT", "income_statement")
    assert out == [{"good": 1}, {"good": 2}]


@pytest.mark.asyncio
async def test_get_financial_statement_cached_miss_falls_back_to_live():
    repo = MagicMock()
    repo.get_financial_statements = AsyncMock(return_value=[])
    svc = _make_service(repo)

    with patch.object(svc, "get_financial_statement", AsyncMock(return_value=[{"live": 1}])) as live_mock:
        out = await svc.get_financial_statement_cached("FPT", "income_statement", "annual")
    live_mock.assert_awaited_once_with("FPT", "income_statement", "annual")
    assert out == [{"live": 1}]


# ---------------------------------------------------------------------------
# is_company_data_stale
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_is_company_data_stale_true_when_empty():
    repo = MagicMock()
    repo.count_company_profiles = AsyncMock(return_value=0)
    svc = _make_service(repo)
    assert await svc.is_company_data_stale() is True


@pytest.mark.asyncio
async def test_is_company_data_stale_true_when_oldest_is_none():
    repo = MagicMock()
    repo.count_company_profiles = AsyncMock(return_value=5)
    repo.get_oldest_profile_sync = AsyncMock(return_value=None)
    svc = _make_service(repo)
    assert await svc.is_company_data_stale() is True


@pytest.mark.asyncio
async def test_is_company_data_stale_true_when_older_than_threshold(monkeypatch):
    """Oldest sync further back than COMPANY_SYNC_STALE_DAYS → stale."""
    from app.services import stock_service as svc_mod
    monkeypatch.setattr(svc_mod.settings, "COMPANY_SYNC_STALE_DAYS", 7)

    repo = MagicMock()
    repo.count_company_profiles = AsyncMock(return_value=5)
    repo.get_oldest_profile_sync = AsyncMock(
        return_value=datetime.utcnow() - timedelta(days=14)
    )
    svc = _make_service(repo)
    assert await svc.is_company_data_stale() is True


@pytest.mark.asyncio
async def test_is_company_data_stale_false_when_fresh(monkeypatch):
    from app.services import stock_service as svc_mod
    monkeypatch.setattr(svc_mod.settings, "COMPANY_SYNC_STALE_DAYS", 7)

    repo = MagicMock()
    repo.count_company_profiles = AsyncMock(return_value=30)
    repo.get_oldest_profile_sync = AsyncMock(
        return_value=datetime.utcnow() - timedelta(days=1)
    )
    svc = _make_service(repo)
    assert await svc.is_company_data_stale() is False


@pytest.mark.asyncio
async def test_is_company_data_stale_true_when_vn30_coverage_is_partial(monkeypatch):
    """An interrupted sync leaves e.g. 3 of 30 profiles; recent but incomplete
    must still count as stale so the next startup finishes the job."""
    from app.services import stock_service as svc_mod
    monkeypatch.setattr(svc_mod.settings, "COMPANY_SYNC_STALE_DAYS", 7)

    repo = MagicMock()
    repo.count_company_profiles = AsyncMock(return_value=3)
    repo.get_oldest_profile_sync = AsyncMock(return_value=datetime.utcnow())
    svc = _make_service(repo)
    assert await svc.is_company_data_stale() is True
    repo.get_oldest_profile_sync.assert_not_awaited()


# ---------------------------------------------------------------------------
# get_all_industries_live — both source paths
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_all_industries_live_uses_industries_icb_when_available():
    icb_df = pd.DataFrame({
        "icb_code": ["8300", "9530"],
        "icb_name": ["Banking", "Technology"],
        "level": [2, 2],
    })
    fake_stock = MagicMock()
    fake_stock.listing.industries_icb = lambda: icb_df
    fake_vnstock = MagicMock()
    fake_vnstock.stock.return_value = fake_stock

    svc = _make_service()
    with _patch_vnstock(svc, fake_vnstock):
        out = await svc.get_all_industries_live()
    assert [i.code for i in out] == ["8300", "9530"]
    assert [i.name for i in out] == ["Banking", "Technology"]


@pytest.mark.asyncio
async def test_get_all_industries_live_falls_back_to_symbols_by_industries():
    """industries_icb() raises → fall through to symbols_by_industries
    and deduplicate by code."""
    sym_df = pd.DataFrame({
        "symbol": ["FPT", "VNM", "FPT"],
        "icb_code2": ["9530", "8300", "9530"],
        "icb_name2": ["Tech", "Food", "Tech"],
        "en_icb_name2": ["Tech", "Food", "Tech"],
    })
    fake_stock = MagicMock()
    fake_stock.listing.industries_icb.side_effect = RuntimeError("not supported")
    fake_stock.listing.symbols_by_industries = lambda: sym_df
    fake_vnstock = MagicMock()
    fake_vnstock.stock.return_value = fake_stock

    svc = _make_service()
    with _patch_vnstock(svc, fake_vnstock):
        out = await svc.get_all_industries_live()
    # 2 unique codes after dedup; sorted by code.
    assert [i.code for i in out] == ["8300", "9530"]


@pytest.mark.asyncio
async def test_get_all_industries_live_returns_empty_on_total_failure():
    fake_stock = MagicMock()
    fake_stock.listing.industries_icb.side_effect = RuntimeError("down")
    fake_stock.listing.symbols_by_industries.side_effect = RuntimeError("also down")
    fake_vnstock = MagicMock()
    fake_vnstock.stock.return_value = fake_stock

    svc = _make_service()
    with _patch_vnstock(svc, fake_vnstock):
        assert await svc.get_all_industries_live() == []


# ---------------------------------------------------------------------------
# _get_historical_data_live
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_historical_data_live_returns_sorted_response():
    hist_df = pd.DataFrame({
        "time": ["2026-05-02", "2026-05-01"],
        "open": [101, 100],
        "high": [102, 101],
        "low": [99, 98],
        "close": [101.5, 100.5],
        "volume": [10000, 9000],
    })
    symbols_df = pd.DataFrame({"symbol": ["FPT"], "organ_name": ["FPT Corp"]})

    fake_stock = MagicMock()
    fake_stock.quote.history = lambda start, end: hist_df
    fake_stock.listing.all_symbols = lambda: symbols_df
    fake_vnstock = MagicMock()
    fake_vnstock.stock.return_value = fake_stock

    svc = _make_service()
    with _patch_vnstock(svc, fake_vnstock):
        out = await svc._get_historical_data_live("fpt", date(2026, 5, 1), date(2026, 5, 2))
    assert out is not None
    assert out.symbol == "FPT"
    assert out.name == "FPT Corp"
    assert out.count == 2
    # Sorted ascending.
    assert out.data[0].date == date(2026, 5, 1)


@pytest.mark.asyncio
async def test_get_historical_data_live_returns_none_on_empty_df():
    fake_stock = MagicMock()
    fake_stock.quote.history = lambda start, end: pd.DataFrame()
    fake_vnstock = MagicMock()
    fake_vnstock.stock.return_value = fake_stock

    svc = _make_service()
    with _patch_vnstock(svc, fake_vnstock):
        out = await svc._get_historical_data_live("FPT", date(2026, 5, 1), date(2026, 5, 2))
    assert out is None


@pytest.mark.asyncio
async def test_get_historical_data_live_returns_none_on_exception():
    fake_stock = MagicMock()
    fake_stock.quote.history.side_effect = RuntimeError("down")
    fake_vnstock = MagicMock()
    fake_vnstock.stock.return_value = fake_stock

    svc = _make_service()
    with _patch_vnstock(svc, fake_vnstock):
        out = await svc._get_historical_data_live("FPT", date(2026, 5, 1), date(2026, 5, 2))
    assert out is None


# ---------------------------------------------------------------------------
# _get_top_movers_live
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_top_movers_live_returns_empty_on_no_price_data():
    svc = _make_service()
    with patch.object(svc, "get_price_board", AsyncMock(return_value=[])):
        out = await svc._get_top_movers_live(limit=10, sort_by="gainers")
    assert out == []


@pytest.mark.asyncio
async def test_get_top_movers_live_falls_back_to_vn30_when_vn100_empty():
    svc = _make_service()

    async def fake_price_board(group):
        return [{"symbol": "FPT", "matchPrice": 100, "changePercent": 2.0, "change": 2.0, "totalQty": 10000}] if group == "VN30" else []

    fake_stock = MagicMock()
    fake_stock.listing.all_symbols = lambda: pd.DataFrame({"symbol": ["FPT"], "organ_name": ["FPT Corp"]})
    fake_vnstock = MagicMock()
    fake_vnstock.stock.return_value = fake_stock

    with patch.object(svc, "get_price_board", side_effect=fake_price_board), \
         _patch_vnstock(svc, fake_vnstock):
        out = await svc._get_top_movers_live(limit=10, sort_by="gainers")
    assert len(out) == 1
    assert out[0].symbol == "FPT"
    assert out[0].name == "FPT Corp"


@pytest.mark.asyncio
async def test_get_top_movers_live_sorts_gainers_desc():
    """Positive changes only, highest first."""
    svc = _make_service()
    rows = [
        {"symbol": "A", "matchPrice": 100, "changePercent": 1.0, "totalQty": 1000},
        {"symbol": "B", "matchPrice": 100, "changePercent": 5.0, "totalQty": 1000},
        {"symbol": "C", "matchPrice": 100, "changePercent": -1.0, "totalQty": 1000},  # filtered out
        {"symbol": "D", "matchPrice": 100, "changePercent": 3.0, "totalQty": 1000},
    ]
    with patch.object(svc, "get_price_board", AsyncMock(return_value=rows)), \
         _patch_vnstock(svc, MagicMock()):
        out = await svc._get_top_movers_live(limit=10, sort_by="gainers")
    assert [m.symbol for m in out] == ["B", "D", "A"]


@pytest.mark.asyncio
async def test_get_top_movers_live_sorts_losers_asc_negative_only():
    svc = _make_service()
    rows = [
        {"symbol": "A", "matchPrice": 100, "changePercent": -1.0, "totalQty": 1000},
        {"symbol": "B", "matchPrice": 100, "changePercent": -5.0, "totalQty": 1000},
        {"symbol": "C", "matchPrice": 100, "changePercent": 2.0, "totalQty": 1000},  # filtered out
    ]
    with patch.object(svc, "get_price_board", AsyncMock(return_value=rows)), \
         _patch_vnstock(svc, MagicMock()):
        out = await svc._get_top_movers_live(limit=10, sort_by="losers")
    assert [m.symbol for m in out] == ["B", "A"]


@pytest.mark.asyncio
async def test_get_top_movers_live_sorts_volume_desc_no_filter():
    """Volume sort doesn't filter on changePercent sign."""
    svc = _make_service()
    rows = [
        {"symbol": "A", "matchPrice": 100, "changePercent": 0.5, "totalQty": 5000},
        {"symbol": "B", "matchPrice": 100, "changePercent": -1.0, "totalQty": 10000},
        {"symbol": "C", "matchPrice": 100, "changePercent": 2.0, "totalQty": 1000},
    ]
    with patch.object(svc, "get_price_board", AsyncMock(return_value=rows)), \
         _patch_vnstock(svc, MagicMock()):
        out = await svc._get_top_movers_live(limit=10, sort_by="volume")
    assert [m.symbol for m in out] == ["B", "A", "C"]


# ---------------------------------------------------------------------------
# fetch_and_save_historical_data
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fetch_and_save_historical_data_raises_when_company_missing():
    repo = MagicMock()
    repo.get_company_by_symbol = AsyncMock(return_value=None)
    svc = _make_service(repo)

    with pytest.raises(ValueError, match="Company not found"):
        await svc.fetch_and_save_historical_data("ZZZ")


@pytest.mark.asyncio
async def test_fetch_and_save_historical_data_persists_rows_and_stamps_company():
    company = _make_company(id=11)
    repo = MagicMock()
    repo.get_company_by_symbol = AsyncMock(return_value=company)
    repo.save_prices = AsyncMock(return_value=2)
    repo.update_company = AsyncMock()
    svc = _make_service(repo)

    hist_df = pd.DataFrame({
        "time": [date(2026, 5, 1), date(2026, 5, 2)],
        "open": [100, 101],
        "high": [101, 102],
        "low": [99, 100],
        "close": [100.5, 101.5],
        "volume": [1000, 1100],
    })
    fake_stock = MagicMock()
    fake_stock.quote.history = lambda start, end: hist_df
    fake_vnstock = MagicMock()
    fake_vnstock.stock.return_value = fake_stock

    with _patch_vnstock(svc, fake_vnstock):
        count = await svc.fetch_and_save_historical_data("FPT", date(2026, 5, 1), date(2026, 5, 2))

    assert count == 2
    repo.save_prices.assert_awaited_once()
    # Each StockPrice carried company_id=11.
    persisted = repo.save_prices.await_args.args[0]
    assert all(isinstance(p, StockPrice) and p.company_id == 11 for p in persisted)
    # last_synced_at stamped.
    update_kwargs = repo.update_company.await_args.kwargs
    assert "last_synced_at" in update_kwargs


@pytest.mark.asyncio
async def test_fetch_and_save_historical_data_returns_zero_on_empty_df():
    company = _make_company(id=11)
    repo = MagicMock()
    repo.get_company_by_symbol = AsyncMock(return_value=company)
    repo.save_prices = AsyncMock()
    svc = _make_service(repo)

    fake_stock = MagicMock()
    fake_stock.quote.history = lambda start, end: pd.DataFrame()
    fake_vnstock = MagicMock()
    fake_vnstock.stock.return_value = fake_stock

    with _patch_vnstock(svc, fake_vnstock):
        n = await svc.fetch_and_save_historical_data("FPT")
    assert n == 0
    repo.save_prices.assert_not_awaited()
