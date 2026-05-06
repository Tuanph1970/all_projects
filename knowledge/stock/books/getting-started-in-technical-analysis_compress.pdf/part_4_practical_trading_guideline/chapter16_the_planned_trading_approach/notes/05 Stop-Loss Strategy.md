# 05 Stop-Loss Strategy

**Element 2 of [[03 Risk Control Plan]]** · [[00 Chapter 16 Index]]

![[06_stop_loss.svg]]

## Definition

A **stop-loss strategy** is the predetermined exit rule that triggers when a trade moves against you. The chapter's central message can be condensed into one sentence: **know where you'll get out before you get in.**

Without a pre-set stop, traders procrastinate on liquidating losers — hoping rather than acting — and a single such lapse can be enough to take them out of the game.

Two acceptable forms:
- A **GTC (good-till-canceled) stop order** placed at trade entry.
- A **mental stop** with the order placed when price approaches the level — only suitable for traders who can be honest with themselves about discipline.

System traders may not need explicit stops if their system reverses position on its own — the reversal performs the stop's protective function.

## Easy Analogy

A stop-loss is like the timer on a parking meter. You decide the maximum time (loss) before you walked away from the car (entered the trade). When the timer expires, you move the car (exit the trade) — no debating with yourself about whether to risk a ticket "for just five more minutes". The decision was already made when you parked.

Without the timer, you'd talk yourself into "just a little longer", and one $300 fine cancels a year's worth of saved meter money.

## Numeric / Concrete Example

A trader enters AAPL at $175 with a stop at $168 — risking $7/share.

**Day 1-3:** stock drifts to $172. The trader's brain starts working:
- "It's almost back to break-even, just need a little patience."
- "Earnings come out next week, I should give it room."
- "If I sell here I'll just lock in the loss."

**With the GTC stop in place:** none of that mental noise matters. If price tags $168, the trade is closed at $168. Total loss: $7 × 200 = $1,400. Done. Move on.

**Without the stop:** AAPL drifts to $165, then $158 on a sector sell-off. The trader, now down $3,400, sells in panic at $156. Total loss: $3,800 — more than 2.7× the planned loss. One trade just consumed the next two months of profitable work.

## Python Code

A simple stop-loss check inside a backtest loop:

```python
def stop_hit(direction, current_low, current_high, stop_price):
    """For a long, stop hits when low <= stop. For a short, when high >= stop."""
    if direction == 'long':
        return current_low <= stop_price
    return current_high >= stop_price

# Always trail in the favourable direction only
def trail_stop(direction, current_stop, candidate_stop):
    if direction == 'long':
        return max(current_stop, candidate_stop)
    return min(current_stop, candidate_stop)
```

The trader's notebook in [[03_traders_notebook.py]] enforces the **never-widen-a-stop** rule.

## Relationships

### Within Chapter 16
- Inseparable from [[04 Maximum Risk Per Trade]]: the stop distance is the denominator of the position-sizing formula. No stop = no sizing rule.
- [[08 Market Volatility Adjustments]] often expresses the stop in terms of ATR multiples instead of fixed dollars.
- Recorded in two columns of [[12 Traders Notebook]] — initial stop and current stop — so the analyst can later check whether stops are being placed too tight or too wide.

### Outside Chapter 16
- **Chapter 9 — Choosing Stop-Loss Points** is the deep-dive companion to this rule. It covers placement around relative highs/lows, breakouts, and price retracements.
- **Chapter 18 — Rule #9 (Risk Control)**: predetermining the exit before entry is repeatedly cited as one of the rules every interviewed trader mentions.

## When This Concept Works Well
- When the stop is at a level the *market structure* — not the trader's pain threshold — defines (below a swing low, beyond an ATR band, etc.).
- When stops are tightened in the trader's favour but never loosened.

## When It Fails
- When stops are placed too close, just under noise levels — every trade gets stopped out by ordinary volatility ("death by a thousand stops").
- When the trader keeps mental stops but routinely "gives the trade a little more room" — that's just hope dressed up as analysis.
