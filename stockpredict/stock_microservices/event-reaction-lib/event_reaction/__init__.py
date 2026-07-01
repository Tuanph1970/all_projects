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

# Public API (SRS §4.2)
from event_reaction.cross_section import cross_sectional_exposure
from event_reaction.jumps import jump_test_daily
from event_reaction.pipeline import assert_no_leakage, measure_event_reaction
from event_reaction.returns import abnormal_returns
from event_reaction.surprise import make_surprise

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
    # public API (SRS §4.2)
    "measure_event_reaction",
    "assert_no_leakage",
    "make_surprise",
    "abnormal_returns",
    "jump_test_daily",
    "cross_sectional_exposure",
]
