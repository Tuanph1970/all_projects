"""GetGraphStats use case."""
from app.application.queries.queries import GetStatsQuery
from app.application.dto.response_dto import GraphStatsResponse
from app.domain.ports.knowledge_graph_repository import KnowledgeGraphRepository


class GetGraphStatsUseCase:
    """Return knowledge graph statistics."""

    def __init__(self, graph_repo: KnowledgeGraphRepository):
        self._graph_repo = graph_repo

    async def execute(self, query: GetStatsQuery = None) -> GraphStatsResponse:
        stats = await self._graph_repo.get_stats()
        return GraphStatsResponse(
            total_notes=stats.get("notes", 0),
            total_tags=stats.get("tags", 0),
            total_links=stats.get("links", 0),
        )
