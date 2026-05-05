# 11 — Trade Exit (and Re-entry)

## Definition

In a basic trend-following system, you only liquidate when the *opposite* signal fires (a long stays long until a sell signal arrives). A **trade-exit rule** lets you liquidate *before* the opposite signal — to:

- cap the loss on a losing trade;
- lock in some open profit on a winner that has started to give back too much.

Two consequences make trade-exit rules tricky:

1. **You must define a re-entry rule.** Without re-entry, the system would exit a long, then never re-establish it even when the trend is still in force — you'd miss the rest of the move.
2. **The exit + re-entry pair introduces whipsaw losses.** If you exit a perfectly good trade and re-enter at a slightly worse price, the round-trip is a loss that the original system wouldn't have suffered.

Schwager's caution: adding a trade-exit rule does **not** always improve performance. It often makes things worse. It should be added only when testing shows it pays for itself.

## Illustration

![[11_trade_exit.png]]

A long position taken on the rising portion (green up-arrow), followed by a trailing stop (red dashed line). When price falls more than 5 points below the running peak, the trade is exited (red X). A re-entry is triggered later when a new high is made.

## Analogy

You're playing a card game with cash on the line. You're up significantly mid-game.

- The **basic system** says: only stand up from the table when the dealer shouts "game over."
- A **trade-exit rule** says: if your current chip stack falls more than 30% below your peak, walk away — even if the game isn't formally over.
- A **re-entry rule** says: ...but if a new pot starts and the situation looks promising again, sit back down.

You've protected your peak. You haven't permanently quit. And you've accepted that occasionally you'll walk away, then walk back, paying the cover charge twice for nothing — that's the whipsaw cost.

## Numeric example

A long position entered at $98.25 with a trailing-stop trade-exit rule (peak − $5):

```
Initial buy day 20 @ $98.25
Trailing stop activates if price falls $5 below running peak.
[In this particular series, price kept rising → no exit triggered.]
```

Compare to a series where price reached $115 then fell back to $108:

```
Peak: $115 → trailing stop at $110.
Day price first closes below $110 → trade exits at, say, $109.30.
P&L on first leg: 109.30 – 98.25 = +$11.05  (locked in)
Re-entry: price subsequently breaks above $115 again → re-enter at $115.50.
The whipsaw cost: $115.50 entry vs $109.30 prior exit = $6.20 worse.
Pays off only if the second leg is meaningfully larger than $6.20.
```

## Code

[[../codes/11_trade_exit.py]]

```python
def trailing_stop_exit(prices, entry_idx, entry_price, side='LONG',
                        stop_distance=5.0):
    p = np.asarray(prices, dtype=float)
    best = entry_price
    for i in range(entry_idx + 1, len(p)):
        if side == 'LONG':
            best = max(best, p[i])
            if p[i] < best - stop_distance:
                return i, p[i]
        else:
            best = min(best, p[i])
            if p[i] > best + stop_distance:
                return i, p[i]
    return None, None

def reentry_breakout(prices, exit_idx, side='LONG', n=20):
    p = np.asarray(prices, dtype=float)
    for i in range(exit_idx + n, len(p)):
        if side == 'LONG' and p[i] > p[exit_idx:i].max():
            return i, p[i]
        if side == 'SHORT' and p[i] < p[exit_idx:i].min():
            return i, p[i]
    return None, None
```

## Relationships

### Within the chapter

- **Modification of:** any base trend-following system — [[02_Moving_Average_Systems]], [[04_Crossover_Moving_Average_System]], [[05_Breakout_Systems]].
- **Sibling of:** [[10_Pyramiding]]. Pyramiding scales position size up; trade exit scales it down or to zero. Together they give the system bidirectional position sizing.
- **Often paired with:** [[06_Confirmation_Conditions]] (require confirmation on the re-entry to avoid immediate whipsaw back).

### Beyond the chapter

- **Ch. 9 (Stop-Loss Points):** the entire vocabulary of stop placement comes from there — Schwager treats stops and trade-exits as the same family.
- **Ch. 10 (Setting Objectives):** profit targets are a related but distinct exit mechanism — they exit on a price level rather than a give-back from peak.
- **Ch. 11 (Most Important Rule):** failed signals (price action that contradicts the original signal) are themselves a form of trade exit.
- **Ch. 16 (Planned Trading Approach):** the trade-exit rule is part of every individual trade plan.

### When trade-exit rules help most

- **Markets with sharp reversals** where waiting for the opposite signal hands back too much profit.
- **High-volatility instruments** where a small fraction of the move from peak is still a meaningful dollar amount.
- **Combined with risk control on a portfolio level** — the trade-exit caps single-trade damage when something goes wrong.

They hurt in **slow, persistent trends** where the small reactions look like exits but the trend resumes cleanly without a re-entry signal — you've cut the trade short, paid two extra round-trips, and missed the second leg.
