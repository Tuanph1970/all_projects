"""Coverage climb tests for the small uncovered helper modules.

Targets:
- shared/utils.py: truncate_text, clean_text
- shared/logger.py: setup_logging
- domain/value_objects/llm_response.py: LLMResponse dataclass
- infrastructure/factories/graph_context_factory.py: build from notes
- infrastructure/event_handlers/logging_handler.py: log per-event-type
- api/error_handlers.py: exception → HTTP status mapping
- api/middleware.py: request logging
- infrastructure/external/ollama_adapter.py: generate / stream /
  health_check with httpx mocked
- infrastructure/persistence/neo4j_knowledge_graph_repository.py:
  fulltext / fallback / tag / related / stats / health, all with the
  Neo4j AsyncDriver mocked
"""
import json
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.api.error_handlers import (
    global_exception_handler,
    knowledge_qa_error_handler,
)
from app.api.middleware import log_request_middleware
from app.domain.entities.knowledge_note import KnowledgeNote
from app.domain.events.domain_events import (
    AnswerGeneratedEvent,
    DomainEvent,
    QuestionAskedEvent,
    SessionClearedEvent,
    SessionCreatedEvent,
)
from app.domain.exceptions import (
    EmptyQueryError,
    GraphConnectionError,
    GraphQueryError,
    KnowledgeQAError,
    LLMConnectionError,
    SessionNotFoundError,
)
from app.domain.value_objects.llm_response import LLMResponse
from app.infrastructure.event_handlers.logging_handler import LoggingEventHandler
from app.infrastructure.external.ollama_adapter import OllamaLLMAdapter
from app.infrastructure.factories.graph_context_factory import GraphContextFactory
from app.infrastructure.persistence.neo4j_knowledge_graph_repository import (
    Neo4jKnowledgeGraphRepository,
)
from app.shared.logger import setup_logging
from app.shared.utils import clean_text, truncate_text


# ---------------------------------------------------------------------------
# shared/utils.py
# ---------------------------------------------------------------------------

class TestTruncateText:
    def test_short_text_unchanged(self):
        assert truncate_text("hello", max_length=100) == "hello"

    def test_long_text_truncated_at_word_boundary(self):
        # Word boundary is well past the 0.8 × max_length threshold,
        # so we should break on whitespace, not mid-word.
        text = "alpha beta gamma " * 10  # 170 chars
        out = truncate_text(text, max_length=100)
        assert out.endswith("...")
        # The non-ellipsis portion ends at a known whole word ("beta")
        # rather than mid-word ("ga" partial). We can't predict the exact
        # ending word every time, but the truncated content should not
        # contain a partial word like "ga".
        body = out[:-3]
        assert " ga" not in body[-5:]  # would mean we cut mid-"gamma"
        assert len(out) <= 105

    def test_long_text_truncated_without_word_boundary_falls_through(self):
        """No space in the back 20% → return the hard cut + ellipsis."""
        text = "a" * 200  # no spaces at all
        out = truncate_text(text, max_length=50)
        assert out == "a" * 50 + "..."


class TestCleanText:
    def test_collapses_triple_newlines_to_double(self):
        assert clean_text("line1\n\n\n\nline2") == "line1\n\nline2"

    def test_collapses_multiple_spaces(self):
        assert clean_text("hello       world") == "hello world"

    def test_strips_leading_trailing_whitespace(self):
        assert clean_text("   text   ") == "text"


# ---------------------------------------------------------------------------
# shared/logger.py
# ---------------------------------------------------------------------------

def test_setup_logging_applies_requested_level():
    # logging.basicConfig is a no-op if root has handlers configured,
    # so clear them first to force a fresh config.
    root = logging.getLogger()
    saved_handlers = list(root.handlers)
    root.handlers.clear()
    try:
        setup_logging("WARNING")
        assert root.level == logging.WARNING
    finally:
        root.handlers.clear()
        root.handlers.extend(saved_handlers)


def test_setup_logging_falls_back_to_info_for_unknown_level():
    """getattr(... , level, logging.INFO) ensures bogus level → INFO."""
    root = logging.getLogger()
    saved_handlers = list(root.handlers)
    root.handlers.clear()
    try:
        setup_logging("NOT_A_LEVEL")
        assert root.level == logging.INFO
    finally:
        root.handlers.clear()
        root.handlers.extend(saved_handlers)


# ---------------------------------------------------------------------------
# domain/value_objects/llm_response.py
# ---------------------------------------------------------------------------

class TestLLMResponse:
    def test_construct_with_defaults(self):
        r = LLMResponse(text="hi", model="llama3.1")
        assert r.text == "hi"
        assert r.model == "llama3.1"
        assert r.tokens_used is None
        assert r.duration_ms is None
        assert r.finish_reason is None

    def test_frozen_dataclass_is_immutable(self):
        r = LLMResponse(text="hi", model="llama3.1")
        with pytest.raises(Exception):  # FrozenInstanceError
            r.text = "changed"


# ---------------------------------------------------------------------------
# infrastructure/factories/graph_context_factory.py
# ---------------------------------------------------------------------------

class TestGraphContextFactory:
    def test_create_from_notes_builds_references_and_context(self):
        notes_with_scores = [
            (KnowledgeNote(id="1", title="N1", content="content1"), 0.9),
            (KnowledgeNote(id="2", title="N2", content="content2"), 0.7),
        ]
        ctx = GraphContextFactory.create_from_notes(notes_with_scores)
        assert ctx.total_results == 2
        assert ctx.has_results is True
        assert [n.id for n in ctx.notes] == ["1", "2"]
        assert [r.relevance_score for r in ctx.references] == [0.9, 0.7]

    def test_create_from_empty_notes_list(self):
        ctx = GraphContextFactory.create_from_notes([])
        assert ctx.total_results == 0
        assert ctx.has_results is False
        assert ctx.notes == ()
        assert ctx.references == ()


# ---------------------------------------------------------------------------
# infrastructure/event_handlers/logging_handler.py
# ---------------------------------------------------------------------------

class TestLoggingEventHandler:
    def test_handles_question_asked(self, caplog):
        with caplog.at_level(logging.INFO):
            LoggingEventHandler().handle(
                QuestionAskedEvent(session_id="s1", question="Why?")
            )
        assert any("Question asked" in r.getMessage() for r in caplog.records)

    def test_handles_answer_generated(self, caplog):
        with caplog.at_level(logging.INFO):
            LoggingEventHandler().handle(
                AnswerGeneratedEvent(session_id="s1", tokens_used=42, model="llama")
            )
        assert any("Answer generated" in r.getMessage() for r in caplog.records)

    def test_handles_session_created(self, caplog):
        with caplog.at_level(logging.INFO):
            LoggingEventHandler().handle(SessionCreatedEvent(session_id="s2"))
        assert any("Session created" in r.getMessage() for r in caplog.records)

    def test_handles_session_cleared(self, caplog):
        with caplog.at_level(logging.INFO):
            LoggingEventHandler().handle(SessionClearedEvent(session_id="s3"))
        assert any("Session cleared" in r.getMessage() for r in caplog.records)

    def test_handles_unknown_event_via_generic_branch(self, caplog):
        with caplog.at_level(logging.INFO):
            LoggingEventHandler().handle(DomainEvent())
        assert any("DomainEvent" in r.getMessage() for r in caplog.records)


# ---------------------------------------------------------------------------
# api/error_handlers.py
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_error_handler_returns_400_for_empty_query():
    resp = await knowledge_qa_error_handler(MagicMock(), EmptyQueryError("empty"))
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_error_handler_returns_404_for_session_not_found():
    resp = await knowledge_qa_error_handler(MagicMock(), SessionNotFoundError("nope"))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_error_handler_returns_503_for_graph_connection():
    resp = await knowledge_qa_error_handler(MagicMock(), GraphConnectionError("down"))
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_error_handler_returns_503_for_llm_connection():
    resp = await knowledge_qa_error_handler(MagicMock(), LLMConnectionError("down"))
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_error_handler_returns_500_for_graph_query():
    resp = await knowledge_qa_error_handler(MagicMock(), GraphQueryError("bad"))
    assert resp.status_code == 500


@pytest.mark.asyncio
async def test_error_handler_returns_500_for_other_domain_errors():
    """Any KnowledgeQAError subclass not handled above falls through to 500."""
    class CustomError(KnowledgeQAError):
        pass

    resp = await knowledge_qa_error_handler(MagicMock(), CustomError("?"))
    assert resp.status_code == 500


@pytest.mark.asyncio
async def test_global_exception_handler_returns_500_with_type_name():
    resp = await global_exception_handler(MagicMock(), ValueError("oops"))
    assert resp.status_code == 500
    body = json.loads(resp.body)
    assert body["type"] == "ValueError"


# ---------------------------------------------------------------------------
# api/middleware.py
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_log_request_middleware_logs_status_and_duration(caplog):
    request = MagicMock()
    request.method = "GET"
    request.url.path = "/health"

    response = MagicMock()
    response.status_code = 200

    async def call_next(_req):
        return response

    with caplog.at_level(logging.INFO):
        out = await log_request_middleware(request, call_next)
    assert out is response
    assert any("/health" in r.getMessage() and "200" in r.getMessage() for r in caplog.records)


# ---------------------------------------------------------------------------
# OllamaLLMAdapter
# ---------------------------------------------------------------------------

class _FakeHttpxClient:
    def __init__(self, response):
        self._response = response

    async def __aenter__(self):
        c = MagicMock()
        c.post = AsyncMock(return_value=self._response)
        c.get = AsyncMock(return_value=self._response)
        return c

    async def __aexit__(self, *_):
        return False


@pytest.mark.asyncio
async def test_ollama_generate_returns_message_content():
    resp = MagicMock()
    resp.raise_for_status = lambda: None
    resp.json.return_value = {"message": {"content": "hi from llama"}}

    with patch(
        "app.infrastructure.external.ollama_adapter.httpx.AsyncClient",
        return_value=_FakeHttpxClient(resp),
    ):
        out = await OllamaLLMAdapter("http://ollama:11434", "llama3.1").generate(
            [{"role": "user", "content": "hi"}]
        )
    assert out == "hi from llama"


@pytest.mark.asyncio
async def test_ollama_generate_returns_empty_string_when_message_missing():
    resp = MagicMock()
    resp.raise_for_status = lambda: None
    resp.json.return_value = {}

    with patch(
        "app.infrastructure.external.ollama_adapter.httpx.AsyncClient",
        return_value=_FakeHttpxClient(resp),
    ):
        out = await OllamaLLMAdapter("http://ollama:11434").generate([])
    assert out == ""


@pytest.mark.asyncio
async def test_ollama_health_check_true_on_200():
    resp = MagicMock()
    resp.status_code = 200
    with patch(
        "app.infrastructure.external.ollama_adapter.httpx.AsyncClient",
        return_value=_FakeHttpxClient(resp),
    ):
        ok = await OllamaLLMAdapter("http://ollama:11434").health_check()
    assert ok is True


@pytest.mark.asyncio
async def test_ollama_health_check_false_on_non_200():
    resp = MagicMock()
    resp.status_code = 503
    with patch(
        "app.infrastructure.external.ollama_adapter.httpx.AsyncClient",
        return_value=_FakeHttpxClient(resp),
    ):
        ok = await OllamaLLMAdapter("http://ollama:11434").health_check()
    assert ok is False


@pytest.mark.asyncio
async def test_ollama_health_check_false_on_exception():
    class Boom:
        async def __aenter__(self):
            raise httpx.ConnectError("down")

        async def __aexit__(self, *_):
            return False

    with patch(
        "app.infrastructure.external.ollama_adapter.httpx.AsyncClient",
        return_value=Boom(),
    ):
        ok = await OllamaLLMAdapter("http://ollama:11434").health_check()
    assert ok is False


@pytest.mark.asyncio
async def test_ollama_generate_stream_yields_content_until_done():
    """The stream parses each line as JSON; yields message.content;
    breaks on done=True; skips malformed lines."""
    lines = [
        json.dumps({"message": {"content": "hel"}}),
        json.dumps({"message": {"content": "lo"}}),
        "{not valid json",
        json.dumps({"done": True}),
        json.dumps({"message": {"content": "after-done"}}),  # never yielded
    ]

    async def iter_lines():
        for line in lines:
            yield line

    class StreamCtx:
        async def __aenter__(self):
            resp = MagicMock()
            resp.raise_for_status = lambda: None
            resp.aiter_lines = iter_lines
            return resp

        async def __aexit__(self, *_):
            return False

    class ClientCtx:
        async def __aenter__(self):
            client = MagicMock()
            client.stream = lambda *a, **kw: StreamCtx()
            return client

        async def __aexit__(self, *_):
            return False

    with patch(
        "app.infrastructure.external.ollama_adapter.httpx.AsyncClient",
        return_value=ClientCtx(),
    ):
        chunks = []
        async for chunk in OllamaLLMAdapter("http://ollama:11434").generate_stream(
            [{"role": "user", "content": "hi"}]
        ):
            chunks.append(chunk)
    assert chunks == ["hel", "lo"]


# ---------------------------------------------------------------------------
# Neo4jKnowledgeGraphRepository — driver mocked
# ---------------------------------------------------------------------------

class _FakeNeo4jSessionCtx:
    """async-with stub that yields a session whose .run() returns a
    pre-canned Neo4jResult-shaped MagicMock."""

    def __init__(self, fake_result):
        self._fake_result = fake_result

    async def __aenter__(self):
        session = MagicMock()
        session.run = AsyncMock(return_value=self._fake_result)
        return session

    async def __aexit__(self, *_):
        return False


def _result_with_data(records: list[dict]):
    r = MagicMock()
    r.data = AsyncMock(return_value=records)
    return r


def _result_with_single(record):
    r = MagicMock()
    r.single = AsyncMock(return_value=record)
    return r


def _driver_with_session_returning(fake_result):
    """Build an AsyncDriver mock where .session() returns the canned ctx."""
    driver = MagicMock()
    driver.session = lambda: _FakeNeo4jSessionCtx(fake_result)
    return driver


def _driver_with_session_raising(exc):
    driver = MagicMock()

    class Boom:
        async def __aenter__(self):
            raise exc

        async def __aexit__(self, *_):
            return False

    driver.session = lambda: Boom()
    return driver


@pytest.mark.asyncio
async def test_neo4j_fulltext_search_empty_query_returns_empty():
    repo = Neo4jKnowledgeGraphRepository(_driver_with_session_returning(_result_with_data([])))
    out = await repo.fulltext_search("   ")
    assert out == []


@pytest.mark.asyncio
async def test_neo4j_fulltext_search_returns_notes_with_scores():
    records = [
        {
            "id": "n1", "title": "T1", "content": "c1",
            "tags": "a, b", "headings": "h1, h2",
            "word_count": 10, "has_code": True, "has_mermaid": False,
            "score": 0.95,
        },
        {
            "id": "n2", "title": "T2", "content": "c2",
            "tags": ["x", "y"], "headings": ["h3"],
            "score": 0.5,
        },
    ]
    repo = Neo4jKnowledgeGraphRepository(_driver_with_session_returning(_result_with_data(records)))
    out = await repo.fulltext_search("trading", limit=10)
    assert len(out) == 2
    note1, score1 = out[0]
    assert note1.id == "n1"
    assert note1.title == "T1"
    # Comma-separated string tag normalized to a list.
    assert note1.tags == ["a", "b"]
    assert note1.has_code is True
    assert score1 == 0.95
    # Already-list tags pass through.
    assert out[1][0].tags == ["x", "y"]


@pytest.mark.asyncio
async def test_neo4j_fulltext_search_falls_back_on_exception():
    """When the fulltext call raises, fallback is attempted (the second
    `async with self._driver.session()` call)."""
    driver = MagicMock()
    states = {"call": 0}

    class Once:
        async def __aenter__(self):
            states["call"] += 1
            if states["call"] == 1:
                raise RuntimeError("fulltext index missing")
            session = MagicMock()
            session.run = AsyncMock(return_value=_result_with_data([
                {"id": "n1", "title": "T", "content": "c"}
            ]))
            return session

        async def __aexit__(self, *_):
            return False

    driver.session = lambda: Once()
    repo = Neo4jKnowledgeGraphRepository(driver)
    out = await repo.fulltext_search("query", limit=5)
    # Fallback ran and returned 1 record.
    assert len(out) == 1
    assert out[0][0].id == "n1"
    assert out[0][1] == 1.0  # fallback score


@pytest.mark.asyncio
async def test_neo4j_fallback_search_raises_GraphQueryError_when_neo4j_dead():
    """Both fulltext and the fallback raise → GraphQueryError out."""
    repo = Neo4jKnowledgeGraphRepository(_driver_with_session_raising(RuntimeError("down")))
    with pytest.raises(GraphQueryError):
        # Call fallback directly (fulltext also errors and triggers
        # this path, but invoking it directly keeps the assertion clean).
        await repo._fallback_search("q", 5)


@pytest.mark.asyncio
async def test_neo4j_search_by_tags_returns_notes():
    records = [
        {"id": "n1", "title": "T1", "content": "c1", "tags": ["python", "fastapi"]},
    ]
    repo = Neo4jKnowledgeGraphRepository(_driver_with_session_returning(_result_with_data(records)))
    notes = await repo.search_by_tags(["python"], limit=10)
    assert [n.id for n in notes] == ["n1"]


@pytest.mark.asyncio
async def test_neo4j_search_by_tags_returns_empty_on_exception():
    repo = Neo4jKnowledgeGraphRepository(_driver_with_session_raising(RuntimeError("down")))
    out = await repo.search_by_tags(["python"])
    assert out == []


@pytest.mark.asyncio
async def test_neo4j_get_related_notes_returns_notes():
    records = [
        {"id": "n2", "title": "Related", "content": "linked-content"},
    ]
    repo = Neo4jKnowledgeGraphRepository(_driver_with_session_returning(_result_with_data(records)))
    out = await repo.get_related_notes("n1", limit=3)
    assert [n.id for n in out] == ["n2"]


@pytest.mark.asyncio
async def test_neo4j_get_related_notes_returns_empty_on_exception():
    repo = Neo4jKnowledgeGraphRepository(_driver_with_session_raising(RuntimeError("down")))
    out = await repo.get_related_notes("n1")
    assert out == []


@pytest.mark.asyncio
async def test_neo4j_get_stats_returns_counts():
    record = {"notes": 100, "tags": 20, "links": 50}
    repo = Neo4jKnowledgeGraphRepository(_driver_with_session_returning(_result_with_single(record)))
    stats = await repo.get_stats()
    assert stats == {"notes": 100, "tags": 20, "links": 50}


@pytest.mark.asyncio
async def test_neo4j_get_stats_returns_zeros_when_no_record():
    repo = Neo4jKnowledgeGraphRepository(_driver_with_session_returning(_result_with_single(None)))
    stats = await repo.get_stats()
    assert stats == {"notes": 0, "tags": 0, "links": 0}


@pytest.mark.asyncio
async def test_neo4j_get_stats_returns_zeros_on_exception():
    repo = Neo4jKnowledgeGraphRepository(_driver_with_session_raising(RuntimeError("down")))
    stats = await repo.get_stats()
    assert stats == {"notes": 0, "tags": 0, "links": 0}


@pytest.mark.asyncio
async def test_neo4j_health_check_true_on_record():
    repo = Neo4jKnowledgeGraphRepository(
        _driver_with_session_returning(_result_with_single({"ok": 1}))
    )
    assert await repo.health_check() is True


@pytest.mark.asyncio
async def test_neo4j_health_check_false_on_exception():
    repo = Neo4jKnowledgeGraphRepository(_driver_with_session_raising(RuntimeError("down")))
    assert await repo.health_check() is False
