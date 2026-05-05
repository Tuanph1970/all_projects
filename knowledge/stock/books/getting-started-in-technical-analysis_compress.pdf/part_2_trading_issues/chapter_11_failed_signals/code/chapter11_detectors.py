"""
chapter11_detectors.py
======================
Pattern detection functions for the failed-signal concepts in Chapter 11
of "Getting Started in Technical Analysis" by Jack D. Schwager.

Each function takes an OHLC pandas DataFrame with columns:
    ['open', 'high', 'low', 'close']
indexed by date, and returns a DataFrame of detected events.

These are reference implementations meant to teach the *idea*; production
trading systems would tune thresholds and add risk/sizing logic.
"""
from __future__ import annotations
import pandas as pd
import numpy as np
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Concept 2 — Bull / Bear Trap
# ---------------------------------------------------------------------------
def detect_bull_bear_traps(
    df: pd.DataFrame,
    lookback: int = 20,
    initial_confirm_days: int = 1,
    strong_confirm_days: int = 1,
    time_confirm_days: int = 20,
) -> pd.DataFrame:
    """
    A bull trap = upside breakout above prior `lookback` high, followed by:
      - initial price confirmation: close BACK INSIDE the prior range
      - OR strong price confirmation: close BELOW prior `lookback` low
      - OR time confirmation: `time_confirm_days` elapse without new high

    Returns one row per detected trap event with the trigger date and type.
    """
    high_n = df["high"].rolling(lookback).max().shift(1)
    low_n  = df["low"].rolling(lookback).min().shift(1)
    events = []

    for i in range(lookback, len(df) - time_confirm_days):
        # ---- BULL TRAP search
        if df["high"].iloc[i] > high_n.iloc[i]:                  # breakout up
            breakout_high = df["high"].iloc[i]
            range_low     = low_n.iloc[i]
            for j in range(i + 1, min(i + time_confirm_days + 1, len(df))):
                # Invalidation: new high above the breakout
                if df["high"].iloc[j] > breakout_high:
                    break
                # Initial confirmation: close back inside the prior range
                if df["close"].iloc[j] < high_n.iloc[i]:
                    events.append(dict(
                        date=df.index[j], type="bull_trap",
                        confirmation="initial_price",
                        breakout_date=df.index[i],
                        breakout_level=high_n.iloc[i]))
                    break
                # Strong confirmation: close below opposite end of range
                if df["close"].iloc[j] < range_low:
                    events.append(dict(
                        date=df.index[j], type="bull_trap",
                        confirmation="strong_price",
                        breakout_date=df.index[i],
                        breakout_level=high_n.iloc[i]))
                    break

        # ---- BEAR TRAP search (mirror)
        if df["low"].iloc[i] < low_n.iloc[i]:
            breakout_low = df["low"].iloc[i]
            range_high   = high_n.iloc[i]
            for j in range(i + 1, min(i + time_confirm_days + 1, len(df))):
                if df["low"].iloc[j] < breakout_low:
                    break
                if df["close"].iloc[j] > low_n.iloc[i]:
                    events.append(dict(
                        date=df.index[j], type="bear_trap",
                        confirmation="initial_price",
                        breakout_date=df.index[i],
                        breakout_level=low_n.iloc[i]))
                    break
                if df["close"].iloc[j] > range_high:
                    events.append(dict(
                        date=df.index[j], type="bear_trap",
                        confirmation="strong_price",
                        breakout_date=df.index[i],
                        breakout_level=low_n.iloc[i]))
                    break
    return pd.DataFrame(events)


# ---------------------------------------------------------------------------
# Concept 4 — False Trend Line Breakouts
# ---------------------------------------------------------------------------
def detect_false_trendline_break(
    closes: pd.Series, slope: float, intercept: float, x0: int,
    direction: str = "up", confirm_closes: int = 2,
) -> list[int]:
    """
    Given a trend line `y = slope*(t - x0) + intercept`, return indices where
    the close re-crosses the line `confirm_closes` times after an initial break.

    direction = "up"   → uptrend line; we test for false DOWNSIDE break
    direction = "down" → downtrend line; we test for false UPSIDE break
    """
    events = []
    on_wrong_side = 0
    for t in range(x0, len(closes)):
        line = slope * (t - x0) + intercept
        if direction == "up":
            broke = closes.iloc[t] < line          # below the uptrend line
            recovered = closes.iloc[t] > line
        else:
            broke = closes.iloc[t] > line          # above the downtrend line
            recovered = closes.iloc[t] < line

        if broke:
            on_wrong_side += 1
            recover_streak = 0
        elif on_wrong_side > 0 and recovered:
            recover_streak = locals().get("recover_streak", 0) + 1
            if recover_streak >= confirm_closes:
                events.append(t)
                on_wrong_side = 0
                recover_streak = 0
    return events


# ---------------------------------------------------------------------------
# Concept 5 — Filled Gaps
# ---------------------------------------------------------------------------
def detect_filled_gaps(df: pd.DataFrame, max_lookahead: int = 30) -> pd.DataFrame:
    """
    A gap day's low > prior day's high (upside gap) or
    a gap day's high < prior day's low (downside gap).

    The gap is FILLED when a later close passes the prior day's close
    (Schwager's stricter definition).
    """
    out = []
    prior_close = df["close"].shift(1)
    prior_high  = df["high"].shift(1)
    prior_low   = df["low"].shift(1)

    for i in range(1, len(df) - 1):
        # upside gap
        if df["low"].iloc[i] > prior_high.iloc[i]:
            for j in range(i + 1, min(i + max_lookahead + 1, len(df))):
                if df["close"].iloc[j] < prior_close.iloc[i]:
                    out.append(dict(
                        gap_date=df.index[i], fill_date=df.index[j],
                        gap_type="up", gap_size=df["low"].iloc[i] - prior_high.iloc[i]))
                    break
        # downside gap
        if df["high"].iloc[i] < prior_low.iloc[i]:
            for j in range(i + 1, min(i + max_lookahead + 1, len(df))):
                if df["close"].iloc[j] > prior_close.iloc[i]:
                    out.append(dict(
                        gap_date=df.index[i], fill_date=df.index[j],
                        gap_type="down", gap_size=prior_low.iloc[i] - df["high"].iloc[i]))
                    break
    return pd.DataFrame(out)


# ---------------------------------------------------------------------------
# Concept 6 — Return to Spike Extremes
# ---------------------------------------------------------------------------
def detect_spikes(df: pd.DataFrame, k: float = 1.5) -> pd.DataFrame:
    """
    Spike high: high > prior high AND high > next high, with the close
    near the LOW of the day's range. Spike strength is scaled by `k`.
    """
    rng   = df["high"] - df["low"]
    spikes = []
    for i in range(1, len(df) - 1):
        # spike high
        if (df["high"].iloc[i] > df["high"].iloc[i-1] + k*rng.iloc[i-1]
                and df["high"].iloc[i] > df["high"].iloc[i+1] + k*rng.iloc[i+1]
                and df["close"].iloc[i] < df["low"].iloc[i] + 0.4*rng.iloc[i]):
            spikes.append(dict(date=df.index[i], type="spike_high",
                               level=df["high"].iloc[i]))
        # spike low
        if (df["low"].iloc[i] < df["low"].iloc[i-1] - k*rng.iloc[i-1]
                and df["low"].iloc[i] < df["low"].iloc[i+1] - k*rng.iloc[i+1]
                and df["close"].iloc[i] > df["high"].iloc[i] - 0.4*rng.iloc[i]):
            spikes.append(dict(date=df.index[i], type="spike_low",
                               level=df["low"].iloc[i]))
    return pd.DataFrame(spikes)


def detect_spike_failures(df: pd.DataFrame, spikes: pd.DataFrame,
                          min_age_days: int = 20) -> pd.DataFrame:
    """A spike is 'failed' when price closes beyond its extreme."""
    out = []
    for _, sp in spikes.iterrows():
        spike_idx = df.index.get_loc(sp["date"])
        for j in range(spike_idx + min_age_days, len(df)):
            if sp["type"] == "spike_high" and df["close"].iloc[j] > sp["level"]:
                out.append(dict(spike_date=sp["date"], failure_date=df.index[j],
                                type="spike_high_failed"))
                break
            if sp["type"] == "spike_low" and df["close"].iloc[j] < sp["level"]:
                out.append(dict(spike_date=sp["date"], failure_date=df.index[j],
                                type="spike_low_failed"))
                break
    return pd.DataFrame(out)


# ---------------------------------------------------------------------------
# Concept 7 — Wide-Ranging Day Failure
# ---------------------------------------------------------------------------
def detect_wide_ranging_days(df: pd.DataFrame, n: int = 15, k: float = 2.0
                             ) -> pd.DataFrame:
    """
    Wide-ranging day: today's true range / true range of past N days > k.
    Direction = 'up' if close near top, 'down' if close near bottom.
    """
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"]  - prev_close).abs()
    ], axis=1).max(axis=1)

    avg_tr = tr.rolling(n).mean()
    vr = tr / avg_tr
    rng = df["high"] - df["low"]
    pos = (df["close"] - df["low"]) / rng     # 0 = at low, 1 = at high

    wrd = []
    for i in range(n, len(df)):
        if vr.iloc[i] > k:
            direction = "up" if pos.iloc[i] > 0.7 else (
                        "down" if pos.iloc[i] < 0.3 else "neutral")
            wrd.append(dict(
                date=df.index[i], direction=direction, vr=float(vr.iloc[i]),
                day_high=df["high"].iloc[i], day_low=df["low"].iloc[i]))
    return pd.DataFrame(wrd)


def detect_wrd_failures(df: pd.DataFrame, wrds: pd.DataFrame) -> pd.DataFrame:
    """A WRD fails when price closes beyond the *opposite* extreme of the bar."""
    out = []
    for _, w in wrds.iterrows():
        if w["direction"] == "neutral":
            continue
        idx = df.index.get_loc(w["date"])
        for j in range(idx + 1, len(df)):
            if w["direction"] == "down" and df["close"].iloc[j] > w["day_high"]:
                out.append(dict(wrd_date=w["date"], fail_date=df.index[j],
                                type="wrd_down_failed"))
                break
            if w["direction"] == "up" and df["close"].iloc[j] < w["day_low"]:
                out.append(dict(wrd_date=w["date"], fail_date=df.index[j],
                                type="wrd_up_failed"))
                break
    return pd.DataFrame(out)


# ---------------------------------------------------------------------------
# Concept 8 / 9 — Flag/Pennant counter & opposite-direction breakouts
# ---------------------------------------------------------------------------
@dataclass
class FlagPattern:
    start_idx: int
    end_idx: int
    upper: float
    lower: float
    prior_trend: str          # "up" or "down"


def detect_flag_failures(df: pd.DataFrame, flag: FlagPattern,
                         lookahead: int = 30) -> dict:
    """
    Given a hand-identified flag/pennant region, scan forward and classify:
      - 'normal'              : breakout in expected direction (continuation)
      - 'counter_anticipated' : breakout in opposite direction
      - 'opposite_after_normal': normal break then closes beyond opposite end
    """
    after = df.iloc[flag.end_idx + 1: flag.end_idx + 1 + lookahead]
    expected = "up" if flag.prior_trend == "up" else "down"

    state = "inside"
    for i, (_, bar) in enumerate(after.iterrows()):
        if state == "inside":
            if bar["close"] > flag.upper and expected == "up":
                state = "normal_up"
            elif bar["close"] < flag.lower and expected == "down":
                state = "normal_down"
            elif bar["close"] > flag.upper and expected == "down":
                return dict(type="counter_anticipated", direction="up",
                            day=after.index[i])
            elif bar["close"] < flag.lower and expected == "up":
                return dict(type="counter_anticipated", direction="down",
                            day=after.index[i])
        elif state == "normal_up" and bar["close"] < flag.lower:
            return dict(type="opposite_after_normal", direction="down",
                        day=after.index[i])
        elif state == "normal_down" and bar["close"] > flag.upper:
            return dict(type="opposite_after_normal", direction="up",
                        day=after.index[i])

    return dict(type=state, direction=None, day=None)


# ---------------------------------------------------------------------------
# Concept 10 — Failed Head-and-Shoulders
# ---------------------------------------------------------------------------
@dataclass
class HeadAndShoulders:
    left_shoulder_idx: int
    head_idx: int
    right_shoulder_idx: int
    pattern: str = "top"        # "top" or "bottom"


def detect_hs_failure(df: pd.DataFrame, hs: HeadAndShoulders,
                      lookahead: int = 60) -> int | None:
    """
    Failed H&S top: close ABOVE the right-shoulder high.
    Failed H&S bottom: close BELOW the right-shoulder low.
    Returns the index of failure or None.
    """
    rs_idx = hs.right_shoulder_idx
    rs_level = (df["high"].iloc[rs_idx] if hs.pattern == "top"
                else df["low"].iloc[rs_idx])
    for j in range(rs_idx + 1, min(rs_idx + lookahead + 1, len(df))):
        if hs.pattern == "top" and df["close"].iloc[j] > rs_level:
            return j
        if hs.pattern == "bottom" and df["close"].iloc[j] < rs_level:
            return j
    return None


# ---------------------------------------------------------------------------
# Concept 11 — Breaking of Curvature (rounding pattern failure)
# ---------------------------------------------------------------------------
def fit_rounding_curve(closes: pd.Series, start: int, end: int,
                       pattern: str = "top") -> tuple:
    """Fit y = a*(x - h)^2 + k to the segment; for tops, a < 0."""
    x = np.arange(end - start)
    y = closes.iloc[start:end].values
    coeffs = np.polyfit(x, y, 2)         # a*x^2 + b*x + c
    return coeffs


def detect_curvature_break(closes: pd.Series, start: int, end: int,
                           pattern: str = "top", lookahead: int = 30,
                           tolerance: float = 0.02) -> int | None:
    """
    Project the fitted parabola forward; flag the first close that violates
    the curve by more than `tolerance` * price (i.e. curvature broken).
    """
    coeffs = fit_rounding_curve(closes, start, end, pattern)
    a, b, c = coeffs
    for j in range(end, min(end + lookahead, len(closes))):
        x = j - start
        proj = a*x*x + b*x + c
        actual = closes.iloc[j]
        if pattern == "top" and actual > proj * (1 + tolerance):
            return j
        if pattern == "bottom" and actual < proj * (1 - tolerance):
            return j
    return None


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Build a tiny synthetic series that contains a bull trap
    np.random.seed(1)
    n = 80
    closes = np.r_[
        np.linspace(50, 51, 25) + np.random.randn(25) * 0.3,    # range
        np.linspace(51, 56, 4)  + np.random.randn(4)  * 0.3,    # breakout
        np.linspace(56, 47, 8)  + np.random.randn(8)  * 0.4,    # fail
        np.linspace(47, 42, 43) + np.random.randn(43) * 0.4,
    ]
    dates = pd.bdate_range("2024-01-01", periods=n)
    df = pd.DataFrame({
        "open":  np.r_[closes[0], closes[:-1]],
        "high":  closes + np.abs(np.random.randn(n)) * 0.4,
        "low":   closes - np.abs(np.random.randn(n)) * 0.4,
        "close": closes,
    }, index=dates)

    traps = detect_bull_bear_traps(df, lookback=20)
    print("Bull/bear traps detected:")
    print(traps)

    gaps = detect_filled_gaps(df)
    print(f"\nFilled gaps: {len(gaps)}")
