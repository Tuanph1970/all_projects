---
tags: [technical-analysis, schwager, chapter-7, risk-control, money-management, expected-value]
chapter: 7
concept: 1
title: "Risk Control and Win Rate vs Profitability"
related: [confirmation-conditions, stop-loss, trading-ranges, failed-signals]
status: deep-dive-complete
---

# Risk Control and Win Rate vs Profitability

## Definition

Trading success does **not** require being right more than half the time. What matters is that losses on losing trades are **rigidly controlled** while profitable trades are **permitted to run their course**. A trader can be wrong on the majority of trades and still achieve a large net profit — as long as the average win is substantially larger than the average loss.

This is the **foundational reason** Schwager gives for why chart analysis remains valid despite widespread knowledge of patterns.

## Schwager's Own Words

> *"Trading success does not depend on being right more than half the time, or for that matter, even half the time, as long as losses are rigidly controlled and profitable trades are permitted to run their course."*  
> — Chapter 7, p.120

> *"A chart pattern does not need to be right more than 50% of the time — or, for that matter, even close to 50% of the time — to be valuable."*  
> — Chapter 12, p.198 (September 1994 Silver trade commentary)

> *"The success rate of trades is the least important performance statistic and may even be inversely related to performance."*  
> — Chapter 18, quoting Bill Eckhardt

> *"It never bothered me to lose, because I always knew I would make it right back."*  
> — Chapter 18, quoting Linda Raschke

## Analogy — The Venture Capital Portfolio

Think of trading like a venture capital fund. A VC expects **most investments to fail** — maybe 7 out of 10 startups go to zero. But the 2–3 winners return 10x or 50x, more than covering all the losses. The VC doesn't need a >50% success rate; they need **asymmetric payoffs** — small losses on failures, massive gains on successes.

In software terms: it's like running A/B tests. Most experiments show no improvement (you "lose" the time invested). But the ones that work deliver outsized value. The key is to **kill failing experiments quickly** (small loss = tight stop) and **scale the winners aggressively** (let profits run).

## Schwager's Eurodollar Example — Step by Step

September 1992 Eurodollar futures. A trader in March 1991 identifies a trading range and decides to trade in the direction of any closing breakout, placing stops at the **midpoint** of the range.

| Step | What Happened | Result | Cumulative |
|------|---------------|--------|------------|
| **Setup** | Trading range identified (Fig 7.1) | — | $0 |
| **Trade 1** | March sell breakout → false breakout → stopped at midpoint | **-$500** | -$500 |
| **Adjust** | Range redefined (widened) after false breakout | — | -$500 |
| **Trade 2** | May sell breakout → another false breakout → stopped | **-$500** | -$1,000 |
| **Adjust** | Range widened again | — | -$1,000 |
| **Trade 3** | Buy breakout → **real breakout** → major price advance | **+$3,000** | +$2,000 |

**Win rate: 33%** — two out of three trades were losers.  
**Net result: +$2,000** — the single winner far exceeded both losses combined.

### Critical Mechanics That Made This Work

1. **Stops at the midpoint** — not at the edge (too tight, too many false stops) and not beyond the range (too much risk)
2. **Range redefined after each false breakout** — the system adapts, it doesn't stubbornly repeat
3. **No revenge trading** — same position size on trade 3 as trade 1
4. **Profits allowed to run** — no premature exit on trade 3

## The Expected Value Formula

From Chapter 12 (p.198), Schwager provides the formula explicitly:

```
Expected Gain Per Trade = (Win% × Avg Win) - (Loss% × Avg Loss)
```

### Worked Examples

| Win Rate | Avg Win | Avg Loss | R:R Ratio | EV/Trade | Profitable? |
|----------|---------|----------|-----------|----------|-------------|
| 33% | $3,000 | $500 | 6:1 | **+$655** | Yes |
| 40% | $2,000 | $800 | 2.5:1 | **+$320** | Yes |
| 50% | $1,000 | $1,000 | 1:1 | **$0** | Breakeven |
| 60% | $500 | $1,200 | 0.4:1 | **-$180** | No — despite 60% wins! |
| 25% | $5,000 | $500 | 10:1 | **+$875** | Yes — despite 75% losses! |

The fourth row is the trap most traders fall into: high win rate with poor risk management (cutting winners, letting losers run) produces net losses. The fifth row is the trend-follower's reality: many small losses, rare huge wins.

### Breakeven Win Rate

The minimum win rate needed to break even:

```
Breakeven Win Rate = Avg Loss / (Avg Win + Avg Loss)
```

With R:R of 6:1 → breakeven at **14.3%**. The Eurodollar system only needs to be right 1 time in 7 to survive.

## The Asymmetry Principle

The entire concept rests on **structural asymmetry** between wins and losses:

```
Losses are BOUNDED by your stop
Wins are UNBOUNDED (you let them run)
```

This asymmetry is created by two trading disciplines:

1. **Stop-losses** — define your maximum loss per trade BEFORE entry (Ch 9)
2. **No premature profit-taking** — don't exit winners just because you're up (Ch 10, Rule #31)

Schwager reinforces this in Chapter 16 with concrete guidelines:
- Maximum risk per trade should be **3% or less** of total equity
- Traders risking more than **7%** per trade should reconsider their suitability for trading

## Schwager's Three-Part Framework from Chapter 18

Bill Eckhardt's observation (Ch 18, Rule #27):

> *"Human nature does not operate to maximize gain but rather the chance of a gain."*

This means our instincts push us toward:
- **Taking small profits quickly** (feels good, high win rate)
- **Holding losing positions** (avoids admitting we were wrong)

Both behaviors **destroy the asymmetry** that makes this concept work. The discipline required is to do the opposite of what feels natural: cut losses fast, let winners run.

## Python Implementation

```python
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional


@dataclass
class TradeResult:
    """Single trade outcome."""
    entry_date: str
    exit_date: str
    direction: str       # 'long' or 'short'
    entry_price: float
    exit_price: float
    stop_price: float
    pnl: float
    is_winner: bool
    exit_reason: str     # 'stop', 'target', 'trailing_stop', 'signal_reversal'


def calculate_expected_value(
    win_rate: float,
    avg_win: float,
    avg_loss: float
) -> dict:
    """
    Calculate expected value per trade given win rate and
    average win/loss sizes.
    
    Demonstrates Schwager's Ch7 insight: win rate alone
    doesn't determine profitability.
    
    Parameters
    ----------
    win_rate : float
        Fraction of trades that are winners (0.0 to 1.0)
    avg_win : float
        Average dollar gain on winning trades
    avg_loss : float
        Average dollar loss on losing trades (positive number)
    
    Returns
    -------
    dict with expected_value, profit_factor, breakeven_win_rate,
         reward_risk_ratio
    
    Example
    -------
    >>> ev = calculate_expected_value(0.33, 3000, 500)
    >>> ev['expected_value']
    655.0
    >>> ev['breakeven_win_rate']
    0.1429
    """
    loss_rate = 1.0 - win_rate
    expected_value = (win_rate * avg_win) - (loss_rate * avg_loss)
    
    gross_profit = win_rate * avg_win
    gross_loss = loss_rate * avg_loss
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    
    breakeven_win_rate = avg_loss / (avg_win + avg_loss)
    
    return {
        'expected_value': round(expected_value, 2),
        'profit_factor': round(profit_factor, 2),
        'breakeven_win_rate': round(breakeven_win_rate, 4),
        'win_rate': win_rate,
        'reward_risk_ratio': round(avg_win / avg_loss, 2) if avg_loss > 0 else float('inf')
    }


def simulate_trade_sequence(
    trades: list[dict],
    initial_capital: float = 100000.0
) -> dict:
    """
    Simulate a sequence of trades to demonstrate that
    win rate != profitability.
    
    Parameters
    ----------
    trades : list of dict
        Each dict has 'result' (float, positive=win, negative=loss)
        and optional 'label' (str)
    initial_capital : float
        Starting account equity
    
    Returns
    -------
    dict with equity_curve, win_rate, net_pnl, max_drawdown,
         avg_win, avg_loss, reward_risk_ratio
    """
    equity = initial_capital
    equity_curve = [equity]
    peak = equity
    max_drawdown = 0
    wins = 0
    win_amounts = []
    loss_amounts = []
    
    for trade in trades:
        pnl = trade['result']
        equity += pnl
        equity_curve.append(equity)
        
        if pnl > 0:
            wins += 1
            win_amounts.append(pnl)
        elif pnl < 0:
            loss_amounts.append(abs(pnl))
        
        if equity > peak:
            peak = equity
        drawdown = (peak - equity) / peak if peak > 0 else 0
        max_drawdown = max(max_drawdown, drawdown)
    
    n_trades = len(trades)
    win_rate = wins / n_trades if n_trades > 0 else 0
    avg_win = np.mean(win_amounts) if win_amounts else 0
    avg_loss = np.mean(loss_amounts) if loss_amounts else 0
    
    return {
        'equity_curve': equity_curve,
        'win_rate': round(win_rate, 4),
        'net_pnl': round(equity - initial_capital, 2),
        'max_drawdown': round(max_drawdown, 4),
        'final_equity': round(equity, 2),
        'n_trades': n_trades,
        'avg_win': round(avg_win, 2),
        'avg_loss': round(avg_loss, 2),
        'reward_risk_ratio': round(avg_win / avg_loss, 2) if avg_loss > 0 else float('inf')
    }


def position_size_from_risk(
    account_equity: float,
    max_risk_pct: float,
    entry_price: float,
    stop_price: float,
    point_value: float = 1.0
) -> int:
    """
    Calculate position size given Schwager's risk control rules.
    
    From Chapter 16: max risk per trade should be 3% or less
    of total equity. Above 7% → reconsider trading suitability.
    
    Parameters
    ----------
    account_equity : float
        Current account value
    max_risk_pct : float
        Maximum risk as fraction (e.g., 0.03 for 3%)
    entry_price : float
        Planned entry price
    stop_price : float
        Planned stop-loss price
    point_value : float
        Dollar value per point of price movement
        (1.0 for stocks, varies for futures)
    
    Returns
    -------
    int : maximum number of shares/contracts
    
    Example
    -------
    >>> position_size_from_risk(100000, 0.03, 50.0, 45.0)
    600  # $3,000 risk / $5 per share = 600 shares
    """
    max_risk_dollars = account_equity * max_risk_pct
    risk_per_unit = abs(entry_price - stop_price) * point_value
    
    if risk_per_unit <= 0:
        return 0
    
    return int(max_risk_dollars / risk_per_unit)


# === Schwager's Eurodollar example ===
if __name__ == "__main__":
    eurodollar_trades = [
        {'result': -500, 'label': 'Trade 1: March sell breakout (false)'},
        {'result': -500, 'label': 'Trade 2: May sell breakout (false)'},
        {'result': 3000, 'label': 'Trade 3: Buy breakout (real)'},
    ]
    
    result = simulate_trade_sequence(eurodollar_trades)
    print("=== Schwager's Eurodollar Example ===")
    print(f"  Win rate:      {result['win_rate']:.0%}")
    print(f"  Net P&L:       ${result['net_pnl']:,.2f}")
    print(f"  Max drawdown:  {result['max_drawdown']:.2%}")
    print(f"  Avg win:       ${result['avg_win']:,.2f}")
    print(f"  Avg loss:      ${result['avg_loss']:,.2f}")
    print(f"  R:R ratio:     {result['reward_risk_ratio']:.1f}:1")
    
    print("\n=== Expected Value at Different Win Rates ===")
    print(f"{'Win%':>6} {'AvgWin':>8} {'AvgLoss':>8} {'EV/Trade':>10} {'BkEven':>8} {'R:R':>6}")
    for wr in [0.25, 0.33, 0.40, 0.50, 0.60]:
        ev = calculate_expected_value(wr, avg_win=3000, avg_loss=500)
        print(f"{wr:>6.0%} {'$3,000':>8} {'$500':>8} "
              f"${ev['expected_value']:>9,.2f} "
              f"{ev['breakeven_win_rate']:>7.1%} "
              f"{ev['reward_risk_ratio']:>5.1f}:1")
    
    print("\n=== Position Sizing (Ch16 Rules) ===")
    equity = 100000
    for risk_pct in [0.01, 0.02, 0.03, 0.05]:
        size = position_size_from_risk(equity, risk_pct, 50.0, 45.0)
        print(f"  {risk_pct:.0%} risk on $100K, $5 stop → {size} shares")
```

## When This Concept Works Best

- **Trend-following strategies** — most trades get stopped out, but occasional big trends pay for everything
- **Breakout trading** — false breakouts are frequent but real ones produce large moves
- **Any approach with defined stop-losses** — losses are bounded while wins are open-ended
- **Portfolio-level thinking** — even if individual patterns have low accuracy, the system profits overall
- **Flag/pennant trading** — Schwager specifically notes (Ch 12, p.198): "when wrong, evidence of failure is provided quickly" but "when right, it can capture a major downswing"

## When It Doesn't Work

- **If you don't use stops** — one losing trade can wipe out many winners
- **If you take profits too early** — eliminates the asymmetry you need
- **If you increase position size on losers** ("averaging down") — violates the bounded-loss requirement
- **If you use reward:risk < 1** — you need >50% win rate just to break even, and most chart patterns don't deliver that
- **Psychologically** — requires accepting that most trades will lose, which goes against human nature (Eckhardt's point)

## Comparison: Schwager vs. Textbook Expectation

| Aspect | Textbook Expectation | Schwager's Reality |
|--------|---------------------|--------------------|
| Good win rate | >50% | Irrelevant — even 25% can work |
| Focus metric | % of winning trades | Expected value per trade |
| What makes a system good | High accuracy | Asymmetric payoffs |
| Natural human behavior | Matches winning | Actively works against you |
| Role of losses | Evidence of failure | Cost of doing business |

## Links

### Inside This Chapter
- [[Ch7 - Is Chart Analysis Still Valid (MOC)]]
- [[Ch7 - Confirmation Conditions]] — Reduces false signals, improving the win/loss ratio
- [[Ch7 - Multi-Timeframe Analysis]] — Context reduces the number of wrong-side trades
- [[Ch7 - Fundamental-Technical Synthesis]] — Another filter to improve trade quality
- [[Ch7 - Using Failed Signals as Trading Indicators]] — Turns losers into new high-probability entries

### Inside the Book (Earlier Chapters)
- [[Ch3 - Trends]] — Where stops are placed relative to trend lines
- [[Ch4 - Trading Ranges and Support and Resistance]] — Trading range midpoint as stop placement
- [[Ch5 - Chart Patterns]] — The patterns generating the signals; flags/pennants as asymmetric setups

### Inside the Book (Later Chapters)
- Chapter 9 — Choosing Stop-Loss Points (detailed mechanics of risk control)
- Chapter 10 — Setting Objectives / Position Exit (how to let winners run)
- Chapter 12 — Real-World Chart Analysis: Silver trade (p.198) with expected gain formula
- Chapter 16 — The Planned Trading Approach: max 3% risk per trade, position sizing
- Chapter 17 — Rule #31: "Do not take small, quick profits in major position trades"
- Chapter 18 — Rule #9: Money management more important than method
- Chapter 18 — Rule #15: "Losing is part of the game"
- Chapter 18 — Rule #27: "Maximize gains, not the number of wins" (Eckhardt)
