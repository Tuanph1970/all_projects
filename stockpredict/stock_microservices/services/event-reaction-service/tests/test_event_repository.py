"""T10 — MySqlEventRepository against sqlite (offline)."""
from __future__ import annotations

import pandas as pd


def _rows():
    return [
        {"event_id": "e1", "ts_utc": pd.Timestamp("2022-01-05 18:00", tz="UTC"),
         "kind": "rate_decision", "actual": 0.5, "consensus": 0.25, "asset_scope": "AAA"},
        {"event_id": "e2", "ts_utc": pd.Timestamp("2022-02-05 12:00", tz="UTC"),
         "kind": "tariff", "actual": 0.1, "consensus": 0.1, "asset_scope": None},
    ]


def test_upsert_then_fetch_returns_contract(sqlite_repo):
    sqlite_repo.upsert(_rows())
    df = sqlite_repo.fetch()
    assert {"event_id", "ts_utc", "kind", "actual", "consensus"} <= set(df.columns)
    assert str(df["ts_utc"].dt.tz) == "UTC"
    assert set(df["event_id"]) == {"e1", "e2"}


def test_fetch_filter_by_kind(sqlite_repo):
    sqlite_repo.upsert(_rows())
    df = sqlite_repo.fetch(kind="tariff")
    assert list(df["event_id"]) == ["e2"]


def test_upsert_is_idempotent_on_event_id(sqlite_repo):
    sqlite_repo.upsert(_rows())
    updated = dict(_rows()[0])
    updated["actual"] = 0.99
    sqlite_repo.upsert([updated])
    df = sqlite_repo.fetch(kind="rate_decision")
    assert len(df) == 1  # updated in place, not duplicated
    assert df.iloc[0]["actual"] == 0.99
