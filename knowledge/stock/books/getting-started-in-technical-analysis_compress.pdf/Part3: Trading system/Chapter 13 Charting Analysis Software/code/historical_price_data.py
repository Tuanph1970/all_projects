"""
Chapter 13 - Concept 1: Historical Price Data
Schwager - Getting Started in Technical Analysis

Demonstrates how to download and work with historical price data,
simulating what charting software does internally.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

# ── Simulate historical daily OHLCV data (3 years of data) ──────────────────
np.random.seed(42)
n_days = 756  # ~3 years of trading days

dates = pd.bdate_range(end=datetime.today(), periods=n_days)

# Simulate a realistic price path (geometric Brownian motion)
returns = np.random.normal(0.0003, 0.015, n_days)
close_prices = 100 * np.cumprod(1 + returns)

high_prices  = close_prices * (1 + np.abs(np.random.normal(0, 0.008, n_days)))
low_prices   = close_prices * (1 - np.abs(np.random.normal(0, 0.008, n_days)))
open_prices  = np.roll(close_prices, 1)
open_prices[0] = close_prices[0]
volume       = np.random.randint(500_000, 5_000_000, n_days)

df = pd.DataFrame({
    'Date': dates, 'Open': open_prices, 'High': high_prices,
    'Low': low_prices, 'Close': close_prices, 'Volume': volume
}).set_index('Date')

# ── Real Example ─────────────────────────────────────────────────────────────
print("=" * 55)
print("HISTORICAL PRICE DATA — COVERAGE SUMMARY")
print("=" * 55)
print(f"Date Range  : {df.index[0].date()} -> {df.index[-1].date()}")
print(f"Total Days  : {len(df)} trading days (~{len(df)/252:.1f} years)")
print(f"Price Range : ${df['Low'].min():.2f} - ${df['High'].max():.2f}")
print(f"Start/End   : ${df['Close'].iloc[0]:.2f} -> ${df['Close'].iloc[-1]:.2f}")
total_return = (df['Close'].iloc[-1] / df['Close'].iloc[0] - 1) * 100
print(f"Total Return: {total_return:+.1f}%")

# ── Visualisation ────────────────────────────────────────────────────────────
fig, axes = plt.subplots(3, 1, figsize=(14, 10),
                         gridspec_kw={'height_ratios': [3, 1, 1]})
fig.suptitle("Historical Price Data — 3-Year Daily OHLCV Dataset\n(Ch.13: Charting and Analysis Software)",
             fontsize=13, fontweight='bold')

ax1 = axes[0]
ax1.fill_between(df.index, df['Low'], df['High'],
                 alpha=0.15, color='royalblue', label='Daily Range (High-Low)')
ax1.plot(df.index, df['Close'], color='navy', linewidth=1, label='Close Price')
ax1.plot(df.index, df['Open'],  color='darkorange', linewidth=0.5,
         alpha=0.5, label='Open Price')
ax1.set_ylabel("Price ($)"); ax1.legend(fontsize=9)
ax1.set_title("3 Years of Daily OHLCV — Historical Dataset"); ax1.grid(True, alpha=0.3)
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=6))

ax2 = axes[1]
ax2.bar(df.index, df['Volume'] / 1e6, color='steelblue', alpha=0.6, width=1)
ax2.set_ylabel("Volume (M)"); ax2.set_title("Daily Volume"); ax2.grid(True, alpha=0.3)
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=6))

ax3 = axes[2]
rolling_ret = df['Close'].pct_change(252).dropna() * 100
ax3.axhline(0, color='black', linewidth=0.8, linestyle='--')
ax3.fill_between(rolling_ret.index, rolling_ret, 0,
                 where=rolling_ret >= 0, color='green', alpha=0.4, label='Positive yr')
ax3.fill_between(rolling_ret.index, rolling_ret, 0,
                 where=rolling_ret < 0, color='red', alpha=0.4, label='Negative yr')
ax3.set_ylabel("1-Yr Return %")
ax3.set_title("Rolling 1-Year Return — Why Historical Depth Matters")
ax3.legend(fontsize=8); ax3.grid(True, alpha=0.3)
ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
ax3.xaxis.set_major_locator(mdates.MonthLocator(interval=6))

plt.tight_layout()
plt.savefig("/home/claude/obsidian_ch13/charts/historical_price_data.png",
            dpi=150, bbox_inches='tight')
plt.close()
print("Chart saved.")
