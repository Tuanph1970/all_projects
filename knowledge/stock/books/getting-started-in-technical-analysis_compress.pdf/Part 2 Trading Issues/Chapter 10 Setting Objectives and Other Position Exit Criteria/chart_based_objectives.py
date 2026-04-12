"""
Chart-Based Objectives — Chapter 10, Concept 1
================================================
Uses chart pattern geometry to project minimum price targets.

Schwager's framework: patterns are more reliable as trade signals
than as price objective indicators, but they still provide useful
guideline targets.

Supported patterns:
  - Head-and-Shoulders (top and bottom)
  - Double Top / Double Bottom
  - Rectangle (trading range breakout)
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional


@dataclass
class ChartObjective:
    """Result of a chart-based price objective calculation."""
    pattern: str
    breakout_price: float
    target_price: float
    measured_distance: float
    direction: str  # 'long' or 'short'
    confidence_note: str = (
        "Chart objectives are less reliable than the trade signal itself. "
        "Use as guideline, not gospel."
    )

    @property
    def reward_distance(self) -> float:
        """Absolute distance from breakout to target."""
        return abs(self.target_price - self.breakout_price)

    def risk_reward_ratio(self, stop_price: float) -> float:
        """
        Calculate reward-to-risk ratio given a stop-loss price.
        
        Parameters
        ----------
        stop_price : float
            The stop-loss price for the trade.
            
        Returns
        -------
        float
            Reward-to-risk ratio. Values > 1.0 mean reward exceeds risk.
        """
        risk = abs(self.breakout_price - stop_price)
        if risk == 0:
            return float('inf')
        return self.reward_distance / risk


def head_and_shoulders_objective(
    head_price: float,
    neckline_at_head: float,
    neckline_at_breakout: float,
    pattern_type: str = "top"
) -> ChartObjective:
    """
    Calculate price objective for a Head-and-Shoulders pattern.
    
    The minimum expected move after neckline penetration equals
    the distance from the head to the neckline.
    
    Parameters
    ----------
    head_price : float
        Price at the top (H&S top) or bottom (H&S bottom) of the head.
    neckline_at_head : float
        Neckline price level directly below/above the head.
    neckline_at_breakout : float
        Neckline price level at the breakout point.
        (May differ from neckline_at_head if neckline is sloped.)
    pattern_type : str
        'top' for bearish H&S top, 'bottom' for bullish H&S bottom.
        
    Returns
    -------
    ChartObjective
        The projected price objective and metadata.
        
    Examples
    --------
    >>> obj = head_and_shoulders_objective(
    ...     head_price=150.0,
    ...     neckline_at_head=130.0,
    ...     neckline_at_breakout=132.0,
    ...     pattern_type='top'
    ... )
    >>> print(f"Target: {obj.target_price}")
    Target: 112.0
    """
    measured_distance = abs(head_price - neckline_at_head)
    
    if pattern_type == "top":
        target = neckline_at_breakout - measured_distance
        direction = "short"
    else:
        target = neckline_at_breakout + measured_distance
        direction = "long"
    
    return ChartObjective(
        pattern=f"Head-and-Shoulders {pattern_type}",
        breakout_price=neckline_at_breakout,
        target_price=target,
        measured_distance=measured_distance,
        direction=direction,
    )


def double_top_bottom_objective(
    extreme_price: float,
    support_or_resistance: float,
    pattern_type: str = "top"
) -> ChartObjective:
    """
    Calculate price objective for a Double Top or Double Bottom.
    
    The projected move equals the height of the pattern
    (distance from the peaks/troughs to the intervening
    support/resistance level).
    
    Parameters
    ----------
    extreme_price : float
        Price at the double top or double bottom.
    support_or_resistance : float
        The intervening reaction low (double top) or
        reaction high (double bottom).
    pattern_type : str
        'top' or 'bottom'.
        
    Returns
    -------
    ChartObjective
    """
    measured_distance = abs(extreme_price - support_or_resistance)
    
    if pattern_type == "top":
        target = support_or_resistance - measured_distance
        direction = "short"
        breakout = support_or_resistance
    else:
        target = support_or_resistance + measured_distance
        direction = "long"
        breakout = support_or_resistance
    
    return ChartObjective(
        pattern=f"Double {pattern_type}",
        breakout_price=breakout,
        target_price=target,
        measured_distance=measured_distance,
        direction=direction,
    )


def rectangle_breakout_objective(
    range_high: float,
    range_low: float,
    breakout_direction: str = "up"
) -> ChartObjective:
    """
    Calculate price objective for a rectangle/trading range breakout.
    
    The projected move equals the height of the trading range.
    
    Parameters
    ----------
    range_high : float
        Upper boundary of the trading range.
    range_low : float
        Lower boundary of the trading range.
    breakout_direction : str
        'up' or 'down'.
        
    Returns
    -------
    ChartObjective
    """
    measured_distance = range_high - range_low
    
    if breakout_direction == "up":
        target = range_high + measured_distance
        breakout = range_high
        direction = "long"
    else:
        target = range_low - measured_distance
        breakout = range_low
        direction = "short"
    
    return ChartObjective(
        pattern="Rectangle breakout",
        breakout_price=breakout,
        target_price=target,
        measured_distance=measured_distance,
        direction=direction,
    )


# --- Example usage ---
if __name__ == "__main__":
    # Head-and-Shoulders Top example
    hs = head_and_shoulders_objective(
        head_price=150.0,
        neckline_at_head=130.0,
        neckline_at_breakout=132.0,
        pattern_type="top"
    )
    print(f"=== {hs.pattern} ===")
    print(f"  Breakout at:       ${hs.breakout_price:.2f}")
    print(f"  Measured distance: ${hs.measured_distance:.2f}")
    print(f"  Price objective:   ${hs.target_price:.2f}")
    print(f"  Direction:         {hs.direction}")
    print(f"  R:R at stop $140:  {hs.risk_reward_ratio(140.0):.2f}")
    print()

    # Double Bottom example
    db = double_top_bottom_objective(
        extreme_price=40.0,
        support_or_resistance=48.0,
        pattern_type="bottom"
    )
    print(f"=== {db.pattern} ===")
    print(f"  Breakout at:       ${db.breakout_price:.2f}")
    print(f"  Measured distance: ${db.measured_distance:.2f}")
    print(f"  Price objective:   ${db.target_price:.2f}")
    print()

    # Rectangle Breakout example
    rect = rectangle_breakout_objective(
        range_high=100.0,
        range_low=85.0,
        breakout_direction="up"
    )
    print(f"=== {rect.pattern} ===")
    print(f"  Breakout at:       ${rect.breakout_price:.2f}")
    print(f"  Measured distance: ${rect.measured_distance:.2f}")
    print(f"  Price objective:   ${rect.target_price:.2f}")
    print(f"  R:R at stop $95:   {rect.risk_reward_ratio(95.0):.2f}")
