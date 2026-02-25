"""Abstract interface for knowledge graph access."""
from abc import ABC, abstractmethod
from typing import Optional

from app.domain.entities.knowledge_note import KnowledgeNote


class KnowledgeGraphRepository(ABC):
    """Port for accessing the knowledge graph."""

    @abstractmethod
    async def fulltext_search(
        self, query: str, limit: int = 5
    ) -> list[tuple[KnowledgeNote, float]]:
        """Full-text search returning notes with relevance scores."""
        ...

    @abstractmethod
    async def search_by_tags(
        self, keywords: list[str], limit: int = 5
    ) -> list[KnowledgeNote]:
        """Search notes by matching tags."""
        ...

    @abstractmethod
    async def get_related_notes(
        self, note_id: str, limit: int = 3
    ) -> list[KnowledgeNote]:
        """Get notes linked to the given note via LINKS_TO."""
        ...

    @abstractmethod
    async def get_stats(self) -> dict:
        """Return graph statistics (note count, tag count, link count)."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the graph database is reachable."""
        ...
