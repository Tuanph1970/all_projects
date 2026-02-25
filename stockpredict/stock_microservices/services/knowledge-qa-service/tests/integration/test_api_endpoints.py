"""Integration tests for API endpoints using FastAPI TestClient."""
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.domain.entities.knowledge_note import KnowledgeNote


@pytest.fixture
def client():
    return TestClient(app)


def test_liveness(client):
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


def test_service_info(client):
    response = client.get("/stock_helper/api/v2/knowledge-qa/info")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "knowledge-qa-service"
    assert "endpoints" in data


def test_search_requires_query(client):
    response = client.get("/stock_helper/api/v2/knowledge-qa/search")
    assert response.status_code == 422  # Missing required 'q' parameter


def test_chat_requires_body(client):
    response = client.post("/stock_helper/api/v2/knowledge-qa/chat")
    assert response.status_code == 422  # Missing request body


def test_chat_validates_empty_question(client):
    response = client.post(
        "/stock_helper/api/v2/knowledge-qa/chat",
        json={"question": "", "session_id": "test"},
    )
    assert response.status_code == 422  # Validation error (min_length=1)


def test_get_history_empty_session(client):
    response = client.get("/stock_helper/api/v2/knowledge-qa/chat/history/nonexistent")
    assert response.status_code == 200
    data = response.json()
    assert data["messages"] == []
    assert data["message_count"] == 0


def test_clear_nonexistent_session(client):
    response = client.post("/stock_helper/api/v2/knowledge-qa/chat/clear/nonexistent")
    assert response.status_code == 200
    data = response.json()
    assert "cleared" in data["message"].lower() or "clear" in data["message"].lower()
