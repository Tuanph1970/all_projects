"""SearchQuery value object - parsed user query with extracted keywords."""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class SearchQuery:
    """Parsed user query with extracted keywords and intent."""

    raw_query: str
    keywords: tuple[str, ...] = field(default_factory=tuple)
    intent: str = "general"  # "general" | "specific" | "comparison" | "definition"

    def to_search_string(self) -> str:
        """Convert keywords to a search-friendly string."""
        return " ".join(self.keywords) if self.keywords else self.raw_query
