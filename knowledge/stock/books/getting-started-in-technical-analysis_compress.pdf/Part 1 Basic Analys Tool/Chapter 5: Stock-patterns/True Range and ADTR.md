---
tags: [technical-analysis, schwager, building-block, volatility]
source: "Schwager - Getting Started in Technical Analysis, Appendix pp.322"
related: ["[[Spikes]]", "[[Run Days]]", "[[Wide-Ranging Days]]"]
---

# True Range and ADTR

## Definition

Developed by **Welles Wilder Jr.** (1978, *New Concepts in Technical Trading Systems*).

### Range vs. True Range

- **Range**: `R = High - Low` (ignores gaps between days)
- **True Range**: `TR = True High - True Low` (accounts for gaps)

Where:
- **True High** = max(today's high, yesterday's close)
- **True Low** = min(today's low, yesterday's close)

### Average Daily True Range (ADTR)

Simply a moving average of daily true range values. Commonly used as a **market volatility measurement**.

## Why True Range Matters

Standard range misses gap activity. If a stock closes at 100, gaps up to open at 105, and trades 105–108, the standard range is 3 (108–105). But the true range is 8 (108–100), which better reflects the actual price movement a trader experienced.

## Usage Across Patterns

This is a shared building block used by three one-day patterns:

- [[Spikes]] — protrusion measured as multiples of ADTR
- [[Run Days]] — uses true high/true low for neighborhood comparison
- [[Wide-Ranging Days]] — Volatility Ratio = TR / ADTR

## Python Implementation

```python
def compute_true_range(df: pd.DataFrame) -> pd.Series:
    """Wilder's True Range: max(H-L, |H-prevC|, |L-prevC|)"""
    prev_close = df['close'].shift(1)
    tr = pd.concat([
        df['high'] - df['low'],
        (df['high'] - prev_close).abs(),
        (df['low'] - prev_close).abs()
    ], axis=1).max(axis=1)
    return tr

def compute_adtr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average Daily True Range — rolling mean of true range."""
    return compute_true_range(df).rolling(period).mean()
```
