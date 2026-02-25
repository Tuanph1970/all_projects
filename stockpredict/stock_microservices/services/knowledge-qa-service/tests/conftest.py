"""Test fixtures for Knowledge QA Service."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from app.domain.entities.knowledge_note import KnowledgeNote
from app.domain.entities.chat_session import ChatSession
from app.domain.entities.chat_message import ChatMessage
from app.domain.value_objects.graph_context import GraphContext
from app.domain.value_objects.note_reference import NoteReference
from app.domain.ports.knowledge_graph_repository import KnowledgeGraphRepository
from app.domain.ports.chat_session_repository import ChatSessionRepository
from app.domain.ports.llm_port import LLMPort


@pytest.fixture
def sample_note():
    """A sample knowledge note."""
    return KnowledgeNote(
        id="note-1",
        title="Trading Psychology",
        content="Trading psychology is about managing emotions. "
                "Fear and greed are the main emotions that affect trading decisions.",
        filepath="Trading/Psychology.md",
        folder="Trading",
        tags=["trading", "psychology", "emotions"],
        word_count=25,
    )


@pytest.fixture
def sample_notes():
    """Multiple sample notes."""
    return [
        KnowledgeNote(
            id="note-1",
            title="Trading Psychology",
            content="Trading psychology is about managing emotions.",
            tags=["trading", "psychology"],
        ),
        KnowledgeNote(
            id="note-2",
            title="Risk Management",
            content="Risk management involves position sizing and stop losses.",
            tags=["trading", "risk"],
        ),
        KnowledgeNote(
            id="note-3",
            title="Technical Analysis",
            content="Technical analysis uses charts and indicators.",
            tags=["analysis", "technical"],
        ),
    ]


@pytest.fixture
def sample_session():
    """A sample chat session with messages."""
    session = ChatSession(id="test-session-1")
    session.add_user_message("What is trading psychology?")
    session.add_assistant_message(
        content="Trading psychology involves managing emotions...",
        sources=[{"note_id": "note-1", "title": "Trading Psychology", "relevance_score": 0.9, "snippet": "..."}],
    )
    return session


@pytest.fixture
def mock_graph_repo(sample_notes):
    """Mock KnowledgeGraphRepository."""
    repo = AsyncMock(spec=KnowledgeGraphRepository)
    repo.fulltext_search.return_value = [(n, 0.9 - i * 0.1) for i, n in enumerate(sample_notes)]
    repo.search_by_tags.return_value = sample_notes[:2]
    repo.get_related_notes.return_value = [sample_notes[2]]
    repo.get_stats.return_value = {"notes": 100, "tags": 50, "links": 200}
    repo.health_check.return_value = True
    return repo


@pytest.fixture
def mock_session_repo(sample_session):
    """Mock ChatSessionRepository."""
    repo = AsyncMock(spec=ChatSessionRepository)
    repo.get.return_value = sample_session
    return repo


@pytest.fixture
def mock_llm_port():
    """Mock LLMPort."""
    port = AsyncMock(spec=LLMPort)

    async def mock_stream(messages):
        for word in ["Trading", " psychology", " is", " important."]:
            yield word

    port.generate_stream = mock_stream
    port.generate.return_value = "Trading psychology is important."
    port.health_check.return_value = True
    return port
