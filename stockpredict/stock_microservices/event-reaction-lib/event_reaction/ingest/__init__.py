"""ingest stage — ADAPTERS ONLY (network/DB I/O lives here, SRS §4.3)."""
from event_reaction.ingest.http_price_source import HttpPriceSource
from event_reaction.ingest.memory import (
    InMemoryEventSource,
    InMemoryOddsSource,
    InMemoryPriceSource,
)
from event_reaction.ingest.ports import EventSource, OddsSource, PriceSource

__all__ = [
    "EventSource",
    "PriceSource",
    "OddsSource",
    "InMemoryEventSource",
    "InMemoryPriceSource",
    "InMemoryOddsSource",
    "HttpPriceSource",
]
