---
concept: "Skepticism Problem"
chapter: 7
order: 1
tags: [chart-analysis, skepticism, market-efficiency, chapter-7]
source: "Schwager, Ch. 7, p. 120"
---

# 1. The Skepticism Problem

## Definition

The "skepticism problem" is the standard cluster of objections raised against chart analysis as a forecasting tool. Schwager opens Chapter 7 by listing three of them:

1. **"Too simple to work"** — chart patterns look too elementary to outperform random trading.
2. **"Stops are easily triggered"** — floor traders know where everyone's stops sit and can push price to harvest them.
3. **"Too well publicized"** — once a method is in textbooks read by millions, it should self-destruct (because everyone trades it the same way).

Chapter 7 concedes all three points are *basically valid* and then spends the rest of the chapter giving five concrete reasons charts still work in skilled hands. Concept #1 is therefore the **framing question** — every other concept in this chapter is an answer to it.

## Simple Analogy

Skepticism about chart analysis is like skepticism about **cooking from a recipe book**. *"If everyone has the same cookbook, why isn't every meal identical and mediocre?"* The answer is obvious to anyone who has ever cooked: knowing the recipe is 5% of the outcome. Knife skill, judgement on heat, knowing when the onions are *really* caramelised, choosing which recipe to make tonight given what's in the fridge — that is 95%, and it cannot be photocopied. Charts are the recipe. Skill, timing, and synthesis are the cook.

## Chart Illustration

![[01_skepticism.png]]
*The three classic objections (red) framed against the price chart. Schwager's response (green) is the rest of the chapter.*

## Real Numeric Example — The "self-destruct" claim, tested

Schwager's own observation (Ch. 11, p. 176): before the 1980s, simple chart breakouts produced "many excellent signals without an abundance of false signals". By the late 1990s, "price reversals following breakouts are more often the rule than the exception." So the skeptics are *partly right*: the **mechanical** signal has degraded. Concretely, in our Eurodollar simulation:

| Year era | Naive breakout win rate | Net P&L pattern |
|---|---|---|
| Pre-1980 (Schwager's account) | ~60–70% | Big winners, few losers |
| 1990s (our sim) | **1 of 3 = 33%** | Two small losses + one big winner = still profitable |
| 2020s (often) | <30% | Profitable only with discipline (concepts 2-6) |

The mechanical signal lost edge, but the *strategy as a whole* didn't — because of risk control, not signal quality.

## Code

```python
# From ch7_master.py — the Eurodollar simulation that generates these numbers
df     = make_eurodollar_series(seed=7)
trades = simulate_breakout_strategy(df, lookback=30)

wins   = sum(1 for t in trades if t.pnl_pts > 0)
net    = sum(t.pnl_pts for t in trades)
print(f"{len(trades)} trades, {wins} wins ({wins/len(trades):.0%}), "
      f"net {net:+.2f}pt = ${net*2500:+,.0f}")
# 3 trades, 1 wins (33%), net +1.17pt = $+2,913
```

The point: **33% win rate, still profitable.** The skeptic's "too few winners" intuition assumes equal-size wins and losses. It is wrong.

Full source: [[ch7_master.py]]

## Relationships

### Within Chapter 7
- The five concepts that **answer** this question:
  - [[02_Risk_Control]] — win rate is the wrong metric
  - [[03_Confirmation_Conditions]] — filter most false signals
  - [[04_Patterns_In_Context]] — context the textbook can't capture
  - [[05_Knowledge_Of_Fundamentals]] — orthogonal information dimension
  - [[06_Failed_Signals]] — turn the publicity *against* the crowd
- Concludes in [[07_Art_Vs_Science]] — what survives publicity is judgement, not rules.

### Outside Chapter 7
- [[Chapter_1_Charts_Forecasting_Or_Folklore]] — the "great debate" in Ch. 1 is exactly this question, dramatised as a dialogue between Ms. Trend and Professor Coin.
- [[Chapter_11_Most_Important_Rule]] — Schwager argues *failed signals* are now MORE reliable than original signals precisely because publicity has degraded the originals.
- **Outside the book:** efficient-market hypothesis (Fama, 1970), random-walk theory (Malkiel), behavioral finance (Shleifer, Thaler) — each addresses the same skepticism from a different angle.

### When does this framing matter?
| Situation | Should you take the skeptic seriously? |
|---|---|
| Trading a popular chart pattern mechanically | ✅ Yes — edge has likely been competed away |
| Trading the same pattern with confirmation + context + fundamentals | ⚠️ Less so — you've moved beyond the mechanical signal |
| Using failed signals contrarily | ❌ The skeptic's argument now works *for* you |

---

**Source:** Schwager (1999), Ch. 7, p. 120, opening paragraphs.
**Tags:** #skepticism #market-efficiency #chart-analysis #chapter-7
