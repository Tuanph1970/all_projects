"""
Failed Top/Bottom Formation Detector — Chapter 11, Concept 11
===============================================================
When patterns normally associated with major tops or bottoms are
penetrated, price has "neglected to respect the support or resistance
level implied by such formations" — a failed signal.

Three sub-patterns:
1. Failed double top: price breaks above the double top → BUY
2. Failed double bottom: price breaks below the double bottom → SELL
3. Failed head-and-shoulders: price retraces beyond the most recent
   shoulder (top: above right shoulder = BUY; bottom: below right
   shoulder = SELL)

Schwager notes:
- Double top/bottom penetrations are good but relatively rare
- Failed H&S patterns are more common and often excellent
- Waiting for a retracement after confirmation can be beneficial

Key examples:
- Coffee 1993-94 (Fig 11.27-28): double top penetrated → immense rally
- IBM (Fig 11.29): failed H&S top → above right shoulder = BUY
- Soybean oil (Fig 11.30): failed H&S bottom → below right shoulder = SELL
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class FormationType(Enum):
    DOUBLE_TOP = "double_top"
    DOUBLE_BOTTOM = "double_bottom"
    HS_TOP = "head_and_shoulders_top"
    HS_BOTTOM = "head_and_shoulders_bottom"


@dataclass
class TopBottomFormation:
    """A detected top or bottom formation."""
    formation_type: FormationType
    key_level: float           # The resistance (top) or support (bottom) level
    formation_start_idx: int
    formation_end_idx: int
    # For H&S patterns
    left_shoulder_idx: Optional[int] = None
    head_idx: Optional[int] = None
    right_shoulder_idx: Optional[int] = None
    right_shoulder_price: Optional[float] = None
    neckline: Optional[float] = None
    # For double top/bottom
    peak1_idx: Optional[int] = None
    peak2_idx: Optional[int] = None


@dataclass
class FailedFormation:
    """A confirmed failed top/bottom formation."""
    formation: TopBottomFormation
    penetration_date: pd.Timestamp
    penetration_bar_idx: int
    penetration_price: float
    trade_direction: str        # 'long' or 'short'
    confirmation_level: float   # Level that was breached to confirm failure


def detect_double_top(
    df: pd.DataFrame,
    tolerance_pct: float = 0.02,
    min_valley_depth_pct: float = 0.03,
    min_bars_between: int = 10,
) -> Optional[TopBottomFormation]:
    """
    Detect a double top pattern.

    Two peaks at approximately the same level with a meaningful valley
    between them.
    """
    highs = df['high'].values
    n = len(highs)
    if n < 20:
        return None

    # Find swing highs
    swing_highs = []
    for i in range(3, n - 3):
        if (highs[i] > highs[i-1] and highs[i] > highs[i-2] and
                highs[i] > highs[i+1] and highs[i] > highs[i+2]):
            swing_highs.append((i, highs[i]))

    # Check pairs for double top
    for a in range(len(swing_highs)):
        for b in range(a + 1, len(swing_highs)):
            i1, p1 = swing_highs[a]
            i2, p2 = swing_highs[b]

            if i2 - i1 < min_bars_between:
                continue

            avg_peak = (p1 + p2) / 2
            if abs(p1 - p2) / avg_peak > tolerance_pct:
                continue

            # Check for meaningful valley between
            valley = df.iloc[i1:i2 + 1]['low'].min()
            valley_depth = (avg_peak - valley) / avg_peak
            if valley_depth < min_valley_depth_pct:
                continue

            return TopBottomFormation(
                formation_type=FormationType.DOUBLE_TOP,
                key_level=max(p1, p2),
                formation_start_idx=i1,
                formation_end_idx=i2,
                peak1_idx=i1,
                peak2_idx=i2,
            )

    return None


def detect_double_bottom(
    df: pd.DataFrame,
    tolerance_pct: float = 0.02,
    min_peak_height_pct: float = 0.03,
    min_bars_between: int = 10,
) -> Optional[TopBottomFormation]:
    """Detect a double bottom pattern. Mirror of detect_double_top."""
    lows = df['low'].values
    n = len(lows)
    if n < 20:
        return None

    swing_lows = []
    for i in range(3, n - 3):
        if (lows[i] < lows[i-1] and lows[i] < lows[i-2] and
                lows[i] < lows[i+1] and lows[i] < lows[i+2]):
            swing_lows.append((i, lows[i]))

    for a in range(len(swing_lows)):
        for b in range(a + 1, len(swing_lows)):
            i1, p1 = swing_lows[a]
            i2, p2 = swing_lows[b]

            if i2 - i1 < min_bars_between:
                continue

            avg_trough = (p1 + p2) / 2
            if abs(p1 - p2) / avg_trough > tolerance_pct:
                continue

            peak = df.iloc[i1:i2 + 1]['high'].max()
            peak_height = (peak - avg_trough) / avg_trough
            if peak_height < min_peak_height_pct:
                continue

            return TopBottomFormation(
                formation_type=FormationType.DOUBLE_BOTTOM,
                key_level=min(p1, p2),
                formation_start_idx=i1,
                formation_end_idx=i2,
                peak1_idx=i1,
                peak2_idx=i2,
            )

    return None


def detect_hs_top(
    df: pd.DataFrame,
    shoulder_tolerance_pct: float = 0.03,
    head_min_exceed_pct: float = 0.02,
) -> Optional[TopBottomFormation]:
    """
    Detect a head-and-shoulders top pattern.

    Left shoulder ~ right shoulder (within tolerance).
    Head significantly above both shoulders.
    """
    highs = df['high'].values
    n = len(highs)
    if n < 30:
        return None

    swing_highs = []
    for i in range(3, n - 3):
        if (highs[i] > highs[i-1] and highs[i] > highs[i-2] and
                highs[i] > highs[i+1] and highs[i] > highs[i+2]):
            swing_highs.append((i, highs[i]))

    if len(swing_highs) < 3:
        return None

    # Try triplets as LS, Head, RS
    for a in range(len(swing_highs) - 2):
        ls_idx, ls_price = swing_highs[a]
        hd_idx, hd_price = swing_highs[a + 1]
        rs_idx, rs_price = swing_highs[a + 2]

        # Head must be above both shoulders
        if hd_price <= ls_price * (1 + head_min_exceed_pct):
            continue
        if hd_price <= rs_price * (1 + head_min_exceed_pct):
            continue

        # Shoulders approximately equal
        avg_shoulder = (ls_price + rs_price) / 2
        if abs(ls_price - rs_price) / avg_shoulder > shoulder_tolerance_pct:
            continue

        # Find neckline (connect valleys between shoulders)
        valley1 = df.iloc[ls_idx:hd_idx + 1]['low'].min()
        valley2 = df.iloc[hd_idx:rs_idx + 1]['low'].min()
        neckline = (valley1 + valley2) / 2

        return TopBottomFormation(
            formation_type=FormationType.HS_TOP,
            key_level=rs_price,  # Confirmation = above right shoulder
            formation_start_idx=ls_idx,
            formation_end_idx=rs_idx,
            left_shoulder_idx=ls_idx,
            head_idx=hd_idx,
            right_shoulder_idx=rs_idx,
            right_shoulder_price=rs_price,
            neckline=neckline,
        )

    return None


def detect_failed_formation(
    df: pd.DataFrame,
    formation: TopBottomFormation,
) -> Optional[FailedFormation]:
    """
    Check if a top/bottom formation has been penetrated (failed).

    - Double top: close above the double top level → BUY
    - Double bottom: close below the double bottom level → SELL
    - H&S top: close above right shoulder → BUY
    - H&S bottom: close below right shoulder → SELL

    Returns
    -------
    FailedFormation or None
    """
    for i in range(formation.formation_end_idx + 1, len(df)):
        bar = df.iloc[i]

        if formation.formation_type == FormationType.DOUBLE_TOP:
            if bar['close'] > formation.key_level:
                return FailedFormation(
                    formation=formation,
                    penetration_date=df.index[i],
                    penetration_bar_idx=i,
                    penetration_price=bar['close'],
                    trade_direction='long',
                    confirmation_level=formation.key_level,
                )

        elif formation.formation_type == FormationType.DOUBLE_BOTTOM:
            if bar['close'] < formation.key_level:
                return FailedFormation(
                    formation=formation,
                    penetration_date=df.index[i],
                    penetration_bar_idx=i,
                    penetration_price=bar['close'],
                    trade_direction='short',
                    confirmation_level=formation.key_level,
                )

        elif formation.formation_type == FormationType.HS_TOP:
            if bar['close'] > formation.right_shoulder_price:
                return FailedFormation(
                    formation=formation,
                    penetration_date=df.index[i],
                    penetration_bar_idx=i,
                    penetration_price=bar['close'],
                    trade_direction='long',
                    confirmation_level=formation.right_shoulder_price,
                )

        elif formation.formation_type == FormationType.HS_BOTTOM:
            if bar['close'] < formation.right_shoulder_price:
                return FailedFormation(
                    formation=formation,
                    penetration_date=df.index[i],
                    penetration_bar_idx=i,
                    penetration_price=bar['close'],
                    trade_direction='short',
                    confirmation_level=formation.right_shoulder_price,
                )

    return None


# ── Example usage ──────────────────────────────────────────────────
if __name__ == "__main__":
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=80, freq='B')

    # Simulate: advance → double top → failed (breaks above)
    prices = [100]
    for i in range(19):
        prices.append(prices[-1] + 0.8 + np.random.randn() * 0.3)
    # First top
    prices.extend([prices[-1] + 0.2, prices[-1] + 0.4])
    # Valley
    for i in range(8):
        prices.append(prices[-1] - 0.6 + np.random.randn() * 0.2)
    # Second top (similar level)
    for i in range(8):
        prices.append(prices[-1] + 0.6 + np.random.randn() * 0.2)
    # Decline
    for i in range(8):
        prices.append(prices[-1] - 0.4 + np.random.randn() * 0.3)
    # Rally through double top
    for i in range(32):
        prices.append(prices[-1] + 0.6 + np.random.randn() * 0.3)

    prices = np.array(prices[:80])
    highs = prices + np.random.uniform(0.5, 2, 80)
    lows = prices - np.random.uniform(0.5, 2, 80)

    df = pd.DataFrame({
        'high': highs, 'low': lows, 'close': prices
    }, index=dates)

    dt = detect_double_top(df.iloc[:50], tolerance_pct=0.03, min_bars_between=8)
    if dt:
        print(f"Double top detected:")
        print(f"  Level:    {dt.key_level:.1f}")
        print(f"  Peak 1:   bar {dt.peak1_idx}")
        print(f"  Peak 2:   bar {dt.peak2_idx}")

        ff = detect_failed_formation(df, dt)
        if ff:
            print(f"\n  FAILED on {ff.penetration_date.date()}")
            print(f"    Price:  {ff.penetration_price:.1f}")
            print(f"    Trade:  {ff.trade_direction}")
        else:
            print("  Not yet failed.")
    else:
        print("No double top detected.")
