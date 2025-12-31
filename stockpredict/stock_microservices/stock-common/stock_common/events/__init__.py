"""
Event bus module for RabbitMQ-based event-driven communication.

Provides:
- EventBus: Async event publishing and consuming
- Event: Base event model
- EventHandler: Handler decorator for event consumers
"""

from stock_common.events.bus import EventBus
from stock_common.events.models import Event, EventMetadata
from stock_common.events.handlers import event_handler, EventHandlerRegistry

__all__ = [
    "EventBus",
    "Event",
    "EventMetadata",
    "event_handler",
    "EventHandlerRegistry",
]
