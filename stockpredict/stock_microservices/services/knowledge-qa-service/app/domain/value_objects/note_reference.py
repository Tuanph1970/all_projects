"""NoteReference value object - immutable reference to a source note."""
from dataclasses import dataclass


@dataclass(frozen=True)
class NoteReference:
    """Immutable reference to a knowledge note used as a source."""

    note_id: str
    title: str
    relevance_score: float
    snippet: str

    def to_dict(self) -> dict:
        return {
            "note_id": self.note_id,
            "title": self.title,
            "relevance_score": self.relevance_score,
            "snippet": self.snippet,
        }
