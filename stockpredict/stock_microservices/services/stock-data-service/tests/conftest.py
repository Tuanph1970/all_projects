"""
Test Configuration and Fixtures for Stock Data Service
"""
import sys
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, date

# Mock vnstock3 before importing app modules
sys.modules['vnstock3'] = MagicMock()

# Unit tests never hit the network: disable the vnai-quota spacing that
# StockService.vnstock_call() applies between vnstock calls (default 3.1s).
import os
os.environ.setdefault("VNSTOCK_MIN_INTERVAL_SECONDS", "0")
os.environ.setdefault("VNSTOCK_RATE_LIMIT_RETRY", "false")

from app.main import app
from app.api.dependencies import get_db, get_stock_service
from app.models.schemas import (
    CompanyResponse, CompanyDetailResponse, HistoricalDataResponse,
    TopMoverResponse, SearchResult, MarketIndexResponse, IndustryResponse,
    StockPriceResponse
)


@pytest.fixture(autouse=True)
def _clear_components_cache():
    """Reset the StockComponents cache around every test (Backlog #144).

    It is module-level process state, so without this the first test to build a
    component hands its mock to every later test for the same (symbol, source)
    and their own mocks are never consulted. That is exactly how it failed when
    the cache was introduced: one test passed and the next five did not, with
    assertion errors that pointed at period translation rather than at shared
    state. Autouse, because remembering to ask for it is the failure mode.
    """
    from app.services.stock_service import clear_components_cache
    clear_components_cache()
    yield
    clear_components_cache()


@pytest_asyncio.fixture
async def mock_db():
    """Mock database session"""
    mock_session = AsyncMock()
    yield mock_session


@pytest.fixture
def mock_stock_service():
    """Mock stock service"""
    mock_service = MagicMock()
    mock_service.get_all_companies = AsyncMock(return_value=([], 0, 0))
    mock_service.get_company_by_symbol = AsyncMock(return_value=None)
    mock_service.get_company_detail = AsyncMock(return_value=None)
    mock_service.get_historical_data = AsyncMock(return_value=None)
    mock_service.get_top_gainers = AsyncMock(return_value=[])
    mock_service.get_top_losers = AsyncMock(return_value=[])
    mock_service.get_top_actives = AsyncMock(return_value=[])
    mock_service.search_companies = AsyncMock(return_value=[])
    mock_service.get_industries = AsyncMock(return_value=[])
    mock_service.get_market_indices = AsyncMock(return_value=[])
    mock_service.get_companies_by_industry = AsyncMock(return_value=[])
    return mock_service


@pytest_asyncio.fixture
async def client(mock_db, mock_stock_service):
    """Create test client with mocked dependencies"""

    async def override_get_db():
        yield mock_db

    def override_get_stock_service():
        return mock_stock_service

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_stock_service] = override_get_stock_service

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def mock_company():
    """Mock company response"""
    return CompanyResponse(
        id=1,
        symbol="VNM",
        name="Vietnam Dairy Products JSC",
        exchange="HOSE",
        industry_id=1,
        industry_name="Food & Beverage",
        is_active=True,
        is_tradeable=True,
        market_cap=180000000000000
    )


@pytest.fixture
def mock_company_detail():
    """Mock company detail response"""
    return CompanyDetailResponse(
        id=1,
        symbol="VNM",
        name="Vietnam Dairy Products JSC",
        name_en="Vinamilk",
        exchange="HOSE",
        industry=IndustryResponse(
            id=1,
            code="FOOD",
            name="Food & Beverage",
            level=1
        ),
        current_price=75000.0,
        change=1500.0,
        change_percent=2.04,
        volume=1500000,
        market_cap=180000000000000,
        description="Leading dairy company in Vietnam",
        website="https://www.vinamilk.com.vn"
    )


@pytest.fixture
def mock_historical_data():
    """Mock historical data response"""
    return HistoricalDataResponse(
        symbol="VNM",
        name="Vietnam Dairy Products JSC",
        exchange="HOSE",
        data=[
            StockPriceResponse(
                date=date.today(),
                open=74000.0,
                high=76000.0,
                low=73500.0,
                close=75000.0,
                volume=1500000
            )
        ],
        count=1
    )


@pytest.fixture
def mock_top_mover():
    """Mock top mover response"""
    return TopMoverResponse(
        symbol="VNM",
        name="Vietnam Dairy Products JSC",
        exchange="HOSE",
        close=75000.0,
        change=1500.0,
        change_percent=2.04,
        volume=1500000
    )


@pytest.fixture
def mock_search_result():
    """Mock search result"""
    return SearchResult(
        symbol="VNM",
        name="Vietnam Dairy Products JSC",
        exchange="HOSE",
        industry_name="Food & Beverage"
    )


@pytest.fixture
def mock_market_index():
    """Mock market index response"""
    return MarketIndexResponse(
        code="VNINDEX",
        name="VN-Index",
        date=date.today(),
        close=1200.5,
        change=15.3,
        change_percent=1.29,
        volume=500000000
    )


@pytest.fixture
def mock_industry():
    """Mock industry response"""
    return IndustryResponse(
        id=1,
        code="FOOD",
        name="Food & Beverage",
        level=1,
        company_count=25
    )

# ── gen-5 vendor construction, for tests written against the gen-4 facade ──
#
# Backlog #142 moved production from `Vnstock().stock(...)` to the gen-5 direct
# classes, so patching `StockService.vnstock` no longer intercepts anything —
# tests that did it started making REAL network calls and the suite hung on
# 30s read timeouts rather than failing.
#
# Rather than rewrite every fake, this maps the EXISTING ones onto the new
# construction path: the fakes already describe the vendor surface correctly
# (`fake.stock(symbol, source).finance.ratio(...)`), and that shape is still
# exactly what the service needs — only who constructs each component changed.
# So one adapter here beats fifteen rewritten fixtures, and the fakes stay
# readable as descriptions of the vendor rather than of our plumbing.
import contextlib as _contextlib
from unittest.mock import patch as _patch


@_contextlib.contextmanager
def patch_vendor_components(fake_vnstock):
    """Make the gen-5 classes resolve to `fake_vnstock.stock(...).<kind>`.

    `VnListing` is served from the fake's PRIMARY components object, not from a
    KBS-specific sheet, and the distinction is load-bearing. Production pins the
    listing component to KBS (LISTING_SOURCE) because gen-4 did — but in gen-4's
    OBJECT GRAPH `.listing` hung off the components object built for the
    configured source, with the KBS pinning hidden inside it. Source-aware fakes
    (see `_vnstock_with(..., kbs_ratio_df=...)`) model that graph: their KBS
    sheet carries only `finance.ratio`. Passing source="KBS" through to such a
    fake would therefore ask for `.listing` on a sheet that has none, which is a
    fixture artefact and not a production behaviour change.
    """
    def _sub(kind):
        def build(*args, **kwargs):
            symbol = kwargs.get("symbol") or (args[0] if args else "")
            source = kwargs.get("source") or (args[1] if len(args) > 1 else None)
            if kind == "listing":
                symbol, source = "", None     # the primary sheet — see above
            try:
                components = fake_vnstock.stock(symbol=symbol, source=source)
            except TypeError:                     # fakes with a positional API
                components = fake_vnstock.stock(symbol, source)
            return getattr(components, kind)
        return build

    with _patch("app.services.stock_service.VnQuote", side_effect=_sub("quote")), \
         _patch("app.services.stock_service.VnCompany", side_effect=_sub("company")), \
         _patch("app.services.stock_service.VnFinance", side_effect=_sub("finance")), \
         _patch("app.services.stock_service.VnListing", side_effect=_sub("listing")), \
         _patch("app.services.stock_service.VnTrading", side_effect=_sub("trading")):
        yield

