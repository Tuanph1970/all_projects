"""KnowledgeNote entity - represents a note from the knowledge graph."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class KnowledgeNote:
    """Entity representing a note in the knowledge graph."""

    id: str
    title: str
    content: str
    filepath: str = ""
    folder: str = ""
    tags: list[str] = field(default_factory=list)
    headings: list[str] = field(default_factory=list)
    word_count: int = 0
    has_code: bool = False
    has_mermaid: bool = False
    created: Optional[datetime] = None
    modified: Optional[datetime] = None

    @property
    def snippet(self) -> str:
        """Return first 500 chars as snippet."""
        return self.content[:500] if self.content else ""

    def matches_keywords(self, keywords: list[str]) -> bool:
        """Check if note matches any of the given keywords."""
        text = f"{self.title} {self.content} {' '.join(self.tags)}".lower()
        return any(kw.lower() in text for kw in keywords)
