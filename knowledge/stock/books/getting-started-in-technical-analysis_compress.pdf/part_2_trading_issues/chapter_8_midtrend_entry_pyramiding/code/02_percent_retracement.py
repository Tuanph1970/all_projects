"""
Concept 2 — Percent Retracement (Chapter 8, Strategy 1)
=======================================================
Enter a midtrend position when the market retraces a configurable
percentage of the prior price swing. Schwager suggests a 35–65% band.

Logic (long side):
    swing_low  = most recent relative low
    swing_high = most recent relative high (after swing_low)
    swing_size = swing_high - swing_low
    entry zone = swing_high - swing_size * pct
    stop       = swing_low (or just below it)
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import pandas as pd


@dataclass
class RetracementEntry:
    bar: int
    entry_price: float
    stop_price: float
    swing_low: float
    swing_high: float
    pct_retraced: float


def find_swing_points(prices: pd.Series, window: int = 5) -> tuple[list[int], list[int]]:
    """
    Return indices of relative lows and relative highs.
    A relative low/high is lower/higher than its `window` neighbors on each side.
    Endpoints are included as candidates if they are the extreme of the half-window
    they have available (so a series that starts at its low still produces a low at 0).
    """
    lows, highs = [], []
    p = prices.values
    n = len(p)
    for i in range(n):
        lo = max(0, i - window)
        hi = min(n, i + window + 1)
        seg = p[lo:hi]
        if p[i] == seg.min():
            lows.append(i)
        if p[i] == seg.max():
            highs.append(i)
    # de-duplicate consecutive plateau matches by keeping first occurrence
    def _thin(idxs):
        out = []
        for i in idxs:
            if not out or i - out[-1] >= window:
                out.append(i)
        return out
    return _thin(lows), _thin(highs)


class PercentRetracementStrategy:
    """Enter long when an uptrend pulls back X% of its last swing."""
    name = "percent_retracement"

    def __init__(self, retracement_pct: float = 0.50, swing_window: int = 5):
        if not 0.0 < retracement_pct < 1.0:
            raise ValueError("retracement_pct must be in (0, 1)")
        self.pct = retracement_pct
        self.swing_window = swing_window

    def generate(self, prices: pd.Series) -> list[RetracementEntry]:
        lows, highs = find_swing_points(prices, self.swing_window)
        entries: list[RetracementEntry] = []

        for hi_idx in highs:
            # find the most recent relative low that came BEFORE this high
            prior_lows = [l for l in lows if l < hi_idx]
            if not prior_lows:
                continue
            lo_idx = prior_lows[-1]

            swing_low = float(prices.iloc[lo_idx])
            swing_high = float(prices.iloc[hi_idx])
            if swing_high <= swing_low:
                continue

            target = swing_high - (swing_high - swing_low) * self.pct

            # scan forward for first bar that touches the retracement zone
            for j in range(hi_idx + 1, len(prices)):
                if prices.iloc[j] <= target:
                    entries.append(RetracementEntry(
                        bar=j,
                        entry_price=target,
                        stop_price=swing_low * 0.99,    # just below the low
                        swing_low=swing_low,
                        swing_high=swing_high,
                        pct_retraced=self.pct,
                    ))
                    break

        return entries


# ---------------------------------------------------------------------
if __name__ == "__main__":
    np.random.seed(1)
    # Three rally + pullback cycles. Pullbacks retrace ~60% of each rally
    # so the 50% retracement entry is actually triggered.
    legs = []
    base = 100.0
    for amp in (15, 12, 18):
        peak = base + amp
        trough = base + amp * 0.40            # 60% retracement of the rally
        legs.append(np.linspace(base, peak, 30))
        legs.append(np.linspace(peak, trough, 20))
        base = trough
    prices = pd.Series(
        np.concatenate(legs) + np.random.normal(0, 0.4, sum(len(l) for l in legs)),
        name="close",
    )

    strat = PercentRetracementStrategy(retracement_pct=0.50)
    signals = strat.generate(prices)

    print(f"Generated {len(signals)} retracement entries:")
    for s in signals[:5]:
        print(f"  bar={s.bar:3d}  entry={s.entry_price:6.2f}  "
              f"stop={s.stop_price:6.2f}  "
              f"swing={s.swing_low:.1f}->{s.swing_high:.1f}")

    # Sanity: every entry sits between swing_low and swing_high
    for s in signals:
        assert s.swing_low <= s.entry_price <= s.swing_high
    print("OK — all entries fall inside their swing range.")
