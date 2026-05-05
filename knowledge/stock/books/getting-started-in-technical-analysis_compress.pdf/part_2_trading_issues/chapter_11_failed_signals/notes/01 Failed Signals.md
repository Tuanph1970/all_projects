# 01 Failed Signals

**Parent:** [[00 Chapter 11 Index]]
**Tags:** #chapter11 #master-concept #failed-signal

## Definition

A **failed signal** is what happens when a market sets up a textbook chart pattern, takes the action the pattern predicts (e.g. an upside breakout), and then *refuses to follow through* — quickly retreating instead of extending in the expected direction. Schwager's central claim in Chapter 11 is that this non-follow-through is itself among the most reliable signals on a chart, and it usually points to a meaningful move in the **opposite** direction of the original pattern.

The mechanism is simple to picture: the breakout activates stop orders sitting just past the range boundary, those stops fill the few buyers (or sellers) standing there, and once that thin layer of liquidity is exhausted the market discovers there is no real demand (or supply) — so it falls back through where it came from and keeps going.

## Illustration

![[01_failed_signals_overview.png]]

In the book, **Figure 11.1** (Wal-Mart) is the canonical example: a breakout above a long consolidation that immediately reverses below the lower boundary.

## Common-life analogy

Imagine a crowd at a concert pressing toward a fire exit, convinced the show is cancelled. The first few people push the door open — but the moment they step through, they realise the parking lot is empty, no one organised an evacuation, and security is locking the door behind them. They scramble back inside, and seeing them retreat, the rest of the crowd panics in the **other** direction toward the main exit. The "the show is cancelled" rumour was the original signal; the few who acted on it and turned back are the failed signal — and the bigger movement happens away from the rumoured exit, not toward it.

## Numeric example

Stock has been trading between $48 and $54 for two months.
- Day 1: closes at $54.20 — apparent upside breakout.
- Day 2: $54.80.
- Day 3: closes at $53.20 — back inside the range. **Initial price confirmation** of bull trap.
- Day 8: closes at $47.50 — below the range low. **Strong price confirmation.**

A trader who recognises the failed signal sells short at $53.20 with a stop just above $54.80 (the breakout high). Risk is $1.60. If the market falls to $42 (a typical trap-driven extension), the reward is $11.20 — a ~7:1 reward-to-risk on a setup whose expected hit rate is well above coin flip.

## Python sketch

```python
def is_bull_trap(highs, closes, range_high, breakout_idx, lookahead=20):
    """Return True if a close back inside the range happens within `lookahead`."""
    breakout_high = highs[breakout_idx]
    for j in range(breakout_idx + 1, min(breakout_idx + lookahead + 1, len(closes))):
        if highs[j] > breakout_high:        # invalidated by a new high
            return False
        if closes[j] < range_high:          # initial-price confirmation
            return True
    return False
```

Full implementation: `code/chapter11_detectors.py` → `detect_bull_bear_traps()`.

## Relationships within the chapter

Failed Signals is the **umbrella** under which every other concept in the chapter lives. Each downstream concept identifies *which* pattern is being judged for follow-through:

| If the original pattern is… | …its failure is described in |
|---|---|
| Range breakout | [[02 Bull and Bear Traps]] |
| Trend line break | [[04 False Trend Line Breakouts]] |
| Continuation gap | [[05 Filled Gaps]] |
| Reversal spike | [[06 Return to Spike Extremes]] |
| Wide-ranging day | [[07 Return to Wide-Ranging Day Extremes]] |
| Flag / pennant | [[08 Counter-to-Anticipated Flag Pennant Breakout]], [[09 Opposite-Direction Breakout After Normal Breakout]] |
| Top / bottom (double, H&S) | [[10 Penetration of Top and Bottom Formations]] |
| Rounding | [[11 Breaking of Curvature]] |

[[03 Confirmation Conditions]] is the protocol you apply to **all** of them to decide when a failure is "official."

## When the concept works best

- **Crowded patterns.** The more traders are watching the same breakout, the more stop orders sit just past the boundary, and the cleaner the trap when it springs. See [[12 Future Reliability of Failed Signals]].
- **Long, well-defined prior pattern.** A six-week range that fails its breakout is more reliable than a two-day micro-range.
- **Sharp reversal speed.** The faster prices snap back, the stronger the signal. A drift back over two months is much less informative than a snap back in three days.

## Relationships outside the chapter

- The **patterns** that can fail are catalogued in [[Chapter 5 - Chart Patterns]] (gaps, spikes, WRDs, flags, H&S, rounding) and [[Chapter 4 - Trading Ranges and Support and Resistance]] (range breakouts).
- Failed-signal entries need disciplined exits — see [[Chapter 9 - Stop Loss Points]].
- The principle is restated as **Rule #76** ("a failed signal is more reliable than the original signal") in [[Chapter 17 - Eighty-Two Trading Rules]].
- Skilled use of failed signals is one of the five reasons Schwager argues chart analysis remains valid despite popularity, in [[Chapter 7 - Is Chart Analysis Still Valid]].
