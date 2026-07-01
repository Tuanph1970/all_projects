"""Domain exceptions — all library-raised errors derive from EventReactionError.

Mirrors chart-decomp's exception hierarchy (NFR-3) so the service `_handle` can map
each class to an HTTP status.
"""
from __future__ import annotations


class EventReactionError(Exception):
    """Base for all event-reaction errors."""


class InsufficientDataError(EventReactionError):
    """Raised when a series/panel is too short to complete the requested operation."""


class AlignmentError(EventReactionError):
    """Raised when an event cannot be aligned to the price grid.

    Causes: naive (tz-unaware) datetime, or a required window extending beyond the
    available data (which would force look-ahead — EC1).
    """


class LeakageError(EventReactionError):
    """Raised by the no-leakage guard when a post-event mutation changes a pre-event
    quantity (EC1 / FR-NOLEAK)."""
