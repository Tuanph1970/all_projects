---
concept: "Using Failed Signals"
chapter: 7
order: 6
tags: [failed-signals, contrarian, false-breakout, chapter-7]
source: "Schwager, Ch. 7, p. 124 (introduced); Ch. 11 (developed)"
---

# 6. Using Failed Signals

## Definition

A **failed signal** is when a market generates a textbook chart signal (e.g., an upside breakout) and then **fails to follow through** — instead reversing back through the level that created the signal. Schwager argues this *failure to follow through* is itself one of the most reliable trading signals available, often **more reliable than the original pattern**.

The trader's response to a failed signal is therefore not just to exit the original trade but to **reverse direction** — go from long to short (or vice versa). The failure becomes the new trade.

Schwager introduces this concept briefly in Chapter 7 (as the fifth answer to skepticism) and develops it across an entire chapter — Chapter 11, *"The Most Important Rule in Chart Analysis"*. The reason failed signals work is closely tied to the publicity argument: as more traders pile into mechanical breakout strategies, false breakouts become more common, which means the failures become more frequent and the contrarian opportunity more valuable.

## Simple Analogy

A failed signal is like **a runner crossing the starting line on a false start**. The textbook says the race has begun — but everyone watches the runners pull up, look around, and shuffle back behind the line. The *false start itself* tells the careful spectator: "Wait, there's tension here. This race isn't ready to begin." The patient bettor who notices what just happened — runners advanced, then retreated — has more information than the bettor who only saw the gun go off.

## Chart Illustration

![[06_failed_signals.png]]
*Yellow shaded zones mark periods where a breakout (red triangle) failed and price returned inside the prior range (green star). Each failure becomes a contrarian trade signal in the opposite direction.*

## Real Numeric Example — Eurodollar failed-signal events

Running the failed-signal detector on the same Eurodollar series produces 5 distinct events:

| Signal date | Signal direction | Failed by | Days to fail | Contrarian direction |
|---|---|---|---|---|
| 1991-05-03 | Up | 1991-05-06 | 3 | Short |
| 1991-08-12 | Down | 1991-08-14 | 2 | Long |
| 1991-10-16 | Up | 1991-10-17 | 1 | Short |
| 1991-12-13 | Up | 1991-12-18 | 5 | Short |
| 1992-02-10 | Up | 1992-02-12 | 2 | Short |

Looking at the second event in particular — the August 1991 failed *downside* breakout — turning around and going long would have caught a portion of the major rally that began later that autumn. This is the high-conviction setup Schwager describes:

> The novice trader will ignore a failed signal, riding a position into a large loss while hoping for the best. The more experienced trader will exit quickly. But the *truly skilled* trader will be able to do a 180-degree turn, reversing a position at a loss if market behaviour points to such a course of action. (Ch. 11, p. 177)

The contrarian P&L from the August 1991 long reversal alone, held until the third trade's stop hit, would have been roughly **+1.8 points = +$4,500 per contract** — comparable to the entire net result of the unfiltered breakout strategy.

## Code

```python
def detect_failed_breakouts(df, lookback=30, fail_window=20):
    """Find breakouts that close back inside the prior range within
       fail_window days. Each failure is a contrarian signal."""
    failures, i = [], lookback
    while i < len(df):
        win = df.iloc[i-lookback:i]
        hi, lo = win["high"].max(), win["low"].min()
        c = df["close"].iat[i]
        for direction, level in [(+1, hi), (-1, lo)]:
            if (direction == +1 and c > hi) or (direction == -1 and c < lo):
                for j in range(i+1, min(i+1+fail_window, len(df))):
                    cj = df["close"].iat[j]
                    failed = ((direction == +1 and cj < hi) or
                              (direction == -1 and cj > lo))
                    if failed:
                        failures.append(dict(
                            signal_idx=i, signal_dir=direction,
                            fail_idx=j, contrarian_dir=-direction,
                        ))
                        i = j
                        break
                break
        i += 1
    return failures
```

Full source: [[ch7_master.py]]

## Relationships

### Within Chapter 7
- **Inverts [[01_Skepticism_Problem]]:** the skeptic says publicity destroys edge. Failed signals show how publicity *creates* a new edge — the more crowded the original signal, the more profitable its failures become.
- **Requires [[02_Risk_Control]]:** to reverse on a failure, you must first have survived the original loss. Tight stops are the precondition.
- **Contrasts with [[03_Confirmation_Conditions]]:** confirmation refuses to enter until the signal proves itself. Failed signals enter precisely when the signal *disproves* itself.
- **Strongest when combined with [[04_Patterns_In_Context]]:** a failure that runs counter to the long-term trend is suspect; a failure that runs *with* it is high-conviction.
- **Demands [[07_Art_Vs_Science]]:** reversing on a loss requires emotional discipline and judgement that no mechanical rule can encode well.

### Outside Chapter 7
- **[[Chapter_11_Most_Important_Rule]]** — Schwager devotes an entire chapter to failed signals, calling them collectively "the most important rule in chart analysis." Categories developed in Ch. 11:
  - Bull traps and bear traps (failed breakouts)
  - Failed head-and-shoulders patterns (penetration of recent shoulder)
  - Counter-to-anticipated breakouts of flags and pennants
  - Penetration of wide-ranging days
  - Breaking of curvature in rounding patterns
- [[Chapter_4_Trading_Ranges]] — the original trading-range breakouts whose failures Concept #6 trades.
- [[Chapter_5_Chart_Patterns]] — flags, H&S, and rounding patterns are the most common patterns that fail.
- [[Chapter_12_Real_World_Charts]] — many of the 19 trade case studies use failed signals as either entry or reversal triggers.
- **Outside the book:** Tom DeMark's "TD Sequential", VSA (Volume Spread Analysis) "no demand / no supply" tests, Wyckoff's "spring" and "upthrust" — every framework has a failed-signal concept.

### When do failed signals work well vs. poorly?
| Situation | Effect of trading failed signals |
|---|---|
| Crowded, well-known setup (popular breakout) | ✅ Excellent — false-breakout rate is high |
| Obscure / novel pattern | ❌ Few failures because few traders know to take it |
| Strong fundamental support behind original signal | ❌ Failures are themselves false; original signal eventually wins |
| Range-bound market | ✅ Excellent — failures are constant |
| Strongly trending market | ⚠️ Counter-trend failures usually *do* fail; trade with-trend failures only |
| News-driven move that retraces quickly | ✅ Classic failed-signal setup |

### The publicity-feedback loop

```
More traders use breakout signals
         ↓
Easier to push price beyond range temporarily (stop-running)
         ↓
False-breakout rate rises
         ↓
Failed-signal trade becomes more profitable
         ↓
Smart money increasingly trades the failure, not the original
```

Schwager warns explicitly: *"If the use of failed signals were to become significantly more widespread, however, their long-term reliability could be adversely affected"* (Ch. 11, p. 177). The remedy he proposes is to **make failed signals dynamic** — pegged to whatever the prevailing *conventional wisdom* is at the time. In that recursive form, the concept is timeless.

---

**Source:** Schwager (1999), Ch. 7, p. 124 (introduced); developed extensively in Ch. 11, pp. 152-177.
**Tags:** #failed-signals #contrarian #false-breakout #publicity-feedback #chapter-7
