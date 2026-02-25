"""In-memory implementation of ChatSessionRepository."""
from typing import Optional

from app.domain.entities.chat_session import ChatSession
from app.domain.ports.chat_session_repository import ChatSessionRepository


class InMemoryChatSessionRepository(ChatSessionRepository):
    """In-memory storage for chat sessions."""

    def __init__(self):
        self._sessions: dict[str, ChatSession] = {}

    async def get(self, session_id: str) -> Optional[ChatSession]:
        return self._sessions.get(session_id)

    async def save(self, session: ChatSession) -> None:
        self._sessions[session.id] = session

    async def delete(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
