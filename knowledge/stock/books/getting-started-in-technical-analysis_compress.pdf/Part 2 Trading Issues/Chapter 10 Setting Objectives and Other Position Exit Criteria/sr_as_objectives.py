"""
Support and Resistance as Objectives — Chapter 10, Concept 3
=============================================================
Uses prior support and resistance levels as profit-taking zones.

Schwager's key insight: S/R levels represent only TEMPORARY
objectives. Plan to re-enter if a reaction develops at the
S/R target rather than committing the full exit there.

This module provides:
  - S/R level detection from price history
  - Objective zone identification for long and short positions
  - Role reversal detection (broken support → resistance, etc.)
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Literal


@dataclass
class SRLevel:
    """A support or resistance level derived from price history."""
    price: float
    role: str  # 'support' or 'resistance'
    strength: int  # Number of touches/tests
    source: str  # e.g., 'prior_high', 'prior_low', 'range_boundary'
    first_touch_idx: int = 0
    last_touch_idx: int = 0

    @property
    def description(self) -> str:
        return f"{self.role.capitalize()} at {self.price:.2f} ({self.strength} touches, from {self.source})"


@dataclass
class SRObjective:
    """
    A profit objective based on an S/R level.
    
    Schwager warns: these are TEMPORARY objectives.
    Use for partial exits, not full position closure.
    """
    level: SRLevel
    direction: str  # 'long' or 'short'
    entry_price: float
    objective_price: float
    profit_distance: float
    is_temporary: bool = True  # Schwager's explicit caveat
    reentry_advice: str = (
        "S/R objectives are temporary. Plan to re-enter "
        "at a better price if a reaction develops."
    )

    def risk_reward(self, stop_price: float) -> float:
        """R:R ratio given a stop-loss price."""
        risk = abs(self.entry_price - stop_price)
        if risk == 0:
            return float('inf')
        return self.profit_distance / risk


def find_sr_levels(
    highs: pd.Series,
    lows: pd.Series,
    closes: pd.Series,
    lookback: int = 20,
    tolerance_pct: float = 1.0,
    min_touches: int = 2
) -> List[SRLevel]:
    """
    Detect support and resistance levels from price history.
    
    Identifies price zones that have been tested multiple times
    (prior highs, prior lows, range boundaries).
    
    Parameters
    ----------
    highs, lows, closes : pd.Series
        OHLC data (high, low, close).
    lookback : int
        Window for detecting local extremes.
    tolerance_pct : float
        Max percentage distance to cluster touches into one level.
    min_touches : int
        Minimum tests to qualify as a significant level.
        
    Returns
    -------
    list of SRLevel
        Detected support and resistance levels sorted by strength.
    """
    # Find local highs (resistance candidates)
    local_highs = []
    local_lows = []
    
    half = lookback // 2
    for i in range(half, len(highs) - half):
        window_h = highs.iloc[i - half:i + half + 1]
        if highs.iloc[i] == window_h.max():
            local_highs.append((i, highs.iloc[i]))
        
        window_l = lows.iloc[i - half:i + half + 1]
        if lows.iloc[i] == window_l.min():
            local_lows.append((i, lows.iloc[i]))
    
    # Cluster nearby levels
    levels = []
    
    def cluster_prices(points, role, source):
        if not points:
            return
        sorted_pts = sorted(points, key=lambda x: x[1])
        used = set()
        for i, (idx_a, price_a) in enumerate(sorted_pts):
            if i in used:
                continue
            cluster = [(idx_a, price_a)]
            used.add(i)
            for j, (idx_b, price_b) in enumerate(sorted_pts):
                if j in used:
                    continue
                avg = (price_a + price_b) / 2
                if avg > 0 and abs(price_a - price_b) / avg * 100 <= tolerance_pct:
                    cluster.append((idx_b, price_b))
                    used.add(j)
            if len(cluster) >= min_touches:
                avg_price = np.mean([p for _, p in cluster])
                indices = [idx for idx, _ in cluster]
                levels.append(SRLevel(
                    price=round(avg_price, 2),
                    role=role,
                    strength=len(cluster),
                    source=source,
                    first_touch_idx=min(indices),
                    last_touch_idx=max(indices),
                ))
    
    cluster_prices(local_highs, 'resistance', 'prior_high')
    cluster_prices(local_lows, 'support', 'prior_low')
    
    levels.sort(key=lambda x: x.strength, reverse=True)
    return levels


def find_objectives(
    current_price: float,
    direction: Literal['long', 'short'],
    sr_levels: List[SRLevel],
    max_objectives: int = 3
) -> List[SRObjective]:
    """
    Find the nearest S/R levels that serve as profit objectives.
    
    For long positions: looks for resistance levels above current price.
    For short positions: looks for support levels below current price.
    
    Parameters
    ----------
    current_price : float
        Current entry or market price.
    direction : str
        'long' or 'short'.
    sr_levels : list of SRLevel
        All detected S/R levels.
    max_objectives : int
        Maximum number of objective levels to return.
        
    Returns
    -------
    list of SRObjective
        Nearest S/R objectives, sorted by distance from current price.
    """
    objectives = []
    
    for level in sr_levels:
        if direction == 'long' and level.price > current_price:
            # Resistance above = upside objective
            obj = SRObjective(
                level=level,
                direction='long',
                entry_price=current_price,
                objective_price=level.price,
                profit_distance=level.price - current_price,
            )
            objectives.append(obj)
        elif direction == 'short' and level.price < current_price:
            # Support below = downside objective
            obj = SRObjective(
                level=level,
                direction='short',
                entry_price=current_price,
                objective_price=level.price,
                profit_distance=current_price - level.price,
            )
            objectives.append(obj)
    
    objectives.sort(key=lambda x: x.profit_distance)
    return objectives[:max_objectives]


def detect_role_reversals(
    sr_levels: List[SRLevel],
    current_price: float,
    tolerance_pct: float = 1.5
) -> List[SRLevel]:
    """
    Detect S/R levels that have undergone role reversal.
    
    Chapter 4 principle: broken support becomes resistance,
    broken resistance becomes support. These reversed levels
    can serve as re-entry zones.
    
    Parameters
    ----------
    sr_levels : list of SRLevel
        Original S/R levels.
    current_price : float
        Current market price to determine which levels are broken.
    tolerance_pct : float
        How far price must be beyond the level to confirm a break.
        
    Returns
    -------
    list of SRLevel
        New levels with reversed roles.
    """
    reversed_levels = []
    
    for level in sr_levels:
        break_distance = abs(current_price - level.price) / level.price * 100
        if break_distance < tolerance_pct:
            continue  # Not clearly broken
        
        if level.role == 'resistance' and current_price > level.price:
            # Broken resistance → now support
            reversed_levels.append(SRLevel(
                price=level.price,
                role='support',
                strength=level.strength,
                source='role_reversal (was resistance)',
                first_touch_idx=level.first_touch_idx,
                last_touch_idx=level.last_touch_idx,
            ))
        elif level.role == 'support' and current_price < level.price:
            # Broken support → now resistance
            reversed_levels.append(SRLevel(
                price=level.price,
                role='resistance',
                strength=level.strength,
                source='role_reversal (was support)',
                first_touch_idx=level.first_touch_idx,
                last_touch_idx=level.last_touch_idx,
            ))
    
    return reversed_levels


# --- Example usage ---
if __name__ == "__main__":
    print("=== Manual S/R Objective Example ===")
    # Schwager's wheat example: two prior highs form support
    levels = [
        SRLevel(price=365.0, role='support', strength=2,
                source='prior_high', first_touch_idx=0, last_touch_idx=30),
        SRLevel(price=390.0, role='resistance', strength=3,
                source='prior_high', first_touch_idx=10, last_touch_idx=50),
    ]
    
    # Short entry at 385
    objs = find_objectives(385.0, 'short', levels)
    for o in objs:
        print(f"  Objective: {o.objective_price} ({o.level.source})")
        print(f"  Profit distance: {o.profit_distance:.1f}")
        print(f"  R:R at stop 395: {o.risk_reward(395.0):.2f}")
        print(f"  Temporary? {o.is_temporary}")
        print(f"  Advice: {o.reentry_advice}")
    print()

    print("=== Role Reversal Detection ===")
    reversed = detect_role_reversals(levels, current_price=400.0)
    for r in reversed:
        print(f"  {r.description}")
    print()

    print("=== Automated S/R Detection from Synthetic Data ===")
    np.random.seed(42)
    n = 200
    close = pd.Series(100 + np.cumsum(np.random.randn(n) * 0.8))
    high = close + np.abs(np.random.randn(n) * 0.5)
    low = close - np.abs(np.random.randn(n) * 0.5)
    
    detected = find_sr_levels(high, low, close, lookback=20, tolerance_pct=1.5)
    print(f"  Found {len(detected)} S/R levels")
    for lvl in detected[:5]:
        print(f"    {lvl.description}")
    
    if detected:
        current = float(close.iloc[-1])
        objs = find_objectives(current, 'long', detected)
        print(f"\n  Long objectives from {current:.1f}:")
        for o in objs:
            print(f"    Target {o.objective_price:.1f} "
                  f"(+{o.profit_distance:.1f}, {o.level.strength} touches)")
