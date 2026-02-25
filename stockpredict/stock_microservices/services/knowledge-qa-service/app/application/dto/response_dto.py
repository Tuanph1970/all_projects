"""Response DTOs for the Knowledge QA API."""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class NoteReferenceDTO(BaseModel):
    """DTO for a source note reference."""
    note_id: str
    title: str
    relevance_score: float
    snippet: str


class ChatMessageDTO(BaseModel):
    """DTO for a chat message."""
    id: str
    role: str
    content: str
    sources: list[NoteReferenceDTO] = []
    timestamp: str
    tokens_used: Optional[int] = None
    model: Optional[str] = None
    duration_ms: Optional[float] = None


class ChatHistoryResponse(BaseModel):
    """Response for chat history."""
    session_id: str
    messages: list[ChatMessageDTO]
    message_count: int


class ClearSessionResponse(BaseModel):
    """Response for clearing a session."""
    session_id: str
    message: str = "Session cleared successfully"


class SearchNoteDTO(BaseModel):
    """DTO for a search result note."""
    id: str
    title: str
    snippet: str
    tags: list[str] = []
    relevance_score: float = 0.0


class SearchNotesResponse(BaseModel):
    """Response for note search."""
    query: str
    results: list[SearchNoteDTO]
    total: int


class GraphStatsResponse(BaseModel):
    """Response for graph statistics."""
    total_notes: int
    total_tags: int
    total_links: int


class HealthResponse(BaseModel):
    """Response for health check."""
    status: str
    service: str
    neo4j: str
    ollama: str


class StreamChunk(BaseModel):
    """A chunk in the SSE stream."""
    type: str  # "token" | "sources" | "done" | "error"
    data: str | list[dict] | None = None
