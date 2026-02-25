"""Domain events for the Knowledge QA bounded context."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class DomainEvent:
    """Base domain event."""
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class QuestionAskedEvent(DomainEvent):
    """Emitted when a user asks a question."""
    session_id: str = ""
    question: str = ""


@dataclass
class AnswerGeneratedEvent(DomainEvent):
    """Emitted when an answer is generated."""
    session_id: str = ""
    tokens_used: Optional[int] = None
    model: Optional[str] = None


@dataclass
class SessionCreatedEvent(DomainEvent):
    """Emitted when a new session is created."""
    session_id: str = ""


@dataclass
class SessionClearedEvent(DomainEvent):
    """Emitted when a session is cleared."""
    session_id: str = ""
