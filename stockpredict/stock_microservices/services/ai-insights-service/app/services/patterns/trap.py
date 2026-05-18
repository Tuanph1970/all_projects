"""Bull / Bear trap detector (Schwager Ch 11, F-006).

A trap occurs when price appears to break a significant S/R level but
immediately reverses back inside the range, catching breakout traders on the
wrong side.

  Bull trap: price closes ABOVE resistance → closes back BELOW resistance
             within `revert_bars` bars.
  Bear trap: price closes BELOW support → closes back ABOVE support
             within `revert_bars` bars.

S/R levels are derived internally from fractal swing pivots so this detector
can run standalone without calling the analysis-service.  The decision-helper-
service can supply pre-computed typed levels (from F-003) via the optional
`sr_levels` constructor argument for higher accuracy.

Return shape (details dict):
    trap_type       : "bull_trap" | "bear_trap"
    severity        : 0..1  (how far price penetrated before reversing)
    bar_index       : absolute bar index of the trap entry bar
    level_breached  : the S/R price that was penetrated
    revert_bar      : bar index where price reverted inside the level
"""
from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np
import pandas as pd

from app.services.patterns.base import PatternDetector, PatternMatch
from app.services.patterns.continuation import _rolling_atr, _linreg


# ---------------------------------------------------------------------------
# Internal S/R level builder
# ---------------------------------------------------------------------------

def _build_sr_levels(
    ohlc: pd.DataFrame,
    swing_window: int = 3,
    cluster_pct: float = 0.025,
    lookback: int = 60,
) -> Tuple[List[float], List[float]]:
    """Return (supports, resistances) derived from fractal swing pivots.

    Pivots within `cluster_pct` of each other are merged into a single level
    at their mean price.  Uses only the most recent `lookback` bars so that
    stale levels from a prior trend don't contaminate the scan.
    """
    n = len(ohlc)
    start = max(0, n - lookback)
    sl = ohlc.iloc[start:]
    highs = sl["high"].to_numpy(dtype=float)
    lows = sl["low"].to_numpy(dtype=float)

    raw_highs = [highs[i] for i in PatternDetector._find_swing_highs(highs, swing_window)]
    raw_lows = [lows[i] for i in PatternDetector._find_swing_lows(lows, swing_window)]

    def _cluster(prices: List[float]) -> List[float]:
        if not prices:
            return []
        prices = sorted(prices)
        clusters: List[List[float]] = [[prices[0]]]
        for p in prices[1:]:
            ref = np.mean(clusters[-1])
            if abs(p - ref) / max(ref, 1e-8) <= cluster_pct:
                clusters[-1].append(p)
            else:
                clusters.append([p])
        return [float(np.mean(c)) for c in clusters]

    return _cluster(raw_lows), _cluster(raw_highs)


# ---------------------------------------------------------------------------
# TrapDetector
# ---------------------------------------------------------------------------

class TrapDetector(PatternDetector):
    """Bull / Bear trap detector (Schwager Ch 11).

    Scans the most recent `scan_bars` bars for penetration events at each
    S/R level and checks whether price reverted within `revert_bars` bars.
    Returns the most recent (rightmost) trap found, or None.
    """

    pattern_name = "Trap"
    pattern_type = "neutral"

    def __init__(
        self,
        revert_bars: int = 3,
        swing_window: int = 3,
        cluster_pct: float = 0.025,
        sr_lookback: int = 60,
        scan_bars: int = 30,
        min_penetration_pct: float = 0.002,
    ):
        self.revert_bars = revert_bars
        self.swing_window = swing_window
        self.cluster_pct = cluster_pct
        self.sr_lookback = sr_lookback
        self.scan_bars = scan_bars
        self.min_penetration_pct = min_penetration_pct

    def detect(self, ohlc: pd.DataFrame) -> Optional[PatternMatch]:
        ok, _ = self._validate_ohlc(ohlc, min_bars=self.swing_window * 4 + self.revert_bars + 5)
        if not ok:
            return None

        n = len(ohlc)
        close = ohlc["close"].to_numpy(dtype=float)
        high_a = ohlc["high"].to_numpy(dtype=float)
        low_a = ohlc["low"].to_numpy(dtype=float)
        atr = _rolling_atr(ohlc)

        supports, resistances = _build_sr_levels(
            ohlc, self.swing_window, self.cluster_pct, self.sr_lookback
        )

        scan_start = max(0, n - self.scan_bars)
        best: Optional[PatternMatch] = None

        for i in range(scan_start, n - self.revert_bars):
            ra = float(atr[i]) if not np.isnan(atr[i]) else 1.0

            # --- Bull trap: close above resistance, then revert below it. ---
            for res_level in resistances:
                if close[i] <= res_level:
                    continue
                penetration = close[i] - res_level
                if penetration < self.min_penetration_pct * res_level:
                    continue

                for j in range(i + 1, min(i + self.revert_bars + 1, n)):
                    if close[j] < res_level:
                        severity = min(1.0, penetration / ra)
                        target = res_level - (close[i] - res_level)  # measured move down
                        confidence = round(min(0.88, 0.50 + 0.30 * severity), 3)
                        match = PatternMatch(
                            pattern_name="Bull Trap",
                            pattern_type="bearish",
                            found=True,
                            confidence=confidence,
                            key_bars=[i, j],
                            measured_move_target=float(round(target, 4)),
                            neckline=float(round(res_level, 4)),
                            details={
                                "trap_type": "bull_trap",
                                "severity": float(round(severity, 3)),
                                "bar_index": int(i),
                                "level_breached": float(round(res_level, 4)),
                                "revert_bar": int(j),
                                "penetration": float(round(penetration, 4)),
                            },
                        )
                        if best is None or i > best.key_bars[0]:
                            best = match
                        break

            # --- Bear trap: close below support, then revert above it. ---
            for sup_level in supports:
                if close[i] >= sup_level:
                    continue
                penetration = sup_level - close[i]
                if penetration < self.min_penetration_pct * sup_level:
                    continue

                for j in range(i + 1, min(i + self.revert_bars + 1, n)):
                    if close[j] > sup_level:
                        severity = min(1.0, penetration / ra)
                        target = sup_level + (sup_level - close[i])
                        confidence = round(min(0.88, 0.50 + 0.30 * severity), 3)
                        match = PatternMatch(
                            pattern_name="Bear Trap",
                            pattern_type="bullish",
                            found=True,
                            confidence=confidence,
                            key_bars=[i, j],
                            measured_move_target=float(round(target, 4)),
                            neckline=float(round(sup_level, 4)),
                            details={
                                "trap_type": "bear_trap",
                                "severity": float(round(severity, 3)),
                                "bar_index": int(i),
                                "level_breached": float(round(sup_level, 4)),
                                "revert_bar": int(j),
                                "penetration": float(round(penetration, 4)),
                            },
                        )
                        if best is None or i > best.key_bars[0]:
                            best = match
                        break

        return best


# ---------------------------------------------------------------------------
# Aggregator helper
# ---------------------------------------------------------------------------

def run_trap_detectors(ohlc: pd.DataFrame) -> List[PatternMatch]:
    """Run the trap detector and return a list (0 or 1 items)."""
    try:
        m = TrapDetector().detect(ohlc)
        return [m] if m is not None and m.found else []
    except Exception:  # noqa: BLE001
        return []
