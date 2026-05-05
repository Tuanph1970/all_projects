# Reaction to Long-Term Moving Average

**Type:** Strategy (Strategy 4 of 4)
**Chapter:** [[Chapter_08_Index|Chapter 8 — Midtrend Entry and Pyramiding]]
**Pages:** 133–135

---

## Definition

**Reaction to Long-Term Moving Average** uses a slow-smoothing MA (Schwager illustrates with a 40-day) as a *moving support line* in an uptrend (or *moving resistance* in a downtrend). When price dips back to or below the MA, that's interpreted as the counter-move running out of steam — buy on the dip.

Operational rules (uptrend):
- Compute the MA over a long window (e.g., 40 days).
- Buy any bar where price dips at/below the MA having been above it on the previous bar.
- Use a price-based or recent-low protective stop.

Mirror conditions for downtrends.

**Important nuance:** Schwager points out that this use of the MA is *counter-trend* (entering on the dip), not *trend-reversal*. For trend-reversal signals, you typically use a **two**-MA crossover; here we use **price vs. one MA**, which is more sensitive and meant for re-entries, not regime change.

## Illustration

![[05_long_term_ma_reaction.png]]

## Analogy — a tide and a beach

The trend is like a rising tide. The waves go in and out — each wave retreats, then comes back. The 40-day MA is the **average tide line** drawn on the sand. Each time the water pulls back to that line, you know it's about to come forward again. You don't need to predict the exact wave; you just need to know where the average is.

If the water pulls back *well below* that line and stays there → the tide has turned. You stop fishing in the same spot.

## Numeric example

Suppose Stock XYZ is in a clear uptrend:

| Day | Close | 40-day MA | Signal |
|---|---|---|---|
| 100 | $58.20 | $55.10 | above MA — no signal |
| 101 | $57.40 | $55.30 | still above |
| 102 | **$54.80** | $55.45 | **dipped below MA → BUY** |
| | | | entry $54.80, stop $53.20 (≈3% below) |
| 130 | $62.00 | $58.20 | above MA again |

The entry sits within 1% of the MA, and the move from $54.80 to $62.00 (a ~13% return in ~30 days) repays the small ~3% risk roughly **4×**.

If the trend had failed and price continued to $52, the stop at $53.20 would have closed the trade for a small loss instead of a large one.

## Code

```python
# /code/05_long_term_ma_reaction.py
class LongTermMAReactionStrategy:
    def __init__(self, trend: TrendDir, ma_period: int = 40,
                 stop_buffer_pct: float = 0.03): ...
    def generate(self, prices: pd.Series) -> list[MAReactionEntry]: ...
```

The implementation walks every bar with a valid MA, fires a BUY when price *first* crosses from above the MA to at/below it (the upward equivalent for SHORT), and places the stop a configurable buffer below the entry.

Full file: `05_long_term_ma_reaction.py`

## Relationships

### Within Chapter 8

- **vs. [[Percent_Retracement]]:** Retracement uses a *fixed* level computed from one swing; MA-reaction uses a *moving* level that updates daily. The MA gives more signals but can be noisy in choppy ranges.
- **vs. [[Reversal_of_Minor_Reaction]]:** Both wait for a pullback, but minor-reaction requires a confirmation candle (close > X-day high). MA reaction fires the moment price touches the MA, no confirmation needed → earlier but less reliable.
- **vs. [[Continuation_Pattern_Breakout]]:** Pattern breakout requires a *shape*; MA reaction needs none. MA reaction works on smoothly trending markets that never form clean patterns.
- **For [[Pyramiding]]:** Most automation-friendly trigger of the four — easy to encode in a system.

**Use long-term MA reaction when**

✅ the trend is persistent and price keeps reverting to its average
✅ you want a fully mechanical, code-able rule
✅ you want lots of entry attempts (smaller positions, more trades)

❌ avoid when the market is in a wide trading range (price will cross the MA constantly with no follow-through)

### Outside Chapter 8

- [[Chapter_03_Trends]] — defines moving averages and trend identification; this strategy reuses the same MA but for re-entry, not identification.
- [[Chapter_14_Trading_Systems_Structure]] — uses **two** moving averages for crossover trend signals; explicitly contrasted in this chapter to clarify the different roles.
- [[Appendix_Weighted_Moving_Averages]] — exponentially or linearly weighted MAs (EWMA, LWMA) are alternative kernels for the same idea.
- [[Chapter_06_Oscillators]] — overbought/oversold readings can be combined with the MA pullback for a higher-confidence entry.
