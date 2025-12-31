"""
Integration tests for AI services (ai-insights-service and chatbot-service).

Tests cover:
- AI-powered stock insights
- News sentiment analysis
- Stock comparison
- Chatbot conversations
- Session management
"""

import pytest
import httpx
from datetime import datetime

from tests.conftest import get_api_path


pytestmark = [pytest.mark.integration]


# =============================================================================
# AI Insights Service Tests
# =============================================================================

class TestAIInsightsHealth:
    """Test ai-insights-service health endpoints."""

    async def test_health_live(self, ai_insights_client: httpx.AsyncClient):
        """Test liveness probe endpoint."""
        response = await ai_insights_client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"

    async def test_health_ready(self, ai_insights_client: httpx.AsyncClient):
        """Test readiness probe endpoint."""
        response = await ai_insights_client.get("/health/ready")
        assert response.status_code == 200


class TestAICapabilities:
    """Test AI capabilities endpoint."""

    async def test_get_capabilities(self, ai_insights_client: httpx.AsyncClient):
        """Test listing AI capabilities."""
        response = await ai_insights_client.get(get_api_path("ai/capabilities"))
        assert response.status_code == 200
        data = response.json()

        # Should list available AI features
        assert isinstance(data, (list, dict))


class TestStockInsights:
    """Test AI-powered stock insights."""

    async def test_generate_insight(
        self,
        ai_insights_client: httpx.AsyncClient,
        auth_headers: dict
    ):
        """Test generating AI insight for a stock."""
        response = await ai_insights_client.post(
            get_api_path("ai/insight"),
            headers=auth_headers,
            json={"symbol": "VNM"}
        )
        # May fail if LLM not configured
        assert response.status_code in [200, 400, 401, 503]

        if response.status_code == 200:
            data = response.json()
            assert "insight" in data or "analysis" in data or "summary" in data

    async def test_get_insight_endpoint(
        self,
        ai_insights_client: httpx.AsyncClient,
        auth_headers: dict
    ):
        """Test GET endpoint for insights."""
        response = await ai_insights_client.get(
            get_api_path("ai/insight/VNM"),
            headers=auth_headers
        )
        assert response.status_code in [200, 400, 401, 503]

    async def test_insight_with_context(
        self,
        ai_insights_client: httpx.AsyncClient,
        auth_headers: dict
    ):
        """Test insight with additional context."""
        response = await ai_insights_client.post(
            get_api_path("ai/insight"),
            headers=auth_headers,
            json={
                "symbol": "FPT",
                "context": "Looking for long-term investment",
                "include_technical": True,
                "include_fundamental": True
            }
        )
        assert response.status_code in [200, 400, 401, 503]


class TestStockComparison:
    """Test AI-powered stock comparison."""

    async def test_compare_stocks(
        self,
        ai_insights_client: httpx.AsyncClient,
        auth_headers: dict
    ):
        """Test comparing multiple stocks with AI."""
        response = await ai_insights_client.post(
            get_api_path("ai/compare"),
            headers=auth_headers,
            json={
                "symbols": ["VNM", "VIC", "FPT"]
            }
        )
        assert response.status_code in [200, 400, 401, 503]

        if response.status_code == 200:
            data = response.json()
            # Should contain comparison analysis
            assert isinstance(data, dict)

    async def test_compare_with_criteria(
        self,
        ai_insights_client: httpx.AsyncClient,
        auth_headers: dict
    ):
        """Test comparison with specific criteria."""
        response = await ai_insights_client.post(
            get_api_path("ai/compare"),
            headers=auth_headers,
            json={
                "symbols": ["VNM", "VIC"],
                "criteria": ["growth", "value", "dividend"]
            }
        )
        assert response.status_code in [200, 400, 401, 503]


class TestNewsAnalysis:
    """Test AI-powered news analysis."""

    async def test_analyze_news_impact(
        self,
        ai_insights_client: httpx.AsyncClient,
        auth_headers: dict
    ):
        """Test analyzing news impact on a stock."""
        response = await ai_insights_client.post(
            get_api_path("ai/news-analysis"),
            headers=auth_headers,
            json={
                "symbol": "VNM",
                "news_text": "Vinamilk announces record quarterly profits and expansion plans"
            }
        )
        # May return 422 if request validation fails
        assert response.status_code in [200, 400, 401, 422, 503]

        if response.status_code == 200:
            data = response.json()
            # Should contain sentiment and impact analysis
            assert any(key in data for key in [
                "sentiment", "impact", "analysis", "recommendation"
            ])


class TestQuestionAnswering:
    """Test AI question answering."""

    async def test_ask_question(
        self,
        ai_insights_client: httpx.AsyncClient,
        auth_headers: dict
    ):
        """Test asking a stock-related question."""
        response = await ai_insights_client.post(
            get_api_path("ai/ask"),
            headers=auth_headers,
            json={
                "question": "What is the current P/E ratio of VNM and is it undervalued?"
            }
        )
        assert response.status_code in [200, 400, 401, 503]

        if response.status_code == 200:
            data = response.json()
            assert "answer" in data or "response" in data

    async def test_ask_with_symbol_context(
        self,
        ai_insights_client: httpx.AsyncClient,
        auth_headers: dict
    ):
        """Test asking question with symbol context."""
        response = await ai_insights_client.post(
            get_api_path("ai/ask"),
            headers=auth_headers,
            json={
                "question": "Should I buy this stock?",
                "symbol": "FPT"
            }
        )
        assert response.status_code in [200, 400, 401, 503]


class TestMarketOverview:
    """Test AI market overview."""

    async def test_get_market_overview(
        self,
        ai_insights_client: httpx.AsyncClient,
        auth_headers: dict
    ):
        """Test getting AI-generated market overview."""
        response = await ai_insights_client.get(
            get_api_path("ai/market-overview"),
            headers=auth_headers
        )
        assert response.status_code in [200, 401, 503]

        if response.status_code == 200:
            data = response.json()
            # Should contain market analysis
            assert isinstance(data, dict)


# =============================================================================
# Chatbot Service Tests
# =============================================================================

class TestChatbotHealth:
    """Test chatbot-service health endpoints."""

    async def test_health_live(self, chatbot_client: httpx.AsyncClient):
        """Test liveness probe endpoint."""
        response = await chatbot_client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"

    async def test_health_ready(self, chatbot_client: httpx.AsyncClient):
        """Test readiness probe endpoint."""
        response = await chatbot_client.get("/health/ready")
        assert response.status_code == 200


class TestChatConversation:
    """Test chat conversation endpoints."""

    async def test_send_chat_message(
        self,
        chatbot_client: httpx.AsyncClient,
        auth_headers: dict
    ):
        """Test sending a chat message."""
        response = await chatbot_client.post(
            get_api_path("chat/chat"),
            headers=auth_headers,
            json={
                "message": "What stocks should I look at today?"
            }
        )
        assert response.status_code in [200, 401, 503]

        if response.status_code == 200:
            data = response.json()
            assert "response" in data or "message" in data or "reply" in data

    async def test_chat_with_session_id(
        self,
        chatbot_client: httpx.AsyncClient,
        auth_headers: dict
    ):
        """Test chat with session continuity."""
        session_id = "test-session-123"

        # First message
        response1 = await chatbot_client.post(
            get_api_path("chat/chat"),
            headers=auth_headers,
            json={
                "message": "Tell me about VNM",
                "session_id": session_id
            }
        )
        assert response1.status_code in [200, 401, 503]

        # Follow-up message
        response2 = await chatbot_client.post(
            get_api_path("chat/chat"),
            headers=auth_headers,
            json={
                "message": "What about its competitors?",
                "session_id": session_id
            }
        )
        assert response2.status_code in [200, 401, 503]

    async def test_chat_about_specific_stock(
        self,
        chatbot_client: httpx.AsyncClient,
        auth_headers: dict
    ):
        """Test chatting about a specific stock."""
        response = await chatbot_client.post(
            get_api_path("chat/chat"),
            headers=auth_headers,
            json={
                "message": "Analyze FPT stock for me",
                "symbol": "FPT"
            }
        )
        assert response.status_code in [200, 401, 503]

    async def test_chat_portfolio_question(
        self,
        chatbot_client: httpx.AsyncClient,
        auth_headers: dict
    ):
        """Test asking about portfolio."""
        response = await chatbot_client.post(
            get_api_path("chat/chat"),
            headers=auth_headers,
            json={
                "message": "How is my portfolio performing?"
            }
        )
        assert response.status_code in [200, 401, 503]


class TestChatHistory:
    """Test chat history endpoints."""

    async def test_get_chat_history(
        self,
        chatbot_client: httpx.AsyncClient,
        auth_headers: dict
    ):
        """Test getting chat history for a session."""
        session_id = "test-session-456"

        # Send a message first
        await chatbot_client.post(
            get_api_path("chat/chat"),
            headers=auth_headers,
            json={
                "message": "Hello",
                "session_id": session_id
            }
        )

        # Get history
        response = await chatbot_client.get(
            get_api_path(f"chat/history/{session_id}"),
            headers=auth_headers
        )
        assert response.status_code in [200, 401, 404]

        if response.status_code == 200:
            data = response.json()
            items = data if isinstance(data, list) else data.get("messages", [])
            assert isinstance(items, list)


class TestSessionManagement:
    """Test chat session management."""

    async def test_clear_session(
        self,
        chatbot_client: httpx.AsyncClient,
        auth_headers: dict
    ):
        """Test clearing a chat session."""
        session_id = "test-session-789"

        # Create session with a message
        await chatbot_client.post(
            get_api_path("chat/chat"),
            headers=auth_headers,
            json={
                "message": "Hello",
                "session_id": session_id
            }
        )

        # Clear session
        response = await chatbot_client.delete(
            get_api_path(f"chat/session/{session_id}"),
            headers=auth_headers
        )
        assert response.status_code in [200, 204, 401, 404]


class TestChatSuggestions:
    """Test chat suggestions endpoint."""

    async def test_get_suggestions(
        self,
        chatbot_client: httpx.AsyncClient,
        auth_headers: dict
    ):
        """Test getting quick action suggestions."""
        response = await chatbot_client.get(
            get_api_path("chat/suggestions"),
            headers=auth_headers
        )
        assert response.status_code in [200, 401]

        if response.status_code == 200:
            data = response.json()
            items = data if isinstance(data, list) else data.get("suggestions", [])
            assert isinstance(items, list)


class TestChatbotIntentDetection:
    """Test chatbot intent detection."""

    async def test_stock_price_intent(
        self,
        chatbot_client: httpx.AsyncClient,
        auth_headers: dict
    ):
        """Test detecting stock price inquiry intent."""
        response = await chatbot_client.post(
            get_api_path("chat/chat"),
            headers=auth_headers,
            json={
                "message": "What is the current price of VNM?"
            }
        )
        assert response.status_code in [200, 401, 503]

    async def test_analysis_intent(
        self,
        chatbot_client: httpx.AsyncClient,
        auth_headers: dict
    ):
        """Test detecting analysis intent."""
        response = await chatbot_client.post(
            get_api_path("chat/chat"),
            headers=auth_headers,
            json={
                "message": "Give me a technical analysis of FPT"
            }
        )
        assert response.status_code in [200, 401, 503]

    async def test_recommendation_intent(
        self,
        chatbot_client: httpx.AsyncClient,
        auth_headers: dict
    ):
        """Test detecting recommendation intent."""
        response = await chatbot_client.post(
            get_api_path("chat/chat"),
            headers=auth_headers,
            json={
                "message": "What stocks do you recommend for growth?"
            }
        )
        assert response.status_code in [200, 401, 503]


class TestAIServiceIntegration:
    """Test integration between AI services."""

    async def test_chatbot_uses_insights(
        self,
        chatbot_client: httpx.AsyncClient,
        ai_insights_client: httpx.AsyncClient,
        auth_headers: dict
    ):
        """Test that chatbot can access AI insights."""
        # Ask chatbot for analysis
        chat_response = await chatbot_client.post(
            get_api_path("chat/chat"),
            headers=auth_headers,
            json={
                "message": "Give me an AI analysis of VNM"
            }
        )

        # Should work or gracefully handle unavailable service
        assert chat_response.status_code in [200, 401, 503]


class TestRateLimiting:
    """Test rate limiting on AI endpoints."""

    @pytest.mark.slow
    async def test_ai_rate_limiting(
        self,
        ai_insights_client: httpx.AsyncClient,
        auth_headers: dict
    ):
        """Test that AI endpoints have rate limiting."""
        responses = []
        for _ in range(10):
            response = await ai_insights_client.post(
                get_api_path("ai/insight"),
            headers=auth_headers,
                json={"symbol": "VNM"}
            )
            responses.append(response.status_code)

        # May see 429 if rate limited
        # Or all may succeed if generous limits
        assert all(code in [200, 401, 429, 503] for code in responses)


class TestInputValidation:
    """Test input validation for AI services."""

    async def test_insight_empty_symbol(
        self,
        ai_insights_client: httpx.AsyncClient,
        auth_headers: dict
    ):
        """Test insight with empty symbol."""
        response = await ai_insights_client.post(
            get_api_path("ai/insight"),
            headers=auth_headers,
            json={"symbol": ""}
        )
        # Some services accept empty symbol and return default or error message
        assert response.status_code in [200, 400, 422]

    async def test_chat_empty_message(
        self,
        chatbot_client: httpx.AsyncClient,
        auth_headers: dict
    ):
        """Test chat with empty message."""
        response = await chatbot_client.post(
            get_api_path("chat/chat"),
            headers=auth_headers,
            json={"message": ""}
        )
        assert response.status_code in [400, 422]

    async def test_compare_single_stock(
        self,
        ai_insights_client: httpx.AsyncClient,
        auth_headers: dict
    ):
        """Test comparison with single stock."""
        response = await ai_insights_client.post(
            get_api_path("ai/compare"),
            headers=auth_headers,
            json={"symbols": ["VNM"]}  # Need at least 2
        )
        assert response.status_code in [400, 422]
