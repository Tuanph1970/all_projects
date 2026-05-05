"""
Chapter 13 - Concept 3: Real-Time (Tick) Price Data
Schwager - Getting Started in Technical Analysis

Simulates intraday tick-level price data and compares
real-time vs delayed (15-min) vs EOD views of the same day.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta

np.random.seed(99)

# ── Simulate one trading day of tick data (9:30 AM - 4:00 PM) ───────────────
market_open  = datetime(2026, 4, 29, 9, 30, 0)
market_close = datetime(2026, 4, 29, 16, 0, 0)
trading_seconds = int((market_close - market_open).total_seconds())
n_ticks = 3000  # ~3000 trades in a day for a liquid stock

tick_times = sorted([
    market_open + timedelta(seconds=int(s))
    for s in np.random.choice(trading_seconds, n_ticks, replace=False)
])

tick_prices = 200.0 + np.cumsum(np.random.normal(0, 0.05, n_ticks))
tick_sizes  = np.random.randint(100, 5000, n_ticks)

ticks = pd.DataFrame({'Price': tick_prices, 'Size': tick_sizes},
                     index=pd.DatetimeIndex(tick_times))

# ── Aggregate to different resolutions ─────────────────────────────────────
def to_ohlcv(df, freq):
    agg = df['Price'].resample(freq).ohlc().dropna()
    agg['Volume'] = df['Size'].resample(freq).sum()
    return agg

rt_1min   = to_ohlcv(ticks, '1min')   # real-time (1-min bars)
delayed   = to_ohlcv(ticks, '15min')  # 15-min delayed
eod_bar   = to_ohlcv(ticks, '1D')     # end-of-day single bar

# ── Numeric example ──────────────────────────────────────────────────────────
print("=" * 60)
print("REAL-TIME vs DELAYED vs EOD — SAME TRADING DAY")
print("=" * 60)
print(f"\nTotal ticks recorded  : {len(ticks):,}")
print(f"Price range today      : ${ticks['Price'].min():.2f} - ${ticks['Price'].max():.2f}")
print(f"\n1-min bars (real-time) : {len(rt_1min)} bars")
print(f"15-min bars (delayed)  : {len(delayed)} bars")
print(f"EOD bar                : {len(eod_bar)} bar")
print(f"\nEOD Summary:")
print(f"  Open : ${eod_bar['open'].iloc[0]:.2f}")
print(f"  High : ${eod_bar['high'].iloc[0]:.2f}")
print(f"  Low  : ${eod_bar['low'].iloc[0]:.2f}")
print(f"  Close: ${eod_bar['close'].iloc[0]:.2f}")

# ── Visualisation: 3 panels showing the same day at different resolutions ───
fig, axes = plt.subplots(3, 1, figsize=(14, 10))
fig.suptitle("Real-Time vs Delayed vs EOD — The Same Trading Day\n(Ch.13: Charting and Analysis Software)",
             fontsize=13, fontweight='bold')

time_fmt = mdates.DateFormatter('%H:%M')

# Panel 1: Real-time (all ticks as scatter)
ax1 = axes[0]
ax1.scatter(ticks.index, ticks['Price'], s=1, color='navy', alpha=0.4)
ax1.plot(rt_1min.index, rt_1min['close'], color='royalblue', linewidth=0.8,
         label='1-min close (real-time)')
ax1.set_ylabel("Price ($)"); ax1.legend(fontsize=9)
ax1.set_title("Real-Time: Every Tick + 1-Minute Bars"); ax1.grid(True, alpha=0.3)
ax1.xaxis.set_major_formatter(time_fmt)

# Panel 2: 15-min delayed bars
ax2 = axes[1]
for idx, row in delayed.iterrows():
    color = 'green' if row['close'] >= row['open'] else 'red'
    ax2.plot([idx, idx], [row['low'], row['high']], color=color, linewidth=1.5)
    ax2.plot([idx, idx + pd.Timedelta('14min')],
             [row['open'], row['open']], color=color, linewidth=2)
    ax2.plot([idx, idx + pd.Timedelta('14min')],
             [row['close'], row['close']], color=color, linewidth=2)
ax2.set_ylabel("Price ($)")
ax2.set_title("15-Min Delayed Data (fraction of real-time cost)"); ax2.grid(True, alpha=0.3)
ax2.xaxis.set_major_formatter(time_fmt)

# Panel 3: EOD - just one bar & summary annotation
ax3 = axes[2]
row = eod_bar.iloc[0]
ax3.barh(0, row['close'] - row['open'], left=row['open'], height=0.3,
         color='green' if row['close'] >= row['open'] else 'red', alpha=0.7)
ax3.plot([row['low'], row['high']], [0, 0], 'k-', linewidth=2)
ax3.set_yticks([])
ax3.set_xlabel("Price ($)")
ax3.set_title(f"End-of-Day: Single Bar | O={row['open']:.2f}  H={row['high']:.2f}  "
              f"L={row['low']:.2f}  C={row['close']:.2f}")
ax3.grid(True, alpha=0.3, axis='x')
ax3.set_xlim(row['low'] - 1, row['high'] + 1)

plt.tight_layout()
plt.savefig("/home/claude/obsidian_ch13/charts/real_time_data.png",
            dpi=150, bbox_inches='tight')
plt.close()
print("Chart saved.")
