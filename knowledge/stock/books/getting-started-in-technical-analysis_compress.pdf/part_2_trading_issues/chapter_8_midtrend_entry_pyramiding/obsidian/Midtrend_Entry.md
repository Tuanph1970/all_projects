# Midtrend Entry

**Type:** Concept (overview)
**Chapter:** [[Chapter_08_Index|Chapter 8 — Midtrend Entry and Pyramiding]]
**Pages:** 129–135

---

## Definition

**Midtrend entry** is the act of opening a new position *after* a market has already moved substantially in the trend's direction. The phrase is a name for a problem (and a set of techniques for solving it), not a single mechanic.

The chapter formalises four operational definitions of "the pause inside a trend is ending — get in now":
1. [[Percent_Retracement]]
2. [[Reversal_of_Minor_Reaction]]
3. [[Continuation_Pattern_Breakout]]
4. [[Reaction_to_Long_Term_MA]]

The two goals are always the same: **favourable entry timing** and **risk control** (a defined stop).

## Illustration

![[01_midtrend_entry_overview.png]]

## Analogy — catching a moving train

Imagine you're standing on a train platform and the train you wanted to catch has already started moving. You have three bad options and one good one:

- Run alongside and jump on now → risky, you might trip (= chasing the price)
- Refuse to board because it's already moving → you stay stranded (= the mistake the chapter warns against)
- Wait for it to come back → it isn't coming back (= "I'll buy on the dip" when the dip never comes)
- **Wait for the next station, where it slows briefly to let people on, and board there → safe and clean**

Each of the four strategies in this chapter is a different definition of *"the next station"*.

## Numeric example

In May 1994, coffee had already rallied **35%** off the April low. A trader looking at the chart felt it was "too late." It turned out only ~20% of the total move had happened — coffee continued upward for two more months, completing the remaining ~80% of the rally. Refusing to enter at 35% missed roughly 4× the move.

The underlying principle, quoted by Schwager from Edwin Lefèvre: *"Prices are never too high to begin buying or too low to begin selling."*

## Code

See [[#Source]] — a generic engine that takes any combination of the four strategies and scans a price series. Each strategy returns `(bar, side, entry, stop, reason)` records, and the engine applies a risk-per-trade filter on top.

## Source

```python
# /code/01_midtrend_entry.py
class MidtrendEntryEngine:
    def __init__(self, strategies, max_risk_per_trade=0.02): ...
    def scan(self, prices) -> pd.DataFrame: ...
```

Full file: `01_midtrend_entry.py`

## Relationships

### Within Chapter 8

| Concept | Relationship |
|---|---|
| [[Percent_Retracement]] | Most aggressive — enters before the trend has visibly resumed. **Best when** the market shows clean, oscillating swings. |
| [[Reversal_of_Minor_Reaction]] | Most patient — waits for both a reaction *and* a confirmation. **Best when** false starts are common (whipsaw markets). |
| [[Continuation_Pattern_Breakout]] | Pattern-driven — needs a recognisable consolidation. **Best when** the market produces clean flags / triangles. |
| [[Reaction_to_Long_Term_MA]] | Mechanical — easy to automate. **Best when** the trend is persistent enough that price keeps reverting to its MA. |
| [[Pyramiding]] | Identical decision problem — same four triggers, plus three risk rules. |

### Outside Chapter 8

- [[Chapter_03_Trends]] — defines the trend itself (the precondition).
- [[Chapter_09_Choosing_Stop_Loss_Points]] — formalises the stop placement that every entry above implicitly requires.
- [[Chapter_14_Trading_Systems_Structure]] — re-uses these triggers as system rules.
- [[Chapter_11_Most_Important_Rule]] — failed midtrend entries become *contrarian* signals.
