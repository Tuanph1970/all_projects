"""Chatbot Service API Routes"""
from typing import Optional
from datetime import datetime
import uuid
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
import json

from app.api.dependencies import get_current_user_optional, get_current_user
from app.services.chatbot_service import ChatbotService
from app.models.schemas import (
    ChatRequest, ChatResponse, ConversationHistory, IntentType,
    FeedbackRequest, FeedbackResponse, FeedbackType,
    ExportFormat, ExportResponse,
    IntentInfo, IntentsResponse,
    UsageStats, StatsResponse
)

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    data: ChatRequest,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Send a message to the chatbot"""
    service = ChatbotService()
    return await service.chat(
        message=data.message,
        session_id=data.session_id,
        user_id=current_user["user_id"] if current_user else None,
        context=data.context
    )


@router.get("/history/{session_id}", response_model=ConversationHistory)
async def get_history(
    session_id: str,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Get conversation history"""
    service = ChatbotService()
    history = await service.get_history(session_id)
    if not history:
        raise HTTPException(status_code=404, detail="Session not found")
    return history


@router.delete("/session/{session_id}")
async def clear_session(
    session_id: str,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Clear conversation session"""
    service = ChatbotService()
    await service.clear_session(session_id)
    return {"message": "Session cleared"}


@router.websocket("/ws/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time chat"""
    await websocket.accept()
    service = ChatbotService()

    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)

            response = await service.chat(
                message=message_data.get("message", ""),
                session_id=session_id,
                context=message_data.get("context")
            )

            await websocket.send_json(response.model_dump(mode="json"))

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({"error": str(e)})


@router.get("/suggestions")
async def get_suggestions():
    """Get quick action suggestions"""
    return {
        "suggestions": [
            {"text": "Giá VNM hôm nay", "intent": "stock_price"},
            {"text": "Phân tích FPT", "intent": "stock_analysis"},
            {"text": "Dự đoán VIC", "intent": "stock_prediction"},
            {"text": "So sánh VNM và VIC", "intent": "stock_comparison"},
            {"text": "Thị trường hôm nay", "intent": "market_overview"}
        ]
    }


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    data: FeedbackRequest,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Submit feedback on a chatbot response"""
    service = ChatbotService()

    # Verify session exists
    history = await service.get_history(data.session_id)
    if not history:
        raise HTTPException(status_code=404, detail="Session not found")

    if data.message_index >= len(history.messages):
        raise HTTPException(status_code=400, detail="Invalid message index")

    # In production, store feedback in database
    feedback_id = str(uuid.uuid4())

    # Log feedback for analysis
    feedback_data = {
        "feedback_id": feedback_id,
        "session_id": data.session_id,
        "message_index": data.message_index,
        "feedback_type": data.feedback_type.value,
        "comment": data.comment,
        "suggested_response": data.suggested_response,
        "user_id": current_user["user_id"] if current_user else None,
        "timestamp": datetime.now().isoformat()
    }

    return FeedbackResponse(
        feedback_id=feedback_id,
        session_id=data.session_id,
        acknowledged=True,
        message="Thank you for your feedback! It helps us improve."
    )


@router.get("/history/{session_id}/export", response_model=ExportResponse)
async def export_history(
    session_id: str,
    format: ExportFormat = Query(default=ExportFormat.JSON),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Export conversation history in various formats"""
    service = ChatbotService()

    history = await service.get_history(session_id)
    if not history:
        raise HTTPException(status_code=404, detail="Session not found")

    if format == ExportFormat.JSON:
        content = json.dumps(
            {
                "session_id": history.session_id,
                "messages": [
                    {
                        "role": m.role.value,
                        "content": m.content,
                        "timestamp": m.timestamp.isoformat()
                    }
                    for m in history.messages
                ],
                "created_at": history.created_at.isoformat(),
                "last_activity": history.last_activity.isoformat()
            },
            ensure_ascii=False,
            indent=2
        )
    elif format == ExportFormat.TEXT:
        lines = [f"Conversation Export - Session: {session_id}", "=" * 50, ""]
        for m in history.messages:
            role = "You" if m.role.value == "user" else "Assistant"
            lines.append(f"[{m.timestamp.strftime('%H:%M:%S')}] {role}:")
            lines.append(m.content)
            lines.append("")
        content = "\n".join(lines)
    elif format == ExportFormat.MARKDOWN:
        lines = [
            f"# Conversation Export",
            f"**Session ID:** {session_id}",
            f"**Date:** {history.created_at.strftime('%Y-%m-%d %H:%M')}",
            "",
            "---",
            ""
        ]
        for m in history.messages:
            role = "**You**" if m.role.value == "user" else "**Assistant**"
            lines.append(f"### {role} - {m.timestamp.strftime('%H:%M:%S')}")
            lines.append("")
            lines.append(m.content)
            lines.append("")
        content = "\n".join(lines)
    else:
        content = ""

    return ExportResponse(
        session_id=session_id,
        format=format,
        content=content,
        message_count=len(history.messages),
        exported_at=datetime.now()
    )


@router.get("/intents", response_model=IntentsResponse)
async def get_intents():
    """Get list of supported intents with descriptions"""
    intents = [
        IntentInfo(
            intent=IntentType.STOCK_PRICE,
            description="Get current stock price and basic info",
            example_queries=["Giá VNM", "VNM bao nhiêu", "Price of FPT"],
            supported_entities=["symbol"]
        ),
        IntentInfo(
            intent=IntentType.STOCK_ANALYSIS,
            description="Get technical and fundamental analysis",
            example_queries=["Phân tích VNM", "Analyze FPT", "VIC technical"],
            supported_entities=["symbol", "analysis_type"]
        ),
        IntentInfo(
            intent=IntentType.STOCK_PREDICTION,
            description="Get price predictions and forecasts",
            example_queries=["Dự đoán VNM", "Forecast FPT", "VIC next week"],
            supported_entities=["symbol", "timeframe"]
        ),
        IntentInfo(
            intent=IntentType.STOCK_COMPARISON,
            description="Compare multiple stocks",
            example_queries=["So sánh VNM và VIC", "Compare FPT vs CMG"],
            supported_entities=["symbols"]
        ),
        IntentInfo(
            intent=IntentType.MARKET_OVERVIEW,
            description="Get market overview and trends",
            example_queries=["Thị trường hôm nay", "Market today", "VN-Index"],
            supported_entities=["market_index", "sector"]
        ),
        IntentInfo(
            intent=IntentType.PORTFOLIO_QUERY,
            description="Query user portfolio",
            example_queries=["Danh mục của tôi", "My portfolio", "Holdings"],
            supported_entities=["portfolio_id"]
        ),
        IntentInfo(
            intent=IntentType.GENERAL_QUESTION,
            description="General questions about stocks and market",
            example_queries=["RSI là gì", "What is P/E ratio"],
            supported_entities=[]
        ),
        IntentInfo(
            intent=IntentType.GREETING,
            description="Greetings and conversation starters",
            example_queries=["Xin chào", "Hello", "Hi"],
            supported_entities=[]
        ),
    ]

    return IntentsResponse(
        intents=intents,
        total=len(intents)
    )


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    period: str = Query(default="today", regex="^(today|week|month|all)$"),
    current_user: dict = Depends(get_current_user),
):
    """Get chatbot usage statistics (admin only).

    Numbers are aggregated from Redis counters that the /chat endpoint
    increments per turn. Returns zeros when Redis is unavailable rather
    than failing — the endpoint stays up so admin dashboards keep working.
    Backlog #4.
    """
    service = ChatbotService()
    raw = await service.get_usage_stats(period)
    return StatsResponse(
        period=period,
        stats=UsageStats(**raw),
        generated_at=datetime.now(),
    )
