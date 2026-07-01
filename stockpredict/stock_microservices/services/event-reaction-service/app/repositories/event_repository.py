"""MySqlEventRepository — implements the EventSource port over the SQL event store.

Materialises the events contract DataFrame[event_id, ts_utc(UTC), kind, actual,
consensus] (gap map §4). Works with any SQLAlchemy engine (MySQL in prod, sqlite in
tests). Upsert is keyed by event_id.
"""
from __future__ import annotations

from typing import Optional

import pandas as pd
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.domain import Base, EventRecord

_COLUMNS = ["event_id", "ts_utc", "kind", "actual", "consensus"]


class MySqlEventRepository:
    def __init__(self, engine: Engine):
        self._engine = engine
        self._Session = sessionmaker(bind=engine, expire_on_commit=False)

    def ensure_schema(self) -> None:
        Base.metadata.create_all(self._engine)

    def upsert(self, rows: list[dict]) -> int:
        with self._Session() as s:  # type: Session
            for r in rows:
                obj = s.get(EventRecord, r["event_id"])
                payload = {
                    "ts_utc": pd.Timestamp(r["ts_utc"]).to_pydatetime(),
                    "kind": r["kind"],
                    "actual": float(r["actual"]),
                    "consensus": None if r.get("consensus") is None else float(r["consensus"]),
                    "asset_scope": r.get("asset_scope"),
                }
                if obj is None:
                    s.add(EventRecord(event_id=r["event_id"], **payload))
                else:
                    for k, v in payload.items():
                        setattr(obj, k, v)
            s.commit()
        return len(rows)

    def fetch(
        self,
        kind: Optional[str] = None,
        since: Optional[pd.Timestamp] = None,
        until: Optional[pd.Timestamp] = None,
    ) -> pd.DataFrame:
        stmt = select(EventRecord)
        if kind is not None:
            stmt = stmt.where(EventRecord.kind == kind)
        if since is not None:
            stmt = stmt.where(EventRecord.ts_utc >= pd.Timestamp(since).to_pydatetime())
        if until is not None:
            stmt = stmt.where(EventRecord.ts_utc <= pd.Timestamp(until).to_pydatetime())
        stmt = stmt.order_by(EventRecord.ts_utc)

        with self._Session() as s:
            recs = s.scalars(stmt).all()

        if not recs:
            return pd.DataFrame(columns=_COLUMNS)
        df = pd.DataFrame(
            [
                {
                    "event_id": r.event_id,
                    "ts_utc": r.ts_utc,
                    "kind": r.kind,
                    "actual": r.actual,
                    "consensus": r.consensus,
                }
                for r in recs
            ]
        )
        # Force tz-aware UTC (sqlite may return naive) — EC6.
        df["ts_utc"] = pd.to_datetime(df["ts_utc"], utc=True)
        return df
