"""T11 — FastAPI routes (offline, mocked sources)."""
from __future__ import annotations

_BASE = "/stock_helper/api/v2/event-reaction"


def test_health_live(client):
    r = client.get("/health/live")
    assert r.status_code == 200
    assert r.json() == {"status": "alive"}


def test_measure_returns_populated_reaction(client, price_index):
    body = {
        "symbol": "AAA",
        "market_symbol": "IDX",
        "event": {
            "event_id": "e1",
            "ts_utc": price_index[201].isoformat(),
            "kind": "rate_decision",
            "actual": 0.5,
            "consensus": 0.25,
        },
        "method": "consensus",
    }
    r = client.post(f"{_BASE}/measure", json=body)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["surprise"]["method"] == "consensus"
    assert isinstance(data["jump"]["is_jump"], bool)
    assert "car" in data["abnormal"]


def test_alignment_error_maps_to_422(client, price_index):
    # Event too close to the series start -> estimation window underflows -> AlignmentError.
    body = {
        "symbol": "AAA",
        "market_symbol": "IDX",
        "event": {
            "event_id": "e2",
            "ts_utc": price_index[5].isoformat(),
            "kind": "rate_decision",
            "actual": 0.5,
            "consensus": 0.25,
        },
    }
    r = client.post(f"{_BASE}/measure", json=body)
    assert r.status_code == 422


def test_ingest_and_list_roundtrip(client, price_index):
    body = {
        "events": [
            {
                "event_id": "x1",
                "ts_utc": price_index[10].isoformat(),
                "kind": "tariff",
                "actual": 0.2,
                "consensus": 0.1,
            }
        ]
    }
    r = client.post(f"{_BASE}/events", json=body)
    assert r.status_code == 200
    assert r.json()["ingested"] == 1
    listed = client.get(f"{_BASE}/events", params={"kind": "tariff"}).json()
    assert listed["data"][0]["event_id"] == "x1"
