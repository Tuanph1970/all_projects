# 01 — Trend-Following Systems (Fast vs Slow)

## Definition

A **trend-following system** is a rule-based trading system that tries to identify the direction of an established price trend and trade *with* it, holding the position until evidence of a trend reversal triggers an exit. The system makes no attempt to call tops or bottoms — it accepts giving back some profit at the end of each trend in exchange for capturing the bulk of the move.

The system's **sensitivity** (fast vs slow) is controlled by how short or long the lookback window is:

- **Fast system** — short lookback. Reacts quickly to reversals. Captures more of each move when right, but generates many false signals (whipsaws) when wrong.
- **Slow system** — long lookback. Smoother, fewer signals, fewer false alarms — at the cost of late entries and bigger per-trade drawdowns before the system flips.

Schwager's empirical view: in most markets, slow systems beat fast systems because the cost of avoided whipsaws exceeds the cost of late entries.

## Illustration

![[01_fast_vs_slow.png]]

The same price series traded by a fast (N=7) and slow (N=40) breakout system. Fast generates many signals — most of them wrong in flat zones. Slow generates almost nothing but stays cleanly with the trend.

## Analogy

Imagine you're driving on a winding mountain road in heavy rain. You see brake lights ahead.

- The **fast** driver hits the brakes the moment any red light flickers. They never crash, but they keep braking for nothing — every reflection, every distant taillight. The ride is jerky, exhausting, and slow.
- The **slow** driver waits until the brake lights are clearly steady before reacting. They miss the very first warning, but they only slow down when slowing down was actually needed. Smoother ride, faster overall.

Both styles "work." Which one wins on a long trip depends on how often the road is genuinely dangerous vs. just noisy.

## Numeric example

```
Test: 150-day synthetic price series, breakout system

         Signals    Closed-trade P&L
Fast (N=7):  16          +$10.16
Slow (N=20):  7          –$ 7.55  (in this particular series)
Slow (N=40):  1            $ 0.00
```

The "right" speed depends on the data — there's no universal answer. The lesson is the **shape of the trade-off**, not the absolute numbers. Fast systems trade often; slow systems trade decisively.

## Code

[[../codes/01_trend_following.py]]

```python
def breakout_signals(prices, N):
    sigs, pos = [], 0
    for i in range(N, len(prices)):
        hi = prices[i-N:i].max()
        lo = prices[i-N:i].min()
        if prices[i] > hi and pos != 1:
            sigs.append((i, prices[i], 'BUY')); pos = 1
        elif prices[i] < lo and pos != -1:
            sigs.append((i, prices[i], 'SELL')); pos = -1
    return sigs
```

## Relationships

### Within the chapter

- **Parent of:** every other concept in the chapter. Moving averages (2–4) and breakouts (5) are *families* of trend-following systems. Modifications (6–11) all attempt to fix the natural weaknesses of trend-following.
- **Direct contrast with:** [[12_Countertrend_Systems]] — designed to do the opposite, and to work in conditions where trend-following fails (range-bound markets).
- **Tightly coupled to:** [[13_Diversification]] — Schwager argues trend-following only works *because* of diversification (insurance against missing the rare giant moves).

### Beyond the chapter

- **Ch. 3 (Trends):** the visual concept of a trend that this whole machinery tries to capture mechanically.
- **Ch. 7 (Is Chart Analysis Still Valid?):** the case that pure pattern reading isn't enough — systems give you discipline.
- **Ch. 15 (Testing):** the fast/slow choice is a *parameter* you have to test honestly (no curve-fitting).
- **Ch. 16 (Planned Trading Approach):** systems become one of the building blocks alongside risk management and trade plan.

### When does a fast system actually work better?

- Markets with frequent, sharp reversals (some equity index futures intraday).
- Markets where transaction costs are tiny relative to typical moves.
- Markets where the giant moves come fast and hard (currencies during macro shocks).

For most stock charts and most slower-moving futures, slow wins.
