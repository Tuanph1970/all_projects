"""ChatMessage entity - a single message in a chat session."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid


@dataclass
class ChatMessage:
    """A single message in a conversation."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    role: str = "user"  # "user" | "assistant" | "system"
    content: str = ""
    sources: list[dict] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    tokens_used: Optional[int] = None
    model: Optional[str] = None
    duration_ms: Optional[float] = None

    def is_user_message(self) -> bool:
        return self.role == "user"

    def is_assistant_message(self) -> bool:
        return self.role == "assistant"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "sources": self.sources,
            "timestamp": self.timestamp.isoformat(),
            "tokens_used": self.tokens_used,
            "model": self.model,
            "duration_ms": self.duration_ms,
        }
