"""Domain event dataclasses — ADR-001 §4."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict


def _new_event_id() -> str:
    return str(uuid.uuid4())


@dataclass(frozen=True)
class DomainEvent:
    event_type: str
    payload: Dict[str, Any]
    aggregate_id: str                        # "user_id:ticker:bar_date"
    event_id: str = field(default_factory=_new_event_id)
    event_version: int = 1
    occurred_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    trace_id: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "event_version": self.event_version,
            "occurred_at": self.occurred_at,
            "aggregate_id": self.aggregate_id,
            "trace_id": self.trace_id,
            "payload": self.payload,
        }


# ---------------------------------------------------------------------------
# Concrete event constructors
# ---------------------------------------------------------------------------

def recommendation_created(
    run_id: int, user_id: int, ticker: str, bar_date: str,
    action: str, trigger: str, payload: Dict[str, Any],
) -> DomainEvent:
    return DomainEvent(
        event_type="decision.recommendation.created",
        aggregate_id=f"{user_id}:{ticker}:{bar_date}",
        payload={"run_id": run_id, "user_id": user_id, "ticker": ticker,
                 "bar_date": bar_date, "action": action, "trigger": trigger, **payload},
    )


def signal_failed(
    user_id: int, ticker: str, bar_date: str,
    signal_kind: str, failure_kind: str,
) -> DomainEvent:
    return DomainEvent(
        event_type="decision.signal.failed",
        aggregate_id=f"{user_id}:{ticker}:{bar_date}",
        payload={"signal_kind": signal_kind, "failure_kind": failure_kind,
                 "ticker": ticker, "bar_date": bar_date},
    )
