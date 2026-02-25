"""Domain service for orchestrating graph-based retrieval."""
from app.domain.ports.knowledge_graph_repository import KnowledgeGraphRepository
from app.domain.value_objects.search_query import SearchQuery
from app.domain.value_objects.graph_context import GraphContext
from app.domain.value_objects.note_reference import NoteReference


class GraphRetrievalService:
    """Orchestrates knowledge graph search and context assembly."""

    def __init__(self, graph_repo: KnowledgeGraphRepository):
        self._graph_repo = graph_repo

    async def retrieve_context(
        self, query: SearchQuery, max_notes: int = 5, include_related: bool = True
    ) -> GraphContext:
        """Retrieve relevant context from the knowledge graph."""
        notes_with_scores = []

        # 1. Full-text search using the raw query
        fulltext_results = await self._graph_repo.fulltext_search(
            query.to_search_string(), limit=max_notes
        )
        notes_with_scores.extend(fulltext_results)

        # 2. Tag-based search if we have keywords
        if query.keywords:
            tag_results = await self._graph_repo.search_by_tags(
                list(query.keywords), limit=max_notes
            )
            # Add tag results with a default score, avoiding duplicates
            existing_ids = {n.id for n, _ in notes_with_scores}
            for note in tag_results:
                if note.id not in existing_ids:
                    notes_with_scores.append((note, 0.5))
                    existing_ids.add(note.id)

        # 3. Sort by relevance and take top results
        notes_with_scores.sort(key=lambda x: x[1], reverse=True)
        top_notes = notes_with_scores[:max_notes]

        # 4. Optionally follow links for additional context
        if include_related and top_notes:
            existing_ids = {n.id for n, _ in top_notes}
            for note, _ in list(top_notes[:2]):  # Follow links from top 2
                related = await self._graph_repo.get_related_notes(note.id, limit=2)
                for rel_note in related:
                    if rel_note.id not in existing_ids and len(top_notes) < max_notes + 2:
                        top_notes.append((rel_note, 0.3))
                        existing_ids.add(rel_note.id)

        # 5. Build references
        references = tuple(
            NoteReference(
                note_id=note.id,
                title=note.title,
                relevance_score=score,
                snippet=note.snippet,
            )
            for note, score in top_notes
        )

        return GraphContext(
            notes=tuple(note for note, _ in top_notes),
            references=references,
            total_results=len(notes_with_scores),
        )
