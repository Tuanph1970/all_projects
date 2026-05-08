"""Route-plumbing tests for the knowledge-qa router.

The existing test_api_endpoints.py covers liveness, validation, and the
empty-session paths. This file fills the route gaps with mocked use
cases — verifies routes correctly delegate to their use cases and
return the right shape, without spinning up Neo4j or Ollama.
"""
import pytest
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.api.dependencies import (
    get_ask_question_use_case,
    get_history_use_case,
    get_clear_session_use_case,
    get_search_notes_use_case,
    get_graph_stats_use_case,
)


PREFIX = "/stock_helper/api/v2/knowledge-qa"


@pytest.fixture
def client():
    yield TestClient(app)
    # Each test that sets dependency overrides is responsible for clearing
    # them; this keeps the fixture cheap.
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# /chat — SSE streaming
# ---------------------------------------------------------------------------

def test_chat_streams_use_case_chunks(client):
    """Use case yields a sequence of SSE chunks; route should stream them."""

    async def fake_execute(command):
        for chunk in [
            "event: message\ndata: hello\n\n",
            "event: message\ndata: world\n\n",
            "event: done\ndata: {}\n\n",
        ]:
            yield chunk

    fake_use_case = AsyncMock()
    fake_use_case.execute = fake_execute

    app.dependency_overrides[get_ask_question_use_case] = lambda: fake_use_case

    r = client.post(
        f"{PREFIX}/chat",
        json={"question": "What is trading psychology?", "session_id": "s1"},
    )

    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("text/event-stream")
    body = r.text
    assert "data: hello" in body
    assert "data: world" in body
    assert "event: done" in body


def test_chat_stream_sets_no_buffering_headers(client):
    """SSE needs Cache-Control: no-cache + X-Accel-Buffering: no for nginx."""

    async def fake_execute(command):
        yield "data: x\n\n"

    fake_use_case = AsyncMock()
    fake_use_case.execute = fake_execute
    app.dependency_overrides[get_ask_question_use_case] = lambda: fake_use_case

    r = client.post(f"{PREFIX}/chat", json={"question": "hi", "session_id": "s1"})

    assert r.headers["cache-control"] == "no-cache"
    assert r.headers["x-accel-buffering"] == "no"
    assert r.headers.get("connection", "").lower() == "keep-alive"


def test_chat_validates_question_min_length(client):
    """Empty question must 422 from the schema's Field constraint."""
    r = client.post(
        f"{PREFIX}/chat", json={"question": "", "session_id": "s1"}
    )
    assert r.status_code == 422


def test_chat_validates_session_id_required(client):
    """session_id is required — not passing it must 422."""
    r = client.post(f"{PREFIX}/chat", json={"question": "hi"})
    assert r.status_code == 422


def test_chat_validates_max_context_notes_upper_bound(client):
    """max_context_notes > 20 is rejected by schema validation."""
    r = client.post(
        f"{PREFIX}/chat",
        json={"question": "What?", "session_id": "s1", "max_context_notes": 100},
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# /chat/history/{session_id}
# ---------------------------------------------------------------------------

def test_history_returns_use_case_response(client):
    fake_use_case = AsyncMock()
    fake_use_case.execute.return_value = {
        "session_id": "s1",
        "messages": [
            {
                "id": "msg-1",
                "role": "user",
                "content": "hi",
                "timestamp": "2026-05-08T00:00:00",
                "sources": [],
            },
        ],
        "message_count": 1,
    }
    app.dependency_overrides[get_history_use_case] = lambda: fake_use_case

    r = client.get(f"{PREFIX}/chat/history/s1")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["session_id"] == "s1"
    assert body["message_count"] == 1
    assert len(body["messages"]) == 1


# ---------------------------------------------------------------------------
# /chat/clear/{session_id}
# ---------------------------------------------------------------------------

def test_clear_session_delegates_to_use_case(client):
    fake_use_case = AsyncMock()
    fake_use_case.execute.return_value = {
        "session_id": "s1",
        "message": "Session s1 cleared",
    }
    app.dependency_overrides[get_clear_session_use_case] = lambda: fake_use_case

    r = client.post(f"{PREFIX}/chat/clear/s1")
    assert r.status_code == 200
    assert r.json()["session_id"] == "s1"

    # Verify the command carried the path-param session id
    fake_use_case.execute.assert_awaited_once()
    command = fake_use_case.execute.await_args.args[0]
    assert command.session_id == "s1"


# ---------------------------------------------------------------------------
# /search
# ---------------------------------------------------------------------------

def test_search_forwards_query_and_limit(client):
    fake_use_case = AsyncMock()
    fake_use_case.execute.return_value = {
        "query": "psychology",
        "results": [],
        "total": 0,
    }
    app.dependency_overrides[get_search_notes_use_case] = lambda: fake_use_case

    r = client.get(f"{PREFIX}/search?q=psychology&limit=5")
    assert r.status_code == 200

    query = fake_use_case.execute.await_args.args[0]
    assert query.query == "psychology"
    assert query.limit == 5


def test_search_validates_q_max_length(client):
    """q > 500 chars must 422."""
    r = client.get(f"{PREFIX}/search?q={'x' * 501}")
    assert r.status_code == 422


def test_search_validates_limit_upper_bound(client):
    r = client.get(f"{PREFIX}/search?q=hi&limit=999")
    assert r.status_code == 422


def test_search_default_limit_is_ten(client):
    fake_use_case = AsyncMock()
    fake_use_case.execute.return_value = {"query": "hi", "results": [], "total": 0}
    app.dependency_overrides[get_search_notes_use_case] = lambda: fake_use_case

    client.get(f"{PREFIX}/search?q=hi")

    query = fake_use_case.execute.await_args.args[0]
    assert query.limit == 10


# ---------------------------------------------------------------------------
# /stats
# ---------------------------------------------------------------------------

def test_stats_returns_use_case_payload(client):
    fake_use_case = AsyncMock()
    fake_use_case.execute.return_value = {
        "total_notes": 100,
        "total_tags": 50,
        "total_links": 200,
    }
    app.dependency_overrides[get_graph_stats_use_case] = lambda: fake_use_case

    r = client.get(f"{PREFIX}/stats")
    assert r.status_code == 200
    body = r.json()
    assert body["total_notes"] == 100
    assert body["total_tags"] == 50
    assert body["total_links"] == 200
