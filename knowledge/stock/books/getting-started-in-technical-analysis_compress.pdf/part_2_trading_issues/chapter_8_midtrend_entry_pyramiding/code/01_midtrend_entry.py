"""
Concept 1 — Midtrend Entry (Chapter 8)
======================================
A framework / orchestrator that delegates to one of four concrete
midtrend entry strategies. Useful as the top-level entry point for a
backtest that compares strategies on the same price series.

Strategies:
    1. PercentRetracementStrategy
    2. MinorReactionReversalStrategy
    3. ContinuationBreakoutStrategy
    4. LongTermMAReactionStrategy
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Protocol
import numpy as np
import pandas as pd


class Side(Enum):
    LONG = 1
    SHORT = -1


@dataclass
class Signal:
    bar_index: int
    side: Side
    entry_price: float
    stop_price: float
    reason: str


class MidtrendStrategy(Protocol):
    """Anything that can scan a price series and emit entry signals."""
    name: str
    def generate(self, prices: pd.Series) -> list[Signal]: ...


class MidtrendEntryEngine:
    """
    Orchestrates one or more midtrend entry strategies over the same
    price series. The point of the chapter — never refuse to enter a
    valid trend just because price has already moved a lot — is encoded
    here as a *positive policy*: as long as a strategy fires, we take
    the signal (subject to risk control).
    """

    def __init__(self, strategies: list[MidtrendStrategy],
                 max_risk_per_trade: float = 0.02):
        self.strategies = strategies
        self.max_risk_per_trade = max_risk_per_trade

    def scan(self, prices: pd.Series) -> pd.DataFrame:
        rows = []
        for strat in self.strategies:
            for s in strat.generate(prices):
                risk = abs(s.entry_price - s.stop_price) / s.entry_price
                rows.append({
                    "strategy": strat.name,
                    "bar": s.bar_index,
                    "side": s.side.name,
                    "entry": round(s.entry_price, 2),
                    "stop": round(s.stop_price, 2),
                    "risk_pct": round(risk * 100, 2),
                    "passes_risk": risk <= self.max_risk_per_trade,
                    "reason": s.reason,
                })
        return pd.DataFrame(rows)


# ---------------------------------------------------------------------
# Demo with synthetic data + one toy strategy (others are in their own
# files). Run this file directly to see the engine wiring.
# ---------------------------------------------------------------------
if __name__ == "__main__":
    np.random.seed(7)
    prices = pd.Series(
        100 + np.cumsum(np.random.normal(0.3, 1.0, 200)),
        name="close",
    )

    class DummyStrategy:
        name = "dummy_every_50"
        def generate(self, p: pd.Series) -> list[Signal]:
            return [Signal(i, Side.LONG, float(p.iloc[i]),
                           float(p.iloc[i]) * 0.97, "demo")
                    for i in range(50, len(p), 50)]

    engine = MidtrendEntryEngine([DummyStrategy()])
    print(engine.scan(prices))
