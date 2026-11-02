"""
Event bus module for RabbitMQ-based event-driven communication.

Provides:
- EventBus: Async event publishing and consuming
- Event: Base event model
- EventHandler: Handler decorator for event consumers
"""

from stock_common.events.bus import EventBus
from stock_common.events.models import Event, EventMetadata
from stock_common.events.routing import (
    PRICE_UPDATED_PATTERN,
    price_updated_routing_key,
    topic_matches,
)
from stock_common.events.handlers import event_handler, EventHandlerRegistry

__all__ = [
    "EventBus",
    "Event",
    "EventMetadata",
    "PRICE_UPDATED_PATTERN",
    "price_updated_routing_key",
    "topic_matches",
    "event_handler",
    "EventHandlerRegistry",
]
