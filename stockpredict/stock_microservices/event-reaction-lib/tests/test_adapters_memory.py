"""T8 — ingest ports + in-memory adapters (SRS §4.3, NFR-1)."""
from __future__ import annotations

import pandas as pd
import pytest

from event_reaction.ingest import (
    EventSource,
    InMemoryEventSource,
    InMemoryOddsSource,
    InMemoryPriceSource,
    OddsSource,
    PriceSource,
)


def _events():
    return pd.DataFrame(
        {
            "event_id": ["e1", "e2", "e3"],
            "ts_utc": pd.to_datetime(
                ["2022-01-05", "2022-02-05", "2022-03-05"], utc=True
            ),
            "kind": ["rate_decision", "tariff", "rate_decision"],
            "actual": [0.5, 0.1, 0.75],
            "consensus": [0.25, 0.1, 0.5],
        }
    )


class TestProtocolConformance:
    def test_adapters_satisfy_ports(self):
        assert isinstance(InMemoryEventSource(_events()), EventSource)
        idx = pd.date_range("2022-01-03", periods=3, freq="B", tz="UTC")
        assert isinstance(InMemoryPriceSource({"AAA": pd.Series([1, 2, 3], index=idx)}), PriceSource)
        assert isinstance(InMemoryOddsSource({"r": pd.Series([0.1], index=idx[:1])}), OddsSource)


class TestEventSource:
    def test_filter_by_kind(self):
        src = InMemoryEventSource(_events())
        out = src.fetch(kind="rate_decision")
        assert list(out["event_id"]) == ["e1", "e3"]

    def test_filter_by_time_window(self):
        src = InMemoryEventSource(_events())
        out = src.fetch(since=pd.Timestamp("2022-02-01", tz="UTC"))
        assert list(out["event_id"]) == ["e2", "e3"]

    def test_emits_events_contract(self):
        out = InMemoryEventSource(_events()).fetch()
        assert {"event_id", "ts_utc", "kind", "actual", "consensus"} <= set(out.columns)
        assert str(out["ts_utc"].dt.tz) == "UTC"


class TestPriceSource:
    def test_history_slices_tz_aware(self):
        idx = pd.date_range("2022-01-03", periods=10, freq="B", tz="UTC")
        src = InMemoryPriceSource({"AAA": pd.Series(range(10), index=idx, dtype=float)})
        out = src.history("AAA", start=idx[2], end=idx[5])
        assert str(out.index.tz) == "UTC"
        assert len(out) == 4


class TestOddsSource:
    def test_values_in_unit_interval(self):
        idx = pd.date_range("2022-01-03", periods=3, freq="B", tz="UTC")
        s = pd.Series([0.1, 0.5, 0.9], index=idx)
        out = InMemoryOddsSource({"r": s}).series("r")
        assert out.between(0.0, 1.0).all()
