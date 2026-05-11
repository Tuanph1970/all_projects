"""Tests for the /insights/indicators and /insights/comprehensive routes.

These endpoints were never exercised by the existing suite, so the
formatter logic that wraps the InsightsService output for the frontend
was uncovered (routes.py lines 286-320, 337-357, 382-391). Each test
mocks InsightsService to return a canned schema response so we
verify the response-shaping, not the service internals.
"""
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.models.schemas import (
    AIScoreComponent,
    AvailableIndicatorsResponse,
    ComprehensiveInsights,
    ComprehensiveInsightsResponse,
    IndicatorCategory,
    IndicatorDataPoint,
    IndicatorDataResponse,
    PatternRecognition,
    PricePrediction,
    RiskAssessment,
    SentimentAnalysis,
)


PREFIX = "/stock_helper/api/v2/ai"


# ---------------------------------------------------------------------------
# /insights/indicators/available
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_available_indicators_wraps_categories_with_descriptions(client: AsyncClient):
    """Response should attach a human-readable description to each
    indicator (frontend renders these in the indicator picker)."""
    canned = AvailableIndicatorsResponse(
        categories=[
            IndicatorCategory(category="trend", indicators=["MACD", "EMA"], description="Trend indicators"),
            IndicatorCategory(category="momentum", indicators=["RSI"], description="Momentum"),
        ],
        total_indicators=3,
    )
    with patch("app.api.routes.InsightsService") as MockService:
        MockService.return_value.get_available_indicators = MagicMock(return_value=canned)
        r = await client.get(f"{PREFIX}/insights/indicators/available")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "success"
        by_cat = body["data"]["indicators_by_category"]
        assert by_cat["trend"][0]["name"] == "MACD"
        # The route enriches known indicators; MACD has a known description.
        assert "Moving Average" in by_cat["trend"][0]["description"]
        assert body["data"]["total_indicators"] == 3


@pytest.mark.asyncio
async def test_available_indicators_passes_through_unknown_indicator_name(client: AsyncClient):
    """Unknown indicators fall back to using the name as description."""
    canned = AvailableIndicatorsResponse(
        categories=[
            IndicatorCategory(category="custom", indicators=["XYZ"], description="Custom"),
        ],
        total_indicators=1,
    )
    with patch("app.api.routes.InsightsService") as MockService:
        MockService.return_value.get_available_indicators = MagicMock(return_value=canned)
        r = await client.get(f"{PREFIX}/insights/indicators/available")
        assert r.status_code == 200
        assert r.json()["data"]["indicators_by_category"]["custom"][0]["description"] == "XYZ"


# ---------------------------------------------------------------------------
# /insights/indicators/data
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_indicator_data_attaches_indicator_metadata(client: AsyncClient):
    """When the request specifies indicators per category, the response
    should include an `indicators` metadata dict for chart-panel rendering."""
    canned = IndicatorDataResponse(
        status="success",
        symbol="FPT",
        data=[
            IndicatorDataPoint(
                date="2026-05-01", open=1.0, high=2.0, low=0.5, close=1.5, volume=100, macd=0.1
            )
        ],
        count=1,
    )
    with patch("app.api.routes.InsightsService") as MockService:
        MockService.return_value.get_indicator_data = AsyncMock(return_value=canned)
        r = await client.post(
            f"{PREFIX}/insights/indicators/data",
            json={
                "symbol": "FPT",
                "start_date": "2026-04-01",
                "end_date": "2026-05-01",
                "indicators": {"trend": "MACD", "momentum": "RSI"},
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body["symbol"] == "FPT"
        assert body["count"] == 1
        # Only the categories the request mentioned should appear.
        assert set(body["indicators"].keys()) == {"trend", "momentum"}
        assert body["indicators"]["trend"]["name"] == "MACD"


@pytest.mark.asyncio
async def test_indicator_data_empty_indicators_dict_produces_empty_metadata(client: AsyncClient):
    """No indicators selected → metadata is an empty dict, not missing."""
    canned = IndicatorDataResponse(status="success", symbol="VNM", data=[], count=0)
    with patch("app.api.routes.InsightsService") as MockService:
        MockService.return_value.get_indicator_data = AsyncMock(return_value=canned)
        r = await client.post(
            f"{PREFIX}/insights/indicators/data",
            json={
                "symbol": "VNM",
                "start_date": "2026-04-01",
                "end_date": "2026-05-01",
                "indicators": {},
            },
        )
        assert r.status_code == 200
        assert r.json()["indicators"] == {}


# ---------------------------------------------------------------------------
# /insights/comprehensive
# ---------------------------------------------------------------------------

def _comprehensive_canned():
    return ComprehensiveInsightsResponse(
        status="success",
        symbol="FPT",
        insights=ComprehensiveInsights(
            ai_score=AIScoreComponent(
                overall_score=72.0,
                confidence_level="high",
                pattern_score=70.0,
                sentiment_score=75.0,
                risk_score=68.0,
                prediction_score=74.0,
            ),
            sentiment_analysis=SentimentAnalysis(
                sentiment_type="bullish",
                score=0.6,
                confidence=0.8,
                news_count=5,
                summary="Positive momentum",
            ),
            risk_assessment=RiskAssessment(
                risk_level="medium",
                volatility=0.18,
                beta=1.1,
                var_95=0.05,
                risk_score=55.0,
                factors=[],
            ),
            pattern_recognition=PatternRecognition(
                summary="No notable patterns",
                patterns=[],
            ),
            price_prediction=PricePrediction(
                random_forest=None,
                xgboost=None,
                ensemble=None,
                model_comparison="N/A",
            ),
        ),
        generated_at=datetime(2026, 5, 11, 12, 0, 0),
    )


@pytest.mark.asyncio
async def test_comprehensive_insights_unwraps_into_flat_data_shape(client: AsyncClient):
    """The route flattens the ComprehensiveInsightsResponse into
    {status, data: {symbol, insights, generated_at}}."""
    with patch("app.api.routes.InsightsService") as MockService:
        MockService.return_value.get_comprehensive_insights = AsyncMock(return_value=_comprehensive_canned())
        r = await client.post(
            f"{PREFIX}/insights/comprehensive",
            json={
                "symbol": "FPT",
                "start_date": "2026-04-01",
                "end_date": "2026-05-01",
                "selected_indicators": {"trend": "MACD"},
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "success"
        assert body["data"]["symbol"] == "FPT"
        assert body["data"]["insights"]["ai_score"]["overall_score"] == 72.0
        assert body["data"]["generated_at"].startswith("2026-05-11")
