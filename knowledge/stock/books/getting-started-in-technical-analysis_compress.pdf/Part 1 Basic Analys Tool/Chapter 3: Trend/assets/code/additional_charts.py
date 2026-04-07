"""Generate additional charts for the Obsidian vault."""
import numpy as np
import matplotlib.pyplot as plt

# --- Chart: Conventional vs Internal trend lines ---
def plot_conventional_vs_internal():
    np.random.seed(55)
    n = 140
    pr = []
    p = 52
    seed = [0.3,0.8,-0.2,0.5,0.9,-0.4,0.6,0.1,-0.7,0.4,0.8,-0.3,0.5,0.7,-0.5,0.2,0.8,-0.1,0.6,0.3]
    for i in range(n):
        s = seed[i % 20]
        if i < 6: p += 0.1 + s * 0.6
        elif i == 6: p -= 3.5
        elif i < 18: p += 0.22 + s * 0.5
        elif i < 22: p -= 0.3 + s * 0.4
        elif i < 35: p += 0.2 + s * 0.5
        elif i < 40: p -= 0.25 + s * 0.4
        elif i < 55: p += 0.18 + s * 0.5
        elif i == 55: p -= 4.2
        elif i < 70: p += 0.25 + s * 0.5
        elif i < 76: p -= 0.2 + s * 0.4
        elif i < 90: p += 0.15 + s * 0.5
        elif i < 96: p -= 0.2 + s * 0.4
        elif i < 110: p += 0.18 + s * 0.5
        elif i < 116: p -= 0.3 + s * 0.4
        else: p += 0.12 + s * 0.5
        pr.append(p)

    rls = [6, 20, 38, 55, 74, 93, 114]
    rl_prices = [pr[i] for i in rls]

    # Conventional: connect first and last extreme RL
    conv_slope = (rl_prices[-1] - rl_prices[0]) / (rls[-1] - rls[0])
    conv_int = rl_prices[0] - conv_slope * rls[0]
    conv_at = lambda x: conv_slope * x + conv_int

    # Internal: least-squares through all RLs
    xs = np.array(rls, dtype=float)
    ys = np.array(rl_prices)
    int_slope = np.sum((xs - xs.mean()) * (ys - ys.mean())) / np.sum((xs - xs.mean())**2)
    int_int = ys.mean() - int_slope * xs.mean()
    int_at = lambda x: int_slope * x + int_int

    fig, axes = plt.subplots(3, 1, figsize=(12, 12), sharex=True)
    x = np.arange(n)

    for ax in axes:
        ax.plot(x, pr, color="#555", linewidth=0.8, alpha=0.7)
        ax.set_facecolor("#fafafa")
        ax.grid(True, alpha=0.15)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    # Panel 1: Conventional
    axes[0].set_title("Conventional: anchored to extreme lows", fontsize=12, fontweight="bold", loc="left")
    axes[0].plot(x, [conv_at(i) for i in x], color="#A32D2D", linewidth=2, label="Conventional line")
    for i, ri in enumerate(rls):
        is_extreme = (i == 0 or i == len(rls)-1 or i == 3)
        c = "#A32D2D" if is_extreme else "#185FA5"
        axes[0].scatter(ri, pr[ri], color=c, s=40 if is_extreme else 25, zorder=5)
    axes[0].scatter(rls[3], pr[rls[3]], color="#BA7517", s=60, zorder=6, edgecolors="black", linewidths=0.5)
    axes[0].annotate("Spike low\n(dominates the line)", xy=(rls[3], pr[rls[3]]),
                     xytext=(rls[3]+10, pr[rls[3]]-3), fontsize=9, color="#BA7517",
                     arrowprops=dict(arrowstyle="->", color="#BA7517"))
    axes[0].legend(fontsize=9)

    # Panel 2: Internal
    axes[1].set_title("Internal: best-fit through majority of lows", fontsize=12, fontweight="bold", loc="left")
    axes[1].plot(x, [int_at(i) for i in x], color="#0F6E56", linewidth=2, linestyle="--", label="Internal line")
    for ri in rls:
        axes[1].scatter(ri, pr[ri], color="#185FA5", s=25, zorder=5)
    axes[1].scatter(rls[3], pr[rls[3]], color="#BA7517", s=40, zorder=6)
    axes[1].annotate("Spike now has\nless influence", xy=(rls[3], pr[rls[3]]),
                     xytext=(rls[3]+10, pr[rls[3]]-3), fontsize=9, color="#BA7517",
                     arrowprops=dict(arrowstyle="->", color="#BA7517"))
    axes[1].legend(fontsize=9)

    # Panel 3: Both
    axes[2].set_title("Both overlaid — note where price actually holds", fontsize=12, fontweight="bold", loc="left")
    axes[2].plot(x, [conv_at(i) for i in x], color="#A32D2D", linewidth=2, label="Conventional")
    axes[2].plot(x, [int_at(i) for i in x], color="#0F6E56", linewidth=2, linestyle="--", label="Internal")
    for ri in rls:
        axes[2].scatter(ri, pr[ri], color="#185FA5", s=25, zorder=5)
    axes[2].legend(fontsize=9)
    axes[2].set_xlabel("Time →", fontsize=10)

    plt.tight_layout()
    fig.savefig("conventional_vs_internal.png", dpi=150, bbox_inches="tight")
    print("Saved: conventional_vs_internal.png")

# --- Chart: Trending vs Sideways MA comparison ---
def plot_trending_vs_sideways():
    def sma(data, n):
        return [np.mean(data[max(0,i-n+1):i+1]) if i >= n-1 else None for i in range(len(data))]

    def gen_signals(ma, threshold):
        sigs = []
        mh, ml, state = None, None, 0
        for i, v in enumerate(ma):
            if v is None: continue
            if mh is None: mh = v; ml = v; continue
            if v > mh: mh = v
            if v < ml: ml = v
            if state <= 0 and v - ml >= threshold:
                sigs.append((i, "buy")); state = 1; mh = v
            elif state >= 0 and mh - v >= threshold:
                sigs.append((i, "sell")); state = -1; ml = v
        return sigs

    np.random.seed(77)
    # Trending
    tr = []; p = 100
    for i in range(160):
        if i < 15: p += 0.05 + (np.random.random()-0.45)*1.2
        elif i < 50: p -= 0.25 + (np.random.random()-0.4)*0.8
        elif i < 60: p += 0.15 + (np.random.random()-0.5)*0.9
        elif i < 130: p -= 0.3 + (np.random.random()-0.35)*0.8
        else: p -= 0.05 + (np.random.random()-0.5)*0.9
        tr.append(p)

    np.random.seed(88)
    sw = []; p = 100
    for i in range(160):
        p += np.sin(i/8)*0.8 + (np.random.random()-0.5)*1.5
        p = max(p, 93); p = min(p, 107)
        sw.append(p)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

    for ax, data, title in [(ax1, tr, "Trending market — few signals, big captures (Fig 3.20)"),
                             (ax2, sw, "Sideways market — many signals, all losses (Fig 3.21)")]:
        ma_vals = sma(data, 20)
        sigs = gen_signals(ma_vals, 1.5)
        x = np.arange(len(data))

        ax.set_facecolor("#fafafa")
        ax.grid(True, alpha=0.15)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.set_title(title, fontsize=12, fontweight="bold", loc="left")

        ax.plot(x, data, color="#888", linewidth=0.8, alpha=0.6)
        valid_ma = [(i, v) for i, v in enumerate(ma_vals) if v is not None]
        ax.plot([i for i,v in valid_ma], [v for i,v in valid_ma], color="#534AB7", linewidth=2, label="SMA(20)")

        wins, losses = 0, 0
        for si in range(len(sigs)):
            bar, typ = sigs[si]
            col = "#1D9E75" if typ == "buy" else "#A32D2D"
            marker = "^" if typ == "buy" else "v"
            ax.scatter(bar, data[bar], color=col, s=80, zorder=5, marker=marker)
            if si > 0:
                pbar, ptyp = sigs[si-1]
                pl = data[bar] - data[pbar] if ptyp == "buy" else data[pbar] - data[bar]
                if pl > 0: wins += 1
                else: losses += 1
                pcol = "#1D9E75" if pl > 0 else "#A32D2D"
                ax.plot([pbar, bar], [data[pbar], data[bar]], color=pcol, linewidth=0.5, linestyle="--", alpha=0.4)

        ax.legend(fontsize=9, loc="best")
        ax.text(0.98, 0.95, f"{len(sigs)} signals | W:{wins} L:{losses}",
                transform=ax.transAxes, ha="right", va="top", fontsize=10,
                color="#534AB7", fontweight="bold")

    plt.tight_layout()
    fig.savefig("trending_vs_sideways.png", dpi=150, bbox_inches="tight")
    print("Saved: trending_vs_sideways.png")

if __name__ == "__main__":
    plot_conventional_vs_internal()
    plot_trending_vs_sideways()
