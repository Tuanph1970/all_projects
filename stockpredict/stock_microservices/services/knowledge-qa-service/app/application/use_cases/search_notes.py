"""SearchNotes use case."""
from app.application.queries.queries import SearchNotesQuery
from app.application.dto.response_dto import SearchNotesResponse
from app.application.mappers.entity_mapper import EntityMapper
from app.domain.services.query_understanding import QueryUnderstandingService
from app.domain.ports.knowledge_graph_repository import KnowledgeGraphRepository


class SearchNotesUseCase:
    """Search notes directly in the knowledge base."""

    def __init__(
        self,
        query_service: QueryUnderstandingService,
        graph_repo: KnowledgeGraphRepository,
    ):
        self._query_service = query_service
        self._graph_repo = graph_repo

    async def execute(self, query: SearchNotesQuery) -> SearchNotesResponse:
        search_query = self._query_service.parse(query.query)

        results = await self._graph_repo.fulltext_search(
            search_query.to_search_string(), limit=query.limit
        )

        notes_dto = [
            EntityMapper.note_to_search_dto(note, score)
            for note, score in results
        ]

        return SearchNotesResponse(
            query=query.query,
            results=notes_dto,
            total=len(notes_dto),
        )
