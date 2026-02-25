"""Abstract interface for chat session storage."""
from abc import ABC, abstractmethod
from typing import Optional

from app.domain.entities.chat_session import ChatSession


class ChatSessionRepository(ABC):
    """Port for chat session persistence."""

    @abstractmethod
    async def get(self, session_id: str) -> Optional[ChatSession]:
        """Get a session by ID, or None if not found."""
        ...

    @abstractmethod
    async def save(self, session: ChatSession) -> None:
        """Save or update a session."""
        ...

    @abstractmethod
    async def delete(self, session_id: str) -> None:
        """Delete a session."""
        ...
