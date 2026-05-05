"""
Chapter 13 - Concept 5: Data Quality & Cleaning
Schwager - Getting Started in Technical Analysis

Demonstrates common data errors (missing days, price spikes)
and how to detect and clean them — a critical step that
professional data vendors perform before delivery.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

np.random.seed(21)

# ── Generate clean price series ──────────────────────────────────────────────
n = 252
dates  = pd.bdate_range(end=datetime.today(), periods=n)
clean  = 100 * np.cumprod(1 + np.random.normal(0.0003, 0.012, n))

# ── Inject common data errors ────────────────────────────────────────────────
dirty = clean.copy()

# Error type 1: Price spike (exchange mis-report)
spike_idx = [50, 130, 200]
for i in spike_idx:
    dirty[i] = dirty[i] * np.random.choice([5.5, 0.1])  # 10x spike or near-zero

# Error type 2: Missing days (gaps) — set 3 values to NaN
missing_idx = [80, 81, 160]
dirty_series = pd.Series(dirty, index=dates)
dirty_series.iloc[missing_idx] = np.nan

# ── Cleaning: spike detection using Z-score on log returns ──────────────────
dirty_clean = dirty_series.copy()

log_ret = np.log(dirty_clean / dirty_clean.shift(1)).dropna()
z_scores = (log_ret - log_ret.mean()) / log_ret.std()

SPIKE_THRESHOLD = 5.0  # flag moves > 5 std devs
spikes_found = z_scores[np.abs(z_scores) > SPIKE_THRESHOLD]

# Replace spikes with interpolated values
dirty_clean[spikes_found.index] = np.nan
dirty_clean = dirty_clean.interpolate(method='time')  # fill gaps too

print("=" * 55)
print("DATA QUALITY & CLEANING — DIAGNOSTIC REPORT")
print("=" * 55)
print(f"Dataset       : {n} trading days")
print(f"\nErrors injected:")
print(f"  Price spikes  : {len(spike_idx)} occurrences")
print(f"  Missing days  : {len(missing_idx)} gaps")
print(f"\nErrors detected by Z-score filter (threshold={SPIKE_THRESHOLD}):")
print(f"  Flagged       : {len(spikes_found)} points")
for ts, z in spikes_found.items():
    print(f"    {ts.date()}  z-score={z:.1f}  "
          f"dirty=${dirty_series[ts]:.2f}  clean=${clean[dates.get_loc(ts)]:.2f}")
print(f"\nMissing values : {dirty_series.isna().sum()} → filled via time interpolation")

# ── Visualisation ─────────────────────────────────────────────────────────
fig, axes = plt.subplots(2, 1, figsize=(14, 9))
fig.suptitle("Data Quality & Cleaning — Detecting Errors Before Analysis\n"
             "(Ch.13: Charting and Analysis Software)", fontsize=13, fontweight='bold')

ax1 = axes[0]
ax1.plot(dates, clean, color='green', linewidth=1.5, label='True/Clean data', zorder=3)
ax1.plot(dates, dirty_series.values, color='red', linewidth=1,
         alpha=0.7, label='Dirty data (with errors)', linestyle='--')
for i in spike_idx:
    ax1.axvline(dates[i], color='red', linewidth=1, alpha=0.5)
    ax1.annotate('SPIKE', xy=(dates[i], dirty[i]),
                 fontsize=7, color='darkred', ha='center')
for i in missing_idx:
    ax1.axvline(dates[i], color='orange', linewidth=1.5, alpha=0.7)
ax1.set_ylabel("Price ($)"); ax1.legend(fontsize=9)
ax1.set_title("Raw vs Dirty Data — Errors Clearly Visible"); ax1.grid(True, alpha=0.3)
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=3))

ax2 = axes[1]
ax2.plot(dates, clean, color='green', linewidth=1.5, label='True data')
ax2.plot(dirty_clean.index, dirty_clean.values, color='royalblue',
         linewidth=1.2, linestyle=':', label='After cleaning (interpolated)')
ax2.fill_between(dates,
                 np.minimum(clean, dirty_clean.reindex(dates).values),
                 np.maximum(clean, dirty_clean.reindex(dates).values),
                 alpha=0.15, color='orange', label='Residual error after cleaning')
ax2.set_ylabel("Price ($)"); ax2.legend(fontsize=9)
ax2.set_title("After Cleaning — Very Close to True Data"); ax2.grid(True, alpha=0.3)
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=3))

plt.tight_layout()
plt.savefig("/home/claude/obsidian_ch13/charts/data_cleaning.png",
            dpi=150, bbox_inches='tight')
plt.close()
print("Chart saved.")
