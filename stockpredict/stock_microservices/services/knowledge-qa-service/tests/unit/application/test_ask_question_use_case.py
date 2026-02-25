"""Tests for AskQuestionUseCase."""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock

from app.application.use_cases.ask_question import AskQuestionUseCase
from app.application.commands.commands import AskQuestionCommand
from app.domain.services.query_understanding import QueryUnderstandingService
from app.domain.services.graph_retrieval import GraphRetrievalService
from app.domain.services.answer_generation import AnswerGenerationService
from app.domain.entities.knowledge_note import KnowledgeNote
from app.domain.entities.chat_session import ChatSession
from app.domain.value_objects.graph_context import GraphContext
from app.domain.value_objects.note_reference import NoteReference
from app.infrastructure.external.prompt_builder import PromptBuilder
from app.infrastructure.persistence.in_memory_session_repository import InMemoryChatSessionRepository


@pytest.fixture
def notes():
    return [
        KnowledgeNote(id="n1", title="Trading", content="About trading", tags=["trading"]),
    ]


@pytest.fixture
def graph_context(notes):
    return GraphContext(
        notes=tuple(notes),
        references=(
            NoteReference(note_id="n1", title="Trading", relevance_score=0.9, snippet="About trading"),
        ),
        total_results=1,
    )


@pytest.fixture
def mock_retrieval(graph_context):
    service = AsyncMock(spec=GraphRetrievalService)
    service.retrieve_context.return_value = graph_context
    return service


@pytest.fixture
def mock_generation():
    service = AsyncMock(spec=AnswerGenerationService)

    async def mock_stream(messages):
        yield "Trading"
        yield " is"
        yield " important."

    service.generate_answer_stream = mock_stream
    return service


@pytest.mark.asyncio
async def test_ask_question_streams_response(mock_retrieval, mock_generation):
    session_repo = InMemoryChatSessionRepository()
    use_case = AskQuestionUseCase(
        query_service=QueryUnderstandingService(),
        retrieval_service=mock_retrieval,
        generation_service=mock_generation,
        session_repo=session_repo,
        prompt_builder=PromptBuilder(),
    )

    command = AskQuestionCommand(question="What is trading?", session_id="test-1")

    chunks = []
    async for chunk in use_case.execute(command):
        chunks.append(chunk)

    # Should have token chunks, sources chunk, and done chunk
    token_chunks = [c for c in chunks if '"type": "token"' in c]
    source_chunks = [c for c in chunks if '"type": "sources"' in c]
    done_chunks = [c for c in chunks if '"type": "done"' in c]

    assert len(token_chunks) == 3
    assert len(source_chunks) == 1
    assert len(done_chunks) == 1


@pytest.mark.asyncio
async def test_ask_question_saves_session(mock_retrieval, mock_generation):
    session_repo = InMemoryChatSessionRepository()
    use_case = AskQuestionUseCase(
        query_service=QueryUnderstandingService(),
        retrieval_service=mock_retrieval,
        generation_service=mock_generation,
        session_repo=session_repo,
        prompt_builder=PromptBuilder(),
    )

    command = AskQuestionCommand(question="test", session_id="sess-1")

    async for _ in use_case.execute(command):
        pass

    # Session should be saved
    session = await session_repo.get("sess-1")
    assert session is not None
    assert session.message_count == 2  # user + assistant


@pytest.mark.asyncio
async def test_ask_question_empty_raises(mock_retrieval, mock_generation):
    from app.domain.exceptions import EmptyQueryError

    session_repo = InMemoryChatSessionRepository()
    use_case = AskQuestionUseCase(
        query_service=QueryUnderstandingService(),
        retrieval_service=mock_retrieval,
        generation_service=mock_generation,
        session_repo=session_repo,
        prompt_builder=PromptBuilder(),
    )

    command = AskQuestionCommand(question="   ", session_id="test-1")

    with pytest.raises(EmptyQueryError):
        async for _ in use_case.execute(command):
            pass
