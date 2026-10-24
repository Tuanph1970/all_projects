"""Backlog #76 — `book_value_per_share`, finally obtainable.

The field has been `None` since the 4.x rewrite. The previous investigation
did the right thing: it probed VCI live under five candidate names
(`BVPS (VND)`, `BVPS`, `Book value per share`, …), found none, and **refused
to derive it** from `(pe x eps) / pb` — `eps` is quarterly while `P/E` is
trailing, so the implied price and the BVPS falling out of it would be wrong
by roughly 4x, and a wrong book value is worse than an absent one.

What changed is the *source*, not the arithmetic. Backlog `#95a` moved the
financial-statement `ratio` call to **KBS** because VCI's is corrupted, and
the KBS ratio sheet carries **`book_value_per_share_bvps`** directly — no
derivation needed. Verified live for FPT at both `period="year"` and
`period="quarter"`.

Scope, deliberately narrow: this adds the one field `#76` asks for. The
existing ratio fields keep reading VCI, because re-sourcing them all means
changing `_latest_metrics` (which keys off `item_en`, absent from KBS), unit
handling (VCI reports ROE as a fraction, KBS as a percent) and period
semantics — with fifteen working fields at risk. That is logged separately
rather than smuggled in here.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from app.services import stock_service as svc_mod
from app.services.stock_service import StockService


def _kbs_ratio_frame(bvps=28_450.0):
    """The KBS shape: item / item_id, years as columns, no `item_en`."""
    return pd.DataFrame({
        "item": ["P/E", "ROE (%)", "BVPS"],
        "item_id": ["pe_ratio", "roe", "book_value_per_share_bvps"],
        "2025": [15.91, 28.3, bvps],
        "2024": [26.74, 28.69, bvps - 5000],
    })


class TestTheKbsLookup:

    def test_bvps_is_read_from_the_kbs_item_id(self):
        out = svc_mod.bvps_from_ratio_frame(_kbs_ratio_frame())
        assert out == pytest.approx(28_450.0)

    def test_the_latest_period_is_used(self):
        """Columns are newest-first in the KBS annual frame, and the helper
        must not quietly take an older year."""
        f = _kbs_ratio_frame()
        assert svc_mod.bvps_from_ratio_frame(f) == pytest.approx(f["2025"].iloc[2])

    def test_a_frame_without_the_id_yields_none(self):
        f = _kbs_ratio_frame().drop(index=2)
        assert svc_mod.bvps_from_ratio_frame(f) is None

    def test_a_frame_without_item_id_yields_none(self):
        """VCI's frame has `item_en` but no usable BVPS id; it must not crash."""
        f = pd.DataFrame({"item_en": ["P/E"], "2025": [8.76]})
        assert svc_mod.bvps_from_ratio_frame(f) is None

    def test_empty_and_none_are_inert(self):
        assert svc_mod.bvps_from_ratio_frame(None) is None
        assert svc_mod.bvps_from_ratio_frame(pd.DataFrame()) is None

    def test_a_non_numeric_cell_is_declined_not_coerced(self):
        # object dtype on purpose: assigning a string into a float column
        # raises a pandas FutureWarning and would be coerced in a later
        # version, which would quietly change what this test exercises.
        f = _kbs_ratio_frame()
        f["2025"] = f["2025"].astype(object)
        f.loc[2, "2025"] = "n/a"
        assert svc_mod.bvps_from_ratio_frame(f) is None

    def test_a_non_positive_book_value_is_declined(self):
        """A book value of zero or less is not a book value — and publishing a
        wrong one is what the original investigation refused to do."""
        assert svc_mod.bvps_from_ratio_frame(_kbs_ratio_frame(bvps=0.0)) is None
        assert svc_mod.bvps_from_ratio_frame(_kbs_ratio_frame(bvps=-12.0)) is None


class TestItIsWiredIntoTheResponse:

    def _service(self, kbs_frame):
        svc = StockService(MagicMock())

        def make_stock(symbol=None, source=None):
            fin = MagicMock()
            if source == "KBS":
                fin.ratio = lambda **kw: kbs_frame
            else:
                # VCI: the existing shape, with no BVPS under any name
                fin.ratio = lambda **kw: pd.DataFrame({
                    "item_en": ["P/E", "ROE (%)"], "item_id": ["pe_ratio", "roe"],
                    "2025-Q4": [8.76, 0.2311],
                })
                for nm in ("income_statement", "balance_sheet", "cash_flow"):
                    setattr(fin, nm, lambda **kw: pd.DataFrame())
            st = MagicMock()
            st.finance = fin
            st.listing.all_symbols = lambda: pd.DataFrame()
            st.company.overview = lambda: pd.DataFrame()
            return st

        fv = MagicMock()
        fv.stock.side_effect = make_stock
        return svc, fv

    @pytest.mark.asyncio
    async def test_the_response_carries_book_value_per_share(self):
        svc, fv = self._service(_kbs_ratio_frame())
        with patch.object(type(svc), "vnstock",
                          new_callable=lambda: property(lambda self: fv)):
            out = await svc.get_company_financials("FPT")
        assert out is not None
        assert out.book_value_per_share == pytest.approx(28_450.0)

    @pytest.mark.asyncio
    async def test_a_kbs_outage_does_not_fail_the_whole_response(self):
        """The supplementary call is best-effort: BVPS is one field, and
        losing the vendor for it must not take the other fifteen with it."""
        svc = StockService(MagicMock())

        def make_stock(symbol=None, source=None):
            fin = MagicMock()
            if source == "KBS":
                def boom(**kw):
                    raise RuntimeError("KBS unavailable")
                fin.ratio = boom
            else:
                fin.ratio = lambda **kw: pd.DataFrame({
                    "item_en": ["P/E"], "item_id": ["pe_ratio"], "2025-Q4": [8.76],
                })
                for nm in ("income_statement", "balance_sheet", "cash_flow"):
                    setattr(fin, nm, lambda **kw: pd.DataFrame())
            st = MagicMock()
            st.finance = fin
            st.listing.all_symbols = lambda: pd.DataFrame()
            st.company.overview = lambda: pd.DataFrame()
            return st

        fv = MagicMock()
        fv.stock.side_effect = make_stock
        with patch.object(type(svc), "vnstock",
                          new_callable=lambda: property(lambda self: fv)):
            out = await svc.get_company_financials("FPT")
        assert out is not None
        assert out.book_value_per_share is None
        # Backlog #97: VCI's ratio values are NOT a fallback. They were eight
        # years stale (this 8.76 is one of them), so when KBS is unavailable
        # the ratio fields stay unset rather than serving a stale number —
        # the principle #76 was decided on, applied to the other fifteen
        # fields as well.
        assert out.pe_ratio is None
        assert out.ratios_as_of is None
