"""Mappers between domain entities and DTOs."""
from app.domain.entities.chat_message import ChatMessage
from app.domain.entities.chat_session import ChatSession
from app.domain.entities.knowledge_note import KnowledgeNote
from app.domain.value_objects.note_reference import NoteReference
from app.application.dto.response_dto import (
    ChatMessageDTO,
    NoteReferenceDTO,
    SearchNoteDTO,
)


class EntityMapper:
    """Maps domain entities to/from DTOs."""

    @staticmethod
    def message_to_dto(message: ChatMessage) -> ChatMessageDTO:
        sources = [
            NoteReferenceDTO(**s) if isinstance(s, dict) else NoteReferenceDTO(
                note_id=s.note_id, title=s.title,
                relevance_score=s.relevance_score, snippet=s.snippet
            )
            for s in message.sources
        ]
        return ChatMessageDTO(
            id=message.id,
            role=message.role,
            content=message.content,
            sources=sources,
            timestamp=message.timestamp.isoformat(),
            tokens_used=message.tokens_used,
            model=message.model,
            duration_ms=message.duration_ms,
        )

    @staticmethod
    def note_to_search_dto(note: KnowledgeNote, score: float = 0.0) -> SearchNoteDTO:
        return SearchNoteDTO(
            id=note.id,
            title=note.title,
            snippet=note.snippet,
            tags=note.tags,
            relevance_score=score,
        )

    @staticmethod
    def reference_to_dto(ref: NoteReference) -> NoteReferenceDTO:
        return NoteReferenceDTO(
            note_id=ref.note_id,
            title=ref.title,
            relevance_score=ref.relevance_score,
            snippet=ref.snippet,
        )
