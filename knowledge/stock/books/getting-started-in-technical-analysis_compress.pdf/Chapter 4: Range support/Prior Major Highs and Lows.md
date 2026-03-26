# Prior Major Highs and Lows

> *Part of: [[Chapter 4 - Trading Ranges and Support and Resistance MOC]]*

---

## Definition

**Prior Major Highs and Lows** are single, prominent historical peaks and valleys on a price chart that act as future [[Support and Resistance|resistance and support]] levels.

- **Prior Major High**: A significant past peak where sellers overwhelmed buyers and price reversed downward. Acts as **resistance** for future rallies.
- **Prior Major Low**: A significant past valley where buyers overwhelmed sellers and price reversed upward. Acts as **support** for future declines.

### Schwager's Key Rules

1. **Approximate zones, not precise points**: A prior high of $65 does not mean resistance is exactly at $65. It means resistance exists in the **general vicinity** of $65 (e.g., $63–$67).
2. **Penetration ≠ invalidation**: If price rallies to $66 (past the prior high of $65), that does not automatically mean resistance is "broken." Schwager calls this assumption "nonsense."
3. **Penetrations need confirmation**: To treat a penetration as a buy/sell signal, require a minimum number of closes beyond the level, a minimum percent penetration, or both.
4. **Applicable across timeframes**: Most important on weekly charts but also applies to daily charts.
5. **[[Role Reversal Principle|Role reversal]]**: Once a prior high is sustainably penetrated, it becomes support. Once a prior low is sustainably penetrated, it becomes resistance.

---

## How to Detect

### What Makes a High/Low "Major"?

A prior high or low qualifies as "Major" if it meets these criteria:

| Criterion | Major | Minor |
|-----------|-------|-------|
| **Time distance** | Months or years ago | Days ago |
| **Price magnitude** | Price moved away from the level significantly (>10–20%) | Small pullback (<5%) |
| **Visual prominence** | Clearly visible as a "mountain peak" or "valley floor" on the chart | Just a small jagged edge |
| **Chart timeframe** | Stands out on a weekly or monthly chart | Only visible on an intraday chart |

### Detection Steps

1. Zoom out to a weekly or multi-year daily chart.
2. Identify the most prominent peaks (mountains) and valleys (canyons).
3. Draw **horizontal zones** (not thin lines) at these levels.
4. Watch for price to approach these zones from either direction.
5. Expect price to slow down, consolidate, or reverse in the vicinity of these zones.

### Penetration as a Trading Signal

When price does break through a prior high or low:

| Confirmation Method | Description |
|-------------------|-------------|
| **Time filter** | Minimum N closes beyond the level (e.g., 3 consecutive closes) |
| **Percent filter** | Minimum percentage beyond the level (e.g., 2–3%) |
| **Combined** | Both conditions must be met |

**A one-period, modest penetration proves nothing.** Always wait for confirmation.

---

## Analogy

### The Memory Building

Imagine the stock market is a person climbing a multi-story building. The building has **memory** — it remembers where the climber stumbled or succeeded in the past.

| Element | Analogy |
|---------|---------|
| **Prior Major High** | A floor where the climber hit their head on the ceiling and fell back down. Next time they approach that floor, they flinch. |
| **Prior Major Low** | A floor with a trampoline. The climber fell here before but bounced back up. Next time they fall, the trampoline catches them. |
| **Vicinity (zone)** | The ceiling isn't a razor-thin laser beam at exactly 100 feet. It's a thick concrete slab between 98 and 102 feet. |
| **Penetration** | The climber's fingertips touching the next floor doesn't mean they've arrived. They must stand firmly on that floor for several days. |

**Why the building has memory**: Other climbers (traders) remember the dangerous and safe floors. At the "dangerous ceiling," they sell (creating resistance). At the "trampoline floor," they buy (creating support).

---

## Use Case / Example

### Figure 4.15 — Soybean Oil (Multi-Year S/R)

**Resistance at Prior High**: A spike in 1984/1985 established a high around ~34. In 1988 and again in 1993, price rallied toward ~34 and struggled to go higher. Sellers remembered this level as "too expensive" and sold, pushing price back down.

**Support at Prior Low**: The 1986 crash bottomed around ~14–18. In 1989, 1991, and 1992, price dropped toward this zone and bounced. Buyers remembered this level as "cheap" and bought, preventing further declines.

**Result**: A single chart shows both effects — a ceiling at the prior high and a floor at the prior low — creating a massive box that contained price for nearly a decade.

### Figure 4.16 — Wheat (Precision Across Years)

- The 1988/1989 peak at ~450 acted as resistance in 1991 and 1994 (price touched it and reversed).
- The 1986 bottom at ~240 acted as support in 1990 (price dropped almost exactly to ~240 and bounced).
- These levels remained relevant across **4–8 years** of market history.

### Figures 4.18/4.19 — Deutsche Mark (Penetration as Buy Signal)

**Setup (Fig 4.18)**: A horizontal line at ~62 acted as resistance — price hit it twice in 1993 and fell.

**Breakout**: In mid-1994, price broke above 62 with **three consecutive closes** above the level (the confirmation condition).

**Result**: After the confirmed breakout, price rallied from ~63 to ~74. The confirmation filter avoided any false signals.

### Figures 4.20/4.21 — Coffee & Soybean Oil (Penetration as Sell Signal)

**Coffee (Fig 4.20)**: Support at ~100 (the 1987 low) broke in 1989. With confirmation, this generated a sell signal. Price then crashed from ~100 to ~60 over the next few years.

**Soybean Oil (Fig 4.21)**: Support at ~22.50 broke in mid-1994. After the confirmed breakdown, price crashed sharply from ~22.50 to ~19.

Both were **good signals** — the confirmed penetration of a prior low correctly predicted a major downtrend.

---

## Python Code

```python
import pandas as pd
import numpy as np


def find_prior_major_highs_lows(df, prominence_window=50, min_move_pct=10):
    """
    Identify Prior Major Highs and Lows on a price chart.

    A point qualifies as 'major' if:
        1. It is the highest/lowest point within a window
        2. Price moved away from it by at least min_move_pct %

    Parameters:
        prominence_window: Bars to look left and right for prominence
        min_move_pct: Minimum % move away from the level to qualify as 'major'

    Returns:
        dict with 'major_highs' and 'major_lows' (lists of (index, price))
    """
    highs = []
    lows = []
    prices_high = df['High'].values
    prices_low = df['Low'].values
    prices_close = df['Close'].values

    for i in range(prominence_window, len(df) - prominence_window):
        # Check if this is a local maximum
        window_high = prices_high[i - prominence_window:i + prominence_window + 1]
        if prices_high[i] == np.max(window_high):
            # Check prominence: did price fall significantly after?
            future_min = np.min(prices_low[i:min(i + prominence_window * 2, len(df))])
            drop_pct = (prices_high[i] - future_min) / prices_high[i] * 100
            if drop_pct >= min_move_pct:
                highs.append({
                    'date': df.index[i],
                    'price': prices_high[i],
                    'drop_pct': round(drop_pct, 1)
                })

        # Check if this is a local minimum
        window_low = prices_low[i - prominence_window:i + prominence_window + 1]
        if prices_low[i] == np.min(window_low):
            future_max = np.max(prices_high[i:min(i + prominence_window * 2, len(df))])
            rise_pct = (future_max - prices_low[i]) / prices_low[i] * 100
            if rise_pct >= min_move_pct:
                lows.append({
                    'date': df.index[i],
                    'price': prices_low[i],
                    'rise_pct': round(rise_pct, 1)
                })

    return {'major_highs': highs, 'major_lows': lows}


def check_proximity_to_major_levels(current_price, major_levels, zone_pct=2.0):
    """
    Check if current price is near any major S/R level.

    Parameters:
        current_price: Current market price
        major_levels: Output from find_prior_major_highs_lows()
        zone_pct: How close (%) price must be to trigger a warning

    Returns:
        List of nearby levels with distance info
    """
    nearby = []
    zone = current_price * zone_pct / 100

    for h in major_levels['major_highs']:
        distance = abs(current_price - h['price'])
        if distance <= zone:
            nearby.append({
                'type': 'RESISTANCE (Prior Major High)',
                'level': h['price'],
                'date': h['date'],
                'distance_pct': round(distance / current_price * 100, 2)
            })

    for l in major_levels['major_lows']:
        distance = abs(current_price - l['price'])
        if distance <= zone:
            nearby.append({
                'type': 'SUPPORT (Prior Major Low)',
                'level': l['price'],
                'date': l['date'],
                'distance_pct': round(distance / current_price * 100, 2)
            })

    return sorted(nearby, key=lambda x: x['distance_pct'])
```

### Usage

```python
import yfinance as yf

df = yf.download("AAPL", period="5y")
levels = find_prior_major_highs_lows(df, prominence_window=50, min_move_pct=10)

print("=== MAJOR HIGHS (Resistance) ===")
for h in levels['major_highs']:
    print(f"  {h['date'].strftime('%Y-%m-%d')}: ${h['price']:.2f} (dropped {h['drop_pct']}%)")

print("\n=== MAJOR LOWS (Support) ===")
for l in levels['major_lows']:
    print(f"  {l['date'].strftime('%Y-%m-%d')}: ${l['price']:.2f} (rose {l['rise_pct']}%)")

# Check current proximity
current = df['Close'].iloc[-1]
nearby = check_proximity_to_major_levels(current, levels, zone_pct=3.0)
if nearby:
    print(f"\n⚠️  Price ${current:.2f} is near:")
    for n in nearby:
        print(f"  {n['type']} at ${n['level']:.2f} ({n['distance_pct']}% away)")
```

---

## Related Concepts
- [[Support and Resistance]]
- [[Role Reversal Principle]]
- [[Concentrations of Relative Highs and Lows]]
- [[Trading Range Breakout]]

---

## Tags
#technical-analysis #schwager #prior-highs #prior-lows #support #resistance #zones
