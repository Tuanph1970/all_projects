"""
Generate illustrative charts for Chapter 4 concepts.
These are simulated price series designed to clearly demonstrate each pattern.
"""
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches

np.random.seed(42)
plt.rcParams['figure.dpi'] = 110
plt.rcParams['savefig.bbox'] = 'tight'

OUT = '/home/claude/chapter4/images'

# ---------- helper ----------
def random_walk(n, start=100, vol=1.0, drift=0.0):
    rets = np.random.normal(drift, vol, n)
    return start + np.cumsum(rets)


# 1) Trading Range
def chart_trading_range():
    n = 200
    upper, lower = 110, 90
    mid = (upper + lower) / 2
    prices = mid + 8 * np.sin(np.linspace(0, 6*np.pi, n)) + np.random.normal(0, 1.2, n)
    prices = np.clip(prices, lower + 0.5, upper - 0.5)

    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.plot(prices, color='#1f77b4', linewidth=1.2)
    ax.axhline(upper, color='red', linestyle='--', linewidth=1.3, label=f'Resistance ≈ {upper}')
    ax.axhline(lower, color='green', linestyle='--', linewidth=1.3, label=f'Support ≈ {lower}')
    ax.fill_between(range(n), lower, upper, color='gray', alpha=0.08)
    ax.set_title('Trading Range — Sideways Price Corridor')
    ax.set_xlabel('Trading day')
    ax.set_ylabel('Price')
    ax.legend(loc='upper right')
    plt.savefig(f'{OUT}/01_trading_range.png')
    plt.close()


# 2) Trading Range Breakout (with confirmation)
def chart_breakout():
    n_range = 140
    n_break = 60
    upper, lower = 110, 90
    mid = (upper + lower) / 2
    range_part = mid + 7 * np.sin(np.linspace(0, 5*np.pi, n_range)) + np.random.normal(0, 1.0, n_range)
    range_part = np.clip(range_part, lower + 0.5, upper - 0.5)

    # Breakout - false attempt then true breakout
    breakout_part = np.zeros(n_break)
    breakout_part[0:8] = np.linspace(range_part[-1], 113, 8)   # false break
    breakout_part[8:18] = np.linspace(113, 102, 10)            # falls back
    breakout_part[18:35] = np.linspace(102, 118, 17)           # confirmed break
    breakout_part[35:] = 118 + np.cumsum(np.random.normal(0.3, 0.8, n_break - 35))

    prices = np.concatenate([range_part, breakout_part])

    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.plot(prices, color='#1f77b4', linewidth=1.2)
    ax.axhline(upper, color='red', linestyle='--', linewidth=1.3, label='Range upper boundary')
    ax.axhline(lower, color='green', linestyle='--', linewidth=1.3, label='Range lower boundary')
    ax.axvspan(0, n_range, alpha=0.08, color='gray', label='Trading range')

    # Mark false breakout
    ax.annotate('False breakout\n(no confirmation)', xy=(n_range + 5, 112.5),
                xytext=(n_range - 35, 122), fontsize=9,
                arrowprops=dict(arrowstyle='->', color='orange'))
    # Mark confirmed breakout
    ax.annotate('Confirmed breakout\n(5+ days above)', xy=(n_range + 25, 116),
                xytext=(n_range + 35, 103), fontsize=9, color='darkgreen',
                arrowprops=dict(arrowstyle='->', color='darkgreen'))

    ax.set_title('Trading Range Breakout — False vs. Confirmed')
    ax.set_xlabel('Trading day')
    ax.set_ylabel('Price')
    ax.legend(loc='lower right')
    plt.savefig(f'{OUT}/02_breakout.png')
    plt.close()


# 3) Support and Resistance (after a breakout, roles flip)
def chart_support_resistance_flip():
    n = 240
    p = np.zeros(n)
    p[0:80] = 100 + 5*np.sin(np.linspace(0, 4*np.pi, 80)) + np.random.normal(0, 0.7, 80)
    p[80:130] = np.linspace(p[79], 118, 50) + np.random.normal(0, 0.6, 50)  # breakout up
    p[130:180] = np.linspace(118, 106, 50) + np.random.normal(0, 0.6, 50)   # pullback
    p[180:] = np.linspace(106, 122, n-180) + np.random.normal(0, 0.7, n-180) # bounce

    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.plot(p, color='#1f77b4', linewidth=1.2)
    ax.axhline(105, color='purple', linestyle='--', linewidth=1.3,
               label='Old resistance → new support')
    ax.axvspan(0, 80, alpha=0.08, color='gray')
    ax.annotate('Trading range\n(105 = ceiling)', xy=(40, 102), fontsize=9, ha='center')
    ax.annotate('Breakout', xy=(105, 112), fontsize=9, color='darkgreen')
    ax.annotate('Pullback bounces\noff old ceiling\n(now floor)',
                xy=(180, 106), xytext=(150, 95), fontsize=9,
                arrowprops=dict(arrowstyle='->', color='purple'))
    ax.set_title('Support / Resistance Role Reversal After Breakout')
    ax.set_xlabel('Trading day')
    ax.set_ylabel('Price')
    ax.legend(loc='upper left')
    plt.savefig(f'{OUT}/03_sr_flip.png')
    plt.close()


# 4) Prior major highs/lows
def chart_prior_highs_lows():
    n = 260
    p = np.zeros(n)
    p[0:50] = 100 + np.cumsum(np.random.normal(0.25, 0.8, 50))     # rally to peak
    peak1 = p[49]
    p[50:110] = np.linspace(peak1, 95, 60) + np.random.normal(0, 0.7, 60) # decline
    trough1 = p[109]
    p[110:170] = np.linspace(trough1, peak1 - 1.5, 60) + np.random.normal(0, 0.7, 60) # rally back
    p[170:220] = np.linspace(p[169], trough1 + 0.5, 50) + np.random.normal(0, 0.7, 50) # decline test
    p[220:] = np.linspace(p[219], 108, n - 220) + np.random.normal(0, 0.7, n - 220)

    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.plot(p, color='#1f77b4', linewidth=1.2)
    ax.axhline(peak1, color='red', linestyle='--', linewidth=1.3, label=f'Prior major high → resistance')
    ax.axhline(trough1, color='green', linestyle='--', linewidth=1.3, label=f'Prior major low → support')
    ax.scatter([49, 109], [peak1, trough1], color=['red', 'green'], zorder=5, s=60)
    ax.annotate('Major high', xy=(49, peak1), xytext=(20, peak1+2), fontsize=9, color='red')
    ax.annotate('Major low', xy=(109, trough1), xytext=(80, trough1-2.5), fontsize=9, color='green')
    ax.annotate('Rally stalls\nat prior high', xy=(165, peak1-1.5),
                xytext=(140, peak1-6), fontsize=9,
                arrowprops=dict(arrowstyle='->'))
    ax.annotate('Decline holds\nat prior low', xy=(218, trough1+0.5),
                xytext=(195, trough1-3), fontsize=9,
                arrowprops=dict(arrowstyle='->'))
    ax.set_title('Prior Major Highs / Lows as Support and Resistance')
    ax.set_xlabel('Trading day')
    ax.set_ylabel('Price')
    ax.legend(loc='upper left')
    plt.savefig(f'{OUT}/04_prior_highs_lows.png')
    plt.close()


# 5) Concentrations of relative highs and lows
def chart_concentrations():
    n = 300
    base = 100 + 4*np.sin(np.linspace(0, 5*np.pi, n))
    p = base + np.random.normal(0, 1.2, n)
    # Add several relative highs near 108
    for idx in [25, 70, 115, 160]:
        p[idx-2:idx+3] += 4 * np.exp(-0.5 * (np.arange(-2, 3))**2)
    # Drift up at the end to test the zone
    p[230:] = p[230:] + np.linspace(0, 6, n-230)

    # Find relative highs/lows (5-bar)
    N = 5
    rh, rl = [], []
    for i in range(N, n - N):
        if p[i] == max(p[i-N:i+N+1]):
            rh.append(i)
        if p[i] == min(p[i-N:i+N+1]):
            rl.append(i)

    # Identify zone around the cluster of relative highs
    high_vals = [p[i] for i in rh if i < 200]
    if high_vals:
        zone_low = np.percentile(high_vals, 40)
        zone_high = np.percentile(high_vals, 90)
    else:
        zone_low, zone_high = 107, 110

    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.plot(p, color='#1f77b4', linewidth=1.2)
    ax.scatter(rh, [p[i] for i in rh], color='red', marker='v', s=40, label='Relative highs', zorder=5)
    ax.scatter(rl, [p[i] for i in rl], color='green', marker='^', s=40, label='Relative lows', zorder=5)
    ax.axhspan(zone_low, zone_high, color='red', alpha=0.15, label='Resistance zone')
    ax.set_title('Resistance Zone from Concentration of Relative Highs')
    ax.set_xlabel('Trading day')
    ax.set_ylabel('Price')
    ax.legend(loc='upper left')
    plt.savefig(f'{OUT}/05_concentrations.png')
    plt.close()


# 6) Price envelope bands
def chart_envelope_bands():
    n = 200
    p = 100 + np.cumsum(np.random.normal(0.05, 0.9, n))
    p += 5 * np.sin(np.linspace(0, 4*np.pi, n))

    window = 20
    ma = np.convolve(p, np.ones(window)/window, mode='valid')
    ma_full = np.concatenate([np.full(window-1, np.nan), ma])
    pct = 0.025
    upper = ma_full * (1 + pct)
    lower = ma_full * (1 - pct)

    # Bollinger
    rolling_std = np.array([np.std(p[max(0,i-window+1):i+1]) for i in range(n)])
    bb_upper = ma_full + 2 * rolling_std
    bb_lower = ma_full - 2 * rolling_std

    fig, axes = plt.subplots(2, 1, figsize=(9, 7), sharex=True)

    ax = axes[0]
    ax.plot(p, color='#1f77b4', linewidth=1.2, label='Price')
    ax.plot(ma_full, color='black', linewidth=1.0, label=f'{window}-day MA')
    ax.plot(upper, color='red', linestyle='--', linewidth=1.0, label=f'MA × (1+{pct})')
    ax.plot(lower, color='green', linestyle='--', linewidth=1.0, label=f'MA × (1-{pct})')
    ax.fill_between(range(n), lower, upper, color='gray', alpha=0.10)
    ax.set_title('Price Envelope Band — % around moving average')
    ax.legend(loc='upper left', fontsize=8)
    ax.set_ylabel('Price')

    ax = axes[1]
    ax.plot(p, color='#1f77b4', linewidth=1.2, label='Price')
    ax.plot(ma_full, color='black', linewidth=1.0, label=f'{window}-day MA')
    ax.plot(bb_upper, color='red', linestyle='--', linewidth=1.0, label='MA + 2σ')
    ax.plot(bb_lower, color='green', linestyle='--', linewidth=1.0, label='MA − 2σ')
    ax.fill_between(range(n), bb_lower, bb_upper, color='gray', alpha=0.10)
    ax.set_title('Bollinger Bands — standard deviations around moving average')
    ax.legend(loc='upper left', fontsize=8)
    ax.set_xlabel('Trading day')
    ax.set_ylabel('Price')

    plt.tight_layout()
    plt.savefig(f'{OUT}/06_envelope_bands.png')
    plt.close()


if __name__ == '__main__':
    chart_trading_range()
    chart_breakout()
    chart_support_resistance_flip()
    chart_prior_highs_lows()
    chart_concentrations()
    chart_envelope_bands()
    print("All charts generated.")
