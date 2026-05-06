# 01 Trading Philosophy

**Step 1 of the Planned Trading Approach** · [[00 Chapter 16 Index]]

![[02_trading_philosophy.svg]]

## Definition

A **trading philosophy** is the explicit, repeatable basis for making trade decisions — the answer to *"How do I decide what to buy and when?"* It must be specific enough that two traders following the same philosophy on the same chart would reach the same conclusion. Vague answers like "gut feeling" or "tips from friends" do not qualify.

The philosophy can rest on:
- Fundamental analysis (earnings, macro, supply/demand)
- Chart analysis (patterns, support/resistance, trends)
- Technical trading systems (mechanical signals)
- Some hybrid of the above, possibly different in different markets

## Easy Analogy

Imagine you're learning to drive in a foreign country and someone asks how you'll handle intersections. *"I'll figure it out when I get there"* gets you killed. *"I'll watch for traffic lights and obey them"* keeps you alive. A philosophy is the rule you commit to BEFORE the situation arises, so the situation doesn't catch you improvising.

Or: a trading philosophy is to a trader what a recipe is to a cook. You can cook without one, but every dish will taste different and you'll never know which version is the keeper.

## Numeric / Concrete Example

A specific philosophy might read:

> **My edge:** Trade breakouts on US large-cap stocks with market cap > $10B and average daily volume > 5M shares.
>
> **Entry:** Daily close above the highest high of the prior 20 trading days.
> **Confirmation:** Close must be at least 2% above the breakout level.
> **Stop:** Below the most recent 10-day low.
> **Exit (winning):** Trail stop below 10-day low; exit on close below trailing stop.
> **Exit (losing):** Hard stop, no exceptions.

Every rule above is testable. There is no ambiguity. That is what "specific philosophy" means.

## Python Code

The whole point of being specific is that the rules can be encoded:

```python
def is_breakout_signal(df, n=20, confirmation_pct=0.02):
    """Returns True on the day a breakout fires."""
    prior_high = df['high'].iloc[-n-1:-1].max()
    today_close = df['close'].iloc[-1]
    return today_close >= prior_high * (1 + confirmation_pct)
```

Compare that to "I'll buy when it feels strong" — there is no function for that.

See [[03_traders_notebook.py]] for how to record which philosophy each trade belongs to.

## Relationships

### Within Chapter 16
- The philosophy chosen here directly drives [[02 Market Selection]] (Step 2): you only trade markets where this philosophy has historical edge.
- It defines what gets logged in the **reason for trade** column of [[12 Traders Notebook]].
- [[14 Personal Trading Analysis]] (Step 7) tests whether the philosophy is actually working — and feeds adjustments back here.

### Outside Chapter 16
- **Chapter 1 — Charts: Forecasting Tool or Folklore?** — establishes whether chart-based philosophies are even valid.
- **Chapter 14 — Technical Trading Systems** — the most rigorous version of a philosophy is a coded system.
- **Chapter 18 — Rule #10 (The Trading Plan)**: Driehaus emphasizes a plan must reflect a *core philosophy* or you won't hold your positions through hard times.

## When This Concept Works Well
- When you have at least one full market cycle (bull + bear) of historical evidence that the approach works.
- When you can write the rules in plain English without using the word "feel".
- When you accept that the philosophy will sometimes lose — you don't abandon it after one bad trade.

## When It Fails
- When traders mix philosophies mid-trade ("I bought on the breakout but I'll hold it because earnings are coming up").
- When the philosophy is built around the last 6 months of data (curve-fit to recent conditions).
