"""Tests for StockService.get_company_financials.

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
    """Mimic vnstock's flat-column ratio output with the metric names the
    code searches for (P/E, ROE (%), etc.). One row is enough — the
    method only reads iloc[0]."""
    return pd.DataFrame({
        "P/E": [15.0],
        "P/B": [2.3],
        "P/S": [1.1],
        "ROE (%)": [0.20],     # < 1 → will be x100
        "ROA (%)": [0.07],     # < 1 → x100
        "EPS (VND)": [3500.0],
        "BVPS (VND)": [25000.0],
        "Debt/Equity": [0.6],
        "Net Profit Margin (%)": [0.12],   # < 1 → x100
        "Market Capital (Bn. VND)": [200_000.0],
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
    assert out.eps == 3500.0
    assert out.book_value_per_share == 25000.0
    assert out.debt_to_equity == 0.6
    assert out.market_cap == 200_000.0
    # Nested mirror.
    assert out.financial_ratios is not None
    assert out.financial_ratios.pe == 15.0
    assert out.financial_ratios.roe == pytest.approx(20.0)


@pytest.mark.asyncio
async def test_ratio_block_skips_percent_conversion_when_already_percent_scaled():
    """ROE already > 1 (e.g. expressed as 22.5) is left alone."""
    ratio_df = pd.DataFrame({
        "P/E": [10.0],
        "ROE (%)": [22.5],  # > 1 → no conversion
        "ROA (%)": [8.0],   # > 1 → no conversion
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
    is_df = pd.DataFrame({
        "Revenue (Bn. VND)": [1000.0],
        "Attribute to parent company (Bn. VND)": [100.0],
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
async def test_income_statement_block_converts_yoy_to_percent_when_fractional():
    """A YoY value with abs < 10 is treated as a fraction (0.15 → 15%)."""
    is_df = pd.DataFrame({
        "Revenue (Bn. VND)": [1000.0],
        "Attribute to parent company (Bn. VND)": [120.0],
        "Revenue YoY (%)": [0.15],     # fractional → x100 → 15%
        "Attribute to parent company YoY (%)": [-0.08],  # → -8%
    })
    fake_stock = _build_fake_stock(is_df=is_df)
    svc = _make_service()
    with _patch_vnstock(svc, _vnstock_with(fake_stock)):
        out = await svc.get_company_financials("FPT")
    assert out.income_statement.revenue == 1000.0
    assert out.income_statement.netIncome == 120.0
    assert out.revenue_growth == pytest.approx(15.0)
    assert out.earnings_growth == pytest.approx(-8.0)
    assert out.growth_metrics.revenueGrowth == pytest.approx(15.0)


@pytest.mark.asyncio
async def test_income_statement_block_leaves_yoy_alone_when_already_percent():
    """abs >= 10 is treated as already a percent (e.g. 25.0 stays 25.0)."""
    is_df = pd.DataFrame({
        "Revenue (Bn. VND)": [1000.0],
        "Revenue YoY (%)": [25.0],  # already a percent
    })
    fake_stock = _build_fake_stock(is_df=is_df)
    svc = _make_service()
    with _patch_vnstock(svc, _vnstock_with(fake_stock)):
        out = await svc.get_company_financials("FPT")
    assert out.revenue_growth == 25.0


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
    bs_df = pd.DataFrame({
        "TOTAL ASSETS (Bn. VND)": [10_000.0],
        "Cash and cash equivalents (Bn. VND)": [500.0],
        "TOTAL EQUITY (Bn. VND)": [4_000.0],   # matches 'equity' + 'total' substrings
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
    """The fallback branch picks up 'OWNER EQUITY' columns (the bank case)."""
    bs_df = pd.DataFrame({
        "TOTAL ASSETS (Bn. VND)": [50_000.0],
        "Cash and cash equivalents (Bn. VND)": [2_000.0],
        "OWNER EQUITY (Bn. VND)": [3_500.0],
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
    bs_df = pd.DataFrame({
        "TOTAL ASSETS (Bn. VND)": [5_000.0],
        "Cash and cash equivalents (Bn. VND)": [100.0],
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
    cf_df = pd.DataFrame({
        "Net Cash Flows from Operating Activities before BIT": [800.0],
        "Net Cash Flows from Investing Activities": [-200.0],
        "Cash flows from financial activities": [-100.0],
        "Net increase/decrease in cash and cash equivalents": [500.0],
        "Purchase of fixed assets": [-150.0],  # negative outflow
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
    cf_df = pd.DataFrame({
        "Net Cash Flows from Operating Activities before BIT": [800.0],
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
    is_df = pd.DataFrame({
        "Revenue (Bn. VND)": [60_000.0],
        "Attribute to parent company (Bn. VND)": [8_000.0],
        "Revenue YoY (%)": [12.0],
    })
    bs_df = pd.DataFrame({
        "TOTAL ASSETS (Bn. VND)": [80_000.0],
        "Cash and cash equivalents (Bn. VND)": [5_000.0],
        "TOTAL EQUITY (Bn. VND)": [40_000.0],
    })
    cf_df = pd.DataFrame({
        "Net Cash Flows from Operating Activities before BIT": [9_000.0],
        "Net Cash Flows from Investing Activities": [-2_000.0],
        "Cash flows from financial activities": [-1_000.0],
        "Net increase/decrease in cash and cash equivalents": [6_000.0],
        "Purchase of fixed assets": [-1_500.0],
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
    assert out.revenue_growth == 12.0
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
