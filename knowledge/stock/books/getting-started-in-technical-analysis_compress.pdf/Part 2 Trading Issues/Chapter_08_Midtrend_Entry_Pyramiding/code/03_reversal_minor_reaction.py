"""
Concept 3 — Reversal of Minor Reaction (Chapter 8, Strategy 2)
==============================================================
The idea: instead of guessing how far a pullback will go, *wait* for a
counter-trend wiggle to define itself, then enter when the main trend
resumes.

Definitions used in this implementation (long-side / uptrend):
    reaction defined  = a new N-day low (default N = 10)
    trend resumed     = close higher than the most recent X-day high
                        (default X = 3)
    protective stop   = the relative low that defined the reaction

(Mirror conditions for short-side / downtrend.)
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import numpy as np
import pandas as pd


class TrendDir(Enum):
    UP = 1
    DOWN = -1


@dataclass
class ReactionEntry:
    bar: int
    side: str
    entry_price: float
    stop_price: float
    reaction_extreme_bar: int
    reaction_extreme_price: float


class MinorReactionReversalStrategy:
    """
    Detect minor counter-trend reactions and enter on first sign the
    primary trend resumes.
    """
    name = "minor_reaction_reversal"

    def __init__(self, trend: TrendDir,
                 reaction_lookback: int = 10,
                 resumption_lookback: int = 3):
        self.trend = trend
        self.N = reaction_lookback
        self.X = resumption_lookback

    def generate(self, prices: pd.Series) -> list[ReactionEntry]:
        p = prices.values
        entries: list[ReactionEntry] = []
        i = self.N
        while i < len(p):
            if self.trend is TrendDir.UP:
                # reaction = today is the lowest of the last N days
                window = p[i-self.N:i+1]
                if p[i] == window.min():
                    react_bar = i
                    react_price = p[i]
                    # scan forward for trend resumption
                    j = i + 1
                    while j < len(p):
                        recent_high = p[max(0, j-self.X):j].max()
                        if p[j] > recent_high and p[j] > react_price:
                            entries.append(ReactionEntry(
                                bar=j, side="LONG",
                                entry_price=float(p[j]),
                                stop_price=float(react_price) * 0.99,
                                reaction_extreme_bar=react_bar,
                                reaction_extreme_price=float(react_price),
                            ))
                            i = j  # advance past this signal
                            break
                        j += 1
                    else:
                        i = len(p)
                        continue
            else:  # DOWN
                window = p[i-self.N:i+1]
                if p[i] == window.max():
                    react_bar = i
                    react_price = p[i]
                    j = i + 1
                    while j < len(p):
                        recent_low = p[max(0, j-self.X):j].min()
                        if p[j] < recent_low and p[j] < react_price:
                            entries.append(ReactionEntry(
                                bar=j, side="SHORT",
                                entry_price=float(p[j]),
                                stop_price=float(react_price) * 1.01,
                                reaction_extreme_bar=react_bar,
                                reaction_extreme_price=float(react_price),
                            ))
                            i = j
                            break
                        j += 1
                    else:
                        i = len(p)
                        continue
            i += 1
        return entries


# ---------------------------------------------------------------------
if __name__ == "__main__":
    np.random.seed(2)
    # Build a clean uptrend with periodic minor pullbacks
    n = 250
    t = np.arange(n)
    prices = pd.Series(
        100 + 0.25 * t                       # drift
        + 4 * np.sin(t / 6)                  # oscillation (creates reactions)
        + np.random.normal(0, 0.6, n),
        name="close",
    )

    strat = MinorReactionReversalStrategy(TrendDir.UP, 10, 3)
    sigs = strat.generate(prices)
    print(f"Generated {len(sigs)} long entries on minor-reaction reversals:")
    for s in sigs[:6]:
        print(f"  bar={s.bar:3d}  entry={s.entry_price:6.2f}  "
              f"stop={s.stop_price:6.2f}  "
              f"react_low={s.reaction_extreme_price:.2f}@bar{s.reaction_extreme_bar}")

    for s in sigs:
        # entry must be after the reaction
        assert s.bar > s.reaction_extreme_bar
        # for long entries, stop is below entry (long-side test)
        assert s.stop_price < s.entry_price
    print("OK — invariants hold.")
