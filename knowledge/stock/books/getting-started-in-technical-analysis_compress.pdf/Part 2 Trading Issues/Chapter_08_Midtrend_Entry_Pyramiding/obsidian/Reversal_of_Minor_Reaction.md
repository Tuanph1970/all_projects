# Reversal of Minor Reaction

**Type:** Strategy (Strategy 2 of 4)
**Chapter:** [[Chapter_08_Index|Chapter 8 — Midtrend Entry and Pyramiding]]
**Pages:** 132

---

## Definition

**Reversal of Minor Reaction** waits for a small counter-trend wiggle to *form first*, then enters when the primary trend resumes. Unlike [[Percent_Retracement]] (which is a fixed price level), this strategy is *behavioural* — it lets the market tell you the reaction is over.

Two parameters drive it:
- **N** — number of days that defines the reaction (a new N-day low in an uptrend, or N-day high in a downtrend).
- **X** — number of days that defines the resumption (close above the most recent X-day high, or below the X-day low for shorts).

Larger N/X = fewer false signals, later entries. Smaller N/X = more sensitive, more whipsaws.

## Illustration

![[03_reversal_minor_reaction.png]]

## Analogy — pushing a swing

When you push a child on a swing, you don't push at random — you push **at the moment the swing has finished going backwards and is just starting to come forward again**. Pushing too early (while it's still going back) wastes your effort. Pushing too late (when it's already in full forward swing) doesn't help much.

The minor reaction = the swing going backwards. The trend resumption = the swing starting forward again. The strategy says: *push at exactly that turn*.

## Numeric example

Downtrend example using N = 10, X = 4:

| Bar | Close | What happens |
|---|---|---|
| 35 | 120 | trend low so far |
| 36–47 | rises to 132 | counter-rally |
| **47** | **132** | new **10-day high** → **reaction defined**, mark this as protective stop |
| 48–55 | drifts lower | no signal yet |
| **56** | **closes at 128** which is below the **4-day low** (was 129) → **SHORT signal** |
|   | | entry: 128, stop: 132 (the reaction high), risk = $4 |

If the trader had used N = 5 instead, the reaction would have been "defined" at bar 41 (a less-significant peak), creating a worse entry.
If they had used X = 7, the resumption signal would have come at bar ~62, giving up $3 of the move but with fewer false starts.

## Code

```python
# /code/03_reversal_minor_reaction.py
class MinorReactionReversalStrategy:
    def __init__(self, trend: TrendDir,
                 reaction_lookback: int = 10,
                 resumption_lookback: int = 3): ...
    def generate(self, prices: pd.Series) -> list[ReactionEntry]: ...
```

The implementation walks the price series, marks any bar that's the lowest of the last N bars as a "reaction defined", then watches forward for the first close above the most recent X-day high (with a guard that the entry must be above the reaction extreme — so we don't enter into a still-falling market).

Full file: `03_reversal_minor_reaction.py`

## Relationships

### Within Chapter 8

- **vs. [[Percent_Retracement]]:** Retracement is *anticipatory* (place the order before behaviour confirms it). Minor-reaction is *reactive* (wait for confirmation, then chase). Retracement gives a better price; minor-reaction gives better confirmation.
- **vs. [[Continuation_Pattern_Breakout]]:** Both are confirmation-based, but a continuation pattern requires a *recognisable shape* over many bars; the minor-reaction approach uses just two N-day / X-day rules and works on shorter horizons.
- **vs. [[Reaction_to_Long_Term_MA]]:** Minor-reaction is purely price-based (no smoothing); MA reaction is smoothing-based.
- **For [[Pyramiding]]:** Schwager's preferred trigger for adding units, because each pyramid add is automatically gated by a fresh confirmation.

**Use minor-reaction reversal when**

✅ the trend is well-established but choppy
✅ you've been whipsawed by retracement-style entries before
✅ you want a *single rule* you can backtest cleanly

❌ avoid in fast trends without pullbacks (you'll miss the move entirely)

### Outside Chapter 8

- [[Appendix_Reaction_Count]] — a more sophisticated variant using a "reaction count" and "thrust count" (cumulative rather than single-bar).
- [[Chapter_14_Trading_Systems_Structure]] — the **breakout system** uses the same N-day-high/low mechanic, but as a *primary* trend signal rather than a *re-entry* signal. Same operator, different role.
