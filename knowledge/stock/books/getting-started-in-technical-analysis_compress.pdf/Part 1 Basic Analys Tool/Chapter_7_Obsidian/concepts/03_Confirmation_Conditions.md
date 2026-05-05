---
concept: "Confirmation Conditions"
chapter: 7
order: 3
tags: [confirmation, false-signals, filter, breakout, chapter-7]
source: "Schwager, Ch. 7, pp. 122-123"
---

# 3. Confirmation Conditions

## Definition

A **confirmation condition** is an additional rule that must be satisfied *after* a primary chart signal before a trader will actually enter the position. The purpose is to filter out false signals at the cost of slightly later entry on real ones.

Common confirmation devices Schwager lists (p. 122):
- **Time delay** — wait N days after the breakout before entering.
- **Minimum percent penetration** — require price to clear the level by ≥ x%.
- **Specific chart patterns** — e.g., require two thrust days in the signal direction.

The trade-off is fundamental and unavoidable:

> The less restrictive the conditions, the greater the number of false signals; the more restrictive the conditions, the greater the surrendered profit potential due to late entry.

There is **no universally best** confirmation rule — Schwager makes this point explicitly. The choice is one of the central ways chart analysis is *individualised* between traders.

## Simple Analogy

Confirmation conditions are like **waiting for the elevator doors to fully close before pressing the button to your floor**. Press too early (no confirmation) and the doors open back up — wasted action, slight embarrassment. Press too late (over-restrictive confirmation) and the elevator has already started moving toward someone else's floor — you missed it. The right delay is short enough not to miss the ride and long enough that the doors actually mean it.

## Chart Illustration

![[03_confirmation.png]]
*Top panel: every breakout taken — three trades, two false. Bottom panel: same data with a 3-day wait + close-still-beyond-level confirmation. Notice how the entries shift later, and the size of each trade's P&L changes.*

## Real Numeric Example — Same Eurodollar series, two rule sets

| Rule Set | # Trades | Wins | Net (pts) | Net (USD) |
|---|---|---|---|---|
| **No confirmation** | 3 | 1 | +1.17 | **+$2,913** |
| **3-day wait + close-still-beyond-level** | 3 | 1 | +0.34 | +$858 |

In *this* random seed, confirmation actually **reduced** profits because the late entry shrank the winning trade more than it shrank the losing trades. Schwager warns about this directly: *"one could also construct examples in which the use of confirmation conditions is detrimental to the trading results"* (p. 123). His point isn't that confirmation always helps — it's that **classical chart concepts become a more powerful trading approach when combined with confirmation rules** *that the trader has tuned to their market and time horizon*.

In other simulations (other random seeds), confirmation ranges from −20% to +60% impact on net P&L. **Tuning is empirical, market-specific, and cannot be skipped.**

## Code

```python
def simulate_with_confirmation(df, lookback=30, wait_days=3):
    """Wait wait_days; enter only if price is still beyond the original
       breakout level."""
    trades, in_pos, pending = [], 0, None
    for i in range(lookback, len(df)):
        win = df.iloc[i-lookback:i]
        hi, lo = win["high"].max(), win["low"].min()
        mid    = 0.5 * (hi + lo)
        c      = df["close"].iat[i]
        if in_pos == 0 and pending is None:
            if   c > hi: pending = dict(dir=+1, idx=i, level=hi, mid=mid)
            elif c < lo: pending = dict(dir=-1, idx=i, level=lo, mid=mid)
        elif pending and i - pending["idx"] >= wait_days:
            confirmed = (pending["dir"]==+1 and c > pending["level"]) or \
                        (pending["dir"]==-1 and c < pending["level"])
            if confirmed:
                in_pos, entry, stop = pending["dir"], c, pending["mid"]
            pending = None
        elif in_pos != 0:
            stopped = (in_pos==+1 and c<stop) or (in_pos==-1 and c>stop)
            if stopped:
                trades.append((in_pos, entry, c, (c-entry)*in_pos))
                in_pos = 0
    return trades
```

Full source: [[ch7_master.py]]

## Relationships

### Within Chapter 7
- **Complements [[02_Risk_Control]]:** Risk control caps loss *size*; confirmation reduces loss *frequency*. Together they shrink total drawdown.
- **Distinct from [[06_Failed_Signals]]:** confirmation says *"don't act until the signal proves itself"*. Failed signals say *"if the signal proves itself wrong, fade it."* They are the same insight from opposite ends — both rely on observing what happens *after* the textbook signal.
- **Limits [[07_Art_Vs_Science]]:** the *which* and *how strict* of confirmation are pure judgement, not formula.

### Outside Chapter 7
- [[Chapter_4_Trading_Ranges]] — Schwager already advised using confirmation on trading-range breakouts (p. 56-58: "five days beyond the range", "minimum percent penetration", "thrust days"). Chapter 7 generalises that advice to all signals.
- [[Chapter_5_Chart_Patterns]] — thrust days, run days, and wide-ranging days (Ch. 5 §2) become the building blocks of pattern-based confirmation.
- [[Chapter_6_Oscillators]] — oscillator signals as "trading alerts" awaiting price confirmation is *exactly* this concept under a different name.
- [[Chapter_14_Trading_Systems]] — "filter rules" and "confirmation conditions" are listed as the second of ten cures for whipsaws in standard trend-following systems (Table 14.2, p. 251).
- [[Chapter_15_Testing_And_Optimizing]] — confirmation parameters are the most over-optimised knobs in system design; cross-validation matters.

### When does confirmation work well vs. poorly?
| Market / signal type | Effect of adding confirmation |
|---|---|
| High-noise, frequent false breakouts | ✅ Big improvement — many small losses removed |
| Strong, fast trends with clean breakouts | ⚠️ Slight reduction — late entry costs profit |
| News-driven gaps | ❌ Confirmation arrives too late; the move is over |
| Overlapping signals across timeframes | ✅ Multi-timeframe agreement *is* a confirmation rule |
| Very thin / illiquid markets | ⚠️ Slippage makes the late entry materially worse |

### Choosing wait_days

| wait_days | Behaviour |
|---|---|
| 0  | No confirmation; every signal taken |
| 1–2 | Filters obvious overnight reversals only |
| **3–5** | Schwager's typical illustration; balances filtering vs. timing |
| 5–10 | Heavy filtering; high opportunity cost |
| 10+ | The signal is essentially a delayed trend-following entry |

---

**Source:** Schwager (1999), Ch. 7, pp. 122-123, Figure 7.3.
**Tags:** #confirmation #false-signals #filter-rules #chapter-7
