# Data Quality and Cleaning
**Chapter:** [[Chapter_13_Index|13 — Charting and Analysis Software]]  
**Source:** Schwager, *Getting Started in Technical Analysis*, p.222–223

---

## Definition
Data quality and cleaning refers to the **process of detecting and correcting errors** in raw price data before it is used for analysis. Common errors include price spikes (exchange mis-reports), missing trading days (gaps), and zero-volume outliers. Professional data vendors clean data before delivery, but even they are not perfect — traders must remain vigilant.

---

## Simple Analogy
Data cleaning is like **proofreading a recipe** before cooking. If the recipe says "add 1,000 grams of salt" (when it should be 10 grams), you'll ruin the dish. A professional cookbook editor catches these typos — but occasionally one slips through. A smart cook always sanity-checks the quantities before pouring. In trading, an uncorrected spike can destroy a back-test result the same way a typo ruins a meal.

---

## Chart Illustration
![[charts/data_cleaning.png]]
*Top panel: dirty data (red dashes) with 3 visible price spikes vs. clean data (green). Bottom panel: after Z-score cleaning, the corrected series (blue dots) closely tracks the true values.*

---

## Real Numeric Example
Errors detected by Z-score filter (threshold = 5.0 standard deviations):

| Date | Dirty Price | True Price | Z-Score | Action |
|------|------------|------------|---------|--------|
| 2025-07-22 | $9.98 | $99.78 | −6.4 | Flagged → interpolated |
| 2025-11-11 | $10.16 | $101.60 | −6.4 | Flagged → interpolated |
| 2026-02-17 | $10.80 | $107.98 | −6.3 | Flagged → interpolated |

**Missing days:** 3 gaps filled via time interpolation.

---

## Python Code
**File:** [[code/data_cleaning.py]]
```python
# Key snippet — Z-score spike detection
import numpy as np, pandas as pd

def detect_spikes(price_series: pd.Series, threshold: float = 5.0) -> pd.Index:
    """Return timestamps of anomalous price moves (|z-score| > threshold)."""
    log_ret = np.log(price_series / price_series.shift(1)).dropna()
    z = (log_ret - log_ret.mean()) / log_ret.std()
    return z[np.abs(z) > threshold].index

def clean_series(price_series: pd.Series, threshold: float = 5.0) -> pd.Series:
    cleaned = price_series.copy()
    spikes = detect_spikes(cleaned, threshold)
    cleaned[spikes] = np.nan          # remove spikes
    cleaned = cleaned.interpolate(method='time')  # fill gaps + spikes
    return cleaned
```

---

## Relationships

### Within Chapter 13
| Concept | How They Relate |
|---------|-----------------|
| [[Historical Price Data]] | Historical data requires one-time cleaning; vendor cleans it, but errors persist |
| [[End-of-Day Price Data]] | EOD requires daily vigilance — new downloads can introduce new errors |
| [[Real-Time (Tick) Price Data]] | RT data is most error-prone (exchange mis-prints happen in real time); filtering must be instant |
| [[Continuous Futures Data]] | Roll adjustments in continuous data can introduce artificial gaps if not done correctly |
| [[Software Selection Framework]] | Better software includes automated data validation and error flagging tools |

### Outside Chapter 13
| Chapter | Concept | Relationship |
|---------|---------|--------------|
| Ch. 15 | System Testing | A single data spike can create a phantom "perfect trade" that inflates back-test results |
| Ch. 14 | Trading Systems | Signal integrity depends entirely on data integrity |
| Ch. 2 | Types of Charts | Price spikes appear as obvious visual anomalies on bar/candlestick charts |

### Most Common Data Errors to Watch For
| Error Type | Description | Detection Method |
|-----------|-------------|-----------------|
| **Price spike** | Exchange mis-report, 10× normal price | Z-score on log returns |
| **Missing day** | Holiday or transmission failure | Check against calendar |
| **Zero volume** | Data feed failure | Volume = 0 on non-holiday |
| **Duplicate row** | Feed sent twice | Deduplicate by date |
| **Adjusted vs. unadjusted** | Split/dividend adjustments missing | Compare raw vs. adjusted close |

---

## Tags
#data-quality #data-cleaning #price-spikes #missing-data #back-testing #technical-analysis #chapter13
