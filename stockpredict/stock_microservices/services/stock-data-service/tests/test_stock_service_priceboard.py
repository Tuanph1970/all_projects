"""Tests for the industry-live + price-board chain on StockService.

Covers the four remaining big methods on stock_service.py:
- get_companies_by_industry_code_live: vnstock symbols_by_industries
  filter + pagination + name enrichment from all_symbols.
- _price_board_row_to_dict: the static DB-row → camelCase mapper.
- _fetch_price_board_live: synchronous requests.post to Vietcap with
  the bid/ask + matchPrice reshape, error swallow → [].
- refresh_price_board: deletes the group's rows + inserts fresh +
  fans out price updates.
- get_price_board: DB hit short-circuits; DB miss triggers refresh +
  re-reads; stale rows (#48) trigger a refresh, and survive a failed one.

All vnstock + Vietcap HTTP + event publisher are mocked.
"""
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from app.models.domain import PriceBoard
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


def _row_with_scalars(rows):
    """Wrap a list as a SQLAlchemy result-shaped MagicMock."""
    result = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = rows
    result.scalars.return_value = scalars
    return result


# ---------------------------------------------------------------------------
# get_companies_by_industry_code_live
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_industry_live_returns_empty_when_no_data():
    fake_stock = MagicMock()
    fake_stock.listing.symbols_by_industries.return_value = pd.DataFrame()
    svc = _make_service()
    with _patch_vnstock(svc, _vnstock_with(fake_stock)):
        out = await svc.get_companies_by_industry_code_live("8300")
    assert out.total == 0
    assert out.items == []


@pytest.mark.asyncio
async def test_industry_live_returns_empty_when_no_icb_column():
    """A DataFrame that doesn't expose any of the known ICB column names
    returns empty rather than crashing."""
    df = pd.DataFrame({"symbol": ["FPT"], "noise_col": [1]})
    fake_stock = MagicMock()
    fake_stock.listing.symbols_by_industries.return_value = df
    svc = _make_service()
    with _patch_vnstock(svc, _vnstock_with(fake_stock)):
        out = await svc.get_companies_by_industry_code_live("8300")
    assert out.total == 0


@pytest.mark.asyncio
async def test_industry_live_returns_empty_when_no_match():
    df = pd.DataFrame({
        "symbol": ["FPT", "VNM"],
        "icb_code": ["9530", "3500"],
        "icb_name": ["Tech", "Food"],
    })
    fake_stock = MagicMock()
    fake_stock.listing.symbols_by_industries.return_value = df
    fake_stock.listing.all_symbols.return_value = pd.DataFrame()
    svc = _make_service()
    with _patch_vnstock(svc, _vnstock_with(fake_stock)):
        # Code that nothing starts with.
        out = await svc.get_companies_by_industry_code_live("99999")
    assert out.total == 0


@pytest.mark.asyncio
async def test_industry_live_filters_and_paginates_with_enrichment():
    """All 3 banks share the 8300 prefix; page 1, page_size 2 returns
    2 of 3 with company names enriched from all_symbols()."""
    industries_df = pd.DataFrame({
        "symbol": ["VCB", "BID", "CTG", "FPT"],
        # All bank codes start with "8300" (the prefix we'll filter for).
        "icb_code": ["83001", "83002", "83003", "95301"],
        "icb_name": ["Banks", "Banks", "Banks", "Tech"],
        "exchange": ["HOSE", "HOSE", "HOSE", "HOSE"],
        "com_type_code": ["B", "B", "B", "T"],
    })
    listing_df = pd.DataFrame({
        "symbol": ["VCB", "BID", "CTG"],
        "organ_name": ["Vietcombank", "BIDV", "VietinBank"],
    })

    fake_stock = MagicMock()
    fake_stock.listing.symbols_by_industries.return_value = industries_df
    fake_stock.listing.all_symbols.return_value = listing_df

    svc = _make_service()
    with _patch_vnstock(svc, _vnstock_with(fake_stock)):
        page1 = await svc.get_companies_by_industry_code_live("8300", page=1, page_size=2)
    assert page1.total == 3   # 3 of 4 match the 8300 prefix
    assert page1.page_size == 2
    assert page1.total_pages == 2
    assert len(page1.items) == 2
    assert page1.items[0].symbol == "VCB"
    assert page1.items[0].name == "Vietcombank"  # enriched
    assert page1.items[1].symbol == "BID"
    assert page1.items[1].name == "BIDV"


@pytest.mark.asyncio
async def test_industry_live_returns_symbol_as_name_when_enrichment_missing():
    """No matching row in all_symbols → fall back to using the symbol
    itself as the display name."""
    industries_df = pd.DataFrame({
        "symbol": ["XYZ"],
        "icb_code": ["8300"],
        "icb_name": ["Banks"],
    })
    listing_df = pd.DataFrame({"symbol": ["ABC"], "organ_name": ["Other"]})

    fake_stock = MagicMock()
    fake_stock.listing.symbols_by_industries.return_value = industries_df
    fake_stock.listing.all_symbols.return_value = listing_df

    svc = _make_service()
    with _patch_vnstock(svc, _vnstock_with(fake_stock)):
        out = await svc.get_companies_by_industry_code_live("8300")
    assert out.items[0].name == "XYZ"


@pytest.mark.asyncio
async def test_industry_live_swallows_enrichment_failure():
    """When listing.all_symbols raises, filtering + pagination still
    succeed — just no name enrichment."""
    industries_df = pd.DataFrame({
        "symbol": ["FPT"], "icb_code": ["9530"], "icb_name": ["Tech"],
    })
    fake_stock = MagicMock()
    fake_stock.listing.symbols_by_industries.return_value = industries_df
    fake_stock.listing.all_symbols.side_effect = RuntimeError("listing down")

    svc = _make_service()
    with _patch_vnstock(svc, _vnstock_with(fake_stock)):
        out = await svc.get_companies_by_industry_code_live("9530")
    assert out.total == 1
    assert out.items[0].symbol == "FPT"
    # No enrichment → name falls back to symbol.
    assert out.items[0].name == "FPT"


@pytest.mark.asyncio
async def test_industry_live_returns_empty_on_outer_exception():
    """vnstock.stock(...) raising returns a valid empty PaginatedResponse,
    not None or a 500."""
    fake_vnstock = MagicMock()
    fake_vnstock.stock.side_effect = RuntimeError("vnstock down")
    svc = _make_service()
    with _patch_vnstock(svc, fake_vnstock):
        out = await svc.get_companies_by_industry_code_live("8300")
    assert out.total == 0
    assert out.items == []
    assert out.total_pages == 0


# ---------------------------------------------------------------------------
# _price_board_row_to_dict
# ---------------------------------------------------------------------------

def test_price_board_row_to_dict_maps_all_camelcase_fields():
    row = PriceBoard(
        symbol="FPT", stock_group="VN30",
        ref_price=100.0, ceiling=110.0, floor=90.0,
        match_price=105.0, match_qty=1000, match_value=105_000,
        change=5.0, change_percent=5.0,
        total_qty=10_000, total_value=1_050_000,
        highest=106.0, lowest=99.0, open_price=100.0, average_price=104.0,
        buy_price_1=104.0, buy_qty_1=500,
        buy_price_2=103.5, buy_qty_2=300,
        buy_price_3=103.0, buy_qty_3=200,
        sell_price_1=105.5, sell_qty_1=400,
        sell_price_2=106.0, sell_qty_2=300,
        sell_price_3=106.5, sell_qty_3=200,
        exchange="HOSE", trading_status="NORMAL",
    )
    out = StockService._price_board_row_to_dict(row)
    # snake_case → camelCase confirmed for the headline fields.
    assert out["symbol"] == "FPT"
    assert out["refPrice"] == 100.0
    assert out["matchPrice"] == 105.0
    assert out["matchQty"] == 1000
    assert out["changePercent"] == 5.0
    assert out["totalQty"] == 10_000
    assert out["openPrice"] == 100.0
    assert out["averagePrice"] == 104.0
    assert out["buyPrice1"] == 104.0
    assert out["sellQty3"] == 200
    assert out["tradingStatus"] == "NORMAL"


# ---------------------------------------------------------------------------
# _fetch_price_board_live
# ---------------------------------------------------------------------------

def _vietcap_item(symbol="FPT", current_price=105.0, ref_price=100.0,
                  bid_count=3, ask_count=3):
    """One element of the Vietcap response array. Shape mirrors the
    real payload (listingInfo + matchPrice + bidAsk wrappers)."""
    return {
        "listingInfo": {
            "symbol": symbol,
            "refPrice": ref_price,
            "ceiling": ref_price * 1.07,
            "floor": ref_price * 0.93,
            "board": "HOSE",
            "tradingStatus": "NORMAL",
        },
        "matchPrice": {
            "matchPrice": current_price,
            "matchVol": 1000,
            "accumulatedValue": 105_000_000,
            "accumulatedVolume": 100_000,
            "highest": current_price + 1,
            "lowest": current_price - 1,
            "openPrice": ref_price,
            "avgMatchPrice": current_price,
        },
        "bidAsk": {
            "bidPrices": [{"price": ref_price - i, "volume": 100 + i} for i in range(bid_count)],
            "askPrices": [{"price": ref_price + i + 1, "volume": 200 + i} for i in range(ask_count)],
        },
    }


@pytest.mark.asyncio
async def test_fetch_price_board_live_reshapes_records():
    """Happy path: 2 items → 2 records with computed change + bid/ask
    expanded into the 1/2/3 columns."""
    fake_response = MagicMock()
    fake_response.json.return_value = [_vietcap_item(), _vietcap_item(symbol="VNM")]
    fake_response.raise_for_status = lambda: None

    svc = _make_service()
    with patch("requests.post", return_value=fake_response):
        out = await svc._fetch_price_board_live("VN30")
    assert len(out) == 2
    rec0 = out[0]
    assert rec0["symbol"] == "FPT"
    # change = matchPrice - refPrice = 105 - 100 = 5
    assert rec0["change"] == 5.0
    assert rec0["changePercent"] == 5.0
    # Bid/ask flattened.
    assert rec0["buyPrice1"] == 100.0
    assert rec0["buyQty1"] == 100
    assert rec0["buyPrice3"] == 98.0
    assert rec0["sellPrice1"] == 101.0
    assert rec0["sellQty3"] == 202
    assert rec0["exchange"] == "HOSE"


@pytest.mark.asyncio
async def test_fetch_price_board_live_handles_fewer_than_3_bidask_levels():
    """Items with only 1 bid + 1 ask level: levels 2/3 are None, not crashes."""
    fake_response = MagicMock()
    fake_response.json.return_value = [_vietcap_item(bid_count=1, ask_count=1)]
    fake_response.raise_for_status = lambda: None

    svc = _make_service()
    with patch("requests.post", return_value=fake_response):
        out = await svc._fetch_price_board_live("VN30")
    assert out[0]["buyPrice1"] is not None
    assert out[0]["buyPrice2"] is None
    assert out[0]["sellPrice2"] is None


@pytest.mark.asyncio
async def test_fetch_price_board_live_handles_missing_ref_price_gracefully():
    """When refPrice is None or 0 we skip the change-percent calc rather
    than divide-by-zero."""
    item = _vietcap_item(ref_price=0)
    item["listingInfo"]["refPrice"] = None  # explicit None
    fake_response = MagicMock()
    fake_response.json.return_value = [item]
    fake_response.raise_for_status = lambda: None

    svc = _make_service()
    with patch("requests.post", return_value=fake_response):
        out = await svc._fetch_price_board_live("VN30")
    assert out[0]["change"] is None
    assert out[0]["changePercent"] is None


@pytest.mark.asyncio
async def test_fetch_price_board_live_returns_empty_on_http_failure():
    """Any exception from the Vietcap call surfaces as [] — never 500."""
    svc = _make_service()
    with patch("requests.post", side_effect=ConnectionError("Vietcap down")):
        out = await svc._fetch_price_board_live("VN30")
    assert out == []


@pytest.mark.asyncio
async def test_fetch_price_board_live_returns_empty_when_response_empty():
    fake_response = MagicMock()
    fake_response.json.return_value = []
    fake_response.raise_for_status = lambda: None

    svc = _make_service()
    with patch("requests.post", return_value=fake_response):
        out = await svc._fetch_price_board_live("VN30")
    assert out == []


# ---------------------------------------------------------------------------
# refresh_price_board
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_refresh_price_board_returns_zero_when_no_live_records():
    svc = _make_service()
    repo = svc.repository
    repo.session = MagicMock()
    repo.session.execute = AsyncMock()
    with patch.object(svc, "_fetch_price_board_live", AsyncMock(return_value=[])):
        n = await svc.refresh_price_board("VN30")
    assert n == 0
    # No DELETE issued because we short-circuited.
    repo.session.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_refresh_price_board_persists_records_and_publishes_events():
    """Happy path: DELETE old rows, add new PriceBoard rows, commit,
    then fan out via publish_price_updates."""
    fake_records = [
        {
            "symbol": "FPT", "matchPrice": 105.0, "refPrice": 100.0,
            "change": 5.0, "changePercent": 5.0, "totalQty": 1000,
        }
    ]

    svc = _make_service()
    repo = svc.repository
    repo.session = MagicMock()
    repo.session.execute = AsyncMock()
    repo.session.add = MagicMock()
    repo.session.commit = AsyncMock()

    publish_mock = AsyncMock()
    with patch.object(svc, "_fetch_price_board_live", AsyncMock(return_value=fake_records)), \
         patch("app.services.event_publisher.publish_price_updates", publish_mock):
        n = await svc.refresh_price_board("VN30")
    assert n == 1
    # DELETE-then-INSERT pattern.
    repo.session.execute.assert_awaited_once()  # the DELETE
    repo.session.add.assert_called_once()
    repo.session.commit.assert_awaited_once()
    publish_mock.assert_awaited_once_with(fake_records)


@pytest.mark.asyncio
async def test_refresh_price_board_swallows_publish_failure():
    """If publish_price_updates raises, the refresh still returns the
    count it actually persisted — events are best-effort."""
    fake_records = [{"symbol": "FPT", "matchPrice": 105.0}]

    svc = _make_service()
    repo = svc.repository
    repo.session = MagicMock()
    repo.session.execute = AsyncMock()
    repo.session.add = MagicMock()
    repo.session.commit = AsyncMock()

    with patch.object(svc, "_fetch_price_board_live", AsyncMock(return_value=fake_records)), \
         patch("app.services.event_publisher.publish_price_updates",
               AsyncMock(side_effect=RuntimeError("rabbit down"))):
        n = await svc.refresh_price_board("VN30")
    assert n == 1


# ---------------------------------------------------------------------------
# get_price_board
# ---------------------------------------------------------------------------

# #48 — the board is refreshed when stale. VN trades 09:00-15:00 ICT (UTC+7),
# Mon-Fri. These instants are UTC, as PriceBoard.updated_at is stored.
TUE_1030_ICT = datetime(2026, 10, 20, 3, 30)    # Tuesday, mid-session
TUE_0100_ICT = datetime(2026, 10, 19, 18, 0)    # Tuesday 01:00, the nightly refresh
TUE_1600_ICT = datetime(2026, 10, 20, 9, 0)     # Tuesday, after the close
MON_1600_ICT = datetime(2026, 10, 19, 9, 0)     # Monday, after the close
SAT_1000_ICT = datetime(2026, 10, 24, 3, 0)     # Saturday
FRI_1500_ICT = datetime(2026, 10, 23, 8, 0)     # Friday, the close itself
FRI_1430_ICT = datetime(2026, 10, 23, 7, 30)    # Friday, before the close
MAX_AGE = timedelta(seconds=60)


@pytest.mark.parametrize("updated_at, now, stale", [
    # In session: stale once older than the max age
    (TUE_1030_ICT - timedelta(seconds=30), TUE_1030_ICT, False),
    (TUE_1030_ICT - timedelta(seconds=90), TUE_1030_ICT, True),
    # The reported bug: the 01:00 refresh served all day long
    (TUE_0100_ICT, TUE_1030_ICT, True),
    # After the close: fresh only if taken at/after today's close
    (TUE_0100_ICT, TUE_1600_ICT, True),
    (TUE_1600_ICT - timedelta(minutes=30), TUE_1600_ICT, False),
    # Overnight: yesterday's post-close snapshot is still the latest market
    (MON_1600_ICT, TUE_0100_ICT, False),
    # Weekend: Friday's close is the latest market; earlier is stale
    (FRI_1500_ICT, SAT_1000_ICT, False),
    (FRI_1430_ICT, SAT_1000_ICT, True),
    (None, SAT_1000_ICT, True),
])
def test_price_board_is_stale(updated_at, now, stale):
    assert svc_mod.price_board_is_stale(updated_at, now, MAX_AGE) is stale


def _board_rows(updated_at):
    return [
        PriceBoard(symbol="FPT", stock_group="VN30", match_price=105.0,
                   ref_price=100.0, updated_at=updated_at),
        PriceBoard(symbol="VNM", stock_group="VN30", match_price=70.0,
                   ref_price=70.0, updated_at=updated_at),
    ]


@pytest.mark.asyncio
async def test_get_price_board_refreshes_stale_rows_during_session():
    """#48: rows from the 01:00 refresh must not be served mid-session."""
    stale = _row_with_scalars(_board_rows(TUE_0100_ICT))
    fresh = _row_with_scalars(_board_rows(TUE_1030_ICT))

    svc = _make_service()
    svc.repository.session = MagicMock()
    svc.repository.session.execute = AsyncMock(side_effect=[stale, fresh])

    with patch.object(svc_mod, "_utcnow", return_value=TUE_1030_ICT), \
         patch.object(svc, "refresh_price_board", AsyncMock(return_value=2)) as refresh_mock:
        out = await svc.get_price_board("VN30")
    refresh_mock.assert_awaited_once_with("VN30")
    assert svc.repository.session.execute.await_count == 2  # read, re-read
    assert len(out) == 2


@pytest.mark.asyncio
async def test_get_price_board_serves_stale_rows_when_refresh_fails():
    """A failed refresh must not blank a board that has data."""
    stale = _row_with_scalars(_board_rows(TUE_0100_ICT))

    svc = _make_service()
    svc.repository.session = MagicMock()
    svc.repository.session.execute = AsyncMock(return_value=stale)

    with patch.object(svc_mod, "_utcnow", return_value=TUE_1030_ICT), \
         patch.object(svc, "refresh_price_board", AsyncMock(return_value=0)):
        out = await svc.get_price_board("VN30")
    assert [r["symbol"] for r in out] == ["FPT", "VNM"]


@pytest.mark.asyncio
async def test_get_price_board_returns_cached_rows_when_db_populated():
    cached = _board_rows(TUE_1030_ICT - timedelta(seconds=10))

    svc = _make_service()
    repo = svc.repository
    repo.session = MagicMock()
    repo.session.execute = AsyncMock(return_value=_row_with_scalars(cached))

    with patch.object(svc_mod, "_utcnow", return_value=TUE_1030_ICT), \
         patch.object(svc, "refresh_price_board", AsyncMock()) as refresh_mock:
        out = await svc.get_price_board("VN30")
    refresh_mock.assert_not_awaited()  # cache hit short-circuits
    assert len(out) == 2
    assert out[0]["symbol"] == "FPT"
    assert out[0]["matchPrice"] == 105.0


@pytest.mark.asyncio
async def test_get_price_board_fetches_and_re_reads_when_db_empty():
    """First execute() returns empty, refresh_price_board returns >0,
    second execute() returns the fresh rows."""
    empty_result = _row_with_scalars([])
    fresh_rows = [PriceBoard(symbol="FPT", stock_group="VN30", match_price=105.0)]
    fresh_result = _row_with_scalars(fresh_rows)

    svc = _make_service()
    repo = svc.repository
    repo.session = MagicMock()
    repo.session.execute = AsyncMock(side_effect=[empty_result, fresh_result])

    with patch.object(svc, "refresh_price_board", AsyncMock(return_value=1)) as refresh_mock:
        out = await svc.get_price_board("VN30")
    refresh_mock.assert_awaited_once()
    assert len(out) == 1
    assert out[0]["symbol"] == "FPT"


@pytest.mark.asyncio
async def test_get_price_board_returns_empty_when_refresh_yields_nothing():
    """DB empty + Vietcap returned nothing → [], no second execute."""
    svc = _make_service()
    repo = svc.repository
    repo.session = MagicMock()
    repo.session.execute = AsyncMock(return_value=_row_with_scalars([]))

    with patch.object(svc, "refresh_price_board", AsyncMock(return_value=0)):
        out = await svc.get_price_board("VN30")
    assert out == []
