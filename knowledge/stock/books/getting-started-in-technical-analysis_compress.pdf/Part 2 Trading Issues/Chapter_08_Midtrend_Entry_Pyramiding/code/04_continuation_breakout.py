"""
Concept 4 — Continuation Pattern & Trading Range Breakouts (Strategy 3)
=======================================================================
Detect a stretch of bars where prices "go sideways" (a consolidation /
flag / triangle / trading range), then enter on a close that breaks out
of the consolidation in the direction of the prior trend.

This implementation uses a simple operational definition of a
consolidation:
    - at least `min_bars` bars
    - the high-low range of the consolidation is no more than
      `max_range_pct` of the consolidation's average price
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import pandas as pd


@dataclass
class BreakoutEntry:
    bar: int
    side: str
    entry_price: float
    stop_price: float
    consolidation_start: int
    consolidation_end: int
    consolidation_high: float
    consolidation_low: float


class ContinuationBreakoutStrategy:
    name = "continuation_breakout"

    def __init__(self,
                 min_bars: int = 5,
                 max_range_pct: float = 0.05,
                 trend_lookback: int = 30):
        self.min_bars = min_bars
        self.max_range_pct = max_range_pct
        self.trend_lookback = trend_lookback

    def _is_consolidation(self, segment: np.ndarray) -> bool:
        if len(segment) < self.min_bars:
            return False
        rng = segment.max() - segment.min()
        avg = segment.mean()
        return (rng / avg) <= self.max_range_pct

    def _prevailing_trend(self, prices: np.ndarray, end_idx: int) -> int:
        """Return +1 for uptrend, -1 for downtrend, 0 otherwise."""
        start = max(0, end_idx - self.trend_lookback)
        window = prices[start:end_idx + 1]
        if len(window) < 5:
            return 0
        slope = np.polyfit(range(len(window)), window, 1)[0]
        return 1 if slope > 0 else (-1 if slope < 0 else 0)

    def generate(self, prices: pd.Series) -> list[BreakoutEntry]:
        p = prices.values
        out: list[BreakoutEntry] = []
        i = 0
        while i < len(p) - self.min_bars:
            # Try to extend a consolidation starting at i
            best_end = -1
            for j in range(i + self.min_bars - 1, len(p)):
                if self._is_consolidation(p[i:j+1]):
                    best_end = j
                else:
                    break
            if best_end == -1:
                i += 1
                continue

            # Have a candidate consolidation [i, best_end]
            seg = p[i:best_end+1]
            seg_high = float(seg.max())
            seg_low  = float(seg.min())

            # Determine prior trend
            trend = self._prevailing_trend(p, i)

            # Look for breakout on first bar after consolidation
            for k in range(best_end + 1, len(p)):
                if trend > 0 and p[k] > seg_high:
                    out.append(BreakoutEntry(
                        bar=k, side="LONG",
                        entry_price=float(p[k]),
                        stop_price=seg_low,
                        consolidation_start=i,
                        consolidation_end=best_end,
                        consolidation_high=seg_high,
                        consolidation_low=seg_low,
                    ))
                    i = k
                    break
                if trend < 0 and p[k] < seg_low:
                    out.append(BreakoutEntry(
                        bar=k, side="SHORT",
                        entry_price=float(p[k]),
                        stop_price=seg_high,
                        consolidation_start=i,
                        consolidation_end=best_end,
                        consolidation_high=seg_high,
                        consolidation_low=seg_low,
                    ))
                    i = k
                    break
            else:
                i = best_end + 1
                continue
            i += 1
        return out


# ---------------------------------------------------------------------
if __name__ == "__main__":
    np.random.seed(3)
    # Up-rally → flag → resumption  (twice)
    legs = [
        np.linspace(100, 120, 30),               # rally
        120 + np.random.normal(0, 0.7, 12),      # consolidation
        np.linspace(121, 135, 25),               # resumption
        135 + np.random.normal(0, 0.6, 10),      # consolidation
        np.linspace(135, 150, 25),
    ]
    prices = pd.Series(np.concatenate(legs), name="close")

    strat = ContinuationBreakoutStrategy(min_bars=6, max_range_pct=0.04)
    sigs = strat.generate(prices)

    print(f"Generated {len(sigs)} breakout entries:")
    for s in sigs:
        print(f"  bar={s.bar:3d}  side={s.side}  entry={s.entry_price:6.2f}  "
              f"stop={s.stop_price:6.2f}  "
              f"box=[{s.consolidation_low:.1f},{s.consolidation_high:.1f}] "
              f"bars[{s.consolidation_start},{s.consolidation_end}]")

    for s in sigs:
        if s.side == "LONG":
            assert s.entry_price > s.consolidation_high
            assert s.stop_price < s.entry_price
    print("OK — long entries are above the box top, stops below.")
