"""AskQuestion use case - main RAG pipeline flow."""
import json
import time
import logging
from typing import AsyncIterator

from app.application.commands.commands import AskQuestionCommand
from app.domain.services.query_understanding import QueryUnderstandingService
from app.domain.services.graph_retrieval import GraphRetrievalService
from app.domain.services.answer_generation import AnswerGenerationService
from app.domain.ports.chat_session_repository import ChatSessionRepository
from app.domain.entities.chat_session import ChatSession
from app.domain.exceptions import EmptyQueryError
from app.infrastructure.external.prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)


class AskQuestionUseCase:
    """Main use case: receive question -> retrieve context -> generate answer -> stream back."""

    def __init__(
        self,
        query_service: QueryUnderstandingService,
        retrieval_service: GraphRetrievalService,
        generation_service: AnswerGenerationService,
        session_repo: ChatSessionRepository,
        prompt_builder: PromptBuilder,
    ):
        self._query_service = query_service
        self._retrieval_service = retrieval_service
        self._generation_service = generation_service
        self._session_repo = session_repo
        self._prompt_builder = prompt_builder

    async def execute(self, command: AskQuestionCommand) -> AsyncIterator[str]:
        """Execute the ask question pipeline, yielding SSE chunks."""
        if not command.question.strip():
            raise EmptyQueryError("Question cannot be empty")

        start_time = time.time()

        # 1. Get or create session
        session = await self._session_repo.get(command.session_id)
        if session is None:
            session = ChatSession(id=command.session_id)

        # 2. Add user message
        session.add_user_message(command.question)

        # 3. Parse query
        search_query = self._query_service.parse(command.question)
        logger.info(f"Parsed query: keywords={search_query.keywords}, intent={search_query.intent}")

        # 4. Retrieve context from graph
        graph_context = await self._retrieval_service.retrieve_context(
            search_query, max_notes=command.max_context_notes
        )
        logger.info(f"Retrieved {len(graph_context.notes)} notes from graph")

        # 5. Build LLM prompt
        history = session.get_history_for_llm(max_turns=5)
        messages = (
            self._prompt_builder
            .with_system_role()
            .with_context(graph_context)
            .with_chat_history(history)
            .with_user_question(command.question)
            .with_source_instruction()
            .build()
        )

        # 6. Stream answer from LLM
        full_answer = []
        async for token in self._generation_service.generate_answer_stream(messages):
            full_answer.append(token)
            yield f"data: {json.dumps({'type': 'token', 'data': token})}\n\n"

        # 7. Send sources
        sources_data = [ref.to_dict() for ref in graph_context.references]
        yield f"data: {json.dumps({'type': 'sources', 'data': sources_data})}\n\n"

        # 8. Save assistant message to session
        duration_ms = (time.time() - start_time) * 1000
        answer_text = "".join(full_answer)
        session.add_assistant_message(
            content=answer_text,
            sources=sources_data,
            duration_ms=duration_ms,
        )
        await self._session_repo.save(session)

        # 9. Done signal
        yield f"data: {json.dumps({'type': 'done', 'data': None})}\n\n"

        logger.info(f"Answer generated in {duration_ms:.0f}ms, {len(answer_text)} chars")
