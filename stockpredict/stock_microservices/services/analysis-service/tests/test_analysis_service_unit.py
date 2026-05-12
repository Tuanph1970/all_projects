"""Unit tests for AnalysisService — pure indicator math, _determine_signal
scoring, _apply_filters / _match_filter operators, cache-hit and
httpx-mocked paths for get_technical_analysis / get_fundamental_analysis
/ run_screener.

httpx + repository are all mocked. Numpy/pandas DataFrames are built
deterministically.
"""
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import numpy as np
import pandas as pd
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.api.dependencies import get_current_user, get_current_user_optional
from app.config import get_settings
from app.models.schemas import (
    AnalysisType,
    FilterOperator,
    ScreenerFilter,
    SignalType,
)
from app.services import analysis_service as svc_mod
from app.services.analysis_service import AnalysisService


settings = get_settings()


def _make_service() -> AnalysisService:
    svc = AnalysisService(session=MagicMock())
    svc.repo = MagicMock()
    return svc


def _trend_df(rows: int, start: float, drift: float) -> pd.DataFrame:
    close = np.array([start + drift * i for i in range(rows)], dtype=float)
    high = close + 1.0
    low = close - 1.0
    return pd.DataFrame({
        "date": pd.date_range("2026-01-01", periods=rows, freq="D"),
        "open": close - 0.2,
        "high": high,
        "low": low,
        "close": close,
        "volume": np.full(rows, 1000),
    })


# ---------------------------------------------------------------------------
# Pure indicator math
# ---------------------------------------------------------------------------

class TestIndicatorMath:
    def test_rsi_returns_50_when_series_too_short(self):
        """A series with no variance (or too few points for 14-day window)
        returns the neutral 50.0 default rather than NaN."""
        svc = _make_service()
        prices = pd.Series([100.0] * 5)
        assert svc._calculate_rsi(prices) == 50.0

    def test_rsi_for_monotonic_uptrend_approaches_100(self):
        svc = _make_service()
        prices = pd.Series([100 + i for i in range(30)])
        # Pure uptrend: gain >> loss → rs huge → rsi ≈ 100.
        rsi = svc._calculate_rsi(prices)
        assert rsi > 95

    def test_rsi_for_monotonic_downtrend_approaches_0(self):
        svc = _make_service()
        prices = pd.Series([200 - i for i in range(30)])
        rsi = svc._calculate_rsi(prices)
        assert rsi < 5

    def test_macd_returns_finite_pair(self):
        svc = _make_service()
        prices = pd.Series(list(range(50)))
        macd, signal = svc._calculate_macd(prices)
        assert np.isfinite(macd)
        assert np.isfinite(signal)

    def test_bollinger_returns_upper_lower_middle(self):
        svc = _make_service()
        # Non-constant series so std() is > 0.
        prices = pd.Series([100 + (i % 5) for i in range(30)])
        upper, lower, middle = svc._calculate_bollinger(prices)
        assert upper > middle > lower

    def test_find_support_resistance_picks_local_extrema(self):
        svc = _make_service()
        # Build a wave with clear pivots.
        prices = pd.Series([
            100, 102, 105, 102, 100,   # local high at index 2
            98, 95, 92, 95, 98,         # local low at index 7
            101, 104, 107, 104, 101,   # local high at index 12
        ])
        supports, resistances = svc._find_support_resistance(prices)
        # Should detect at least one each.
        assert len(supports) >= 1
        assert len(resistances) >= 1

    def test_find_support_resistance_fallback_when_no_pivots(self):
        """A monotonic series has no internal extrema → falls back to
        the global min/max."""
        svc = _make_service()
        prices = pd.Series([100 + i for i in range(10)])
        supports, resistances = svc._find_support_resistance(prices)
        assert supports == [prices.min()]
        assert resistances == [prices.max()]


# ---------------------------------------------------------------------------
# _determine_signal — score-to-signal mapping
# ---------------------------------------------------------------------------

class TestDetermineSignal:
    def test_strong_buy_when_score_at_or_above_50(self):
        """RSI oversold + bullish MACD + above both SMAs → 30+20+15+15 = 80."""
        svc = _make_service()
        signal, strength, score = svc._determine_signal(
            rsi=25, macd=1.0, macd_signal=0.5,
            current_price=110, sma_20=100, sma_50=95,
        )
        assert signal == SignalType.STRONG_BUY
        assert score == 80
        assert 0.0 <= strength <= 1.0

    def test_buy_when_score_in_20_to_50_range(self):
        """Less extreme: -15 from neutral RSI overbought + 20 MACD + 15 + 15 = 35."""
        svc = _make_service()
        signal, _, score = svc._determine_signal(
            rsi=55, macd=1.0, macd_signal=0.5,
            current_price=110, sma_20=100, sma_50=95,
        )
        # rsi=55 contributes 0 → score = 20 + 15 + 15 = 50 → STRONG_BUY
        # Use rsi=62 to get RSI=-15 → 20-15+15+15 = 35
        signal, _, score = svc._determine_signal(
            rsi=62, macd=1.0, macd_signal=0.5,
            current_price=110, sma_20=100, sma_50=95,
        )
        assert signal == SignalType.BUY
        assert score == 35

    def test_strong_sell_when_score_at_or_below_minus_50(self):
        svc = _make_service()
        signal, _, score = svc._determine_signal(
            rsi=75, macd=0.0, macd_signal=1.0,
            current_price=90, sma_20=100, sma_50=105,
        )
        # -30 (rsi>70) + -20 (macd bearish) + -15 (below sma20) + -15 (below sma50) = -80
        assert signal == SignalType.STRONG_SELL
        assert score == -80

    def test_sell_when_score_in_neg20_to_neg50_range(self):
        svc = _make_service()
        # rsi=65 → -15, macd bearish → -20, below sma20 → -15, above sma50 → +15
        signal, _, score = svc._determine_signal(
            rsi=65, macd=0.0, macd_signal=1.0,
            current_price=98, sma_20=100, sma_50=95,
        )
        assert signal == SignalType.SELL
        assert score == -35

    def test_hold_when_score_in_neutral_band(self):
        svc = _make_service()
        # rsi=50 → 0, macd bullish → +20, below sma20 → -15, below sma50 → -15
        signal, _, score = svc._determine_signal(
            rsi=50, macd=1.0, macd_signal=0.5,
            current_price=90, sma_20=100, sma_50=100,
        )
        assert signal == SignalType.HOLD
        assert score == -10


# ---------------------------------------------------------------------------
# _fetch_historical_data — httpx
# ---------------------------------------------------------------------------

class _FakeHttpxClient:
    def __init__(self, response):
        self._response = response

    async def __aenter__(self):
        c = MagicMock()
        c.get = AsyncMock(return_value=self._response)
        return c

    async def __aexit__(self, *_):
        return False


@pytest.mark.asyncio
async def test_fetch_historical_data_returns_sorted_dataframe():
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "data": [
            {"date": "2026-05-02", "close": 110},
            {"date": "2026-05-01", "close": 105},
        ]
    }
    svc = _make_service()
    with patch("app.services.analysis_service.httpx.AsyncClient",
               return_value=_FakeHttpxClient(resp)):
        df = await svc._fetch_historical_data("FPT", days=30)
    assert df is not None
    # Sorted ascending by date.
    assert list(df["close"]) == [105, 110]


@pytest.mark.asyncio
async def test_fetch_historical_data_returns_none_on_non_200():
    resp = MagicMock()
    resp.status_code = 503
    svc = _make_service()
    with patch("app.services.analysis_service.httpx.AsyncClient",
               return_value=_FakeHttpxClient(resp)):
        assert (await svc._fetch_historical_data("FPT")) is None


@pytest.mark.asyncio
async def test_fetch_historical_data_returns_none_on_exception():
    class Boom:
        async def __aenter__(self):
            raise ConnectionError("down")

        async def __aexit__(self, *_):
            return False

    svc = _make_service()
    with patch("app.services.analysis_service.httpx.AsyncClient", return_value=Boom()):
        assert (await svc._fetch_historical_data("FPT")) is None


@pytest.mark.asyncio
async def test_fetch_historical_data_returns_none_when_data_field_empty():
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {}
    svc = _make_service()
    with patch("app.services.analysis_service.httpx.AsyncClient",
               return_value=_FakeHttpxClient(resp)):
        assert (await svc._fetch_historical_data("FPT")) is None


# ---------------------------------------------------------------------------
# get_technical_analysis
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_technical_analysis_returns_cached_response_when_present():
    """If the repo returns a cached AnalysisResult, the service builds
    a response from it without calling _fetch_historical_data."""
    svc = _make_service()
    cached = MagicMock(
        sma_20=100.0, sma_50=98.0,
        overall_signal="buy", signal_strength=0.6, technical_score=35,
        support_levels=[95.0, 90.0], resistance_levels=[105.0, 110.0],
        created_at=datetime.utcnow(),
    )
    svc.repo.get_cached_analysis = AsyncMock(return_value=cached)
    with patch.object(svc, "_fetch_historical_data", AsyncMock()) as fetch_mock:
        out = await svc.get_technical_analysis("FPT")
    fetch_mock.assert_not_awaited()
    assert out is not None
    assert out.technical_score == 35
    assert out.overall_signal == SignalType.BUY


@pytest.mark.asyncio
async def test_technical_analysis_returns_none_when_no_data_available():
    svc = _make_service()
    svc.repo.get_cached_analysis = AsyncMock(return_value=None)
    with patch.object(svc, "_fetch_historical_data", AsyncMock(return_value=None)):
        out = await svc.get_technical_analysis("FPT")
    assert out is None


@pytest.mark.asyncio
async def test_technical_analysis_returns_none_when_too_few_rows():
    svc = _make_service()
    svc.repo.get_cached_analysis = AsyncMock(return_value=None)
    short_df = _trend_df(rows=10, start=100.0, drift=0.0)
    with patch.object(svc, "_fetch_historical_data", AsyncMock(return_value=short_df)):
        out = await svc.get_technical_analysis("FPT")
    assert out is None


@pytest.mark.asyncio
async def test_technical_analysis_happy_path_builds_full_response():
    svc = _make_service()
    svc.repo.get_cached_analysis = AsyncMock(return_value=None)
    svc.repo.save_analysis = AsyncMock()
    df = _trend_df(rows=60, start=100.0, drift=1.0)
    with patch.object(svc, "_fetch_historical_data", AsyncMock(return_value=df)):
        out = await svc.get_technical_analysis("fpt")
    assert out is not None
    assert out.symbol == "FPT"
    # Uptrend (price > sma_20 > sma_50).
    assert out.trend == "bullish"
    # Save was attempted.
    svc.repo.save_analysis.assert_awaited_once()
    # Indicators contain the 6 expected entries.
    assert {i.name for i in out.indicators} == {
        "RSI", "MACD", "SMA 20", "SMA 50", "BB Upper", "BB Lower",
    }


@pytest.mark.asyncio
async def test_technical_analysis_classifies_downtrend():
    svc = _make_service()
    svc.repo.get_cached_analysis = AsyncMock(return_value=None)
    svc.repo.save_analysis = AsyncMock()
    df = _trend_df(rows=60, start=200.0, drift=-1.0)
    with patch.object(svc, "_fetch_historical_data", AsyncMock(return_value=df)):
        out = await svc.get_technical_analysis("FPT")
    assert out.trend == "bearish"


@pytest.mark.asyncio
async def test_technical_analysis_low_volatility_classification():
    svc = _make_service()
    svc.repo.get_cached_analysis = AsyncMock(return_value=None)
    svc.repo.save_analysis = AsyncMock()
    # Flat series → vol << 1.5%.
    df = _trend_df(rows=60, start=100.0, drift=0.0)
    with patch.object(svc, "_fetch_historical_data", AsyncMock(return_value=df)):
        out = await svc.get_technical_analysis("FPT")
    assert out.volatility == "low"


# ---------------------------------------------------------------------------
# get_fundamental_analysis
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fundamental_analysis_returns_none_on_non_200():
    resp = MagicMock()
    resp.status_code = 404
    svc = _make_service()
    with patch("app.services.analysis_service.httpx.AsyncClient",
               return_value=_FakeHttpxClient(resp)):
        out = await svc.get_fundamental_analysis("FPT")
    assert out is None


@pytest.mark.asyncio
async def test_fundamental_analysis_returns_none_on_exception():
    class Boom:
        async def __aenter__(self):
            raise ConnectionError("down")

        async def __aexit__(self, *_):
            return False

    svc = _make_service()
    with patch("app.services.analysis_service.httpx.AsyncClient", return_value=Boom()):
        out = await svc.get_fundamental_analysis("FPT")
    assert out is None


@pytest.mark.asyncio
async def test_fundamental_analysis_happy_path_builds_full_response():
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "company_name": "FPT Corp",
        "market_cap": 1_000_000_000,
        "pe_ratio": 12.0,   # < 15 → undervalued
        "pb_ratio": 1.2,    # < 1.5 → undervalued
        "roe": 18.0,        # > 15 → strong
        "debt_to_equity": 0.4,  # < 0.5 → +10 to fundamental score
        "financial_ratios": {"pe": 12.0, "roe": 18.0},
        "growth_metrics": {"revenueGrowth": 15.0},
        "income_statement": {"revenue": 1000, "eps": 5.0},
        "balance_sheet": {"totalAssets": 5000, "totalEquity": 3000},
        "cash_flow": {"operatingCashFlow": 800, "freeCashFlow": 650},
    }
    svc = _make_service()
    with patch("app.services.analysis_service.httpx.AsyncClient",
               return_value=_FakeHttpxClient(resp)):
        out = await svc.get_fundamental_analysis("FPT")
    assert out is not None
    assert out.symbol == "FPT"
    assert out.company_name == "FPT Corp"
    # P/E < 15 + ROE > 15 + D/E < 0.5 → score = 50 + 15 + 15 + 10 = 90 → undervalued
    assert out.fundamental_score == 90
    assert out.overall_rating == "undervalued"
    # All three ratio factors present.
    factor_names = {f.factor for f in out.valuation_summary.factors}
    assert factor_names == {"P/E", "P/B", "ROE"}


@pytest.mark.asyncio
async def test_fundamental_analysis_with_overvalued_signals():
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "company_name": "X",
        "pe_ratio": 35.0,        # > 25 → overvalued
        "pb_ratio": 5.0,         # > 3 → overvalued
        "roe": 3.0,              # < 5 → weak
        "debt_to_equity": 2.5,   # > 2 → -10
    }
    svc = _make_service()
    with patch("app.services.analysis_service.httpx.AsyncClient",
               return_value=_FakeHttpxClient(resp)):
        out = await svc.get_fundamental_analysis("X")
    assert out is not None
    # 50 - 15 - 10 - 10 = 15 (clamped to 0+)
    assert out.fundamental_score < 40
    assert out.overall_rating == "overvalued"


# ---------------------------------------------------------------------------
# _rate_pe / _rate_roe / _calculate_fundamental_score
# ---------------------------------------------------------------------------

class TestFundamentalRatings:
    def test_rate_pe_none(self):
        assert _make_service()._rate_pe(None) is None

    def test_rate_pe_undervalued_below_10(self):
        assert _make_service()._rate_pe(8.0) == "undervalued"

    def test_rate_pe_overvalued_above_25(self):
        assert _make_service()._rate_pe(30.0) == "overvalued"

    def test_rate_pe_fair_in_between(self):
        assert _make_service()._rate_pe(15.0) == "fair"

    def test_rate_roe_paths(self):
        svc = _make_service()
        assert svc._rate_roe(None) is None
        assert svc._rate_roe(18.0) == "good"
        assert svc._rate_roe(3.0) == "poor"
        assert svc._rate_roe(10.0) == "average"

    def test_calculate_fundamental_score_clamps_to_0_100(self):
        svc = _make_service()
        # All positive factors: 50 + 15 + 15 + 10 = 90
        assert svc._calculate_fundamental_score({
            "pe_ratio": 10.0, "roe": 20.0, "debt_to_equity": 0.3,
        }) == 90
        # All negative factors: 50 - 15 - 10 - 10 = 15
        assert svc._calculate_fundamental_score({
            "pe_ratio": 40.0, "roe": 2.0, "debt_to_equity": 3.0,
        }) == 15
        # Empty data → unchanged baseline.
        assert svc._calculate_fundamental_score({}) == 50


# ---------------------------------------------------------------------------
# _apply_filters / _match_filter — operator branches
# ---------------------------------------------------------------------------

class TestMatchFilter:
    def test_missing_field_returns_false(self):
        svc = _make_service()
        f = ScreenerFilter(field="price", operator=FilterOperator.GT, value=100)
        assert svc._match_filter({"symbol": "X"}, f) is False

    def test_gt_operator(self):
        svc = _make_service()
        f = ScreenerFilter(field="price", operator=FilterOperator.GT, value=100)
        assert svc._match_filter({"price": 150}, f) is True
        assert svc._match_filter({"price": 100}, f) is False

    def test_gte_operator(self):
        svc = _make_service()
        f = ScreenerFilter(field="price", operator=FilterOperator.GTE, value=100)
        assert svc._match_filter({"price": 100}, f) is True
        assert svc._match_filter({"price": 99}, f) is False

    def test_lt_operator(self):
        svc = _make_service()
        f = ScreenerFilter(field="price", operator=FilterOperator.LT, value=100)
        assert svc._match_filter({"price": 50}, f) is True

    def test_lte_operator(self):
        svc = _make_service()
        f = ScreenerFilter(field="price", operator=FilterOperator.LTE, value=100)
        assert svc._match_filter({"price": 100}, f) is True

    def test_eq_operator(self):
        svc = _make_service()
        f = ScreenerFilter(field="symbol", operator=FilterOperator.EQ, value="FPT")
        assert svc._match_filter({"symbol": "FPT"}, f) is True
        assert svc._match_filter({"symbol": "VNM"}, f) is False

    def test_between_operator(self):
        svc = _make_service()
        f = ScreenerFilter(
            field="price", operator=FilterOperator.BETWEEN,
            value=50, value2=150,
        )
        assert svc._match_filter({"price": 100}, f) is True
        assert svc._match_filter({"price": 200}, f) is False


def test_apply_filters_chains_multiple_filters():
    svc = _make_service()
    stocks = [
        {"symbol": "A", "price": 50, "rsi": 80},
        {"symbol": "B", "price": 150, "rsi": 25},
        {"symbol": "C", "price": 100, "rsi": 50},
    ]
    filters = [
        ScreenerFilter(field="price", operator=FilterOperator.GTE, value=100),
        ScreenerFilter(field="rsi", operator=FilterOperator.LT, value=60),
    ]
    out = svc._apply_filters(stocks, filters)
    assert [s["symbol"] for s in out] == ["B", "C"]


# ---------------------------------------------------------------------------
# run_screener
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_screener_returns_cached_when_present():
    svc = _make_service()
    cached = MagicMock()
    cached.results = [{
        "symbol": "FPT", "name": "FPT Corp", "exchange": "HOSE",
        "price": 100.0, "change_percent": 1.0, "volume": 1000,
        "market_cap": None, "pe_ratio": None, "rsi": None, "signal": None,
    }]
    cached.total_matches = 1
    cached.created_at = datetime.utcnow()
    svc.repo.get_cached_screener = AsyncMock(return_value=cached)
    out = await svc.run_screener(filters=[])
    assert out.total == 1
    assert out.stocks[0].symbol == "FPT"


@pytest.mark.asyncio
async def test_run_screener_returns_empty_on_upstream_exception():
    svc = _make_service()
    svc.repo.get_cached_screener = AsyncMock(return_value=None)

    class Boom:
        async def __aenter__(self):
            raise ConnectionError("down")

        async def __aexit__(self, *_):
            return False

    with patch("app.services.analysis_service.httpx.AsyncClient", return_value=Boom()):
        out = await svc.run_screener(filters=[])
    assert out.total == 0
    assert out.stocks == []


@pytest.mark.asyncio
async def test_run_screener_returns_empty_when_no_stocks_returned():
    svc = _make_service()
    svc.repo.get_cached_screener = AsyncMock(return_value=None)

    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = []

    with patch("app.services.analysis_service.httpx.AsyncClient",
               return_value=_FakeHttpxClient(resp)):
        out = await svc.run_screener(filters=[])
    assert out.total == 0


@pytest.mark.asyncio
async def test_run_screener_happy_path_filters_and_paginates():
    svc = _make_service()
    svc.repo.get_cached_screener = AsyncMock(return_value=None)
    svc.repo.cache_screener_results = AsyncMock()

    canned_stocks = [
        {"symbol": "FPT", "matchPrice": 100, "changePercent": 5.0, "totalQty": 10000, "exchange": "HSX"},
        {"symbol": "VNM", "matchPrice": 70, "changePercent": -2.0, "totalQty": 5000, "exchange": "HSX"},
        {"symbol": "FPT", "matchPrice": 100, "changePercent": 5.0},  # duplicate; deduped
    ]
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = canned_stocks

    with patch("app.services.analysis_service.httpx.AsyncClient",
               return_value=_FakeHttpxClient(resp)):
        out = await svc.run_screener(
            filters=[ScreenerFilter(
                field="change_percent",
                operator=FilterOperator.GT,
                value=0,
            )],
            sort_by="change_percent",
            sort_order="desc",
            limit=10,
            offset=0,
        )
    # 4 groups × 2 stocks each = 8 fetched; after dedupe = 2 unique;
    # change_percent > 0 → only FPT matches.
    assert out.total == 1
    assert out.stocks[0].symbol == "FPT"
    # Cache write attempted.
    svc.repo.cache_screener_results.assert_awaited_once()


# ---------------------------------------------------------------------------
# Dependencies — JWT helpers
# ---------------------------------------------------------------------------

def _creds(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def _token(payload: dict) -> str:
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


@pytest.mark.asyncio
async def test_get_current_user_optional_returns_none_without_credentials():
    assert (await get_current_user_optional(credentials=None)) is None


@pytest.mark.asyncio
async def test_get_current_user_optional_returns_none_on_invalid_token():
    assert (await get_current_user_optional(credentials=_creds("not.a.jwt"))) is None


@pytest.mark.asyncio
async def test_get_current_user_optional_returns_user_on_valid_token():
    token = _token({"sub": "42", "email": "alice@example.com"})
    user = await get_current_user_optional(credentials=_creds(token))
    assert user == {"user_id": 42, "email": "alice@example.com"}


@pytest.mark.asyncio
async def test_get_current_user_raises_401_on_invalid_token():
    with pytest.raises(HTTPException) as exc:
        await get_current_user(credentials=_creds("not.a.jwt"))
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_raises_401_when_sub_missing():
    token = _token({"email": "x@y.com"})
    with pytest.raises(HTTPException) as exc:
        await get_current_user(credentials=_creds(token))
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_returns_dict_on_valid_token():
    token = _token({"sub": "7", "email": "alice@example.com"})
    user = await get_current_user(credentials=_creds(token))
    assert user == {"user_id": 7, "email": "alice@example.com"}


# ---------------------------------------------------------------------------
# AnalysisRepository — exercise hash + CRUD
# ---------------------------------------------------------------------------

from app.repositories.analysis_repository import AnalysisRepository


def test_hash_filters_is_deterministic_and_order_independent():
    repo = AnalysisRepository(session=MagicMock())
    a = [{"field": "price", "operator": "gt", "value": 100}]
    b = [{"value": 100, "operator": "gt", "field": "price"}]
    # JSON sort_keys=True → both produce the same hash.
    assert repo._hash_filters(a) == repo._hash_filters(b)


@pytest.mark.asyncio
async def test_save_analysis_persists_with_uppercased_symbol():
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    repo = AnalysisRepository(session)
    out = await repo.save_analysis(
        symbol="fpt", analysis_type=AnalysisType.TECHNICAL, rsi=55.0,
    )
    assert out.symbol == "FPT"


@pytest.mark.asyncio
async def test_save_screener_config_returns_config():
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    repo = AnalysisRepository(session)
    cfg = await repo.save_screener_config(
        user_id=1, name="My Screen", filters=[],
    )
    assert cfg.user_id == 1
    assert cfg.name == "My Screen"


@pytest.mark.asyncio
async def test_get_screener_configs_returns_list():
    session = AsyncMock()
    result = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = [MagicMock(id=1, user_id=1)]
    result.scalars.return_value = scalars
    session.execute = AsyncMock(return_value=result)
    repo = AnalysisRepository(session)
    out = await repo.get_screener_configs(user_id=1)
    assert len(out) == 1


@pytest.mark.asyncio
async def test_delete_screener_config_returns_true_when_row_deleted():
    session = AsyncMock()
    result = MagicMock()
    result.rowcount = 1
    session.execute = AsyncMock(return_value=result)
    session.commit = AsyncMock()
    repo = AnalysisRepository(session)
    assert (await repo.delete_screener_config(1, 1)) is True


@pytest.mark.asyncio
async def test_delete_screener_config_returns_false_when_missing():
    session = AsyncMock()
    result = MagicMock()
    result.rowcount = 0
    session.execute = AsyncMock(return_value=result)
    session.commit = AsyncMock()
    repo = AnalysisRepository(session)
    assert (await repo.delete_screener_config(99, 1)) is False


@pytest.mark.asyncio
async def test_save_fundamental_data_creates_new_when_absent():
    session = AsyncMock()
    none_result = MagicMock()
    none_result.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=none_result)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    repo = AnalysisRepository(session)
    # pe_ratio is a real FundamentalData column.
    out = await repo.save_fundamental_data(symbol="fpt", pe_ratio=12.5)
    assert out.symbol == "FPT"


@pytest.mark.asyncio
async def test_save_fundamental_data_updates_existing():
    """When a row already exists, fields are updated in place."""
    session = AsyncMock()
    existing = MagicMock(symbol="FPT")
    existing.pe_ratio = 0  # so hasattr() returns True
    found = MagicMock()
    found.scalar_one_or_none.return_value = existing
    session.execute = AsyncMock(return_value=found)
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    repo = AnalysisRepository(session)
    out = await repo.save_fundamental_data(symbol="FPT", pe_ratio=15.5)
    assert out is existing
    assert existing.pe_ratio == 15.5
