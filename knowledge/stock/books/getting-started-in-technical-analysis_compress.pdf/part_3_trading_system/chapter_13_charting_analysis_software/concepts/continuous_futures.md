# Continuous Futures Data
**Chapter:** [[Chapter_13_Index|13 — Charting and Analysis Software]]  
**Source:** Schwager, *Getting Started in Technical Analysis*, p.223

---

## Definition
Continuous futures data is a **back-adjusted, gap-free price series** that stitches together successive futures contracts to form a single unbroken historical record. Because individual futures contracts expire and are replaced by new ones at slightly different prices, naive concatenation (the "nearest futures" approach) creates artificial price jumps at rollover dates. Continuous data eliminates these jumps by shifting historical prices backward, preserving the *shape* of the price path for accurate system testing.

---

## Simple Analogy
Imagine tracking the "price of apples at your local market" over 10 years. Each year the vendor changes, and their baseline price is slightly different. If you just record each vendor's price as-is, you'll see phantom price jumps every January. Continuous data is like **adjusting all old records to remove the vendor-change jumps** — so you can study the true trend in apple prices, uncontaminated by supplier changes.

---

## Chart Illustration
![[charts/continuous_futures.png]]
*Three panels: individual contracts (top, each in its own color), nearest futures with visible rollover gaps (middle, orange), and back-adjusted continuous data (bottom, green) — smooth and unbroken.*

---

## Real Numeric Example
Rollover gaps and back-adjustments for 6 contracts over ~18 months:

| Rollover Date | Nearest Price | Continuous Price | Adjustment |
|--------------|--------------|-----------------|-----------|
| 2025-02-13 | $106.29 | $107.37 | +$1.08 |
| 2025-05-13 | $116.96 | $117.76 | +$0.81 |
| 2025-08-08 | $110.48 | $112.59 | +$2.11 |
| 2025-11-05 | $102.72 | $103.74 | +$1.01 |
| 2026-02-02 | $100.07 | $100.07 | $0.00 (anchor) |

The most recent contract is always the anchor (no adjustment needed). All prior contracts are shifted backward to eliminate the accumulated gap.

---

## Python Code
**File:** [[code/continuous_futures.py]]
```python
# Key snippet — back-adjust to create continuous futures
def back_adjust(contracts: dict) -> pd.Series:
    """
    contracts: OrderedDict of {name: pd.Series}, chronologically ordered.
    Returns a single gap-free continuous series.
    """
    names = list(contracts.keys())
    continuous = pd.concat(contracts.values()).sort_index()
    cumulative_adj = 0.0

    for i in range(len(names) - 1, 0, -1):
        prev_last  = contracts[names[i-1]].iloc[-1]
        next_first = contracts[names[i]].iloc[0]
        gap = next_first - prev_last
        cumulative_adj += gap
        continuous[contracts[names[i-1]].index] += cumulative_adj

    return continuous
```

---

## Relationships

### Within Chapter 13
| Concept | How They Relate |
|---------|-----------------|
| [[Historical Price Data]] | Continuous futures are a *specialised form* of historical data, specifically for futures markets |
| [[Data Quality and Cleaning]] | Roll adjustments must be done correctly — incorrect stitching creates artificial signals |
| [[Software Selection Framework]] | Advanced futures-focused software handles continuous construction automatically |

### Outside Chapter 13
| Chapter | Concept | Relationship |
|---------|---------|--------------|
| Ch. 2 | Types of Charts | Schwager mentions individual/nearest/continuous data as a charting consideration for futures |
| Ch. 15 | System Testing | Back-tests on nearest futures give false signals at every rollover; continuous is essential |
| Ch. 14 | Trading System Design | All futures system signals should be generated on continuous, not nearest, data |

### Three Futures Data Types Compared
| Type | Gaps? | Cost | Best For |
|------|-------|------|---------|
| **Individual contract** | N/A (separate files) | Low | Options pricing, expiry analysis |
| **Nearest (front-month)** | Yes — at each rollover | Low | Quick visual inspection only |
| **Continuous (back-adjusted)** | No | Medium | System back-testing, trend analysis |

**Rule of thumb:** Never back-test a futures trading system on nearest futures data — you will see phantom gains and losses at every rollover date.

---

## Tags
#futures #continuous-futures #back-adjustment #roll #historical-data #back-testing #technical-analysis #chapter13
