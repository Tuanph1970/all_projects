---
concept: "Risk Control"
chapter: 7
order: 2
tags: [risk-control, money-management, win-rate, expectancy, chapter-7]
source: "Schwager, Ch. 7, pp. 120-122"
---

# 2. Risk Control

## Definition

**Risk control** is the rigid limitation of loss size on every individual trade. Schwager's claim (and the most important argument in Chapter 7):

> Trading success **does not depend on being right more than half the time**, or for that matter, even half the time, as long as losses are rigidly controlled and profitable trades are permitted to run their course.

In other words, profitability is determined by **expected value per trade**, not by the win rate:

$$
\text{Expectancy} = (P_\text{win} \times \text{AvgWin}) - (P_\text{loss} \times \text{AvgLoss})
$$

If the average winner is many times the average loser, you can lose two-thirds of your trades and still print money. Risk control is what *makes the average loss small*.

## Simple Analogy

Risk control is like **fishing with the rule "throw back anything under 12 inches and keep anything over."** You'll throw most fish back. You won't be "right" most of the time. But the few keepers fill the cooler. The bad day is when a fisherman keeps every small fish out of impatience and goes home with a heavy bucket of worthless minnows. Charts give you the bites; risk control is the 12-inch ruler in your pocket.

## Chart Illustration

![[02_risk_control.png]]
*The exact September 1992 Eurodollar narrative from Schwager's Figures 7.1–7.3, recreated. Two losing trades (red) followed by one large winner (green). Win rate 33%; net result still profitable.*

## Real Numeric Example — Eurodollar 1991

Running the simulation from `ch7_master.py` (seed=7) produces the three trades that mirror Schwager's example exactly:

| # | Direction | Entry | Exit | P&L (pts) | P&L (USD)¹ |
|---|---|---|---|---|---|
| 1 | Long  | 1991-05-03 | 1991-06-11 | **−0.50** | −$1,250 |
| 2 | Short | 1991-08-07 | 1991-09-09 | **−0.39** | −$975  |
| 3 | Long  | 1991-10-16 | 1992-02-27 | **+2.05** | **+$5,138** |
| | | | **Net** | **+1.17** | **+$2,913** |

¹ Eurodollar futures: 1 point = $2,500 per contract.

**Win rate = 33%. Net result = +$2,913 per contract.** The single big winner is more than 4× the size of either loser — that asymmetry is what risk control buys you.

### Why the asymmetry?
- The **stop** was placed at the midpoint of the trading range — a small, defined distance from entry → bounded loss.
- The **winning trade had no profit cap** — once the trend extended, the trade kept running until the stop was hit, capturing 2.05 points.

This is the classic *cut losses short, let profits run* principle, made operational by where you put the stop.

## Code

```python
# Stop = midpoint of the active trading range; bounded loss by construction
def simulate_breakout_strategy(df, lookback=30):
    trades, in_pos = [], 0
    for i in range(lookback, len(df)):
        win = df.iloc[i-lookback:i]
        hi, lo = win["high"].max(), win["low"].min()
        mid    = 0.5 * (hi + lo)            # ← the stop level
        c      = df["close"].iat[i]
        if in_pos == 0:
            if c > hi: in_pos, entry, stop = +1, c, mid
            elif c < lo: in_pos, entry, stop = -1, c, mid
        else:
            stopped = (in_pos==+1 and c<stop) or (in_pos==-1 and c>stop)
            if stopped:
                trades.append((in_pos, entry, c, (c-entry)*in_pos))
                in_pos = 0
    return trades

# Computed expectancy from this run:
# E = 0.33 × 2.05 + 0.67 × (-0.45) ≈ +0.38 pts/trade ≈ +$960/trade
```

Full source: [[ch7_master.py]]

## Relationships

### Within Chapter 7
- **Pairs with [[03_Confirmation_Conditions]]:** confirmation reduces *frequency* of small losses. Risk control caps the *size* of any individual loss. They attack the win-rate problem from two different angles.
- **Pre-condition for [[06_Failed_Signals]]:** you cannot survive long enough to reverse on a failed signal if you're not already capping losses.
- **Conclusion-supporter for [[07_Art_Vs_Science]]:** the *art* of trading is partly *when to honour your stop* — even rule-based traders apply judgement on stop placement.

### Outside Chapter 7
- [[Chapter_9_Stop_Loss]] — the entire chapter is dedicated to *where* to put the stops that make risk control work.
- [[Chapter_10_Setting_Objectives]] — the other side of the same coin: where to take profits.
- [[Chapter_11_Most_Important_Rule]] — failed signals are profitable only if losses on the original signal were small.
- [[Chapter_16_Planned_Trading_Approach]] — Schwager's "Risk Control Plan" formalises this: max risk per trade ≤ 3% of equity, never above 7%.
- **Outside the book:** Kelly criterion (Kelly, 1956), Van Tharp's R-multiples, Ralph Vince's optimal-f.

### When does risk control work well vs. poorly?
| Scenario | Risk control's effect |
|---|---|
| Trending market with clear stops | ✅ Excellent — cuts whipsaws cheaply, lets winners run |
| Choppy range with stops just outside | ⚠️ Stops get harvested repeatedly; need wider stops or no trade |
| Gap-prone markets (overnight news) | ⚠️ Stops can slip — true loss exceeds intended loss |
| Black-swan event (limit moves) | ❌ Stops fail to execute; risk control breaks down |
| Long-tail strategies (lottery payoffs) | ✅ Strong asymmetry — strategy *requires* small consistent losses |

---

**Source:** Schwager (1999), Ch. 7, p. 120-122, Figures 7.1–7.3.
**Tags:** #risk-control #expectancy #money-management #stop-loss #chapter-7
