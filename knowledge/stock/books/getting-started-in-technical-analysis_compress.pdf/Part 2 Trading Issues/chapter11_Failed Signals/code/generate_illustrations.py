"""
Chapter 11 — The Most Important Rule in Chart Analysis
Original educational illustrations (matplotlib) for each concept.

These are synthetic, illustrative charts — NOT reproductions of the
copyrighted figures in the book. They are designed to convey the same
*idea* the book describes, using simulated OHLC data.
"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch
from pathlib import Path

OUT = Path("/home/claude/chapter11/images")
OUT.mkdir(parents=True, exist_ok=True)

# ---------- shared helpers ----------
np.random.seed(7)

def ohlc_from_close(closes, vol=0.6):
    """Produce simple OHLC bars from a close path."""
    opens = np.r_[closes[0], closes[:-1]]
    highs = np.maximum(opens, closes) + np.abs(np.random.randn(len(closes))) * vol
    lows  = np.minimum(opens, closes) - np.abs(np.random.randn(len(closes))) * vol
    return opens, highs, lows, closes

def draw_bars(ax, o, h, l, c, color_up="#1b9e77", color_dn="#d95f02"):
    for i in range(len(c)):
        col = color_up if c[i] >= o[i] else color_dn
        ax.vlines(i, l[i], h[i], color=col, linewidth=1)
        ax.hlines(c[i], i, i+0.35, color=col, linewidth=1.3)
        ax.hlines(o[i], i-0.35, i, color=col, linewidth=1.3)

def style(ax, title):
    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.grid(True, alpha=0.25)
    ax.set_xlabel("Day"); ax.set_ylabel("Price")

def save(fig, name):
    path = OUT / name
    fig.tight_layout()
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {path}")

# ============================================================
# 1. FAILED SIGNALS — overview chart
# ============================================================
fig, ax = plt.subplots(figsize=(9, 4.8))
n = 70
base = np.r_[
    np.linspace(50, 52, 25) + np.random.randn(25) * 0.4,    # range
    np.linspace(52, 56, 8)  + np.random.randn(8)  * 0.3,    # fake breakout
    np.linspace(56, 47, 12) + np.random.randn(12) * 0.4,    # snap back
    np.linspace(47, 41, 25) + np.random.randn(25) * 0.4,    # real move down
]
o, h, l, c = ohlc_from_close(base)
draw_bars(ax, o, h, l, c)
ax.axhline(54, color="gray", linestyle="--", alpha=0.7, label="Resistance of range")
ax.axhline(49, color="gray", linestyle="--", alpha=0.7, label="Support of range")
ax.annotate("Apparent breakout\n(buy signal)", xy=(31, 56.2), xytext=(38, 60),
            arrowprops=dict(arrowstyle="->"), fontsize=9)
ax.annotate("Signal FAILS —\nprices snap back\nand slide", xy=(50, 45),
            xytext=(52, 56), arrowprops=dict(arrowstyle="->"), fontsize=9, color="#b22222")
style(ax, "Failed Signal — apparent breakout reverses (bull trap)")
ax.legend(loc="lower left")
save(fig, "01_failed_signals_overview.png")

# ============================================================
# 2. BULL TRAP & BEAR TRAP (two-panel)
# ============================================================
fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))

# Bull trap
b1 = np.r_[
    np.linspace(100, 102, 20) + np.random.randn(20) * 0.4,
    np.linspace(102, 107, 6)  + np.random.randn(6)  * 0.3,
    np.linspace(107, 96, 12)  + np.random.randn(12) * 0.4,
    np.linspace(96, 88, 22)   + np.random.randn(22) * 0.4,
]
o, h, l, c = ohlc_from_close(b1)
draw_bars(axes[0], o, h, l, c)
axes[0].axhline(104, ls="--", color="gray")
axes[0].annotate("Breakout high\n(BULL TRAP)", xy=(25, 107.3),
                 xytext=(30, 110), arrowprops=dict(arrowstyle="->"), fontsize=9)
style(axes[0], "Bull Trap — false upside breakout")

# Bear trap
b2 = np.r_[
    np.linspace(100, 98, 20)  + np.random.randn(20) * 0.4,
    np.linspace(98, 93, 6)    + np.random.randn(6)  * 0.3,
    np.linspace(93, 102, 12)  + np.random.randn(12) * 0.4,
    np.linspace(102, 110, 22) + np.random.randn(22) * 0.4,
]
o, h, l, c = ohlc_from_close(b2)
draw_bars(axes[1], o, h, l, c)
axes[1].axhline(96, ls="--", color="gray")
axes[1].annotate("Breakout low\n(BEAR TRAP)", xy=(25, 92.7),
                 xytext=(30, 88), arrowprops=dict(arrowstyle="->"), fontsize=9)
style(axes[1], "Bear Trap — false downside breakout")
save(fig, "02_bull_bear_traps.png")

# ============================================================
# 3. CONFIRMATION CONDITIONS
# ============================================================
fig, ax = plt.subplots(figsize=(10, 5))
n = 60
data = np.r_[
    np.linspace(50, 51, 18) + np.random.randn(18) * 0.3,
    np.linspace(51, 55, 5)  + np.random.randn(5)  * 0.25,    # breakout
    np.linspace(55, 50, 4)  + np.random.randn(4)  * 0.3,
    np.linspace(50, 47, 5)  + np.random.randn(5)  * 0.3,    # initial price confirm
    np.linspace(47, 44, 8)  + np.random.randn(8)  * 0.3,    # strong price confirm
    np.linspace(44, 41, 20) + np.random.randn(20) * 0.4,
]
o, h, l, c = ohlc_from_close(data)
draw_bars(ax, o, h, l, c)
ax.axhline(52.5, color="gray", ls="--", alpha=0.7, label="Breakout level")
ax.axhline(49.5, color="#984ea3", ls=":", label="Initial confirm: close back inside range")
ax.axhline(46.5, color="#377eb8", ls=":", label="Strong confirm: close beyond opposite end")
ax.axvline(35, color="#e41a1c", ls=":", alpha=0.6, label="Time confirm (e.g. 4 weeks)")
style(ax, "Three Confirmation Conditions for a Bull Trap")
ax.legend(loc="lower left", fontsize=8)
save(fig, "03_confirmation_conditions.png")

# ============================================================
# 4. FALSE TREND LINE BREAKOUTS
# ============================================================
fig, ax = plt.subplots(figsize=(9.5, 5))
xs = np.arange(60)
trend_low = 50 + 0.3 * xs
noise = np.random.randn(60) * 0.6
data = trend_low + 1 + noise
data[28:33] -= 3.5      # false break below
data[33:]  += 0.4        # but recovers
o, h, l, c = ohlc_from_close(data)
draw_bars(ax, o, h, l, c)
ax.plot(xs, trend_low, "k--", alpha=0.7, label="Uptrend line")
ax.annotate("Apparent\ndownside break", xy=(30, data[30]),
            xytext=(15, 47), arrowprops=dict(arrowstyle="->"), fontsize=9)
ax.annotate("2 closes back ABOVE\nline → FALSE BREAKOUT\nconfirmed (buy signal)",
            xy=(38, data[38]), xytext=(40, 55),
            arrowprops=dict(arrowstyle="->"), fontsize=9, color="#1b9e77")
style(ax, "False Trend Line Breakout")
ax.legend()
save(fig, "04_false_trend_line_breakout.png")

# ============================================================
# 5. FILLED GAPS
# ============================================================
fig, ax = plt.subplots(figsize=(9, 5))
n = 40
data = np.r_[
    np.linspace(50, 52, 15) + np.random.randn(15) * 0.3,
    [56],                                                    # gap up
    np.linspace(56, 57, 4)  + np.random.randn(4)  * 0.2,
    np.linspace(57, 53, 4)  + np.random.randn(4)  * 0.3,
    np.linspace(52.5, 47, 16) + np.random.randn(16) * 0.4,
]
o, h, l, c = ohlc_from_close(data, vol=0.4)
# manually create gap day visual
o[15] = 55.7; h[15] = 56.4; l[15] = 55.5; c[15] = 56.0
draw_bars(ax, o, h, l, c)
# highlight gap area
ax.add_patch(Rectangle((14.5, h[14]), 1, l[15]-h[14],
                       facecolor="#fff3b0", edgecolor="#e09f3e", alpha=0.7))
ax.annotate("Upside GAP", xy=(15, l[15]), xytext=(8, 58),
            arrowprops=dict(arrowstyle="->"), fontsize=10, color="#b87a00")
ax.annotate("Gap FILLED →\nfailed continuation\n(bearish signal)",
            xy=(22, c[22]), xytext=(25, 58),
            arrowprops=dict(arrowstyle="->"), fontsize=9, color="#b22222")
style(ax, "Filled Gap as Failed Signal")
save(fig, "05_filled_gaps.png")

# ============================================================
# 6. RETURN TO SPIKE EXTREMES
# ============================================================
fig, ax = plt.subplots(figsize=(9.5, 5))
n = 60
data = np.r_[
    np.linspace(40, 50, 18) + np.random.randn(18) * 0.4,
    [56],                                                # spike high
    np.linspace(50, 46, 8)  + np.random.randn(8)  * 0.3,
    np.linspace(46, 49, 12) + np.random.randn(12) * 0.3,
    np.linspace(49, 58, 21) + np.random.randn(21) * 0.4, # returns past spike
]
o, h, l, c = ohlc_from_close(data, vol=0.5)
# craft the spike day
o[18] = 51; h[18] = 56.5; l[18] = 50.7; c[18] = 51.2
draw_bars(ax, o, h, l, c)
ax.axhline(56.5, color="#e41a1c", ls="--", alpha=0.7, label="Prior spike high")
ax.annotate("Spike high", xy=(18, 56.5), xytext=(10, 60),
            arrowprops=dict(arrowstyle="->"), fontsize=10)
ax.annotate("Spike penetrated →\nfailed reversal (bullish)",
            xy=(53, 57.5), xytext=(40, 60),
            arrowprops=dict(arrowstyle="->"), fontsize=9, color="#1b9e77")
style(ax, "Return to Spike Extreme as Failed Signal")
ax.legend()
save(fig, "06_return_spike_extreme.png")

# ============================================================
# 7. RETURN TO WIDE-RANGING DAY EXTREMES
# ============================================================
fig, ax = plt.subplots(figsize=(9.5, 5))
n = 40
data = np.r_[
    np.linspace(60, 58, 8)  + np.random.randn(8)  * 0.3,
    [52],                                                # wide-ranging down day close
    np.linspace(52, 50, 4)  + np.random.randn(4)  * 0.3,
    np.linspace(50, 53, 5)  + np.random.randn(5)  * 0.3,
    np.linspace(53, 60, 8)  + np.random.randn(8)  * 0.4,
    np.linspace(60, 68, 14) + np.random.randn(14) * 0.4,
]
o, h, l, c = ohlc_from_close(data, vol=0.4)
# craft the wide-ranging down day
o[8] = 57.5; h[8] = 58.2; l[8] = 51.5; c[8] = 52.0
draw_bars(ax, o, h, l, c)
ax.axhline(58.2, color="#e41a1c", ls="--", alpha=0.7,
           label="High of wide-ranging down day")
ax.annotate("Wide-ranging\ndown day", xy=(8, 54),
            xytext=(2, 50), arrowprops=dict(arrowstyle="->"), fontsize=9)
ax.annotate("Close ABOVE its high →\nfailed signal (bullish)",
            xy=(25, 60.5), xytext=(28, 56),
            arrowprops=dict(arrowstyle="->"), fontsize=9, color="#1b9e77")
style(ax, "Return to Wide-Ranging Day Extreme")
ax.legend()
save(fig, "07_wide_ranging_day_failed.png")

# ============================================================
# 8. COUNTER-TO-ANTICIPATED BREAKOUT OF FLAG / PENNANT
# ============================================================
fig, ax = plt.subplots(figsize=(9.5, 5))
n = 50
# strong rally, then flag (small downward channel), expected up break,
# but actual break is DOWN
data = np.r_[
    np.linspace(40, 60, 12) + np.random.randn(12) * 0.4,   # rally
    np.linspace(60, 58, 10) + np.random.randn(10) * 0.3,   # flag
    np.linspace(58, 50, 6)  + np.random.randn(6)  * 0.4,   # counter-break
    np.linspace(50, 42, 22) + np.random.randn(22) * 0.5,   # downtrend
]
o, h, l, c = ohlc_from_close(data, vol=0.4)
draw_bars(ax, o, h, l, c)
# flag boundaries
xf = np.arange(12, 22)
upper = 60.2 - 0.18 * (xf - 12) + 0.2
lower = 58.8 - 0.18 * (xf - 12) - 0.2
ax.plot(xf, upper, color="#377eb8", lw=1.3)
ax.plot(xf, lower, color="#377eb8", lw=1.3, label="Flag boundaries")
ax.annotate("Strong rally",
            xy=(8, 55), xytext=(2, 60), arrowprops=dict(arrowstyle="->"), fontsize=9)
ax.annotate("Expected: upside break\nActual: DOWNSIDE break\n(counter-to-anticipated)",
            xy=(24, 55), xytext=(27, 60), arrowprops=dict(arrowstyle="->"),
            fontsize=9, color="#b22222")
style(ax, "Counter-to-Anticipated Breakout of Flag")
ax.legend()
save(fig, "08_counter_anticipated_flag.png")

# ============================================================
# 9. OPPOSITE-DIRECTION BREAKOUT AFTER NORMAL BREAKOUT
# ============================================================
fig, ax = plt.subplots(figsize=(9.5, 5))
data = np.r_[
    np.linspace(40, 60, 14) + np.random.randn(14) * 0.4,   # rally
    np.linspace(60, 58, 8)  + np.random.randn(8)  * 0.3,   # flag
    np.linspace(58, 63, 4)  + np.random.randn(4)  * 0.3,   # normal up break
    np.linspace(63, 56, 5)  + np.random.randn(5)  * 0.4,   # quick reversal
    np.linspace(56, 47, 19) + np.random.randn(19) * 0.4,   # close below opposite end → fail
]
o, h, l, c = ohlc_from_close(data, vol=0.4)
draw_bars(ax, o, h, l, c)
ax.axhline(57, color="#377eb8", ls="--", alpha=0.7, label="Lower flag boundary")
ax.axhline(60.5, color="#377eb8", ls="--", alpha=0.7, label="Upper flag boundary")
ax.annotate("1) Normal upside breakout",
            xy=(24, 62.5), xytext=(28, 66),
            arrowprops=dict(arrowstyle="->"), fontsize=9)
ax.annotate("2) Reverses & closes BELOW\nopposite end → failed signal",
            xy=(35, 53), xytext=(38, 60),
            arrowprops=dict(arrowstyle="->"), fontsize=9, color="#b22222")
style(ax, "Opposite-Direction Breakout After Normal Breakout")
ax.legend(loc="lower left")
save(fig, "09_opposite_after_normal.png")

# ============================================================
# 10. PENETRATION OF TOP / BOTTOM FORMATIONS — H&S failure
# ============================================================
fig, ax = plt.subplots(figsize=(10, 5))
xs = np.arange(70)
data = np.r_[
    np.linspace(40, 55, 10) + np.random.randn(10) * 0.4,    # left shoulder up
    np.linspace(55, 50, 5)  + np.random.randn(5)  * 0.3,    # down
    np.linspace(50, 62, 8)  + np.random.randn(8)  * 0.3,    # head up
    np.linspace(62, 49, 8)  + np.random.randn(8)  * 0.3,    # down to neckline
    np.linspace(49, 56, 6)  + np.random.randn(6)  * 0.3,    # right shoulder up
    np.linspace(56, 50, 4)  + np.random.randn(4)  * 0.3,    # back to neckline
    np.linspace(50, 45, 4)  + np.random.randn(4)  * 0.3,    # break neckline (normal H&S)
    np.linspace(45, 60, 10) + np.random.randn(10) * 0.4,    # but recovers
    np.linspace(60, 70, 15) + np.random.randn(15) * 0.4,    # past right shoulder → FAIL
]
o, h, l, c = ohlc_from_close(data, vol=0.4)
draw_bars(ax, o, h, l, c)
# label parts
ax.annotate("L. shoulder", xy=(9, 56), xytext=(0, 60),
            arrowprops=dict(arrowstyle="->"), fontsize=9)
ax.annotate("Head", xy=(22, 63), xytext=(20, 67),
            arrowprops=dict(arrowstyle="->"), fontsize=9)
ax.annotate("R. shoulder", xy=(38, 57), xytext=(36, 62),
            arrowprops=dict(arrowstyle="->"), fontsize=9)
ax.axhline(57, ls="--", color="#e41a1c", alpha=0.6,
           label="Right-shoulder high (failure trigger)")
ax.annotate("Close ABOVE r. shoulder →\nfailed H&S top (bullish)",
            xy=(58, 65), xytext=(45, 67),
            arrowprops=dict(arrowstyle="->"), fontsize=9, color="#1b9e77")
style(ax, "Failed Head-and-Shoulders Top")
ax.legend(loc="lower left")
save(fig, "10_failed_head_shoulders.png")

# ============================================================
# 11. BREAKING OF CURVATURE
# ============================================================
fig, ax = plt.subplots(figsize=(9.5, 5))
xs = np.arange(60)
# build a rounded top via a downward parabola, then break upward
arc = -0.04 * (xs[:35] - 17)**2 + 60
arc += np.random.randn(35) * 0.4
post = np.linspace(arc[-1], 70, 25) + np.random.randn(25) * 0.4
data = np.r_[arc, post]
o, h, l, c = ohlc_from_close(data, vol=0.4)
draw_bars(ax, o, h, l, c)
# draw the implied curve
xc = np.linspace(0, 34, 100)
yc = -0.04 * (xc - 17)**2 + 60
ax.plot(xc, yc, color="#984ea3", ls="--", lw=2, label="Implied rounding-top curve")
ax.annotate("Rounding-top forming\n(bearish bias)", xy=(15, 58),
            xytext=(0, 50), arrowprops=dict(arrowstyle="->"), fontsize=9)
ax.annotate("Breaks ABOVE the curve →\ncurvature failed (bullish)",
            xy=(45, 64), xytext=(40, 50),
            arrowprops=dict(arrowstyle="->"), fontsize=9, color="#1b9e77")
style(ax, "Breaking of Curvature (failed rounding pattern)")
ax.legend(loc="lower right")
save(fig, "11_breaking_curvature.png")

# ============================================================
# 12. FUTURE RELIABILITY — popularity vs efficiency curve
# ============================================================
fig, ax = plt.subplots(figsize=(8.5, 4.5))
pop = np.linspace(0, 100, 100)
eff = 90 * np.exp(-pop / 35) + 5
ax.plot(pop, eff, lw=3, color="#377eb8")
ax.fill_between(pop, eff, alpha=0.15, color="#377eb8")
ax.set_xlabel("Popularity of indicator (% of traders using it)")
ax.set_ylabel("Average reliability / efficiency")
ax.set_title("Inverse relationship: popularity vs. efficiency",
             fontsize=12, fontweight="bold")
ax.annotate("Pre-1980s breakouts\n(few users → reliable)",
            xy=(15, 60), xytext=(25, 75),
            arrowprops=dict(arrowstyle="->"), fontsize=9)
ax.annotate("Modern breakouts\n(crowded → false signals)",
            xy=(80, 14), xytext=(45, 30),
            arrowprops=dict(arrowstyle="->"), fontsize=9)
ax.grid(alpha=0.25)
save(fig, "12_future_reliability.png")

print("\n--- All 12 illustrations created ---")
