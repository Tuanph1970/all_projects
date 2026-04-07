"""
trend_channels.py — Trend Channel Construction
================================================

Builds on trend_lines.py (swing point detection + trend line methods).

A trend channel = base trend line + parallel channel line on the opposite side.
The base line defines the slope. The channel line shares that slope but is
shifted vertically to pass through an anchor point on the opposite side.

Three anchor strategies for the channel line:
    A. Farthest Extreme  — widest channel, contains all price action
    B. Best-Fit Touches  — shifted to best approximate opposite swing points
    C. Specific Swing    — anchored through the most prominent opposite swing

Requirements:
    pip install pandas numpy matplotlib

Usage:
    python trend_channels.py
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import Optional


# =============================================================================
# SHARED: Swing Point Detection (same as trend_lines.py)
# =============================================================================

def detect_swing_points(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """
    Schwager's definition (Glossary p.329):
        RH at bar i: high[i] > high[j] for all j in [i-n, i+n], j != i
        RL at bar i: low[i]  < low[j]  for all j in [i-n, i+n], j != i
    """
    highs = df["high"].values
    lows = df["low"].values
    length = len(df)

    is_rh = np.zeros(length, dtype=bool)
    is_rl = np.zeros(length, dtype=bool)

    for i in range(n, length - n):
        w_h = highs[i - n : i + n + 1]
        w_l = lows[i - n : i + n + 1]

        if highs[i] == np.max(w_h) and np.sum(w_h == highs[i]) == 1:
            is_rh[i] = True
        if lows[i] == np.min(w_l) and np.sum(w_l == lows[i]) == 1:
            is_rl[i] = True

    result = df.copy()
    result["is_rh"] = is_rh
    result["is_rl"] = is_rl
    return result


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class TrendLine:
    """A line defined by slope + intercept, with anchor metadata."""
    slope: float
    intercept: float
    x1: int          # first anchor bar index
    x2: int          # second anchor bar index
    direction: str   # 'up' or 'down'

    def value_at(self, x: int) -> float:
        return self.slope * x + self.intercept

    @property
    def y1(self) -> float:
        return self.value_at(self.x1)

    @property
    def y2(self) -> float:
        return self.value_at(self.x2)


@dataclass
class TrendChannel:
    """A trend channel = base line + channel line (parallel)."""
    base_line: TrendLine        # primary trend line (support for up, resistance for down)
    channel_line: TrendLine     # parallel line on opposite side
    anchor_method: str          # 'farthest_extreme', 'best_fit', 'specific_swing'
    anchor_bar: Optional[int]   # bar index of the channel line anchor point
    anchor_price: Optional[float]

    @property
    def width(self) -> float:
        """Vertical distance between the two lines (constant everywhere)."""
        return abs(self.channel_line.intercept - self.base_line.intercept)

    @property
    def slope(self) -> float:
        return self.base_line.slope

    def base_at(self, x: int) -> float:
        return self.base_line.value_at(x)

    def channel_at(self, x: int) -> float:
        return self.channel_line.value_at(x)

    def midline_at(self, x: int) -> float:
        return (self.base_at(x) + self.channel_at(x)) / 2

    def position_in_channel(self, x: int, price: float) -> float:
        """
        Where is `price` within the channel? Returns 0.0 at the base line,
        1.0 at the channel line. Values outside [0, 1] mean price has
        broken out of the channel.
        """
        b = self.base_at(x)
        c = self.channel_at(x)
        if c == b:
            return 0.0
        return (price - b) / (c - b)


# =============================================================================
# STEP 1: Build the base trend line from swing points
# =============================================================================

def build_base_line(
    df: pd.DataFrame,
    n: int = 10,
    direction: str = "up",
) -> Optional[tuple[TrendLine, pd.DataFrame]]:
    """
    Build the primary (base) trend line by connecting two anchor swing points.

    For an uptrend:  connect two successive RLs (higher lows) → support line
    For a downtrend: connect two successive RHs (lower highs) → resistance line

    Returns the best (longest-spanning) qualifying pair.

    Parameters
    ----------
    df        : DataFrame with 'high', 'low' columns
    n         : swing point window
    direction : 'up' or 'down'

    Returns
    -------
    (TrendLine, DataFrame_with_swing_cols) or None
    """
    data = detect_swing_points(df, n)

    if direction == "up":
        mask = data["is_rl"]
        prices = data.loc[mask, "low"].values
    else:
        mask = data["is_rh"]
        prices = data.loc[mask, "high"].values

    indices = data.index[mask].tolist()
    positions = np.array([data.index.get_loc(idx) for idx in indices])

    if len(positions) < 2:
        return None

    # Find the best pair: longest span with correct slope direction
    best_line = None
    best_span = 0

    for i in range(len(positions)):
        for j in range(i + 1, len(positions)):
            x1, x2 = positions[i], positions[j]
            y1, y2 = prices[i], prices[j]

            # Uptrend base: must have positive slope (higher lows)
            # Downtrend base: must have negative slope (lower highs)
            slope = (y2 - y1) / (x2 - x1) if x2 != x1 else 0
            if direction == "up" and slope <= 0:
                continue
            if direction == "down" and slope >= 0:
                continue

            span = x2 - x1
            if span > best_span:
                best_span = span
                intercept = y1 - slope * x1
                best_line = TrendLine(
                    slope=slope, intercept=intercept,
                    x1=x1, x2=x2, direction=direction,
                )

    if best_line is None:
        return None

    return best_line, data


# =============================================================================
# STEP 2: Three strategies for the channel (parallel) line
# =============================================================================

def _make_channel_line(base: TrendLine, anchor_x: int, anchor_price: float) -> TrendLine:
    """
    Create a line parallel to `base` that passes through (anchor_x, anchor_price).

    MATH:
        base:    y = slope * x + intercept_base
        channel: y = slope * x + intercept_channel

        Since channel must pass through (anchor_x, anchor_price):
            anchor_price = slope * anchor_x + intercept_channel
            intercept_channel = anchor_price - slope * anchor_x

        Same slope → parallel. Different intercept → shifted vertically.
    """
    intercept_channel = anchor_price - base.slope * anchor_x
    return TrendLine(
        slope=base.slope,
        intercept=intercept_channel,
        x1=base.x1,
        x2=base.x2,
        direction=base.direction,
    )


# ── Strategy A: Farthest Extreme ──────────────────────────────────────────

def channel_farthest_extreme(
    df: pd.DataFrame,
    base: TrendLine,
) -> TrendChannel:
    """
    Strategy A: Anchor the channel line at the point between x1 and x2
    that is FARTHEST from the base line on the opposite side.

    For uptrend (base = support):  find the highest high → channel = resistance
    For downtrend (base = resistance): find the lowest low → channel = support

    This gives the widest channel that fully contains all price action
    between the two base anchors.

    Think of it as: "wrap the tightest parallel band around ALL the bars."
    """
    x1, x2 = base.x1, base.x2

    if base.direction == "up":
        # Opposite side = highs above the base line
        prices = df["high"].values[x1 : x2 + 1]
    else:
        # Opposite side = lows below the base line
        prices = df["low"].values[x1 : x2 + 1]

    # Find the bar with max distance from the base line
    max_dist = -np.inf
    anchor_x = x1
    anchor_price = prices[0]

    for i, bar_x in enumerate(range(x1, x2 + 1)):
        base_val = base.value_at(bar_x)
        price = prices[i]
        dist = price - base_val if base.direction == "up" else base_val - price

        if dist > max_dist:
            max_dist = dist
            anchor_x = bar_x
            anchor_price = price

    channel_line = _make_channel_line(base, anchor_x, anchor_price)

    return TrendChannel(
        base_line=base,
        channel_line=channel_line,
        anchor_method="farthest_extreme",
        anchor_bar=anchor_x,
        anchor_price=anchor_price,
    )


# ── Strategy B: Best-Fit Opposite Touches ─────────────────────────────────

def channel_best_fit(
    df: pd.DataFrame,
    base: TrendLine,
    data_with_swings: pd.DataFrame,
) -> TrendChannel:
    """
    Strategy B: Position the channel line to best approximate the opposite-side
    swing points, keeping the base line's slope.

    For uptrend: find all RHs between x1 and x2, compute the intercept that
                 minimizes the sum of squared distances from these RHs to the
                 channel line.
    For downtrend: same with RLs.

    This is more robust than Strategy A because it's not dominated by a
    single spike — it represents the "typical" channel width.

    MATH:
        channel: y = slope * x + c
        For each swing point (xi, yi): residual = yi - (slope * xi + c)
        Minimize sum(residual²) with respect to c:
            d/dc sum((yi - slope*xi - c)²) = 0
            sum(-2(yi - slope*xi - c)) = 0
            c = mean(yi - slope * xi)
    """
    x1, x2 = base.x1, base.x2

    if base.direction == "up":
        mask = data_with_swings["is_rh"]
        price_col = "high"
    else:
        mask = data_with_swings["is_rl"]
        price_col = "low"

    # Get opposite-side swing points within the base line span
    swing_positions = []
    swing_prices = []

    for idx in data_with_swings.index[mask]:
        pos = data_with_swings.index.get_loc(idx)
        if x1 <= pos <= x2:
            swing_positions.append(pos)
            swing_prices.append(data_with_swings.loc[idx, price_col])

    if len(swing_positions) == 0:
        # Fallback to farthest extreme if no swing points found
        return channel_farthest_extreme(df, base)

    swing_positions = np.array(swing_positions, dtype=float)
    swing_prices = np.array(swing_prices)

    # Optimal intercept: c = mean(yi - slope * xi)
    optimal_intercept = np.mean(swing_prices - base.slope * swing_positions)

    channel_line = TrendLine(
        slope=base.slope,
        intercept=optimal_intercept,
        x1=base.x1,
        x2=base.x2,
        direction=base.direction,
    )

    # The "anchor" is the mean position (conceptual, not a single bar)
    mean_x = int(np.mean(swing_positions))
    mean_price = base.slope * mean_x + optimal_intercept

    return TrendChannel(
        base_line=base,
        channel_line=channel_line,
        anchor_method="best_fit",
        anchor_bar=mean_x,
        anchor_price=mean_price,
    )


# ── Strategy C: Specific Swing Point ──────────────────────────────────────

def channel_specific_swing(
    df: pd.DataFrame,
    base: TrendLine,
    data_with_swings: pd.DataFrame,
) -> TrendChannel:
    """
    Strategy C: Anchor the channel line through the most prominent
    opposite-side swing point between x1 and x2.

    "Most prominent" = the RH with the highest high (uptrend) or
    the RL with the lowest low (downtrend).

    This is the textbook method — you pick ONE visible peak/trough
    and draw the parallel through it.
    """
    x1, x2 = base.x1, base.x2

    if base.direction == "up":
        mask = data_with_swings["is_rh"]
        price_col = "high"
    else:
        mask = data_with_swings["is_rl"]
        price_col = "low"

    # Find the most extreme opposite swing point in the span
    best_pos = None
    best_price = None

    for idx in data_with_swings.index[mask]:
        pos = data_with_swings.index.get_loc(idx)
        if x1 <= pos <= x2:
            price = data_with_swings.loc[idx, price_col]
            if best_price is None:
                best_pos = pos
                best_price = price
            elif base.direction == "up" and price > best_price:
                best_pos = pos
                best_price = price
            elif base.direction == "down" and price < best_price:
                best_pos = pos
                best_price = price

    if best_pos is None:
        # Fallback: use the farthest extreme of raw price data
        return channel_farthest_extreme(df, base)

    channel_line = _make_channel_line(base, best_pos, best_price)

    return TrendChannel(
        base_line=base,
        channel_line=channel_line,
        anchor_method="specific_swing",
        anchor_bar=best_pos,
        anchor_price=best_price,
    )


# =============================================================================
# CONVENIENCE: Build a complete channel in one call
# =============================================================================

def build_trend_channel(
    df: pd.DataFrame,
    n: int = 10,
    direction: str = "up",
    anchor_method: str = "farthest_extreme",
) -> Optional[TrendChannel]:
    """
    End-to-end: detect swings → build base line → build channel.

    Parameters
    ----------
    df             : DataFrame with OHLC columns
    n              : swing point detection window
    direction      : 'up' or 'down'
    anchor_method  : 'farthest_extreme', 'best_fit', or 'specific_swing'

    Returns
    -------
    TrendChannel or None if no valid channel can be constructed
    """
    result = build_base_line(df, n=n, direction=direction)
    if result is None:
        return None

    base, data = result

    if anchor_method == "farthest_extreme":
        return channel_farthest_extreme(df, base)
    elif anchor_method == "best_fit":
        return channel_best_fit(df, base, data)
    elif anchor_method == "specific_swing":
        return channel_specific_swing(df, base, data)
    else:
        raise ValueError(f"Unknown anchor_method: {anchor_method}")


# =============================================================================
# VISUALIZATION
# =============================================================================

def plot_channel(
    df: pd.DataFrame,
    channel: TrendChannel,
    ax: Optional[plt.Axes] = None,
    title: str = "",
    extend_bars: int = 20,
    show_midline: bool = True,
    show_position: bool = True,
):
    """Plot a trend channel on OHLC data with annotations."""
    if ax is None:
        fig, ax = plt.subplots(figsize=(14, 7))

    x = np.arange(len(df))
    close = df["close"].values
    high = df["high"].values
    low = df["low"].values

    # Candlesticks
    colors = ["#2ca02c" if c >= o else "#d62728"
              for o, c in zip(df["open"], df["close"])]
    ax.bar(x, close - df["open"], bottom=df["open"],
           width=0.6, color=colors, alpha=0.6)
    ax.vlines(x, low, high, colors="gray", linewidth=0.3, alpha=0.5)

    # Channel lines
    b = channel.base_line
    c = channel.channel_line
    x_start = b.x1
    x_end = min(b.x2 + extend_bars, len(df) - 1)
    xs = np.array([x_start, x_end])

    base_color = "#1f77b4" if b.direction == "up" else "#d62728"
    chan_color = "#ff7f0e"

    # Base line
    ax.plot(xs, [b.value_at(xi) for xi in xs],
            color=base_color, linewidth=2, label="Base line")
    # Channel line
    ax.plot(xs, [c.value_at(xi) for xi in xs],
            color=chan_color, linewidth=2, linestyle="--", label="Channel line")

    # Fill between
    base_ys = [b.value_at(xi) for xi in range(x_start, x_end + 1)]
    chan_ys = [c.value_at(xi) for xi in range(x_start, x_end + 1)]
    fill_xs = list(range(x_start, x_end + 1))
    ax.fill_between(fill_xs, base_ys, chan_ys, alpha=0.08, color=base_color)

    # Midline
    if show_midline:
        mid_ys = [(b.value_at(xi) + c.value_at(xi)) / 2
                  for xi in range(x_start, x_end + 1)]
        ax.plot(fill_xs, mid_ys, color="gray", linewidth=0.8,
                linestyle=":", alpha=0.6, label="Midline")

    # Mark base anchors
    ax.scatter([b.x1, b.x2], [b.y1, b.y2],
               color=base_color, s=80, zorder=5, edgecolors="black",
               linewidths=0.5, label="Base anchors")

    # Mark channel anchor
    if channel.anchor_bar is not None:
        ax.scatter([channel.anchor_bar], [channel.anchor_price],
                   color=chan_color, s=100, zorder=5, marker="D",
                   edgecolors="black", linewidths=0.5,
                   label=f"Channel anchor ({channel.anchor_method})")

    # Position indicator (where is current price in the channel?)
    if show_position:
        last_x = len(df) - 1
        if x_start <= last_x <= x_end:
            pos = channel.position_in_channel(last_x, close[-1])
            pos_text = f"Position: {pos:.0%}"
            if pos > 1.0:
                pos_text += " (ABOVE channel)"
            elif pos < 0.0:
                pos_text += " (BELOW channel)"
            ax.annotate(pos_text, xy=(last_x, close[-1]),
                        xytext=(15, 15), textcoords="offset points",
                        fontsize=9, color="purple",
                        arrowprops=dict(arrowstyle="->", color="purple",
                                        lw=0.8))

    # Formatting
    ax.set_title(title or f"Trend Channel ({channel.anchor_method})",
                 fontsize=12, fontweight="bold", loc="left")
    ax.legend(fontsize=8, loc="best")
    ax.grid(True, alpha=0.15)

    # Date labels
    tick_step = max(1, len(df) // 8)
    tick_pos = list(range(0, len(df), tick_step))
    tick_labels = [df.index[i].strftime("%b %Y")
                   if hasattr(df.index[i], "strftime") else str(df.index[i])
                   for i in tick_pos]
    ax.set_xticks(tick_pos)
    ax.set_xticklabels(tick_labels, fontsize=8, rotation=30)

    return ax


def plot_all_three_strategies(
    df: pd.DataFrame,
    n: int = 10,
    direction: str = "up",
):
    """
    Compare all three channel anchor strategies side by side on the same data.
    """
    fig, axes = plt.subplots(1, 3, figsize=(20, 7), sharey=True)
    fig.suptitle(
        f"Three Channel Anchor Strategies — {direction}trend (N={n})",
        fontsize=14, fontweight="bold",
    )

    methods = ["farthest_extreme", "best_fit", "specific_swing"]
    labels = [
        "A: Farthest Extreme\n(widest, contains all bars)",
        "B: Best-Fit Touches\n(robust, avg of opposite swings)",
        "C: Specific Swing\n(most prominent opposite peak)",
    ]

    for ax, method, label in zip(axes, methods, labels):
        ch = build_trend_channel(df, n=n, direction=direction,
                                 anchor_method=method)
        if ch:
            plot_channel(df, ch, ax=ax, title=label, show_position=False)
            ax.set_title(label, fontsize=10)
            # Annotate channel width
            mid_x = (ch.base_line.x1 + ch.base_line.x2) // 2
            ax.annotate(
                f"Width: {ch.width:.1f}",
                xy=(mid_x, ch.midline_at(mid_x)),
                fontsize=9, ha="center", color="gray",
                bbox=dict(boxstyle="round,pad=0.3", fc="white",
                          ec="gray", alpha=0.8),
            )
        else:
            ax.set_title(f"{label}\n(no valid channel found)", fontsize=10)

    plt.tight_layout()
    return fig


# =============================================================================
# DEMO
# =============================================================================

def generate_sample_data(n_bars: int = 200, seed: int = 42) -> pd.DataFrame:
    """Generate synthetic OHLC data with a clear uptrend period."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2023-01-01", periods=n_bars)

    price = 100.0
    prices = []

    for i in range(n_bars):
        # Clear uptrend for first 120 bars, then sideways
        if i < 120:
            drift = 0.18 + 0.05 * np.sin(i / 15)  # gentle oscillation
        else:
            drift = -0.05

        ret = drift + rng.normal(0, 1.0)
        price = max(price + ret, 50)

        r = 0.8 + rng.exponential(0.8)
        o = price + rng.normal(0, 0.3)
        h = max(o, price) + rng.exponential(r / 2)
        l = min(o, price) - rng.exponential(r / 2)

        prices.append({"open": o, "high": h, "low": l, "close": price})

    return pd.DataFrame(prices, index=dates)


if __name__ == "__main__":
    print("=" * 60)
    print("TREND CHANNEL CONSTRUCTION")
    print("=" * 60)

    # ── Generate data ──
    df = generate_sample_data(200, seed=42)
    print(f"Data: {len(df)} bars, {df.index[0].date()} → {df.index[-1].date()}\n")

    # ── Build channels with all three strategies ──
    for method in ["farthest_extreme", "best_fit", "specific_swing"]:
        ch = build_trend_channel(df, n=10, direction="up",
                                 anchor_method=method)
        if ch:
            print(f"Strategy: {method}")
            print(f"  Base line:    slope={ch.slope:.4f}, "
                  f"anchors at bars {ch.base_line.x1}→{ch.base_line.x2}")
            print(f"  Channel line: anchor bar={ch.anchor_bar}, "
                  f"anchor price={ch.anchor_price:.2f}")
            print(f"  Width:        {ch.width:.2f}")
            last_pos = ch.position_in_channel(len(df) - 1, df["close"].iloc[-1])
            print(f"  Current position in channel: {last_pos:.1%}")
            print()

    # ── Plot comparison ──
    print("Generating comparison chart...")
    fig = plot_all_three_strategies(df, n=10, direction="up")
    fig.savefig("trend_channels_comparison.png", dpi=150, bbox_inches="tight")
    print("Saved: trend_channels_comparison.png")

    # ── Also plot a single detailed channel ──
    ch = build_trend_channel(df, n=10, direction="up",
                             anchor_method="specific_swing")
    if ch:
        fig2, ax2 = plt.subplots(figsize=(14, 7))
        plot_channel(df, ch, ax=ax2,
                     title="Uptrend Channel — Specific Swing Anchor (N=10)")
        fig2.savefig("trend_channel_detail.png", dpi=150, bbox_inches="tight")
        print("Saved: trend_channel_detail.png")

    plt.show()
