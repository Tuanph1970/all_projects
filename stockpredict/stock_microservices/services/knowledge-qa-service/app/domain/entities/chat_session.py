"""ChatSession aggregate root - manages a conversation session."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid

from app.domain.entities.chat_message import ChatMessage
from app.domain.events.domain_events import (
    SessionCreatedEvent,
    SessionClearedEvent,
    QuestionAskedEvent,
    AnswerGeneratedEvent,
)


@dataclass
class ChatSession:
    """Aggregate root for a chat conversation session."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    messages: list[ChatMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict = field(default_factory=dict)
    _events: list = field(default_factory=list, repr=False)

    def __post_init__(self):
        if not self.messages:
            self._events.append(SessionCreatedEvent(session_id=self.id))

    def add_user_message(self, content: str) -> ChatMessage:
        """Add a user message to the session."""
        message = ChatMessage(role="user", content=content)
        self.messages.append(message)
        self.updated_at = datetime.utcnow()
        self._events.append(
            QuestionAskedEvent(session_id=self.id, question=content)
        )
        return message

    def add_assistant_message(
        self,
        content: str,
        sources: Optional[list[dict]] = None,
        tokens_used: Optional[int] = None,
        model: Optional[str] = None,
        duration_ms: Optional[float] = None,
    ) -> ChatMessage:
        """Add an assistant response to the session."""
        message = ChatMessage(
            role="assistant",
            content=content,
            sources=sources or [],
            tokens_used=tokens_used,
            model=model,
            duration_ms=duration_ms,
        )
        self.messages.append(message)
        self.updated_at = datetime.utcnow()
        self._events.append(
            AnswerGeneratedEvent(
                session_id=self.id,
                tokens_used=tokens_used,
                model=model,
            )
        )
        return message

    def clear(self) -> None:
        """Clear all messages from the session."""
        self.messages.clear()
        self.updated_at = datetime.utcnow()
        self._events.append(SessionClearedEvent(session_id=self.id))

    def get_history_for_llm(self, max_turns: int = 10) -> list[dict]:
        """Get recent message history formatted for LLM context."""
        recent = self.messages[-max_turns * 2 :] if len(self.messages) > max_turns * 2 else self.messages
        return [{"role": m.role, "content": m.content} for m in recent]

    @property
    def message_count(self) -> int:
        return len(self.messages)

    def collect_events(self) -> list:
        """Collect and clear pending domain events."""
        events = self._events.copy()
        self._events.clear()
        return events
