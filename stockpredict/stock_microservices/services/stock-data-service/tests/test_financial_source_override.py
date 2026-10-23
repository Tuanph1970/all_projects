"""Backlog #95a — `ratio` comes from KBS, because VCI's is corrupted.

Measured on FPT, 2026-10-23:

    VCI  income_statement (25, 7)   4 clean years
    VCI  balance_sheet    (122, 7)  4 clean years
    VCI  cash_flow        (41, 7)   4 clean years
    VCI  ratio            (54, 19)  16 periods, ALL labelled 2018, values
                                    being 4 genuine periods repeated 4x
    KBS  ratio            (58, 6)   4 clean years — pe_ratio, roe, and
                                    book_value_per_share_bvps (see #76)
    KBS  balance_sheet    (0, 0)    EMPTY

So the fix is a **per-statement** source, not a wholesale switch: VCI for
everything except `ratio`, which uses KBS. A wholesale switch would silently
lose the balance sheet.

KBS also **rejects `lang`** (`Finance.ratio() got an unexpected keyword
argument 'lang'`), so the keyword set is per-source too. Losing `lang="en"`
costs only the English `item_en` label; `item_id` is the stable key and the one
consumers use.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from app.services import stock_service as svc_mod
from app.services.stock_service import StockService


def _service(calls: list):
    """Records (source, statement, kwargs) for each vnstock call."""
    svc = StockService(MagicMock())

    def make_stock(symbol=None, source=None):
        def statement(**kwargs):
            calls.append({"source": source, "kwargs": dict(kwargs)})
            if source == "KBS" and "lang" in kwargs:
                raise TypeError("Finance.ratio() got an unexpected keyword argument 'lang'")
            return pd.DataFrame({"item": ["P/E"], "item_id": ["pe_ratio"],
                                 "2025": [15.9], "2024": [26.7]})
        fin = MagicMock()
        for nm in ("income_statement", "balance_sheet", "cash_flow", "ratio"):
            setattr(fin, nm, statement)
        st = MagicMock()
        st.finance = fin
        return st

    fv = MagicMock()
    fv.stock.side_effect = make_stock
    return svc, fv


def _patched(svc, fv):
    return patch.object(type(svc), "vnstock",
                        new_callable=lambda: property(lambda self: fv))


class TestPerStatementSource:

    @pytest.mark.asyncio
    async def test_ratio_is_fetched_from_kbs(self):
        calls = []
        svc, fv = _service(calls)
        with _patched(svc, fv):
            await svc.get_financial_statement("FPT", "ratio", "annual")
        assert calls and calls[-1]["source"] == "KBS", (
            "VCI's ratio() is corrupted — 16 periods all labelled 2018"
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("stmt", ["income_statement", "balance_sheet", "cash_flow"])
    async def test_the_other_statements_keep_the_configured_source(self, stmt):
        """KBS's balance_sheet is EMPTY, so a wholesale switch would lose it."""
        calls = []
        svc, fv = _service(calls)
        with _patched(svc, fv):
            await svc.get_financial_statement("FPT", stmt, "annual")
        assert calls and calls[-1]["source"] != "KBS"

    def test_the_override_map_is_declared_with_only_ratio(self):
        assert svc_mod.FINANCIAL_SOURCE_OVERRIDES == {"ratio": "KBS"}


class TestPerSourceKeywords:

    @pytest.mark.asyncio
    async def test_lang_is_not_passed_to_kbs(self):
        """KBS raises TypeError on `lang`. The fake raises it too, so this
        test fails loudly if the keyword is sent."""
        calls = []
        svc, fv = _service(calls)
        with _patched(svc, fv):
            recs = await svc.get_financial_statement("FPT", "ratio", "annual")
        assert "lang" not in calls[-1]["kwargs"]
        assert recs, "the KBS call raised, so no records came back"

    @pytest.mark.asyncio
    async def test_lang_is_still_passed_to_vci(self):
        calls = []
        svc, fv = _service(calls)
        with _patched(svc, fv):
            await svc.get_financial_statement("FPT", "income_statement", "annual")
        assert calls[-1]["kwargs"].get("lang") == "en"

    @pytest.mark.asyncio
    async def test_the_period_translation_still_applies_to_the_override(self):
        """#95a must not undo the #95 period fix."""
        calls = []
        svc, fv = _service(calls)
        with _patched(svc, fv):
            await svc.get_financial_statement("FPT", "ratio", "annual")
        assert calls[-1]["kwargs"]["period"] == "year"
