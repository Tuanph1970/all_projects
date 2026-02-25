"""ClearSession use case."""
from app.application.commands.commands import ClearSessionCommand
from app.application.dto.response_dto import ClearSessionResponse
from app.domain.ports.chat_session_repository import ChatSessionRepository


class ClearSessionUseCase:
    """Clear a chat session."""

    def __init__(self, session_repo: ChatSessionRepository):
        self._session_repo = session_repo

    async def execute(self, command: ClearSessionCommand) -> ClearSessionResponse:
        session = await self._session_repo.get(command.session_id)
        if session is not None:
            session.clear()
            await self._session_repo.save(session)

        return ClearSessionResponse(session_id=command.session_id)
