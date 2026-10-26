"""Backlog #91 — `market_indices` was a dead table; now it is populated.

It had a SQLAlchemy model, a repository reader (`stock_repository.py:293`) and
two public endpoints (`/market/indices`, `/market/indices/latest`) — and **no
writer anywhere in the repo**, so both endpoints returned empty forever.

Worse than ordinary dead code, because it *looked* like the right answer: the
Edwards & Magee candidate register cited "index data exists (stock-data-service
serves VNINDEX / VN30 / HNX)" as an EM-6 precondition, which was true of the
endpoint and false of the data. EM-6 had to route around it.

POPULATED rather than deleted, and the evidence decided it:

* the frontend's `MARKET_INDICES` constants are **defined but never called**,
  so nothing breaks either way;
* `tests/integration/test_stock_data_flow.py` asserts 200 and comments
  "Should return index data (VN-Index, HNX-Index, etc.)" — the intent is
  documented and was passing vacuously on an empty list;
* the data is available and was verified at EM-6: VNINDEX 5,672 bars from
  2004-01-05, HNXINDEX 5,217 from 2005, UPCOMINDEX 4,238 from 2009, VN30
  3,669 and HNX30 3,522 from 2012.

So deleting would have removed a documented capability that the vendor can
actually serve.
"""
from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from app.services import stock_service as svc_mod
from app.services.stock_service import StockService


def _quote_frame(n: int = 3, start: float = 1200.0) -> pd.DataFrame:
    base = date(2026, 10, 1)
    return pd.DataFrame({
        "time": [str(base + timedelta(days=i)) for i in range(n)],
        "open": [start + i for i in range(n)],
        "high": [start + i + 5 for i in range(n)],
        "low": [start + i - 5 for i in range(n)],
        "close": [start + i + 2 for i in range(n)],
        "volume": [1_000_000 + i for i in range(n)],
    })


def _service(frame=None, raises=None):
    svc = StockService(MagicMock())

    def history(**kwargs):
        if raises is not None:
            raise raises
        return frame if frame is not None else _quote_frame()

    stock = MagicMock()
    stock.quote.history = history
    fv = MagicMock()
    fv.stock.return_value = stock
    return svc, fv


def _patched(svc, fv):
    return patch.object(type(svc), "vnstock",
                        new_callable=lambda: property(lambda self: fv))


class TestTheIndexSet:

    def test_the_codes_are_the_ones_the_vendor_actually_serves(self):
        """Verified at EM-6 against VCI. VN100 is deliberately absent: 1,082
        bars from 2022 is too short to be useful as an index series."""
        assert set(svc_mod.MARKET_INDEX_CODES) == {
            "VNINDEX", "VN30", "HNXINDEX", "HNX30", "UPCOMINDEX",
        }

    def test_every_code_has_a_display_name(self):
        for code in svc_mod.MARKET_INDEX_CODES:
            assert svc_mod.MARKET_INDEX_NAMES.get(code)


class TestSync:

    @pytest.mark.asyncio
    async def test_rows_are_mapped_and_upserted(self):
        svc, fv = _service()
        svc.repository.bulk_upsert_market_indices = AsyncMock(return_value=3)
        with _patched(svc, fv):
            n = await svc.sync_market_indices(days=5)
        # the method reports what the REPOSITORY wrote, not what it mapped
        assert n == 3
        recs = svc.repository.bulk_upsert_market_indices.call_args.args[0]
        # 3 bars x 5 codes were mapped and handed over
        assert len(recs) == 3 * len(svc_mod.MARKET_INDEX_CODES)
        row = recs[0]
        for key in ("code", "name", "date", "open", "high", "low", "close", "volume"):
            assert key in row, key
        assert row["close"] is not None

    @pytest.mark.asyncio
    async def test_change_is_computed_from_the_previous_close(self):
        """The model carries change / change_percent and the vendor does not,
        so they are derived — and the FIRST bar has no predecessor, so it gets
        None rather than a fabricated zero."""
        svc, fv = _service(_quote_frame(n=3, start=1000.0))
        svc.repository.bulk_upsert_market_indices = AsyncMock(return_value=0)
        with _patched(svc, fv):
            await svc.sync_market_indices(days=5)
        recs = svc.repository.bulk_upsert_market_indices.call_args.args[0]
        first = [r for r in recs if r["code"] == "VNINDEX"][0]
        second = [r for r in recs if r["code"] == "VNINDEX"][1]
        assert first["change"] is None and first["change_percent"] is None
        assert second["change"] == pytest.approx(1.0)
        assert second["change_percent"] == pytest.approx(1.0 / 1002.0 * 100.0, rel=1e-3)

    @pytest.mark.asyncio
    async def test_one_failing_index_does_not_abort_the_others(self):
        """Five vendor calls; a single outage must not lose the other four."""
        svc = StockService(MagicMock())
        svc.repository.bulk_upsert_market_indices = AsyncMock(return_value=0)
        calls = {"n": 0}

        def history(**kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("vendor hiccup")
            return _quote_frame()

        stock = MagicMock()
        stock.quote.history = history
        fv = MagicMock()
        fv.stock.return_value = stock
        with _patched(svc, fv):
            await svc.sync_market_indices(days=5)
        recs = svc.repository.bulk_upsert_market_indices.call_args.args[0]
        codes = {r["code"] for r in recs}
        assert len(codes) == len(svc_mod.MARKET_INDEX_CODES) - 1

    @pytest.mark.asyncio
    async def test_an_empty_vendor_response_writes_nothing(self):
        svc, fv = _service(pd.DataFrame())
        svc.repository.bulk_upsert_market_indices = AsyncMock(return_value=0)
        with _patched(svc, fv):
            n = await svc.sync_market_indices(days=5)
        assert n == 0
        svc.repository.bulk_upsert_market_indices.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_a_row_without_a_close_is_skipped(self):
        """`MarketIndex.close` is NOT NULL, so a priceless row would raise on
        insert and lose the whole batch."""
        frame = _quote_frame(n=2)
        frame.loc[0, "close"] = None
        svc, fv = _service(frame)
        svc.repository.bulk_upsert_market_indices = AsyncMock(return_value=0)
        with _patched(svc, fv):
            await svc.sync_market_indices(days=5)
        recs = svc.repository.bulk_upsert_market_indices.call_args.args[0]
        assert all(r["close"] is not None for r in recs)
        assert len(recs) == len(svc_mod.MARKET_INDEX_CODES)  # 1 of 2 bars kept


class TestReadFallback:

    @pytest.mark.asyncio
    async def test_an_empty_table_triggers_a_sync_then_re_reads(self):
        """The pattern this codebase already uses for historical data and the
        price board: serve the cache, fall back to the vendor when it is
        empty."""
        svc = StockService(MagicMock())
        svc.repository.get_market_indices = AsyncMock(side_effect=[[], ["row"]])
        svc.sync_market_indices = AsyncMock(return_value=5)
        with patch.object(svc, "_market_index_rows_to_response",
                          lambda rows: list(rows)):
            out = await svc.get_market_indices()
        svc.sync_market_indices.assert_awaited_once()
        assert out == ["row"]

    @pytest.mark.asyncio
    async def test_a_populated_table_does_not_hit_the_vendor(self):
        svc = StockService(MagicMock())
        svc.repository.get_market_indices = AsyncMock(return_value=["row"])
        svc.sync_market_indices = AsyncMock(return_value=0)
        with patch.object(svc, "_market_index_rows_to_response",
                          lambda rows: list(rows)):
            await svc.get_market_indices()
        svc.sync_market_indices.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_a_failed_sync_returns_empty_rather_than_raising(self):
        svc = StockService(MagicMock())
        svc.repository.get_market_indices = AsyncMock(return_value=[])
        svc.sync_market_indices = AsyncMock(side_effect=RuntimeError("down"))
        out = await svc.get_market_indices()
        assert out == []


class TestItIsKeptFresh:
    """Backlog #91: the on-read fallback only fires on an EMPTY table, so
    without a refresh the first read would backfill a year and then serve
    that same snapshot forever. The daily 01:00 cycle in `main._run_sync`
    already refreshes the price board; the indices ride along with it."""

    def test_the_daily_sync_cycle_refreshes_the_indices(self):
        import inspect
        import app.main as main_mod
        src = inspect.getsource(main_mod._run_sync)
        assert "sync_market_indices" in src, (
            "nothing refreshes market_indices, so it would go stale after the "
            "first backfill"
        )

    def test_the_daily_refresh_uses_a_short_window_not_the_full_backfill(self):
        """A year of history every night would be five needless vendor calls
        over the guest quota; the upsert is bounded to the dates it writes, so
        a week closes any gap."""
        import inspect
        import app.main as main_mod
        src = inspect.getsource(main_mod._run_sync)
        assert "sync_market_indices(days=7)" in src

    def test_a_failing_index_refresh_does_not_break_the_sync_cycle(self):
        import inspect
        import app.main as main_mod
        src = inspect.getsource(main_mod._run_sync)
        tail = src[src.index("sync_market_indices"):]
        assert "except Exception" in tail
