# Role Reversal Principle

> *Part of: [[Chapter 4 - Trading Ranges and Support and Resistance MOC]]*

---

## Definition

The **Role Reversal Principle** (also called the **Polarity Principle**) states that once a significant [[Support and Resistance|support or resistance]] level is broken, its role reverses:

- **Old Resistance → New Support**: After price breaks above a resistance level (ceiling), that level becomes support (floor) when price returns to it.
- **Old Support → New Resistance**: After price breaks below a support level (floor), that level becomes resistance (ceiling) when price returns to it.

This is one of the most reliable and frequently recurring patterns in technical analysis. Schwager demonstrates it across multiple charts (Figures 4.11, 4.12, 4.13, 4.14, 4.22, 4.23, 4.24) using stocks, currencies, and commodities.

The reversal must be **sustained** — a brief one-day penetration does not qualify. The concept applies at all timeframes and across all markets.

---

## How to Detect

### Step-by-Step Process

1. **Identify a significant S/R level**: Look for a price where the market has reversed multiple times (a [[Trading Range]] boundary, [[Prior Major Highs and Lows|prior high/low]], or [[Concentrations of Relative Highs and Lows|cluster zone]]).
2. **Wait for a sustained breakout**: Price must close beyond the level for multiple days (not just a one-day wick). See [[Trading Range Breakout|confirmation conditions]].
3. **Watch for the "retest"**: After the breakout, price often pulls back to the broken level.
4. **Observe the reaction**: If price bounces off the old level in its new role (old resistance now acts as support, or vice versa), the role reversal is confirmed.

### Key Characteristics

| Scenario | Before Breakout | After Breakout | Retest Behavior |
|----------|----------------|----------------|-----------------|
| **Upside breakout** | Level is resistance (ceiling) | Level becomes support (floor) | Price drops to level and bounces up |
| **Downside breakout** | Level is support (floor) | Level becomes resistance (ceiling) | Price rallies to level and gets rejected |

### The "Vicinity" Rule Still Applies

The retest may not touch the exact level. The bounce or rejection may occur **near** the level (slightly above or below it). This is normal — [[Support and Resistance|S/R zones are approximate]], not precise.

---

## Analogy

### The Two-Story House

| Element | Analogy |
|---------|---------|
| **Price** | A person jumping inside a room |
| **Resistance** | The ceiling above their head |
| **Support** | The floor under their feet |
| **Breakout** | Smashing through the ceiling into the 2nd floor |
| **Role Reversal** | The old ceiling is now the floor of the 2nd floor |

**Before the breakout**: You are on the 1st floor. The ceiling is above you (resistance). You jump and your head keeps hitting it — you can't get through.

**After the breakout**: You smash through the ceiling and land on the 2nd floor. Look down at your feet. What are you standing on? **The old ceiling.** It is now the floor (support). If you slip and fall, the old ceiling catches you.

**The reverse**: If you smash through the floor into the basement, look up above your head. The old floor is now the ceiling (resistance). If you try to jump back up, the old floor blocks you.

### Alternative: The Broken Wall

> *"Once a wall is broken, if you turn around, that wall is now behind you protecting you, not in front of you blocking you."*

Before the breakout: the wall is in front of you, blocking your path.
After the breakout: the wall is behind you, protecting your back.

---

## Use Case / Example

### Figure 4.22 — Deutsche Mark: The "Flip-Flop" at Level 62

This chart demonstrates the same level **changing roles twice** (the most dramatic form of role reversal).

**Step 1 — Resistance**: In February 1991, price peaked at ~62 and fell. Level 62 = resistance (ceiling).

**Step 2 — Breakout Up**: In July 1992, price rallied and broke above 62.

**Step 3 — Role Reversal to Support**: In September 1992, price pulled back to 62. Instead of crashing through, it bounced. The old ceiling (62) became the new floor. Label: *"Support at Prior High."*

**Step 4 — Breakout Down**: In October 1992, price broke below 62.

**Step 5 — Role Reversal to Resistance**: In November–December 1992, price tried to rally back to 62. It hit that level and was rejected downward. The old floor (62) became the new ceiling. Label: *"Resistance at Prior Low."*

**Lesson**: The same price level (62) acted as Resistance → Support → Resistance depending on whether price was above or below it.

### Figure 4.23 — Coffee: Long-Term Resistance at Prior Low

**Prior Low**: In 1987, coffee bottomed at ~100 (support).

**Breakdown**: In 1989, price crashed below 100.

**Role Reversal**: In 1990 and 1991, price tried to rally back to 100. Each time, it was rejected — the old floor had become a powerful ceiling. The 1987 support held as resistance **for years**.

### Figure 4.12 — Soybean Oil: Support "Near" Top of Prior Range

The top of a prior trading range (~22.50) was resistance for months. After a breakout above it, the price pulled back and found support **near** (not exactly at) 22.50. The bounce occurred at ~22.25–22.30, illustrating the "vicinity" principle.

---

## The Psychology Behind Role Reversal

### Why Old Resistance Becomes Support (After Upside Breakout)

| Trader Group | Psychology | Action at Retest |
|-------------|-----------|-----------------|
| **Breakout buyers** | Bought at 62, price went to 68. See the pullback to 62 as a "discount." | Buy more |
| **Regretful watchers** | Missed the breakout. Waiting for a second chance. | Buy at 62 |
| **Trapped sellers** | Sold at 62, lost money when price went to 68. Want to exit at breakeven. | Buy to cover |
| **Net effect** | All three groups are **buying** at the old resistance level → creates support | |

### Why Old Support Becomes Resistance (After Downside Breakout)

| Trader Group | Psychology | Action at Retest |
|-------------|-----------|-----------------|
| **Trapped buyers** | Bought at 50, price crashed to 30. Desperate to exit at breakeven. | Sell at 50 |
| **Late shorts** | Missed the initial crash. See the rally to 50 as a short entry. | Sell short |
| **Breakeven sellers** | Held through the crash, now just want out without more pain. | Sell |
| **Net effect** | All three groups are **selling** at the old support level → creates resistance | |

---

## Python Code

```python
import pandas as pd
import numpy as np


def detect_role_reversal(df, lookback=50, retest_window=30, zone_pct=1.5):
    """
    Detect role reversal events where old S/R levels flip roles.

    Logic:
        1. Find significant highs/lows in history (S/R levels)
        2. Detect when price breaks through them
        3. Watch for a retest that bounces off the level in its new role

    Parameters:
        lookback: Period to identify the S/R level
        retest_window: Max days after breakout to look for a retest
        zone_pct: How close price must come to the level (as % of price)

    Returns:
        DataFrame with 'role_reversal_support' and 'role_reversal_resistance'
    """
    df = df.copy()
    df['role_reversal_support'] = False    # Old resistance → new support
    df['role_reversal_resistance'] = False  # Old support → new resistance

    # Find rolling highs and lows as S/R levels
    df['sr_high'] = df['High'].rolling(window=lookback).max()
    df['sr_low'] = df['Low'].rolling(window=lookback).min()

    for i in range(lookback + retest_window, len(df)):
        current_price = df['Close'].iloc[i]
        zone = current_price * zone_pct / 100

        # Check for old resistance → new support
        # Was there a resistance level that price broke above recently?
        for j in range(i - retest_window, i):
            old_resistance = df['sr_high'].iloc[j - lookback] if j - lookback >= 0 else None
            if old_resistance is None:
                continue

            # Price was above old resistance (breakout happened)
            was_above = df['Close'].iloc[j] > old_resistance
            # Now price is near the old level (retest)
            near_level = abs(df['Low'].iloc[i] - old_resistance) <= zone
            # Price bounced (didn't close below)
            bounced = df['Close'].iloc[i] > old_resistance - zone

            if was_above and near_level and bounced:
                df.iloc[i, df.columns.get_loc('role_reversal_support')] = True
                break

        # Check for old support → new resistance
        for j in range(i - retest_window, i):
            old_support = df['sr_low'].iloc[j - lookback] if j - lookback >= 0 else None
            if old_support is None:
                continue

            was_below = df['Close'].iloc[j] < old_support
            near_level = abs(df['High'].iloc[i] - old_support) <= zone
            rejected = df['Close'].iloc[i] < old_support + zone

            if was_below and near_level and rejected:
                df.iloc[i, df.columns.get_loc('role_reversal_resistance')] = True
                break

    return df
```

### Trading Application

```python
# Entry strategy using role reversal:
# 1. Identify a sustained breakout above resistance
# 2. Wait for price to pull back to the old resistance level
# 3. Buy at the old resistance (now support) with a stop just below
# 4. Target: the next resistance level above

# Risk management:
# Stop-loss = just below the old resistance level
# If price falls back below the level, the role reversal has failed
```

---

## Related Concepts
- [[Support and Resistance]]
- [[Prior Major Highs and Lows]]
- [[Trading Range Breakout]]
- [[False Breakout (Stop Run)]]

---

## Tags
#technical-analysis #schwager #role-reversal #polarity #support-resistance #retest
