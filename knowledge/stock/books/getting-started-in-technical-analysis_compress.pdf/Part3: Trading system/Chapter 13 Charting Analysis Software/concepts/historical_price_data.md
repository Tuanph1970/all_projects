# Historical Price Data
**Chapter:** [[Chapter_13_Index|13 — Charting and Analysis Software]]  
**Source:** Schwager, *Getting Started in Technical Analysis*, p.222

---

## Definition
Historical price data is a **pre-packaged dataset** covering a fixed, past time span (e.g., 3 years, 10 years, 20 years) of daily OHLCV (Open, High, Low, Close, Volume) records for one or more instruments. It is the *foundation layer* of any technical analysis system — a static snapshot you purchase once, then optionally extend with ongoing end-of-day feeds.

---

## Simple Analogy
Think of historical price data like a **library book archive**. Before anyone can search for trends in old newspaper articles, the library must first have the physical collection on shelves. Historical data is that collection — the complete set of past "newspaper pages" (daily price records) that you load onto your shelf before any research begins.

---

## Chart Illustration
![[charts/historical_price_data.png]]
*Three panels: OHLCV bar chart (top), volume (middle), rolling 1-year return (bottom) — illustrating why longer historical depth matters for understanding full market cycles.*

---

## Real Numeric Example
| Attribute | Value |
|-----------|-------|
| Date range | 2023-06-07 → 2026-04-29 |
| Trading days | 756 (~3.0 years) |
| Price range | $81.48 – $138.62 |
| Start price | $100.78 |
| End price | $93.70 |
| Total return | −7.0% |
| Missing days | 0 (business days only) |

A data vendor might sell this 3-year daily dataset for a **one-time fee of $50–$200** depending on the market.

---

## Python Code
**File:** [[code/historical_price_data.py]]
```python
# Key snippet — build a clean historical OHLCV DataFrame
import pandas as pd, numpy as np
from datetime import datetime

np.random.seed(42)
n_days = 756  # ~3 years
dates = pd.bdate_range(end=datetime.today(), periods=n_days)
returns = np.random.normal(0.0003, 0.015, n_days)
close = 100 * np.cumprod(1 + returns)
high  = close * (1 + np.abs(np.random.normal(0, 0.008, n_days)))
low   = close * (1 - np.abs(np.random.normal(0, 0.008, n_days)))
df = pd.DataFrame({'Close': close, 'High': high, 'Low': low}, index=dates)
print(f"Coverage: {df.index[0].date()} to {df.index[-1].date()}")
```

---

## Relationships

### Within Chapter 13
| Concept | How They Relate |
|---------|-----------------|
| [[End-of-Day Price Data]] | EOD data *extends* a historical database daily; historical is the starting archive |
| [[Real-Time (Tick) Price Data]] | RT data is the most granular — historical data is its aggregated, cheaper cousin |
| [[Data Quality and Cleaning]] | All historical data must be cleaned; vendors clean it before delivery |
| [[Continuous Futures Data]] | Continuous futures are a *special form* of historical data (back-adjusted) |
| [[Software Selection Framework]] | Software choice determines which historical data formats it accepts |

### Outside Chapter 13
| Chapter | Concept | Relationship |
|---------|---------|--------------|
| Ch. 2 | Types of Charts | Bar/candlestick charts are drawn from OHLCV historical data |
| Ch. 15 | System Testing | Back-testing requires years of clean historical data |
| Ch. 14 | Trading Systems | System design relies on sufficient historical depth to be statistically meaningful |

### When to Use Historical vs. Other Data
- ✅ **Use Historical** → System back-testing, long-term chart analysis, learning/research
- ⚠️ **Switch to EOD** → When you need to update positions daily after market close  
- ❌ **Don't use Historical alone** → If you trade intraday (you need real-time)

---

## Tags
#price-data #historical-data #ohlcv #back-testing #technical-analysis #chapter13
