"""Dependency Injection container - wires all dependencies via FastAPI Depends()."""
from functools import lru_cache

from app.config import get_settings
from app.domain.services.query_understanding import QueryUnderstandingService
from app.domain.services.graph_retrieval import GraphRetrievalService
from app.domain.services.answer_generation import AnswerGenerationService
from app.infrastructure.persistence.neo4j_connection import get_neo4j_driver
from app.infrastructure.persistence.neo4j_knowledge_graph_repository import Neo4jKnowledgeGraphRepository
from app.infrastructure.persistence.in_memory_session_repository import InMemoryChatSessionRepository
from app.infrastructure.external.ollama_adapter import OllamaLLMAdapter
from app.infrastructure.external.prompt_builder import PromptBuilder
from app.application.use_cases.ask_question import AskQuestionUseCase
from app.application.use_cases.get_chat_history import GetChatHistoryUseCase
from app.application.use_cases.clear_session import ClearSessionUseCase
from app.application.use_cases.search_notes import SearchNotesUseCase
from app.application.use_cases.get_graph_stats import GetGraphStatsUseCase

# Singletons
_session_repo = InMemoryChatSessionRepository()
_query_service = QueryUnderstandingService()
_neo4j_repo: Neo4jKnowledgeGraphRepository | None = None
_ollama_adapter: OllamaLLMAdapter | None = None


async def _get_neo4j_repo() -> Neo4jKnowledgeGraphRepository:
    global _neo4j_repo
    if _neo4j_repo is None:
        settings = get_settings()
        driver = await get_neo4j_driver(
            settings.NEO4J_URI, settings.NEO4J_USER, settings.NEO4J_PASSWORD
        )
        _neo4j_repo = Neo4jKnowledgeGraphRepository(driver)
    return _neo4j_repo


def _get_ollama_adapter() -> OllamaLLMAdapter:
    global _ollama_adapter
    if _ollama_adapter is None:
        settings = get_settings()
        _ollama_adapter = OllamaLLMAdapter(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
            timeout=settings.OLLAMA_TIMEOUT,
        )
    return _ollama_adapter


async def get_ask_question_use_case() -> AskQuestionUseCase:
    neo4j_repo = await _get_neo4j_repo()
    ollama = _get_ollama_adapter()
    retrieval_service = GraphRetrievalService(neo4j_repo)
    generation_service = AnswerGenerationService(ollama)
    return AskQuestionUseCase(
        query_service=_query_service,
        retrieval_service=retrieval_service,
        generation_service=generation_service,
        session_repo=_session_repo,
        prompt_builder=PromptBuilder(),
    )


async def get_history_use_case() -> GetChatHistoryUseCase:
    return GetChatHistoryUseCase(session_repo=_session_repo)


async def get_clear_session_use_case() -> ClearSessionUseCase:
    return ClearSessionUseCase(session_repo=_session_repo)


async def get_search_notes_use_case() -> SearchNotesUseCase:
    neo4j_repo = await _get_neo4j_repo()
    return SearchNotesUseCase(
        query_service=_query_service,
        graph_repo=neo4j_repo,
    )


async def get_graph_stats_use_case() -> GetGraphStatsUseCase:
    neo4j_repo = await _get_neo4j_repo()
    return GetGraphStatsUseCase(graph_repo=neo4j_repo)
