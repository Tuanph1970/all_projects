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


def _ohlc_from_closes(closes) -> pd.DataFrame:
    close = np.asarray(closes, dtype=float)
    return pd.DataFrame({
        "date": pd.date_range("2026-01-01", periods=len(close), freq="D"),
        "open": close,
        "high": close + 0.5,
        "low": close - 0.5,
        "close": close,
        "volume": np.full(len(close), 1000),
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

    def test_find_support_resistance_splits_levels_around_price(self):
        svc = _make_service()
        # Wave with clear pivots: troughs near 92, peaks near 105/107.
        closes = [
            100, 102, 105, 102, 100,   # local high at index 2
            98, 95, 92, 95, 98,        # local low at index 7
            101, 104, 107, 104, 101,   # local high at index 12
        ]
        ohlc = _ohlc_from_closes(closes)
        supports, resistances = svc._find_support_resistance(ohlc, current_price=100.0)
        assert supports and resistances
        # Every support sits below price and every resistance above it — the
        # old implementation returned troughs above price as "support".
        assert all(s < 100.0 for s in supports)
        assert all(r > 100.0 for r in resistances)
        # Ordered nearest-first, so index 0 is S1 / R1.
        assert supports == sorted(supports, reverse=True)
        assert resistances == sorted(resistances)

    def test_find_support_resistance_fallback_when_no_pivots(self):
        """A monotonic series has no internal extrema → falls back to
        the window extremes on whichever side price allows."""
        svc = _make_service()
        ohlc = _ohlc_from_closes([100 + i for i in range(10)])
        supports, resistances = svc._find_support_resistance(ohlc, current_price=105.0)
        assert supports == [float(ohlc["low"].min())]
        assert resistances == [float(ohlc["high"].max())]


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
async def test_technical_analysis_always_refetches_ignoring_cache():
    """The symbol-only cache was removed because it served chart_data=None
    for every period after the first; every call must hit the history API."""
    svc = _make_service()
    svc.repo.get_cached_analysis = AsyncMock()
    svc.repo.save_analysis = AsyncMock()
    df = _trend_df(rows=60, start=100.0, drift=1.0)
    with patch.object(svc, "_fetch_historical_data",
                      AsyncMock(return_value=df)) as fetch_mock:
        out = await svc.get_technical_analysis("FPT")
    fetch_mock.assert_awaited_once()
    svc.repo.get_cached_analysis.assert_not_awaited()
    assert out is not None


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
# get_technical_analysis — the grouped indicator payload the UI reads.
# Regression: the Indicators tab rendered N/A for every one of these because
# the response only carried a flat `indicators` list.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_technical_analysis_fills_every_indicator_group():
    svc = _make_service()
    svc.repo.save_analysis = AsyncMock()
    df = _trend_df(rows=260, start=100.0, drift=0.5)
    with patch.object(svc, "_fetch_historical_data", AsyncMock(return_value=df)):
        out = await svc.get_technical_analysis("FPT", period=100)

    m = out.momentum_indicators
    assert m is not None
    for field in ("RSI", "MACD", "MACD_Signal", "MACD_Histogram", "Stoch_K", "Stoch_D"):
        assert getattr(m, field) is not None, f"{field} would render as N/A"

    v = out.volatility_indicators
    assert v is not None
    for field in ("BB_Upper", "BB_Middle", "BB_Lower", "BB_Width", "ATR", "ATR_Percent"):
        assert getattr(v, field) is not None, f"{field} would render as N/A"
    assert v.BB_Lower < v.BB_Middle < v.BB_Upper

    vol = out.volume_indicators
    assert vol is not None
    assert vol.volume_avg_20 is not None and vol.volume_ratio is not None
    assert vol.OBV is not None

    assert out.support_resistance is not None
    assert out.fibonacci_levels  # non-empty dict keyed by retracement percent
    assert out.trading_analysis.signals


@pytest.mark.asyncio
async def test_technical_analysis_warmup_makes_sma_200_available():
    """SMA 200 was always null because only `period` bars were fetched.
    With the warm-up run it resolves even for a 100-bar display window."""
    svc = _make_service()
    svc.repo.save_analysis = AsyncMock()
    df = _trend_df(rows=300, start=100.0, drift=0.2)
    with patch.object(svc, "_fetch_historical_data",
                      AsyncMock(return_value=df)) as fetch_mock:
        out = await svc.get_technical_analysis("FPT", period=100)
    # Asked the history API for the display window plus the warm-up run.
    requested_days = fetch_mock.await_args.args[1]
    assert requested_days > 100
    assert out.moving_averages.SMA_200 is not None
    # Only the requested window is charted, warm-up bars stay hidden.
    assert len(out.chart_data.dates) == 100


@pytest.mark.asyncio
async def test_technical_analysis_returns_null_not_nan_for_short_history():
    """A window too short for a 200-bar window must serialise as null
    (JSON has no NaN) so the UI shows N/A only where it is truly unknown."""
    svc = _make_service()
    svc.repo.save_analysis = AsyncMock()
    df = _trend_df(rows=30, start=100.0, drift=0.5)
    with patch.object(svc, "_fetch_historical_data", AsyncMock(return_value=df)):
        out = await svc.get_technical_analysis("FPT", period=100)
    assert out.moving_averages.SMA_200 is None
    # Everything computable from 30 bars is still present.
    assert out.momentum_indicators.RSI is not None
    assert out.volatility_indicators.ATR is not None
    # And the payload is JSON-clean — NaN would raise here.
    import json
    json.dumps(out.model_dump(mode="json"), allow_nan=False)


@pytest.mark.asyncio
async def test_trading_signals_agree_with_the_uptrend():
    svc = _make_service()
    svc.repo.save_analysis = AsyncMock()
    df = _trend_df(rows=260, start=100.0, drift=1.0)
    with patch.object(svc, "_fetch_historical_data", AsyncMock(return_value=df)):
        out = await svc.get_technical_analysis("FPT", period=100)
    by_name = {sig.indicator: sig for sig in out.trading_analysis.signals}
    # Price is above every moving average in a monotonic uptrend.
    assert by_name["SMA 20"].signal == "BUY"
    assert by_name["SMA 50"].signal == "BUY"
    assert by_name["Trend"].signal == "BULLISH"


class TestNewIndicatorMath:
    def test_stochastic_pins_to_100_at_window_high(self):
        svc = _make_service()
        ohlc = _ohlc_from_closes([100 + i for i in range(30)])
        k, d = svc._calculate_stochastic(ohlc)
        # Close is the window's high on a monotonic rise (close == high - 0.5,
        # so just under 100 but firmly in the top decile).
        assert k > 90
        assert 0 <= d <= 100

    def test_stochastic_pins_to_0_at_window_low(self):
        svc = _make_service()
        ohlc = _ohlc_from_closes([130 - i for i in range(30)])
        k, _ = svc._calculate_stochastic(ohlc)
        assert k < 10

    def test_obv_is_positive_when_closes_rise(self):
        svc = _make_service()
        assert svc._calculate_obv(_ohlc_from_closes([100 + i for i in range(10)])) > 0

    def test_obv_is_negative_when_closes_fall(self):
        svc = _make_service()
        assert svc._calculate_obv(_ohlc_from_closes([110 - i for i in range(10)])) < 0

    def test_fibonacci_levels_span_the_window_range(self):
        svc = _make_service()
        ohlc = _ohlc_from_closes([100 + i for i in range(20)])
        levels = svc._calculate_fibonacci_levels(ohlc)
        assert set(levels) == {"0.0%", "23.6%", "38.2%", "50.0%", "61.8%", "78.6%", "100.0%"}
        low, high = float(ohlc["low"].min()), float(ohlc["high"].max())
        assert all(low - 0.01 <= p <= high + 0.01 for p in levels.values())
        # Rising window: 0% is the swing origin (the high), 100% the low.
        assert levels["0.0%"] == round(high, 2)
        assert levels["100.0%"] == round(low, 2)

    def test_fibonacci_levels_empty_for_a_flat_window(self):
        svc = _make_service()
        flat = pd.DataFrame({
            "date": pd.date_range("2026-01-01", periods=5, freq="D"),
            "open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0,
            "volume": 1000,
        })
        assert svc._calculate_fibonacci_levels(flat) == {}

    def test_safe_float_nulls_out_nan_and_inf(self):
        svc = _make_service()
        assert svc._safe_float(float("nan")) is None
        assert svc._safe_float(float("inf")) is None
        assert svc._safe_float(None) is None
        assert svc._safe_float(1.23456) == 1.23


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


# ---------------------------------------------------------------------------
# F-001 ATR + F-002 swing pivots (road_map_version_11.xlsx)
# ---------------------------------------------------------------------------

def _ohlc_df(highs, lows, closes, start="2026-01-01"):
    n = len(closes)
    assert len(highs) == n and len(lows) == n
    return pd.DataFrame({
        "date": pd.date_range(start, periods=n, freq="D"),
        "open": closes,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": np.full(n, 1000),
    })


class TestAtrIndicator:
    def test_atr_is_constant_when_true_range_is_constant(self):
        """If every bar has identical TR, Wilder ATR converges to that TR
        from the very first valid bar."""
        svc = _make_service()
        # high=102, low=100 each bar, no gaps -> TR == 2 for every bar.
        n = 30
        df = _ohlc_df(
            highs=[102.0] * n, lows=[100.0] * n,
            closes=[101.0] * n,
        )
        atr = svc._calculate_atr(df, period=14)
        # First period-1 values are NaN (min_periods=period); then constant 2.
        assert pd.isna(atr.iloc[12])
        assert atr.iloc[13] == pytest.approx(2.0, rel=1e-9)
        assert atr.iloc[-1] == pytest.approx(2.0, rel=1e-9)

    def test_atr_uses_prev_close_gap_in_true_range(self):
        """A gap up that exceeds today's H-L should bump TR via |H - prev_close|.
        We verify ATR rises after the gap bar."""
        svc = _make_service()
        # Flat bars (TR=1) for 20 days, then a gap-up bar.
        n = 20
        highs = [101.0] * n + [110.0]   # last bar gaps up
        lows  = [100.0] * n + [108.0]
        closes = [100.5] * n + [109.5]
        df = _ohlc_df(highs, lows, closes)
        atr = svc._calculate_atr(df, period=14)
        # ATR before the gap bar.
        before = atr.iloc[-2]
        after = atr.iloc[-1]
        assert before == pytest.approx(1.0, rel=1e-6)
        # Gap bar TR = max(2, |110 - 100.5|=9.5, |108 - 100.5|=7.5) = 9.5
        # Wilder: ATR_new = ATR_old + (TR - ATR_old)/14 = 1 + (9.5 - 1)/14 ≈ 1.6071
        assert after == pytest.approx(1 + (9.5 - 1) / 14, rel=1e-6)
        assert after > before

    def test_atr_returns_empty_series_when_columns_missing(self):
        svc = _make_service()
        df = pd.DataFrame({"close": [1, 2, 3]})
        with pytest.raises(KeyError):
            svc._calculate_atr(df, period=14)


class TestSwingPivots:
    def test_finds_alternating_highs_and_lows(self):
        """Synthetic zig-zag: every other peak/trough is a confirmed fractal pivot.
        Note: pivots within `window` bars of either end cannot be confirmed."""
        svc = _make_service()
        # 16 bars: peak at i=3, trough at i=7, peak at i=11, trough at i=13 — but
        # window=2 needs 2 bars on each side, so the last confirmable pivot is at
        # i = len - 1 - window = 13. Add trailing bars to confirm i=11.
        highs = [10, 12, 14, 16, 14, 12, 10,  8, 10, 12, 14, 16, 14, 12, 10]
        lows  = [ 9, 11, 13, 15, 13, 11,  9,  7,  9, 11, 13, 15, 13, 11,  9]
        df = _ohlc_df(highs, lows, closes=highs)
        pivots = svc._find_swing_pivots(df, window=2)
        idxs = [(p.bar_index, p.type.value, p.price) for p in pivots]
        # Confirmed pivots: high at i=3, low at i=7 (=7.0, not 8.0), high at i=11.
        assert (3, "high", 16.0) in idxs
        assert (7, "low", 7.0) in idxs
        assert (11, "high", 16.0) in idxs

    def test_returns_empty_when_dataframe_too_short(self):
        svc = _make_service()
        df = _ohlc_df(highs=[1, 2], lows=[0, 1], closes=[1, 2])
        assert svc._find_swing_pivots(df, window=3) == []

    def test_is_deterministic_across_reruns(self):
        svc = _make_service()
        np.random.seed(0)
        n = 80
        closes = np.cumsum(np.random.randn(n)) + 100
        df = _ohlc_df(highs=closes + 1, lows=closes - 1, closes=closes)
        a = svc._find_swing_pivots(df, window=3)
        b = svc._find_swing_pivots(df, window=3)
        assert [(p.bar_index, p.type, p.price) for p in a] == \
               [(p.bar_index, p.type, p.price) for p in b]

    def test_monotonic_series_has_no_internal_pivots(self):
        svc = _make_service()
        # Strictly rising — no high or low can satisfy both sides.
        closes = np.arange(20, dtype=float)
        df = _ohlc_df(highs=closes + 1, lows=closes - 1, closes=closes)
        assert svc._find_swing_pivots(df, window=2) == []


@pytest.mark.asyncio
async def test_get_atr_returns_none_when_history_too_short():
    svc = _make_service()
    with patch.object(svc, "_fetch_historical_data", AsyncMock(return_value=None)):
        assert (await svc.get_atr("FPT")) is None


@pytest.mark.asyncio
async def test_get_atr_builds_response_with_latest_and_series():
    svc = _make_service()
    n = 40
    df = _ohlc_df(
        highs=[102.0] * n, lows=[100.0] * n, closes=[101.0] * n,
    )
    with patch.object(svc, "_fetch_historical_data", AsyncMock(return_value=df)):
        out = await svc.get_atr("fpt", period=14, days=100, tail=10)
    assert out is not None
    assert out.symbol == "FPT"
    assert out.period == 14
    assert out.latest == pytest.approx(2.0, rel=1e-6)
    assert len(out.series) == 10
    assert out.series[-1].atr == pytest.approx(2.0, rel=1e-6)


@pytest.mark.asyncio
async def test_get_swing_pivots_returns_none_when_no_data():
    svc = _make_service()
    with patch.object(svc, "_fetch_historical_data", AsyncMock(return_value=None)):
        assert (await svc.get_swing_pivots("FPT")) is None


@pytest.mark.asyncio
async def test_get_swing_pivots_uppercases_and_passes_window():
    svc = _make_service()
    highs = [10, 12, 14, 16, 14, 12, 10, 8, 10, 12, 14, 16, 14, 12, 10]
    lows  = [ 9, 11, 13, 15, 13, 11,  9, 7,  9, 11, 13, 15, 13, 11,  9]
    df = _ohlc_df(highs, lows, closes=highs)
    with patch.object(svc, "_fetch_historical_data", AsyncMock(return_value=df)):
        out = await svc.get_swing_pivots("fpt", window=2, days=200)
    assert out is not None
    assert out.symbol == "FPT"
    assert out.window == 2
    assert len(out.pivots) >= 3


# ---------------------------------------------------------------------------
# F-003 typed S/R levels (road_map_version_11.xlsx)
# ---------------------------------------------------------------------------

from app.models.schemas import SRLevelType, SwingType as _SwingType  # noqa: E402


class TestSRClustering:
    def test_returns_empty_when_no_swing_pivots(self):
        """A monotonic series produces no fractal pivots → no S/R levels."""
        svc = _make_service()
        closes = np.arange(20, dtype=float)
        df = _ohlc_df(highs=closes + 1, lows=closes - 1, closes=closes)
        supports, resistances = svc._find_sr_levels(df, window=2)
        assert supports == []
        assert resistances == []

    def test_two_close_pivots_merge_into_one_level(self):
        """Two pivots within tolerance_pct of each other become a single level
        with strength=2."""
        svc = _make_service()
        # 15 bars with two clean low pivots: i=3 (price 100) and i=11 (price 101).
        # With window=2 the valid index range is [2, 12], so both are detectable.
        #          idx:  0    1    2    3    4    5    6    7    8    9   10   11   12   13   14
        highs = [110, 112, 110, 108, 110, 112, 110, 112, 110, 112, 110, 108, 110, 112, 110]
        lows  = [109, 111, 109, 100, 109, 111, 109, 111, 109, 111, 109, 101, 109, 111, 109]
        df = _ohlc_df(highs, lows, closes=lows)
        supports, _ = svc._find_sr_levels(df, window=2, tolerance_pct=2.0)
        assert len(supports) == 1
        lvl = supports[0]
        assert lvl.strength == 2
        assert lvl.type == SRLevelType.SUPPORT
        # Mean of 100 and 101 = 100.5
        assert lvl.price == pytest.approx(100.5, rel=1e-6)

    def test_two_distant_pivots_stay_separate(self):
        """Pivots farther apart than tolerance_pct stay as separate levels."""
        svc = _make_service()
        # 15 bars: pivot lows at i=3 (price 100) and i=11 (price 120). ~20% apart.
        highs = [110, 112, 110, 108, 110, 112, 110, 112, 110, 132, 130, 128, 130, 132, 130]
        lows  = [109, 111, 109, 100, 109, 111, 109, 111, 109, 131, 129, 120, 129, 131, 129]
        df = _ohlc_df(highs, lows, closes=lows)
        supports, _ = svc._find_sr_levels(df, window=2, tolerance_pct=2.0)
        # Two pivot lows at 100 and 120 → two separate levels.
        assert len(supports) == 2
        assert all(s.strength == 1 for s in supports)
        prices = sorted(s.price for s in supports)
        assert prices[0] == pytest.approx(100.0, rel=1e-6)
        assert prices[1] == pytest.approx(120.0, rel=1e-6)

    def test_age_bars_measures_distance_to_most_recent_touch(self):
        """age_bars = last_bar_index - max(bar_index in cluster)."""
        svc = _make_service()
        # One low at index 5 in a 13-bar series → age = 12 - 5 = 7
        highs = [110, 112, 114, 112, 110, 108, 110, 112, 114, 112, 110, 108, 110]
        lows  = [109, 111, 113, 111, 109, 100, 109, 111, 113, 111, 109, 107, 109]
        df = _ohlc_df(highs, lows, closes=lows)
        supports, _ = svc._find_sr_levels(df, window=2, tolerance_pct=2.0)
        # The low at i=5 (price 100) is far from i=11 (price 107) — won't cluster.
        s_at_100 = [s for s in supports if abs(s.price - 100.0) < 1.0]
        assert len(s_at_100) == 1
        assert s_at_100[0].age_bars == 12 - 5

    def test_flip_type_when_highs_and_lows_tie_in_cluster(self):
        """A cluster with equal high+low pivot counts is a FLIP level
        (price acted as both support and resistance — Ch 4 S/R flip)."""
        svc = _make_service()
        # Build a series where the SAME price is touched once as a high and
        # once as a low (i.e. price rejected at it from both sides).
        # High at i=3 (price 100), Low at i=9 (price 100) — both at value 100.
        highs = [98, 99, 100, 100, 100, 99, 98, 99, 100, 102, 100, 99, 98]
        lows  = [95, 96, 97, 99, 97, 96, 95, 96,  97, 100,  97, 96, 95]
        # Reshape: we want a clear high pivot at one index and a clear low
        # pivot at another, both at price ~100.
        highs = [99, 102, 105, 102, 99, 96, 99, 102, 103, 102, 99, 96, 99]
        lows  = [98, 101,  99, 101, 98, 95, 98, 101, 100, 101, 98, 95, 98]
        # High pivot at i=2 (high=105), low pivot at i=5 (low=95).
        # These are far apart in price → won't FLIP. Use a simpler approach:
        # construct pivots manually-friendly OHLC so both pivot types land at
        # similar prices.
        highs = [99, 100, 101, 100, 99,  98,  99, 100, 101, 100, 99]
        lows  = [98,  99,  99,  99, 98,  98,  98,  98, 100,  98, 98]
        # i=2: high=101 with neighbors max(100,100)=100 left and max(100,99)=100 right → high pivot at 101.
        # i=8: low=100 with neighbors min(98,98)=98 left and min(98,98)=98 right → NOT a low (100 > 98).
        # The math of FLIP is fragile to construct; assert FLIP via direct call
        # to the clustering on hand-built pivots instead.

        # Direct test: build two pivots (one high, one low) at identical price
        # and feed through clustering by stubbing _find_swing_pivots.
        from app.models.schemas import SwingPivot
        df = _ohlc_df(highs, lows, closes=lows)  # df shape only — content unused
        fake_pivots = [
            SwingPivot(bar_index=2, date="2026-01-03", type=_SwingType.HIGH, price=100.0),
            SwingPivot(bar_index=8, date="2026-01-09", type=_SwingType.LOW,  price=100.0),
        ]
        with patch.object(svc, "_find_swing_pivots", return_value=fake_pivots):
            supports, resistances = svc._find_sr_levels(df, window=2, tolerance_pct=2.0)
        # Tied counts (1 high, 1 low) → FLIP — appears in both lists.
        assert len(supports) == 1 and supports[0].type == SRLevelType.FLIP
        assert len(resistances) == 1 and resistances[0].type == SRLevelType.FLIP
        assert supports[0] is resistances[0] or supports[0].price == resistances[0].price

    def test_tolerance_pct_widens_clustering(self):
        """Same pivots, larger tolerance → fewer (merged) levels."""
        svc = _make_service()
        from app.models.schemas import SwingPivot
        df = _ohlc_df(highs=[1] * 10, lows=[1] * 10, closes=[1] * 10)  # shape only
        fake_pivots = [
            SwingPivot(bar_index=1, date="d", type=_SwingType.LOW, price=100.0),
            SwingPivot(bar_index=3, date="d", type=_SwingType.LOW, price=102.0),
            SwingPivot(bar_index=5, date="d", type=_SwingType.LOW, price=104.0),
        ]
        with patch.object(svc, "_find_swing_pivots", return_value=fake_pivots):
            tight, _ = svc._find_sr_levels(df, tolerance_pct=1.0)
            loose, _ = svc._find_sr_levels(df, tolerance_pct=5.0)
        # 1% tolerance: 100 vs 102 differ by 2% → don't merge → 3 levels.
        # 5% tolerance: all three within 5% of running mean → 1 level.
        assert len(tight) == 3
        assert len(loose) == 1
        assert loose[0].strength == 3


@pytest.mark.asyncio
async def test_get_sr_levels_returns_none_when_no_data():
    svc = _make_service()
    with patch.object(svc, "_fetch_historical_data", AsyncMock(return_value=None)):
        assert (await svc.get_sr_levels("FPT")) is None


@pytest.mark.asyncio
async def test_get_sr_levels_returns_typed_response():
    svc = _make_service()
    # 15 bars — two low pivots within 1% of each other.
    highs = [110, 112, 110, 108, 110, 112, 110, 112, 110, 112, 110, 108, 110, 112, 110]
    lows  = [109, 111, 109, 100, 109, 111, 109, 111, 109, 111, 109, 101, 109, 111, 109]
    df = _ohlc_df(highs, lows, closes=lows)
    with patch.object(svc, "_fetch_historical_data", AsyncMock(return_value=df)):
        out = await svc.get_sr_levels("fpt", window=2, tolerance_pct=2.0, days=200)
    assert out is not None
    assert out.symbol == "FPT"
    assert out.window == 2
    assert out.tolerance_pct == 2.0
    # The clustered support level (price ≈ 100.5) appears in supports.
    assert len(out.supports) >= 1
    assert any(s.strength == 2 for s in out.supports)


# ---------------------------------------------------------------------------
# F-004 regime feature vector (road_map_version_11.xlsx)
# ---------------------------------------------------------------------------

from app.models.schemas import (  # noqa: E402
    Regime, RegimeFeatures,
    SwingPivot as _SwingPivot,
    SwingType as _Sw,
)


class TestRegimeFeatureHelpers:
    def test_ma_slope_zero_when_series_too_short(self):
        svc = _make_service()
        prices = pd.Series([100.0] * 30)  # < ma_window + lookback
        assert svc._calculate_ma_slope(prices, ma_window=50, lookback=20) == 0.0

    def test_ma_slope_positive_on_linear_uptrend(self):
        """Linear close = 100 + 0.5*i → MA(50) climbs steadily; slope > 0."""
        svc = _make_service()
        prices = pd.Series([100 + 0.5 * i for i in range(120)])
        slope = svc._calculate_ma_slope(prices, ma_window=50, lookback=20)
        assert slope > 0.001  # above the default trend threshold

    def test_ma_slope_negative_on_linear_downtrend(self):
        svc = _make_service()
        prices = pd.Series([200 - 0.5 * i for i in range(120)])
        slope = svc._calculate_ma_slope(prices, ma_window=50, lookback=20)
        assert slope < -0.001

    def test_ma_slope_near_zero_on_flat_series(self):
        svc = _make_service()
        prices = pd.Series([100.0] * 120)
        slope = svc._calculate_ma_slope(prices, ma_window=50, lookback=20)
        assert slope == 0.0

    def test_count_hh_hl_zero_when_too_few_pivots(self):
        svc = _make_service()
        assert svc._count_hh_hl([]) == 0
        assert svc._count_hh_hl([_SwingPivot(
            bar_index=0, date="d", type=_Sw.HIGH, price=100,
        )]) == 0

    def test_count_hh_hl_positive_for_higher_highs_and_higher_lows(self):
        """HH + HL pattern: each new pivot beats the previous of its type."""
        svc = _make_service()
        pivots = [
            _SwingPivot(bar_index=0, date="d", type=_Sw.LOW,  price=100),
            _SwingPivot(bar_index=1, date="d", type=_Sw.HIGH, price=110),
            _SwingPivot(bar_index=2, date="d", type=_Sw.LOW,  price=105),  # HL → +1
            _SwingPivot(bar_index=3, date="d", type=_Sw.HIGH, price=115),  # HH → +1
            _SwingPivot(bar_index=4, date="d", type=_Sw.LOW,  price=108),  # HL → +1
            _SwingPivot(bar_index=5, date="d", type=_Sw.HIGH, price=120),  # HH → +1
        ]
        assert svc._count_hh_hl(pivots) == 4

    def test_count_hh_hl_negative_for_lower_highs_and_lower_lows(self):
        svc = _make_service()
        pivots = [
            _SwingPivot(bar_index=0, date="d", type=_Sw.HIGH, price=120),
            _SwingPivot(bar_index=1, date="d", type=_Sw.LOW,  price=110),
            _SwingPivot(bar_index=2, date="d", type=_Sw.HIGH, price=115),  # LH → -1
            _SwingPivot(bar_index=3, date="d", type=_Sw.LOW,  price=105),  # LL → -1
            _SwingPivot(bar_index=4, date="d", type=_Sw.HIGH, price=112),  # LH → -1
            _SwingPivot(bar_index=5, date="d", type=_Sw.LOW,  price=100),  # LL → -1
        ]
        assert svc._count_hh_hl(pivots) == -4

    def test_adx_strong_on_clean_linear_uptrend(self):
        """A pure linear uptrend has all +DM and no -DM → ADX climbs high."""
        svc = _make_service()
        n = 80
        closes = np.array([100 + 0.5 * i for i in range(n)], dtype=float)
        df = _ohlc_df(highs=closes + 1, lows=closes - 1, closes=closes)
        adx = svc._calculate_adx(df, period=14)
        assert adx > 25

    def test_adx_low_on_flat_series(self):
        """No directional movement → no +DM/-DM accumulation → ADX ≈ 0."""
        svc = _make_service()
        n = 80
        df = _ohlc_df(highs=[101.0] * n, lows=[99.0] * n, closes=[100.0] * n)
        adx = svc._calculate_adx(df, period=14)
        # Flat series — ADX may be 0 or NaN-fallback-to-0.
        assert adx < 5

    def test_range_atr_ratio_zero_when_atr_zero(self):
        svc = _make_service()
        df = _ohlc_df(highs=[101.0] * 30, lows=[99.0] * 30, closes=[100.0] * 30)
        assert svc._range_atr_ratio(df, atr=0.0, lookback=20) == 0.0

    def test_range_atr_ratio_grows_with_trend(self):
        """Linear trend over N bars gives band ≈ N * drift; ATR ≈ drift+noise.
        So ratio ≈ N for a clean trend, much smaller for sideways noise."""
        svc = _make_service()
        n = 60
        trend = np.array([100 + 1.0 * i for i in range(n)], dtype=float)
        df_trend = _ohlc_df(highs=trend + 1, lows=trend - 1, closes=trend)
        atr_trend = svc._calculate_atr(df_trend, period=14).dropna().iloc[-1]
        ratio_trend = svc._range_atr_ratio(df_trend, atr=float(atr_trend), lookback=20)
        # 20 bars of drift=1 → band ≈ 21, atr ≈ 2 → ratio ≈ 10+
        assert ratio_trend > 5


class TestClassifyRegime:
    def test_trend_when_strong_slope_high_adx_matching_structure(self):
        svc = _make_service()
        features = RegimeFeatures(
            slope=0.005,         # well above 0.001
            hh_hl_count=4,       # uptrend structure agrees with positive slope
            adx=40.0,            # well above 20
            range_atr_ratio=15.0,
        )
        regime, confidence = svc._classify_regime(features)
        assert regime == Regime.TREND
        assert 0.0 < confidence <= 1.0

    def test_trend_negative_direction(self):
        svc = _make_service()
        features = RegimeFeatures(
            slope=-0.005, hh_hl_count=-4, adx=40.0, range_atr_ratio=15.0,
        )
        regime, _ = svc._classify_regime(features)
        assert regime == Regime.TREND

    def test_undefined_when_slope_and_structure_disagree(self):
        """Slope says up but HH/HL says down — conflicting signals → UNDEFINED."""
        svc = _make_service()
        features = RegimeFeatures(
            slope=0.005, hh_hl_count=-3, adx=40.0, range_atr_ratio=15.0,
        )
        regime, confidence = svc._classify_regime(features)
        assert regime == Regime.UNDEFINED
        assert confidence == 0.0

    def test_range_when_flat_slope_low_adx_narrow_band(self):
        svc = _make_service()
        features = RegimeFeatures(
            slope=0.0001, hh_hl_count=0, adx=12.0, range_atr_ratio=5.0,
        )
        regime, confidence = svc._classify_regime(features)
        assert regime == Regime.RANGE
        assert 0.0 < confidence <= 1.0

    def test_undefined_when_neither_trend_nor_range(self):
        """Moderate slope, moderate ADX, wide band — falls in the gap."""
        svc = _make_service()
        features = RegimeFeatures(
            slope=0.0005,        # below trend threshold
            hh_hl_count=1,
            adx=22.0,            # above range threshold
            range_atr_ratio=20.0,
        )
        regime, confidence = svc._classify_regime(features)
        assert regime == Regime.UNDEFINED
        assert confidence == 0.0


@pytest.mark.asyncio
async def test_get_regime_returns_none_when_no_data():
    svc = _make_service()
    with patch.object(svc, "_fetch_historical_data", AsyncMock(return_value=None)):
        assert (await svc.get_regime("FPT")) is None


@pytest.mark.asyncio
async def test_get_regime_returns_none_when_history_too_short():
    """Need at least ma_window + lookback bars to compute the slope feature."""
    svc = _make_service()
    short = _ohlc_df(highs=[101.0] * 40, lows=[99.0] * 40, closes=[100.0] * 40)
    with patch.object(svc, "_fetch_historical_data", AsyncMock(return_value=short)):
        assert (await svc.get_regime("FPT", ma_window=50, lookback=20)) is None


@pytest.mark.asyncio
async def test_get_regime_classifies_clean_uptrend_as_trend():
    svc = _make_service()
    n = 200
    closes = np.array([100 + 0.5 * i for i in range(n)], dtype=float)
    df = _ohlc_df(highs=closes + 1, lows=closes - 1, closes=closes)
    with patch.object(svc, "_fetch_historical_data", AsyncMock(return_value=df)):
        out = await svc.get_regime("fpt")
    assert out is not None
    assert out.symbol == "FPT"
    assert out.regime == Regime.TREND
    assert out.features.slope > 0
    assert out.features.adx > 20
    assert out.confidence > 0


@pytest.mark.asyncio
async def test_get_regime_classifies_flat_series_as_range():
    """A perfectly flat series has zero slope, zero ADX, narrow band → RANGE."""
    svc = _make_service()
    n = 200
    df = _ohlc_df(highs=[101.0] * n, lows=[99.0] * n, closes=[100.0] * n)
    with patch.object(svc, "_fetch_historical_data", AsyncMock(return_value=df)):
        out = await svc.get_regime("FPT")
    assert out is not None
    assert out.regime == Regime.RANGE
    assert out.features.slope == 0.0
    assert out.features.adx < 20


@pytest.mark.asyncio
async def test_get_regime_returns_undefined_when_data_lacks_ohlc_columns():
    svc = _make_service()
    bad = pd.DataFrame({
        "date": pd.date_range("2026-01-01", periods=120, freq="D"),
        "close": [100.0] * 120,
    })
    with patch.object(svc, "_fetch_historical_data", AsyncMock(return_value=bad)):
        assert (await svc.get_regime("FPT")) is None


def test_find_support_resistance_returns_plain_number_lists():
    """Regression guard: whatever the detection strategy, the output shape
    TechnicalAnalysisResponse.support_levels / resistance_levels relies on is
    two lists of plain numbers (they are rounded and JSON-serialised)."""
    svc = _make_service()
    ohlc = _ohlc_from_closes([
        100, 102, 105, 102, 100,
        98, 95, 92, 95, 98,
        101, 104, 107, 104, 101,
    ])
    supports, resistances = svc._find_support_resistance(ohlc, current_price=100.0)
    assert isinstance(supports, list) and isinstance(resistances, list)
    assert all(isinstance(s, (int, float)) for s in supports)
    assert all(isinstance(r, (int, float)) for r in resistances)
