"""Shared test fixtures — deterministic, seeded, fully offline (no I/O).

All price/odds series are tz-aware UTC (CLAUDE.md invariant). Builders return callables
so individual tests can size and shape their own synthetic data.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def rng():
    return np.random.default_rng(42)


@pytest.fixture
def utc_index():
    """Factory: a tz-aware UTC business-day DatetimeIndex of length n."""
    def _make(n: int, start: str = "2022-01-03") -> pd.DatetimeIndex:
        return pd.date_range(start=start, periods=n, freq="B", tz="UTC")
    return _make


@pytest.fixture
def price_series(rng, utc_index):
    """Factory: a tz-aware UTC daily price Series (geometric random walk)."""
    def _make(n: int = 400, mu: float = 0.0, sigma: float = 0.01, start: float = 100.0,
              seed: int | None = None) -> pd.Series:
        r = (rng if seed is None else np.random.default_rng(seed)).normal(mu, sigma, n)
        prices = start * np.exp(np.cumsum(r))
        return pd.Series(prices, index=utc_index(n), name="close")
    return _make


@pytest.fixture
def event_row():
    """Factory: one event as a pandas Series (a row of the events contract)."""
    def _make(ts_utc: str = "2022-06-01 18:00", kind: str = "rate_decision",
              actual: float = 0.50, consensus: float = 0.25) -> pd.Series:
        return pd.Series(
            {
                "event_id": "evt-1",
                "ts_utc": pd.Timestamp(ts_utc, tz="UTC"),
                "kind": kind,
                "actual": actual,
                "consensus": consensus,
            }
        )
    return _make
