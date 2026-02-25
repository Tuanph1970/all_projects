"""Integration tests for Neo4jKnowledgeGraphRepository.

Requires a running Neo4j instance.
Skip with: pytest -m "not integration"
"""
import pytest
from app.infrastructure.persistence.neo4j_connection import get_neo4j_driver, close_neo4j_driver
from app.infrastructure.persistence.neo4j_knowledge_graph_repository import Neo4jKnowledgeGraphRepository

NEO4J_URI = "bolt://localhost:7687"


@pytest.fixture
async def repo():
    """Create repository connected to local Neo4j."""
    try:
        driver = await get_neo4j_driver(NEO4J_URI)
        repo = Neo4jKnowledgeGraphRepository(driver)
        yield repo
    except Exception:
        pytest.skip("Neo4j not available")
    finally:
        await close_neo4j_driver()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_health_check(repo):
    result = await repo.health_check()
    assert result is True


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_stats(repo):
    stats = await repo.get_stats()
    assert "notes" in stats
    assert "tags" in stats
    assert "links" in stats
    assert isinstance(stats["notes"], int)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_fulltext_search(repo):
    results = await repo.fulltext_search("trading", limit=3)
    # May return results if notes about trading exist
    assert isinstance(results, list)
    for note, score in results:
        assert note.title
        assert isinstance(score, float)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_search_by_tags(repo):
    results = await repo.search_by_tags(["trading"], limit=3)
    assert isinstance(results, list)
