"""
Chapter 13 - Concept 6: Continuous Futures Data
Schwager - Getting Started in Technical Analysis

Compares the three types of historical futures data:
  1. Individual contract data
  2. Nearest futures (front-month)
  3. Continuous (back-adjusted) futures
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

np.random.seed(55)

# ── Simulate futures contracts (each lasts ~3 months) ───────────────────────
n_contracts = 6
days_per_contract = 63  # ~3 months each
total_days = n_contracts * days_per_contract

dates = pd.bdate_range(end=datetime.today(), periods=total_days)

# Each contract has a small price gap at rollover (normal in futures)
contracts = {}
base_price = 100.0
for c in range(n_contracts):
    idx_start = c * days_per_contract
    idx_end   = idx_start + days_per_contract
    contract_dates = dates[idx_start:idx_end]

    # Small premium at contract inception (contango/backwardation)
    gap = np.random.uniform(-1.5, 2.0)
    if c == 0:
        gap = 0.0
    base_price = base_price + gap

    ret = np.random.normal(0.0003, 0.013, days_per_contract)
    prices = base_price * np.cumprod(1 + ret)
    contracts[f'Contract_{c+1}'] = pd.Series(prices, index=contract_dates)
    base_price = prices[-1]  # next contract starts near last price

# ── Build Nearest Futures (naive stitching — creates gaps) ──────────────────
nearest = pd.concat(contracts.values()).sort_index()

# ── Build Back-Adjusted Continuous Futures (roll adjustments applied) ────────
# Identify rollover points and compute cumulative adjustment factors
continuous = nearest.copy()
rollover_dates = [contracts[f'Contract_{c+1}'].index[0]
                  for c in range(1, n_contracts)]
cumulative_adj = 0.0

for i, roll_date in enumerate(reversed(rollover_dates)):
    prev_contract_name = f'Contract_{n_contracts - i - 1}'
    next_contract_name = f'Contract_{n_contracts - i}'
    prev_last = contracts[prev_contract_name].iloc[-1]
    next_first = contracts[next_contract_name].iloc[0]
    gap = next_first - prev_last
    cumulative_adj += gap
    roll_idx = contracts[prev_contract_name].index
    continuous[roll_idx] += cumulative_adj

# ── Numeric example ────────────────────────────────────────────────────────
print("=" * 60)
print("FUTURES DATA TYPES — NUMERIC COMPARISON")
print("=" * 60)
print(f"\nContracts simulated : {n_contracts} (each ~3 months)")
print(f"\nRollover gaps (nearest vs continuous):")
for i, roll_date in enumerate(rollover_dates):
    near_val = nearest.loc[roll_date]
    cont_val = continuous.loc[roll_date]
    print(f"  {roll_date.date()}: Nearest=${near_val:.2f}  Continuous=${cont_val:.2f}  "
          f"adj={cont_val - near_val:+.2f}")
print(f"\nFinal values (today):")
print(f"  Nearest    : ${nearest.iloc[-1]:.2f}")
print(f"  Continuous : ${continuous.iloc[-1]:.2f}")

# ── Visualisation ─────────────────────────────────────────────────────────
fig, axes = plt.subplots(3, 1, figsize=(14, 10))
fig.suptitle("Individual vs Nearest vs Continuous Futures Data\n"
             "(Ch.13: Charting and Analysis Software)", fontsize=13, fontweight='bold')

colors = plt.cm.tab10(np.linspace(0, 0.6, n_contracts))
roll_color = 'red'

# Panel 1: Individual contracts (each in its own color)
ax1 = axes[0]
for (name, series), col in zip(contracts.items(), colors):
    ax1.plot(series.index, series.values, color=col, linewidth=1.5,
             label=name.replace('_', ' '))
for roll_date in rollover_dates:
    ax1.axvline(roll_date, color=roll_color, linewidth=0.8, linestyle='--', alpha=0.5)
ax1.set_ylabel("Price ($)"); ax1.legend(fontsize=7, ncol=3)
ax1.set_title("1) Individual Contract Data — Gaps at Rollovers")
ax1.grid(True, alpha=0.3)
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))

# Panel 2: Nearest futures (visible gaps)
ax2 = axes[1]
ax2.plot(nearest.index, nearest.values, color='darkorange',
         linewidth=1.2, label='Nearest Futures (front-month)')
for roll_date in rollover_dates:
    ax2.axvline(roll_date, color=roll_color, linewidth=1, linestyle='--', alpha=0.7)
    ax2.annotate('GAP', xy=(roll_date, nearest.loc[roll_date]),
                 xytext=(5, 10), textcoords='offset points',
                 fontsize=6, color='darkred')
ax2.set_ylabel("Price ($)"); ax2.legend(fontsize=9)
ax2.set_title("2) Nearest Futures — Price Gaps at Rollover Dates (problematic for backtesting)")
ax2.grid(True, alpha=0.3)
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))

# Panel 3: Continuous (back-adjusted)
ax3 = axes[2]
ax3.plot(continuous.index, continuous.values, color='darkgreen',
         linewidth=1.5, label='Continuous (Back-Adjusted)')
ax3.plot(nearest.index, nearest.values, color='darkorange',
         linewidth=0.8, alpha=0.4, linestyle=':', label='Nearest (for reference)')
ax3.set_ylabel("Price ($)"); ax3.legend(fontsize=9)
ax3.set_title("3) Continuous Futures — Smooth, Gap-Free (best for system testing)")
ax3.grid(True, alpha=0.3)
ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))

plt.tight_layout()
plt.savefig("/home/claude/obsidian_ch13/charts/continuous_futures.png",
            dpi=150, bbox_inches='tight')
plt.close()
print("Chart saved.")
