"""
Concept 5 — Reaction to Long-Term Moving Average (Strategy 4)
=============================================================
Premise: in an established uptrend, dips toward a long-term moving
average tend to mark "the reaction is over, trend is about to resume".
Schwager illustrates this with a 40-day MA on a stock chart.

Implementation:
    given a (you-decided) trend direction:
        UP   → buy on bars where price <= MA and the previous bar was > MA
        DOWN → sell on bars where price >= MA and the previous bar was < MA

Note: Schwager makes the point that this use of an MA crossover is
*counter*-trend (i.e., entering on the dip), as opposed to using
crossovers as trend-reversal signals. There is no contradiction — it's
just a different role for the same indicator.
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
class MAReactionEntry:
    bar: int
    side: str
    entry_price: float
    stop_price: float
    ma_value: float


class LongTermMAReactionStrategy:
    name = "long_term_ma_reaction"

    def __init__(self, trend: TrendDir, ma_period: int = 40,
                 stop_buffer_pct: float = 0.03):
        self.trend = trend
        self.ma_period = ma_period
        self.stop_buffer_pct = stop_buffer_pct

    def generate(self, prices: pd.Series) -> list[MAReactionEntry]:
        ma = prices.rolling(self.ma_period).mean()
        out: list[MAReactionEntry] = []
        for i in range(self.ma_period, len(prices)):
            ma_now = ma.iloc[i]
            ma_prev = ma.iloc[i - 1]
            p_now = prices.iloc[i]
            p_prev = prices.iloc[i - 1]
            if self.trend is TrendDir.UP:
                # price dips at/below MA having been above on the previous bar
                if p_now <= ma_now and p_prev > ma_prev:
                    out.append(MAReactionEntry(
                        bar=i, side="LONG",
                        entry_price=float(p_now),
                        stop_price=float(p_now) * (1 - self.stop_buffer_pct),
                        ma_value=float(ma_now),
                    ))
            else:
                if p_now >= ma_now and p_prev < ma_prev:
                    out.append(MAReactionEntry(
                        bar=i, side="SHORT",
                        entry_price=float(p_now),
                        stop_price=float(p_now) * (1 + self.stop_buffer_pct),
                        ma_value=float(ma_now),
                    ))
        return out


# ---------------------------------------------------------------------
if __name__ == "__main__":
    np.random.seed(11)
    n = 300
    t = np.arange(n)
    prices = pd.Series(
        100 + 0.30 * t                      # persistent uptrend
        + 5 * np.sin(t / 7)                 # cyclic pullbacks
        + np.random.normal(0, 0.7, n),
        name="close",
    )

    strat = LongTermMAReactionStrategy(TrendDir.UP, ma_period=40)
    sigs = strat.generate(prices)

    print(f"Generated {len(sigs)} dip-to-MA buy entries:")
    for s in sigs[:5]:
        print(f"  bar={s.bar:3d}  entry={s.entry_price:6.2f}  "
              f"stop={s.stop_price:6.2f}  MA={s.ma_value:6.2f}")

    for s in sigs:
        assert s.entry_price <= s.ma_value + 0.001
        assert s.stop_price < s.entry_price
    print(f"OK — all {len(sigs)} entries sit at/below MA with stop below.")
