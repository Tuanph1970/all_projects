"""Tests for GraphRetrievalService."""
import pytest
from unittest.mock import AsyncMock

from app.domain.services.graph_retrieval import GraphRetrievalService
from app.domain.value_objects.search_query import SearchQuery
from app.domain.entities.knowledge_note import KnowledgeNote


@pytest.fixture
def notes():
    return [
        KnowledgeNote(id="n1", title="Note 1", content="Content about trading", tags=["trading"]),
        KnowledgeNote(id="n2", title="Note 2", content="Content about risk", tags=["risk"]),
    ]


@pytest.fixture
def graph_repo(notes):
    repo = AsyncMock()
    repo.fulltext_search.return_value = [(notes[0], 0.9), (notes[1], 0.7)]
    repo.search_by_tags.return_value = []
    repo.get_related_notes.return_value = []
    return repo


@pytest.mark.asyncio
async def test_retrieve_context_basic(graph_repo, notes):
    service = GraphRetrievalService(graph_repo)
    query = SearchQuery(raw_query="trading", keywords=("trading",), intent="general")

    context = await service.retrieve_context(query, max_notes=5)

    assert context.has_results
    assert len(context.notes) == 2
    assert context.notes[0].id == "n1"
    assert len(context.references) == 2
    assert context.references[0].relevance_score == 0.9


@pytest.mark.asyncio
async def test_retrieve_context_empty(graph_repo):
    graph_repo.fulltext_search.return_value = []
    graph_repo.search_by_tags.return_value = []
    service = GraphRetrievalService(graph_repo)
    query = SearchQuery(raw_query="nonexistent", keywords=("nonexistent",))

    context = await service.retrieve_context(query)

    assert not context.has_results
    assert len(context.notes) == 0


@pytest.mark.asyncio
async def test_retrieve_context_with_related(graph_repo, notes):
    related = KnowledgeNote(id="n3", title="Related", content="Related content")
    graph_repo.get_related_notes.return_value = [related]
    service = GraphRetrievalService(graph_repo)
    query = SearchQuery(raw_query="trading", keywords=("trading",))

    context = await service.retrieve_context(query, max_notes=5, include_related=True)

    assert len(context.notes) == 3  # 2 fulltext + 1 related


@pytest.mark.asyncio
async def test_context_string_output(graph_repo, notes):
    service = GraphRetrievalService(graph_repo)
    query = SearchQuery(raw_query="trading", keywords=("trading",))

    context = await service.retrieve_context(query)
    context_str = context.to_context_string()

    assert "Note 1" in context_str
    assert "Note 2" in context_str
