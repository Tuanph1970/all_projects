# Pyramiding

**Type:** Concept (companion to [[Midtrend_Entry]])
**Chapter:** [[Chapter_08_Index|Chapter 8 — Midtrend Entry and Pyramiding]]
**Pages:** 135

---

## Definition

**Pyramiding** is the practice of **adding new units to an existing winning position** as the trend extends — for example, buying 100 shares at $30, then another 100 at $35, $42, $48 as the rally continues.

Schwager makes the key observation that **the timing problem for a pyramid add is identical to the midtrend-entry problem**. Therefore any of the four strategies in this chapter can serve as the trigger for adding a unit. What pyramiding adds *on top* of midtrend entry is a small set of risk-management rules.

### The three pyramid risk rules

1. **Last-unit-must-be-profitable.** Never add a new unit unless the *most recent* unit you placed currently shows a profit. (Adding to a losing leg compounds losses.)
2. **No-net-loss-at-stop.** Never add if the new aggregate stop would imply a *net loss* on the entire position. The combined stop, applied to the average entry, must be at break-even or better.
3. **Pyramid-no-larger-than-base.** Each pyramid unit must be **no larger** than the original base position. (No "doubling down" with bigger size.)

## Illustration

![[06_pyramiding.png]]

## Analogy — building with stacking blocks

Think of a child building a tower with wooden blocks. They place a big base block first. Then they add smaller blocks on top. Three rules keep the tower from collapsing:

1. **The block below has to be steady before you place a new one on top.** (= last unit must be profitable)
2. **You can't add a block so heavy that, if everything wobbled, the whole tower would fall over.** (= aggregate stop ≥ break-even)
3. **No block on top can be bigger than the base.** (= pyramid units ≤ base)

If the trader adds bigger and bigger units (an *inverted* pyramid) the position becomes top-heavy — a small reversal wipes out everything below. Hence the geometric metaphor.

## Numeric example

A trader buys **100 shares at $30**, stop at $28.

| Step | Price | Add | Stop | Avg entry | Total qty | PnL @ stop |
|---|---|---|---|---|---|---|
| 1 | $30 | +100 | $28 | $30.00 | 100 | −$200 (initial risk) |
| 2 | $35 | +100 | $32 | $32.50 | 200 | −$100 *(rule 2 violated → reject)* |
| 2′ | $42 | +100 | $36 | $36.00 | 200 | $0 ✅ |
| 3 | $44 | +200 | $40 | — | — | *(rule 3 violated → reject)* |
| 3′ | $41 | +100 | $39 | — | — | *(rule 1 violated → reject; last unit @ $42 is in loss)* |
| 3″ | $48 | +100 | $42 | $40.00 | 300 | +$600 ✅ |

The trader now holds 300 shares with break-even average $40, locked-in $600 profit at the worst case if stopped out at $42.

## Code

```python
# /code/06_pyramiding.py
@dataclass
class PyramidPosition:
    side: Literal["LONG", "SHORT"]
    base_qty: int
    units: list[Unit] = field(default_factory=list)
    stop_price: float | None = None

    def open_base(self, bar, price, stop): ...
    def try_add(self, bar, price, qty, proposed_stop) -> tuple[bool, str]:
        # Rule 3 — qty ≤ base
        # Rule 1 — last unit in profit
        # Rule 2 — aggregate stop ≥ break-even
```

The `try_add` method enforces the three rules and returns `(accepted, human-readable reason)` so a system log shows exactly why a pyramid attempt was rejected.

Full file: `06_pyramiding.py`

## Relationships

### Within Chapter 8

- **Triggers come from any of the four strategies:** [[Percent_Retracement]], [[Reversal_of_Minor_Reaction]], [[Continuation_Pattern_Breakout]], [[Reaction_to_Long_Term_MA]]. Pyramiding *consumes* their signals.
- **Most natural pairings:**
    - **Trending market with regular pullbacks** → [[Reversal_of_Minor_Reaction]] for the trigger (each pullback is a clean signal).
    - **Trending market with consolidations** → [[Continuation_Pattern_Breakout]] for the trigger.
    - **Smooth trend without distinct pullbacks** → [[Reaction_to_Long_Term_MA]].

### Outside Chapter 8

- [[Chapter_09_Choosing_Stop_Loss_Points]] — the "stop" referenced in rule 2 is formalised here. A pyramid system needs a clear method for raising the stop as price advances.
- [[Chapter_14_Trading_Systems_Structure]] — defines the **standard problem #3** of trend-following systems: *failure to exploit major price moves*. Pyramiding is the canonical solution. Chapter 14 provides a more elaborate example of a 10-day-low/-high-based pyramid scheme.
- [[Chapter_16_Planned_Trading_Approach]] — pyramiding multiplies position size, so it interacts directly with the *maximum risk per trade* limit.
- **Anti-pattern: averaging down.** Pyramiding adds to *winners*; averaging down adds to *losers*. They look superficially similar, but the risk profile is opposite — pyramiding caps loss while averaging down compounds it. Schwager is unambiguous: the second is one of the most common ways to blow up an account.
