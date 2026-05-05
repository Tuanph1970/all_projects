"""
Chapter 13 - Concept 2: End-of-Day Price Data
Schwager - Getting Started in Technical Analysis

Demonstrates end-of-day data: what it contains, how to build
a running database, and the difference from historical snapshots.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta

np.random.seed(7)

# ── Simulate a price database built day by day (end-of-day) ──────────────────
# Imagine a trader who started subscribing on Jan 1 last year
start_date = datetime.today() - timedelta(days=365)
trading_days = pd.bdate_range(start=start_date, end=datetime.today())

returns = np.random.normal(0.0004, 0.012, len(trading_days))
close   = 150 * np.cumprod(1 + returns)
high    = close * (1 + np.abs(np.random.normal(0, 0.006, len(trading_days))))
low     = close * (1 - np.abs(np.random.normal(0, 0.006, len(trading_days))))
open_p  = np.roll(close, 1); open_p[0] = close[0]
volume  = np.random.randint(1_000_000, 8_000_000, len(trading_days))

eod_db = pd.DataFrame({
    'Date': trading_days, 'Open': open_p, 'High': high,
    'Low': low, 'Close': close, 'Volume': volume
}).set_index('Date')

# ── Real numeric example: EOD data for last 5 days ──────────────────────────
print("=" * 65)
print("END-OF-DAY PRICE DATA — LAST 5 ENTRIES IN DATABASE")
print("=" * 65)
print(eod_db[['Open','High','Low','Close','Volume']].tail(5).round(2).to_string())
print(f"\nDatabase size   : {len(eod_db)} days")
print(f"Approx coverage : {len(eod_db)/252:.1f} year of end-of-day data")
print(f"Available hours  after market close (e.g., 6-8 PM)")
print(f"Typical cost    : $15-$50/month (vs. $200-$500/mo real-time)")

# ── Visualisation: show daily close + the idea of 'added each evening' ────
fig, axes = plt.subplots(2, 1, figsize=(14, 8),
                         gridspec_kw={'height_ratios': [3, 1]})
fig.suptitle("End-of-Day (EOD) Price Data — Database Built Daily\n(Ch.13: Charting and Analysis Software)",
             fontsize=13, fontweight='bold')

ax1 = axes[0]
ax1.plot(eod_db.index, eod_db['Close'], color='darkblue', linewidth=1.5,
         label='EOD Close Price')
ax1.fill_between(eod_db.index, eod_db['Low'], eod_db['High'],
                 alpha=0.1, color='steelblue', label='Daily High-Low Range')

# Highlight last 10 days (the most recently downloaded)
last10 = eod_db.tail(10)
ax1.scatter(last10.index, last10['Close'], color='red', s=40, zorder=5,
            label='Last 10 EOD Downloads')
ax1.axvspan(last10.index[0], last10.index[-1],
            alpha=0.08, color='red', label='Recent 2-week window')
ax1.set_ylabel("Price ($)"); ax1.legend(fontsize=9)
ax1.set_title("EOD Database: ~1 Year of Daily OHLCV (1 row added each evening)")
ax1.grid(True, alpha=0.3)
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=2))

ax2 = axes[1]
ax2.bar(eod_db.index, eod_db['Volume'] / 1e6, color='steelblue', alpha=0.5, width=1)
ax2.bar(last10.index, last10['Volume'] / 1e6, color='crimson', alpha=0.7, width=1,
        label='Recent downloads')
ax2.set_ylabel("Volume (M)"); ax2.set_title("Volume (red = most recent EOD downloads)")
ax2.legend(fontsize=8); ax2.grid(True, alpha=0.3)
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=2))

plt.tight_layout()
plt.savefig("/home/claude/obsidian_ch13/charts/end_of_day_data.png",
            dpi=150, bbox_inches='tight')
plt.close()
print("Chart saved.")
