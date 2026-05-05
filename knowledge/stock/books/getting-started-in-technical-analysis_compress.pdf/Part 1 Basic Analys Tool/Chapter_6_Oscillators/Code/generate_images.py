"""
Generate all visualization images for Chapter 6 concepts.
Outputs PNG files into /home/claude/chapter6/Images/
"""
import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from oscillators_master import (
    generate_synthetic_prices, momentum, rate_of_change, rate_of_change_pct,
    ma_oscillator, price_oscillator, macd, rsi, stochastic, slow_stochastic,
    detect_divergence, find_pivots
)

OUT = "/home/claude/chapter6/Images"
os.makedirs(OUT, exist_ok=True)

# Build dataset once and reuse
df = generate_synthetic_prices(n_days=200, seed=42)
np.random.seed(7)
df['high'] = df['close'] * (1 + np.random.uniform(0, 0.015, len(df)))
df['low'] = df['close'] * (1 - np.random.uniform(0, 0.015, len(df)))

plt.rcParams.update({
    'figure.figsize': (12, 7),
    'axes.grid': True,
    'grid.alpha': 0.3,
    'font.size': 10,
})

def save(fig, name):
    path = os.path.join(OUT, name)
    fig.tight_layout()
    fig.savefig(path, dpi=110, bbox_inches='tight')
    plt.close(fig)
    print("Saved", path)

# -----------------------------------------------------------------------------
# 1. Momentum chart
# -----------------------------------------------------------------------------
fig, axes = plt.subplots(2, 1, sharex=True, gridspec_kw={'height_ratios': [2, 1]})
axes[0].plot(df.index, df['close'], color='steelblue', label='Close')
axes[0].set_title('Price with 10-day Momentum')
axes[0].set_ylabel('Price ($)')
axes[0].legend()

mom = momentum(df['close'], 10)
axes[1].plot(df.index, mom, color='darkorange', label='Momentum (10)')
axes[1].axhline(0, color='black', lw=1)
axes[1].fill_between(df.index, mom, 0, where=(mom >= 0), alpha=0.25, color='green')
axes[1].fill_between(df.index, mom, 0, where=(mom < 0), alpha=0.25, color='red')
axes[1].set_ylabel('Momentum')
axes[1].legend()
save(fig, '01_momentum.png')

# -----------------------------------------------------------------------------
# 2. ROC chart
# -----------------------------------------------------------------------------
fig, axes = plt.subplots(2, 1, sharex=True, gridspec_kw={'height_ratios': [2, 1]})
axes[0].plot(df.index, df['close'], color='steelblue', label='Close')
axes[0].set_title('Price with 10-day Rate of Change (ROC)')
axes[0].set_ylabel('Price ($)')
axes[0].legend()

roc = rate_of_change(df['close'], 10)
axes[1].plot(df.index, roc, color='purple', label='ROC ratio')
axes[1].axhline(1.0, color='black', lw=1, label='Equilibrium (1.0)')
axes[1].set_ylabel('ROC')
axes[1].legend()
save(fig, '02_roc.png')

# -----------------------------------------------------------------------------
# 3. Equilibrium line illustration (combined momentum + ROC like Fig 6.2)
# -----------------------------------------------------------------------------
fig, axes = plt.subplots(3, 1, sharex=True, gridspec_kw={'height_ratios': [2, 1, 1]})
axes[0].plot(df.index, df['close'], color='steelblue')
axes[0].set_title('Equilibrium Line: separates positive and negative momentum')
axes[0].set_ylabel('Price ($)')

axes[1].plot(df.index, mom, color='darkorange')
axes[1].axhline(0, color='red', lw=1.5, label='Equilibrium (0)')
axes[1].set_ylabel('Momentum')
axes[1].legend()

axes[2].plot(df.index, roc, color='purple')
axes[2].axhline(1.0, color='red', lw=1.5, label='Equilibrium (1.0)')
axes[2].set_ylabel('ROC')
axes[2].legend()
save(fig, '03_equilibrium_line.png')

# -----------------------------------------------------------------------------
# 4. Moving Average Oscillator
# -----------------------------------------------------------------------------
fig, axes = plt.subplots(2, 1, sharex=True, gridspec_kw={'height_ratios': [2, 1]})
ma20 = df['close'].rolling(20).mean()
axes[0].plot(df.index, df['close'], color='steelblue', label='Close')
axes[0].plot(df.index, ma20, color='red', label='20-day MA')
axes[0].set_title('Price - Moving Average Oscillator')
axes[0].set_ylabel('Price ($)')
axes[0].legend()

osc = ma_oscillator(df['close'], 20)
axes[1].plot(df.index, osc, color='teal')
axes[1].axhline(0, color='black', lw=1)
axes[1].fill_between(df.index, osc, 0, where=(osc >= 0), alpha=0.3, color='green')
axes[1].fill_between(df.index, osc, 0, where=(osc < 0), alpha=0.3, color='red')
axes[1].set_ylabel('Price - MA(20)')
save(fig, '04_ma_oscillator.png')

# -----------------------------------------------------------------------------
# 5. Price Oscillator
# -----------------------------------------------------------------------------
fig, axes = plt.subplots(2, 1, sharex=True, gridspec_kw={'height_ratios': [2, 1]})
ma10 = df['close'].rolling(10).mean()
axes[0].plot(df.index, df['close'], color='steelblue', label='Close', alpha=0.6)
axes[0].plot(df.index, ma10, color='orange', label='10-day MA')
axes[0].plot(df.index, ma20, color='red', label='20-day MA')
axes[0].set_title('Price Oscillator: short MA - long MA')
axes[0].set_ylabel('Price ($)')
axes[0].legend()

posc = price_oscillator(df['close'], 10, 20)
axes[1].plot(df.index, posc, color='darkgreen')
axes[1].axhline(0, color='black', lw=1)
axes[1].fill_between(df.index, posc, 0, where=(posc >= 0), alpha=0.3, color='green')
axes[1].fill_between(df.index, posc, 0, where=(posc < 0), alpha=0.3, color='red')
axes[1].set_ylabel('MA(10) - MA(20)')
save(fig, '05_price_oscillator.png')

# -----------------------------------------------------------------------------
# 6. MACD
# -----------------------------------------------------------------------------
fig, axes = plt.subplots(2, 1, sharex=True, gridspec_kw={'height_ratios': [2, 1]})
axes[0].plot(df.index, df['close'], color='steelblue', label='Close')
axes[0].set_title('MACD (12, 26, 9)')
axes[0].set_ylabel('Price ($)')
axes[0].legend()

macd_line, signal_line, hist = macd(df['close'])
axes[1].plot(df.index, macd_line, color='blue', label='MACD line')
axes[1].plot(df.index, signal_line, color='red', label='Signal line (9 EMA)')
axes[1].bar(df.index, hist, color=['green' if h > 0 else 'red' for h in hist],
            alpha=0.5, label='Histogram')
axes[1].axhline(0, color='black', lw=0.8)
axes[1].set_ylabel('MACD')
axes[1].legend(loc='upper left', fontsize=8)
save(fig, '06_macd.png')

# -----------------------------------------------------------------------------
# 7. Overbought/Oversold on momentum (mirrors Schwager Fig. 6.7)
# -----------------------------------------------------------------------------
fig, axes = plt.subplots(2, 1, sharex=True, gridspec_kw={'height_ratios': [2, 1]})
axes[0].plot(df.index, df['close'], color='steelblue')
axes[0].set_title('Overbought / Oversold zones on Momentum')
axes[0].set_ylabel('Price ($)')

ob = mom.quantile(0.90)
os_ = mom.quantile(0.10)
axes[1].plot(df.index, mom, color='darkorange')
axes[1].axhline(ob, color='red', ls='--', label=f'Overbought ({ob:.2f})')
axes[1].axhline(os_, color='green', ls='--', label=f'Oversold ({os_:.2f})')
axes[1].axhline(0, color='black', lw=0.8)
axes[1].fill_between(df.index, mom, ob, where=(mom > ob), color='red', alpha=0.3)
axes[1].fill_between(df.index, mom, os_, where=(mom < os_), color='green', alpha=0.3)
axes[1].legend(fontsize=8)
axes[1].set_ylabel('Momentum')
save(fig, '07_overbought_oversold.png')

# -----------------------------------------------------------------------------
# 8. RSI
# -----------------------------------------------------------------------------
fig, axes = plt.subplots(2, 1, sharex=True, gridspec_kw={'height_ratios': [2, 1]})
axes[0].plot(df.index, df['close'], color='steelblue')
axes[0].set_title('Relative Strength Index (14-day)')
axes[0].set_ylabel('Price ($)')

rsi_vals = rsi(df['close'], 14)
axes[1].plot(df.index, rsi_vals, color='purple')
axes[1].axhline(70, color='red', ls='--', label='Overbought (70)')
axes[1].axhline(30, color='green', ls='--', label='Oversold (30)')
axes[1].axhline(50, color='gray', lw=0.8)
axes[1].fill_between(df.index, rsi_vals, 70, where=(rsi_vals > 70), color='red', alpha=0.3)
axes[1].fill_between(df.index, rsi_vals, 30, where=(rsi_vals < 30), color='green', alpha=0.3)
axes[1].set_ylim(0, 100)
axes[1].set_ylabel('RSI')
axes[1].legend(fontsize=8)
save(fig, '08_rsi.png')

# -----------------------------------------------------------------------------
# 9. Stochastics (slow)
# -----------------------------------------------------------------------------
fig, axes = plt.subplots(2, 1, sharex=True, gridspec_kw={'height_ratios': [2, 1]})
axes[0].plot(df.index, df['close'], color='steelblue')
axes[0].set_title('Slow Stochastic (14, 3, 3)')
axes[0].set_ylabel('Price ($)')

slow_k, slow_d = slow_stochastic(df['high'], df['low'], df['close'])
axes[1].plot(df.index, slow_k, color='blue', label='%K (slow)')
axes[1].plot(df.index, slow_d, color='red', label='%D (slow)')
axes[1].axhline(80, color='red', ls='--', label='Overbought (80)')
axes[1].axhline(20, color='green', ls='--', label='Oversold (20)')
axes[1].set_ylim(0, 100)
axes[1].set_ylabel('Stochastic')
axes[1].legend(fontsize=8)
save(fig, '09_stochastics.png')

# -----------------------------------------------------------------------------
# 10. Divergence visualization
# -----------------------------------------------------------------------------
fig, axes = plt.subplots(2, 1, sharex=True, gridspec_kw={'height_ratios': [2, 1]})
axes[0].plot(df.index, df['close'], color='steelblue')
axes[0].set_title('Bullish & Bearish Divergence (price vs RSI)')
axes[0].set_ylabel('Price ($)')

bearish, bullish = detect_divergence(df['close'], rsi_vals, window=7)
for p_idx, o_idx in bearish[:3]:
    axes[0].annotate('Bearish Div',
                     xy=(df.index[p_idx], df['close'].iloc[p_idx]),
                     xytext=(df.index[p_idx], df['close'].iloc[p_idx] * 1.08),
                     arrowprops=dict(arrowstyle='->', color='red'),
                     color='red', fontsize=8)
for p_idx, o_idx in bullish[:3]:
    axes[0].annotate('Bullish Div',
                     xy=(df.index[p_idx], df['close'].iloc[p_idx]),
                     xytext=(df.index[p_idx], df['close'].iloc[p_idx] * 0.92),
                     arrowprops=dict(arrowstyle='->', color='green'),
                     color='green', fontsize=8)

axes[1].plot(df.index, rsi_vals, color='purple')
axes[1].axhline(70, color='red', ls='--', alpha=0.5)
axes[1].axhline(30, color='green', ls='--', alpha=0.5)
axes[1].set_ylim(0, 100)
axes[1].set_ylabel('RSI(14)')
save(fig, '10_divergence.png')

# -----------------------------------------------------------------------------
# 11. Trading-Alert workflow (oscillator alert + price confirmation)
# -----------------------------------------------------------------------------
fig, axes = plt.subplots(2, 1, sharex=True, gridspec_kw={'height_ratios': [2, 1]})
axes[0].plot(df.index, df['close'], color='steelblue', label='Close')
# alerts: where RSI > 70 (overbought)
alerts = df.index[rsi_vals > 70]
for d in alerts[:5]:
    axes[0].axvline(d, color='orange', alpha=0.4, ls=':')
axes[0].set_title('Oscillators as Trading Alerts (orange = alert, red = confirmed entry)')
axes[0].set_ylabel('Price ($)')

# confirmation: alert + 2-day price drop
confirmations = []
for d in alerts:
    pos = df.index.get_loc(d)
    if pos < len(df) - 3:
        if df['close'].iloc[pos + 2] < df['close'].iloc[pos]:
            confirmations.append(df.index[pos + 2])
for d in confirmations[:5]:
    axes[0].scatter(d, df.loc[d, 'close'], color='red', s=80, marker='v', zorder=5)
axes[0].legend()

axes[1].plot(df.index, rsi_vals, color='purple')
axes[1].axhline(70, color='red', ls='--', label='Alert level')
axes[1].set_ylim(0, 100)
axes[1].set_ylabel('RSI(14)')
axes[1].legend(fontsize=8)
save(fig, '11_trading_alerts.png')

# -----------------------------------------------------------------------------
# 12. Sensitivity comparison: 5-day vs 20-day momentum (mirrors Fig. 6.3)
# -----------------------------------------------------------------------------
fig, axes = plt.subplots(3, 1, sharex=True, gridspec_kw={'height_ratios': [2, 1, 1]})
axes[0].plot(df.index, df['close'], color='steelblue')
axes[0].set_title('Sensitivity: 5-day vs 20-day Momentum')
axes[0].set_ylabel('Price ($)')

mom5 = momentum(df['close'], 5)
mom20 = momentum(df['close'], 20)
axes[1].plot(df.index, mom5, color='darkorange')
axes[1].axhline(0, color='black', lw=0.8)
axes[1].set_ylabel('Momentum (5)')
axes[2].plot(df.index, mom20, color='brown')
axes[2].axhline(0, color='black', lw=0.8)
axes[2].set_ylabel('Momentum (20)')
save(fig, '12_sensitivity.png')

print("\nAll images generated.")
