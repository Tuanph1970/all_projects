"""event_reaction — event-reaction measurement library.

Public API (SRS §4.2) is re-exported here as the stages land. Core principle:
markets price the *surprise*, not the raw event.
"""
from __future__ import annotations

from event_reaction.exceptions import (
    AlignmentError,
    EventReactionError,
    InsufficientDataError,
    LeakageError,
)
from event_reaction.types import (
    DEFAULTS,
    AbnormalReturns,
    AlignedEvent,
    CrossSectionExposure,
    EventReaction,
    JumpTest,
    Params,
    Surprise,
)

__all__ = [
    # exceptions
    "EventReactionError",
    "InsufficientDataError",
    "AlignmentError",
    "LeakageError",
    # types
    "DEFAULTS",
    "Params",
    "AlignedEvent",
    "Surprise",
    "AbnormalReturns",
    "JumpTest",
    "CrossSectionExposure",
    "EventReaction",
]
