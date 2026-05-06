"""
Chapter 5 — Chart Pattern Detection
====================================

A consolidated reference module collecting the detection routines sketched
throughout the Chapter 5 study notes. Patterns are split into three families,
mirroring Schwager's chapter structure:

    1. One-day patterns   : gaps, spikes, reversal days, thrust days, wide-ranging days
    2. Continuation       : triangles, flags & pennants
    3. Top/bottom forms   : V, double, triple, head & shoulders, rounded, wedges, islands

Conventions:
    - All functions take a pandas DataFrame `df` with columns:
          ['open', 'high', 'low', 'close']  (lowercase, DatetimeIndex)
    - Detection functions return either a boolean Series aligned to df.index,
      or a dict / list of dicts describing pattern occurrences.
    - These are *teaching implementations*, not battle-tested production code.
      They favor clarity over robustness. Use them as a starting point.

Dependencies:
    pip install pandas numpy
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Shared primitives
# ---------------------------------------------------------------------------

def true_range(df: pd.DataFrame) -> pd.Series:
    """Wilder's true range: max of (H-L, |H - prevC|, |L - prevC|)."""
    prev_close = df["close"].shift(1)
    a = df["high"] - df["low"]
    b = (df["high"] - prev_close).abs()
    c = (df["low"] - prev_close).abs()
    return pd.concat([a, b, c], axis=1).max(axis=1)


def atr(df: pd.DataFrame, window: int = 15) -> pd.Series:
    """Simple-moving-average ATR over `window` bars (Schwager uses 15)."""
    return true_range(df).rolling(window).mean()


def find_swing_highs(df: pd.DataFrame, window: int = 5) -> pd.Series:
    """Boolean Series: True where high is the max in a +/- `window` window."""
    rolled = df["high"].rolling(2 * window + 1, center=True).max()
    return (df["high"] == rolled) & df["high"].notna()


def find_swing_lows(df: pd.DataFrame, window: int = 5) -> pd.Series:
    rolled = df["low"].rolling(2 * window + 1, center=True).min()
    return (df["low"] == rolled) & df["low"].notna()


# ---------------------------------------------------------------------------
# 1. ONE-DAY PATTERNS
# ---------------------------------------------------------------------------

def detect_gaps(df: pd.DataFrame) -> pd.DataFrame:
    """Tag each bar with gap_up / gap_down booleans and gap size."""
    out = pd.DataFrame(index=df.index)
    prev_high = df["high"].shift(1)
    prev_low = df["low"].shift(1)
    out["gap_up"] = df["low"] > prev_high
    out["gap_down"] = df["high"] < prev_low
    out["gap_size"] = np.where(out["gap_up"], df["low"] - prev_high,
                                np.where(out["gap_down"], prev_low - df["high"], 0.0))
    return out


def is_filled(df: pd.DataFrame, gap_idx: int, lookahead: int = 5) -> bool:
    """Has the gap that opened at `gap_idx` been filled in the next N bars?"""
    if gap_idx < 1 or gap_idx >= len(df):
        return False
    prev_high = df["high"].iloc[gap_idx - 1]
    prev_low = df["low"].iloc[gap_idx - 1]
    today_low = df["low"].iloc[gap_idx]
    today_high = df["high"].iloc[gap_idx]
    forward = df.iloc[gap_idx + 1: gap_idx + 1 + lookahead]
    if forward.empty:
        return False
    if today_low > prev_high:                   # gap up: filled when price re-enters
        return (forward["low"] <= prev_high).any()
    if today_high < prev_low:                   # gap down
        return (forward["high"] >= prev_low).any()
    return False


def detect_spike_highs(df: pd.DataFrame, window: int = 10,
                       gap_factor: float = 0.5) -> pd.Series:
    """Spike high = bar whose high exceeds the surrounding bars by a wide margin
    AND closes near the opposite extreme (low end of its range)."""
    surrounding_max = df["high"].rolling(2 * window + 1, center=True).max().shift(0)
    is_local_top = df["high"] == surrounding_max
    sep_left = df["high"] - df["high"].shift(1)
    sep_right = df["high"] - df["high"].shift(-1)
    rng = df["high"] - df["low"]
    wide_separation = (sep_left > gap_factor * rng) & (sep_right > gap_factor * rng)
    closes_low = (df["close"] - df["low"]) < 0.25 * rng
    return is_local_top & wide_separation & closes_low


def detect_spike_lows(df: pd.DataFrame, window: int = 10,
                      gap_factor: float = 0.5) -> pd.Series:
    surrounding_min = df["low"].rolling(2 * window + 1, center=True).min().shift(0)
    is_local_bot = df["low"] == surrounding_min
    sep_left = df["low"].shift(1) - df["low"]
    sep_right = df["low"].shift(-1) - df["low"]
    rng = df["high"] - df["low"]
    wide_separation = (sep_left > gap_factor * rng) & (sep_right > gap_factor * rng)
    closes_high = (df["high"] - df["close"]) < 0.25 * rng
    return is_local_bot & wide_separation & closes_high


def reversal_high_days(df: pd.DataFrame, strong: bool = True) -> pd.Series:
    """Schwager's strong reversal-high day: new high (vs N prior bars) AND
    close below the *prior bar's low*. Standard variant: close below open."""
    new_high = df["high"] > df["high"].rolling(20).max().shift(1)
    if strong:
        cond = df["close"] < df["low"].shift(1)
    else:
        cond = df["close"] < df["open"]
    return new_high & cond


def reversal_low_days(df: pd.DataFrame, strong: bool = True) -> pd.Series:
    new_low = df["low"] < df["low"].rolling(20).min().shift(1)
    if strong:
        cond = df["close"] > df["high"].shift(1)
    else:
        cond = df["close"] > df["open"]
    return new_low & cond


def thrust_days(df: pd.DataFrame) -> pd.DataFrame:
    """Up-thrust: close > prior high. Down-thrust: close < prior low."""
    out = pd.DataFrame(index=df.index)
    out["up_thrust"] = df["close"] > df["high"].shift(1)
    out["down_thrust"] = df["close"] < df["low"].shift(1)
    return out


def thrust_clusters(df: pd.DataFrame, n: int = 3) -> pd.Series:
    """Returns +1 where there are >=n up-thrusts in last 5 bars, -1 for down."""
    t = thrust_days(df)
    up = t["up_thrust"].rolling(5).sum() >= n
    dn = t["down_thrust"].rolling(5).sum() >= n
    return up.astype(int) - dn.astype(int)


def wide_ranging_days(df: pd.DataFrame, atr_window: int = 15,
                      threshold: float = 2.0) -> pd.Series:
    """Volatility ratio = TR / ATR15.  Schwager flags VR > 2.0."""
    tr = true_range(df)
    a = atr(df, atr_window)
    vr = tr / a
    return vr > threshold


# ---------------------------------------------------------------------------
# 2. CONTINUATION PATTERNS
# ---------------------------------------------------------------------------

def detect_triangle(df: pd.DataFrame, window: int = 30,
                    convergence_pct: float = 0.5) -> dict | None:
    """Fit upper/lower lines through recent swing points; report triangle if
    the channel narrows by at least `convergence_pct` from start to end."""
    seg = df.tail(window)
    if len(seg) < window:
        return None
    sh = find_swing_highs(seg, window=2)
    sl = find_swing_lows(seg, window=2)
    if sh.sum() < 2 or sl.sum() < 2:
        return None

    high_pts = seg.loc[sh, "high"]
    low_pts = seg.loc[sl, "low"]
    x_h = np.arange(len(seg))[sh.values]
    x_l = np.arange(len(seg))[sl.values]
    upper_m, upper_b = np.polyfit(x_h, high_pts.values, 1)
    lower_m, lower_b = np.polyfit(x_l, low_pts.values, 1)

    width_start = (upper_b) - (lower_b)
    width_end = (upper_m * (window - 1) + upper_b) - (lower_m * (window - 1) + lower_b)
    if width_start <= 0 or width_end / width_start > (1 - convergence_pct):
        return None

    # Classify
    if upper_m < -1e-9 and lower_m > 1e-9:
        kind = "symmetrical"
    elif abs(upper_m) < 1e-9 and lower_m > 1e-9:
        kind = "ascending"
    elif upper_m < -1e-9 and abs(lower_m) < 1e-9:
        kind = "descending"
    else:
        kind = "irregular"

    return {
        "kind": kind,
        "upper_slope": upper_m,
        "lower_slope": lower_m,
        "width_start": width_start,
        "width_end": width_end,
        "convergence": 1 - width_end / width_start,
    }


def triangle_breakout(df: pd.DataFrame, upper: float, lower: float) -> str | None:
    """Return 'up' / 'down' / None given last close vs the boundary lines."""
    last = df["close"].iloc[-1]
    if last > upper:
        return "up"
    if last < lower:
        return "down"
    return None


def find_flagpole(df: pd.DataFrame, min_pct: float = 0.10,
                  max_bars: int = 8) -> tuple[int, int] | None:
    """Find the most recent strong, fast move (the 'pole')."""
    closes = df["close"].values
    for end in range(len(closes) - 1, max_bars, -1):
        for start in range(end - max_bars, end - 2):
            move = (closes[end] - closes[start]) / closes[start]
            if abs(move) >= min_pct:
                return start, end
    return None


def detect_flag(df: pd.DataFrame, max_bars: int = 15) -> dict | None:
    """Pole + tight, slightly counter-trend consolidation."""
    pole = find_flagpole(df)
    if pole is None:
        return None
    s, e = pole
    flag_seg = df.iloc[e: e + max_bars]
    if len(flag_seg) < 4:
        return None
    pole_height = abs(df["close"].iloc[e] - df["close"].iloc[s])
    flag_range = flag_seg["high"].max() - flag_seg["low"].min()
    if flag_range > 0.5 * pole_height:
        return None
    direction = "bull" if df["close"].iloc[e] > df["close"].iloc[s] else "bear"
    return {"pole_start": s, "pole_end": e, "flag_bars": len(flag_seg),
            "direction": direction, "pole_height": pole_height,
            "flag_range": flag_range}


def flag_target(pole_start_price: float, pole_end_price: float,
                breakout_price: float) -> float:
    """Measured-move target = breakout +/- pole height."""
    pole = pole_end_price - pole_start_price
    return breakout_price + pole


# ---------------------------------------------------------------------------
# 3. TOP / BOTTOM PATTERNS
# ---------------------------------------------------------------------------

def detect_v_top(df: pd.DataFrame, run_length: int = 20,
                 reversal_pct: float = 0.05) -> dict | None:
    """Sharp run-up of `run_length` bars, then a sharp single-bar reversal."""
    if len(df) < run_length + 2:
        return None
    pre = df["close"].iloc[-run_length - 1: -1]
    last = df["close"].iloc[-1]
    run_up = (pre.iloc[-1] - pre.iloc[0]) / pre.iloc[0]
    pull_back = (last - pre.iloc[-1]) / pre.iloc[-1]
    if run_up > reversal_pct and pull_back < -reversal_pct:
        return {"run_up": run_up, "pull_back": pull_back, "peak_idx": len(df) - 2}
    return None


def confirm_v_with_spike_or_reversal(df: pd.DataFrame, v_idx: int) -> bool:
    spikes = detect_spike_highs(df).iloc[max(0, v_idx - 2): v_idx + 1]
    revs = reversal_high_days(df).iloc[max(0, v_idx - 2): v_idx + 1]
    return bool(spikes.any() or revs.any())


def detect_double_top(df: pd.DataFrame, window: int = 60,
                      tol: float = 0.02) -> dict | None:
    """Two prominent peaks within `tol` of each other, separated by a trough."""
    seg = df.tail(window)
    sh = find_swing_highs(seg, window=3)
    peaks = seg.loc[sh, "high"].sort_values(ascending=False)
    if len(peaks) < 2:
        return None
    p1, p2 = peaks.iloc[0], peaks.iloc[1]
    if abs(p1 - p2) / max(p1, p2) > tol:
        return None
    i1, i2 = sorted([peaks.index[0], peaks.index[1]])
    trough = seg.loc[i1:i2, "low"].min()
    height = max(p1, p2) - trough
    return {"peak_1": p1, "peak_2": p2, "neckline": trough,
            "height": height, "target": trough - height}


def detect_triple_top(df: pd.DataFrame, window: int = 100,
                      tol: float = 0.025) -> dict | None:
    seg = df.tail(window)
    sh = find_swing_highs(seg, window=3)
    peaks = seg.loc[sh, "high"]
    if len(peaks) < 3:
        return None
    top3 = peaks.sort_values(ascending=False).head(3)
    if (top3.max() - top3.min()) / top3.max() > tol:
        return None
    idxs = sorted(top3.index)
    troughs = [seg.loc[idxs[i]:idxs[i + 1], "low"].min() for i in range(2)]
    neckline = min(troughs)
    height = top3.mean() - neckline
    return {"peaks": list(top3.values), "neckline": neckline,
            "height": height, "target": neckline - height}


def detect_head_and_shoulders(df: pd.DataFrame, window: int = 80,
                              shoulder_tol: float = 0.05) -> dict | None:
    """LS, head (highest), RS where head > both shoulders and shoulders are
    at roughly equal height. Neckline = avg of the two intervening troughs."""
    seg = df.tail(window)
    sh = find_swing_highs(seg, window=3)
    peaks = seg.loc[sh, "high"]
    if len(peaks) < 3:
        return None
    # Look at last three peaks in chronological order
    last3 = peaks.iloc[-3:]
    ls, head, rs = last3.iloc[0], last3.iloc[1], last3.iloc[2]
    if not (head > ls and head > rs):
        return None
    if abs(ls - rs) / head > shoulder_tol:
        return None
    idxs = list(last3.index)
    trough1 = seg.loc[idxs[0]:idxs[1], "low"].min()
    trough2 = seg.loc[idxs[1]:idxs[2], "low"].min()
    neckline = (trough1 + trough2) / 2
    height = head - neckline
    return {"left_shoulder": ls, "head": head, "right_shoulder": rs,
            "neckline": neckline, "height": height,
            "target": neckline - height}


def detect_rounding(df: pd.DataFrame, window: int = 60,
                    r2_min: float = 0.7) -> dict | None:
    """Fit a parabola y = ax^2 + bx + c. Rounded top: a < 0; bottom: a > 0."""
    seg = df.tail(window)["close"].values
    if len(seg) < window:
        return None
    x = np.arange(len(seg))
    a, b, c = np.polyfit(x, seg, 2)
    fitted = a * x ** 2 + b * x + c
    ss_res = ((seg - fitted) ** 2).sum()
    ss_tot = ((seg - seg.mean()) ** 2).sum()
    r2 = 1 - ss_res / ss_tot if ss_tot else 0
    if r2 < r2_min:
        return None
    kind = "rounded_top" if a < 0 else "rounded_bottom"
    return {"kind": kind, "curvature_a": a, "r2": r2, "fitted": fitted}


def break_of_curvature(df: pd.DataFrame, fitted_curve: np.ndarray,
                       buffer: float = 0.0) -> int | None:
    """Index of first bar where close diverges meaningfully from fitted curve."""
    closes = df.tail(len(fitted_curve))["close"].values
    diffs = closes - fitted_curve
    sigma = np.std(diffs)
    for i, d in enumerate(diffs):
        if abs(d) > 2 * sigma + buffer:
            return i
    return None


def detect_wedge(df: pd.DataFrame, window: int = 40,
                 min_convergence: float = 0.4) -> dict | None:
    """Wedge: both boundary lines slope the *same* direction but converge."""
    seg = df.tail(window)
    if len(seg) < window:
        return None
    sh = find_swing_highs(seg, window=2)
    sl = find_swing_lows(seg, window=2)
    if sh.sum() < 2 or sl.sum() < 2:
        return None
    x_h = np.arange(len(seg))[sh.values]
    x_l = np.arange(len(seg))[sl.values]
    upper_m, upper_b = np.polyfit(x_h, seg.loc[sh, "high"].values, 1)
    lower_m, lower_b = np.polyfit(x_l, seg.loc[sl, "low"].values, 1)

    # Same direction?
    if np.sign(upper_m) != np.sign(lower_m) or abs(upper_m) < 1e-9:
        return None

    width_start = upper_b - lower_b
    width_end = (upper_m * (window - 1) + upper_b) - (lower_m * (window - 1) + lower_b)
    if width_start <= 0:
        return None
    convergence = 1 - width_end / width_start
    if convergence < min_convergence:
        return None

    kind = "rising_wedge" if upper_m > 0 else "falling_wedge"
    expected_break = "down" if kind == "rising_wedge" else "up"
    return {"kind": kind, "expected_break": expected_break,
            "convergence": convergence,
            "upper_slope": upper_m, "lower_slope": lower_m}


def wedge_target(wedge_widest: float, breakout_price: float,
                 direction: str) -> float:
    """Conservative target = breakout +/- wedge's widest height."""
    return breakout_price + wedge_widest if direction == "up" \
        else breakout_price - wedge_widest


def detect_island_top(df: pd.DataFrame, max_island_bars: int = 10) -> dict | None:
    """Gap up, sideways/up cluster, gap down — the cluster sits on its own
    'island' surrounded by gap-induced empty space."""
    gaps = detect_gaps(df)
    up_idx = np.where(gaps["gap_up"])[0]
    for u in up_idx:
        for d in range(u + 2, min(u + max_island_bars + 1, len(df))):
            if not gaps["gap_down"].iloc[d]:
                continue
            # Confirm island: low of every bar in [u, d-1] is above d's high
            island_lows = df["low"].iloc[u: d].min()
            if island_lows > df["high"].iloc[d]:
                return {"start_idx": u, "end_idx": d,
                        "island_low": island_lows,
                        "gap_down_high": df["high"].iloc[d],
                        "size": d - u}
    return None


def detect_island_bottom(df: pd.DataFrame, max_island_bars: int = 10) -> dict | None:
    gaps = detect_gaps(df)
    dn_idx = np.where(gaps["gap_down"])[0]
    for u in dn_idx:
        for d in range(u + 2, min(u + max_island_bars + 1, len(df))):
            if not gaps["gap_up"].iloc[d]:
                continue
            island_highs = df["high"].iloc[u: d].max()
            if island_highs < df["low"].iloc[d]:
                return {"start_idx": u, "end_idx": d,
                        "island_high": island_highs,
                        "gap_up_low": df["low"].iloc[d],
                        "size": d - u}
    return None


# ---------------------------------------------------------------------------
# Convenience: combined signals
# ---------------------------------------------------------------------------

def reversal_and_spike(df: pd.DataFrame) -> pd.Series:
    """Composite: bar that is both a strong reversal AND a spike — high confidence."""
    rh = reversal_high_days(df, strong=True)
    sh = detect_spike_highs(df)
    rl = reversal_low_days(df, strong=True)
    sl = detect_spike_lows(df)
    return (rh & sh).astype(int) - (rl & sl).astype(int)


def measured_target(breakout_price: float, widest_height: float,
                    direction: str) -> float:
    """Generic measured-move target for double/triple/H&S patterns."""
    return breakout_price - widest_height if direction == "down" \
        else breakout_price + widest_height


# ---------------------------------------------------------------------------
# Quick demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # synthetic OHLC for smoke-testing
    rng = np.random.default_rng(42)
    n = 200
    drift = np.cumsum(rng.normal(0, 1, n))
    close = 100 + drift
    high = close + rng.uniform(0.5, 2.0, n)
    low = close - rng.uniform(0.5, 2.0, n)
    open_ = close + rng.normal(0, 0.5, n)
    df = pd.DataFrame({"open": open_, "high": high, "low": low, "close": close},
                      index=pd.date_range("2024-01-01", periods=n))

    print("Gaps detected:", detect_gaps(df)[["gap_up", "gap_down"]].sum().to_dict())
    print("Wide-ranging days:", int(wide_ranging_days(df).sum()))
    print("Reversal highs:", int(reversal_high_days(df).sum()))
    print("Triangle:", detect_triangle(df))
    print("Wedge:", detect_wedge(df))
    print("Rounding:", detect_rounding(df))
