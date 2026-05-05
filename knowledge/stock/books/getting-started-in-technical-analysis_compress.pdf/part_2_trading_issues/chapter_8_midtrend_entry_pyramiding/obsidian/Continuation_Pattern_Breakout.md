# Continuation Pattern Breakout

**Type:** Strategy (Strategy 3 of 4)
**Chapter:** [[Chapter_08_Index|Chapter 8 — Midtrend Entry and Pyramiding]]
**Pages:** 132–133

---

## Definition

**Continuation Pattern Breakout** enters in the trend's direction when price **breaks out of a sideways consolidation** that formed during a pause in the trend. The consolidation can be a flag, pennant, triangle, or simple trading range; what matters is that it represents *the market catching its breath*, after which it tends to resume in the direction it was going.

Operational definition (this implementation):
- Identify a stretch of at least **5 bars** whose high–low range is small relative to price (≤ 5%).
- Determine the prevailing trend over the prior ~30 bars.
- Buy on a close above the consolidation top (uptrend) or sell below the bottom (downtrend).
- Place the protective stop at the **opposite** edge of the consolidation.

Schwager makes a useful refinement: once a trend is *already* established, you don't *have* to wait for the breakout — you can also enter *inside* the consolidation, anticipating the resolution. Either way, the consolidation low/high becomes the stop.

## Illustration

![[04_continuation_breakout.png]]

## Analogy — runner pausing for water

A long-distance runner who has been steadily moving forward stops at a water station for a few seconds. They're not turning around, they're not quitting — they're just topping up. When they put the cup down and step forward again, you can be quite sure they'll keep heading toward the finish line.

The water station = the consolidation. Stepping forward again = the breakout. The bench they were standing next to = your stop reference (if they sit *back down* on it, something's wrong, get out of the trade).

## Numeric example

Suppose a stock rallies from $100 to $120, then trades between **$118 and $122** for 8 days.

| Field | Value |
|---|---|
| Consolidation top | $122 |
| Consolidation bottom | $118 |
| Consolidation range | $4 (~3.3% of avg price → qualifies) |
| Buy signal | first **close above $122** |
| Stop | $118 (opposite edge) |
| Risk per share at entry $122.50 | **$4.50** |
| If projection target = $140 | reward $17.50 → reward/risk ≈ **3.9 : 1** |

If price never closes above $122, no trade. If price *closes below $118 first* (downside break of the consolidation), the pattern fails and the trader stands aside — possibly reversing if other Chapter-11 conditions are met.

## Code

```python
# /code/04_continuation_breakout.py
class ContinuationBreakoutStrategy:
    def __init__(self, min_bars=5, max_range_pct=0.05, trend_lookback=30): ...
    def generate(self, prices: pd.Series) -> list[BreakoutEntry]: ...
```

The implementation:
1. Slides a window across the price series; extends it as long as the range stays small.
2. Once the window can't be extended, the resulting interval is the consolidation.
3. The prior-trend slope (linear regression) determines which side of the box to break.
4. The first bar that pierces the right side becomes the entry; the opposite side is the stop.

Full file: `04_continuation_breakout.py`

## Relationships

### Within Chapter 8

- **vs. [[Percent_Retracement]]:** Retracement enters on a *pullback*; pattern breakout enters on a *resumption*. Pattern breakout is more conservative — you've waited for the market to confirm itself — but you pay for it with worse fill.
- **vs. [[Reversal_of_Minor_Reaction]]:** Both are confirmation-based, but pattern breakout requires a *visible structure*. Minor-reaction works on noisy, structureless trends.
- **vs. [[Reaction_to_Long_Term_MA]]:** Pattern breakout is event-driven (triggered by the breakout bar); MA reaction can fire any day price dips to the average.
- **For [[Pyramiding]]:** A natural fit — every consolidation along a trend offers a chance to add a unit, with the pattern's other side providing a tight stop.

**Use continuation breakout when**

✅ the chart shows clean rectangles, flags, triangles, or pennants
✅ you can tolerate occasional false breakouts (they happen — see [[Chapter_11_Most_Important_Rule]] for how to *exploit* them)
✅ you want a clear, geometric stop (the pattern's far edge)

❌ avoid when the market is moving smoothly without consolidating

### Outside Chapter 8

- [[Chapter_05_Chart_Patterns]] — the *taxonomy* of continuation patterns (flag, pennant, triangle, rectangle) referenced here.
- [[Chapter_04_Trading_Ranges_Support_Resistance]] — a "trading range" is just a wide continuation pattern.
- [[Chapter_11_Most_Important_Rule]] — when a pattern *fails* (price breaks out and immediately reverses), it becomes a strong signal in the *opposite* direction. Failed continuation = bull/bear trap.
- [[Chapter_14_Trading_Systems_Structure]] — the breakout system in trend-following systems uses N-day high/low as a generic version of this idea.
