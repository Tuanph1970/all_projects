"""Observer pattern - log domain events."""
import logging

from app.domain.events.domain_events import (
    DomainEvent,
    QuestionAskedEvent,
    AnswerGeneratedEvent,
    SessionCreatedEvent,
    SessionClearedEvent,
)

logger = logging.getLogger(__name__)


class LoggingEventHandler:
    """Handles domain events by logging them."""

    def handle(self, event: DomainEvent) -> None:
        """Log a domain event."""
        if isinstance(event, QuestionAskedEvent):
            logger.info(
                f"[Event] Question asked in session {event.session_id}: "
                f"{event.question[:100]}..."
            )
        elif isinstance(event, AnswerGeneratedEvent):
            logger.info(
                f"[Event] Answer generated in session {event.session_id}, "
                f"model={event.model}, tokens={event.tokens_used}"
            )
        elif isinstance(event, SessionCreatedEvent):
            logger.info(f"[Event] Session created: {event.session_id}")
        elif isinstance(event, SessionClearedEvent):
            logger.info(f"[Event] Session cleared: {event.session_id}")
        else:
            logger.info(f"[Event] {type(event).__name__} at {event.timestamp}")
