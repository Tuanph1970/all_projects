"""
Test Configuration and Fixtures for Chatbot Service
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.main import app
from app.api.dependencies import get_current_user, get_current_user_optional
from app.models.schemas import (
    ChatResponse, ConversationHistory, Message, MessageRole,
    IntentType, FeedbackType
)


@pytest_asyncio.fixture
async def client():
    """Create test client with mocked dependencies"""

    def override_get_current_user():
        return {"user_id": 1, "email": "testuser@example.com"}

    def override_get_current_user_optional():
        return {"user_id": 1, "email": "testuser@example.com"}

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_user_optional] = override_get_current_user_optional

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def unauthenticated_client():
    """Create test client without authentication"""
    def override_get_current_user_optional():
        return None

    app.dependency_overrides[get_current_user_optional] = override_get_current_user_optional

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def mock_chat_response():
    """Mock chat response"""
    return ChatResponse(
        session_id="test-session-123",
        message="VNM is currently trading at 75,000 VND",
        intent="stock_price",
        entities=[{"symbol": "VNM"}],
        actions_taken=["fetch_price"],
        suggestions=["View analysis", "Check prediction"],
        timestamp=datetime.now()
    )


@pytest.fixture
def mock_conversation_history():
    """Mock conversation history"""
    return ConversationHistory(
        session_id="test-session-123",
        messages=[
            Message(
                role=MessageRole.USER,
                content="What is the price of VNM?",
                timestamp=datetime(2024, 1, 15, 10, 30, 0)
            ),
            Message(
                role=MessageRole.ASSISTANT,
                content="VNM is currently trading at 75,000 VND",
                timestamp=datetime(2024, 1, 15, 10, 30, 5)
            ),
            Message(
                role=MessageRole.USER,
                content="Can you analyze it?",
                timestamp=datetime(2024, 1, 15, 10, 31, 0)
            ),
            Message(
                role=MessageRole.ASSISTANT,
                content="VNM shows positive momentum with RSI at 55.",
                timestamp=datetime(2024, 1, 15, 10, 31, 10)
            ),
        ],
        created_at=datetime(2024, 1, 15, 10, 30, 0),
        last_activity=datetime(2024, 1, 15, 10, 31, 10)
    )


@pytest.fixture
def feedback_request_data():
    """Test data for feedback submission"""
    return {
        "session_id": "test-session-123",
        "message_index": 1,
        "feedback_type": "helpful",
        "comment": "Great response!"
    }


@pytest.fixture
def chat_request_data():
    """Test data for chat request"""
    return {
        "message": "What is the price of VNM?",
        "session_id": "test-session-123"
    }
