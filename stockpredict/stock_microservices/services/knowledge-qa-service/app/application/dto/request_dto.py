"""Request DTOs for the Knowledge QA API."""
from pydantic import BaseModel, Field
from typing import Optional


class AskQuestionRequest(BaseModel):
    """Request body for asking a question."""
    question: str = Field(..., min_length=1, max_length=2000, description="The question to ask")
    session_id: str = Field(..., min_length=1, max_length=100, description="Chat session ID")
    max_context_notes: int = Field(default=5, ge=1, le=20, description="Max notes to use as context")


class SearchNotesRequest(BaseModel):
    """Query params for searching notes."""
    q: str = Field(..., min_length=1, max_length=500, description="Search query")
    limit: int = Field(default=10, ge=1, le=50, description="Max results to return")


class ClearSessionRequest(BaseModel):
    """Request body for clearing a session."""
    pass
