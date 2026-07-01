"""Service layer — wires the ingest adapters into the event_reaction library.

Keeps EC1 discipline: the prior same-kind events handed to the surprise stage are
filtered to strictly BEFORE the event timestamp.
"""
from __future__ import annotations

from typing import Optional

import pandas as pd

from event_reaction import (
    DEFAULTS,
    cross_sectional_exposure,
    measure_event_reaction,
)


class EventReactionService:
    def __init__(self, price_source, event_repo=None):
        self.price_source = price_source
        self.event_repo = event_repo

    def measure(
        self,
        symbol: str,
        market_symbol: str,
        event: dict,
        *,
        method: str = "consensus",
        jump_n_null: int = 0,
    ):
        prices = self.price_source.history(symbol)
        market = self.price_source.history(market_symbol)
        ts = pd.Timestamp(event["ts_utc"])

        prior = None
        if self.event_repo is not None:
            hist = self.event_repo.fetch(kind=event.get("kind"))
            if len(hist):
                prior = hist[hist["ts_utc"] < ts]  # EC1: strictly-before only

        return measure_event_reaction(
            pd.Series(event), prices, market,
            params=DEFAULTS, prior_same_kind=prior, surprise_method=method,
            jump_n_null=jump_n_null,
        )

    def cross_section(self, rows: list[dict], *, cluster: str = "event_date"):
        panel = pd.DataFrame(rows)
        panel["event_date"] = pd.to_datetime(panel["event_date"], utc=True)
        return cross_sectional_exposure(panel, cluster=cluster)

    def ingest(self, rows: list[dict]) -> int:
        return self.event_repo.upsert(rows)

    def list_events(self, kind: Optional[str] = None) -> pd.DataFrame:
        return self.event_repo.fetch(kind=kind)
