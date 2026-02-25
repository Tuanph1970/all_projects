"""GraphContext value object - assembled context from graph traversal."""
from dataclasses import dataclass, field

from app.domain.entities.knowledge_note import KnowledgeNote
from app.domain.value_objects.note_reference import NoteReference


@dataclass(frozen=True)
class GraphContext:
    """Context assembled from knowledge graph traversal."""

    notes: tuple[KnowledgeNote, ...] = field(default_factory=tuple)
    references: tuple[NoteReference, ...] = field(default_factory=tuple)
    total_results: int = 0

    def to_context_string(self) -> str:
        """Build a context string for the LLM prompt."""
        if not self.notes:
            return "No relevant notes found in the knowledge base."

        parts = []
        for i, note in enumerate(self.notes, 1):
            tags_str = f" [Tags: {', '.join(note.tags)}]" if note.tags else ""
            parts.append(
                f"--- Source {i}: {note.title}{tags_str} ---\n{note.snippet}\n"
            )
        return "\n".join(parts)

    @property
    def has_results(self) -> bool:
        return len(self.notes) > 0

    @property
    def source_titles(self) -> list[str]:
        return [n.title for n in self.notes]
