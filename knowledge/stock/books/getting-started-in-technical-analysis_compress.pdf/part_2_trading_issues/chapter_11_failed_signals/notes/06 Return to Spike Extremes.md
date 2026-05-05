# 06 Return to Spike Extremes

**Parent:** [[00 Chapter 11 Index]] · **Master:** [[01 Failed Signals]]
**Tags:** #chapter11 #failed-signal #spike

## Definition

A **price spike** is a single day whose high (or low) sits sharply outside the highs (or lows) of the days immediately before and after, with the close near the *opposite* extreme of that day's range. Spikes typically mark a buying or selling climax, so they often serve as relative tops or bottoms.

A **return to a spike extreme** is when price later closes beyond the spike's prior high (in the case of a spike high) or below the spike's prior low (for a spike low). When that happens, the spike is converted into a **failed signal** — the climax it appeared to mark was not durable, and a meaningful continuation in the direction of the penetration is likely.

The strength of the failure scales with two things: **how extreme the original spike was** (the more it stood out from neighbouring bars, the more meaningful its violation), and **how much time has passed** (Schwager prefers at least several weeks, ideally several months — a quick re-test of a spike is much weaker than a re-test months later).

## Illustration

![[06_return_spike_extreme.png]]

The book's **Figure 11.13** (March 1994 soybean oil) shows a spike high being penetrated four months later, leading to a strong upside extension; **Figure 11.14** (March 1992 cotton) shows the same with a downside spike.

## Common-life analogy

A friend swears off chocolate after a particularly brutal sugar crash. The crash is the spike — sharp, painful, defining. For weeks they don't go near the candy aisle. If three months later you spot them not just buying chocolate but eating two bars in a row at lunch, the original "I'm done with chocolate" moment didn't take — and you can bet the chocolate streak will run a while.

## Numeric example

Stock prints a spike high on **June 1**: high $84.00 (vs $76 the day before, $74 the day after), close $74.50 (near the low). Four months later:

| Day | Close | Above $84? |
|-----|-------|-----------|
| Oct 1 | 81.50 | no |
| Oct 7 | 83.90 | no |
| Oct 8 | 84.60 | **yes** ← failed-signal trigger |

Long entry on close at $84.60. Stop just below the lows of the consolidation that built up before the breakout — say $80. Risk = $4.60. The "negation" rule says: if a future close drops below the spike-day's low ($73.00), abandon the trade — the failure has itself failed.

## Python sketch

```python
def find_spikes(df, k=1.5):
    """Spike high: high > prior + k*range AND > next + k*range, close in lower 40%."""
    rng = df["high"] - df["low"]
    spikes = []
    for i in range(1, len(df) - 1):
        if (df["high"].iloc[i] > df["high"].iloc[i-1] + k * rng.iloc[i-1] and
            df["high"].iloc[i] > df["high"].iloc[i+1] + k * rng.iloc[i+1] and
            df["close"].iloc[i] < df["low"].iloc[i] + 0.4 * rng.iloc[i]):
            spikes.append(("high", i, df["high"].iloc[i]))
    return spikes

def spike_failed(df, spikes, min_age=20):
    """Return (spike_idx, fail_idx) when a close passes the spike extreme."""
    for kind, i, level in spikes:
        for j in range(i + min_age, len(df)):
            if kind == "high" and df["close"].iloc[j] > level:
                yield i, j; break
```

Full version in `code/chapter11_detectors.py`.

## Relationships within the chapter

- One of the **single-bar pattern failures** alongside [[07 Return to Wide-Ranging Day Extremes]] — both transform a one-day climax bar into a failed signal when its extreme is later violated.
- Uses [[03 Confirmation Conditions]] (close beyond the spike level).
- Schwager warns about a **"failed failed signal"** — a penetration that itself reverses (his Figure 11.15 example). The negation rule (close beyond the *opposite* extreme of the spike) handles this — same defensive idea as the invalidation conditions for [[02 Bull and Bear Traps]].

## When the concept works best

- **Months between the spike and the test.** A spike re-tested next week is not yet a failure; the market simply hasn't had time to respect it.
- **Spikes that are extreme in magnitude.** A $1 spike on a $50 stock is mostly noise; a $10 spike is a structural feature whose violation matters.
- **Spikes that occurred at clean, well-defined market turns** rather than mid-trend.

## Relationships outside the chapter

- Spike anatomy and the conditions that make a spike "high quality" are in [[Chapter 5 - Chart Patterns]] (one-day pattern section).
- Spike highs and lows are also frequent **stop-placement reference points** — see [[Chapter 9 - Stop Loss Points]].
- The interaction "spike → reversal → re-test → failure" is a small worked example in [[Chapter 12 - Real World Chart Analysis]].
