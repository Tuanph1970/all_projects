"""The dashboard's long-term recommendations were empty because of one word.

`get_financial_statement(symbol, type, period)` passed our **API's** period
vocabulary straight to vnstock. Our API says `"annual"`; vnstock 4.0.7 wants
`"year"`. It does not reject `"annual"` — it silently returns **quarterly**
data instead, and the column labels then collapse:

    period="annual"  ->  shape (25, 19), year columns ['2026'] x 16
    period="year"    ->  shape (25, 7),  year columns ['2025','2024','2023','2022']

`DataFrame.to_dict(orient="records")` keeps **one** value per duplicated key,
so sixteen quarterly columns became a single `'2026'`. For `ratio` every
column was labelled `'2018'`, so the served data was eight years stale.

Downstream: `ai-insights`' long-term recommender scores *consecutive years* of
P/E improvement and profit growth. Given one year it can score nothing, so it
returned `{"recommendations": []}` and the dashboard rendered N/A.

Nothing raised. The endpoint answered HTTP 200 with plausible JSON throughout.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from app.services import stock_service as svc_mod
from app.services.stock_service import StockService


def _service(captured: dict) -> StockService:
    """A service whose vnstock call records the period it was handed."""
    svc = StockService(MagicMock())

    def income_statement(period=None, lang=None):
        captured["period"] = period
        return pd.DataFrame({
            "item": ["Sales"], "item_en": ["Sales"], "item_id": ["sales"],
            "2025": [1.0], "2024": [2.0],
        })

    fake_finance = MagicMock()
    fake_finance.income_statement = income_statement
    fake_stock = MagicMock()
    fake_stock.finance = fake_finance
    fake_vnstock = MagicMock()
    fake_vnstock.stock.return_value = fake_stock
    return svc, fake_vnstock


def _patched(svc, fake_vnstock):
    return patch.object(type(svc), "vnstock",
                        new_callable=lambda: property(lambda self: fake_vnstock))


class TestPeriodTranslation:

    @pytest.mark.asyncio
    async def test_annual_is_translated_to_vnstocks_year(self):
        captured = {}
        svc, fv = _service(captured)
        with _patched(svc, fv):
            await svc.get_financial_statement("FPT", "income_statement", "annual")
        assert captured["period"] == "year", (
            "our API's 'annual' must be translated; vnstock silently returns "
            "QUARTERLY data for an unrecognised period"
        )

    @pytest.mark.asyncio
    async def test_quarter_passes_through_unchanged(self):
        captured = {}
        svc, fv = _service(captured)
        with _patched(svc, fv):
            await svc.get_financial_statement("FPT", "income_statement", "quarter")
        assert captured["period"] == "quarter"

    @pytest.mark.asyncio
    async def test_year_is_accepted_as_well_as_annual(self):
        captured = {}
        svc, fv = _service(captured)
        with _patched(svc, fv):
            await svc.get_financial_statement("FPT", "income_statement", "year")
        assert captured["period"] == "year"

    @pytest.mark.asyncio
    async def test_an_unknown_period_is_refused_rather_than_degraded(self):
        """The whole defect was a silent degradation, so an unrecognised
        period must not reach the vendor at all."""
        captured = {}
        svc, fv = _service(captured)
        with _patched(svc, fv):
            out = await svc.get_financial_statement("FPT", "income_statement", "yearly")
        assert out == []
        assert "period" not in captured, "an unknown period reached vnstock"

    @pytest.mark.asyncio
    async def test_multiple_year_columns_survive_to_the_records(self):
        """The point of the fix: more than one year must come back."""
        captured = {}
        svc, fv = _service(captured)
        with _patched(svc, fv):
            recs = await svc.get_financial_statement("FPT", "income_statement", "annual")
        assert recs
        years = sorted(k for k in recs[0] if str(k).isdigit())
        assert years == ["2024", "2025"]


class TestDuplicateColumnGuard:
    """The duplication is what made the bug invisible, so it gets its own
    alarm: `to_dict('records')` silently keeps one value per repeated key."""

    def _dup_service(self):
        svc = StockService(MagicMock())

        def income_statement(period=None, lang=None):
            df = pd.DataFrame([[1.0, 2.0, 3.0]], columns=["2026", "2026", "2026"])
            df.insert(0, "item", ["Sales"])
            return df

        fake_finance = MagicMock()
        fake_finance.income_statement = income_statement
        fake_stock = MagicMock()
        fake_stock.finance = fake_finance
        fv = MagicMock()
        fv.stock.return_value = fake_stock
        return svc, fv

    @pytest.mark.asyncio
    async def test_duplicate_columns_are_logged_loudly(self, caplog):
        svc, fv = self._dup_service()
        with _patched(svc, fv), caplog.at_level("WARNING"):
            await svc.get_financial_statement("FPT", "income_statement", "annual")
        assert any("duplicate" in r.message.lower() for r in caplog.records), (
            "a duplicated column label silently discards data and must warn"
        )

    @pytest.mark.asyncio
    async def test_duplicate_columns_do_not_silently_lose_every_value(self):
        svc, fv = self._dup_service()
        with _patched(svc, fv):
            recs = await svc.get_financial_statement("FPT", "income_statement", "annual")
        assert recs
        # three distinct values were present; at least two must survive
        values = [v for k, v in recs[0].items() if k != "item"]
        assert len(values) >= 2, f"columns collapsed to {recs[0]}"


class TestTheVocabularyIsDeclared:

    def test_the_map_is_explicit_and_covers_our_api_values(self):
        m = svc_mod.VNSTOCK_PERIODS
        assert m["annual"] == "year"
        assert m["quarter"] == "quarter"
