---
chapter: 3
concept: Simple Moving Average
tags: [technical-analysis, trends, chapter-3, moving-average]
source: "Schwager, Getting Started in Technical Analysis, Ch. 3, pp. 45-50"
---

# Simple Moving Average

## Definition

A **simple moving average (SMA)** is the arithmetic mean of the past N daily closes, including the current day. As each new bar arrives, the oldest bar drops out of the window — the set of values being averaged "moves" through time. The SMA smooths a price series by averaging away short-term noise, making the underlying trend easier to see; the smoothing effect grows with N (a 40-day SMA is much smoother than a 5-day SMA). The cost of smoothing is **lag**: turns in the SMA always trail the corresponding turns in price.

A useful equivalence: the SMA is rising today if and only if today's close is greater than the close N days ago. (When the window slides one bar forward, only one value enters the sum and one leaves — the rest cancels.) This gives a one-line definition of "trend up" using SMAs.

A simple trading system based on SMA: buy when the SMA reverses upward by at least M ticks off its low, sell when it reverses downward by at least M ticks off its high. The threshold M prevents whipsaw flip-flops when the SMA is nearly flat. The system performs beautifully in trending markets and disastrously in choppy ones.

## Illustration

**Trending market — clean, profitable signals:**

![[09_moving_average_trending.png]]

The 30-day SMA cleanly captures the up-then-down regime. The buy at the start and the sell near the peak ride almost the whole move.

**Choppy/sideways market — whipsaw losses:**

![[10_moving_average_sideways.png]]

The same rule applied to a sideways market produces a string of buy/sell flips, each one losing money.

## Analogy

A simple moving average is like the rolling average score of a basketball team over the last 30 games. A single bad night doesn't crash the average; a single great game doesn't spike it. The 30-game average gives you a sense of how good the team has been *recently* — without overreacting to any individual game. But there's a price: if the team genuinely starts improving, the rolling average won't reflect it for several games. The very smoothness that protects you from noise also makes you slow to recognize real change.

## Numeric Example

5-day moving average on these closes: 100, 102, 101, 103, 105, 107, 106, 108

| Day | Close | 5-day SMA |
|----:|------:|----------:|
| 1   | 100   | —         |
| 2   | 102   | —         |
| 3   | 101   | —         |
| 4   | 103   | —         |
| 5   | 105   | (100+102+101+103+105)/5 = **102.2** |
| 6   | 107   | (102+101+103+105+107)/5 = **103.6** |
| 7   | 106   | (101+103+105+107+106)/5 = **104.4** |
| 8   | 108   | (103+105+107+106+108)/5 = **105.8** |

Each day, one new close enters the window and one old close leaves. The SMA rises every day in this example because every new close is greater than the close 5 days earlier.

**Backtest demonstration** (from `05_moving_average.py`):
- Trending market, N=30, threshold=0.5: 2 signals, P&L = **+9.74**
- Choppy market, N=30, threshold=0.3: 7 signals, P&L = **−46.15**

That single comparison captures the entire personality of the SMA: it is a trend-follower, and it pays for choppy markets.

## Python Implementation

See [[05_moving_average.py]]:

```python
from moving_average import sma, ma_reversal_signals, backtest_ma_signals

# Compute the moving average
ma_values = sma(closes, window=30)

# Generate buy/sell signals from MA reversals
signals = ma_reversal_signals(ma_values, threshold=0.5)
for s in signals:
    print(f"bar {s.bar}: {s.kind} at MA={s.ma_value:.2f}")

# Or: full backtest in one call
sigs, pnl = backtest_ma_signals(closes, window=30, threshold=0.5)
print(f"Total P&L: {pnl:.2f} from {len(sigs)} trades")
```

The streaming version `sma_streaming(prices, window)` is a generator suitable for live tick processing: O(1) update per bar, O(N) memory.

## Relationships

**Within Chapter 3:**
- An alternative way to encode the trend information from [[01_Uptrend]] / [[02_Downtrend]]. Where the pivot method is discrete (RH/RL points), the SMA is continuous.
- A curved counterpart to the straight-line [[03_Uptrend_Line]] / [[04_Downtrend_Line]]: both serve as "dynamic support/resistance" in trending markets.
- Conceptually closer to [[08_Internal_Trend_Line]] than to a conventional trend line — both are best-fit smoothers rather than tangent lines.
- The lookback parameter N plays the same role as N in [[06_TD_Line]]: bigger N = slower, fewer, more significant signals.
- The reversal-based MA system is the third way to read the trend, alongside [[06_Trend_Line_Rules]] and pivot-pattern rules.

**Outside Chapter 3:**
- Variants discussed later in the book: weighted moving average, exponential moving average, dual-MA crossovers, MACD (Ch. 14 and Appendix).
- MAs feed directly into many **chart pattern** confirmations (Ch. 5).
- The MA can serve as an objective **stop-loss** location — exit on close back through the MA (Ch. 9).
- The lag property is precisely what motivates **oscillators** (Ch. 6) — oscillators are designed to lead, where MAs lag.
- The whipsaw problem in choppy markets is the central case study for the **false signals** discussion (Ch. 11).

## When does this concept work well?

| Market type | Effectiveness | Why |
|---|---|---|
| Strong, persistent trend | ✅ Excellent | Signals capture most of the move |
| Choppy / sideways | ❌ Disastrous | Whipsaws bleed capital steadily |
| Steady trend with mild pullbacks | ✅ Good | Pullbacks don't reverse the MA |
| Sharp, fast reversal | ⚠️ Late | MA lags by ~N/2 bars |
| Live tick processing | ✅ O(1) update | The streaming form is trivially fast |

## Choosing N

| N | Behavior |
|---|---|
| 5-10 | Very reactive, many false signals, low lag |
| 20-50 | Balanced — common defaults for swing trading |
| 100-200 | Smooth, slow, identifies major regime |

## Source

Schwager, *Getting Started in Technical Analysis*, Ch. 3, pp. 45-50 (Figures 3.18-3.21). The discussion explicitly contrasts the trending-market case (Fig. 3.20: three signals, two big winners) against the choppy-market case (Fig. 3.21: six consecutive losses and a break-even) using the same rule set.
