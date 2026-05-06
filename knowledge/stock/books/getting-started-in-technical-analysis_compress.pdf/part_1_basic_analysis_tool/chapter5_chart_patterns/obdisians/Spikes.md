# Spikes

> Part of: [[Chapter_05_Chart_Patterns]] → One-Day Patterns

## Definition

A **spike high** is a daily bar whose high sticks out sharply above the highs of both the day before and the day after. The close is typically near the *low* of the bar's range, and a meaningful preceding price advance is required.

A **spike low** is the mirror image: a low far below neighboring lows, close near the *top* of the day's range, after a meaningful decline.

The qualifying conditions are subjective — there's no single threshold for "sharply above" — but three factors strengthen the signal:

1. The bigger the gap between the spike's extreme and its neighbors' extremes, the stronger.
2. The closer the close is to the opposite end of the bar, the stronger.
3. The longer the prior trend, the stronger.

A spike marks a *climax* of buying (at a top) or selling (at a bottom). Sometimes it's only a relative high/low; sometimes it's a major turn.

## Illustration

![[spikes_illustration.svg]]

## Analogy — Auction Final Bid

Picture an estate auction. Bidding has been climbing steadily for ten minutes. Suddenly someone shouts a price *way* above the previous bid — but no one else raises their paddle. The auctioneer says "going once, twice…" and the price drops back as the bidder reconsiders or someone secures it at a discount.

That outlier shout is a **spike high**. It's not just a high price — it's a high price that *nobody else was willing to validate*. The market reached up, found nothing, and pulled back. The further the shout, and the longer the silence after it, the more clearly it marks the top of what people will pay.

## Numeric Example

| Day | High | Low | Close |
|---|---|---|---|
| T−2 | 50.20 | 49.80 | 50.10 |
| T−1 | 50.50 | 50.00 | 50.40 |
| **T (spike high)** | **53.10** | 50.30 | **50.45** |
| T+1 | 50.80 | 50.20 | 50.55 |
| T+2 | 50.70 | 50.10 | 50.30 |

Checks:
- Spike high (53.10) exceeds neighbors (50.50, 50.80) by 2.60 and 2.30 — **wide difference** ✓
- Close (50.45) is at 5.4% of the day's range from the low → **near the low** ✓
- Assume a 6-week prior advance from 45 → 53 → **substantive prior move** ✓

All three conditions met → high-conviction relative high, possibly a major top.

## Python Code

```python
import pandas as pd

def detect_spike_highs(df: pd.DataFrame,
                      min_excess: float = 0.02,
                      max_close_pct: float = 0.30,
                      min_prior_run: int = 10) -> pd.Series:
    """
    Returns a boolean Series where True marks a spike-high day.

    min_excess     : how much higher the spike must be vs neighbors (fraction)
    max_close_pct  : the close must sit within the lower max_close_pct of the day's range
    min_prior_run  : require an advance of >= this many bars before
    """
    h, l, c = df["high"], df["low"], df["close"]
    prev_h, next_h = h.shift(1), h.shift(-1)

    cond_higher = (h > prev_h * (1 + min_excess)) & (h > next_h * (1 + min_excess))
    rng = (h - l).replace(0, 1e-9)
    cond_close_low = (c - l) / rng <= max_close_pct

    rolling_low = l.rolling(min_prior_run).min().shift(1)
    cond_prior  = h > rolling_low * 1.05    # at least 5% above the prior low window

    return cond_higher & cond_close_low & cond_prior


def detect_spike_lows(df: pd.DataFrame,
                     min_excess: float = 0.02,
                     max_close_pct: float = 0.30,
                     min_prior_run: int = 10) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    prev_l, next_l = l.shift(1), l.shift(-1)

    cond_lower = (l < prev_l * (1 - min_excess)) & (l < next_l * (1 - min_excess))
    rng = (h - l).replace(0, 1e-9)
    cond_close_high = (h - c) / rng <= max_close_pct

    rolling_high = h.rolling(min_prior_run).max().shift(1)
    cond_prior   = l < rolling_high * 0.95

    return cond_lower & cond_close_high & cond_prior
```

> Note: spike detection has a one-bar look-ahead because we need the *next* day's high/low. Spikes can therefore only be confirmed on T+1.

## Relationships

### Within Chapter 5

- **Versus [[Reversal Days]]**: A spike high need not close below the prior day's close (which a reversal day requires). A reversal day need not extend far above the prior day's high (which a spike requires). When both conditions are met → highest-significance signal.
- **Combines with [[Wide-Ranging Days]]**: a spike that is also a wide-ranging day is far stronger than either alone.
- **Inside [[V Tops and Bottoms]]**: the most reliable V-shaped reversals contain a spike at the apex.
- **Inside [[Island Reversals]]**: the "island" is often spike-shaped.

### Outside Chapter 5

- **[[Chapter 11 - The Most Important Rule]]** — return to the spike's extreme some weeks/months later transforms the spike into a *failed signal*: a major continuation indicator in the opposite direction.
- **[[Chapter 06 - Oscillators]]** — spikes that coincide with overbought/oversold extremes on RSI or stochastics gain extra weight.
- **[[Chapter 09 - Choosing Stop-Loss Points]]** — placing a stop just beyond the spike's extreme uses the spike as a tested level.

### When does this concept work well?

- **Best**: late in an extended, accelerated trend, especially with a news catalyst that morning.
- **Worst**: choppy markets without a prior trend — these "spikes" are just normal volatility.

#chart-patterns #one-day-pattern #spikes
