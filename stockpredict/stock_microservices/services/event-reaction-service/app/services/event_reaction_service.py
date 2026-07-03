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
        ts = pd.Timestamp(event["ts_utc"])

        # Fetch a window sized around the event, not stock-data-service's default
        # (~1y of recent bars) which won't cover older events. The market model needs
        # L+g estimation bars strictly before t0 (plus the local-vol window); convert
        # that trading-bar budget to calendar days (~5 trading days / 7 calendar) and
        # pad generously for holidays / trading halts. End a bit past t0 to cover the
        # event window (k2) and the trailing jump window.
        bars_before = DEFAULTS.L + DEFAULTS.g + DEFAULTS.k1 + DEFAULTS.jump_local_window
        lookback_days = int(bars_before * 7 / 5) + 90  # buffer for market gaps
        start = ts - pd.Timedelta(days=lookback_days)
        end = ts + pd.Timedelta(days=30)

        prices = self.price_source.history(symbol, start=start, end=end)
        market = self.price_source.history(market_symbol, start=start, end=end)

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
