"""
Event models for the event bus.

Defines the base Event class and metadata for event-driven communication.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class EventMetadata(BaseModel):
    """Metadata attached to every event."""

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: Optional[str] = Field(default=None, description="Correlation ID for tracing")
    causation_id: Optional[str] = Field(default=None, description="ID of the event that caused this event")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_service: str = Field(default="unknown", description="Service that published the event")
    version: str = Field(default="1.0", description="Event schema version")


class Event(BaseModel):
    """Base event model for all domain events."""

    event_type: str = Field(..., description="Event type identifier (e.g., 'stock.price.updated')")
    metadata: EventMetadata = Field(default_factory=EventMetadata)
    payload: Dict[str, Any] = Field(default_factory=dict, description="Event payload data")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

    def with_correlation(self, correlation_id: str) -> "Event":
        """Create a copy of the event with a correlation ID."""
        self.metadata.correlation_id = correlation_id
        return self

    def with_causation(self, causation_id: str) -> "Event":
        """Create a copy of the event with a causation ID."""
        self.metadata.causation_id = causation_id
        return self


# Pre-defined domain events
class DomainEvents:
    """Registry of domain event types."""

    # Stock Data Events
    STOCK_PRICE_UPDATED = "stock.price.updated"
    STOCK_COMPANY_SYNCED = "stock.company.synced"
    STOCK_DATA_AVAILABLE = "stock.data.available"
    STOCK_SYNC_REQUESTED = "stock.sync.requested"
    STOCK_SYNC_COMPLETED = "stock.sync.completed"
    STOCK_SYNC_FAILED = "stock.sync.failed"

    # Prediction Events
    PREDICTION_TRAINING_STARTED = "prediction.training.started"
    PREDICTION_TRAINING_PROGRESS = "prediction.training.progress"
    PREDICTION_TRAINING_COMPLETED = "prediction.training.completed"
    PREDICTION_TRAINING_FAILED = "prediction.training.failed"
    PREDICTION_GENERATED = "prediction.generated"
    PREDICTION_MODEL_CREATED = "prediction.model.created"
    PREDICTION_MODEL_UPDATED = "prediction.model.updated"

    # Portfolio Events
    PORTFOLIO_UPDATED = "portfolio.updated"
    PORTFOLIO_STOCK_ADDED = "portfolio.stock.added"
    PORTFOLIO_STOCK_REMOVED = "portfolio.stock.removed"
    PORTFOLIO_TRANSACTION_COMPLETED = "portfolio.transaction.completed"
    PORTFOLIO_ALERT_TRIGGERED = "portfolio.alert.triggered"
    PORTFOLIO_ALERT_CREATED = "portfolio.alert.created"

    # Analysis Events
    ANALYSIS_COMPLETED = "analysis.completed"
    ANALYSIS_PATTERN_DETECTED = "analysis.pattern.detected"
    ANALYSIS_REQUESTED = "analysis.requested"

    # AI Insights Events
    AI_INSIGHT_GENERATED = "ai.insight.generated"
    AI_PATTERN_DETECTED = "ai.pattern.detected"
    AI_RISK_ASSESSED = "ai.risk.assessed"
    AI_SENTIMENT_ANALYZED = "ai.sentiment.analyzed"

    # Chatbot Events
    CHATBOT_QUESTION_ASKED = "chatbot.question.asked"
    CHATBOT_RESPONSE_GENERATED = "chatbot.response.generated"

    # Auth Events
    AUTH_USER_REGISTERED = "auth.user.registered"
    AUTH_USER_LOGGED_IN = "auth.user.logged_in"
    AUTH_USER_LOGGED_OUT = "auth.user.logged_out"
    AUTH_PASSWORD_CHANGED = "auth.password.changed"
