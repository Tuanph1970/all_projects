# 12 — Expected Gain per Trade

## Definition

**Expected gain per trade** is the average profit (or loss) you would expect to earn on a single random trade drawn from a strategy's distribution of outcomes. The formula is:

> **E = (win_rate × avg_win) − ((1 − win_rate) × avg_loss)**

Schwager uses it in Figure 12.9 to make a counter-intuitive point: **a strategy can be profitable even with a win rate well below 50%**, provided the average win is much larger than the average loss. The flag-near-range-extreme pattern is his example — a setup whose successful trades capture entire downswings while its failures invalidate quickly with small losses. Conversely, **a strategy with a 70% win rate can lose money** if losses are large relative to wins.

The lesson: stop optimizing for "percent winners." Optimize for E.

## Illustration

![[12_expected_gain.png]]

Two systems compared side by side. System A wins 70% of the time but pays −3 on losses for every +1 on wins — net E = −0.20. System B wins only 35% of the time but pays +5 on wins for every −1 on losses — net E = +1.10. **The lower win rate wins.**

## Analogy

A vending machine that gives you back $1 nine times out of ten and takes $20 the tenth time is a worse deal than a vending machine that gives you back $20 once in five tries and charges $1 the other four. People feel "wins" emotionally — most paychecks make us happier than the few losses make us sad — but the machine doesn't care about our feelings, only about the arithmetic. Trading systems work the same way: the chart pattern is the vending machine, and only its long-run arithmetic determines your account.

## Numeric Example

Schwager's Figure 12.9 setup — flag near low end of a broad trading range, sell on flag breakdown:

| Outcome | Probability | Average size | Contribution |
|---|---|---|---|
| Pattern works (full downswing) | 35% | +5R | +1.75R |
| Pattern fails (small upside break) | 65% | −1R | −0.65R |
| **Expected gain per trade** | | | **+1.10R** |

Even though the pattern is *wrong* almost two times out of three, every random trade contributes +1.10R on average. After 100 trades that's +110R — a substantial outcome.

Compare to a "high-quality" 70% win-rate strategy with sloppy risk control:

| Outcome | Probability | Average size | Contribution |
|---|---|---|---|
| Win | 70% | +1R | +0.70R |
| Loss (un-controlled) | 30% | −3R | −0.90R |
| **Expected gain per trade** | | | **−0.20R** |

The "winning" system bleeds.

## Python

```python
from chapter12_concepts import expected_gain_per_trade

# Schwager's flag-near-range-extreme example
e_flag = expected_gain_per_trade(win_rate=0.35, avg_win=5.0, avg_loss=1.0)
print(f"Flag-near-extreme  E = {e_flag:+.2f}R per trade")  # +1.10R

# Counterexample: high win rate but bad risk control
e_sloppy = expected_gain_per_trade(win_rate=0.70, avg_win=1.0, avg_loss=3.0)
print(f"High-WR, bad risk  E = {e_sloppy:+.2f}R per trade")  # -0.20R

# Sensitivity scan: required win rate to break even at various R:R
print("\nBreak-even win rates:")
for rr in [1.0, 2.0, 3.0, 5.0]:
    # E = 0  →  p = avg_loss / (avg_win + avg_loss)
    # With avg_win = rr, avg_loss = 1:
    p_be = 1.0 / (rr + 1.0)
    print(f"  R:R = 1:{rr:.0f}  →  break-even win rate = {p_be:.1%}")
# 1:1 → 50.0%, 1:2 → 33.3%, 1:3 → 25.0%, 1:5 → 16.7%
```

## Relationships

### Within Chapter 12

- **[[01_Primary_Premise_Violation]]** — premise discipline is what *makes* the avg_loss small. Without it, asymmetry collapses.
- **[[03_Stop_Placement_Quality]]** — too-tight stops raise loss frequency without proportionally improving avg_loss; too-loose stops do the opposite. Both shift E.
- **[[07_Flag_and_Pennant_Continuation]]** — Schwager's specific example pattern: small loss when wrong, large win when right.
- **[[10_Trailing_Stop]]** — trails preserve avg_win by letting trends run, materially improving E.
- **All the failed-signal trades** (bull/bear traps, counter-to-anticipated breakouts) inherit this asymmetry by construction.

### When does the principle work best?

This is not a *pattern* but a *framework* — it applies universally. It is **most useful** for evaluating systems that:
- Produce few but high-magnitude winners (trend-following).
- Look "bad" by win-rate but reward asymmetric setups.
- Are being compared against alternatives with different win/loss profiles.

It is **least informative** when avg_win and avg_loss have very high variance — in those cases, additional measures like the standard deviation of trade outcomes, max drawdown, and the Sharpe ratio matter as much as E itself.

### Outside the chapter

- **Chapter 14 — Trading Systems Structure.** Schwager evaluates trend-following systems primarily by return/risk metrics — E is the simplest such metric.
- **Chapter 15 — Testing and Optimizing.** Average parameter set performance is measured in expected return; the chapter warns against over-fitting to win rate.
- **Chapter 17 — 82 Trading Rules.** Several rules — "cut losses short, let profits run," "the average win should be larger than the average loss" — are direct verbal restatements of optimizing E.
- **External — Kelly Criterion.** The optimal bet size given E and the win/loss distribution; conceptually downstream of expected gain.

## Source

- Schwager, *Getting Started in Technical Analysis*, Ch. 12, Figure 12.9 (p. 197–198)
- Background: Ch. 14, 15, 17 — system evaluation, optimization, trading rules
- Code: [`chapter12_concepts.py → expected_gain_per_trade()`](code/chapter12_concepts.py)
- Image: [`12_expected_gain.png`](images/12_expected_gain.png)
