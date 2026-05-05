# Percent Retracement

**Type:** Strategy (Strategy 1 of 4)
**Chapter:** [[Chapter_08_Index|Chapter 8 — Midtrend Entry and Pyramiding]]
**Pages:** 130–132

---

## Definition

**Percent Retracement** is a midtrend entry strategy that exploits the market's natural tendency to *partially undo* its prior swings before resuming the main trend. The trader pre-commits to a buy/sell zone defined as a percentage of the most recent swing.

Operational rules (long side):
- Identify the most recent **relative low → relative high** swing.
- Calculate `entry zone = swing_high − (swing_high − swing_low) × pct`, where `pct` is conventionally chosen from the **35–65% band**.
- Place a **protective stop** just below the swing low.

If price never retraces enough, no trade is taken — that's the price you pay for the precision.

## Illustration

![[02_percent_retracement.png]]

## Analogy — bargain shopping with a price ceiling

Suppose a coat you want is on sale on and off all year. You don't want to pay full price ($140), but you also don't want to wait forever. So you decide in advance: *"I'll buy when it drops at least to $120 (50% off the spread between full price and last summer's clearance price of $100)."*

- If it goes on sale to $120 → you buy.
- If it never drops that far → you don't buy at all, no regrets.
- If it drops below $100 (your "swing low") → something is wrong with the coat (or the brand). Walk away. ← *that's the stop.*

That's exactly the trade.

## Numeric example

| Field | Value |
|---|---|
| Swing low | **$100** |
| Swing high | **$140** |
| Swing size | $40 |
| 35% retracement entry | $140 − ($40 × 0.35) = **$126** |
| 50% retracement entry | $140 − ($40 × 0.50) = **$120** |
| 65% retracement entry | $140 − ($40 × 0.65) = **$114** |
| Protective stop | just below **$100** (e.g., $99) |
| Risk-per-share at 50% entry | $120 − $99 = **$21** (17.5% of entry) |

For tighter risk, choose a *shallower* retracement (35%). For better entry price, choose a *deeper* retracement (65%) — at the cost of often missing the trade.

## Code

```python
# /code/02_percent_retracement.py
class PercentRetracementStrategy:
    def __init__(self, retracement_pct: float = 0.50, swing_window: int = 5): ...
    def generate(self, prices: pd.Series) -> list[RetracementEntry]: ...
```

The implementation:
1. Scans the series for relative highs and lows (`find_swing_points`).
2. For each high, looks for the prior low.
3. Pre-computes the retracement target.
4. Walks forward looking for the first bar that touches the target.

Full file: `02_percent_retracement.py`

## Relationships

### Within Chapter 8

- **vs. [[Reversal_of_Minor_Reaction]]:** Retracement is *static* (level pre-defined); minor-reaction is *dynamic* (waits for behaviour). Retracement gets you in earlier and cheaper *when triggered* but misses more trades.
- **vs. [[Continuation_Pattern_Breakout]]:** Retracement enters in the *opposite* direction of the very recent move (counter-trend dip); pattern breakout enters in the *same* direction as the recent move (with-trend break).
- **vs. [[Reaction_to_Long_Term_MA]]:** Both look for a pullback, but retracement uses a horizontal price level (geometric), while MA reaction uses a moving curve (smoothed).
- **For [[Pyramiding]]:** Excellent trigger — the swing is reset every time you add, so the rule mechanically scales with the trend.

**Use percent retracement when**

✅ the market produces clean, well-defined swings
✅ you can wait days/weeks without entering
✅ volatility is moderate (extreme volatility blows through retracement zones)

❌ avoid when the market is moving in a one-way trend that never pulls back

### Outside Chapter 8

- [[Chapter_04_Trading_Ranges_Support_Resistance]] — retracement levels are essentially horizontal support / resistance derived from the most recent swing.
- [[Chapter_10_Setting_Objectives]] — measured-move objectives reverse the same arithmetic to project *targets*.
- The Fibonacci variants (38.2%, 50%, 61.8%) used outside the book are flavours of the same concept.
