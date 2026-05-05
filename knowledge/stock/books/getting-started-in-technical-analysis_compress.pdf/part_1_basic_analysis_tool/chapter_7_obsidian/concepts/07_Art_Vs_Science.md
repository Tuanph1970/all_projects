---
concept: "Chart Analysis as Art"
chapter: 7
order: 7
tags: [art-vs-science, discretionary, judgement, synthesis, chapter-7]
source: "Schwager, Ch. 7, pp. 124-126 (Conclusion)"
---

# 7. Chart Analysis as an Art (vs. Mechanical Science)

## Definition

Schwager closes Chapter 7 with the conclusion that ties the previous five concepts together: **chart analysis is an art, not a science**. The "art" framing means:

- Chart analysis cannot be reduced to a fixed set of rules that any trader can follow mechanically and expect to profit.
- The viability of chart analysis depends on the **individual trader's skill, experience, and ability to synthesise** the various inputs (charts at multiple timeframes, fundamentals, risk control, signal confirmation, failed-signal recognition).
- This is precisely why chart analysis **survives publicity**: textbooks can transmit the rules, but they cannot transmit the synthesis. The mechanical signal degrades; the discretionary practitioner does not.

Schwager's exact framing:

> The skill and subjectivity implied in this approach place chart analysis in the realm of an art that cannot be mimicked by merely following a set of textbook rules. (p. 124)

And:

> It would be unreasonable to expect to play the violin well without some degree of practice and innate talent. Chart analysis is no different. (p. 126)

This concept is the chapter's **conclusion** — and arguably the entire book's thesis.

## Simple Analogy

Chart analysis is like **cooking**. Anyone can read a recipe (the textbook patterns). The recipe is identical for everyone. Yet a hundred home cooks following the same recipe produce a hundred different dishes — some excellent, most mediocre, a few inedible. The variance comes from skill that the recipe cannot encode: knife technique, sense of timing, knowing when the onions are *truly* caramelised, when to deviate from the recipe because tonight's tomatoes are unusually ripe. The mechanical recipe-follower cooks fine the first time. The chef cooks better every year. Charts work the same way.

## Chart Illustration

![[07_art_vs_science.png]]
*The same price series interpreted two ways. Left: every moving-average crossover taken mechanically — many false signals. Right: a discretionary read — a hand-drawn trend line and a recognition that a flag is forming. Same data, different conclusions, different P&L.*

## Real Numeric Example — three traders, same chart

Take the September 1992 Eurodollar series and apply three different "personalities":

| Trader profile | Concepts applied | # Trades | Wins | Net (USD/contract) |
|---|---|---|---|---|
| **A. Mechanical novice** | Take every breakout, no stops | 3 | 1 | uncertain (could be huge loss) |
| **B. Disciplined rule-follower** | Breakouts + risk control | 3 | 1 | +$2,913 |
| **C. Skilled chartist** | Breakouts + risk control + multi-timeframe + fundamentals + reverses on failures | 2 long + 1 short-reversal | 2-3 | ~+$8,000+ |

The data are the same. The difference between Trader B and Trader C is not knowledge of *patterns* — it is **synthesis**. Trader C did not know more rules; they knew when each rule applied and when to override it. That is what Schwager calls art.

The corollary is uncomfortable: there is **no path** from B to C that runs purely through more reading. The path runs through **screen time, journaling, mistakes, and reflection** — the same way violin proficiency runs through practice, not theory.

## Code

```python
# This concept resists code in a way the others did not — that is the point.
# The best we can do is implement the *rule-based* portion that Trader B uses,
# and tag the trades that Trader C would have ALSO modified discretionarily.

def trader_b_pipeline(df):
    """Pure rules: every breakout taken, stops at midpoint."""
    return simulate_breakout_strategy(df, lookback=30)

def trader_c_pipeline(df, weekly_bias=+1, fundamental_bias=+1):
    """Rules + filters + reversals on failures.
       The 'reversal on failure' step is partially encoded but in practice
       requires real-time judgement — multiple valid entries; the chosen one
       depends on the trader's read."""
    breakouts = simulate_breakout_strategy(df, lookback=30)
    breakouts = filter_by_fundamental(breakouts, fundamental_bias)  # bias filter
    breakouts = [t for t in breakouts if t.direction == weekly_bias] # context filter
    failures  = detect_failed_breakouts(df, lookback=30, fail_window=20)
    # ↑ The decision of which failures to act on, and how aggressively, is
    #   the discretionary part — no closed-form rule.
    return breakouts, failures
```

The honest comment in the code — *"the decision of which failures to act on... is the discretionary part — no closed-form rule"* — is the entire concept in a sentence. Full source: [[ch7_master.py]]

## Relationships

### Within Chapter 7
- **Synthesises [[02_Risk_Control]] + [[03_Confirmation_Conditions]] + [[04_Patterns_In_Context]] + [[05_Knowledge_Of_Fundamentals]] + [[06_Failed_Signals]]:** none of these five tools alone makes a trader. The art is knowing *which subset to apply when* and how each tool's output should weight against the others.
- **Reframes [[01_Skepticism_Problem]]:** the skeptic's argument ("publicity destroys edge") is correct *for the rules* and incorrect *for the synthesis*. Concept #7 is why those two views can both be true.

### Outside Chapter 7
- [[Preface]] — Schwager's opening: *"I am supplying the tools, but not the architectural design — that is left to the individual reader."* Concept #7 is the formal statement of that disclaimer.
- [[Chapter_1_Charts_Forecasting_Or_Folklore]] — the Random-Walker / Chartist debate is unresolvable precisely *because* charting is an art; it cannot be tested as a mechanical rule.
- [[Chapter_12_Real_World_Charts]] — 19 case studies of Schwager's actual trades. The chapter is structured as "Trade Entry Reasons → Trade Exit → Comment" — the **Comment** section is where the art lives.
- [[Chapter_15_Testing_Optimizing_Systems]] — paradoxical relationship: Schwager spends a chapter on rigorous statistical testing of trading systems. The takeaway from Ch. 15 (*"the value of parameter optimization is far overstated"*) is consistent with Ch. 7 §7: rules alone are insufficient.
- [[Chapter_18_Market_Wizdom]] — every Market Wizard interviewed describes their edge as some form of synthesis, intuition, or pattern recognition that cannot be fully verbalised.
- **Outside the book:** Daniel Kahneman's distinction between *expert intuition* (valid in domains with rapid feedback) and *pseudo-expertise* (in random domains) — Schwager's "art" is the former. Tetlock's *superforecasters* show similar non-mechanical synthesis.

### When does the "art" framing matter most?
| Situation | Why the art framing matters |
|---|---|
| Beginner thinks they can buy a system and retire | ❌ Concept #7 is the warning they need |
| Skilled trader doubts themselves after a losing month | ✅ Concept #7 reframes their edge as durable, not mechanical |
| Researcher claims to have "back-tested" chart analysis and found no edge | ⚠️ The back-test could only have tested the rule-based subset — not the art |
| Hedge fund attempts to systemise a discretionary trader | ⚠️ Possible but fragile; the art is hard to extract |

### What CAN be transmitted vs. what CANNOT

| Transmittable (textbook can teach) | Non-transmittable (only experience teaches) |
|---|---|
| Pattern definitions | Which pattern matters most *right now* |
| Stop-placement rules | When to honour vs. widen the stop |
| Confirmation rules | Choice of confirmation parameter for *this* market |
| List of failed signals | Recognition of a failed signal in real time, before it's obvious |
| Multi-timeframe procedure | Knowing which timeframe is the "true" one this week |
| Fundamentals as filter | Forecast accuracy itself — separate skill |

The right-hand column is the moat. It cannot be photocopied. That is why chart analysis is still valid.

## The chapter's final line (paraphrased)

Chart analysis remains a highly individualistic approach. Success or failure depends on the trader's skill and experience. Expecting to play the violin well without practice and innate talent would be unreasonable; chart analysis is no different.

---

**Source:** Schwager (1999), Ch. 7, pp. 124-126, Conclusion section.
**Tags:** #art-vs-science #discretionary-trading #synthesis #judgement #chapter-7 #conclusion
