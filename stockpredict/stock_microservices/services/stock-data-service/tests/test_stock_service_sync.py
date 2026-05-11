"""Tests for the sync orchestration methods of StockService.

Covers the four methods that pull data from vnstock and persist it to
the local DB cache:
- sync_company_profile: overview + trading_stats + shareholders → upsert
- sync_company_financials: 4 statement types → bulk upsert each
- ensure_company_and_sync: create-company-if-missing + 5-year history sync
- sync_all_company_data: VN30 orchestration (rate-limited)

asyncio.sleep is patched inside sync_all_company_data so the 2-second
inter-symbol rate-limit doesn't slow the test suite to a crawl.
"""
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from app.models.domain import Company
from app.services import stock_service as svc_mod
from app.services.stock_service import StockService


def _make_service(repo=None) -> StockService:
    return StockService(repo if repo is not None else MagicMock())


def _patch_vnstock(svc: StockService, fake_vnstock):
    return patch.object(
        type(svc),
        "vnstock",
        new_callable=lambda: property(lambda self: fake_vnstock),
    )


def _vnstock_with(fake_stock) -> MagicMock:
    v = MagicMock()
    v.stock.return_value = fake_stock
    return v


def _company(id=1, symbol="FPT", last_synced_at=None) -> Company:
    c = Company(id=id, symbol=symbol, name=symbol, exchange="HOSE", is_active=True, is_tradeable=True)
    c.last_synced_at = last_synced_at
    return c


# ---------------------------------------------------------------------------
# sync_company_profile
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sync_company_profile_returns_false_on_empty_overview():
    fake_stock = MagicMock()
    fake_stock.company.overview = lambda: pd.DataFrame()
    repo = MagicMock()
    repo.upsert_company_profile = AsyncMock()
    svc = _make_service(repo)

    with _patch_vnstock(svc, _vnstock_with(fake_stock)):
        ok = await svc.sync_company_profile("FPT")
    assert ok is False
    repo.upsert_company_profile.assert_not_awaited()


@pytest.mark.asyncio
async def test_sync_company_profile_happy_path_upserts_with_enrichment():
    """Overview + trading_stats + shareholders all succeed → upsert
    gets the enriched payload (foreign_percent, outstanding_share derived,
    no_shareholders count, no_employees, free_float_rate)."""
    overview_df = pd.DataFrame({
        "symbol": ["FPT"],
        "company_profile": ["FPT Corporation"],
        "history": ["Founded 1988"],
        "icb_name2": ["Tech"],
        "icb_name3": ["Software"],
        "icb_name4": ["Application Software"],
        "charter_capital": [1_000_000_000.0],
        "issue_share": [1_000_000.0],
        "no_employees": [42000],
        "free_float_rate": [0.55],
    })
    trading_df = pd.DataFrame({
        "current_holding_ratio": [0.4],
        "foreign_holding_room": [400_000],   # outstanding_share = 400_000 / 0.4 = 1_000_000
    })
    shareholders_df = pd.DataFrame({"name": ["A", "B", "C", "D", "E"]})

    fake_stock = MagicMock()
    fake_stock.company.overview = lambda: overview_df
    fake_stock.company.trading_stats = lambda: trading_df
    fake_stock.company.shareholders = lambda: shareholders_df

    repo = MagicMock()
    repo.upsert_company_profile = AsyncMock()
    svc = _make_service(repo)

    with _patch_vnstock(svc, _vnstock_with(fake_stock)):
        ok = await svc.sync_company_profile("FPT")
    assert ok is True
    repo.upsert_company_profile.assert_awaited_once()
    args, kwargs = repo.upsert_company_profile.await_args
    assert args[0] == "FPT"
    assert kwargs["company_profile"] == "FPT Corporation"
    assert kwargs["industry"] == "Tech"
    assert kwargs["foreign_percent"] == 0.4
    assert kwargs["outstanding_share"] == 1_000_000
    assert kwargs["no_shareholders"] == 5
    assert kwargs["no_employees"] == 42000
    assert kwargs["free_float_rate"] == pytest.approx(0.55)


@pytest.mark.asyncio
async def test_sync_company_profile_swallows_trading_stats_and_shareholders_errors():
    """When the enrichment endpoints fail, we still upsert the base
    overview with the fallback outstanding_share derived from issue_share."""
    overview_df = pd.DataFrame({
        "symbol": ["FPT"],
        "company_profile": ["P"],
        "issue_share": [500_000.0],
    })
    fake_stock = MagicMock()
    fake_stock.company.overview = lambda: overview_df
    fake_stock.company.trading_stats.side_effect = RuntimeError("trading_stats down")
    fake_stock.company.shareholders.side_effect = RuntimeError("shareholders down")

    repo = MagicMock()
    repo.upsert_company_profile = AsyncMock()
    svc = _make_service(repo)

    with _patch_vnstock(svc, _vnstock_with(fake_stock)):
        ok = await svc.sync_company_profile("FPT")
    assert ok is True
    kwargs = repo.upsert_company_profile.await_args.kwargs
    # Enrichment fields absent (or unset); base overview present.
    assert kwargs["company_profile"] == "P"


@pytest.mark.asyncio
async def test_sync_company_profile_returns_false_on_vnstock_exception():
    """vnstock.stock(...) raising bubbles up to the outer try; the method
    logs, attempts a rollback, and returns False."""
    fake_vnstock = MagicMock()
    fake_vnstock.stock.side_effect = RuntimeError("vnstock down")

    repo = MagicMock()
    repo.session = MagicMock()
    repo.session.rollback = AsyncMock()
    svc = _make_service(repo)

    with _patch_vnstock(svc, fake_vnstock):
        ok = await svc.sync_company_profile("FPT")
    assert ok is False
    repo.session.rollback.assert_awaited()


# ---------------------------------------------------------------------------
# sync_company_financials
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sync_company_financials_iterates_all_4_statement_types():
    svc = _make_service()
    # Each statement type returns 2 records → 8 total upserts.
    canned_records = [
        {"report_year": "2025", "revenue": 100},
        {"report_year": "2024", "revenue": 80},
    ]
    svc.repository.bulk_upsert_financial_statements = AsyncMock(return_value=2)

    with patch.object(svc, "get_financial_statement", AsyncMock(return_value=canned_records)):
        total = await svc.sync_company_financials("FPT")
    assert total == 8  # 4 statement types × 2 records persisted
    # 4 calls, one per statement type.
    assert svc.repository.bulk_upsert_financial_statements.await_count == 4


@pytest.mark.asyncio
async def test_sync_company_financials_skips_statement_types_with_no_records():
    """An empty record list → no bulk_upsert for that statement_type."""
    svc = _make_service()
    svc.repository.bulk_upsert_financial_statements = AsyncMock(return_value=0)

    with patch.object(svc, "get_financial_statement", AsyncMock(return_value=[])):
        total = await svc.sync_company_financials("FPT")
    assert total == 0
    svc.repository.bulk_upsert_financial_statements.assert_not_awaited()


@pytest.mark.asyncio
async def test_sync_company_financials_swallows_per_type_errors():
    """A failure on one statement_type doesn't abort the other 3."""
    svc = _make_service()
    svc.repository.bulk_upsert_financial_statements = AsyncMock(return_value=1)
    svc.repository.session = MagicMock()
    svc.repository.session.rollback = AsyncMock()

    call_count = {"n": 0}

    async def flaky_statement(*_a, **_kw):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("income statement down")
        return [{"report_year": "2025", "revenue": 100}]

    with patch.object(svc, "get_financial_statement", flaky_statement):
        total = await svc.sync_company_financials("FPT")
    # 1 type errored, 3 types each returned 1 record → 3 upserts each at 1 row.
    assert total == 3


@pytest.mark.asyncio
async def test_sync_company_financials_handles_unparseable_report_year():
    """A record whose report_year isn't an int doesn't crash the bulk
    upsert — it goes through as None."""
    svc = _make_service()
    svc.repository.bulk_upsert_financial_statements = AsyncMock(return_value=1)

    records = [{"report_year": "not-a-year", "revenue": 100}]
    with patch.object(svc, "get_financial_statement", AsyncMock(return_value=records)):
        total = await svc.sync_company_financials("FPT")
    assert total == 4  # 4 stmt types, all reach this branch → 4 upserts
    db_records = svc.repository.bulk_upsert_financial_statements.await_args_list[0].args[3]
    assert db_records[0]["report_year"] is None


# ---------------------------------------------------------------------------
# ensure_company_and_sync
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ensure_company_and_sync_skips_when_fresh():
    """Company synced within 24h is skipped (returns skipped=True)."""
    company = _company(last_synced_at=datetime.utcnow() - timedelta(hours=3))
    repo = MagicMock()
    repo.get_company_by_symbol = AsyncMock(return_value=company)
    svc = _make_service(repo)

    with patch.object(svc, "fetch_and_save_historical_data", AsyncMock()) as fetch_mock:
        out = await svc.ensure_company_and_sync("FPT")
    assert out == {"created": False, "synced": 0, "skipped": True}
    fetch_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_ensure_company_and_sync_syncs_when_stale():
    """Company exists but last_synced_at is older than 24h → re-sync history."""
    company = _company(last_synced_at=datetime.utcnow() - timedelta(hours=30))
    repo = MagicMock()
    repo.get_company_by_symbol = AsyncMock(return_value=company)
    svc = _make_service(repo)

    with patch.object(svc, "fetch_and_save_historical_data", AsyncMock(return_value=1250)) as fetch_mock:
        out = await svc.ensure_company_and_sync("FPT")
    assert out == {"created": False, "synced": 1250, "skipped": False}
    fetch_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_ensure_company_and_sync_creates_company_when_missing():
    """No company row → create from listing.all_symbols, then sync history."""
    repo = MagicMock()
    repo.get_company_by_symbol = AsyncMock(return_value=None)
    repo.create_company = AsyncMock(return_value=_company(id=99, symbol="NEW"))
    svc = _make_service(repo)

    listing_df = pd.DataFrame({
        "symbol": ["NEW"], "organ_name": ["New Corp"], "exchange": ["HOSE"]
    })
    fake_stock = MagicMock()
    fake_stock.listing.all_symbols.return_value = listing_df
    with _patch_vnstock(svc, _vnstock_with(fake_stock)), \
         patch.object(svc, "fetch_and_save_historical_data", AsyncMock(return_value=500)):
        out = await svc.ensure_company_and_sync("new")
    assert out["created"] is True
    assert out["synced"] == 500
    repo.create_company.assert_awaited_once()


@pytest.mark.asyncio
async def test_ensure_company_and_sync_defaults_to_hose_when_symbol_not_in_listing():
    """Symbol missing from listing → name=symbol, exchange=HOSE."""
    repo = MagicMock()
    repo.get_company_by_symbol = AsyncMock(return_value=None)
    repo.create_company = AsyncMock(return_value=_company(id=99, symbol="WTF"))
    svc = _make_service(repo)

    listing_df = pd.DataFrame({
        "symbol": ["FPT"], "organ_name": ["FPT Corp"], "exchange": ["HOSE"]
    })
    fake_stock = MagicMock()
    fake_stock.listing.all_symbols.return_value = listing_df
    with _patch_vnstock(svc, _vnstock_with(fake_stock)), \
         patch.object(svc, "fetch_and_save_historical_data", AsyncMock(return_value=0)):
        out = await svc.ensure_company_and_sync("WTF")
    create_kwargs = repo.create_company.await_args.kwargs
    assert create_kwargs == {"symbol": "WTF", "name": "WTF", "exchange": "HOSE"}
    assert out["created"] is True


@pytest.mark.asyncio
async def test_ensure_company_and_sync_raises_when_listing_fails_during_create():
    """vnstock listing.all_symbols raising during the create path should
    propagate (the caller handles it)."""
    repo = MagicMock()
    repo.get_company_by_symbol = AsyncMock(return_value=None)
    svc = _make_service(repo)

    fake_stock = MagicMock()
    fake_stock.listing.all_symbols.side_effect = RuntimeError("listing down")
    with _patch_vnstock(svc, _vnstock_with(fake_stock)), \
         pytest.raises(RuntimeError, match="listing down"):
        await svc.ensure_company_and_sync("FPT")


# ---------------------------------------------------------------------------
# sync_all_company_data
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sync_all_company_data_iterates_vn30_and_aggregates_results(monkeypatch):
    """Happy path: 30 symbols each succeed. asyncio.sleep is patched
    so the 2-second rate-limit doesn't actually wait."""
    monkeypatch.setattr(svc_mod.asyncio, "sleep", AsyncMock())

    svc = _make_service()
    with patch.object(svc, "sync_company_profile", AsyncMock(return_value=True)), \
         patch.object(svc, "sync_company_financials", AsyncMock(return_value=4)), \
         patch.object(svc, "ensure_company_and_sync",
                      AsyncMock(return_value={"created": False, "synced": 1000, "skipped": False})):
        result = await svc.sync_all_company_data()

    n = len(svc.STOCK_GROUPS["VN30"])
    assert result["profiles"] == n
    assert result["financials"] == n * 4
    assert result["historical"] == n * 1000
    assert result["errors"] == []


@pytest.mark.asyncio
async def test_sync_all_company_data_records_per_symbol_errors(monkeypatch):
    """A symbol whose sync_company_profile raises is recorded in errors,
    not aborted. asyncio.sleep is still mocked."""
    monkeypatch.setattr(svc_mod.asyncio, "sleep", AsyncMock())

    svc = _make_service()
    svc.repository.session = MagicMock()
    svc.repository.session.rollback = AsyncMock()

    sequence = iter(range(100))

    async def flaky_profile(_sym):
        i = next(sequence)
        if i == 0:
            raise RuntimeError("boom on first")
        return True

    with patch.object(svc, "sync_company_profile", flaky_profile), \
         patch.object(svc, "sync_company_financials", AsyncMock(return_value=4)), \
         patch.object(svc, "ensure_company_and_sync",
                      AsyncMock(return_value={"created": False, "synced": 0, "skipped": False})):
        result = await svc.sync_all_company_data()

    # First symbol errored — its label is in errors, others succeeded.
    assert any("boom on first" in e for e in result["errors"])
    n = len(svc.STOCK_GROUPS["VN30"])
    assert result["profiles"] == n - 1


@pytest.mark.asyncio
async def test_sync_all_company_data_swallows_history_errors_separately(monkeypatch):
    """ensure_company_and_sync raising on one symbol is recorded as
    a {symbol}-historical: ... error but profile/financials counters
    for that symbol still tick up."""
    monkeypatch.setattr(svc_mod.asyncio, "sleep", AsyncMock())

    svc = _make_service()
    svc.repository.session = MagicMock()
    svc.repository.session.rollback = AsyncMock()

    sequence = iter(range(100))

    async def flaky_history(_sym):
        i = next(sequence)
        if i == 0:
            raise RuntimeError("history-boom")
        return {"created": False, "synced": 100, "skipped": False}

    with patch.object(svc, "sync_company_profile", AsyncMock(return_value=True)), \
         patch.object(svc, "sync_company_financials", AsyncMock(return_value=2)), \
         patch.object(svc, "ensure_company_and_sync", flaky_history):
        result = await svc.sync_all_company_data()

    assert any("-historical: history-boom" in e for e in result["errors"])
    n = len(svc.STOCK_GROUPS["VN30"])
    # All 30 profiles counted; 29 historical-syncs ran.
    assert result["profiles"] == n
    assert result["historical"] == (n - 1) * 100


@pytest.mark.asyncio
async def test_sync_all_company_data_counts_skipped_history_without_increment(monkeypatch):
    """ensure_company_and_sync returning {skipped: True} doesn't bump
    historical count — but doesn't fail either."""
    monkeypatch.setattr(svc_mod.asyncio, "sleep", AsyncMock())

    svc = _make_service()
    with patch.object(svc, "sync_company_profile", AsyncMock(return_value=True)), \
         patch.object(svc, "sync_company_financials", AsyncMock(return_value=2)), \
         patch.object(svc, "ensure_company_and_sync",
                      AsyncMock(return_value={"created": False, "synced": 0, "skipped": True})):
        result = await svc.sync_all_company_data()

    assert result["historical"] == 0
    assert result["errors"] == []
