# End-of-Day Price Data
**Chapter:** [[Chapter_13_Index|13 — Charting and Analysis Software]]  
**Source:** Schwager, *Getting Started in Technical Analysis*, p.222

---

## Definition
End-of-day (EOD) price data is the **daily OHLCV record** (Open, High, Low, Close, Volume) for each trading instrument, made available a few hours after the market closes each session. A trader *downloads* this each evening via modem or Internet to append one new row to their local price database, keeping it perpetually current without paying for real-time data.

---

## Simple Analogy
EOD data is like the **evening news weather report**. You don't watch weather radar all day — you tune in at 6 PM to get today's summary (high, low, rainfall). It's not live, but for planning tomorrow's activities it's perfectly sufficient. The "download" is you turning on the TV each evening; the database is your weather notebook.

---

## Chart Illustration
![[charts/end_of_day_data.png]]
*1 year of daily EOD database — the red dots highlight the 10 most recently downloaded rows, showing how the database grows one row per trading day.*

---

## Real Numeric Example
Last 5 entries of an EOD database:

| Date | Open | High | Low | Close | Volume |
|------|------|------|-----|-------|--------|
| 2026-04-23 | 149.45 | 148.02 | 146.97 | 147.72 | 5,413,734 |
| 2026-04-24 | 147.72 | 148.88 | 146.71 | 147.75 | 6,981,347 |
| 2026-04-27 | 147.75 | 150.42 | 148.53 | 148.92 | 3,693,142 |
| 2026-04-28 | 148.92 | 151.88 | 150.55 | 151.20 | 2,412,113 |
| 2026-04-29 | 151.20 | 153.46 | 151.31 | 152.74 | 7,187,395 |

**Cost comparison:**
- EOD subscription: ~$15–$50/month
- Real-time feed: ~$200–$500/month

---

## Python Code
**File:** [[code/end_of_day_data.py]]
```python
# Key snippet — simulate daily EOD download (append one row per day)
import pandas as pd, numpy as np
from datetime import datetime, timedelta

# Simulate 1 year of daily EOD data
trading_days = pd.bdate_range(
    start=datetime.today() - timedelta(days=365),
    end=datetime.today()
)
close = 150 * np.cumprod(1 + np.random.normal(0.0004, 0.012, len(trading_days)))

eod_db = pd.DataFrame({'Close': close}, index=trading_days)
# Each evening: eod_db.loc[today] = download_new_bar()
print(eod_db.tail(3).round(2))  # Last 3 downloads
```

---

## Relationships

### Within Chapter 13
| Concept | How They Relate |
|---------|-----------------|
| [[Historical Price Data]] | Historical is the starting archive; EOD *extends* it daily |
| [[Real-Time (Tick) Price Data]] | RT data is granular intraday; EOD compresses a day into one bar — ~10x cheaper |
| [[Data Quality and Cleaning]] | EOD data can have errors (wrong prices) that still need checking even after vendor cleaning |
| [[Software Selection Framework]] | Mid-level software needs EOD download capability (price download feature) |

### Outside Chapter 13
| Chapter | Concept | Relationship |
|---------|---------|--------------|
| Ch. 3 | Trends | Trend lines on daily charts are drawn from EOD data |
| Ch. 5 | Chart Patterns | All classic patterns (H&S, double tops) form on daily EOD charts |
| Ch. 8 | Midtrend Entry | Entry decisions made after the EOD bar prints are based on EOD data |

### When EOD Works Best vs. Not
- ✅ **EOD is ideal** → Swing trading, position trading, end-of-day analysis, most charting
- ⚠️ **EOD is insufficient** → If you place intraday orders or need real-time fills
- ❌ **EOD fails completely** → Day trading, scalping, intraday momentum strategies

---

## Tags
#price-data #end-of-day #eod #swing-trading #database #technical-analysis #chapter13
