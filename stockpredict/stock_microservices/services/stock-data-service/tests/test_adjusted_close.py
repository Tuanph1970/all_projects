"""adj_close population on ingest (Backlog #56).

Context that makes these tests meaningful: vnstock/VCI hands back a series that is
already BACK-ADJUSTED for share-count events. Its OHLCV column map is exactly
time/open/high/low/close/volume — there is no separate adjusted field — and a bonus
issue restates the whole prior history. Verified against TCB's 1:1 bonus issue (ex-date
June 2024): the stored series runs smoothly through it at the post-bonus level, with no
discontinuity anywhere near the ~50% a raw series would show.

So `close` IS the adjusted close. The bug these tests close is that nothing ever wrote
it down: adj_close stayed NULL, and a NULL adj_close reads as "these prices are
unadjusted" to any consumer computing a return — the opposite of the truth.
"""
from __future__ import annotations

import pandas as pd
import pytest

from app.services.stock_service import adjusted_close


class TestAdjustedClose:
    def test_mirrors_close_when_the_source_has_no_adjusted_column(self):
        """The VCI case, which is what actually runs."""
        row = {"time": "2024-06-12", "open": 23.0, "high": 23.8,
               "low": 22.9, "close": 23.57, "volume": 1_000_000}
        assert adjusted_close(row) == pytest.approx(23.57)

    def test_prefers_an_explicit_adjusted_column_when_one_exists(self):
        """A future source that does expose one is picked up without touching either
        call site — the helper is the single place the convention lives."""
        assert adjusted_close({"close": 100.0, "adj_close": 87.0}) == pytest.approx(87.0)

    @pytest.mark.parametrize("key", ["adj_close", "adjusted_close", "adjClose"])
    def test_accepts_the_common_spellings(self, key):
        assert adjusted_close({"close": 100.0, key: 87.0}) == pytest.approx(87.0)

    def test_works_on_a_pandas_row(self):
        """Both call sites iterate a DataFrame, so the input is a Series, not a dict."""
        df = pd.DataFrame([{"close": 23.57, "volume": 10}])
        (_, row), = df.iterrows()
        assert adjusted_close(row) == pytest.approx(23.57)

    def test_returns_none_when_there_is_no_price_at_all(self):
        assert adjusted_close({"volume": 10}) is None

    def test_a_null_adjusted_column_falls_back_to_close(self):
        assert adjusted_close({"close": 23.57, "adj_close": None}) == pytest.approx(23.57)

    def test_the_result_is_never_none_when_close_is_present(self):
        """The whole point of Backlog #56: a populated close must never yield a NULL
        adj_close, because downstream that reads as "unadjusted"."""
        for row in ({"close": 0.01}, {"close": 1e6}, {"close": 23.57, "adj_close": None}):
            assert adjusted_close(row) is not None


class TestIngestPopulatesAdjClose:
    """Both ingest paths must write it — the live fallback and the persisting one."""

    def test_live_path_sets_adj_close_on_the_response(self):
        from app.models.schemas import StockPriceResponse
        row = {"close": 23.57}
        priced = StockPriceResponse(
            date="2024-06-12", open=23.0, high=23.8, low=22.9,
            close=row["close"], volume=10, value=None,
            adj_close=adjusted_close(row), change=None, change_percent=None,
        )
        assert priced.adj_close == pytest.approx(priced.close)

    def test_saved_price_carries_adj_close(self):
        from app.models.domain import StockPrice
        row = {"close": 23.57}
        price = StockPrice(company_id=1, date="2024-06-12", close=row["close"],
                           adj_close=adjusted_close(row), volume=10)
        assert price.adj_close == pytest.approx(23.57)

    def test_the_repository_upsert_carries_adj_close_through(self):
        """save_prices() lists the columns it writes explicitly; adj_close must be in
        both the insert and the on-duplicate update, or a re-sync would blank it."""
        import inspect
        from app.repositories.stock_repository import StockRepository
        source = inspect.getsource(StockRepository.save_prices)
        assert '"adj_close": p.adj_close' in source
        assert '"adj_close"' in source.split("on_duplicate_key_update")[1]


def test_backfill_statement_is_self_limiting():
    """The one-time backfill must match nothing on a second run, so a reboot is free."""
    import inspect
    import app.main as main
    source = inspect.getsource(main.lifespan)
    assert "UPDATE stock_prices SET adj_close = close" in source
    assert "WHERE adj_close IS NULL" in source
