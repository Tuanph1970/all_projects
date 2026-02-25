"""CQRS Queries for the Knowledge QA application."""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class GetHistoryQuery:
    """Query to retrieve chat session history."""
    session_id: str


@dataclass(frozen=True)
class SearchNotesQuery:
    """Query to search notes in the knowledge base."""
    query: str
    limit: int = 10


@dataclass(frozen=True)
class GetStatsQuery:
    """Query to retrieve knowledge graph statistics."""
    pass
