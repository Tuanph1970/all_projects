"""GetChatHistory use case."""
from app.application.queries.queries import GetHistoryQuery
from app.application.dto.response_dto import ChatHistoryResponse
from app.application.mappers.entity_mapper import EntityMapper
from app.domain.ports.chat_session_repository import ChatSessionRepository
from app.domain.exceptions import SessionNotFoundError


class GetChatHistoryUseCase:
    """Retrieve chat session history."""

    def __init__(self, session_repo: ChatSessionRepository):
        self._session_repo = session_repo

    async def execute(self, query: GetHistoryQuery) -> ChatHistoryResponse:
        session = await self._session_repo.get(query.session_id)
        if session is None:
            return ChatHistoryResponse(
                session_id=query.session_id,
                messages=[],
                message_count=0,
            )

        messages = [EntityMapper.message_to_dto(m) for m in session.messages]
        return ChatHistoryResponse(
            session_id=session.id,
            messages=messages,
            message_count=session.message_count,
        )
