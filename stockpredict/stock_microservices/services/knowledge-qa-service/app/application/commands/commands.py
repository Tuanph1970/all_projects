"""CQRS Commands for the Knowledge QA application."""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AskQuestionCommand:
    """Command to ask a question against the knowledge base."""
    question: str
    session_id: str
    max_context_notes: int = 5


@dataclass(frozen=True)
class ClearSessionCommand:
    """Command to clear a chat session."""
    session_id: str
