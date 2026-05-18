"""Continuation and bar-pattern detectors (Schwager Ch 5, 12).

Day 2 of F-005.  Seven pattern types:

  * Flag             – pole + tight parallel-channel pullback
  * Pennant          – pole + tight converging-trendlines pullback
  * Symmetrical Triangle   – converging highs and lows
  * Ascending Triangle     – flat resistance + rising support  (bullish bias)
  * Descending Triangle    – falling resistance + flat support (bearish bias)
  * Gap              – common / breakaway / runaway / exhaustion
  * Wide-Ranging Day – bar range > N × ATR(14)

All detectors share PatternDetector from patterns/base.py and emit a
PatternMatch with the standard fields the decision helper expects.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np
import pandas as pd

from app.services.patterns.base import PatternDetector, PatternMatch


# ---------------------------------------------------------------------------
# Module-private helpers
# ---------------------------------------------------------------------------

def _rolling_atr(ohlc: pd.DataFrame, period: int = 14) -> np.ndarray:
    """Wilder's smoothed ATR — mirrors analysis-service F-001 so pattern
    detectors use the same volatility denominator as the regime classifier."""
    high = ohlc["high"].to_numpy(dtype=float)
    low = ohlc["low"].to_numpy(dtype=float)
    close = ohlc["close"].to_numpy(dtype=float)
    n = len(close)
    tr = np.empty(n)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        tr[i] = max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1]),
        )
    atr = np.full(n, np.nan)
    if n >= period:
        atr[period - 1] = tr[:period].mean()
        for i in range(period, n):
            atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
    return atr


def _linreg(x: np.ndarray, y: np.ndarray) -> Tuple[float, float]:
    """(slope, intercept) via numpy least-squares — no scipy dependency."""
    if len(x) < 2:
        return 0.0, float(y[0]) if len(y) else 0.0
    xm, ym = x.mean(), y.mean()
    ss = float(((x - xm) ** 2).sum())
    slope = 0.0 if ss == 0 else float(((x - xm) * (y - ym)).sum() / ss)
    return slope, ym - slope * xm


def _ref_atr(atr: np.ndarray, idx: int) -> float:
    """Safe ATR lookup — falls back to valid mean if index is NaN."""
    v = float(atr[idx])
    if np.isnan(v) or v <= 0:
        valid = atr[~np.isnan(atr)]
        v = float(valid.mean()) if len(valid) else 1.0
    return max(v, 1e-8)


# ---------------------------------------------------------------------------
# Flag
# ---------------------------------------------------------------------------

class FlagDetector(PatternDetector):
    """Bull or bear flag — strong pole followed by tight parallel-channel
    pullback (counter to the pole), then expected continuation.

    Bull flag: up-pole, both high/low series drift DOWN (slopes ≤ 0).
    Bear flag: down-pole, both series drift UP (slopes ≥ 0).
    Measured move: pole height projected from the breakout edge of the body.
    """

    def __init__(
        self,
        pole_min_bars: int = 4,
        pole_max_bars: int = 25,
        flag_min_bars: int = 3,
        flag_max_bars: int = 15,
        pole_min_atr_multiple: float = 2.0,
        flag_max_retrace_pct: float = 0.50,
        pole_linearity_min: float = 0.55,
    ):
        self.pole_min_bars = pole_min_bars
        self.pole_max_bars = pole_max_bars
        self.flag_min_bars = flag_min_bars
        self.flag_max_bars = flag_max_bars
        self.pole_min_atr_multiple = pole_min_atr_multiple
        self.flag_max_retrace_pct = flag_max_retrace_pct
        self.pole_linearity_min = pole_linearity_min

    def detect(self, ohlc: pd.DataFrame) -> Optional[PatternMatch]:
        ok, _ = self._validate_ohlc(
            ohlc, min_bars=self.pole_min_bars + self.flag_min_bars + 14
        )
        if not ok:
            return None

        n = len(ohlc)
        close = ohlc["close"].to_numpy(dtype=float)
        high_a = ohlc["high"].to_numpy(dtype=float)
        low_a = ohlc["low"].to_numpy(dtype=float)
        atr = _rolling_atr(ohlc)

        for flag_len in range(self.flag_min_bars, min(self.flag_max_bars + 1, n)):
            flag_start = n - flag_len
            pole_end = flag_start - 1
            if pole_end < self.pole_min_bars - 1:
                break

            for pole_len in range(
                self.pole_min_bars, min(self.pole_max_bars + 1, pole_end + 1)
            ):
                pole_start = pole_end - pole_len + 1
                ra = _ref_atr(atr, pole_end)
                pole_close = close[pole_start : pole_end + 1]
                pole_move = pole_close[-1] - pole_close[0]
                pole_height = abs(pole_move)

                if pole_height < self.pole_min_atr_multiple * ra:
                    continue

                # Linearity: pole move mostly in one direction (not a zigzag).
                x_p = np.arange(pole_len, dtype=float)
                sl_p, _ = _linreg(x_p, pole_close)
                if abs(sl_p * (pole_len - 1)) < self.pole_linearity_min * pole_height:
                    continue

                bullish = pole_move > 0

                fg_high = high_a[flag_start:n]
                fg_low = low_a[flag_start:n]
                fg_close = close[flag_start:n]
                x_f = np.arange(flag_len, dtype=float)
                sl_h, _ = _linreg(x_f, fg_high)
                sl_l, _ = _linreg(x_f, fg_low)

                # Parallel channels counter to pole.
                if bullish and not (sl_h <= 0 and sl_l <= 0):
                    continue
                if (not bullish) and not (sl_h >= 0 and sl_l >= 0):
                    continue

                retrace = abs(fg_close[-1] - fg_close[0])
                if retrace > self.flag_max_retrace_pct * pole_height:
                    continue

                breakout = fg_high.max() if bullish else fg_low.min()
                target = breakout + pole_move

                tightness = 1.0 - min(
                    1.0, retrace / max(self.flag_max_retrace_pct * pole_height, 1e-8)
                )
                pole_quality = min(1.0, pole_height / (ra * 4))
                confidence = round(min(0.88, 0.42 + 0.28 * tightness + 0.18 * pole_quality), 3)

                return PatternMatch(
                    pattern_name="Flag",
                    pattern_type="bullish" if bullish else "bearish",
                    found=True,
                    confidence=confidence,
                    key_bars=[pole_start, pole_end, flag_start, n - 1],
                    measured_move_target=float(round(target, 4)),
                    neckline=float(round(breakout, 4)),
                    details={
                        "pole_height": float(round(pole_height, 4)),
                        "pole_bars": int(pole_len),
                        "flag_bars": int(flag_len),
                        "flag_retrace_pct": float(round(retrace / pole_height, 3)),
                    },
                )

        return None


# ---------------------------------------------------------------------------
# Pennant
# ---------------------------------------------------------------------------

class PennantDetector(PatternDetector):
    """Bull or bear pennant — pole followed by converging-trendlines
    consolidation (the high series drifts DOWN, low series UP regardless of
    pole direction).

    Measured move: pole height projected from the trendline breakout.
    """

    def __init__(
        self,
        pole_min_bars: int = 4,
        pole_max_bars: int = 25,
        pennant_min_bars: int = 4,
        pennant_max_bars: int = 15,
        pole_min_atr_multiple: float = 2.0,
        pennant_max_retrace_pct: float = 0.45,
        pole_linearity_min: float = 0.55,
    ):
        self.pole_min_bars = pole_min_bars
        self.pole_max_bars = pole_max_bars
        self.pennant_min_bars = pennant_min_bars
        self.pennant_max_bars = pennant_max_bars
        self.pole_min_atr_multiple = pole_min_atr_multiple
        self.pennant_max_retrace_pct = pennant_max_retrace_pct
        self.pole_linearity_min = pole_linearity_min

    def detect(self, ohlc: pd.DataFrame) -> Optional[PatternMatch]:
        ok, _ = self._validate_ohlc(
            ohlc, min_bars=self.pole_min_bars + self.pennant_min_bars + 14
        )
        if not ok:
            return None

        n = len(ohlc)
        close = ohlc["close"].to_numpy(dtype=float)
        high_a = ohlc["high"].to_numpy(dtype=float)
        low_a = ohlc["low"].to_numpy(dtype=float)
        atr = _rolling_atr(ohlc)

        for pn_len in range(self.pennant_min_bars, min(self.pennant_max_bars + 1, n)):
            pn_start = n - pn_len
            pole_end = pn_start - 1
            if pole_end < self.pole_min_bars - 1:
                break

            for pole_len in range(
                self.pole_min_bars, min(self.pole_max_bars + 1, pole_end + 1)
            ):
                pole_start = pole_end - pole_len + 1
                ra = _ref_atr(atr, pole_end)
                pole_close = close[pole_start : pole_end + 1]
                pole_move = pole_close[-1] - pole_close[0]
                pole_height = abs(pole_move)

                if pole_height < self.pole_min_atr_multiple * ra:
                    continue

                x_p = np.arange(pole_len, dtype=float)
                sl_p, _ = _linreg(x_p, pole_close)
                if abs(sl_p * (pole_len - 1)) < self.pole_linearity_min * pole_height:
                    continue

                bullish = pole_move > 0

                pn_high = high_a[pn_start:n]
                pn_low = low_a[pn_start:n]
                pn_close = close[pn_start:n]
                x_pn = np.arange(pn_len, dtype=float)
                sl_h, ic_h = _linreg(x_pn, pn_high)
                sl_l, ic_l = _linreg(x_pn, pn_low)

                # Converging: highs trending down, lows trending up.
                if not (sl_h < 0 and sl_l > 0):
                    continue

                retrace = abs(pn_close[-1] - pn_close[0])
                if retrace > self.pennant_max_retrace_pct * pole_height:
                    continue

                last = pn_len - 1
                breakout_h = ic_h + sl_h * last
                breakout_l = ic_l + sl_l * last
                breakout = breakout_h if bullish else breakout_l
                target = breakout + pole_move

                width_first = pn_high[0] - pn_low[0]
                width_last = breakout_h - breakout_l
                convergence = 1.0 - min(1.0, width_last / max(width_first, 1e-8))
                pole_quality = min(1.0, pole_height / (ra * 4))
                confidence = round(min(0.88, 0.42 + 0.28 * convergence + 0.18 * pole_quality), 3)

                return PatternMatch(
                    pattern_name="Pennant",
                    pattern_type="bullish" if bullish else "bearish",
                    found=True,
                    confidence=confidence,
                    key_bars=[pole_start, pole_end, pn_start, n - 1],
                    measured_move_target=float(round(target, 4)),
                    neckline=float(round(breakout, 4)),
                    details={
                        "pole_height": float(round(pole_height, 4)),
                        "pole_bars": int(pole_len),
                        "pennant_bars": int(pn_len),
                        "upper_tl_slope": float(round(sl_h, 6)),
                        "lower_tl_slope": float(round(sl_l, 6)),
                    },
                )

        return None


# ---------------------------------------------------------------------------
# Shared triangle helper
# ---------------------------------------------------------------------------

def _triangle_trendlines(
    ohlc: pd.DataFrame, swing_window: int, min_pivots: int, lookback: int
) -> Optional[Tuple]:
    """Fit trendlines through swing pivots in the last `lookback` bars.

    Returns (abs_ph, sl_h, ic_h, abs_pl, sl_l, ic_l, start, seg_len) or None
    if insufficient pivots exist.  All index values are absolute (relative to
    the start of `ohlc`); slopes/intercepts use relative bar numbers 0 …
    seg_len-1 so callers can evaluate the line at any relative bar.
    """
    n = len(ohlc)
    start = max(0, n - lookback)
    sl = ohlc.iloc[start:]
    seg_len = len(sl)

    highs = sl["high"].to_numpy(dtype=float)
    lows = sl["low"].to_numpy(dtype=float)

    rel_ph = PatternDetector._find_swing_highs(highs, swing_window)
    rel_pl = PatternDetector._find_swing_lows(lows, swing_window)

    if len(rel_ph) < min_pivots or len(rel_pl) < min_pivots:
        return None

    abs_ph = [i + start for i in rel_ph]
    abs_pl = [i + start for i in rel_pl]

    x_h = np.array(rel_ph, dtype=float)
    sl_h, ic_h = _linreg(x_h, highs[rel_ph])

    x_l = np.array(rel_pl, dtype=float)
    sl_l, ic_l = _linreg(x_l, lows[rel_pl])

    return abs_ph, sl_h, ic_h, abs_pl, sl_l, ic_l, start, seg_len


# ---------------------------------------------------------------------------
# Symmetrical Triangle
# ---------------------------------------------------------------------------

class SymmetricalTriangleDetector(PatternDetector):
    """Symmetrical triangle — descending upper trendline, ascending lower
    trendline; price coils toward an apex.  Bias is neutral until breakout.

    Measured move: height at the widest pivot, projected from the current
    trendline level (caller picks direction on actual breakout).
    """

    pattern_name = "Symmetrical Triangle"
    pattern_type = "neutral"

    def __init__(
        self,
        swing_window: int = 3,
        min_pivots: int = 2,
        lookback: int = 60,
        slope_threshold_pct: float = 0.0005,
    ):
        self.swing_window = swing_window
        self.min_pivots = min_pivots
        self.lookback = lookback
        self.slope_threshold_pct = slope_threshold_pct

    def detect(self, ohlc: pd.DataFrame) -> Optional[PatternMatch]:
        ok, _ = self._validate_ohlc(ohlc, min_bars=self.swing_window * 4 + 5)
        if not ok:
            return None

        res = _triangle_trendlines(ohlc, self.swing_window, self.min_pivots, self.lookback)
        if res is None:
            return None

        abs_ph, sl_h, ic_h, abs_pl, sl_l, ic_l, start, seg_len = res
        avg_price = float(ohlc["close"].iloc[start:].mean())
        if avg_price <= 0:
            return None

        norm_h = sl_h / avg_price
        norm_l = sl_l / avg_price

        if not (norm_h < -self.slope_threshold_pct and norm_l > self.slope_threshold_pct):
            return None

        first_bar = min(min(abs_ph) - start, min(abs_pl) - start)
        height = (ic_h + sl_h * first_bar) - (ic_l + sl_l * first_bar)
        if height <= 0:
            return None

        last = seg_len - 1
        breakout_h = ic_h + sl_h * last
        breakout_l = ic_l + sl_l * last
        target_up = breakout_h + height
        target_dn = breakout_l - height

        sym = 1.0 - abs(abs(norm_h) - abs(norm_l)) / max(abs(norm_h), abs(norm_l))
        confidence = round(
            min(0.82, 0.38 + 0.30 * sym + 0.14 * min(1.0, height / avg_price / 0.05)), 3
        )

        return PatternMatch(
            pattern_name=self.pattern_name,
            pattern_type=self.pattern_type,
            found=True,
            confidence=confidence,
            key_bars=sorted(set(abs_ph + abs_pl)),
            measured_move_target=float(round(target_up, 4)),
            neckline=float(round(breakout_h, 4)),
            details={
                "upper_slope": float(round(sl_h, 6)),
                "lower_slope": float(round(sl_l, 6)),
                "pattern_height": float(round(height, 4)),
                "target_up": float(round(target_up, 4)),
                "target_dn": float(round(target_dn, 4)),
            },
        )


# ---------------------------------------------------------------------------
# Ascending Triangle
# ---------------------------------------------------------------------------

class AscendingTriangleDetector(PatternDetector):
    """Ascending triangle — flat upper resistance + rising lower support.
    Bullish bias: expected to break above the flat top.

    Measured move: pattern height projected up from the resistance level.
    """

    pattern_name = "Ascending Triangle"
    pattern_type = "bullish"

    def __init__(
        self,
        swing_window: int = 3,
        min_pivots: int = 2,
        lookback: int = 60,
        flat_threshold_pct: float = 0.003,
        slope_threshold_pct: float = 0.0005,
    ):
        self.swing_window = swing_window
        self.min_pivots = min_pivots
        self.lookback = lookback
        self.flat_threshold_pct = flat_threshold_pct
        self.slope_threshold_pct = slope_threshold_pct

    def detect(self, ohlc: pd.DataFrame) -> Optional[PatternMatch]:
        ok, _ = self._validate_ohlc(ohlc, min_bars=self.swing_window * 4 + 5)
        if not ok:
            return None

        res = _triangle_trendlines(ohlc, self.swing_window, self.min_pivots, self.lookback)
        if res is None:
            return None

        abs_ph, sl_h, ic_h, abs_pl, sl_l, ic_l, start, seg_len = res
        avg_price = float(ohlc["close"].iloc[start:].mean())
        if avg_price <= 0:
            return None

        norm_h = sl_h / avg_price
        norm_l = sl_l / avg_price

        if not (abs(norm_h) <= self.flat_threshold_pct and norm_l > self.slope_threshold_pct):
            return None

        first_bar = min(min(abs_ph) - start, min(abs_pl) - start)
        height = (ic_h + sl_h * first_bar) - (ic_l + sl_l * first_bar)
        if height <= 0:
            return None

        resistance = ic_h + sl_h * (seg_len - 1)
        target = resistance + height

        confidence = round(
            min(0.82, 0.45 + 0.25 * min(1.0, norm_l / 0.002) + 0.12 * min(1.0, height / avg_price / 0.05)),
            3,
        )

        return PatternMatch(
            pattern_name=self.pattern_name,
            pattern_type=self.pattern_type,
            found=True,
            confidence=confidence,
            key_bars=sorted(set(abs_ph + abs_pl)),
            measured_move_target=float(round(target, 4)),
            neckline=float(round(resistance, 4)),
            details={
                "upper_slope": float(round(sl_h, 6)),
                "lower_slope": float(round(sl_l, 6)),
                "pattern_height": float(round(height, 4)),
                "resistance_level": float(round(resistance, 4)),
            },
        )


# ---------------------------------------------------------------------------
# Descending Triangle
# ---------------------------------------------------------------------------

class DescendingTriangleDetector(PatternDetector):
    """Descending triangle — falling upper resistance + flat lower support.
    Bearish bias: expected to break below the flat bottom.

    Measured move: pattern height projected down from the support level.
    """

    pattern_name = "Descending Triangle"
    pattern_type = "bearish"

    def __init__(
        self,
        swing_window: int = 3,
        min_pivots: int = 2,
        lookback: int = 60,
        flat_threshold_pct: float = 0.003,
        slope_threshold_pct: float = 0.0005,
    ):
        self.swing_window = swing_window
        self.min_pivots = min_pivots
        self.lookback = lookback
        self.flat_threshold_pct = flat_threshold_pct
        self.slope_threshold_pct = slope_threshold_pct

    def detect(self, ohlc: pd.DataFrame) -> Optional[PatternMatch]:
        ok, _ = self._validate_ohlc(ohlc, min_bars=self.swing_window * 4 + 5)
        if not ok:
            return None

        res = _triangle_trendlines(ohlc, self.swing_window, self.min_pivots, self.lookback)
        if res is None:
            return None

        abs_ph, sl_h, ic_h, abs_pl, sl_l, ic_l, start, seg_len = res
        avg_price = float(ohlc["close"].iloc[start:].mean())
        if avg_price <= 0:
            return None

        norm_h = sl_h / avg_price
        norm_l = sl_l / avg_price

        if not (norm_h < -self.slope_threshold_pct and abs(norm_l) <= self.flat_threshold_pct):
            return None

        first_bar = min(min(abs_ph) - start, min(abs_pl) - start)
        height = (ic_h + sl_h * first_bar) - (ic_l + sl_l * first_bar)
        if height <= 0:
            return None

        support = ic_l + sl_l * (seg_len - 1)
        target = support - height

        confidence = round(
            min(0.82, 0.45 + 0.25 * min(1.0, abs(norm_h) / 0.002) + 0.12 * min(1.0, height / avg_price / 0.05)),
            3,
        )

        return PatternMatch(
            pattern_name=self.pattern_name,
            pattern_type=self.pattern_type,
            found=True,
            confidence=confidence,
            key_bars=sorted(set(abs_ph + abs_pl)),
            measured_move_target=float(round(target, 4)),
            neckline=float(round(support, 4)),
            details={
                "upper_slope": float(round(sl_h, 6)),
                "lower_slope": float(round(sl_l, 6)),
                "pattern_height": float(round(height, 4)),
                "support_level": float(round(support, 4)),
            },
        )


# ---------------------------------------------------------------------------
# Gap
# ---------------------------------------------------------------------------

class GapDetector(PatternDetector):
    """Gap detector — finds and classifies the most recent price gap.

    Gap types (Schwager Ch 5):
      * common     – fills within fill_bars regardless of trend context
      * breakaway  – occurs out of consolidation; counter-trend or no trend
      * runaway    – mid-trend; gap in the trend's direction, not filled
      * exhaustion – late-trend gap in trend direction that FILLS quickly

    Classification reads the pre-gap trend slope and filling behaviour.
    """

    pattern_name = "Gap"
    pattern_type = "neutral"

    def __init__(
        self,
        min_gap_atr_fraction: float = 0.25,
        fill_bars: int = 3,
        trend_lookback: int = 20,
        exhaustion_move_atr: float = 5.0,
    ):
        self.min_gap_atr_fraction = min_gap_atr_fraction
        self.fill_bars = fill_bars
        self.trend_lookback = trend_lookback
        self.exhaustion_move_atr = exhaustion_move_atr

    def detect(self, ohlc: pd.DataFrame) -> Optional[PatternMatch]:
        ok, _ = self._validate_ohlc(ohlc, min_bars=self.trend_lookback + 5)
        if not ok:
            return None

        high = ohlc["high"].to_numpy(dtype=float)
        low = ohlc["low"].to_numpy(dtype=float)
        close = ohlc["close"].to_numpy(dtype=float)
        n = len(close)
        atr = _rolling_atr(ohlc)

        for i in range(n - 1, 0, -1):
            gap_up = low[i] > high[i - 1]
            gap_dn = high[i] < low[i - 1]
            if not (gap_up or gap_dn):
                continue

            ra = _ref_atr(atr, i)
            gap_size = (low[i] - high[i - 1]) if gap_up else (low[i - 1] - high[i])
            if gap_size < self.min_gap_atr_fraction * ra:
                continue

            filled = False
            for j in range(i + 1, min(i + self.fill_bars + 1, n)):
                if gap_up and low[j] <= high[i - 1]:
                    filled = True
                    break
                if gap_dn and high[j] >= low[i - 1]:
                    filled = True
                    break

            # Pre-gap trend.
            pre_start = max(0, i - self.trend_lookback)
            pre_close = close[pre_start:i]
            x_pre = np.arange(len(pre_close), dtype=float)
            sl_pre, _ = _linreg(x_pre, pre_close)
            trend_move = sl_pre * max(len(pre_close) - 1, 1)
            trend_atr_units = abs(trend_move) / ra

            in_trend_direction = (gap_up and sl_pre > 0) or (gap_dn and sl_pre < 0)

            if filled and in_trend_direction and trend_atr_units > self.exhaustion_move_atr:
                gap_type = "exhaustion"
                gap_subtype = "bearish" if gap_up else "bullish"
                confidence = 0.65
            elif filled:
                gap_type = "common"
                gap_subtype = "neutral"
                confidence = 0.58
            elif in_trend_direction:
                gap_type = "runaway"
                gap_subtype = "bullish" if gap_up else "bearish"
                confidence = 0.68
            else:
                gap_type = "breakaway"
                gap_subtype = "bullish" if gap_up else "bearish"
                confidence = 0.70

            neckline = float(low[i]) if gap_up else float(high[i])
            target = neckline + gap_size if gap_up else neckline - gap_size

            return PatternMatch(
                pattern_name=f"Gap ({gap_type})",
                pattern_type=gap_subtype,
                found=True,
                confidence=float(round(confidence, 3)),
                key_bars=[i - 1, i],
                measured_move_target=float(round(target, 4)),
                neckline=float(round(neckline, 4)),
                details={
                    "gap_type": gap_type,
                    "gap_direction": "up" if gap_up else "down",
                    "gap_size": float(round(gap_size, 4)),
                    "gap_atr_fraction": float(round(gap_size / ra, 3)),
                    "filled": filled,
                    "trend_atr_units": float(round(trend_atr_units, 2)),
                },
            )

        return None


# ---------------------------------------------------------------------------
# Wide-Ranging Day
# ---------------------------------------------------------------------------

class WideRangingDayDetector(PatternDetector):
    """Wide-Ranging Day — bar whose range (high−low) exceeds N × ATR(14).

    Schwager (Ch 12): WRDs signal a conviction shift.  The close position
    within the bar determines directional bias: upper half → bullish,
    lower half → bearish.  The measured move projects one bar-range in the
    bias direction.
    """

    pattern_name = "Wide-Ranging Day"

    def __init__(
        self,
        atr_multiple: float = 2.0,
        lookback: int = 20,
        atr_period: int = 14,
    ):
        self.atr_multiple = atr_multiple
        self.lookback = lookback
        self.atr_period = atr_period

    def detect(self, ohlc: pd.DataFrame) -> Optional[PatternMatch]:
        ok, _ = self._validate_ohlc(ohlc, min_bars=self.atr_period + 2)
        if not ok:
            return None

        high = ohlc["high"].to_numpy(dtype=float)
        low = ohlc["low"].to_numpy(dtype=float)
        close = ohlc["close"].to_numpy(dtype=float)
        open_p = (
            ohlc["open"].to_numpy(dtype=float)
            if "open" in ohlc.columns
            else close.copy()
        )
        n = len(close)
        atr = _rolling_atr(ohlc, self.atr_period)

        for i in range(n - 1, max(0, n - self.lookback - 1), -1):
            if np.isnan(atr[i]) or atr[i] <= 0:
                continue
            bar_range = high[i] - low[i]
            if bar_range < self.atr_multiple * atr[i]:
                continue

            close_pct = (close[i] - low[i]) / bar_range
            bullish_wrd = close_pct >= 0.5

            target = (close[i] + bar_range) if bullish_wrd else (close[i] - bar_range)
            strength = min(1.0, bar_range / (atr[i] * self.atr_multiple * 1.5))
            conviction = abs(close_pct - 0.5) * 2
            confidence = round(min(0.85, 0.45 + 0.25 * strength + 0.15 * conviction), 3)

            return PatternMatch(
                pattern_name=self.pattern_name,
                pattern_type="bullish" if bullish_wrd else "bearish",
                found=True,
                confidence=confidence,
                key_bars=[i],
                measured_move_target=float(round(target, 4)),
                neckline=float(round(close[i], 4)),
                details={
                    "bar_index": int(i),
                    "bar_range": float(round(bar_range, 4)),
                    "atr": float(round(atr[i], 4)),
                    "range_atr_multiple": float(round(bar_range / atr[i], 3)),
                    "close_pct_in_range": float(round(close_pct, 3)),
                    "open_price": float(round(open_p[i], 4)),
                },
            )

        return None


# ---------------------------------------------------------------------------
# Aggregator
# ---------------------------------------------------------------------------

CONTINUATION_DETECTORS: List[PatternDetector] = [
    FlagDetector(),
    PennantDetector(),
    SymmetricalTriangleDetector(),
    AscendingTriangleDetector(),
    DescendingTriangleDetector(),
    GapDetector(),
    WideRangingDayDetector(),
]


def run_continuation_detectors(ohlc: pd.DataFrame) -> List[PatternMatch]:
    """Run all continuation / bar-pattern detectors; return found matches
    sorted newest-first by the rightmost key bar."""
    results: List[PatternMatch] = []
    for det in CONTINUATION_DETECTORS:
        try:
            m = det.detect(ohlc)
            if m is not None and m.found:
                results.append(m)
        except Exception:  # noqa: BLE001
            continue
    results.sort(key=lambda m: (m.key_bars[-1] if m.key_bars else 0), reverse=True)
    return results
