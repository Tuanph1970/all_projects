"""FastAPI router for Knowledge QA endpoints - thin controller layer."""
import logging
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.application.commands.commands import AskQuestionCommand, ClearSessionCommand
from app.application.queries.queries import GetHistoryQuery, SearchNotesQuery, GetStatsQuery
from app.application.dto.request_dto import AskQuestionRequest
from app.application.dto.response_dto import (
    ChatHistoryResponse,
    ClearSessionResponse,
    SearchNotesResponse,
    GraphStatsResponse,
    HealthResponse,
)
from app.application.use_cases.ask_question import AskQuestionUseCase
from app.application.use_cases.get_chat_history import GetChatHistoryUseCase
from app.application.use_cases.clear_session import ClearSessionUseCase
from app.application.use_cases.search_notes import SearchNotesUseCase
from app.application.use_cases.get_graph_stats import GetGraphStatsUseCase
from app.api.dependencies import (
    get_ask_question_use_case,
    get_history_use_case,
    get_clear_session_use_case,
    get_search_notes_use_case,
    get_graph_stats_use_case,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/chat")
async def ask_question(
    request: AskQuestionRequest,
    use_case: AskQuestionUseCase = Depends(get_ask_question_use_case),
):
    """Ask a question against the knowledge base. Returns SSE stream."""
    command = AskQuestionCommand(
        question=request.question,
        session_id=request.session_id,
        max_context_notes=request.max_context_notes,
    )

    async def event_stream():
        async for chunk in use_case.execute(command):
            yield chunk

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/chat/history/{session_id}", response_model=ChatHistoryResponse)
async def get_chat_history(
    session_id: str,
    use_case: GetChatHistoryUseCase = Depends(get_history_use_case),
):
    """Get chat session history."""
    query = GetHistoryQuery(session_id=session_id)
    return await use_case.execute(query)


@router.post("/chat/clear/{session_id}", response_model=ClearSessionResponse)
async def clear_session(
    session_id: str,
    use_case: ClearSessionUseCase = Depends(get_clear_session_use_case),
):
    """Clear a chat session."""
    command = ClearSessionCommand(session_id=session_id)
    return await use_case.execute(command)


@router.get("/search", response_model=SearchNotesResponse)
async def search_notes(
    q: str = Query(..., min_length=1, max_length=500, description="Search query"),
    limit: int = Query(default=10, ge=1, le=50),
    use_case: SearchNotesUseCase = Depends(get_search_notes_use_case),
):
    """Search notes directly in the knowledge base."""
    query = SearchNotesQuery(query=q, limit=limit)
    return await use_case.execute(query)


@router.get("/stats", response_model=GraphStatsResponse)
async def get_graph_stats(
    use_case: GetGraphStatsUseCase = Depends(get_graph_stats_use_case),
):
    """Get knowledge graph statistics."""
    return await use_case.execute()
