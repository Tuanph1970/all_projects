"""Tests for StockService.get_company_financials.

**Fixture format (Backlog #47).** These fixtures are vnstock **4.x long
format**: metric names live in the values of an ``item_en`` column and each
reporting period is its own column (``2026-Q1``, ``2025-Q1``, ...). They were
3.x *wide* format — one row, metrics as column names — until 2026-10-13, which
is why all eleven of them failed from commit 567cd1bc onward:
``_latest_metrics`` returns ``{}`` the moment ``item_en`` is absent, so every
field read ``None`` and the tests asserted against a method that could not
work.

The format and the metric names are not taken from the code under test, which
would be circular. They come from 567cd1bc's own message — which records the
transposition and says it was verified against VNM/FPT/HPG/TCB — and were
re-confirmed live on 2026-10-13 through
``GET /companies/{symbol}/financials``, where FPT returns pe=11.60, pb=2.44,
roe=18.71, roa=9.57 from real vendor data.

This is the largest single method in stock_service.py (~195 stmts of
multi-level DataFrame mining across 4 vnstock finance endpoints:
ratio, income_statement, balance_sheet, cash_flow). Each block is
wrapped in its own try/except so a single vendor failure leaves the
rest of the response populated. The tests exercise:

- Full happy path: all four DataFrames populated, response carries
  both flat fields and the four nested data sections.
- Each block's exception swallow (4 independent tests).
- Conversions: ROE/ROA/NPM < 1 multiplied by 100; YoY < 10 absolute
  multiplied by 100; total_liabilities derived from assets - equity;
  free_cash_flow derived from operating + capex (capex negative).
- Equity column fallback path: "owner equity" branch when no
  "Total equity" column is present.
- Empty DataFrames: each block skips cleanly without poisoning the
  response.
- Outer try/except: vnstock.stock() raising returns None.
- Company name fallback: listing.all_symbols failing falls back to
  the symbol itself.
"""
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from app.services.stock_service import StockService


#: The period labels the production code parses (`_period_columns` accepts
#: YYYY-Qn and YYYY, newest first).
LATEST_PERIOD = "2026-Q1"
PRIOR_YEAR_PERIOD = "2025-Q1"


def _long(metrics: dict, prior: dict = None) -> pd.DataFrame:
    """Build a vnstock 4.x long-format statement.

    ``metrics`` maps an ``item_en`` metric name to its value in the latest
    period. ``prior`` optionally supplies the same-quarter-last-year column,
    which is what `_yoy` needs to compute growth — in 4.x growth is DERIVED
    from two period columns, not read from a "... YoY (%)" column the way 3.x
    reported it.
    """
    rows = {"item_en": list(metrics), LATEST_PERIOD: list(metrics.values())}
    if prior is not None:
        rows[PRIOR_YEAR_PERIOD] = [prior.get(k) for k in metrics]
    return pd.DataFrame(rows)


def _make_service(repo=None) -> StockService:
    return StockService(repo if repo is not None else MagicMock())


def _patch_vnstock(svc: StockService, fake_vnstock):
    return patch.object(
        type(svc),
        "vnstock",
        new_callable=lambda: property(lambda self: fake_vnstock),
    )


def _build_fake_stock(
    *,
    ratio_df=None,
    is_df=None,
    bs_df=None,
    cf_df=None,
    symbols_df=None,
    ratio_raises: BaseException = None,
    is_raises: BaseException = None,
    bs_raises: BaseException = None,
    cf_raises: BaseException = None,
    symbols_raises: BaseException = None,
):
    """Build a fake vnstock client whose finance.* and listing methods
    return the canned DataFrames (or raise the canned exceptions)."""
    fake_stock = MagicMock()

    if symbols_raises is not None:
        fake_stock.listing.all_symbols.side_effect = symbols_raises
    else:
        fake_stock.listing.all_symbols.return_value = symbols_df if symbols_df is not None else pd.DataFrame()

    if ratio_raises is not None:
        fake_stock.finance.ratio.side_effect = ratio_raises
    else:
        fake_stock.finance.ratio.return_value = ratio_df if ratio_df is not None else pd.DataFrame()

    if is_raises is not None:
        fake_stock.finance.income_statement.side_effect = is_raises
    else:
        fake_stock.finance.income_statement.return_value = is_df if is_df is not None else pd.DataFrame()

    if bs_raises is not None:
        fake_stock.finance.balance_sheet.side_effect = bs_raises
    else:
        fake_stock.finance.balance_sheet.return_value = bs_df if bs_df is not None else pd.DataFrame()

    if cf_raises is not None:
        fake_stock.finance.cash_flow.side_effect = cf_raises
    else:
        fake_stock.finance.cash_flow.return_value = cf_df if cf_df is not None else pd.DataFrame()

    return fake_stock


def _vnstock_with(fake_stock) -> MagicMock:
    v = MagicMock()
    v.stock.return_value = fake_stock
    return v


# ---------------------------------------------------------------------------
# Outer try/except — vnstock client construction failure
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_company_financials_returns_none_when_vnstock_explodes():
    fake_vnstock = MagicMock()
    fake_vnstock.stock.side_effect = RuntimeError("vnstock unreachable")
    svc = _make_service()
    with _patch_vnstock(svc, fake_vnstock):
        out = await svc.get_company_financials("FPT")
    assert out is None


# ---------------------------------------------------------------------------
# Company name lookup — graceful fallback to the symbol itself
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_company_name_falls_back_to_symbol_when_lookup_raises():
    fake_stock = _build_fake_stock(symbols_raises=RuntimeError("listing down"))
    svc = _make_service()
    with _patch_vnstock(svc, _vnstock_with(fake_stock)):
        out = await svc.get_company_financials("fpt")
    assert out is not None
    assert out.symbol == "FPT"
    assert out.company_name == "FPT"  # symbol-only fallback


@pytest.mark.asyncio
async def test_company_name_uses_listing_when_available():
    symbols_df = pd.DataFrame({"symbol": ["FPT"], "organ_name": ["FPT Corp"]})
    fake_stock = _build_fake_stock(symbols_df=symbols_df)
    svc = _make_service()
    with _patch_vnstock(svc, _vnstock_with(fake_stock)):
        out = await svc.get_company_financials("FPT")
    assert out.company_name == "FPT Corp"


# ---------------------------------------------------------------------------
# Ratio block
# ---------------------------------------------------------------------------

def _ratio_df_basic():
    """vnstock 4.x ratio output, using the metric names the code picks.

    Note what moved between versions besides the shape: 3.x "Debt/Equity"
    is 4.x "Debt to Equity", "Net Profit Margin (%)" is "After-tax Profit
    Margin (%)", and "Market Capital (Bn. VND)" is "Market Cap". EPS now
    comes from the income statement rather than the ratio sheet.
    """
    return _long({
        "P/E": 15.0,
        "P/B": 2.3,
        "P/S": 1.1,
        "ROE (%)": 0.20,                      # < 1 -> x100 by _as_percent
        "ROA (%)": 0.07,                      # < 1 -> x100
        "Debt to Equity": 0.6,
        "Current Ratio": 1.8,
        "Quick Ratio": 1.4,
        "Gross Margin (%)": 0.35,
        "EBIT Margin (%)": 0.18,
        "After-tax Profit Margin (%)": 0.12,  # < 1 -> x100
        "EV/EBITDA": 9.5,
        "Dividend Yield (%)": 0.02,
        "Market Cap": 200_000.0,
    })


@pytest.mark.asyncio
async def test_ratio_block_populates_flat_and_nested_fields_with_percent_conversion():
    fake_stock = _build_fake_stock(ratio_df=_ratio_df_basic())
    svc = _make_service()
    with _patch_vnstock(svc, _vnstock_with(fake_stock)):
        out = await svc.get_company_financials("FPT")
    assert out.pe_ratio == 15.0
    assert out.pb_ratio == 2.3
    # Percent conversion: 0.20 → 20.0
    assert out.roe == pytest.approx(20.0)
    assert out.roa == pytest.approx(7.0)
    assert out.profit_margin == pytest.approx(12.0)
    assert out.debt_to_equity == 0.6
    assert out.market_cap == 200_000.0
    assert out.current_ratio == 1.8
    assert out.ev_ebitda == 9.5
    # eps now comes from the income statement, not the ratio sheet, so this
    # ratio-only fixture leaves it unset. book_value_per_share is unset for a
    # different and less innocent reason — see
    # TestFieldsTheFourXAdaptationDropped at the end of this module.
    assert out.eps is None
    # Nested mirror.
    assert out.financial_ratios is not None
    assert out.financial_ratios.pe == 15.0
    assert out.financial_ratios.roe == pytest.approx(20.0)


@pytest.mark.asyncio
async def test_ratio_block_skips_percent_conversion_when_already_percent_scaled():
    """ROE already > 1 (e.g. expressed as 22.5) is left alone."""
    ratio_df = _long({
        "P/E": 10.0,
        "ROE (%)": 22.5,  # > 1 -> no conversion
        "ROA (%)": 8.0,   # > 1 -> no conversion
    })
    fake_stock = _build_fake_stock(ratio_df=ratio_df)
    svc = _make_service()
    with _patch_vnstock(svc, _vnstock_with(fake_stock)):
        out = await svc.get_company_financials("FPT")
    assert out.roe == 22.5
    assert out.roa == 8.0


@pytest.mark.asyncio
async def test_ratio_block_exception_is_swallowed_and_other_blocks_still_run():
    """ratio() raising should not skip income_statement / balance_sheet / cash_flow."""
    is_df = _long({
        "Net sales": 1000.0,
        "Attributable to parent company": 100.0,
    })
    fake_stock = _build_fake_stock(
        ratio_raises=RuntimeError("ratio API down"),
        is_df=is_df,
    )
    svc = _make_service()
    with _patch_vnstock(svc, _vnstock_with(fake_stock)):
        out = await svc.get_company_financials("FPT")
    assert out is not None
    assert out.pe_ratio is None   # ratio block left defaults in place
    assert out.income_statement.revenue == 1000.0  # income block still populated


# ---------------------------------------------------------------------------
# Income statement block
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_income_statement_block_derives_yoy_growth_from_two_periods():
    """Growth is COMPUTED, not reported.

    3.x shipped a "Revenue YoY (%)" column and the old code scaled it. 4.x
    ships no such column: `_yoy` takes the latest period and the same quarter
    a year earlier and returns `(cur - prev) / abs(prev) * 100`. So the test
    supplies both columns and checks the arithmetic.
    """
    is_df = _long(
        {"Net sales": 1150.0, "Attributable to parent company": 92.0},
        prior={"Net sales": 1000.0, "Attributable to parent company": 100.0},
    )
    fake_stock = _build_fake_stock(is_df=is_df)
    svc = _make_service()
    with _patch_vnstock(svc, _vnstock_with(fake_stock)):
        out = await svc.get_company_financials("FPT")
    assert out.income_statement.revenue == 1150.0
    assert out.income_statement.netIncome == 92.0
    assert out.revenue_growth == pytest.approx(15.0)    # 1150 vs 1000
    assert out.earnings_growth == pytest.approx(-8.0)   # 92 vs 100
    assert out.growth_metrics.revenueGrowth == pytest.approx(15.0)


@pytest.mark.asyncio
async def test_no_prior_year_column_means_no_growth_rather_than_a_wrong_one():
    """With only the latest period, growth is unknowable.

    This is the live situation (Backlog #76): on FPT/TCB/VNM the vendor
    response carries no same-quarter-prior-year column, so `revenue_growth`
    and `earnings_growth` come back None in production. Reporting 0% or
    guessing would be worse than reporting nothing.
    """
    is_df = _long({"Net sales": 1000.0})
    fake_stock = _build_fake_stock(is_df=is_df)
    svc = _make_service()
    with _patch_vnstock(svc, _vnstock_with(fake_stock)):
        out = await svc.get_company_financials("FPT")
    assert out.income_statement.revenue == 1000.0
    assert out.revenue_growth is None
    assert out.earnings_growth is None


@pytest.mark.asyncio
async def test_income_statement_block_exception_swallowed():
    fake_stock = _build_fake_stock(is_raises=RuntimeError("IS API down"))
    svc = _make_service()
    with _patch_vnstock(svc, _vnstock_with(fake_stock)):
        out = await svc.get_company_financials("FPT")
    assert out is not None
    assert out.income_statement.revenue is None  # default
    assert out.revenue_growth is None


# ---------------------------------------------------------------------------
# Balance sheet block — equity discovery + derived liabilities
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_balance_sheet_derives_liabilities_from_assets_minus_equity():
    """Total liabilities is computed: assets - equity."""
    # No "Liabilities" row, so the code must derive assets - equity.
    bs_df = _long({
        "Total Assets": 10_000.0,
        "Cash and cash equivalents": 500.0,
        "Total Equity": 4_000.0,
    })
    fake_stock = _build_fake_stock(bs_df=bs_df)
    svc = _make_service()
    with _patch_vnstock(svc, _vnstock_with(fake_stock)):
        out = await svc.get_company_financials("FPT")
    assert out.balance_sheet.totalAssets == 10_000.0
    assert out.balance_sheet.totalEquity == 4_000.0
    assert out.balance_sheet.cash == 500.0
    # Derived: 10_000 - 4_000.
    assert out.balance_sheet.totalLiabilities == 6_000.0


@pytest.mark.asyncio
async def test_balance_sheet_uses_owner_equity_branch_when_no_total_equity_column():
    """The fallback picks up "Owner's Equity" (the bank case).

    4.x lists that name FIRST in `_pick`, so this is the common path for banks
    rather than an exotic fallback.
    """
    bs_df = _long({
        "TOTAL ASSETS": 50_000.0,          # the all-caps variant _pick also accepts
        "Cash and cash equivalents": 2_000.0,
        "Owner's Equity": 3_500.0,
    })
    fake_stock = _build_fake_stock(bs_df=bs_df)
    svc = _make_service()
    with _patch_vnstock(svc, _vnstock_with(fake_stock)):
        out = await svc.get_company_financials("FPT")
    assert out.balance_sheet.totalEquity == 3_500.0
    assert out.balance_sheet.totalLiabilities == pytest.approx(46_500.0)


@pytest.mark.asyncio
async def test_balance_sheet_leaves_liabilities_none_when_equity_absent():
    """No equity column means no liabilities derivation; assets still set."""
    bs_df = _long({
        "Total Assets": 5_000.0,
        "Cash and cash equivalents": 100.0,
    })
    fake_stock = _build_fake_stock(bs_df=bs_df)
    svc = _make_service()
    with _patch_vnstock(svc, _vnstock_with(fake_stock)):
        out = await svc.get_company_financials("FPT")
    assert out.balance_sheet.totalAssets == 5_000.0
    assert out.balance_sheet.totalEquity is None
    assert out.balance_sheet.totalLiabilities is None


@pytest.mark.asyncio
async def test_balance_sheet_block_exception_swallowed():
    fake_stock = _build_fake_stock(bs_raises=RuntimeError("BS API down"))
    svc = _make_service()
    with _patch_vnstock(svc, _vnstock_with(fake_stock)):
        out = await svc.get_company_financials("FPT")
    assert out is not None
    assert out.balance_sheet.totalAssets is None


# ---------------------------------------------------------------------------
# Cash flow block — free cash flow derivation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cash_flow_block_derives_free_cash_flow():
    """Free CF = operating + capex; capex is reported negative so the
    addition is the right operation."""
    cf_df = _long({
        "Net cash inflows/(outflows) from operating activities": 800.0,
        "Net cash inflows/(outflows) from investing activities": -200.0,
        "Net cash inflows/(outflows) from financing activities": -100.0,
        "Net increase/decrease in cash and cash equivalents": 500.0,
        "Purchases of fixed assets and other long term assets": -150.0,  # outflow
    })
    fake_stock = _build_fake_stock(cf_df=cf_df)
    svc = _make_service()
    with _patch_vnstock(svc, _vnstock_with(fake_stock)):
        out = await svc.get_company_financials("FPT")
    assert out.cash_flow.operatingCashFlow == 800.0
    assert out.cash_flow.investingCashFlow == -200.0
    assert out.cash_flow.financingCashFlow == -100.0
    assert out.cash_flow.netCashFlow == 500.0
    # 800 + (-150) = 650.
    assert out.cash_flow.freeCashFlow == pytest.approx(650.0)


@pytest.mark.asyncio
async def test_cash_flow_block_skips_free_cash_flow_when_capex_missing():
    cf_df = _long({
        "Net cash inflows/(outflows) from operating activities": 800.0,
    })
    fake_stock = _build_fake_stock(cf_df=cf_df)
    svc = _make_service()
    with _patch_vnstock(svc, _vnstock_with(fake_stock)):
        out = await svc.get_company_financials("FPT")
    assert out.cash_flow.operatingCashFlow == 800.0
    assert out.cash_flow.freeCashFlow is None


@pytest.mark.asyncio
async def test_cash_flow_block_exception_swallowed():
    fake_stock = _build_fake_stock(cf_raises=RuntimeError("CF API down"))
    svc = _make_service()
    with _patch_vnstock(svc, _vnstock_with(fake_stock)):
        out = await svc.get_company_financials("FPT")
    assert out is not None
    assert out.cash_flow.operatingCashFlow is None


# ---------------------------------------------------------------------------
# Full happy path — all four blocks populated
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_full_happy_path_returns_all_sections():
    """All four DataFrames populated → flat fields + four nested sections set."""
    symbols_df = pd.DataFrame({"symbol": ["VNM"], "organ_name": ["Vinamilk"]})
    ratio_df = _ratio_df_basic()
    is_df = _long(
        {
            "Net sales": 60_000.0,
            "Attributable to parent company": 8_000.0,
            "EPS basic (VND)": 3_500.0,
        },
        # A prior-year column so growth is exercised on the happy path too.
        prior={"Net sales": 53_571.43, "Attributable to parent company": 7_000.0},
    )
    bs_df = _long({
        "Total Assets": 80_000.0,
        "Cash and cash equivalents": 5_000.0,
        "Total Equity": 40_000.0,
    })
    cf_df = _long({
        "Net cash inflows/(outflows) from operating activities": 9_000.0,
        "Net cash inflows/(outflows) from investing activities": -2_000.0,
        "Net cash inflows/(outflows) from financing activities": -1_000.0,
        "Net increase/decrease in cash and cash equivalents": 6_000.0,
        "Purchases of fixed assets and other long term assets": -1_500.0,
    })

    fake_stock = _build_fake_stock(
        symbols_df=symbols_df,
        ratio_df=ratio_df,
        is_df=is_df,
        bs_df=bs_df,
        cf_df=cf_df,
    )
    svc = _make_service()
    with _patch_vnstock(svc, _vnstock_with(fake_stock)):
        out = await svc.get_company_financials("vnm")
    # Top-level
    assert out.symbol == "VNM"
    assert out.company_name == "Vinamilk"
    assert out.pe_ratio == 15.0
    assert out.roe == pytest.approx(20.0)
    # Income
    assert out.income_statement.revenue == 60_000.0
    assert out.income_statement.netIncome == 8_000.0
    assert out.eps == 3_500.0
    assert out.revenue_growth == pytest.approx(12.0, abs=0.01)   # derived
    # Balance sheet derived liabilities
    assert out.balance_sheet.totalLiabilities == 40_000.0
    # Cash flow derived free CF
    assert out.cash_flow.freeCashFlow == pytest.approx(7_500.0)


@pytest.mark.asyncio
async def test_all_empty_dataframes_still_returns_valid_response():
    """When every vnstock endpoint returns an empty DataFrame, we still
    get a valid response with the symbol populated and all blocks at
    their default None values."""
    fake_stock = _build_fake_stock()
    svc = _make_service()
    with _patch_vnstock(svc, _vnstock_with(fake_stock)):
        out = await svc.get_company_financials("FPT")
    assert out is not None
    assert out.symbol == "FPT"
    assert out.pe_ratio is None
    assert out.financial_ratios is not None
    assert out.balance_sheet.totalAssets is None
    assert out.cash_flow.operatingCashFlow is None


# ---------------------------------------------------------------------------
# Fields the 4.x adaptation stopped populating (Backlog #76)
# ---------------------------------------------------------------------------

class TestFieldsRestoredFromBacklog76:
    """`debt_to_assets` and `enterprise_value`, restored 2026-10-14.

    Both were derivable from values already in hand, so the 4.x rewrite had
    simply stopped assigning them. They were `xfail(strict=True)` until the
    derivations landed, at which point the markers had to come off — which is
    what strict xfail is for.
    """

    @staticmethod
    def _fixture(**over):
        bs = {
            "Total Assets": 80_000.0,
            "Cash and cash equivalents": 5_000.0,
            "Total Equity": 40_000.0,
            "Liabilities": 35_000.0,
            "Long-term liabilities": 12_000.0,
        }
        bs.update(over.pop("bs", {}))
        return _build_fake_stock(ratio_df=_ratio_df_basic(), bs_df=_long(bs), **over)

    @pytest.mark.asyncio
    async def test_debt_to_assets_is_a_ratio_derived_from_the_balance_sheet(self):
        svc = _make_service()
        with _patch_vnstock(svc, _vnstock_with(self._fixture())):
            out = await svc.get_company_financials("FPT")
        # 35,000 / 80,000. A ratio, matching debt_to_equity's units rather than
        # a percentage.
        assert out.debt_to_assets == pytest.approx(0.4375)

    @pytest.mark.asyncio
    async def test_enterprise_value_is_market_cap_plus_debt_less_cash(self):
        svc = _make_service()
        with _patch_vnstock(svc, _vnstock_with(self._fixture())):
            out = await svc.get_company_financials("FPT")
        # 200,000 + 12,000 - 5,000. Only LONG-TERM liabilities are available,
        # so this is a lower bound on EV — stated in the code comment too.
        assert out.enterprise_value == pytest.approx(207_000.0)

    @pytest.mark.asyncio
    async def test_neither_is_fabricated_when_the_balance_sheet_is_thin(self):
        """The bank case, and the reason it matters.

        Live, TCB returns a balance sheet with `totalAssets` only — equity,
        cash, liabilities and long-term debt are all None, because bank line
        names differ from the ones `_pick` knows (Backlog #77). Both
        derivations must then yield None rather than treating a missing term as
        zero, which would report an enterprise value equal to market cap and a
        debt ratio of zero for every bank.
        """
        svc = _make_service()
        thin = _build_fake_stock(
            ratio_df=_ratio_df_basic(),
            bs_df=_long({"Total Assets": 1_273_076.0}),
        )
        with _patch_vnstock(svc, _vnstock_with(thin)):
            out = await svc.get_company_financials("TCB")
        assert out.balance_sheet.totalAssets == 1_273_076.0
        assert out.debt_to_assets is None
        assert out.enterprise_value is None


class TestFieldsTheFourXAdaptationDropped:
    """`book_value_per_share` is still never set, and now we know why.

    Found while migrating these fixtures: because all eleven tests in this
    module were red from 567cd1bc onward, the one test that asserted
    `book_value_per_share` was red too — so the field going away was invisible.
    That is the cost of a red suite, concretely.

    It is a REGRESSION relative to pre-567cd1bc, which read it straight from
    the ratio sheet as `BVPS (VND)`. But it cannot be restored the same way:
    probed live on 2026-10-14 against FPT, VNM and TCB under five candidate
    names — `BVPS (VND)`, `BVPS`, `Book value per share`,
    `Book Value Per Share (VND)`, `Book value per share (VND)` — and vnstock
    4.x supplies none of them.

    Nor is it safely derivable from what is in hand. `(pe x eps) / pb` is the
    obvious algebra and is wrong here: `eps` is quarterly while P/E is
    trailing, so the implied price is out by roughly a factor of four. A wrong
    book value is worse than an absent one, so this stays unset until there is
    a shares-outstanding figure or a price feed to divide by.

    Kept as `xfail(strict=True)` so the debt stays visible: the moment a real
    source appears the test passes, strict turns that into a failure, and the
    marker must come off.

    `debt_to_assets` and `enterprise_value` WERE here and have been restored —
    see TestFieldsRestoredFromBacklog76 above.

    `revenue_growth` / `earnings_growth` are deliberately NOT here. They are
    also always `None` live, but for a legitimate reason — the vendor response
    carries no same-quarter-prior-year column, so growth is genuinely unknown.
    `test_no_prior_year_column_means_no_growth_rather_than_a_wrong_one` asserts
    that correct behaviour instead.
    """

    @staticmethod
    def _full_fixture():
        return _build_fake_stock(
            ratio_df=_ratio_df_basic(),
            is_df=_long({"Net sales": 60_000.0, "EPS basic (VND)": 3_500.0}),
            bs_df=_long({
                "Total Assets": 80_000.0,
                "Cash and cash equivalents": 5_000.0,
                "Total Equity": 40_000.0,
                "Long-term liabilities": 12_000.0,
            }),
        )

    @pytest.mark.asyncio
    @pytest.mark.xfail(strict=True, reason="Backlog #76: vnstock 4.x supplies no BVPS field; needs shares outstanding or a price feed")
    async def test_book_value_per_share_is_populated(self):
        svc = _make_service()
        with _patch_vnstock(svc, _vnstock_with(self._full_fixture())):
            out = await svc.get_company_financials("FPT")
        assert out.book_value_per_share is not None
