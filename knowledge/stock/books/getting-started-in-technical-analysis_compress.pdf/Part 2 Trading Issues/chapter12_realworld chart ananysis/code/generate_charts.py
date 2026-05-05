"""
Chart generators for Chapter 12: Real-World Chart Analysis
Recreates the style of illustrations used by Schwager.
"""
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyArrowPatch
import os

OUT = "/home/claude/obsidian_chapter12/images"
os.makedirs(OUT, exist_ok=True)

# ------------------------------------------------------------------
# Helper: draw OHLC bars in the style of an old futures chart
# ------------------------------------------------------------------
def draw_ohlc(ax, ohlc, color="black", linewidth=0.9):
    for i, (o, h, l, c) in enumerate(ohlc):
        ax.vlines(i, l, h, color=color, linewidth=linewidth)
        ax.hlines(o, i - 0.3, i,       color=color, linewidth=linewidth)
        ax.hlines(c, i,       i + 0.3, color=color, linewidth=linewidth)

def style(ax, title):
    ax.set_title(title, fontsize=11)
    ax.grid(True, linestyle=":", alpha=0.4)
    ax.set_xlabel("Time (bars)")
    ax.set_ylabel("Price")

def synth_ohlc(prices, vol=0.4, seed=None):
    """Build OHLC from a closing-price path."""
    if seed is not None:
        np.random.seed(seed)
    ohlc = []
    prev = prices[0]
    for p in prices:
        o = prev + np.random.normal(0, vol * 0.3)
        c = p
        h = max(o, c) + abs(np.random.normal(0, vol))
        l = min(o, c) - abs(np.random.normal(0, vol))
        ohlc.append((o, h, l, c))
        prev = c
    return ohlc

# ==================================================================
# 1. PRIMARY PREMISE VIOLATION  (Figure 12.1)
# ==================================================================
fig, ax = plt.subplots(figsize=(9, 5))
np.random.seed(1)
n = 60
x = np.arange(n)
# Triangle consolidation, breakout, pullback, then breakdown
prices = np.concatenate([
    100 + np.random.normal(0, 0.6, 15) + np.linspace(0, 1.5, 15),     # rising into triangle
    103 + np.random.normal(0, 0.4, 12),                               # triangle
    np.linspace(103, 107, 8) + np.random.normal(0, 0.4, 8),           # breakout up
    np.linspace(107, 103.5, 6) + np.random.normal(0, 0.4, 6),         # pullback
    np.linspace(103.5, 96, 12) + np.random.normal(0, 0.5, 12),        # breakdown — invalidation
    np.linspace(96, 92, 7)  + np.random.normal(0, 0.5, 7),
])
ohlc = synth_ohlc(prices, vol=0.5, seed=2)
draw_ohlc(ax, ohlc)

# Triangle outline
ax.plot([12, 28], [104.5, 103.2], color="blue", linestyle="--", linewidth=1.2)
ax.plot([12, 28], [101.3, 102.6], color="blue", linestyle="--", linewidth=1.2)
ax.text(18, 105.5, "Triangular consolidation", fontsize=9, color="blue")

# Breakout arrow
ax.annotate("Upside breakout (entry premise)", xy=(30, 105.5), xytext=(36, 109),
            arrowprops=dict(arrowstyle="->", color="green"), fontsize=9, color="green")

# Invalidation
ax.annotate("Premise violated:\nbreakdown below triangle",
            xy=(45, 99), xytext=(46, 108),
            arrowprops=dict(arrowstyle="->", color="red"), fontsize=9, color="red")
ax.axhline(101.5, xmin=0.18, xmax=0.85, color="red", linewidth=0.8, linestyle=":")
ax.text(50, 101.7, "Lower triangle boundary", fontsize=8, color="red")

style(ax, "Primary Premise Violation — Exit Once the Trade Idea Is Invalidated")
plt.tight_layout()
plt.savefig(f"{OUT}/01_primary_premise_violation.png", dpi=140)
plt.close()

# ==================================================================
# 2. MARKET ORDER vs LIMIT ORDER trade-off  (Figure 12.2)
# ==================================================================
fig, ax = plt.subplots(figsize=(9, 5))
np.random.seed(3)
prices = np.concatenate([
    115 + np.random.normal(0, 0.4, 10),
    np.linspace(115, 118, 5),                 # rally
    118 - np.linspace(0, 0.5, 4),
    np.linspace(117.5, 116, 4),               # never reached the 117 sell point cleanly
    np.linspace(116, 105, 25) + np.random.normal(0, 0.5, 25),  # the move missed
    np.linspace(105, 102, 6),
])
ohlc = synth_ohlc(prices, vol=0.4, seed=4)
draw_ohlc(ax, ohlc)
ax.axhline(117.5, color="orange", linestyle="--", linewidth=1)
ax.text(2, 117.7, "Limit sell @ 117 — never reached", fontsize=9, color="orange")
ax.annotate("Missed move (would-be profit)", xy=(40, 105), xytext=(20, 110),
            arrowprops=dict(arrowstyle="->", color="red"), fontsize=9, color="red")
style(ax, "Limit vs. Market Orders — Waiting Can Cost the Whole Trade")
plt.tight_layout()
plt.savefig(f"{OUT}/02_market_vs_limit_order.png", dpi=140)
plt.close()

# ==================================================================
# 3. STOP TOO CLOSE (premature exit — Figure 12.3 / 12.11 / 12.16)
# ==================================================================
fig, ax = plt.subplots(figsize=(9, 5))
np.random.seed(5)
prices = np.concatenate([
    100 + np.random.normal(0, 0.4, 8),
    np.linspace(100, 106, 8),                       # uptrend
    106 + np.random.normal(0, 0.5, 8),              # flag
    np.array([105.2, 104.5, 104.8, 105.5, 106.2]),  # one-day spike below stop
    np.linspace(106.2, 114, 18),                    # the move you missed
    np.linspace(114, 113, 5),
])
ohlc = synth_ohlc(prices, vol=0.5, seed=6)
draw_ohlc(ax, ohlc)
ax.axhline(105, color="red", linestyle="--", linewidth=1)
ax.text(0.5, 105.1, "Stop placed too tight", fontsize=9, color="red")
ax.annotate("Spike triggers stop, then move resumes",
            xy=(24, 105), xytext=(28, 109),
            arrowprops=dict(arrowstyle="->", color="red"), fontsize=9, color="red")
style(ax, "Stops Too Close — Premature Liquidation of Good Trades")
plt.tight_layout()
plt.savefig(f"{OUT}/03_stop_too_close.png", dpi=140)
plt.close()

# ==================================================================
# 4. MEASURED MOVE OBJECTIVE  (Figure 12.4 / 12.7 / 12.8)
# ==================================================================
fig, ax = plt.subplots(figsize=(9, 5))
np.random.seed(7)
# Move 1: advance from 100 to 110, then pullback to 104, then projected to 114
phase1 = np.linspace(100, 110, 12)
phase2 = np.linspace(110, 104, 6) + np.random.normal(0, 0.3, 6)   # pullback
phase3 = np.linspace(104, 114.5, 14)                              # projected MM
phase4 = 114 + np.random.normal(0, 0.4, 8)
prices = np.concatenate([phase1, phase2, phase3, phase4])
ohlc = synth_ohlc(prices, vol=0.4, seed=8)
draw_ohlc(ax, ohlc)

# Annotate the measured move geometry
ax.plot([0, 11], [100, 110], "g-", linewidth=2, label="Move A")
ax.plot([17, 31], [104, 114], "g-", linewidth=2, label="Move B (projected)")
ax.axhline(114, color="purple", linestyle="--", linewidth=1)
ax.text(33, 114.3, "MM target = pullback low + size of A", fontsize=9, color="purple")
ax.legend(loc="lower right", fontsize=9)
style(ax, "Measured Move Objective — Project Move A's Size onto the Pullback")
plt.tight_layout()
plt.savefig(f"{OUT}/04_measured_move_objective.png", dpi=140)
plt.close()

# ==================================================================
# 5. CONFIRMED BULL TRAP  (Figure 12.8)
# ==================================================================
fig, ax = plt.subplots(figsize=(9, 5))
np.random.seed(9)
prices = np.concatenate([
    np.linspace(380, 410, 18),
    np.array([411, 413, 415, 417, 416]),                # spike to record high
    np.linspace(415, 405, 4),                           # immediate reversal
    np.linspace(405, 395, 6) + np.random.normal(0, 0.6, 6),
    np.linspace(395, 380, 8) + np.random.normal(0, 0.6, 8),
    np.linspace(380, 370, 6),
])
ohlc = synth_ohlc(prices, vol=0.7, seed=10)
draw_ohlc(ax, ohlc)
ax.axhline(410, color="blue", linestyle="--", linewidth=1)
ax.text(0.5, 410.5, "Prior trading-range high", fontsize=9, color="blue")
ax.annotate("Bull-trap top:\nbreakout fails immediately",
            xy=(21, 416), xytext=(28, 418),
            arrowprops=dict(arrowstyle="->", color="red"), fontsize=9, color="red")
style(ax, "Bull Trap — A Failed Upside Breakout Signals a Major Top")
plt.tight_layout()
plt.savefig(f"{OUT}/05_bull_trap.png", dpi=140)
plt.close()

# ==================================================================
# 6. BEAR TRAP REVERSAL  (Figure 12.13)
# ==================================================================
fig, ax = plt.subplots(figsize=(9, 5))
np.random.seed(11)
prices = np.concatenate([
    np.linspace(20, 18, 14) + np.random.normal(0, 0.15, 14),       # downtrend
    np.array([17.5, 17.2, 16.9]),                                  # break to new low
    np.array([17.4, 17.7, 18.0]),                                  # immediately fails
    np.linspace(18.0, 19.5, 8),
    np.linspace(19.5, 22, 12),                                     # rally
    np.linspace(22, 23.5, 6),
])
ohlc = synth_ohlc(prices, vol=0.18, seed=12)
draw_ohlc(ax, ohlc)
ax.axhline(17.6, color="blue", linestyle="--", linewidth=1)
ax.text(0.5, 17.65, "Prior support", fontsize=9, color="blue")
ax.annotate("Bear-trap low:\nbreakdown fails, market reverses up",
            xy=(15, 16.95), xytext=(20, 19),
            arrowprops=dict(arrowstyle="->", color="green"), fontsize=9, color="green")
style(ax, "Bear Trap — A Failed Downside Breakout Signals a Major Bottom")
plt.tight_layout()
plt.savefig(f"{OUT}/06_bear_trap.png", dpi=140)
plt.close()

# ==================================================================
# 7. FLAG / PENNANT CONTINUATION  (Figure 12.5 / 12.10 / 12.11 / 12.14)
# ==================================================================
fig, ax = plt.subplots(figsize=(9, 5))
np.random.seed(13)
prices = np.concatenate([
    np.linspace(50, 56, 10),                            # flagpole
    56 + np.random.normal(0, 0.25, 8),                  # flag (sideways/slight down)
    np.array([55.6, 55.4, 55.6, 55.8, 56.0, 56.2]),
    np.linspace(56.5, 62.5, 12),                        # next leg
    62 + np.random.normal(0, 0.4, 8),
])
ohlc = synth_ohlc(prices, vol=0.3, seed=14)
draw_ohlc(ax, ohlc)
# Flag boundaries
ax.plot([10, 23], [56.6, 56.4], color="blue", linestyle="--")
ax.plot([10, 23], [55.4, 55.2], color="blue", linestyle="--")
ax.text(11, 57.1, "Flag (consolidation)", fontsize=9, color="blue")
ax.annotate("Pole", xy=(5, 53), xytext=(2, 58),
            arrowprops=dict(arrowstyle="->"), fontsize=9)
ax.annotate("Continuation move", xy=(30, 60), xytext=(25, 53),
            arrowprops=dict(arrowstyle="->", color="green"), fontsize=9, color="green")
style(ax, "Flag / Pennant — Brief Pause Before the Trend Continues")
plt.tight_layout()
plt.savefig(f"{OUT}/07_flag_pennant.png", dpi=140)
plt.close()

# ==================================================================
# 8. COUNTER-TO-ANTICIPATED BREAKOUT  (Figure 12.6 / 12.9 / 12.15)
# ==================================================================
fig, ax = plt.subplots(figsize=(9, 5))
np.random.seed(15)
prices = np.concatenate([
    np.linspace(70, 64, 10),                            # downtrend (the pole)
    64 + np.random.normal(0, 0.3, 8),                   # narrow consolidation
    np.array([64.2, 64.5, 64.0, 63.8, 64.2, 64.6]),
    np.linspace(65.0, 71.5, 14),                        # counter-to-anticipated breakout UP
    71 + np.random.normal(0, 0.4, 6),
])
ohlc = synth_ohlc(prices, vol=0.32, seed=16)
draw_ohlc(ax, ohlc)
ax.plot([10, 24], [64.7, 64.7], color="blue", linestyle="--")
ax.plot([10, 24], [63.6, 63.6], color="blue", linestyle="--")
ax.text(11, 65.1, "Expected: continuation down", fontsize=9, color="blue")
ax.annotate("Counter-to-anticipated\nupside breakout — reversal!",
            xy=(28, 68), xytext=(28, 62),
            arrowprops=dict(arrowstyle="->", color="red"), fontsize=9, color="red")
style(ax, "Counter-to-Anticipated Breakout — Failure Becomes the New Signal")
plt.tight_layout()
plt.savefig(f"{OUT}/08_counter_to_anticipated.png", dpi=140)
plt.close()

# ==================================================================
# 9. WIDE-RANGING DAY  (Figure 12.7 / 12.13 / 12.17)
# ==================================================================
fig, ax = plt.subplots(figsize=(9, 5))
np.random.seed(17)
prices = np.concatenate([
    np.linspace(200, 188, 16) + np.random.normal(0, 0.5, 16),
    np.array([187, 188]),                               # bottoming
])
ohlc = synth_ohlc(prices, vol=0.6, seed=18)
# Insert a deliberate wide-ranging up day
wr_open  = 188.5
wr_close = 196.5
wr_high  = 197.2
wr_low   = 187.8
ohlc.append((wr_open, wr_high, wr_low, wr_close))
# More bars after
post = synth_ohlc(np.linspace(196, 205, 12), vol=0.5, seed=19)
ohlc.extend(post)
draw_ohlc(ax, ohlc)
n_bars = len(ohlc)
wr_idx = 18
ax.add_patch(patches.Rectangle((wr_idx - 0.45, wr_low), 0.9, wr_high - wr_low,
                               fill=False, edgecolor="red", linewidth=2))
ax.annotate("Wide-ranging up day\nnear extended low",
            xy=(wr_idx, wr_high), xytext=(wr_idx + 4, wr_high + 5),
            arrowprops=dict(arrowstyle="->", color="red"), fontsize=9, color="red")
style(ax, "Wide-Ranging Day — Outsized Bar Signals Possible Trend Reversal")
plt.tight_layout()
plt.savefig(f"{OUT}/09_wide_ranging_day.png", dpi=140)
plt.close()

# ==================================================================
# 10. TRAILING STOP  (Figure 12.13)
# ==================================================================
fig, ax = plt.subplots(figsize=(9, 5))
np.random.seed(20)
prices = np.concatenate([
    np.linspace(15, 18, 10),
    np.linspace(18, 22, 10),
    np.linspace(22, 26, 10),
    np.linspace(26, 24.5, 5),
])
ohlc = synth_ohlc(prices, vol=0.25, seed=21)
draw_ohlc(ax, ohlc)
# Trailing stop: rises with each new high - 1.5
closes = [c for (o, h, l, c) in ohlc]
running_max = np.maximum.accumulate(closes)
trail = running_max - 1.5
ax.plot(range(len(trail)), trail, color="red", linewidth=1.4, label="Trailing stop")
ax.legend(loc="upper left", fontsize=9)
ax.annotate("Stop ratchets up\nwith new highs", xy=(20, trail[20]),
            xytext=(8, 24), arrowprops=dict(arrowstyle="->", color="red"),
            fontsize=9, color="red")
ax.annotate("Stop hit on pullback", xy=(33, trail[33]),
            xytext=(25, 17), arrowprops=dict(arrowstyle="->", color="red"),
            fontsize=9, color="red")
style(ax, "Trailing Stop — Lock In Profit, Let the Trend Run")
plt.tight_layout()
plt.savefig(f"{OUT}/10_trailing_stop.png", dpi=140)
plt.close()

# ==================================================================
# 11. ISLAND REVERSAL + SPIKE HIGH  (Figure 12.17)
# ==================================================================
fig, ax = plt.subplots(figsize=(9, 5))
np.random.seed(22)
prices = np.concatenate([
    np.linspace(700, 760, 14),
    np.array([765, 770, 775, 778]),                     # rally into spike
    np.array([790, 800]),                               # gap up
    np.array([798, 802, 800]),                          # island top
    np.array([788, 780]),                               # gap down
    np.linspace(778, 740, 12),
    np.linspace(740, 710, 8),
])
ohlc = synth_ohlc(prices, vol=1.0, seed=23)
draw_ohlc(ax, ohlc)
# Mark the island
ax.add_patch(patches.Rectangle((17.5, 790), 4.0, 18,
                               fill=False, edgecolor="purple", linewidth=1.6))
ax.annotate("Island reversal\n(gap up + gap down)",
            xy=(19, 800), xytext=(25, 770),
            arrowprops=dict(arrowstyle="->", color="purple"), fontsize=9, color="purple")
ax.annotate("Spike high after extended advance",
            xy=(20, 810), xytext=(2, 805),
            arrowprops=dict(arrowstyle="->", color="red"), fontsize=9, color="red")
style(ax, "Island Reversal + Spike High — Multi-Pattern Top Signal")
plt.tight_layout()
plt.savefig(f"{OUT}/11_island_spike.png", dpi=140)
plt.close()

# ==================================================================
# 12. EXPECTED GAIN PER TRADE  (Figure 12.9 lesson)
# ==================================================================
fig, ax = plt.subplots(figsize=(9, 5))
# Bar plot: System A (high win-rate, small wins) vs System B (low win-rate, big wins)
labels = ["System A\n(70% win, +1, -3)", "System B\n(35% win, +5, -1)"]
win_rate = [0.70, 0.35]
avg_win = [1.0, 5.0]
avg_loss = [3.0, 1.0]
expected = [w * aw - (1 - w) * al for w, aw, al in zip(win_rate, avg_win, avg_loss)]
colors = ["#d62728" if e < 0 else "#2ca02c" for e in expected]

bars = ax.bar(labels, expected, color=colors, edgecolor="black")
for b, e in zip(bars, expected):
    ax.text(b.get_x() + b.get_width() / 2, e + (0.05 if e >= 0 else -0.15),
            f"E = {e:+.2f}R", ha="center", fontsize=11, fontweight="bold")
ax.axhline(0, color="black", linewidth=0.8)
ax.set_ylabel("Expected gain per trade (R)")
ax.set_title("Expected Gain per Trade — Win-Rate Alone Is Misleading", fontsize=11)
ax.grid(True, axis="y", linestyle=":", alpha=0.4)
plt.tight_layout()
plt.savefig(f"{OUT}/12_expected_gain.png", dpi=140)
plt.close()

print("All charts generated successfully.")
print(os.listdir(OUT))
