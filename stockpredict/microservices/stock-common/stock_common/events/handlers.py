"""
Event handler utilities and decorators.

Provides:
- @event_handler decorator for registering event handlers
- EventHandlerRegistry for managing handlers
"""

import logging
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Type

from stock_common.events.models import Event

logger = logging.getLogger(__name__)


class EventHandlerRegistry:
    """
    Registry for event handlers.

    Allows registering handlers for specific event types and
    dispatching events to the appropriate handlers.
    """

    def __init__(self):
        self._handlers: Dict[str, List[Callable[[Event], Any]]] = {}
        self._wildcard_handlers: List[Callable[[Event], Any]] = []

    def register(
        self,
        event_pattern: str,
        handler: Callable[[Event], Any],
    ) -> None:
        """
        Register a handler for an event pattern.

        Args:
            event_pattern: Event type pattern (e.g., 'stock.price.updated', 'stock.*')
            handler: Async function to handle the event
        """
        if event_pattern == "*" or event_pattern == "#":
            self._wildcard_handlers.append(handler)
        else:
            if event_pattern not in self._handlers:
                self._handlers[event_pattern] = []
            self._handlers[event_pattern].append(handler)
        logger.debug(f"Registered handler {handler.__name__} for pattern '{event_pattern}'")

    def unregister(
        self,
        event_pattern: str,
        handler: Optional[Callable[[Event], Any]] = None,
    ) -> None:
        """
        Unregister a handler or all handlers for a pattern.

        Args:
            event_pattern: Event type pattern
            handler: Specific handler to remove (removes all if None)
        """
        if handler is None:
            self._handlers.pop(event_pattern, None)
        elif event_pattern in self._handlers:
            self._handlers[event_pattern] = [
                h for h in self._handlers[event_pattern] if h != handler
            ]

    def get_handlers(self, event_type: str) -> List[Callable[[Event], Any]]:
        """
        Get all handlers matching an event type.

        Supports wildcard patterns:
        - 'stock.*' matches 'stock.price.updated', 'stock.company.synced', etc.
        - 'stock.#' matches any event starting with 'stock.'
        """
        handlers = list(self._wildcard_handlers)

        # Exact match
        if event_type in self._handlers:
            handlers.extend(self._handlers[event_type])

        # Wildcard matching
        parts = event_type.split(".")
        for pattern, pattern_handlers in self._handlers.items():
            pattern_parts = pattern.split(".")

            if self._matches_pattern(parts, pattern_parts):
                handlers.extend(pattern_handlers)

        return handlers

    def _matches_pattern(self, event_parts: List[str], pattern_parts: List[str]) -> bool:
        """Check if event type matches a pattern with wildcards."""
        if len(pattern_parts) > len(event_parts):
            return False

        for i, pattern_part in enumerate(pattern_parts):
            if pattern_part == "#":
                return True  # Match rest of the event type
            if pattern_part == "*":
                continue  # Match any single part
            if i >= len(event_parts) or pattern_part != event_parts[i]:
                return False

        return len(pattern_parts) == len(event_parts)

    async def dispatch(self, event: Event) -> List[Any]:
        """
        Dispatch an event to all matching handlers.

        Args:
            event: The event to dispatch

        Returns:
            List of results from all handlers
        """
        handlers = self.get_handlers(event.event_type)
        results = []

        for handler in handlers:
            try:
                result = await handler(event)
                results.append(result)
            except Exception as e:
                logger.error(f"Error in handler {handler.__name__}: {e}")
                raise

        return results


# Global registry instance
_registry = EventHandlerRegistry()


def event_handler(event_pattern: str):
    """
    Decorator for registering event handlers.

    Usage:
        @event_handler("stock.price.updated")
        async def handle_price_update(event: Event):
            print(f"Price updated: {event.payload}")

        @event_handler("stock.*")
        async def handle_all_stock_events(event: Event):
            print(f"Stock event: {event.event_type}")
    """

    def decorator(func: Callable[[Event], Any]):
        @wraps(func)
        async def wrapper(event: Event) -> Any:
            return await func(event)

        _registry.register(event_pattern, wrapper)
        return wrapper

    return decorator


def get_handler_registry() -> EventHandlerRegistry:
    """Get the global event handler registry."""
    return _registry
