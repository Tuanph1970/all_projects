# Concentrations of Relative Highs and Lows

> *Part of: [[Chapter 4 - Trading Ranges and Support and Resistance MOC]]*

---

## Definition

**Concentrations of Relative Highs and Lows** refers to price zones where multiple relative highs and relative lows cluster within a narrow band. Unlike [[Prior Major Highs and Lows]] which focus on single, prominent peaks and valleys, this concept identifies **zones of congestion** — areas where many smaller turning points happened close together.

These cluster zones create stronger [[Support and Resistance|support and resistance]] barriers than any single high or low because they represent a price area where the market repeatedly found equilibrium.

**Key rules from Schwager:**
- **Zones, not points**: The cluster creates a horizontal band (drawn with two lines), not a single line.
- **Support if current price is higher**: If price has rallied above the cluster zone, it acts as a support region when price pulls back.
- **Resistance if current price is lower**: If price is below the cluster zone, it acts as a resistance region when price rallies.
- **Best on long-term charts**: Most useful on weekly charts, but also applicable to daily charts of sufficient duration (2+ years).
- **Needs continuous data**: Individual contract charts (in futures) are usually too short for this method. Use continuous futures or long-duration stock charts.

---

## How to Detect

### Visual Method (The "Squint Test")

1. Open a weekly chart spanning 5–10 years (or a daily chart of 2+ years).
2. **Mark relative highs** (small peaks where price reversed downward, even briefly).
3. **Mark relative lows** (small valleys where price reversed upward, even briefly).
4. **Look for clusters**: Identify horizontal bands where many of these marks are concentrated.
5. **Draw two horizontal lines** around the cluster to define the zone.

### What Counts as "Relative" (vs. "Major")?

| Type | Description | Example |
|------|-------------|---------|
| **Major High/Low** | The absolute peak or valley on the chart | The all-time high in 1990 |
| **Relative High** | A smaller peak — price reversed down briefly, even if it later went higher | A local top in March before a rally continued in June |
| **Relative Low** | A smaller valley — price reversed up briefly, even if it later went lower | A local bottom in July before a decline continued in September |

**The key insight**: You don't need the absolute top or bottom. You need a **density** of turning points. If price turned around 10 times in the $62–$65 zone over 3 years, that zone is more significant than a single spike to $70 that happened once.

### Quantitative Detection

Count the number of local highs and lows that fall within each price zone. The zone with the highest count (most "touches") is the strongest S/R zone.

---

## Analogy

### The Neighborhood

Think of the price chart as a city map, and the cluster zone as a **neighborhood** where many people live.

| Element | Analogy |
|---------|---------|
| **A single prior high** | A single house on a deserted road — one person might react when you pass by |
| **A concentration zone** | An entire neighborhood — hundreds of people will react when you pass through |
| **Support** | Walking through a friendly neighborhood — people come out to help you (buyers step in) |
| **Resistance** | Walking through a hostile neighborhood — people come out to block you (sellers step in) |

**Why clusters are stronger than single points**: If only one person (one prior high) remembers a price level, the market might push through easily. But if an entire neighborhood (a cluster of many highs and lows) remembers that zone, there are far more buyers or sellers waiting to act. The barrier is thicker and harder to break.

---

## Use Case / Example

### Figure 4.25 — Swiss Franc: Support from a Cluster Zone

**The Cluster (1986–1989)**: On this weekly chart, price moved sideways between approximately 62 and 65. During these years, many relative highs (↓) and relative lows (↑) formed within this narrow band. The arrows on the chart show the density of turning points — they are heavily concentrated in this zone.

**The Breakout (1990)**: Price rallied sharply from the cluster zone up to ~90.

**The Retest (1991–1994)**: After the rally, price declined significantly. When it returned to the 62–65 zone, it found support and bounced. This happened multiple times (1991, 1992, 1993–1994).

**Why it worked**: The 62–65 zone wasn't just one prior high or low — it was an area where the market had spent **3 years** turning around repeatedly. When price returned to this "neighborhood," the collective memory of all those turning points created strong buying pressure (support).

### Figure 4.26 — Crude Oil: Resistance from a Cluster Zone

**The Cluster (1987–1989)**: Crude oil traded sideways with many relative highs and lows concentrated between approximately 22 and 25.

**The Spike (1990)**: An exogenous event (likely the Gulf War) drove price to ~38 — far above the cluster zone.

**The Return (1991–1994)**: After the spike, price crashed back down. By 1993–1994, price was trading around 18–20 (below the cluster zone). Every time it tried to rally toward the 22–25 zone, it was rejected.

**Why it worked**: The cluster zone acted as resistance because price was approaching from below. Sellers who remembered the 22–25 zone as a congestion area stepped in to sell.

---

## Python Code

```python
import pandas as pd
import numpy as np


def find_relative_highs_lows(df, order=5):
    """
    Find relative (local) highs and lows on a price chart.

    Parameters:
        order: Number of bars on each side to compare.
               A point is a relative high if it's higher than
               the 'order' bars before AND after it.

    Returns:
        DataFrame with 'rel_high' and 'rel_low' columns (NaN where not a turning point)
    """
    df = df.copy()
    df['rel_high'] = np.nan
    df['rel_low'] = np.nan

    for i in range(order, len(df) - order):
        # Check if this bar's high is higher than all surrounding bars
        window_highs = df['High'].iloc[i - order:i + order + 1].values
        if df['High'].iloc[i] == np.max(window_highs):
            df.iloc[i, df.columns.get_loc('rel_high')] = df['High'].iloc[i]

        # Check if this bar's low is lower than all surrounding bars
        window_lows = df['Low'].iloc[i - order:i + order + 1].values
        if df['Low'].iloc[i] == np.min(window_lows):
            df.iloc[i, df.columns.get_loc('rel_low')] = df['Low'].iloc[i]

    return df


def find_cluster_zones(df, order=5, zone_width_pct=2.0, min_touches=3):
    """
    Find concentration zones where relative highs and lows cluster.

    Parameters:
        order: Lookback for finding relative highs/lows
        zone_width_pct: Width of each bin as % of avg price
        min_touches: Minimum turning points in a zone to qualify

    Returns:
        List of dicts: {'center', 'lower', 'upper', 'touches', 'type'}
    """
    df = find_relative_highs_lows(df, order=order)

    # Collect all turning point prices
    rel_highs = df['rel_high'].dropna().values
    rel_lows = df['rel_low'].dropna().values
    all_points = np.concatenate([rel_highs, rel_lows])

    if len(all_points) == 0:
        return []

    # Create price bins
    avg_price = df['Close'].mean()
    bin_width = avg_price * zone_width_pct / 100
    price_min = np.min(all_points)
    price_max = np.max(all_points)

    bins = np.arange(price_min, price_max + bin_width, bin_width)
    hist, bin_edges = np.histogram(all_points, bins=bins)

    # Find zones with sufficient concentration
    current_price = df['Close'].iloc[-1]
    zones = []

    for i in range(len(hist)):
        if hist[i] >= min_touches:
            lower = bin_edges[i]
            upper = bin_edges[i + 1]
            center = (lower + upper) / 2

            zone_type = 'support' if center < current_price else 'resistance'

            zones.append({
                'center': round(center, 2),
                'lower': round(lower, 2),
                'upper': round(upper, 2),
                'touches': int(hist[i]),
                'type': zone_type,
                'distance_pct': round(abs(current_price - center) / current_price * 100, 2)
            })

    # Sort by number of touches (strongest first)
    zones = sorted(zones, key=lambda x: x['touches'], reverse=True)

    return zones


def print_cluster_zones(zones, current_price):
    """Pretty-print the cluster zones."""
    print(f"Current Price: ${current_price:.2f}\n")
    print(f"{'Type':>12} | {'Zone':>20} | {'Center':>8} | {'Touches':>7} | {'Distance':>8}")
    print("-" * 70)
    for z in zones:
        print(f"{z['type'].upper():>12} | "
              f"${z['lower']:.2f} - ${z['upper']:.2f} | "
              f"${z['center']:.2f} | "
              f"{z['touches']:>7} | "
              f"{z['distance_pct']:>7.1f}%")
```

### Usage

```python
import yfinance as yf

# Use a long timeframe for best results (Schwager recommends weekly or 2+ years daily)
df = yf.download("AAPL", period="5y")

zones = find_cluster_zones(df, order=10, zone_width_pct=3.0, min_touches=4)
current_price = df['Close'].iloc[-1]

print_cluster_zones(zones, current_price)

# Example output:
#         Type |                 Zone |   Center | Touches | Distance
# ----------------------------------------------------------------------
#      SUPPORT |  $145.20 - $152.80   |  $149.00 |      12 |    15.2%
#   RESISTANCE |  $195.50 - $203.10   |  $199.30 |       8 |     5.1%
#      SUPPORT |  $165.00 - $172.60   |  $168.80 |       6 |     9.8%
```

### Parameter Tuning

| Parameter | Low Value | High Value | Effect |
|-----------|-----------|------------|--------|
| `order` | 3 (many small turns) | 20 (only major turns) | Controls sensitivity |
| `zone_width_pct` | 1% (tight zones) | 5% (wide zones) | Controls zone granularity |
| `min_touches` | 2 (weak zones) | 6+ (very strong zones) | Controls minimum strength |

---

## Comparison: Single Peaks vs. Cluster Zones

| Feature | [[Prior Major Highs and Lows]] | Concentrations |
|---------|-------------------------------|----------------|
| **What to look for** | One dramatic peak or valley | Many smaller peaks and valleys clustered together |
| **Drawn as** | A single horizontal line (or narrow band) | A wider horizontal zone (two lines) |
| **Strength** | One data point | Multiple data points (statistically stronger) |
| **Best timeframe** | Any | Weekly or 2+ year daily charts |
| **Analogy** | A single house on a road | An entire neighborhood |

---

## Related Concepts
- [[Prior Major Highs and Lows]]
- [[Support and Resistance]]
- [[Role Reversal Principle]]
- [[Trading Range]]

---

## Tags
#technical-analysis #schwager #cluster-zones #relative-highs-lows #support-resistance #concentration
