"""Factory for building GraphContext from raw Neo4j results."""
from app.domain.entities.knowledge_note import KnowledgeNote
from app.domain.value_objects.graph_context import GraphContext
from app.domain.value_objects.note_reference import NoteReference


class GraphContextFactory:
    """Factory pattern for building GraphContext from raw data."""

    @staticmethod
    def create_from_notes(
        notes_with_scores: list[tuple[KnowledgeNote, float]],
    ) -> GraphContext:
        """Create a GraphContext from a list of notes with scores."""
        references = tuple(
            NoteReference(
                note_id=note.id,
                title=note.title,
                relevance_score=score,
                snippet=note.snippet,
            )
            for note, score in notes_with_scores
        )

        return GraphContext(
            notes=tuple(note for note, _ in notes_with_scores),
            references=references,
            total_results=len(notes_with_scores),
        )
