# 04 — Crossover Moving Average System

## Definition

A **crossover moving average system** uses *two* moving averages of different lengths and generates trade signals from their relative position:

- **Buy** when the shorter-term MA crosses *above* the longer-term MA.
- **Sell** when the shorter-term MA crosses *below* the longer-term MA.

Because both inputs are smoothed, the false-signal problem of the simple MA system is sharply reduced — a sudden one-day price spike can yank price across a single MA, but it can rarely yank a 10-day MA across a 40-day MA.

In a sense, the simple MA system is a special case where the short-term MA has length 1 (i.e., raw price). Going from "price vs MA" to "MA vs MA" is a meaningful upgrade with very little extra complexity.

## Illustration

![[04_crossover_ma.png]]

The orange line is the 10-day MA, the red line is the 40-day MA, and the blue line is price. Signals fire only when the orange line crosses the red line — a much rarer event than price crossing a single MA.

## Analogy

Two friends are watching the weather to decide whether to plan a picnic this weekend.

- **Friend A** looks at the **last 10 days** of weather and decides if conditions are getting nicer.
- **Friend B** looks at the **last 40 days** of weather to gauge the broader season.

A single freak hot day doesn't move either friend's verdict much. They throw a picnic only when Friend A's recent assessment becomes warmer than Friend B's seasonal one — i.e., the recent trend has clearly turned warmer than the seasonal baseline. They cancel only when the recent assessment becomes colder than the seasonal one.

This requires both views to actually disagree, so they avoid getting jerked around by a single weird day.

## Numeric example

Same 180-day synthetic series, three configurations:

| System | Short N | Long N | Signals | Comment |
|--------|---------|--------|---------|---------|
| Simple MA | — | 20 | 20 | Many whipsaws |
| Crossover MA | 5 | 20 | 8 | Better |
| Crossover MA | 10 | 40 | **2** | Much cleaner |

Doubling the lookbacks (10/40 vs 5/20) cuts signals dramatically — the system trades only when both MAs really disagree.

## Code

[[../codes/04_crossover_ma.py]]

```python
def crossover_signals(prices, short_n, long_n):
    s = pd.Series(prices)
    short = s.rolling(short_n).mean().values
    long_ = s.rolling(long_n).mean().values
    sigs, pos = [], 0
    for i in range(long_n, len(prices)):
        prev_diff = short[i-1] - long_[i-1]
        diff = short[i] - long_[i]
        if prev_diff <= 0 and diff > 0 and pos != 1:
            sigs.append((i, prices[i], 'BUY')); pos = 1
        elif prev_diff >= 0 and diff < 0 and pos != -1:
            sigs.append((i, prices[i], 'SELL')); pos = -1
    return sigs
```

## Relationships

### Within the chapter

- **Direct upgrade of:** [[02_Moving_Average_Systems]]. Same idea, smoother inputs.
- **Adds parameters:** the crossover system has *two* parameters (short N, long N) — a "parameter set" rather than a single number. This becomes important in [[00_Chapter14_Overview]] and in Chapter 15's optimization discussion.
- **Compatible with all modifications:** confirmation rules ([[06_Confirmation_Conditions]]), filters ([[07_Filter]]), pyramiding ([[10_Pyramiding]]), and trade-exit rules ([[11_Trade_Exit]]) all work on top of it.

### Beyond the chapter

- **Ch. 8 (Midtrend Entry):** uses moving averages as bounce zones for adding to existing positions, not as crossover signals — a different application of the same tool.
- **Ch. 15 (Testing):** the canonical example used to discuss parameter sets, robustness, and optimization curves.
- **MACD (general technical analysis):** the most famous instance of a crossover system, using two EWMAs and a signal line.

### When does the crossover system shine?

- Markets with sustained, multi-month trends (energies, currencies during macro shifts).
- When you can afford to be late to the start of the move (you'll always miss the first stretch — that's the price of fewer false signals).
- As the spine of a system that adds smaller refinements (filter, confirmation) rather than as a standalone strategy.
