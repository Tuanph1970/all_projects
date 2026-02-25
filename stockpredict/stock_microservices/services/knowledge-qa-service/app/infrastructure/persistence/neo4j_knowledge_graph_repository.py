"""Neo4j implementation of KnowledgeGraphRepository."""
import logging
from typing import Optional
from neo4j import AsyncDriver

from app.domain.entities.knowledge_note import KnowledgeNote
from app.domain.ports.knowledge_graph_repository import KnowledgeGraphRepository
from app.domain.exceptions import GraphQueryError

logger = logging.getLogger(__name__)


class Neo4jKnowledgeGraphRepository(KnowledgeGraphRepository):
    """Implements KnowledgeGraphRepository using Neo4j."""

    def __init__(self, driver: AsyncDriver):
        self._driver = driver

    async def fulltext_search(
        self, query: str, limit: int = 5
    ) -> list[tuple[KnowledgeNote, float]]:
        """Full-text search using Neo4j full-text index."""
        if not query.strip():
            return []

        cypher = """
        CALL db.index.fulltext.queryNodes('note_search', $query)
        YIELD node, score
        RETURN node.id AS id, node.title AS title,
               left(node.content, 1000) AS content,
               node.filepath AS filepath, node.folder AS folder,
               node.tags AS tags, node.headings AS headings,
               node.word_count AS word_count,
               node.has_code AS has_code, node.has_mermaid AS has_mermaid,
               node.created AS created, node.modified AS modified,
               score
        ORDER BY score DESC
        LIMIT $limit
        """
        try:
            async with self._driver.session() as session:
                result = await session.run(cypher, parameters={"query": query, "limit": limit})
                records = await result.data()

            notes = []
            for record in records:
                note = self._record_to_note(record)
                notes.append((note, record.get("score", 0.0)))
            return notes
        except Exception as e:
            logger.error(f"Full-text search failed: {e}")
            # Fallback to CONTAINS search if fulltext index doesn't exist
            return await self._fallback_search(query, limit)

    async def _fallback_search(
        self, query: str, limit: int = 5
    ) -> list[tuple[KnowledgeNote, float]]:
        """Fallback search using CONTAINS when fulltext index is unavailable."""
        cypher = """
        MATCH (n:Note)
        WHERE toLower(n.title) CONTAINS toLower($query)
           OR toLower(n.content) CONTAINS toLower($query)
        RETURN n.id AS id, n.title AS title,
               left(n.content, 1000) AS content,
               n.filepath AS filepath, n.folder AS folder,
               n.tags AS tags, n.headings AS headings,
               n.word_count AS word_count,
               n.has_code AS has_code, n.has_mermaid AS has_mermaid,
               n.created AS created, n.modified AS modified,
               1.0 AS score
        LIMIT $limit
        """
        try:
            async with self._driver.session() as session:
                result = await session.run(cypher, parameters={"query": query, "limit": limit})
                records = await result.data()

            return [
                (self._record_to_note(r), r.get("score", 1.0))
                for r in records
            ]
        except Exception as e:
            logger.error(f"Fallback search failed: {e}")
            raise GraphQueryError(f"Graph search failed: {e}") from e

    async def search_by_tags(
        self, keywords: list[str], limit: int = 5
    ) -> list[KnowledgeNote]:
        """Search notes by matching tags."""
        cypher = """
        MATCH (n:Note)-[:TAGGED_WITH]->(t:Tag)
        WHERE ANY(kw IN $keywords WHERE toLower(t.name) CONTAINS toLower(kw))
        RETURN DISTINCT n.id AS id, n.title AS title,
               left(n.content, 1000) AS content,
               n.filepath AS filepath, n.folder AS folder,
               n.tags AS tags, n.headings AS headings,
               n.word_count AS word_count,
               n.has_code AS has_code, n.has_mermaid AS has_mermaid,
               n.created AS created, n.modified AS modified
        LIMIT $limit
        """
        try:
            async with self._driver.session() as session:
                result = await session.run(cypher, parameters={"keywords": keywords, "limit": limit})
                records = await result.data()

            return [self._record_to_note(r) for r in records]
        except Exception as e:
            logger.error(f"Tag search failed: {e}")
            return []

    async def get_related_notes(
        self, note_id: str, limit: int = 3
    ) -> list[KnowledgeNote]:
        """Get notes linked to the given note via LINKS_TO."""
        cypher = """
        MATCH (n:Note {id: $note_id})-[:LINKS_TO]->(related:Note)
        RETURN related.id AS id, related.title AS title,
               left(related.content, 500) AS content,
               related.filepath AS filepath, related.folder AS folder,
               related.tags AS tags, related.headings AS headings,
               related.word_count AS word_count,
               related.has_code AS has_code, related.has_mermaid AS has_mermaid,
               related.created AS created, related.modified AS modified
        LIMIT $limit
        """
        try:
            async with self._driver.session() as session:
                result = await session.run(cypher, parameters={"note_id": note_id, "limit": limit})
                records = await result.data()

            return [self._record_to_note(r) for r in records]
        except Exception as e:
            logger.error(f"Related notes query failed: {e}")
            return []

    async def get_stats(self) -> dict:
        """Return graph statistics."""
        cypher = """
        MATCH (n:Note) WITH count(n) AS notes
        OPTIONAL MATCH (t:Tag) WITH notes, count(t) AS tags
        OPTIONAL MATCH ()-[r:LINKS_TO]->()
        RETURN notes, tags, count(r) AS links
        """
        try:
            async with self._driver.session() as session:
                result = await session.run(cypher)
                record = await result.single()

            if record:
                return {
                    "notes": record["notes"],
                    "tags": record["tags"],
                    "links": record["links"],
                }
            return {"notes": 0, "tags": 0, "links": 0}
        except Exception as e:
            logger.error(f"Stats query failed: {e}")
            return {"notes": 0, "tags": 0, "links": 0}

    async def health_check(self) -> bool:
        """Check if Neo4j is reachable."""
        try:
            async with self._driver.session() as session:
                result = await session.run("RETURN 1 AS ok")
                record = await result.single()
                return record is not None and record["ok"] == 1
        except Exception:
            return False

    @staticmethod
    def _record_to_note(record: dict) -> KnowledgeNote:
        """Convert a Neo4j record to a KnowledgeNote entity."""
        tags = record.get("tags") or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]

        headings = record.get("headings") or []
        if isinstance(headings, str):
            headings = [h.strip() for h in headings.split(",") if h.strip()]

        return KnowledgeNote(
            id=record.get("id", ""),
            title=record.get("title", ""),
            content=record.get("content", ""),
            filepath=record.get("filepath", ""),
            folder=record.get("folder", ""),
            tags=tags,
            headings=headings,
            word_count=record.get("word_count", 0) or 0,
            has_code=bool(record.get("has_code", False)),
            has_mermaid=bool(record.get("has_mermaid", False)),
        )
