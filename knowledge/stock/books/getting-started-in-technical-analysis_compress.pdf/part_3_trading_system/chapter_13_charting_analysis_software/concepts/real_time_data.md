# Real-Time (Tick) Price Data
**Chapter:** [[Chapter_13_Index|13 — Charting and Analysis Software]]  
**Source:** Schwager, *Getting Started in Technical Analysis*, p.222–223

---

## Definition
Real-time (or "tick") price data is the **transmission of every individual trade** as it occurs on the exchange — with a delay of only seconds. Each "tick" records the exact price and size of one transaction. This data stream is the most granular and most expensive form of price data, compressed into 1-minute, 5-minute, or other intraday bar charts by charting software.

---

## Simple Analogy
Real-time tick data is like **watching a sports match live**. You see every pass, every play, every second as it happens. EOD data is like watching the highlight reel at 10 PM — you get the score and key moments, but not every move. For a casual fan (position trader), highlights are enough. For the team coach (day trader), every play matters.

---

## Chart Illustration
![[charts/real_time_data.png]]
*Three panels: All 3,000 ticks for one trading day (top), 15-minute delayed bars (middle), and the single EOD bar summarising the whole day (bottom) — illustrating what is lost at each aggregation level.*

---

## Real Numeric Example
One trading day (April 29, 2026):

| Data Type | Bars/Points | Price Range | Cost/Month |
|-----------|------------|-------------|-----------|
| Real-time ticks | 3,000 trades | $198.69–$201.86 | ~$400+ |
| 15-min delayed | 26 bars | $198.69–$201.86 | ~$50–$100 |
| End-of-day | 1 bar | O:200.04 H:201.86 L:198.69 C:200.14 | ~$15–$50 |

**Note:** Delayed quotes (15 or 30 minutes behind) cost a fraction of real-time — often suitable for active but not professional traders.

---

## Python Code
**File:** [[code/real_time_data.py]]
```python
# Key snippet — aggregate ticks into different bar resolutions
import pandas as pd

# ticks = DataFrame with 'Price' and 'Size' indexed by timestamp
def to_ohlcv(tick_df, freq):
    ohlc = tick_df['Price'].resample(freq).ohlc().dropna()
    ohlc['Volume'] = tick_df['Size'].resample(freq).sum()
    return ohlc

rt_1min  = to_ohlcv(ticks, '1min')   # ~390 bars/day
delayed  = to_ohlcv(ticks, '15min')  # ~26 bars/day
eod      = to_ohlcv(ticks, '1D')     # 1 bar/day
```

---

## Relationships

### Within Chapter 13
| Concept | How They Relate |
|---------|-----------------|
| [[Historical Price Data]] | RT is the live equivalent of historical; historical is RT data that has been stored and sold later |
| [[End-of-Day Price Data]] | EOD is RT data compressed to one bar — RT costs ~10–30x more |
| [[Software Selection Framework]] | RT data requires specialised (more expensive) software with real-time feed capability |
| [[Data Quality and Cleaning]] | RT data also has errors (flash crashes, bad prints) that must be filtered instantly |

### Outside Chapter 13
| Chapter | Concept | Relationship |
|---------|---------|--------------|
| Ch. 2 | Types of Charts | Intraday bar charts (1-min, hourly) are only possible with RT data |
| Ch. 6 | Oscillators | Intraday oscillator signals require RT data to act on them in real time |
| Ch. 9 | Stop-Loss Points | Tight intraday stops require RT to monitor and execute |
| Ch. 10 | Setting Objectives | Intraday profit targets need RT to know when price touches the level |

### When Real-Time Is Needed vs. Not
- ✅ **Required** → Day trading, scalping, intraday breakout strategies
- ⚠️ **Optional (use delayed)** → Active swing traders who adjust stops intraday
- ❌ **Unnecessary** → Position traders, system testers, anyone trading daily charts only

---

## Tags
#price-data #real-time #tick-data #intraday #day-trading #technical-analysis #chapter13
