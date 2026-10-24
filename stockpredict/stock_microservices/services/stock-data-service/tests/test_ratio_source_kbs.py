"""Backlog #97 — the ratio fields were eight years stale.

`get_company_financials` read its ratio metrics from VCI, whose `ratio()` is
degenerate: `period="quarter"` returns columns labelled **2018-Q1..Q4** and
`period="year"` returns sixteen columns all labelled **2018** — and both
return the **same four numbers**. FPT's served `pe_ratio` was `11.6044`, one
of those values, while the company's actual FY2025 P/E is `15.91`.

So fifteen fields were present, plausible, and wrong — a harder failure to see
than a `None`, and the same shape as `#95` (the period vocabulary) and `#94`
(the swallowed `NameError`).

Why ANNUAL and not quarterly, decided by measurement rather than taste:

* KBS `period="year"` → `(58, 6)`, four distinct ordered years, sane values.
* KBS `period="quarter"` → columns `2026-Q2, 2025-Q4, 2026-Q1, 2025-Q4_1`:
  unordered, and FPT's `2025-Q4_1` column **duplicates 2026-Q2's values**
  (pe 15.53, pb 3.70, bvps 25141) rather than 2025-Q4's. Quarterly ROE also
  reads `5.89` against an annual `28.3`, i.e. un-annualised. Three different
  traps in one frame.

**What this does not fix, and says so in the response.** KBS annual
price-based ratios (P/E, P/B, P/S, EV/EBITDA, dividend yield) are priced at
**fiscal year end**, not today. Measured: deriving price as `BVPS x P/B` lands
within 2% for TCB and 6% for VNM but **68% out for FPT**, whose price fell
from ~96k to 57k during 2025. So `ratios_as_of` now travels with the numbers
instead of leaving consumers to assume they are current.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from app.services import stock_service as svc_mod
from app.services.stock_service import StockService


def _kbs_annual() -> pd.DataFrame:
    """The real KBS annual shape and real FPT FY2025 values."""
    rows = [
        ("pe_ratio", 15.91), ("pb_ratio", 3.73), ("ps_ratio", 2.33),
        ("roe", 28.3), ("roa", 11.71),
        ("gross_margin", 36.92), ("ebit_margin", 19.76), ("net_margin", 16.02),
        ("dividend_yield", 2.09), ("ev_ebitda", 10.8),
        ("short_term_ratio", 1.4), ("quick_ratio", 1.35),
        ("liabilities_to_equity", 101.48), ("debt_to_equity", 48.17),
        ("book_value_per_share_bvps", 25_679.55),
    ]
    return pd.DataFrame({
        "item": [r[0] for r in rows],
        "item_id": [r[0] for r in rows],
        "2025": [r[1] for r in rows],
        "2024": [r[1] * 0.9 for r in rows],
    })


class TestTheMapping:

    def test_plain_ratios_pass_through(self):
        m, _ = svc_mod.ratio_metrics_from_kbs(_kbs_annual())
        assert m["pe_ratio"] == pytest.approx(15.91)
        assert m["pb_ratio"] == pytest.approx(3.73)
        assert m["ps_ratio"] == pytest.approx(2.33)
        assert m["ev_ebitda"] == pytest.approx(10.8)

    def test_percent_fields_stay_percent(self):
        """The response already carries ROE and the margins as PERCENTS —
        VCI gave 0.2311 and the code multiplied by 100. KBS gives 28.3
        already, so it must NOT be multiplied again."""
        m, _ = svc_mod.ratio_metrics_from_kbs(_kbs_annual())
        assert m["roe"] == pytest.approx(28.3)
        assert m["roa"] == pytest.approx(11.71)
        assert m["gross_margin"] == pytest.approx(36.92)
        assert m["operating_margin"] == pytest.approx(19.76)
        assert m["profit_margin"] == pytest.approx(16.02)
        assert m["dividend_yield"] == pytest.approx(2.09)

    def test_liquidity_ratios_are_multiples(self):
        m, _ = svc_mod.ratio_metrics_from_kbs(_kbs_annual())
        assert m["current_ratio"] == pytest.approx(1.4)
        assert m["quick_ratio"] == pytest.approx(1.35)

    def test_debt_to_equity_uses_total_liabilities_and_is_a_multiple(self):
        """Two traps at once.

        KBS offers `debt_to_equity` (48.17 — interest-bearing debt only) AND
        `liabilities_to_equity` (101.48 — total liabilities). VCI's field was
        TOTAL liabilities over equity, expressed as a MULTIPLE (0.7994), so
        the faithful analogue is `liabilities_to_equity / 100`. Taking KBS's
        same-named field would both change the definition and publish a
        percent as a multiple — 48.17x gearing.
        """
        m, _ = svc_mod.ratio_metrics_from_kbs(_kbs_annual())
        assert m["debt_to_equity"] == pytest.approx(1.0148)

    def test_the_period_is_reported(self):
        _, as_of = svc_mod.ratio_metrics_from_kbs(_kbs_annual())
        assert as_of == "2025"

    def test_the_newest_period_is_chosen_not_the_first_column(self):
        f = _kbs_annual()[["item", "item_id", "2024", "2025"]]
        m, as_of = svc_mod.ratio_metrics_from_kbs(f)
        assert as_of == "2025"
        assert m["pe_ratio"] == pytest.approx(15.91)

    def test_market_cap_is_not_claimed(self):
        """KBS's ratio sheet has no market cap, and VCI's was ~3x stale
        (26.57T against roughly 84T for FPT). Absent beats wrong."""
        m, _ = svc_mod.ratio_metrics_from_kbs(_kbs_annual())
        assert "market_cap" not in m


class TestRobustness:

    def test_a_frame_without_item_id_is_declined(self):
        f = pd.DataFrame({"item_en": ["P/E"], "2025": [8.76]})
        m, as_of = svc_mod.ratio_metrics_from_kbs(f)
        assert m == {} and as_of is None

    def test_empty_and_none_are_inert(self):
        assert svc_mod.ratio_metrics_from_kbs(None) == ({}, None)
        assert svc_mod.ratio_metrics_from_kbs(pd.DataFrame()) == ({}, None)

    def test_non_numeric_cells_are_skipped_not_coerced(self):
        f = _kbs_annual()
        f["2025"] = f["2025"].astype(object)
        f.loc[0, "2025"] = "n/a"
        m, _ = svc_mod.ratio_metrics_from_kbs(f)
        assert "pe_ratio" not in m
        assert m["roe"] == pytest.approx(28.3)

    def test_a_suffixed_duplicate_column_is_not_treated_as_a_period(self):
        """KBS's quarterly frame emits `2025-Q4_1`, which duplicates another
        quarter's values. Even in the annual path, a suffixed label must not
        be mistaken for a period."""
        f = _kbs_annual()
        f["2025_1"] = f["2025"]
        _, as_of = svc_mod.ratio_metrics_from_kbs(f)
        assert as_of == "2025"


class TestWiredIntoTheResponse:

    def _service(self, kbs_frame):
        svc = StockService(MagicMock())

        def make_stock(symbol=None, source=None):
            fin = MagicMock()
            if source == "KBS":
                fin.ratio = lambda **kw: kbs_frame
            else:
                # VCI's degenerate frame: the stale 2018 values
                fin.ratio = lambda **kw: pd.DataFrame({
                    "item_en": ["P/E", "ROE (%)", "Market Cap"],
                    "item_id": ["pe_ratio", "roe", "market_cap"],
                    "2018-Q1": [8.7630467058, 0.2311204592, 26_566_905_346_800.0],
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
    async def test_the_response_carries_the_kbs_values_not_the_stale_ones(self):
        svc, fv = self._service(_kbs_annual())
        with patch.object(type(svc), "vnstock",
                          new_callable=lambda: property(lambda self: fv)):
            out = await svc.get_company_financials("FPT")
        assert out.pe_ratio == pytest.approx(15.91), "still serving VCI's stale 8.76"
        assert out.roe == pytest.approx(28.3)
        assert out.ratios_as_of == "2025"

    @pytest.mark.asyncio
    async def test_the_stale_market_cap_is_no_longer_published(self):
        svc, fv = self._service(_kbs_annual())
        with patch.object(type(svc), "vnstock",
                          new_callable=lambda: property(lambda self: fv)):
            out = await svc.get_company_financials("FPT")
        assert out.market_cap is None

    @pytest.mark.asyncio
    async def test_a_kbs_outage_leaves_the_fields_unset_rather_than_stale(self):
        """If KBS is unavailable the honest answer is None, not VCI's
        eight-year-old figure. A wrong number is worse than an absent one —
        the principle #76 was decided on."""
        svc = StockService(MagicMock())

        def make_stock(symbol=None, source=None):
            fin = MagicMock()
            if source == "KBS":
                def boom(**kw):
                    raise RuntimeError("KBS unavailable")
                fin.ratio = boom
            else:
                fin.ratio = lambda **kw: pd.DataFrame({
                    "item_en": ["P/E"], "item_id": ["pe_ratio"], "2018-Q1": [8.76],
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
        assert out.pe_ratio is None
        assert out.ratios_as_of is None
