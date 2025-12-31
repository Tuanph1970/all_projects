"""Pydantic Schemas for Chatbot Service"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(BaseModel):
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = None


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    session_id: str
    message: str
    intent: Optional[str] = None
    entities: List[Dict[str, Any]] = []
    actions_taken: List[str] = []
    suggestions: List[str] = []
    timestamp: datetime


class ConversationHistory(BaseModel):
    session_id: str
    messages: List[Message]
    created_at: datetime
    last_activity: datetime


class SessionInfo(BaseModel):
    session_id: str
    user_id: Optional[int]
    message_count: int
    created_at: datetime
    last_activity: datetime
    context: Dict[str, Any]


class IntentType(str, Enum):
    STOCK_PRICE = "stock_price"
    STOCK_ANALYSIS = "stock_analysis"
    STOCK_PREDICTION = "stock_prediction"
    STOCK_COMPARISON = "stock_comparison"
    MARKET_OVERVIEW = "market_overview"
    PORTFOLIO_QUERY = "portfolio_query"
    GENERAL_QUESTION = "general_question"
    GREETING = "greeting"
    UNKNOWN = "unknown"


class DetectedIntent(BaseModel):
    intent: IntentType
    confidence: float
    entities: Dict[str, Any]


# Additional schemas for new endpoints

class FeedbackType(str, Enum):
    HELPFUL = "helpful"
    NOT_HELPFUL = "not_helpful"
    INCORRECT = "incorrect"
    NEEDS_IMPROVEMENT = "needs_improvement"


class FeedbackRequest(BaseModel):
    session_id: str
    message_index: int  # Which message in conversation
    feedback_type: FeedbackType
    comment: Optional[str] = Field(None, max_length=500)
    suggested_response: Optional[str] = Field(None, max_length=1000)


class FeedbackResponse(BaseModel):
    feedback_id: str
    session_id: str
    acknowledged: bool
    message: str


class ExportFormat(str, Enum):
    JSON = "json"
    TEXT = "text"
    MARKDOWN = "markdown"


class ExportResponse(BaseModel):
    session_id: str
    format: ExportFormat
    content: str
    message_count: int
    exported_at: datetime


class IntentInfo(BaseModel):
    intent: IntentType
    description: str
    example_queries: List[str]
    supported_entities: List[str]


class IntentsResponse(BaseModel):
    intents: List[IntentInfo]
    total: int


class UsageStats(BaseModel):
    total_sessions: int
    total_messages: int
    avg_messages_per_session: float
    top_intents: Dict[str, int]
    avg_response_time_ms: float
    satisfaction_rate: Optional[float]


class StatsResponse(BaseModel):
    period: str  # today, week, month, all
    stats: UsageStats
    generated_at: datetime
