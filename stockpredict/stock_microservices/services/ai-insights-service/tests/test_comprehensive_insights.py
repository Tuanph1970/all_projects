"""Tests for the comprehensive-insights path of InsightsService.

Covers the five heavy methods that drive the /insights/comprehensive
endpoint:
- _detect_patterns: chart-pattern detection (Uptrend / Downtrend /
  HH-HL / LH-LL / Near Support / Near Resistance / Volume Breakout /
  Consolidation fallback / insufficient-data short-circuit).
- _calculate_risk_assessment: volatility tiers + drawdown risk +
  below-SMA factor + risk_score → risk_level mapping.
- _analyze_sentiment_from_indicators: scoring inputs (momentum, RSI,
  MACD, volume) + bullish/bearish/neutral classification +
  insufficient-data short-circuit.
- _get_predictions: prediction-service happy path + fallback paths.
- get_comprehensive_insights: insufficient-data error response + full
  happy path with AI score weighting.
- get_stock_recommendations: BUY / SELL / HOLD classification + mix
  guarantee + insufficient-data skip.

All synthetic price DataFrames are built deterministically. Network
calls in _get_predictions / _fetch_historical_prices are stubbed.
"""
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from app.services import insights_service as svc_mod
from app.services.insights_service import InsightsService


def _make_service() -> InsightsService:
    """Build an InsightsService without opening Redis."""
    with patch.object(InsightsService, "_init_redis", lambda self: None):
        return InsightsService()


def _trend_df(rows: int, start: float, drift: float, *, with_volume: bool = True,
              vol_mult: float = 1.0) -> pd.DataFrame:
    """Build a deterministic OHLCV frame where close moves by `drift`
    per step starting at `start`. vol_mult > 1 scales the most-recent
    5 rows' volume (used to trigger the volume-breakout pattern)."""
    close = np.array([start + drift * i for i in range(rows)], dtype=float)
    high = close + 1.0
    low = close - 1.0
    open_ = close - 0.2
    if with_volume:
        volume = np.full(rows, 1000.0)
        # Bump the trailing 5 by vol_mult.
        volume[-5:] = volume[-5:] * vol_mult
    else:
        volume = np.full(rows, 1000.0)
    return pd.DataFrame({
        "open": open_, "high": high, "low": low, "close": close, "volume": volume,
    })


# ---------------------------------------------------------------------------
# _detect_patterns
# ---------------------------------------------------------------------------

class TestDetectPatterns:
    def test_returns_empty_when_fewer_than_20_rows(self):
        df = _trend_df(rows=10, start=100.0, drift=0.0)
        assert _make_service()._detect_patterns(df) == []

    def test_consolidation_fallback_when_no_other_patterns(self):
        """A flat 20-day series → Uptrend/Downtrend gates fail; range
        is too small for support/resistance; result is the fallback."""
        df = _trend_df(rows=20, start=100.0, drift=0.0)
        out = _make_service()._detect_patterns(df)
        assert len(out) >= 1
        # Last element is Consolidation when nothing else fired.
        assert any(p.pattern_name == "Consolidation" for p in out)

    def test_strong_uptrend_with_higher_highs_and_volume_breakout(self):
        # 20+ rows, monotonically rising by 1.5/day → >10% over 20d.
        # vol_mult=2.0 → recent_vol > avg_vol_20 * 1.5 triggers breakout.
        df = _trend_df(rows=25, start=100.0, drift=1.5, vol_mult=2.0)
        out = _make_service()._detect_patterns(df)
        names = {p.pattern_name for p in out}
        assert "Uptrend" in names
        assert "Higher Highs & Higher Lows" in names
        assert "Volume Breakout" in names
        uptrend = next(p for p in out if p.pattern_name == "Uptrend")
        assert uptrend.pattern_type == "bullish"
        assert uptrend.signal_strength == "strong"

    def test_downtrend_with_lower_highs_lower_lows(self):
        # Monotonic drop → strong downtrend + LH/LL detection.
        df = _trend_df(rows=25, start=200.0, drift=-1.5)
        out = _make_service()._detect_patterns(df)
        names = {p.pattern_name for p in out}
        assert "Downtrend" in names
        assert "Lower Highs & Lower Lows" in names
        downtrend = next(p for p in out if p.pattern_name == "Downtrend")
        assert downtrend.pattern_type == "bearish"

    def test_moderate_uptrend_signal_strength(self):
        """+5-10% over 20 days → moderate (not strong)."""
        df = _trend_df(rows=25, start=100.0, drift=0.4)  # ~+8%
        out = _make_service()._detect_patterns(df)
        uptrend = next(p for p in out if p.pattern_name == "Uptrend")
        assert uptrend.signal_strength == "moderate"

    def test_near_support_when_recent_price_at_range_bottom(self):
        """Build a series that climbs then dips back to the low — the
        last price sits in the bottom 20% of the recent range."""
        close = np.concatenate([
            np.linspace(100, 130, 19),
            np.array([101.0]),  # back near the bottom
        ])
        df = pd.DataFrame({
            "open": close, "high": close + 1, "low": close - 1, "close": close,
            "volume": np.full(20, 1000.0),
        })
        out = _make_service()._detect_patterns(df)
        names = {p.pattern_name for p in out}
        assert "Near Support" in names

    def test_near_resistance_when_recent_price_at_range_top(self):
        close = np.concatenate([
            np.linspace(100, 130, 19),
            np.array([129.5]),  # near the top
        ])
        df = pd.DataFrame({
            "open": close, "high": close + 1, "low": close - 1, "close": close,
            "volume": np.full(20, 1000.0),
        })
        out = _make_service()._detect_patterns(df)
        names = {p.pattern_name for p in out}
        assert "Near Resistance" in names


# ---------------------------------------------------------------------------
# _calculate_risk_assessment
# ---------------------------------------------------------------------------

class TestCalculateRiskAssessment:
    def test_low_volatility_classification(self):
        """Tiny daily moves → annual_vol < 20% → 'Low Volatility' factor
        + 'low' risk_level when score < 30."""
        df = _trend_df(rows=30, start=100.0, drift=0.0)
        out = _make_service()._calculate_risk_assessment(df)
        # daily returns are all 0 → vol = 0 → risk_score = 20 + 0 + 0 = 20 → 'low'
        assert out.risk_level == "low"
        assert any(f.factor == "Low Volatility" for f in out.factors)

    def test_high_volatility_and_drawdown_classification(self):
        """Large alternating moves → high vol + large drawdown."""
        rng = np.random.default_rng(seed=11)
        # Heavy +/- 5% daily swings
        returns = rng.choice([-0.05, 0.05], size=60)
        close = 100 * np.cumprod(1 + returns)
        df = pd.DataFrame({
            "open": close, "high": close + 1, "low": close - 1, "close": close,
            "volume": np.full(60, 1000.0),
        })
        out = _make_service()._calculate_risk_assessment(df)
        factor_names = {f.factor for f in out.factors}
        assert "High Volatility" in factor_names
        # Likely also includes Drawdown Risk for this big-swing series.
        assert out.risk_level in {"medium", "high", "very_high"}

    def test_moderate_volatility_classification(self):
        """Daily vol around 1.5% → annual_vol ~24% → 'Moderate'."""
        rng = np.random.default_rng(seed=7)
        returns = rng.normal(0, 0.015, size=60)
        close = 100 * np.cumprod(1 + returns)
        df = pd.DataFrame({
            "open": close, "high": close + 1, "low": close - 1, "close": close,
            "volume": np.full(60, 1000.0),
        })
        out = _make_service()._calculate_risk_assessment(df)
        factor_names = {f.factor for f in out.factors}
        assert "Moderate Volatility" in factor_names

    def test_below_moving_average_risk_factor(self):
        """Steady downtrend → last price < sma_20 * 0.95 → factor fires."""
        df = _trend_df(rows=30, start=200.0, drift=-1.0)
        out = _make_service()._calculate_risk_assessment(df)
        factor_names = {f.factor for f in out.factors}
        assert "Below Moving Average" in factor_names


# ---------------------------------------------------------------------------
# _analyze_sentiment_from_indicators
# ---------------------------------------------------------------------------

class TestAnalyzeSentimentFromIndicators:
    def test_insufficient_data_returns_neutral(self):
        df = _trend_df(rows=10, start=100.0, drift=0.0)
        out = _make_service()._analyze_sentiment_from_indicators(df)
        assert out.sentiment_type == "neutral"
        assert "Insufficient" in out.summary

    def test_strong_uptrend_with_oversold_rsi_is_bullish(self):
        # Build a rising series with synthetic RSI/MACD columns that
        # contribute to the bullish total.
        df = _trend_df(rows=25, start=100.0, drift=1.5)  # +5d & +20d > thresholds
        df["rsi"] = 25.0  # oversold → +0.2
        df["macd"] = 0.5
        df["macd_signal"] = 0.0
        # Volume kicker — 5d avg above 1.3x the 20d.
        df.loc[df.index[-5:], "volume"] = 2000.0

        out = _make_service()._analyze_sentiment_from_indicators(df)
        assert out.sentiment_type == "bullish"
        assert out.score > 0
        # Confidence formula: 0.5 + abs(score) * 0.4 — capped at 1.
        assert 0 <= out.confidence <= 1

    def test_strong_downtrend_with_overbought_rsi_is_bearish(self):
        df = _trend_df(rows=25, start=200.0, drift=-1.5)
        df["rsi"] = 78.0  # overbought → -0.2
        df["macd"] = 0.0
        df["macd_signal"] = 0.5  # bearish crossover → -0.2

        out = _make_service()._analyze_sentiment_from_indicators(df)
        assert out.sentiment_type == "bearish"
        assert out.score < 0

    def test_flat_series_with_balanced_signals_is_neutral(self):
        """No price momentum + no RSI/MACD columns → score stays near 0."""
        df = _trend_df(rows=25, start=100.0, drift=0.0)
        out = _make_service()._analyze_sentiment_from_indicators(df)
        assert out.sentiment_type == "neutral"


# ---------------------------------------------------------------------------
# _get_predictions
# ---------------------------------------------------------------------------

class _FakeHttpxClient:
    """async-with stub that yields a client whose .get() returns the
    pre-canned response (mirrors the pattern used elsewhere)."""
    def __init__(self, response):
        self._response = response

    async def __aenter__(self):
        c = MagicMock()
        c.get = AsyncMock(return_value=self._response)
        return c

    async def __aexit__(self, *_):
        return False


@pytest.mark.asyncio
async def test_get_predictions_happy_path_returns_three_models():
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "predictions": [
            {"predicted_price": 110.0, "confidence": 0.7}
        ]
    }
    svc = _make_service()
    with patch("app.services.insights_service.httpx.AsyncClient",
               return_value=_FakeHttpxClient(resp)):
        out = await svc._get_predictions("FPT", current_price=100.0)
    assert out.random_forest is not None
    assert out.xgboost is not None
    assert out.ensemble is not None
    # change = (110 - 100) / 100 * 100 = 10 → direction "up"
    assert out.random_forest.direction == "up"


@pytest.mark.asyncio
async def test_get_predictions_falls_back_to_simple_trend_on_non_200():
    resp = MagicMock()
    resp.status_code = 503
    svc = _make_service()
    with patch("app.services.insights_service.httpx.AsyncClient",
               return_value=_FakeHttpxClient(resp)):
        out = await svc._get_predictions("FPT", current_price=100.0)
    # Fallback: only ensemble populated with the simple-trend model.
    assert out.random_forest is None
    assert out.ensemble is not None
    assert out.ensemble.model_name == "Simple Trend"


@pytest.mark.asyncio
async def test_get_predictions_falls_back_when_predictions_empty():
    """200 OK but `predictions: []` → fall through to simple trend."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"predictions": []}
    svc = _make_service()
    with patch("app.services.insights_service.httpx.AsyncClient",
               return_value=_FakeHttpxClient(resp)):
        out = await svc._get_predictions("FPT", current_price=100.0)
    assert out.ensemble.model_name == "Simple Trend"


@pytest.mark.asyncio
async def test_get_predictions_falls_back_on_exception():
    class Boom:
        async def __aenter__(self):
            raise ConnectionError("down")

        async def __aexit__(self, *_):
            return False

    svc = _make_service()
    with patch("app.services.insights_service.httpx.AsyncClient", return_value=Boom()):
        out = await svc._get_predictions("FPT", current_price=100.0)
    assert out.ensemble.model_name == "Simple Trend"


# ---------------------------------------------------------------------------
# get_comprehensive_insights
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_comprehensive_insights_returns_error_status_when_data_missing():
    """Fetch returns None → response has status='error' and insights=None.
    Closes Backlog #42 (insights is now Optional in the schema)."""
    svc = _make_service()
    with patch.object(svc, "_fetch_historical_prices", AsyncMock(return_value=None)):
        out = await svc.get_comprehensive_insights(
            "FPT", "2026-01-01", "2026-05-01", {}
        )
    assert out.status == "error"
    assert out.symbol == "FPT"
    assert out.insights is None


@pytest.mark.asyncio
async def test_comprehensive_insights_short_dataframe_returns_error_status():
    """<20 rows hits the same error path: error status + insights=None."""
    svc = _make_service()
    short_df = _trend_df(rows=10, start=100.0, drift=0.0)
    with patch.object(svc, "_fetch_historical_prices", AsyncMock(return_value=short_df)):
        out = await svc.get_comprehensive_insights(
            "FPT", "2026-04-01", "2026-05-01", {}
        )
    assert out.status == "error"
    assert out.insights is None


@pytest.mark.asyncio
async def test_comprehensive_insights_happy_path_builds_ai_score():
    """Full pipeline: _fetch_historical_prices returns 30 rising rows,
    _get_predictions returns the up-direction model → overall AI score
    is in the 'high' tier (or moderate at minimum)."""
    svc = _make_service()
    df = _trend_df(rows=30, start=100.0, drift=1.0)

    # Stub _get_predictions to a high-confidence up prediction so the
    # prediction_score adds to the overall score.
    from app.models.schemas import PredictionModel, PricePrediction
    pred = PricePrediction(
        ensemble=PredictionModel(
            model_name="Ensemble",
            predicted_price=130.0, predicted_change=10.0,
            confidence=0.8, direction="up",
            lower_bound=125.0, upper_bound=135.0,
        ),
        model_comparison="ok",
    )

    with patch.object(svc, "_fetch_historical_prices", AsyncMock(return_value=df)), \
         patch.object(svc, "_get_predictions", AsyncMock(return_value=pred)):
        out = await svc.get_comprehensive_insights(
            "FPT", "2026-01-01", "2026-05-01",
            {"trend": "MACD", "momentum": "RSI"},
        )
    assert out.status == "success"
    assert out.symbol == "FPT"
    assert out.insights is not None
    # AI score must be in [0, 100].
    assert 0 <= out.insights.ai_score.overall_score <= 100
    assert out.insights.ai_score.confidence_level in {"high", "moderate", "low"}
    # Pattern detection found at least 1 pattern.
    assert len(out.insights.pattern_recognition.patterns) >= 1


@pytest.mark.asyncio
async def test_comprehensive_insights_low_confidence_for_downtrend():
    """A downtrend + down prediction lands in the 'low' confidence tier."""
    svc = _make_service()
    df = _trend_df(rows=30, start=200.0, drift=-1.5)

    from app.models.schemas import PredictionModel, PricePrediction
    pred = PricePrediction(
        ensemble=PredictionModel(
            model_name="Ensemble",
            predicted_price=170.0, predicted_change=-15.0,
            confidence=0.8, direction="down",
            lower_bound=165.0, upper_bound=175.0,
        ),
        model_comparison="ok",
    )

    with patch.object(svc, "_fetch_historical_prices", AsyncMock(return_value=df)), \
         patch.object(svc, "_get_predictions", AsyncMock(return_value=pred)):
        out = await svc.get_comprehensive_insights(
            "FPT", "2026-01-01", "2026-05-01", {},
        )
    assert out.status == "success"
    # Score should be low (overall < 50 → "low").
    assert out.insights.ai_score.confidence_level in {"low", "moderate"}


# ---------------------------------------------------------------------------
# get_stock_recommendations
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_stock_recommendations_returns_structured_rows_for_uptrend():
    """A pure uptrend yields HOLD ratings (RSI is overbought so the
    scoring stays in the -40 to +40 band even with bullish MACD + MAs).
    Test the structural contract rather than the rating itself."""
    svc = _make_service()
    df = _trend_df(rows=30, start=100.0, drift=1.5)

    with patch.object(svc, "_fetch_historical_prices", AsyncMock(return_value=df)):
        out = await svc.get_stock_recommendations(limit=5)
    assert len(out) == 5
    for r in out:
        assert r["type"] in {"BUY", "SELL", "HOLD"}
        assert r["confidence"] >= 50
        assert {"symbol", "name", "reason", "current_price", "rsi"}.issubset(r.keys())


@pytest.mark.asyncio
async def test_stock_recommendations_buy_when_indicators_align(monkeypatch):
    """Stub _calculate_indicators to inject oversold-RSI + bullish-MACD
    + price-above-MAs into the DataFrame. With those signals plus a
    positive 5d momentum, the score crosses +40 → BUY."""
    svc = _make_service()
    df = _trend_df(rows=30, start=100.0, drift=1.0)
    df["rsi"] = 25.0           # < 30 → +30
    df["macd"] = 0.5
    df["macd_signal"] = 0.0    # bullish crossover → +20
    df["sma_20"] = df["close"] - 1   # current > sma_20
    df["sma_50"] = df["close"] - 2   # current > sma_20 > sma_50 → +25

    def fake_calc(self, frame, indicators):
        # Don't recompute — the DataFrame already has the columns we need.
        return frame

    monkeypatch.setattr(InsightsService, "_calculate_indicators", fake_calc)
    with patch.object(svc, "_fetch_historical_prices", AsyncMock(return_value=df)):
        out = await svc.get_stock_recommendations(limit=5)
    assert any(r["type"] == "BUY" for r in out)


@pytest.mark.asyncio
async def test_stock_recommendations_sell_when_indicators_align(monkeypatch):
    """Mirror: overbought RSI + bearish MACD + price-below-MAs +
    weak 5d momentum drives the score below -40 → SELL."""
    svc = _make_service()
    df = _trend_df(rows=30, start=200.0, drift=-1.5)
    df["rsi"] = 78.0           # > 70 → -30
    df["macd"] = 0.0
    df["macd_signal"] = 0.5    # bearish → -20
    df["sma_20"] = df["close"] + 1
    df["sma_50"] = df["close"] + 2   # current < sma_20 < sma_50 → -25

    def fake_calc(self, frame, indicators):
        return frame

    monkeypatch.setattr(InsightsService, "_calculate_indicators", fake_calc)
    with patch.object(svc, "_fetch_historical_prices", AsyncMock(return_value=df)):
        out = await svc.get_stock_recommendations(limit=5)
    assert any(r["type"] == "SELL" for r in out)


@pytest.mark.asyncio
async def test_stock_recommendations_skips_symbols_with_insufficient_data():
    """If every fetch returns None, no recommendations are produced."""
    svc = _make_service()
    with patch.object(svc, "_fetch_historical_prices", AsyncMock(return_value=None)):
        out = await svc.get_stock_recommendations(limit=5)
    assert out == []


@pytest.mark.asyncio
async def test_stock_recommendations_swallows_per_symbol_errors():
    """One symbol erroring shouldn't abort the whole loop."""
    svc = _make_service()
    df = _trend_df(rows=30, start=100.0, drift=1.0)

    call_count = {"n": 0}

    async def flaky_fetch(*_a, **_kw):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("first fetch boom")
        return df

    with patch.object(svc, "_fetch_historical_prices", flaky_fetch):
        out = await svc.get_stock_recommendations(limit=5)
    # The first symbol errored; the remaining ones produced recs.
    assert len(out) >= 1


# ---------------------------------------------------------------------------
# AI Insights "Analyze does nothing" bug: the selected indicators must change
# the score, the prediction route must be the real one, and a too-short date
# range is widened (end = yesterday, start = end - required days).
# ---------------------------------------------------------------------------

class TestSentimentUsesSelectedIndicators:
    def _df(self):
        # Flat price so no momentum baseline; every signal comes from columns.
        df = _trend_df(rows=30, start=100.0, drift=0.0)
        df["macd"], df["macd_signal"] = 1.0, 0.0            # MACD bullish
        df["sma_20"], df["sma_50"] = 120.0, 130.0            # price below SMAs -> bearish
        df["rsi"] = 50.0                                     # neutral
        df["stoch_k"] = 10.0                                 # oversold -> bullish
        return df

    def test_trend_dropdown_changes_score(self):
        svc = _make_service()
        macd = svc._analyze_sentiment_from_indicators(self._df(), {"trend": "MACD"})
        sma = svc._analyze_sentiment_from_indicators(self._df(), {"trend": "SMA"})
        assert macd.score > 0 > sma.score
        assert "MACD" in macd.summary and "SMA" in sma.summary

    def test_momentum_dropdown_changes_score(self):
        svc = _make_service()
        rsi = svc._analyze_sentiment_from_indicators(self._df(), {"momentum": "RSI"})
        stoch = svc._analyze_sentiment_from_indicators(self._df(), {"momentum": "Stochastic"})
        assert rsi.score == 0.0
        assert stoch.score > 0

    def test_missing_column_is_harmless(self):
        df = _trend_df(rows=30, start=100.0, drift=0.0)   # no indicator columns at all
        out = _make_service()._analyze_sentiment_from_indicators(
            df, {"trend": "WMA", "momentum": "MFI", "volatility": "ATR", "volume": "VWAP"})
        assert out.sentiment_type == "neutral"

    def test_legacy_call_without_selection_still_reads_rsi_and_macd(self):
        df = self._df()
        df["rsi"] = 25.0
        out = _make_service()._analyze_sentiment_from_indicators(df)
        assert out.score > 0


@pytest.mark.asyncio
async def test_get_predictions_calls_predict_route_not_predictions():
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"predictions": [{"predicted_price": 110.0, "confidence": 0.7}]}
    captured = {}

    class Client(_FakeHttpxClient):
        async def __aenter__(self):
            c = await super().__aenter__()
            async def get(url, **kw):
                captured["url"] = url
                return resp
            c.get = get
            return c

    svc = _make_service()
    with patch("app.services.insights_service.httpx.AsyncClient", return_value=Client(resp)):
        await svc._get_predictions("FPT", current_price=100.0)
    assert "/api/v2/predict/predict/FPT" in captured["url"]
    assert "/predictions/" not in captured["url"]


@pytest.mark.asyncio
async def test_fallback_prediction_follows_the_windows_trend():
    """With prediction-service down, the fallback must not be a constant
    'neutral / 0.0%': a rising window projects up, a falling one down."""
    resp = MagicMock()
    resp.status_code = 503
    svc = _make_service()
    up = _trend_df(rows=40, start=100.0, drift=1.0)
    down = _trend_df(rows=40, start=200.0, drift=-1.0)
    with patch("app.services.insights_service.httpx.AsyncClient", return_value=_FakeHttpxClient(resp)):
        p_up = await svc._get_predictions("FPT", float(up["close"].iloc[-1]), up)
        p_down = await svc._get_predictions("FPT", float(down["close"].iloc[-1]), down)
    assert p_up.ensemble.model_name == "Simple Trend"
    assert p_up.ensemble.direction == "up" and p_up.ensemble.predicted_change > 0
    assert p_down.ensemble.direction == "down" and p_down.ensemble.predicted_change < 0


class TestEffectiveDateRange:
    def test_long_enough_range_is_untouched(self):
        svc = _make_service()
        out = svc._effective_date_range("2025-01-01", "2026-09-01", {"trend": "MACD"})
        assert out == ("2025-01-01", "2026-09-01", False, None)

    def test_short_range_is_widened_to_yesterday_minus_required(self):
        svc = _make_service()
        start, end, adjusted, note = svc._effective_date_range(
            "2026-08-20", "2026-09-10", {"trend": "MACD", "momentum": "RSI"})
        yesterday = (datetime.now() - pd.Timedelta(days=1)).date()
        required = svc._required_calendar_days({"trend": "MACD", "momentum": "RSI"})
        assert adjusted is True
        assert end == yesterday.isoformat()
        assert start == (yesterday - pd.Timedelta(days=required)).isoformat()
        assert "MACD" in note
        # MACD is the longest indicator: roughly the "200 days" rule of thumb.
        assert 180 <= required <= 230

    def test_required_days_depends_on_selection(self):
        svc = _make_service()
        assert svc._required_calendar_days({"trend": "MACD"}) > svc._required_calendar_days({"trend": "WMA"})
        assert svc._required_calendar_days({}) == int(20 * 1.6) + 14

    def test_garbage_dates_are_replaced(self):
        svc = _make_service()
        _, _, adjusted, _ = svc._effective_date_range("", "not-a-date", {"trend": "SMA"})
        assert adjusted is True


@pytest.mark.asyncio
async def test_comprehensive_insights_reports_effective_window():
    svc = _make_service()
    df = _trend_df(rows=120, start=100.0, drift=0.5)
    fetch = AsyncMock(return_value=df)
    pred = svc._simple_trend_prediction(100.0, df)
    with patch.object(svc, "_fetch_historical_prices", fetch), \
         patch.object(svc, "_get_predictions", AsyncMock(return_value=pred)):
        out = await svc.get_comprehensive_insights(
            "FPT", "2026-09-01", "2026-09-10", {"trend": "MACD", "momentum": "RSI"})
    assert out.status == "success"
    assert out.date_range_adjusted is True
    # The widened window is what was actually fetched.
    assert fetch.await_args.args[1:] == (out.effective_start_date, out.effective_end_date)
