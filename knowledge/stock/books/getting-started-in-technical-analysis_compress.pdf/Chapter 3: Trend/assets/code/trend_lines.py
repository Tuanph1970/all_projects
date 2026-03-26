"""
trend_lines.py — Six Trend Line Methods for Technical Analysis
==============================================================

Methods 1-3, 5: From Jack Schwager, "Getting Started in Technical Analysis"
Methods 4, 6:   Standard quantitative methods (linear regression, regression channels)

Requirements:
    pip install pandas numpy matplotlib

Optional (for live data):
    pip install yfinance

Usage:
    python trend_lines.py
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from dataclasses import dataclass
from typing import Optional


# =============================================================================
# SHARED: Swing Point Detection (foundation for methods 1, 2, 3)
# =============================================================================

def detect_swing_points(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """
    Detect Relative Highs (RH) and Relative Lows (RL) using Schwager's
    formal definition (Glossary, p.329):

        RH at bar i: high[i] > high[j] for all j in [i-n, i+n], j != i
        RL at bar i: low[i]  < low[j]  for all j in [i-n, i+n], j != i

    Parameters
    ----------
    df : DataFrame with 'high' and 'low' columns
    n  : lookback/lookforward window (Schwager recommends 5-15)

    Returns
    -------
    DataFrame with added bool columns: 'is_rh', 'is_rl'
    """
    highs = df["high"].values
    lows = df["low"].values
    length = len(df)

    is_rh = np.zeros(length, dtype=bool)
    is_rl = np.zeros(length, dtype=bool)

    for i in range(n, length - n):
        window_highs = highs[i - n : i + n + 1]
        window_lows = lows[i - n : i + n + 1]

        # RH: this bar's high is strictly the max in the window
        if highs[i] == np.max(window_highs) and np.sum(window_highs == highs[i]) == 1:
            is_rh[i] = True

        # RL: this bar's low is strictly the min in the window
        if lows[i] == np.min(window_lows) and np.sum(window_lows == lows[i]) == 1:
            is_rl[i] = True

    result = df.copy()
    result["is_rh"] = is_rh
    result["is_rl"] = is_rl
    return result


# =============================================================================
# METHOD 1: Conventional Trend Lines (Schwager Ch.3, pp.34-39)
# =============================================================================

@dataclass
class TrendLine:
    """A trend line defined by two anchor points."""
    x1: int        # index of first anchor
    x2: int        # index of second anchor
    y1: float      # price at first anchor
    y2: float      # price at second anchor
    direction: str # 'up' or 'down'

    @property
    def slope(self) -> float:
        if self.x2 == self.x1:
            return 0.0
        return (self.y2 - self.y1) / (self.x2 - self.x1)

    @property
    def intercept(self) -> float:
        return self.y1 - self.slope * self.x1

    def value_at(self, x: int) -> float:
        """Get the trend line price at any bar index."""
        return self.slope * x + self.intercept


def conventional_trend_lines(
    df: pd.DataFrame, n: int = 10
) -> list[TrendLine]:
    """
    Conventional trend lines: connect successive extreme RLs (uptrend)
    or successive extreme RHs (downtrend).

    Schwager Ch.3: "An uptrend line connects a series of higher lows;
    a downtrend line connects a series of lower highs."

    Algorithm:
    - Detect RH/RL with parameter n
    - For uptrend lines: find sequences of RLs where each RL is higher
      than the previous → connect consecutive pairs
    - For downtrend lines: find sequences of RHs where each RH is lower
      than the previous → connect consecutive pairs

    Parameters
    ----------
    df : DataFrame with 'high', 'low' columns (and DatetimeIndex ideally)
    n  : swing point detection window

    Returns
    -------
    List of TrendLine objects
    """
    data = detect_swing_points(df, n)
    lines = []

    # --- Uptrend lines (connect successive higher lows) ---
    rl_indices = data.index[data["is_rl"]].tolist()
    rl_positions = [data.index.get_loc(idx) for idx in rl_indices]
    rl_prices = [data.loc[idx, "low"] for idx in rl_indices]

    for i in range(len(rl_prices) - 1):
        if rl_prices[i + 1] > rl_prices[i]:  # higher low
            lines.append(TrendLine(
                x1=rl_positions[i], x2=rl_positions[i + 1],
                y1=rl_prices[i], y2=rl_prices[i + 1],
                direction="up",
            ))

    # --- Downtrend lines (connect successive lower highs) ---
    rh_indices = data.index[data["is_rh"]].tolist()
    rh_positions = [data.index.get_loc(idx) for idx in rh_indices]
    rh_prices = [data.loc[idx, "high"] for idx in rh_indices]

    for i in range(len(rh_prices) - 1):
        if rh_prices[i + 1] < rh_prices[i]:  # lower high
            lines.append(TrendLine(
                x1=rh_positions[i], x2=rh_positions[i + 1],
                y1=rh_prices[i], y2=rh_prices[i + 1],
                direction="down",
            ))

    return lines


# =============================================================================
# METHOD 2: Internal Trend Lines (Schwager Ch.3, pp.42-45)
# =============================================================================

def internal_trend_line(
    df: pd.DataFrame,
    n: int = 10,
    direction: str = "up",
) -> Optional[TrendLine]:
    """
    Internal trend line: best-fit line through the majority of swing points,
    ignoring extreme outliers.

    Schwager Ch.3: "An internal trend line is drawn to best approximate the
    majority of relative highs or relative lows without any special
    consideration being given to extreme points."

    Implementation: Uses a RANSAC-like approach to make Schwager's subjective
    concept algorithmic:
    1. Detect all RLs (for uptrend) or RHs (for downtrend)
    2. Fit a line using least-squares through all points
    3. Remove the point with the largest residual (the "extreme")
    4. Repeat until a target inlier fraction is reached
    This approximates what a human does when they eyeball a "best fit"
    ignoring the spikes.

    Parameters
    ----------
    df        : DataFrame with 'high', 'low' columns
    n         : swing point detection window
    direction : 'up' (fit through RLs) or 'down' (fit through RHs)

    Returns
    -------
    TrendLine or None if insufficient points
    """
    data = detect_swing_points(df, n)

    if direction == "up":
        mask = data["is_rl"]
        prices = data.loc[mask, "low"].values
    else:
        mask = data["is_rh"]
        prices = data.loc[mask, "high"].values

    positions = np.array([data.index.get_loc(idx) for idx in data.index[mask]])

    if len(positions) < 3:
        return None

    # Iteratively remove worst outlier until 70% of points remain
    x = positions.copy().astype(float)
    y = prices.copy()
    target_count = max(3, int(len(x) * 0.7))

    while len(x) > target_count:
        # Fit line
        coeffs = np.polyfit(x, y, 1)
        fitted = np.polyval(coeffs, x)
        residuals = np.abs(y - fitted)

        # Remove worst outlier
        worst = np.argmax(residuals)
        x = np.delete(x, worst)
        y = np.delete(y, worst)

    # Final fit on remaining inliers
    coeffs = np.polyfit(x, y, 1)
    slope, intercept = coeffs

    x1_pos = int(x[0])
    x2_pos = int(x[-1])

    return TrendLine(
        x1=x1_pos, x2=x2_pos,
        y1=slope * x1_pos + intercept,
        y2=slope * x2_pos + intercept,
        direction=direction,
    )


# =============================================================================
# METHOD 3: TD Lines — Thomas DeMark (Schwager Ch.3, pp.41-42)
# =============================================================================

def td_trend_lines(
    df: pd.DataFrame, n: int = 8
) -> list[TrendLine]:
    """
    TD Lines (Thomas DeMark): Connect the two most recent qualifying
    relative lows (uptrend) or relative highs (downtrend).

    Schwager Ch.3: "The process consists of connecting exactly two points:
    for uptrend lines, the most recent relative low and the most recent
    preceding lower relative low; for downtrend lines, the most recent
    relative high and the most recent preceding higher relative high."

    Key property: Lines auto-redraw as new swing points form, always
    emphasizing the most recent price action.

    Parameters
    ----------
    df : DataFrame with 'high', 'low' columns
    n  : swing point detection window (DeMark's N parameter)

    Returns
    -------
    List of TrendLine objects (at most one uptrend + one downtrend)
    """
    data = detect_swing_points(df, n)
    lines = []

    # --- TD Uptrend Line ---
    # Most recent RL and the most recent preceding LOWER RL
    rl_indices = data.index[data["is_rl"]].tolist()
    rl_positions = [data.index.get_loc(idx) for idx in rl_indices]
    rl_prices = [data.loc[idx, "low"] for idx in rl_indices]

    if len(rl_prices) >= 2:
        most_recent_rl = len(rl_prices) - 1
        # Walk backward to find a preceding lower RL
        for j in range(most_recent_rl - 1, -1, -1):
            if rl_prices[j] < rl_prices[most_recent_rl]:
                lines.append(TrendLine(
                    x1=rl_positions[j], x2=rl_positions[most_recent_rl],
                    y1=rl_prices[j], y2=rl_prices[most_recent_rl],
                    direction="up",
                ))
                break

    # --- TD Downtrend Line ---
    # Most recent RH and the most recent preceding HIGHER RH
    rh_indices = data.index[data["is_rh"]].tolist()
    rh_positions = [data.index.get_loc(idx) for idx in rh_indices]
    rh_prices = [data.loc[idx, "high"] for idx in rh_indices]

    if len(rh_prices) >= 2:
        most_recent_rh = len(rh_prices) - 1
        for j in range(most_recent_rh - 1, -1, -1):
            if rh_prices[j] > rh_prices[most_recent_rh]:
                lines.append(TrendLine(
                    x1=rh_positions[j], x2=rh_positions[most_recent_rh],
                    y1=rh_prices[j], y2=rh_prices[most_recent_rh],
                    direction="down",
                ))
                break

    return lines


# =============================================================================
# METHOD 4: Linear Regression Line
# =============================================================================

def linear_regression_line(
    df: pd.DataFrame, period: int = 50
) -> pd.DataFrame:
    """
    Linear Regression Line: Least-squares best-fit line through the past
    N closing prices, updated every bar.

    This is the algorithmic equivalent of Schwager's "internal trend line"
    — it finds the line that minimizes total squared distance from all
    prices, naturally downweighting outliers relative to the majority.

    The slope tells you both trend direction and speed quantitatively.

    Parameters
    ----------
    df     : DataFrame with 'close' column
    period : lookback window (common values: 20, 50, 100)

    Returns
    -------
    DataFrame with added columns:
        'lr_line'  : the regression endpoint value at each bar
        'lr_slope' : the slope of the regression at each bar (price/bar)
        'lr_r2'    : R-squared (goodness of fit; higher = cleaner trend)
    """
    close = df["close"].values
    n = len(close)

    lr_line = np.full(n, np.nan)
    lr_slope = np.full(n, np.nan)
    lr_r2 = np.full(n, np.nan)

    for i in range(period - 1, n):
        y = close[i - period + 1 : i + 1]
        x = np.arange(period, dtype=float)

        # Least squares: y = mx + b
        x_mean = x.mean()
        y_mean = y.mean()
        ss_xy = np.sum((x - x_mean) * (y - y_mean))
        ss_xx = np.sum((x - x_mean) ** 2)
        ss_yy = np.sum((y - y_mean) ** 2)

        slope = ss_xy / ss_xx if ss_xx != 0 else 0
        intercept = y_mean - slope * x_mean

        # Endpoint value (the regression value at the current bar)
        lr_line[i] = slope * (period - 1) + intercept
        lr_slope[i] = slope

        # R-squared
        if ss_yy != 0:
            lr_r2[i] = (ss_xy ** 2) / (ss_xx * ss_yy)
        else:
            lr_r2[i] = 1.0

    result = df.copy()
    result["lr_line"] = lr_line
    result["lr_slope"] = lr_slope
    result["lr_r2"] = lr_r2
    return result


# =============================================================================
# METHOD 5: Moving Average (Schwager Ch.3, pp.45-50)
# =============================================================================

def moving_average_trend(
    df: pd.DataFrame,
    period: int = 40,
    threshold: float = 0.0,
) -> pd.DataFrame:
    """
    Moving Average as trend definition.

    Schwager Ch.3: "One very simple method of using moving averages to define
    trends is based on the direction of change in a moving average's value
    relative to the previous day."

    Schwager also notes: "The basic definition of a rising moving average is
    equivalent to the simple condition that today's close is higher than the
    close N days ago." (p.48)

    Signal logic (from Schwager's Figure 3.20):
    - Buy when MA turns up by at least `threshold` from its recent low
    - Sell when MA turns down by at least `threshold` from its recent high

    Parameters
    ----------
    df        : DataFrame with 'close' column
    period    : MA lookback window (Schwager uses 40-day in examples)
    threshold : minimum MA reversal to generate signal (0 = any turn)

    Returns
    -------
    DataFrame with added columns:
        'ma'        : the moving average value
        'ma_signal' : +1 (buy/uptrend), -1 (sell/downtrend), 0 (neutral)
    """
    result = df.copy()
    close = result["close"].values
    n = len(close)

    # Simple Moving Average
    ma = np.full(n, np.nan)
    for i in range(period - 1, n):
        ma[i] = np.mean(close[i - period + 1 : i + 1])

    result["ma"] = ma

    # Signal generation based on MA direction with threshold
    signal = np.zeros(n, dtype=int)
    ma_high = np.nan  # running high of the MA
    ma_low = np.nan   # running low of the MA
    current_signal = 0

    for i in range(period, n):
        if np.isnan(ma[i]):
            continue

        # Track MA extremes
        if np.isnan(ma_high) or ma[i] > ma_high:
            ma_high = ma[i]
        if np.isnan(ma_low) or ma[i] < ma_low:
            ma_low = ma[i]

        # Buy signal: MA rises by threshold from its low
        if current_signal <= 0 and ma[i] - ma_low >= threshold:
            current_signal = 1
            ma_high = ma[i]  # reset high tracker

        # Sell signal: MA falls by threshold from its high
        elif current_signal >= 0 and ma_high - ma[i] >= threshold:
            current_signal = -1
            ma_low = ma[i]  # reset low tracker

        signal[i] = current_signal

    result["ma_signal"] = signal
    return result


# =============================================================================
# METHOD 6: Regression Channel (with Bollinger Band variant)
# =============================================================================

def regression_channel(
    df: pd.DataFrame,
    period: int = 50,
    num_std: float = 2.0,
) -> pd.DataFrame:
    """
    Regression Channel: Linear regression line ± N standard deviations.

    The center line is the linear regression endpoint (Method 4).
    Upper/lower bands are placed at ± num_std standard deviations of
    the residuals (price - regression value) over the lookback period.

    Schwager discusses the price envelope variant in Ch.4 (pp.69-72):
    "The upper boundary is the moving average plus a given percent...
    the lower boundary is the moving average minus a given percent."
    Bollinger Bands are the standard-deviation version of this concept.

    Parameters
    ----------
    df      : DataFrame with 'close' column
    period  : lookback window
    num_std : number of standard deviations for channel width

    Returns
    -------
    DataFrame with added columns:
        'rc_center' : regression line center
        'rc_upper'  : upper channel boundary
        'rc_lower'  : lower channel boundary
        'rc_width'  : channel width (upper - lower), measures volatility
    """
    close = df["close"].values
    n = len(close)

    center = np.full(n, np.nan)
    upper = np.full(n, np.nan)
    lower = np.full(n, np.nan)

    for i in range(period - 1, n):
        y = close[i - period + 1 : i + 1]
        x = np.arange(period, dtype=float)

        # Fit regression
        coeffs = np.polyfit(x, y, 1)
        fitted = np.polyval(coeffs, x)

        # Standard deviation of residuals
        residuals = y - fitted
        std = np.std(residuals, ddof=1)

        # Channel values at the current bar (endpoint)
        endpoint = fitted[-1]
        center[i] = endpoint
        upper[i] = endpoint + num_std * std
        lower[i] = endpoint - num_std * std

    result = df.copy()
    result["rc_center"] = center
    result["rc_upper"] = upper
    result["rc_lower"] = lower
    result["rc_width"] = upper - lower
    return result


# =============================================================================
# VISUALIZATION: Plot all 6 methods on the same price data
# =============================================================================

def plot_all_methods(
    df: pd.DataFrame,
    swing_n: int = 10,
    td_n: int = 8,
    lr_period: int = 50,
    ma_period: int = 40,
    rc_period: int = 50,
    rc_std: float = 2.0,
    ma_threshold: float = 0.0,
):
    """
    Master visualization: 6 subplots, one per method, all on the same
    price data for direct comparison.

    Parameters
    ----------
    df           : DataFrame with 'open', 'high', 'low', 'close' columns
    swing_n      : N for swing point detection (methods 1, 2, 3)
    td_n         : N for TD Lines specifically
    lr_period    : lookback for linear regression (method 4)
    ma_period    : lookback for moving average (method 5)
    rc_period    : lookback for regression channel (method 6)
    rc_std       : std dev multiplier for regression channel
    ma_threshold : minimum MA reversal for signal generation
    """
    fig, axes = plt.subplots(3, 2, figsize=(16, 18), dpi=100)
    fig.suptitle(
        "Six Trend Line Methods Compared\n"
        "(Schwager Ch.3 + External Methods)",
        fontsize=16, fontweight="bold", y=0.98,
    )

    # Use integer positions for x-axis, map to dates for labels
    x = np.arange(len(df))
    close = df["close"].values
    high = df["high"].values
    low = df["low"].values

    def _plot_price(ax, title, subtitle=""):
        """Helper: draw candlesticks on an axis."""
        ax.set_title(f"{title}\n{subtitle}", fontsize=11, loc="left")
        colors = ["#2ca02c" if c >= o else "#d62728"
                  for o, c in zip(df["open"], df["close"])]
        ax.bar(x, df["close"] - df["open"], bottom=df["open"],
               width=0.6, color=colors, alpha=0.7)
        ax.vlines(x, df["low"], df["high"], colors="gray",
                  linewidth=0.4, alpha=0.5)
        ax.set_xlim(-2, len(df) + 2)

        # Date labels on x-axis
        tick_step = max(1, len(df) // 6)
        tick_positions = list(range(0, len(df), tick_step))
        tick_labels = [df.index[i].strftime("%b %Y") if hasattr(df.index[i], "strftime")
                       else str(df.index[i]) for i in tick_positions]
        ax.set_xticks(tick_positions)
        ax.set_xticklabels(tick_labels, fontsize=8, rotation=30)
        ax.grid(True, alpha=0.2)

    # ─── 1. Conventional Trend Lines ───
    ax1 = axes[0, 0]
    _plot_price(ax1, "1. Conventional Trend Lines",
                f"Connect extreme RH/RL (N={swing_n})")
    conv_lines = conventional_trend_lines(df, n=swing_n)
    data_sw = detect_swing_points(df, swing_n)
    rh_mask = data_sw["is_rh"]
    rl_mask = data_sw["is_rl"]
    rh_pos = np.where(rh_mask)[0]
    rl_pos = np.where(rl_mask)[0]
    ax1.scatter(rh_pos, high[rh_pos], marker="v", c="#ff7f0e", s=30,
                zorder=5, label="RH")
    ax1.scatter(rl_pos, low[rl_pos], marker="^", c="#1f77b4", s=30,
                zorder=5, label="RL")
    for tl in conv_lines:
        color = "#1f77b4" if tl.direction == "up" else "#d62728"
        # Extend line a bit beyond anchor points
        ext = min(20, len(df) - tl.x2 - 1)
        xs = [tl.x1, tl.x2 + ext]
        ys = [tl.y1, tl.value_at(tl.x2 + ext)]
        ax1.plot(xs, ys, color=color, linewidth=1.2, alpha=0.7,
                 linestyle="--")
    ax1.legend(fontsize=8, loc="best")

    # ─── 2. Internal Trend Lines ───
    ax2 = axes[0, 1]
    _plot_price(ax2, "2. Internal Trend Lines",
                f"Best-fit ignoring extremes (N={swing_n})")
    for direction, color in [("up", "#1f77b4"), ("down", "#d62728")]:
        itl = internal_trend_line(df, n=swing_n, direction=direction)
        if itl:
            ext = min(20, len(df) - itl.x2 - 1)
            xs = [itl.x1, itl.x2 + ext]
            ys = [itl.y1, itl.value_at(itl.x2 + ext)]
            ax2.plot(xs, ys, color=color, linewidth=2, alpha=0.8,
                     label=f"Internal ({direction})")
    # Also show conventional for comparison (faded)
    for tl in conv_lines:
        color = "#1f77b4" if tl.direction == "up" else "#d62728"
        ext = min(20, len(df) - tl.x2 - 1)
        xs = [tl.x1, tl.x2 + ext]
        ys = [tl.y1, tl.value_at(tl.x2 + ext)]
        ax2.plot(xs, ys, color=color, linewidth=0.5, alpha=0.25,
                 linestyle=":")
    ax2.legend(fontsize=8, loc="best")

    # ─── 3. TD Lines ───
    ax3 = axes[1, 0]
    _plot_price(ax3, "3. TD Lines (DeMark)",
                f"Most recent 2 RLs / RHs (N={td_n})")
    td_lines = td_trend_lines(df, n=td_n)
    data_td = detect_swing_points(df, td_n)
    rh_td = np.where(data_td["is_rh"])[0]
    rl_td = np.where(data_td["is_rl"])[0]
    ax3.scatter(rh_td, high[rh_td], marker="v", c="#ff7f0e", s=25,
                zorder=5, alpha=0.5)
    ax3.scatter(rl_td, low[rl_td], marker="^", c="#1f77b4", s=25,
                zorder=5, alpha=0.5)
    for tl in td_lines:
        color = "#1f77b4" if tl.direction == "up" else "#d62728"
        # TD lines extend forward from anchor 2
        ext = min(30, len(df) - tl.x2 - 1)
        xs = [tl.x1, tl.x2 + ext]
        ys = [tl.y1, tl.value_at(tl.x2 + ext)]
        ax3.plot(xs, ys, color=color, linewidth=1.8, alpha=0.9,
                 label=f"TD {tl.direction}")
        # Mark anchor points
        ax3.scatter([tl.x1, tl.x2],
                    [tl.y1, tl.y2],
                    c=color, s=60, zorder=6, edgecolors="black",
                    linewidths=0.5)
    ax3.legend(fontsize=8, loc="best")

    # ─── 4. Linear Regression Line ───
    ax4 = axes[1, 1]
    _plot_price(ax4, "4. Linear Regression Line",
                f"Least-squares best fit (period={lr_period})")
    lr_data = linear_regression_line(df, period=lr_period)
    ax4.plot(x, lr_data["lr_line"], color="#9467bd", linewidth=1.8,
             label=f"LR({lr_period})")
    # Color background by R² quality
    r2 = lr_data["lr_r2"].values
    for i in range(lr_period, len(df)):
        if not np.isnan(r2[i]):
            alpha = max(0.02, min(0.15, r2[i] * 0.2))
            color = "#2ca02c" if lr_data["lr_slope"].values[i] > 0 else "#d62728"
            ax4.axvspan(i - 0.5, i + 0.5, color=color, alpha=alpha)
    ax4.legend(fontsize=8, loc="best")

    # ─── 5. Moving Average ───
    ax5 = axes[2, 0]
    _plot_price(ax5, "5. Moving Average",
                f"SMA({ma_period}), threshold={ma_threshold}")
    ma_data = moving_average_trend(df, period=ma_period,
                                    threshold=ma_threshold)
    ax5.plot(x, ma_data["ma"], color="#e377c2", linewidth=1.8,
             label=f"SMA({ma_period})")
    # Mark buy/sell signals
    sig = ma_data["ma_signal"].values
    buy_signals = np.where((sig[1:] == 1) & (sig[:-1] != 1))[0] + 1
    sell_signals = np.where((sig[1:] == -1) & (sig[:-1] != -1))[0] + 1
    ax5.scatter(buy_signals, low[buy_signals] * 0.99, marker="^",
                c="#2ca02c", s=60, zorder=5, label="Buy")
    ax5.scatter(sell_signals, high[sell_signals] * 1.01, marker="v",
                c="#d62728", s=60, zorder=5, label="Sell")
    ax5.legend(fontsize=8, loc="best")

    # ─── 6. Regression Channel ───
    ax6 = axes[2, 1]
    _plot_price(ax6, "6. Regression Channel",
                f"LR({rc_period}) ± {rc_std} std devs")
    rc_data = regression_channel(df, period=rc_period, num_std=rc_std)
    ax6.plot(x, rc_data["rc_center"], color="#9467bd", linewidth=1.5,
             label="Center")
    ax6.plot(x, rc_data["rc_upper"], color="#ff7f0e", linewidth=1,
             linestyle="--", alpha=0.7, label="Upper")
    ax6.plot(x, rc_data["rc_lower"], color="#1f77b4", linewidth=1,
             linestyle="--", alpha=0.7, label="Lower")
    ax6.fill_between(x, rc_data["rc_lower"], rc_data["rc_upper"],
                     color="#9467bd", alpha=0.08)
    ax6.legend(fontsize=8, loc="best")

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    return fig


# =============================================================================
# DEMO: Generate sample data and run all methods
# =============================================================================

def generate_sample_data(n_bars: int = 300, seed: int = 42) -> pd.DataFrame:
    """
    Generate realistic synthetic OHLC data with trend + mean-reversion
    regimes for demonstration purposes.
    """
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2023-01-01", periods=n_bars)

    price = 100.0
    prices = []

    for i in range(n_bars):
        # Regime: uptrend → sideways → downtrend → recovery
        if i < 80:
            drift = 0.15
        elif i < 140:
            drift = 0.0
        elif i < 220:
            drift = -0.12
        else:
            drift = 0.10

        ret = drift + rng.normal(0, 1.2)
        price = max(price + ret, 20)

        range_size = 0.8 + rng.exponential(1.0)
        open_price = price + rng.normal(0, 0.3)
        high_price = max(open_price, price) + rng.exponential(range_size / 2)
        low_price = min(open_price, price) - rng.exponential(range_size / 2)

        prices.append({
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "close": price,
        })

    df = pd.DataFrame(prices, index=dates)
    return df


if __name__ == "__main__":
    # ── Option A: Synthetic data (works without any dependencies) ──
    print("Generating synthetic OHLC data...")
    df = generate_sample_data(300, seed=42)

    # ── Option B: Real data with yfinance (uncomment to use) ──
    # import yfinance as yf
    # df = yf.download("AAPL", start="2024-01-01", end="2025-03-01")
    # df.columns = [c.lower() for c in df.columns]

    # ── Run all methods ──
    print(f"Data: {len(df)} bars, {df.index[0]} to {df.index[-1]}")
    print()

    # Method 1: Conventional
    conv = conventional_trend_lines(df, n=10)
    print(f"Method 1 — Conventional: {len(conv)} trend lines "
          f"({sum(1 for t in conv if t.direction == 'up')} up, "
          f"{sum(1 for t in conv if t.direction == 'down')} down)")

    # Method 2: Internal
    itl_up = internal_trend_line(df, n=10, direction="up")
    itl_dn = internal_trend_line(df, n=10, direction="down")
    print(f"Method 2 — Internal: up slope={itl_up.slope:.4f}, "
          f"down slope={itl_dn.slope:.4f}" if itl_up and itl_dn else
          "Method 2 — Internal: insufficient data")

    # Method 3: TD Lines
    td = td_trend_lines(df, n=8)
    print(f"Method 3 — TD Lines: {len(td)} lines "
          f"({', '.join(t.direction for t in td)})")

    # Method 4: Linear Regression
    lr = linear_regression_line(df, period=50)
    last_valid = lr["lr_slope"].dropna().iloc[-1]
    last_r2 = lr["lr_r2"].dropna().iloc[-1]
    print(f"Method 4 — Linear Regression: current slope={last_valid:.4f}, "
          f"R²={last_r2:.3f}")

    # Method 5: Moving Average
    ma = moving_average_trend(df, period=40, threshold=0.5)
    last_sig = ma["ma_signal"].iloc[-1]
    sig_text = {1: "UPTREND", -1: "DOWNTREND", 0: "NEUTRAL"}
    print(f"Method 5 — Moving Average: current signal={sig_text[last_sig]}")

    # Method 6: Regression Channel
    rc = regression_channel(df, period=50, num_std=2.0)
    last_center = rc["rc_center"].dropna().iloc[-1]
    last_width = rc["rc_width"].dropna().iloc[-1]
    print(f"Method 6 — Regression Channel: center={last_center:.2f}, "
          f"width={last_width:.2f}")

    # ── Plot everything ──
    print("\nGenerating comparison chart...")
    fig = plot_all_methods(
        df,
        swing_n=10,
        td_n=8,
        lr_period=50,
        ma_period=40,
        rc_period=50,
        rc_std=2.0,
        ma_threshold=0.5,
    )
    fig.savefig("trend_lines_comparison.png", dpi=150, bbox_inches="tight")
    print("Saved: trend_lines_comparison.png")
    plt.show()
