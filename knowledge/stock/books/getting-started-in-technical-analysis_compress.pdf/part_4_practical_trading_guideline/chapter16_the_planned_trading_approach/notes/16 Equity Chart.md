# 16 Equity Chart

**Step 7b — sub-tool of [[14 Personal Trading Analysis]]**

## Definition

An **equity chart** is a price chart of the trader's account balance over time — typically one point per trading day, plotted close-only. It is interpreted using exactly the same techniques the trader applies to any other market: trends, support and resistance, breakouts of key levels, and especially **changes of character**.

The chart serves as an **early-warning system**. Schwager calls out one specific signal as the most important to recognise:

> **A sudden, steep decline following an extended period of climbing equity** is the signal to lighten positions, tighten stops, and reassess.

The signal works because it captures something segmented analysis is slow to catch: a **regime change**. The strategies that built the climb are no longer behaving the same way. Whether the cause is the trader (overconfidence, oversized bets after a winning streak) or the market (volatility regime shift, correlations spiking), the response is the same — defensive posture first, diagnosis second.

## Easy Analogy

The fuel gauge in a car. Drivers don't need to know exactly *why* the fuel is dropping faster than usual on a given trip — headwind, hill climb, dragging brake — they just need to know that something is consuming fuel faster than expected, and that they should pull over and check before they're stranded. The equity chart is the trader's fuel gauge: it shows the rate of consumption without needing to know the cause.

## Numeric / Concrete Example

A trader's equity chart over 12 months:

```
Equity ($)
110k │                              ╭──────╮
     │                          ╭──╯      ╰─╮
105k │                     ╭───╯            ╰─╮
     │                ╭──╯                    ╰─╮  ← steep drop
100k │           ╭──╯                            ╲
     │       ╭──╯                                  ╲___
 95k │   ╭──╯                                        ╲
     │__╯
 90k │
     └─────────────────────────────────────────────────────
       Jan  Feb  Mar  Apr  May  Jun  Jul  Aug  Sep  Oct  Nov
                                              ↑
                                         WARNING TRIGGERED
```

Through October the trader has climbed from $90k to $108k — eight months of consistent equity growth. In early November, equity drops $4k in five days. **This is the signal**, not the absolute level. Even though equity is still well above the start of year, the *pattern* matches Schwager's warning case exactly: extended climb, sudden steep decline.

The disciplined response:

1. **Lighten** — close half the open positions immediately, regardless of where each individual trade stands.
2. **Tighten stops** on remaining positions toward break-even.
3. **No new trades** until the equity chart either resumes its upward slope or the trader has run a full segmented analysis.
4. **Run [[15 Segmented Trade Analysis]]** to identify which strategy or market is driving the new losses.
5. If the analysis identifies a clear culprit, narrow trading to remaining segments. If not, drop to paper trading per [[10 Losing Period Adjustments]].

The trader who ignores the signal and "trades through it" often watches the gentle dip become a 20% drawdown over the next month. The trader who responds early gives up some upside if the signal turns out to be noise — but the cost of that occasional false alarm is far smaller than the cost of one ignored true alarm.

## Python Code

Implemented in [[04_trade_analysis.py]]:

```python
import pandas as pd

def equity_curve(trades, starting_equity):
    """Cumulative equity series indexed by exit date."""
    df = pd.DataFrame(trades).sort_values('exit_date')
    df['equity'] = starting_equity + df['net_pnl'].cumsum()
    return df.set_index('exit_date')['equity']

def drawdown_series(equity):
    """For each point: percentage decline from running peak."""
    peak = equity.cummax()
    return (equity - peak) / peak

def warning_triggered(equity, climb_window=60, drop_window=5,
                      climb_pct=0.05, drop_pct=0.03):
    """Schwager's signal: extended climb followed by a sudden decline."""
    if len(equity) < climb_window + drop_window:
        return False
    pre = equity.iloc[-(climb_window + drop_window):-drop_window]
    recent = equity.iloc[-drop_window:]
    climbed = (pre.iloc[-1] / pre.iloc[0] - 1) >= climb_pct
    dropped = (recent.iloc[-1] / recent.iloc[0] - 1) <= -drop_pct
    return climbed and dropped
```

The thresholds (`climb_pct=5%` over 60 days, `drop_pct=3%` over 5 days) are starting values — every trader should calibrate them to their own typical volatility, since a 3% drop in 5 days is routine for some styles and catastrophic for others.

See [[04_trade_analysis.py]] for the full implementation, including a `plot_equity_chart()` helper that produces the visualisation in `equity_chart_demo.png`.

## Relationships

### Within Chapter 16
- One half of [[14 Personal Trading Analysis]]; the other half is [[15 Segmented Trade Analysis]]. The chart raises the question, the segmentation answers it.
- The trigger that activates [[10 Losing Period Adjustments]] for discretionary traders.
- Consumes daily P&L from [[12 Traders Notebook]]; updated nightly during [[11 Planning Time Routine]].

### Outside Chapter 16
- **Chapters 6–8 — chart reading techniques** — the trader applies the same trend, support, and breakout concepts to their equity chart that they apply to a stock chart. The skills transfer directly.
- **Chapter 15 — Testing Systems** — backtested equity curves are evaluated visually for exactly the same patterns. The tools are symmetric: the test environment evaluates a system, the live equity chart evaluates the trader.
- **Chapter 18 — Rule #11 (Discipline)** — the willingness to act on the signal is ultimately a discipline test, not an analytical one.

## When This Concept Works Well
- When the chart is plotted on a **fixed cadence** — every trading day — and reviewed even when nothing seems wrong. Equity charts are most useful as **noticing tools** during normal periods, not just diagnostic tools during crises.
- When the trader has pre-committed to a specific response (lighten by 50%, etc.) before the signal fires. Without a pre-committed response, the signal triggers a debate, and the debate usually ends with "let's give it one more day".

## When It Fails
- When the trader interprets every dip as a signal — every system has noise, and overreaction is its own form of discipline failure.
- When the chart is drawn but never *examined*, because the trader knows the slope and "doesn't need to look". The act of physically looking at the chart is what catches the change of character.
- When the equity chart is the **only** tool used. Without [[15 Segmented Trade Analysis]] alongside it, the trader knows something is wrong but can't tell what to fix.
