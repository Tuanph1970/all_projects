# Support and Resistance

> *Part of: [[Chapter 4 - Trading Ranges and Support and Resistance MOC]]*

---

## Definition

**Support** is a price level or zone where buying pressure is strong enough to halt a decline and push price back up. **Resistance** is a price level or zone where selling pressure is strong enough to halt a rally and push price back down.

Schwager's key principles:

- Once a [[Trading Range]] is established (at least 1–2 months of sideways movement), the **upper boundary** acts as resistance and the **lower boundary** acts as support.
- Support and resistance are **approximate areas (zones), not precise points**. Schwager calls the practice of treating them as exact numbers "nonsense."
- After a sustained breakout, support and resistance **reverse roles** — see [[Role Reversal Principle]].
- Support and resistance can be identified through multiple methods: range boundaries, [[Prior Major Highs and Lows]], [[Concentrations of Relative Highs and Lows]], and [[Price Envelope Bands]].

---

## How to Detect

### Method 1: Trading Range Boundaries
When price moves sideways for 1–2+ months, the upper boundary = resistance, lower boundary = support.

### Method 2: Prior Major Highs and Lows
Historical peaks act as resistance; historical valleys act as support. See [[Prior Major Highs and Lows]].

### Method 3: Cluster Zones
Zones where many relative highs and lows concentrate create stronger S/R than single points. See [[Concentrations of Relative Highs and Lows]].

### Method 4: Dynamic Bands
Moving-average-based envelopes provide adaptive S/R that moves with price. See [[Price Envelope Bands]].

### The "Vicinity" Rule

Schwager insists that S/R should be treated as **zones, not lines**:

> *"If a prior high for a stock was 65, then they consider 65 to be major resistance, and if the market rallies to 66, they consider resistance to be broken. This is nonsense."*

- Draw a **band** (e.g., $64–$66), not a single line at $65.
- Different traders remember different prices (the intraday spike, the closing price, etc.), so the "level" is inherently fuzzy.
- In Schwager's chart examples (Figs 4.15–4.17), prices frequently penetrated prior highs/lows slightly before reversing, rather than turning exactly at those levels.

---

## Analogy

### The Cloud Layer

Think of support and resistance not as a thin sheet of glass, but as a **thick layer of clouds**.

| Element | Analogy |
|---------|---------|
| **Resistance** | A cloud layer above you — you can sometimes poke your head through, but it pushes you back down |
| **Support** | A cloud layer below you — you can sometimes dip your feet through, but it pushes you back up |
| **Exact price** | A single raindrop in the cloud (meaningless on its own) |
| **The zone** | The entire cloud (what actually stops you) |

A plane flying through the cloud layer might enter the bottom of the cloud at 9,800 feet and exit the top at 10,200 feet. If you placed your "resistance line" at exactly 10,000 feet, you would be wrong half the time. The entire cloud (9,800–10,200) is the resistance zone.

---

## Use Case / Example

### Figure 4.15 — Soybean Oil: Both Resistance and Support

**Resistance at Prior High**: The chart shows a spike in 1984/1985 establishing a high around $34. In 1988, the price rallied toward that level again but failed to break above it — the 1985 high acted as a ceiling.

**Support at Prior Low**: The 1986 crash established a low around $14–$18. In 1989, 1991, and 1992, the price dropped toward that zone and bounced each time — the prior low zone acted as a floor.

**The Lesson**: A single chart can display both resistance (at prior highs) and support (at prior lows) simultaneously, creating a "box" that contains price for years.

### Figure 4.16 — Wheat: Precision of Levels

- The 1988/1989 peak at ~450 acted as resistance in 1991 and 1994 (price touched it and reversed).
- The 1986 bottom at ~240 acted as support in 1990 (price dropped to ~240 and bounced).
- These levels held relevance **across 4–8 years** of market history.

---

## Python Code

```python
import pandas as pd
import numpy as np


def find_support_resistance_zones(df, window=20, num_zones=5, zone_width_pct=1.5):
    """
    Identify support and resistance zones from price history.

    Approach: Find local maxima and minima, then cluster them into zones.

    Parameters:
        window: Lookback for identifying local highs/lows
        num_zones: Maximum number of S/R zones to return
        zone_width_pct: Width of each zone as % of price

    Returns:
        List of dicts with 'level', 'type', 'strength', 'lower', 'upper'
    """
    df = df.copy()

    # Find local highs (resistance candidates)
    df['local_high'] = df['High'][
        (df['High'] > df['High'].shift(1)) &
        (df['High'] > df['High'].shift(-1)) &
        (df['High'] > df['High'].rolling(window, center=True).mean())
    ]

    # Find local lows (support candidates)
    df['local_low'] = df['Low'][
        (df['Low'] < df['Low'].shift(1)) &
        (df['Low'] < df['Low'].shift(-1)) &
        (df['Low'] < df['Low'].rolling(window, center=True).mean())
    ]

    # Collect all turning points
    highs = df['local_high'].dropna().values
    lows = df['local_low'].dropna().values
    all_levels = np.concatenate([highs, lows])

    if len(all_levels) == 0:
        return []

    # Cluster nearby levels into zones
    all_levels = np.sort(all_levels)
    current_price = df['Close'].iloc[-1]
    zone_width = current_price * zone_width_pct / 100

    zones = []
    cluster = [all_levels[0]]

    for i in range(1, len(all_levels)):
        if all_levels[i] - all_levels[i-1] <= zone_width:
            cluster.append(all_levels[i])
        else:
            level = np.mean(cluster)
            zones.append({
                'level': round(level, 2),
                'lower': round(min(cluster), 2),
                'upper': round(max(cluster), 2),
                'strength': len(cluster),  # More touches = stronger zone
                'type': 'resistance' if level > current_price else 'support'
            })
            cluster = [all_levels[i]]

    # Don't forget the last cluster
    level = np.mean(cluster)
    zones.append({
        'level': round(level, 2),
        'lower': round(min(cluster), 2),
        'upper': round(max(cluster), 2),
        'strength': len(cluster),
        'type': 'resistance' if level > current_price else 'support'
    })

    # Sort by strength (most touches first)
    zones = sorted(zones, key=lambda x: x['strength'], reverse=True)

    return zones[:num_zones]
```

### Usage

```python
import yfinance as yf

df = yf.download("AAPL", period="1y")
zones = find_support_resistance_zones(df, window=10, num_zones=5)

for z in zones:
    print(f"{z['type'].upper():>10} | Level: ${z['level']:.2f} "
          f"(Zone: ${z['lower']:.2f}-${z['upper']:.2f}) | "
          f"Strength: {z['strength']} touches")
```

---

## The Psychology Behind S/R

### Why Resistance Works (at Prior Highs)
- **Breakeven sellers**: Traders who bought at the prior high and lost money wait to sell at breakeven when price returns.
- **Profit-takers**: Traders who are long sell their profitable positions at a level that previously marked a top.
- **Fear**: New buyers hesitate at a level that previously caused a reversal.

### Why Support Works (at Prior Lows)
- **Bargain hunters**: Traders who missed buying at the prior low see a second chance.
- **Short-covering**: Traders who are short cover their positions at a level that previously marked a bottom.
- **Greed**: The prior low is perceived as "cheap" relative to recent trading history.

---

## Related Concepts
- [[Role Reversal Principle]]
- [[Prior Major Highs and Lows]]
- [[Concentrations of Relative Highs and Lows]]
- [[Price Envelope Bands]]
- [[Trading Range]]
- [[Trading Range Breakout]]

---

## Tags
#technical-analysis #schwager #support #resistance #zones #price-levels
