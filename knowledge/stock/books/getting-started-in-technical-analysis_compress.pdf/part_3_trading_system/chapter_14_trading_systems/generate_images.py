"""Generate illustrative charts for all Chapter 14 concepts.
Uses synthesized OHLC data so the images are original educational visuals.
"""
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import os

np.random.seed(42)
OUT = "/home/claude/ch14/images"
os.makedirs(OUT, exist_ok=True)

# ---------- helpers ----------
def make_trending_series(n=200, start=100, drift=0.15, noise=1.2, seed=42):
    rng = np.random.default_rng(seed)
    steps = rng.normal(drift, noise, n)
    return start + np.cumsum(steps)

def make_choppy_series(n=200, start=100, noise=1.5, seed=7):
    rng = np.random.default_rng(seed)
    return start + np.cumsum(rng.normal(0, noise, n))

def style_axes(ax, title):
    ax.set_title(title, fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.set_xlabel('Trading Day')
    ax.set_ylabel('Price')

# ---------- 1. Fast vs Slow Trend-Following ----------
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
prices = make_trending_series(150, 100, 0.2, 1.5, 11)

def breakout_signals(p, n):
    signals = []
    pos = 0
    for i in range(n, len(p)):
        hi = max(p[i-n:i]); lo = min(p[i-n:i])
        if p[i] > hi and pos != 1:
            signals.append((i, p[i], 'B')); pos = 1
        elif p[i] < lo and pos != -1:
            signals.append((i, p[i], 'S')); pos = -1
    return signals

for ax, n, label in [(axes[0], 7, 'Fast (N=7)'), (axes[1], 40, 'Slow (N=40)')]:
    ax.plot(prices, color='steelblue', lw=1.5)
    sigs = breakout_signals(prices, n)
    for i, p, s in sigs:
        if s == 'B':
            ax.scatter(i, p, marker='^', color='green', s=120, zorder=5)
        else:
            ax.scatter(i, p, marker='v', color='red', s=120, zorder=5)
    style_axes(ax, f'{label} Breakout System ({len(sigs)} signals)')

plt.suptitle('Fast vs Slow Trend-Following Systems', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(f'{OUT}/01_fast_vs_slow.png', dpi=110, bbox_inches='tight')
plt.close()

# ---------- 2. Simple Moving Average ----------
fig, ax = plt.subplots(figsize=(12, 5))
prices = make_trending_series(150, 100, 0.18, 1.2, 22)
ma = np.convolve(prices, np.ones(20)/20, mode='valid')
ax.plot(prices, color='steelblue', lw=1.5, label='Price')
ax.plot(range(19, len(prices)), ma, color='orange', lw=2, label='20-day SMA')

# crossover signals
pos = 0
for i in range(20, len(prices)):
    if prices[i] > ma[i-19] and prices[i-1] <= ma[i-20] and pos != 1:
        ax.scatter(i, prices[i], marker='^', color='green', s=120, zorder=5)
        pos = 1
    elif prices[i] < ma[i-19] and prices[i-1] >= ma[i-20] and pos != -1:
        ax.scatter(i, prices[i], marker='v', color='red', s=120, zorder=5)
        pos = -1

style_axes(ax, 'Simple Moving Average Crossover Signals (20-day)')
ax.legend(loc='upper left')
plt.tight_layout()
plt.savefig(f'{OUT}/02_simple_ma.png', dpi=110, bbox_inches='tight')
plt.close()

# ---------- 3. Weighted Moving Averages: SMA vs LWMA vs EWMA ----------
fig, ax = plt.subplots(figsize=(12, 5))
prices = make_trending_series(120, 100, 0.2, 1.0, 33)
N = 15

# SMA
sma = np.convolve(prices, np.ones(N)/N, mode='valid')

# LWMA (linear weights)
weights = np.arange(1, N+1)
lwma = np.array([np.dot(prices[i:i+N], weights)/weights.sum() for i in range(len(prices)-N+1)])

# EWMA
alpha = 2/(N+1)
ewma = np.zeros(len(prices))
ewma[0] = prices[0]
for i in range(1, len(prices)):
    ewma[i] = alpha*prices[i] + (1-alpha)*ewma[i-1]

ax.plot(prices, color='lightgray', lw=1.5, label='Price')
ax.plot(range(N-1, len(prices)), sma, color='blue', lw=2, label=f'SMA({N})')
ax.plot(range(N-1, len(prices)), lwma, color='green', lw=2, label=f'LWMA({N})')
ax.plot(ewma, color='red', lw=2, label=f'EWMA({N})')
style_axes(ax, 'Three Moving Averages: SMA vs LWMA vs EWMA')
ax.legend(loc='upper left')
plt.tight_layout()
plt.savefig(f'{OUT}/03_weighted_ma.png', dpi=110, bbox_inches='tight')
plt.close()

# ---------- 4. Crossover MA system ----------
fig, ax = plt.subplots(figsize=(12, 5))
prices = make_trending_series(180, 100, 0.15, 1.3, 44)
short_ma = np.convolve(prices, np.ones(10)/10, mode='valid')
long_ma = np.convolve(prices, np.ones(40)/40, mode='valid')

ax.plot(prices, color='steelblue', lw=1.3, label='Price', alpha=0.7)
ax.plot(range(9, len(prices)), short_ma, color='orange', lw=2, label='10-day MA')
ax.plot(range(39, len(prices)), long_ma, color='red', lw=2, label='40-day MA')

# Generate crossover signals
short_aligned = short_ma[30:]  # align with long_ma starting point
days = np.arange(39, len(prices))
prev_diff = short_aligned[0] - long_ma[0]
for i in range(1, len(long_ma)):
    diff = short_aligned[i] - long_ma[i]
    day = days[i]
    if prev_diff < 0 and diff > 0:
        ax.scatter(day, prices[day], marker='^', color='green', s=140, zorder=5, edgecolors='black')
    elif prev_diff > 0 and diff < 0:
        ax.scatter(day, prices[day], marker='v', color='red', s=140, zorder=5, edgecolors='black')
    prev_diff = diff

style_axes(ax, 'Crossover Moving Average System (10 & 40)')
ax.legend(loc='upper left')
plt.tight_layout()
plt.savefig(f'{OUT}/04_crossover_ma.png', dpi=110, bbox_inches='tight')
plt.close()

# ---------- 5. Breakout system ----------
fig, ax = plt.subplots(figsize=(12, 5))
prices = make_trending_series(150, 100, 0.2, 1.4, 55)
N = 20

upper = np.array([max(prices[max(0, i-N):i]) if i >= N else np.nan for i in range(len(prices))])
lower = np.array([min(prices[max(0, i-N):i]) if i >= N else np.nan for i in range(len(prices))])

ax.plot(prices, color='steelblue', lw=1.5, label='Price')
ax.plot(upper, color='green', lw=1, ls='--', alpha=0.7, label=f'{N}-day high')
ax.plot(lower, color='red', lw=1, ls='--', alpha=0.7, label=f'{N}-day low')

pos = 0
for i in range(N, len(prices)):
    if prices[i] > upper[i-1] and pos != 1:
        ax.scatter(i, prices[i], marker='^', color='green', s=140, zorder=5, edgecolors='black')
        pos = 1
    elif prices[i] < lower[i-1] and pos != -1:
        ax.scatter(i, prices[i], marker='v', color='red', s=140, zorder=5, edgecolors='black')
        pos = -1

style_axes(ax, f'Breakout System (N={N}): Buy on new {N}-day high, Sell on new {N}-day low')
ax.legend(loc='upper left')
plt.tight_layout()
plt.savefig(f'{OUT}/05_breakout.png', dpi=110, bbox_inches='tight')
plt.close()

# ---------- 6. Confirmation conditions ----------
fig, axes = plt.subplots(3, 1, figsize=(13, 11))
prices = make_choppy_series(140, 100, 1.3, 66)
prices[60:90] = prices[60:90] + np.linspace(0, 12, 30)  # add a real trend
N = 15

# Plot 1: Penetration confirmation
ax = axes[0]
upper = np.array([max(prices[max(0,i-N):i]) if i >= N else np.nan for i in range(len(prices))])
lower = np.array([min(prices[max(0,i-N):i]) if i >= N else np.nan for i in range(len(prices))])
ax.plot(prices, color='steelblue', lw=1.5)
basic_buys = [i for i in range(N, len(prices)) if prices[i] > upper[i-1]]
confirmed_buys = [i for i in basic_buys if prices[i] > upper[i-1]*1.02]
for i in basic_buys:
    ax.scatter(i, prices[i], marker='^', color='lightgreen', s=80, zorder=4, label='Basic signal' if i==basic_buys[0] else '')
for i in confirmed_buys:
    ax.scatter(i, prices[i], marker='^', color='darkgreen', s=160, zorder=5, edgecolors='black', label='Confirmed (2% penetration)' if i==confirmed_buys[0] else '')
style_axes(ax, '(1) Penetration Confirmation: only signals breaking the level by ≥2%')
ax.legend(loc='upper left')

# Plot 2: Time delay
ax = axes[1]
ax.plot(prices, color='steelblue', lw=1.5)
delayed = []
for i in basic_buys:
    if i+5 < len(prices) and prices[i+5] > prices[i]:
        delayed.append(i+5)
for i in basic_buys:
    ax.scatter(i, prices[i], marker='^', color='lightgreen', s=80, zorder=4)
for i in delayed:
    ax.scatter(i, prices[i], marker='^', color='darkgreen', s=160, zorder=5, edgecolors='black')
style_axes(ax, '(2) Time-Delay Confirmation: re-evaluate 5 days later')

# Plot 3: Pattern (3 thrust days)
ax = axes[2]
ax.plot(prices, color='steelblue', lw=1.5)
thrust_confirmed = []
for i in basic_buys:
    cnt = 0
    for j in range(i+1, min(i+15, len(prices))):
        if prices[j] > prices[j-1]:
            cnt += 1
            if cnt >= 3:
                thrust_confirmed.append(j); break
        else:
            cnt = 0
for i in basic_buys:
    ax.scatter(i, prices[i], marker='^', color='lightgreen', s=80, zorder=4)
for i in thrust_confirmed:
    ax.scatter(i, prices[i], marker='^', color='darkgreen', s=160, zorder=5, edgecolors='black')
style_axes(ax, '(3) Pattern Confirmation: 3 thrust days after the signal')

plt.suptitle('Three Confirmation Conditions Reduce False Signals', fontsize=14, fontweight='bold', y=1.0)
plt.tight_layout()
plt.savefig(f'{OUT}/06_confirmation.png', dpi=110, bbox_inches='tight')
plt.close()

# ---------- 7. Filter ----------
fig, axes = plt.subplots(2, 1, figsize=(13, 9))
prices = make_trending_series(180, 100, 0.18, 1.5, 77)
N = 20
ma = np.convolve(prices, np.ones(N)/N, mode='valid')

# Without filter
ax = axes[0]
ax.plot(prices, color='steelblue', lw=1.4, label='Price')
ax.plot(range(N-1, len(prices)), ma, color='orange', lw=2, label=f'{N}-day MA')
pos = 0
for i in range(N, len(prices)):
    idx = i - (N-1)
    if prices[i] > ma[idx] and prices[i-1] <= ma[idx-1] and pos != 1:
        ax.scatter(i, prices[i], marker='^', color='green', s=110, zorder=5)
        pos = 1
    elif prices[i] < ma[idx] and prices[i-1] >= ma[idx-1] and pos != -1:
        ax.scatter(i, prices[i], marker='v', color='red', s=110, zorder=5)
        pos = -1
style_axes(ax, 'WITHOUT Filter — many whipsaw trades')
ax.legend(loc='upper left')

# With filter (signal only if MA itself is moving in direction of trade)
ax = axes[1]
ax.plot(prices, color='steelblue', lw=1.4, label='Price')
ax.plot(range(N-1, len(prices)), ma, color='orange', lw=2, label=f'{N}-day MA')
pos = 0
for i in range(N+1, len(prices)):
    idx = i - (N-1)
    ma_rising = ma[idx] > ma[idx-1]
    if prices[i] > ma[idx] and prices[i-1] <= ma[idx-1] and ma_rising and pos != 1:
        ax.scatter(i, prices[i], marker='^', color='green', s=110, zorder=5, edgecolors='black')
        pos = 1
    elif prices[i] < ma[idx] and prices[i-1] >= ma[idx-1] and not ma_rising and pos != -1:
        ax.scatter(i, prices[i], marker='v', color='red', s=110, zorder=5, edgecolors='black')
        pos = -1
style_axes(ax, 'WITH Filter (only take signals consistent with MA direction)')
ax.legend(loc='upper left')

plt.suptitle('Filter Rule Eliminates Lower-Probability Trades', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(f'{OUT}/07_filter.png', dpi=110, bbox_inches='tight')
plt.close()

# ---------- 8. Market Characteristic Adjustments ----------
fig, ax = plt.subplots(figsize=(12, 5))

# Two regimes: low-vol then high-vol
seg1 = make_trending_series(80, 100, 0.05, 0.4, 100)
seg2 = make_trending_series(80, seg1[-1], 0.10, 2.0, 200)
prices = np.concatenate([seg1, seg2])

# Compute rolling 50-day range as volatility proxy
vol = np.zeros(len(prices))
for i in range(len(prices)):
    win = prices[max(0,i-50):i+1]
    vol[i] = (win.max() - win.min()) / win.mean() if len(win) > 1 else 0

# Adaptive N: low vol = small N (12), high vol = large N (30)
N_array = np.where(vol < 0.05, 12, np.where(vol < 0.1, 20, 30))

ax.plot(prices, color='steelblue', lw=1.5, label='Price')
ax2 = ax.twinx()
ax2.plot(N_array, color='purple', lw=2, ls='--', alpha=0.6, label='Adaptive N')
ax2.set_ylabel('Adaptive Breakout N', color='purple')
ax2.tick_params(axis='y', labelcolor='purple')
ax2.set_ylim(8, 35)

ax.axvline(80, color='gray', ls=':', alpha=0.7)
ax.text(40, prices.max()*0.95, 'Low Volatility\nSmaller N', ha='center', fontsize=10,
        bbox=dict(boxstyle='round', facecolor='lightyellow'))
ax.text(120, prices.max()*0.95, 'High Volatility\nLarger N', ha='center', fontsize=10,
        bbox=dict(boxstyle='round', facecolor='lightcoral'))

style_axes(ax, 'Market Characteristic Adjustment: N adapts to volatility regime')
ax.legend(loc='upper left')
plt.tight_layout()
plt.savefig(f'{OUT}/08_market_adjustments.png', dpi=110, bbox_inches='tight')
plt.close()

# ---------- 9. Buy/Sell differentiation ----------
fig, ax = plt.subplots(figsize=(12, 5))
# Construct asymmetric path: slow rise, fast crash
up = make_trending_series(100, 100, 0.25, 0.8, 88)
down_seg = up[-1] - np.cumsum(np.abs(np.random.default_rng(89).normal(0.5, 1.5, 50)))
prices = np.concatenate([up, down_seg])

ax.plot(prices, color='steelblue', lw=1.5)

# Buys: slow N=30, sells: fast N=10
N_buy, N_sell = 30, 10
pos = 0
for i in range(N_buy, len(prices)):
    hi_buy = max(prices[i-N_buy:i])
    lo_sell = min(prices[i-N_sell:i])
    if prices[i] > hi_buy and pos != 1:
        ax.scatter(i, prices[i], marker='^', color='green', s=140, zorder=5, edgecolors='black')
        pos = 1
    elif prices[i] < lo_sell and pos != -1:
        ax.scatter(i, prices[i], marker='v', color='red', s=140, zorder=5, edgecolors='black')
        pos = -1

ax.axvline(100, color='gray', ls=':', alpha=0.7)
ax.text(50, prices.max()*0.97, 'Slow rise — slow buy (N=30)', ha='center',
        bbox=dict(boxstyle='round', facecolor='lightgreen'))
ax.text(125, prices.max()*0.97, 'Fast crash — fast sell (N=10)', ha='center',
        bbox=dict(boxstyle='round', facecolor='lightcoral'))

style_axes(ax, 'Asymmetric Buy/Sell Conditions (slow buys, fast sells)')
plt.tight_layout()
plt.savefig(f'{OUT}/09_buy_sell_diff.png', dpi=110, bbox_inches='tight')
plt.close()

# ---------- 10. Pyramiding ----------
fig, ax = plt.subplots(figsize=(12, 5))
# Strong uptrend with reactions
prices = make_trending_series(150, 100, 0.35, 1.3, 99)
ax.plot(prices, color='steelblue', lw=1.5, label='Price')

# Initial buy at day 30
buy_idx = 30
ax.scatter(buy_idx, prices[buy_idx], marker='^', color='green', s=200, zorder=5,
           edgecolors='black', label='Initial Buy')

# Find reactions (close < prior 10-day low) and subsequent 10-day high pyramids
pyramid_count = 0
last_buy_price = prices[buy_idx]
in_reaction = False
for i in range(buy_idx+10, len(prices)):
    lo10 = min(prices[i-10:i])
    hi10 = max(prices[i-10:i])
    if not in_reaction and prices[i] < lo10:
        in_reaction = True
        ax.scatter(i, prices[i], marker='o', color='orange', s=80, zorder=4)
    elif in_reaction and prices[i] > hi10 and prices[i] > last_buy_price and pyramid_count < 2:
        pyramid_count += 1
        ax.scatter(i, prices[i], marker='^', color='lime', s=160, zorder=5,
                   edgecolors='black',
                   label=f'Pyramid #{pyramid_count}' if pyramid_count <= 2 else '')
        last_buy_price = prices[i]
        in_reaction = False

style_axes(ax, 'Pyramiding: Add to winning position after reaction + resumption')
ax.legend(loc='upper left')
plt.tight_layout()
plt.savefig(f'{OUT}/10_pyramiding.png', dpi=110, bbox_inches='tight')
plt.close()

# ---------- 11. Trade Exit ----------
fig, ax = plt.subplots(figsize=(12, 5))
prices = make_trending_series(120, 100, 0.18, 1.2, 111)
ax.plot(prices, color='steelblue', lw=1.5, label='Price')

# Buy at day 20
buy_idx = 20
buy_price = prices[buy_idx]
ax.scatter(buy_idx, buy_price, marker='^', color='green', s=180, zorder=5, edgecolors='black', label='Buy')

# Trailing stop at high - 5 (acts as trade exit)
peak = buy_price
exit_idx = None
for i in range(buy_idx+1, len(prices)):
    peak = max(peak, prices[i])
    if prices[i] < peak - 5:
        exit_idx = i; break

if exit_idx is not None:
    ax.scatter(exit_idx, prices[exit_idx], marker='X', color='red', s=200, zorder=5,
               edgecolors='black', label='Trade Exit (stop)')
    ax.axhline(peak - 5, color='red', ls='--', alpha=0.6, label='Trailing Stop')

    # Re-entry rule: new high after exit
    for i in range(exit_idx+5, len(prices)):
        if i > exit_idx and prices[i] > max(prices[exit_idx:i]):
            ax.scatter(i, prices[i], marker='^', color='lime', s=180, zorder=5,
                       edgecolors='black', label='Re-entry')
            break

style_axes(ax, 'Trade Exit Rule + Re-entry Rule (limit losses, keep big trends)')
ax.legend(loc='upper left')
plt.tight_layout()
plt.savefig(f'{OUT}/11_trade_exit.png', dpi=110, bbox_inches='tight')
plt.close()

# ---------- 12. Countertrend (Fading minimum move) ----------
fig, ax = plt.subplots(figsize=(12, 5))
# Range-bound market
t = np.arange(200)
prices = 100 + 5*np.sin(t/10) + np.random.default_rng(123).normal(0, 0.6, 200)
ax.plot(prices, color='steelblue', lw=1.5, label='Price')

# Fading 4% threshold
threshold = 0.04
peak = prices[0]; trough = prices[0]
last_signal = None
for i in range(1, len(prices)):
    if prices[i] > peak: peak = prices[i]
    if prices[i] < trough: trough = prices[i]
    # countertrend sell after rally of 4%
    if last_signal != 'S' and prices[i] >= trough * (1 + threshold):
        ax.scatter(i, prices[i], marker='v', color='red', s=120, zorder=5,
                   edgecolors='black', label='Countertrend Sell' if last_signal is None else '')
        last_signal = 'S'; peak = prices[i]; trough = prices[i]
    elif last_signal != 'B' and prices[i] <= peak * (1 - threshold):
        ax.scatter(i, prices[i], marker='^', color='green', s=120, zorder=5,
                   edgecolors='black', label='Countertrend Buy' if last_signal is None else '')
        last_signal = 'B'; peak = prices[i]; trough = prices[i]

style_axes(ax, 'Countertrend System: Fade 4% Moves in a Range-Bound Market')
ax.legend(loc='upper left')
plt.tight_layout()
plt.savefig(f'{OUT}/12_countertrend.png', dpi=110, bbox_inches='tight')
plt.close()

# ---------- 13. Diversification ----------
fig, axes = plt.subplots(1, 2, figsize=(13, 5))

rng = np.random.default_rng(42)
# Single market drawdown vs multi-market portfolio
n = 250
ret_a = rng.normal(0.0008, 0.018, n)
ret_b = rng.normal(0.0006, 0.020, n)
ret_c = rng.normal(0.0007, 0.017, n)
ret_d = rng.normal(0.0005, 0.022, n)

eq_a = np.cumprod(1+ret_a)
portfolio = np.cumprod(1+(ret_a+ret_b+ret_c+ret_d)/4)

# drawdown calc
def dd(eq):
    peak = np.maximum.accumulate(eq)
    return (eq-peak)/peak * 100

axes[0].plot(eq_a, color='red', lw=1.5, label='Single Market')
axes[0].plot(portfolio, color='green', lw=1.5, label='4-Market Portfolio')
axes[0].set_title('Equity Curves')
axes[0].set_ylabel('Equity (normalized)')
axes[0].set_xlabel('Trading Day')
axes[0].legend(); axes[0].grid(True, alpha=0.3)

axes[1].plot(dd(eq_a), color='red', lw=1.5, label=f'Single Market (max DD: {dd(eq_a).min():.1f}%)')
axes[1].plot(dd(portfolio), color='green', lw=1.5, label=f'Portfolio (max DD: {dd(portfolio).min():.1f}%)')
axes[1].set_title('Drawdowns')
axes[1].set_ylabel('Drawdown (%)')
axes[1].set_xlabel('Trading Day')
axes[1].legend(); axes[1].grid(True, alpha=0.3)
axes[1].fill_between(range(n), dd(eq_a), 0, color='red', alpha=0.15)
axes[1].fill_between(range(n), dd(portfolio), 0, color='green', alpha=0.15)

plt.suptitle('Diversification Reduces Drawdown Without Reducing Return', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(f'{OUT}/13_diversification.png', dpi=110, bbox_inches='tight')
plt.close()

print("All images generated successfully!")
print(os.listdir(OUT))
