"""
Measured Move — Chapter 10, Concept 2
======================================
Projects price targets based on the premise that markets move
in approximately equal-size price swings.

Key Schwager insight: "When two or more of these objectives nearly
coincide, it tends to enhance the reliability of the price area
as an important objective zone."

This module provides:
  - Single measured move projection
  - Multi-swing confluence detection
  - Swing extraction from price data
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional


@dataclass
class MeasuredMoveTarget:
    """A single measured move price projection."""
    swing_label: str
    swing_start: float
    swing_end: float
    reaction_point: float
    target_price: float
    direction: str  # 'up' or 'down'

    @property
    def swing_size(self) -> float:
        return abs(self.swing_end - self.swing_start)

    @property
    def target_distance(self) -> float:
        return abs(self.target_price - self.reaction_point)


@dataclass
class ConfluenceZone:
    """
    A price zone where multiple measured move targets cluster.
    
    Schwager emphasizes that confluence of independent projections
    significantly enhances target reliability.
    """
    center_price: float
    zone_width: float
    contributing_targets: List[MeasuredMoveTarget]
    
    @property
    def zone_low(self) -> float:
        return self.center_price - self.zone_width / 2

    @property
    def zone_high(self) -> float:
        return self.center_price + self.zone_width / 2

    @property
    def num_targets(self) -> int:
        return len(self.contributing_targets)

    @property
    def confidence(self) -> str:
        """Qualitative confidence based on number of converging targets."""
        if self.num_targets >= 3:
            return "high"
        elif self.num_targets == 2:
            return "moderate"
        return "low"


def measured_move(
    swing_start: float,
    swing_end: float,
    reaction_point: float,
    label: str = "MM1"
) -> MeasuredMoveTarget:
    """
    Calculate a single measured move price target.
    
    The premise: the move from the reaction point will approximate
    the size of the reference swing (swing_start → swing_end).
    
    Parameters
    ----------
    swing_start : float
        Starting price of the reference swing.
    swing_end : float
        Ending price of the reference swing (high or low).
    reaction_point : float
        The pullback/reaction price from which the next
        swing is projected.
    label : str
        Identifier for this measured move (e.g., "MM1", "MMA").
        
    Returns
    -------
    MeasuredMoveTarget
    
    Examples
    --------
    >>> # Uptrend: market rallied from 100 to 130, pulled back to 115
    >>> mm = measured_move(100.0, 130.0, 115.0, label="MM1")
    >>> print(f"Target: {mm.target_price}")
    Target: 145.0
    
    >>> # Downtrend: market fell from 80 to 60, bounced to 68
    >>> mm = measured_move(80.0, 60.0, 68.0, label="MM1")
    >>> print(f"Target: {mm.target_price}")
    Target: 48.0
    """
    swing_size = swing_end - swing_start  # Signed
    
    if swing_size > 0:
        # Upswing reference → project upward from reaction
        target = reaction_point + abs(swing_size)
        direction = "up"
    else:
        # Downswing reference → project downward from reaction
        target = reaction_point - abs(swing_size)
        direction = "down"
    
    return MeasuredMoveTarget(
        swing_label=label,
        swing_start=swing_start,
        swing_end=swing_end,
        reaction_point=reaction_point,
        target_price=target,
        direction=direction,
    )


def find_confluence_zones(
    targets: List[MeasuredMoveTarget],
    tolerance_pct: float = 2.0
) -> List[ConfluenceZone]:
    """
    Detect zones where multiple measured move targets cluster.
    
    Schwager's key insight: when independent MM projections
    converge on the same price area, the zone becomes a much
    more reliable objective.
    
    Parameters
    ----------
    targets : list of MeasuredMoveTarget
        All measured move projections to analyze.
    tolerance_pct : float
        Maximum percentage distance between targets to consider
        them part of the same confluence zone. Default 2%.
        
    Returns
    -------
    list of ConfluenceZone
        Detected confluence zones, sorted by number of
        contributing targets (most targets first).
    """
    if not targets:
        return []
    
    prices = sorted(targets, key=lambda t: t.target_price)
    zones = []
    used = set()
    
    for i, anchor in enumerate(prices):
        if i in used:
            continue
        cluster = [anchor]
        used.add(i)
        
        for j, candidate in enumerate(prices):
            if j in used:
                continue
            avg_price = (anchor.target_price + candidate.target_price) / 2
            if avg_price == 0:
                continue
            pct_diff = abs(anchor.target_price - candidate.target_price) / avg_price * 100
            if pct_diff <= tolerance_pct:
                cluster.append(candidate)
                used.add(j)
        
        if len(cluster) >= 2:
            cluster_prices = [t.target_price for t in cluster]
            center = np.mean(cluster_prices)
            width = max(cluster_prices) - min(cluster_prices)
            zones.append(ConfluenceZone(
                center_price=center,
                zone_width=width,
                contributing_targets=cluster,
            ))
    
    zones.sort(key=lambda z: z.num_targets, reverse=True)
    return zones


def extract_swings(
    prices: pd.Series,
    min_swing_pct: float = 3.0
) -> List[Tuple[int, float, int, float]]:
    """
    Extract significant price swings from a price series.
    
    Uses a simple zigzag filter: a new swing is confirmed when
    price moves at least min_swing_pct from the last extreme.
    
    Parameters
    ----------
    prices : pd.Series
        Price series (typically closing prices).
    min_swing_pct : float
        Minimum percentage move to qualify as a swing.
        
    Returns
    -------
    list of (start_idx, start_price, end_idx, end_price)
        Each tuple represents one complete swing.
    """
    if len(prices) < 3:
        return []
    
    extremes = []
    direction = None
    last_high_idx = 0
    last_low_idx = 0
    last_high = prices.iloc[0]
    last_low = prices.iloc[0]
    
    for i in range(1, len(prices)):
        p = prices.iloc[i]
        
        if direction is None:
            if p >= last_low * (1 + min_swing_pct / 100):
                direction = 'up'
                extremes.append((last_low_idx, last_low))
                last_high = p
                last_high_idx = i
            elif p <= last_high * (1 - min_swing_pct / 100):
                direction = 'down'
                extremes.append((last_high_idx, last_high))
                last_low = p
                last_low_idx = i
            else:
                if p > last_high:
                    last_high = p
                    last_high_idx = i
                if p < last_low:
                    last_low = p
                    last_low_idx = i
        elif direction == 'up':
            if p > last_high:
                last_high = p
                last_high_idx = i
            elif p <= last_high * (1 - min_swing_pct / 100):
                extremes.append((last_high_idx, last_high))
                direction = 'down'
                last_low = p
                last_low_idx = i
        else:  # direction == 'down'
            if p < last_low:
                last_low = p
                last_low_idx = i
            elif p >= last_low * (1 + min_swing_pct / 100):
                extremes.append((last_low_idx, last_low))
                direction = 'up'
                last_high = p
                last_high_idx = i
    
    # Build swing list from consecutive extremes
    swings = []
    for i in range(len(extremes) - 1):
        swings.append((
            extremes[i][0], extremes[i][1],
            extremes[i+1][0], extremes[i+1][1]
        ))
    return swings


def project_all_measured_moves(
    swings: List[Tuple[int, float, int, float]]
) -> List[MeasuredMoveTarget]:
    """
    Generate measured move targets from a list of extracted swings.
    
    For each swing, projects a target from the next reaction point
    (which is the end of the following swing).
    
    Parameters
    ----------
    swings : list of swing tuples
        Output from extract_swings().
        
    Returns
    -------
    list of MeasuredMoveTarget
    """
    targets = []
    for i in range(len(swings) - 1):
        _, s_start, _, s_end = swings[i]
        _, reaction_point, _, _ = swings[i + 1]
        
        mm = measured_move(
            swing_start=s_start,
            swing_end=s_end,
            reaction_point=reaction_point,
            label=f"MM{i+1}"
        )
        targets.append(mm)
    return targets


# --- Example usage ---
if __name__ == "__main__":
    print("=== Single Measured Move ===")
    mm = measured_move(100.0, 130.0, 115.0, "MM1")
    print(f"  Swing: {mm.swing_start} → {mm.swing_end} (size: {mm.swing_size})")
    print(f"  Reaction at: {mm.reaction_point}")
    print(f"  Target: {mm.target_price}")
    print(f"  Direction: {mm.direction}")
    print()

    print("=== Confluence Detection (Schwager's Crude Oil Example) ===")
    # Three independent upswings all projecting similar tops
    targets = [
        measured_move(15.50, 18.20, 16.80, "MM1"),  # Mar-May advance
        measured_move(16.80, 18.60, 17.40, "MM2"),  # June upswing
        measured_move(17.40, 19.10, 18.00, "MM3"),  # Jun-Jul upmove
    ]
    for t in targets:
        print(f"  {t.swing_label}: target = {t.target_price:.2f}")
    
    zones = find_confluence_zones(targets, tolerance_pct=3.0)
    for z in zones:
        labels = [t.swing_label for t in z.contributing_targets]
        print(f"\n  Confluence zone: {z.zone_low:.2f} — {z.zone_high:.2f}")
        print(f"  Center: {z.center_price:.2f}")
        print(f"  Contributing: {', '.join(labels)}")
        print(f"  Confidence: {z.confidence}")
    print()

    print("=== Swing Extraction from Synthetic Data ===")
    np.random.seed(42)
    prices = pd.Series(
        100 + np.cumsum(np.random.randn(200) * 1.2)
    )
    swings = extract_swings(prices, min_swing_pct=5.0)
    print(f"  Found {len(swings)} swings")
    for s in swings[:5]:
        print(f"    idx {s[0]}→{s[2]}: {s[1]:.1f} → {s[3]:.1f}")
    
    mm_targets = project_all_measured_moves(swings)
    print(f"\n  Generated {len(mm_targets)} measured move targets")
    zones = find_confluence_zones(mm_targets, tolerance_pct=3.0)
    print(f"  Detected {len(zones)} confluence zone(s)")
    for z in zones:
        print(f"    Zone {z.zone_low:.1f}–{z.zone_high:.1f} "
              f"({z.num_targets} targets, {z.confidence} confidence)")
