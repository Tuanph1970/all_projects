"""
Chatbot Service Tests - New Endpoints
"""
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from app.models.schemas import (
    ChatResponse, ConversationHistory, Message, MessageRole,
    FeedbackType, ExportFormat, IntentType
)


# ============================================================================
# Health Check Tests
# ============================================================================

@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test health endpoint"""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_liveness_check(client: AsyncClient):
    """Test liveness endpoint"""
    response = await client.get("/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"


@pytest.mark.asyncio
async def test_readiness_check(client: AsyncClient):
    """Test readiness endpoint"""
    response = await client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"


# ============================================================================
# Feedback Endpoint Tests
# ============================================================================

@pytest.mark.asyncio
async def test_submit_feedback_success(client: AsyncClient, mock_conversation_history):
    """Test successful feedback submission"""
    with patch("app.api.routes.ChatbotService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.get_history = AsyncMock(return_value=mock_conversation_history)

        response = await client.post(
            "/stock_helper/api/v2/chat/feedback",
            json={
                "session_id": "test-session-123",
                "message_index": 1,
                "feedback_type": "helpful",
                "comment": "Great response!"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "feedback_id" in data
        assert data["session_id"] == "test-session-123"
        assert data["acknowledged"] is True
        assert "message" in data


@pytest.mark.asyncio
async def test_submit_feedback_session_not_found(client: AsyncClient):
    """Test feedback submission with non-existent session"""
    with patch("app.api.routes.ChatbotService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.get_history = AsyncMock(return_value=None)

        response = await client.post(
            "/stock_helper/api/v2/chat/feedback",
            json={
                "session_id": "non-existent-session",
                "message_index": 0,
                "feedback_type": "helpful"
            }
        )

        assert response.status_code == 404


@pytest.mark.asyncio
async def test_submit_feedback_invalid_message_index(client: AsyncClient, mock_conversation_history):
    """Test feedback submission with invalid message index"""
    with patch("app.api.routes.ChatbotService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.get_history = AsyncMock(return_value=mock_conversation_history)

        response = await client.post(
            "/stock_helper/api/v2/chat/feedback",
            json={
                "session_id": "test-session-123",
                "message_index": 100,  # Invalid index
                "feedback_type": "helpful"
            }
        )

        assert response.status_code == 400


@pytest.mark.asyncio
async def test_submit_feedback_all_types(client: AsyncClient, mock_conversation_history):
    """Test feedback submission with all feedback types"""
    with patch("app.api.routes.ChatbotService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.get_history = AsyncMock(return_value=mock_conversation_history)

        for feedback_type in ["helpful", "not_helpful", "incorrect", "needs_improvement"]:
            response = await client.post(
                "/stock_helper/api/v2/chat/feedback",
                json={
                    "session_id": "test-session-123",
                    "message_index": 1,
                    "feedback_type": feedback_type
                }
            )

            assert response.status_code == 200


@pytest.mark.asyncio
async def test_submit_feedback_with_suggested_response(client: AsyncClient, mock_conversation_history):
    """Test feedback submission with suggested response"""
    with patch("app.api.routes.ChatbotService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.get_history = AsyncMock(return_value=mock_conversation_history)

        response = await client.post(
            "/stock_helper/api/v2/chat/feedback",
            json={
                "session_id": "test-session-123",
                "message_index": 1,
                "feedback_type": "needs_improvement",
                "comment": "Could be more detailed",
                "suggested_response": "VNM is trading at 75,000 VND with +1.5% change today"
            }
        )

        assert response.status_code == 200


# ============================================================================
# Export History Tests
# ============================================================================

@pytest.mark.asyncio
async def test_export_history_json(client: AsyncClient, mock_conversation_history):
    """Test exporting history as JSON"""
    with patch("app.api.routes.ChatbotService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.get_history = AsyncMock(return_value=mock_conversation_history)

        response = await client.get(
            "/stock_helper/api/v2/chat/history/test-session-123/export?format=json"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "test-session-123"
        assert data["format"] == "json"
        assert "content" in data
        assert data["message_count"] == 4
        assert "exported_at" in data


@pytest.mark.asyncio
async def test_export_history_text(client: AsyncClient, mock_conversation_history):
    """Test exporting history as plain text"""
    with patch("app.api.routes.ChatbotService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.get_history = AsyncMock(return_value=mock_conversation_history)

        response = await client.get(
            "/stock_helper/api/v2/chat/history/test-session-123/export?format=text"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["format"] == "text"
        assert "Conversation Export" in data["content"]


@pytest.mark.asyncio
async def test_export_history_markdown(client: AsyncClient, mock_conversation_history):
    """Test exporting history as markdown"""
    with patch("app.api.routes.ChatbotService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.get_history = AsyncMock(return_value=mock_conversation_history)

        response = await client.get(
            "/stock_helper/api/v2/chat/history/test-session-123/export?format=markdown"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["format"] == "markdown"
        assert "# Conversation Export" in data["content"]


@pytest.mark.asyncio
async def test_export_history_default_format(client: AsyncClient, mock_conversation_history):
    """Test exporting history with default format (JSON)"""
    with patch("app.api.routes.ChatbotService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.get_history = AsyncMock(return_value=mock_conversation_history)

        response = await client.get(
            "/stock_helper/api/v2/chat/history/test-session-123/export"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["format"] == "json"


@pytest.mark.asyncio
async def test_export_history_session_not_found(client: AsyncClient):
    """Test exporting history for non-existent session"""
    with patch("app.api.routes.ChatbotService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.get_history = AsyncMock(return_value=None)

        response = await client.get(
            "/stock_helper/api/v2/chat/history/non-existent/export"
        )

        assert response.status_code == 404


@pytest.mark.asyncio
async def test_export_history_unauthenticated(unauthenticated_client: AsyncClient, mock_conversation_history):
    """Test export works without authentication"""
    with patch("app.api.routes.ChatbotService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.get_history = AsyncMock(return_value=mock_conversation_history)

        response = await unauthenticated_client.get(
            "/stock_helper/api/v2/chat/history/test-session-123/export"
        )

        assert response.status_code == 200


# ============================================================================
# Intents Endpoint Tests
# ============================================================================

@pytest.mark.asyncio
async def test_get_intents(client: AsyncClient):
    """Test getting list of supported intents"""
    response = await client.get("/stock_helper/api/v2/chat/intents")

    assert response.status_code == 200
    data = response.json()
    assert "intents" in data
    assert "total" in data
    assert data["total"] > 0


@pytest.mark.asyncio
async def test_get_intents_structure(client: AsyncClient):
    """Test intent data structure"""
    response = await client.get("/stock_helper/api/v2/chat/intents")

    assert response.status_code == 200
    data = response.json()

    # Verify intent structure
    assert len(data["intents"]) > 0
    intent = data["intents"][0]
    assert "intent" in intent
    assert "description" in intent
    assert "example_queries" in intent
    assert "supported_entities" in intent
    assert isinstance(intent["example_queries"], list)
    assert isinstance(intent["supported_entities"], list)


@pytest.mark.asyncio
async def test_get_intents_contains_expected_types(client: AsyncClient):
    """Test that expected intent types are present"""
    response = await client.get("/stock_helper/api/v2/chat/intents")

    assert response.status_code == 200
    data = response.json()

    intent_types = [i["intent"] for i in data["intents"]]
    assert "stock_price" in intent_types
    assert "stock_analysis" in intent_types
    assert "stock_prediction" in intent_types
    assert "market_overview" in intent_types


@pytest.mark.asyncio
async def test_get_intents_unauthenticated(unauthenticated_client: AsyncClient):
    """Test intents endpoint works without authentication"""
    response = await unauthenticated_client.get("/stock_helper/api/v2/chat/intents")
    assert response.status_code == 200


# ============================================================================
# Stats Endpoint Tests
# ============================================================================

@pytest.mark.asyncio
async def test_get_stats_today(client: AsyncClient):
    """Test getting stats for today"""
    response = await client.get("/stock_helper/api/v2/chat/stats?period=today")

    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "today"
    assert "stats" in data
    assert "generated_at" in data


@pytest.mark.asyncio
async def test_get_stats_week(client: AsyncClient):
    """Test getting stats for week"""
    response = await client.get("/stock_helper/api/v2/chat/stats?period=week")

    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "week"


@pytest.mark.asyncio
async def test_get_stats_month(client: AsyncClient):
    """Test getting stats for month"""
    response = await client.get("/stock_helper/api/v2/chat/stats?period=month")

    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "month"


@pytest.mark.asyncio
async def test_get_stats_all(client: AsyncClient):
    """Test getting all-time stats"""
    response = await client.get("/stock_helper/api/v2/chat/stats?period=all")

    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "all"


@pytest.mark.asyncio
async def test_get_stats_default_period(client: AsyncClient):
    """Test getting stats with default period"""
    response = await client.get("/stock_helper/api/v2/chat/stats")

    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "today"  # Default value


@pytest.mark.asyncio
async def test_get_stats_structure(client: AsyncClient):
    """Test stats data structure"""
    response = await client.get("/stock_helper/api/v2/chat/stats")

    assert response.status_code == 200
    data = response.json()

    stats = data["stats"]
    assert "total_sessions" in stats
    assert "total_messages" in stats
    assert "avg_messages_per_session" in stats
    assert "top_intents" in stats
    assert "avg_response_time_ms" in stats
    assert "satisfaction_rate" in stats


@pytest.mark.asyncio
async def test_get_stats_invalid_period(client: AsyncClient):
    """Test getting stats with invalid period"""
    response = await client.get("/stock_helper/api/v2/chat/stats?period=invalid")

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_get_stats_requires_auth(unauthenticated_client: AsyncClient):
    """Test stats endpoint requires authentication"""
    # Override to require auth
    from app.api.dependencies import get_current_user
    from app.main import app

    def override_get_current_user():
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Not authenticated")

    app.dependency_overrides[get_current_user] = override_get_current_user

    response = await unauthenticated_client.get("/stock_helper/api/v2/chat/stats")

    # Should require authentication
    assert response.status_code in [401, 403, 422]

    app.dependency_overrides.clear()


# ============================================================================
# Suggestions Endpoint Tests
# ============================================================================

@pytest.mark.asyncio
async def test_get_suggestions(client: AsyncClient):
    """Test getting quick action suggestions"""
    response = await client.get("/stock_helper/api/v2/chat/suggestions")

    assert response.status_code == 200
    data = response.json()
    assert "suggestions" in data
    assert len(data["suggestions"]) > 0


@pytest.mark.asyncio
async def test_suggestions_structure(client: AsyncClient):
    """Test suggestion data structure"""
    response = await client.get("/stock_helper/api/v2/chat/suggestions")

    assert response.status_code == 200
    data = response.json()

    suggestion = data["suggestions"][0]
    assert "text" in suggestion
    assert "intent" in suggestion


# ============================================================================
# Chat Endpoint Tests
# ============================================================================

@pytest.mark.asyncio
async def test_chat_success(client: AsyncClient, mock_chat_response):
    """Test successful chat message"""
    with patch("app.api.routes.ChatbotService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.chat = AsyncMock(return_value=mock_chat_response)

        response = await client.post(
            "/stock_helper/api/v2/chat/chat",
            json={
                "message": "What is the price of VNM?",
                "session_id": "test-session-123"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert "message" in data
        assert "timestamp" in data


@pytest.mark.asyncio
async def test_chat_new_session(client: AsyncClient, mock_chat_response):
    """Test chat creates new session if not provided"""
    with patch("app.api.routes.ChatbotService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.chat = AsyncMock(return_value=mock_chat_response)

        response = await client.post(
            "/stock_helper/api/v2/chat/chat",
            json={"message": "Hello"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data


@pytest.mark.asyncio
async def test_chat_validation(client: AsyncClient):
    """Test chat input validation"""
    # Empty message
    response = await client.post(
        "/stock_helper/api/v2/chat/chat",
        json={"message": ""}
    )
    assert response.status_code == 422


# ============================================================================
# History Endpoint Tests
# ============================================================================

@pytest.mark.asyncio
async def test_get_history_success(client: AsyncClient, mock_conversation_history):
    """Test getting conversation history"""
    with patch("app.api.routes.ChatbotService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.get_history = AsyncMock(return_value=mock_conversation_history)

        response = await client.get("/stock_helper/api/v2/chat/history/test-session-123")

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "test-session-123"
        assert "messages" in data
        assert len(data["messages"]) > 0


@pytest.mark.asyncio
async def test_get_history_not_found(client: AsyncClient):
    """Test getting history for non-existent session"""
    with patch("app.api.routes.ChatbotService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.get_history = AsyncMock(return_value=None)

        response = await client.get("/stock_helper/api/v2/chat/history/non-existent")

        assert response.status_code == 404


# ============================================================================
# Session Management Tests
# ============================================================================

@pytest.mark.asyncio
async def test_clear_session(client: AsyncClient):
    """Test clearing a session"""
    with patch("app.api.routes.ChatbotService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.clear_session = AsyncMock()

        response = await client.delete("/stock_helper/api/v2/chat/session/test-session-123")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Session cleared"


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_chat_then_feedback_workflow(client: AsyncClient, mock_chat_response, mock_conversation_history):
    """Test complete chat to feedback workflow"""
    with patch("app.api.routes.ChatbotService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.chat = AsyncMock(return_value=mock_chat_response)
        mock_instance.get_history = AsyncMock(return_value=mock_conversation_history)

        # Send chat message
        chat_response = await client.post(
            "/stock_helper/api/v2/chat/chat",
            json={"message": "What is VNM price?", "session_id": "test-session-123"}
        )
        assert chat_response.status_code == 200

        # Submit feedback
        feedback_response = await client.post(
            "/stock_helper/api/v2/chat/feedback",
            json={
                "session_id": "test-session-123",
                "message_index": 1,
                "feedback_type": "helpful"
            }
        )
        assert feedback_response.status_code == 200


@pytest.mark.asyncio
async def test_chat_then_export_workflow(client: AsyncClient, mock_chat_response, mock_conversation_history):
    """Test complete chat to export workflow"""
    with patch("app.api.routes.ChatbotService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.chat = AsyncMock(return_value=mock_chat_response)
        mock_instance.get_history = AsyncMock(return_value=mock_conversation_history)

        # Send chat message
        chat_response = await client.post(
            "/stock_helper/api/v2/chat/chat",
            json={"message": "Analyze VNM", "session_id": "test-session-123"}
        )
        assert chat_response.status_code == 200

        # Export conversation
        export_response = await client.get(
            "/stock_helper/api/v2/chat/history/test-session-123/export?format=markdown"
        )
        assert export_response.status_code == 200
        assert "# Conversation Export" in export_response.json()["content"]
