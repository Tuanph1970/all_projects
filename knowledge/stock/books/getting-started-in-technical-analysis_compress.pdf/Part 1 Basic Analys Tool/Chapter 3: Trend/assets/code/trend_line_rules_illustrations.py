"""
trend_line_rules_illustrations.py
=================================

Generate three detailed charts illustrating Schwager's three trend line rules
from Chapter 3 (pp.34-35):

    Rule 1: Approach to trend line = entry opportunity WITH the trend
    Rule 2: Penetration of trend line = reversal signal (with confirmation)
    Rule 3: Opposite end of channel = profit-taking zone

Each chart uses synthetic data designed to clearly demonstrate the concept.
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch


def _style_ax(ax, title, subtitle=""):
    ax.set_facecolor("#fafafa")
    ax.grid(True, alpha=0.15, linewidth=0.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_title(title, fontsize=14, fontweight="bold", loc="left", pad=12)
    if subtitle:
        ax.text(0.0, 1.02, subtitle, transform=ax.transAxes,
                fontsize=10, color="#666", va="bottom")


# =============================================================================
# RULE 1: Approach to trend line = entry with the trend
# =============================================================================

def plot_rule_1(save_path="rule1_entry_at_trendline.png"):
    """
    Rule 1 (Schwager p.34): "Declines approaching an uptrend line and
    rallies approaching a downtrend line are often good opportunities
    to initiate positions in the direction of the major trend."

    The logic: In an established uptrend, the trend line acts as dynamic
    support. Each time price pulls back toward it, you get a low-risk
    entry because your stop is just below the line (defined risk) and
    the expected move is back up toward the channel line (defined reward).
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))
    fig.suptitle(
        "RULE 1: Approach to Trend Line = Entry Opportunity",
        fontsize=16, fontweight="bold", y=0.98,
    )

    # ── Left panel: Uptrend ──
    np.random.seed(10)
    n = 120
    x = np.arange(n)

    # Uptrend base: price oscillates above a rising support line
    support_y = 50 + 0.25 * x
    # Price bounces between support and ~15 above it
    price = np.zeros(n)
    price[0] = 55
    for i in range(1, n):
        # Tend to bounce off support and rally
        dist_to_support = price[i-1] - support_y[i]
        if dist_to_support < 3:
            drift = 0.4  # bounce up near support
        elif dist_to_support > 12:
            drift = -0.3  # pull back when extended
        else:
            drift = 0.1
        price[i] = price[i-1] + drift + np.random.normal(0, 0.8)
        price[i] = max(price[i], support_y[i] - 1)  # slight undershoot ok

    # Identify "touch" points (within 2 of support)
    touches = []
    for i in range(5, n-5):
        dist = price[i] - support_y[i]
        if dist < 2.5 and all(price[i] <= price[j] for j in range(i-3, i)):
            if len(touches) == 0 or i - touches[-1] > 15:
                touches.append(i)

    _style_ax(ax1, "Uptrend: Buy at support line approaches",
              "Each pullback to the trend line = low-risk long entry")

    # Price
    ax1.plot(x, price, color="#333", linewidth=1, alpha=0.7, zorder=2)

    # Support (uptrend) line
    ax1.plot(x, support_y, color="#1a7f37", linewidth=2.5,
             label="Uptrend line (support)", zorder=3)

    # Channel line (parallel, ~14 above)
    channel_y = support_y + 14
    ax1.plot(x, channel_y, color="#1a7f37", linewidth=1.5,
             linestyle="--", alpha=0.5, label="Channel line")
    ax1.fill_between(x, support_y, channel_y, alpha=0.04, color="#1a7f37")

    # Mark entry points
    for idx, t in enumerate(touches[:4]):
        ax1.scatter(t, price[t], color="#1a7f37", s=120, zorder=5,
                    edgecolors="black", linewidths=0.5, marker="^")
        ax1.annotate(
            f"BUY #{idx+1}",
            xy=(t, price[t]), xytext=(t+3, price[t]-5),
            fontsize=9, fontweight="bold", color="#1a7f37",
            arrowprops=dict(arrowstyle="->", color="#1a7f37", lw=1),
        )
        # Stop loss zone
        stop_y = support_y[t] - 2
        ax1.plot([t-3, t+8], [stop_y, stop_y + 0.25*8 - 0.25*3 + support_y[t]-support_y[t] + stop_y - stop_y],
                 color="#cf222e", linewidth=0.8, linestyle=":", alpha=0.5)
        ax1.scatter(t, stop_y, color="#cf222e", s=40, marker="x", zorder=4)
        if idx == 0:
            ax1.annotate("Stop below line\n(defined risk)",
                         xy=(t, stop_y), xytext=(t+8, stop_y-3),
                         fontsize=8, color="#cf222e",
                         arrowprops=dict(arrowstyle="->", color="#cf222e", lw=0.7))

    # Risk/reward annotation on first entry
    if len(touches) >= 1:
        t = touches[0]
        entry = price[t]
        stop = support_y[t] - 2
        target = channel_y[t]
        ax1.annotate("", xy=(t-5, target), xytext=(t-5, entry),
                     arrowprops=dict(arrowstyle="<->", color="#0969da", lw=1.5))
        ax1.text(t-7, (entry + target)/2, "Reward",
                 fontsize=8, color="#0969da", ha="right", rotation=90)
        ax1.annotate("", xy=(t-5, entry), xytext=(t-5, stop),
                     arrowprops=dict(arrowstyle="<->", color="#cf222e", lw=1.5))
        ax1.text(t-7, (entry + stop)/2, "Risk",
                 fontsize=8, color="#cf222e", ha="right", rotation=90)

    ax1.legend(fontsize=9, loc="upper left")
    ax1.set_xlabel("Time →", fontsize=10)
    ax1.set_ylabel("Price", fontsize=10)

    # ── Right panel: Downtrend ──
    np.random.seed(20)

    resistance_y = 120 - 0.25 * x
    price2 = np.zeros(n)
    price2[0] = 115
    for i in range(1, n):
        dist_to_res = resistance_y[i] - price2[i-1]
        if dist_to_res < 3:
            drift = -0.4
        elif dist_to_res > 12:
            drift = 0.3
        else:
            drift = -0.1
        price2[i] = price2[i-1] + drift + np.random.normal(0, 0.8)
        price2[i] = min(price2[i], resistance_y[i] + 1)

    touches2 = []
    for i in range(5, n-5):
        dist = resistance_y[i] - price2[i]
        if dist < 2.5 and all(price2[i] >= price2[j] for j in range(i-3, i)):
            if len(touches2) == 0 or i - touches2[-1] > 15:
                touches2.append(i)

    _style_ax(ax2, "Downtrend: Sell at resistance line approaches",
              "Each rally to the trend line = low-risk short entry")

    ax2.plot(x, price2, color="#333", linewidth=1, alpha=0.7, zorder=2)
    ax2.plot(x, resistance_y, color="#cf222e", linewidth=2.5,
             label="Downtrend line (resistance)", zorder=3)
    channel2_y = resistance_y - 14
    ax2.plot(x, channel2_y, color="#cf222e", linewidth=1.5,
             linestyle="--", alpha=0.5, label="Channel line")
    ax2.fill_between(x, channel2_y, resistance_y, alpha=0.04, color="#cf222e")

    for idx, t in enumerate(touches2[:4]):
        ax2.scatter(t, price2[t], color="#cf222e", s=120, zorder=5,
                    edgecolors="black", linewidths=0.5, marker="v")
        ax2.annotate(
            f"SELL #{idx+1}",
            xy=(t, price2[t]), xytext=(t+3, price2[t]+5),
            fontsize=9, fontweight="bold", color="#cf222e",
            arrowprops=dict(arrowstyle="->", color="#cf222e", lw=1),
        )

    ax2.legend(fontsize=9, loc="lower left")
    ax2.set_xlabel("Time →", fontsize=10)
    ax2.set_ylabel("Price", fontsize=10)

    # Explanation text box
    fig.text(0.5, 0.01,
             "WHY IT WORKS: The trend line defines your risk. Entry near the line means small stop distance (defined risk)\n"
             "and large distance to the channel line (potential reward). The trend provides the directional edge.",
             ha="center", fontsize=10, style="italic", color="#555",
             bbox=dict(boxstyle="round,pad=0.5", fc="#f0f0f0", ec="#ccc"))

    plt.tight_layout(rect=[0, 0.06, 1, 0.95])
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    print(f"Saved: {save_path}")
    return fig


# =============================================================================
# RULE 2: Penetration = reversal signal (with confirmation)
# =============================================================================

def plot_rule_2(save_path="rule2_penetration_signal.png"):
    """
    Rule 2 (Schwager p.35): "The penetration of an uptrend line
    (particularly on a closing basis) is a sell signal; the penetration
    of a downtrend line is a buy signal. Normally, a minimum percentage
    price move or a minimum number of closes beyond the trend line is
    required to confirm a penetration."

    Shows both a confirmed break AND a false break (which becomes even
    more important in Chapter 11).
    """
    fig, axes = plt.subplots(1, 3, figsize=(20, 8))
    fig.suptitle(
        "RULE 2: Penetration of Trend Line = Reversal Signal",
        fontsize=16, fontweight="bold", y=0.98,
    )

    # ── Panel A: The basic concept ──
    ax = axes[0]
    _style_ax(ax, "A. Basic concept",
              "Break below uptrend line = sell")

    np.random.seed(30)
    n = 100
    x = np.arange(n)
    support_y = 50 + 0.3 * x

    # Price follows uptrend then breaks down at bar 70
    price = np.zeros(n)
    price[0] = 55
    for i in range(1, n):
        if i < 65:
            dist = price[i-1] - support_y[i]
            drift = 0.35 if dist < 3 else (-0.15 if dist > 10 else 0.15)
        elif i < 72:
            drift = -0.8  # breakdown phase
        else:
            drift = -0.3 + np.random.normal(0, 0.3)
        price[i] = price[i-1] + drift + np.random.normal(0, 0.6)

    ax.plot(x, price, color="#333", linewidth=1, alpha=0.7)
    ax.plot(x[:80], support_y[:80], color="#1a7f37", linewidth=2.5)

    # Mark the break point
    break_bar = 68
    ax.scatter(break_bar, price[break_bar], color="#cf222e", s=150,
               zorder=5, marker="v", edgecolors="black", linewidths=0.5)
    ax.annotate("SELL\n(line broken)",
                xy=(break_bar, price[break_bar]),
                xytext=(break_bar+5, price[break_bar]+6),
                fontsize=10, fontweight="bold", color="#cf222e",
                arrowprops=dict(arrowstyle="->", color="#cf222e", lw=1.5))

    # Shade the breakdown area
    ax.axvspan(break_bar-2, break_bar+10, alpha=0.08, color="#cf222e")
    ax.text(break_bar+4, support_y[break_bar]+8, "Price breaks\nbelow support",
            fontsize=8, color="#cf222e", ha="center")
    ax.set_xlabel("Time →", fontsize=10)

    # ── Panel B: Confirmation methods ──
    ax = axes[1]
    _style_ax(ax, "B. Three confirmation methods",
              "Don't act on first touch — wait for proof")

    np.random.seed(35)
    n = 120
    x = np.arange(n)
    support_y = 50 + 0.25 * x

    price = np.zeros(n)
    price[0] = 55
    for i in range(1, n):
        if i < 60:
            dist = price[i-1] - support_y[i]
            drift = 0.3 if dist < 3 else (-0.1 if dist > 8 else 0.1)
        elif i < 68:
            drift = -0.6
        elif i < 72:
            drift = -0.15  # stays below for several closes
        else:
            drift = -0.35
        price[i] = price[i-1] + drift + np.random.normal(0, 0.5)

    ax.plot(x, price, color="#333", linewidth=1, alpha=0.7)
    ax.plot(x[:90], support_y[:90], color="#1a7f37", linewidth=2.5)

    # First close below line
    first_close = 65
    ax.axvline(first_close, color="#aaa", linewidth=0.5, linestyle=":")

    # Method 1: Percentage penetration (2% below line)
    pct_line = support_y * 0.98
    ax.plot(x[55:80], pct_line[55:80], color="#9467bd", linewidth=1.2,
            linestyle="--", alpha=0.7)
    pct_bar = 68  # where price crosses the 2% threshold
    ax.scatter(pct_bar, price[pct_bar], color="#9467bd", s=80, zorder=5, marker="s")
    ax.annotate("① 2% penetration",
                xy=(pct_bar, price[pct_bar]),
                xytext=(pct_bar-15, price[pct_bar]-6),
                fontsize=8, fontweight="bold", color="#9467bd",
                arrowprops=dict(arrowstyle="->", color="#9467bd", lw=1))

    # Method 2: N closes below (3 closes)
    closes_bar = 68
    for i in range(3):
        ax.scatter(first_close + i + 1, price[first_close + i + 1],
                   color="#e377c2", s=40, zorder=4, marker="o")
    ax.annotate("② 3 closes below",
                xy=(first_close + 2, price[first_close + 2]),
                xytext=(first_close + 8, price[first_close + 2] + 4),
                fontsize=8, fontweight="bold", color="#e377c2",
                arrowprops=dict(arrowstyle="->", color="#e377c2", lw=1))

    # Method 3: Time delay (6 days, recheck)
    delay_bar = first_close + 6
    ax.axvline(delay_bar, color="#ff7f0e", linewidth=1, linestyle="--", alpha=0.5)
    ax.scatter(delay_bar, price[delay_bar], color="#ff7f0e", s=80, zorder=5, marker="D")
    ax.annotate("③ 6-day delay,\n   still below → confirm",
                xy=(delay_bar, price[delay_bar]),
                xytext=(delay_bar+5, price[delay_bar]+6),
                fontsize=8, fontweight="bold", color="#ff7f0e",
                arrowprops=dict(arrowstyle="->", color="#ff7f0e", lw=1))

    ax.set_xlabel("Time →", fontsize=10)

    # ── Panel C: Confirmed vs False break ──
    ax = axes[2]
    _style_ax(ax, "C. Confirmed vs false break",
              "False breaks → Ch.11 failed signals (even more valuable)")

    np.random.seed(40)
    n = 140
    x = np.arange(n)
    support_y = 50 + 0.2 * x

    price = np.zeros(n)
    price[0] = 55
    for i in range(1, n):
        if i < 40:
            dist = price[i-1] - support_y[i]
            drift = 0.25 if dist < 3 else (-0.1 if dist > 8 else 0.08)
        elif 40 <= i < 50:
            drift = -0.5  # false break attempt
        elif 50 <= i < 65:
            drift = 0.35  # recovery (false break!)
        elif 65 <= i < 80:
            dist = price[i-1] - support_y[i]
            drift = 0.2 if dist < 4 else (-0.1 if dist > 10 else 0.05)
        elif 80 <= i < 95:
            drift = -0.6  # real break
        else:
            drift = -0.3
        price[i] = price[i-1] + drift + np.random.normal(0, 0.5)

    ax.plot(x, price, color="#333", linewidth=1, alpha=0.7)
    ax.plot(x[:110], support_y[:110], color="#1a7f37", linewidth=2.5)

    # False break zone
    ax.axvspan(40, 52, alpha=0.08, color="#ff7f0e")
    ax.text(46, support_y[46]+12, "FALSE BREAK\n(price recovers\nabove line)",
            fontsize=8, fontweight="bold", color="#ff7f0e", ha="center",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#ff7f0e", alpha=0.9))
    ax.scatter(52, price[52], color="#ff7f0e", s=100, zorder=5, marker="^")
    ax.annotate("Failed signal → BUY!\n(Schwager Ch.11)",
                xy=(52, price[52]),
                xytext=(58, price[52]+5),
                fontsize=8, fontweight="bold", color="#ff7f0e",
                arrowprops=dict(arrowstyle="->", color="#ff7f0e", lw=1.2))

    # Real break zone
    ax.axvspan(82, 100, alpha=0.08, color="#cf222e")
    ax.text(91, support_y[91]+8, "CONFIRMED BREAK\n(3+ closes below,\n>2% penetration)",
            fontsize=8, fontweight="bold", color="#cf222e", ha="center",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#cf222e", alpha=0.9))
    ax.scatter(85, price[85], color="#cf222e", s=100, zorder=5, marker="v")
    ax.annotate("SELL (confirmed)",
                xy=(85, price[85]),
                xytext=(90, price[85]+8),
                fontsize=9, fontweight="bold", color="#cf222e",
                arrowprops=dict(arrowstyle="->", color="#cf222e", lw=1.2))

    ax.set_xlabel("Time →", fontsize=10)

    # Bottom explanation
    fig.text(0.5, 0.01,
             "WHY CONFIRMATION MATTERS: Schwager warns that trend line penetration is 'more the rule than the exception.'\n"
             "Without confirmation, you'll get whipsawed repeatedly. With it, you miss some early entries but avoid most false signals.\n"
             "The irony (Ch.11): false breaks are often MORE reliable signals than the breaks themselves.",
             ha="center", fontsize=9, style="italic", color="#555",
             bbox=dict(boxstyle="round,pad=0.5", fc="#f0f0f0", ec="#ccc"))

    plt.tight_layout(rect=[0, 0.08, 1, 0.95])
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    print(f"Saved: {save_path}")
    return fig


# =============================================================================
# RULE 3: Channel line = profit-taking zone
# =============================================================================

def plot_rule_3(save_path="rule3_channel_profit_taking.png"):
    """
    Rule 3 (Schwager p.35): "The lower end of a downtrend channel and
    the upper end of an uptrend channel represent potential profit-taking
    zones for short-term traders."

    The channel line is NOT a reversal signal — it's a "take some off
    the table" zone. Price can (and often does) exceed the channel briefly,
    but it tends to return.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))
    fig.suptitle(
        "RULE 3: Channel Line = Profit-Taking Zone",
        fontsize=16, fontweight="bold", y=0.98,
    )

    # ── Left: Uptrend channel with profit-taking at top ──
    np.random.seed(50)
    n = 150
    x = np.arange(n)
    support_y = 50 + 0.2 * x
    channel_y = support_y + 16

    price = np.zeros(n)
    price[0] = 55
    for i in range(1, n):
        dist_s = price[i-1] - support_y[i]
        dist_c = channel_y[i] - price[i-1]
        if dist_s < 2:
            drift = 0.5
        elif dist_c < 2:
            drift = -0.4
        else:
            drift = 0.08
        price[i] = price[i-1] + drift + np.random.normal(0, 0.7)
        price[i] = max(price[i], support_y[i] - 1.5)

    _style_ax(ax1, "Uptrend channel",
              "Take profits as price approaches the upper channel line")

    ax1.plot(x, price, color="#333", linewidth=1, alpha=0.7)
    ax1.plot(x, support_y, color="#1a7f37", linewidth=2.5, label="Support (base)")
    ax1.plot(x, channel_y, color="#ff7f0e", linewidth=2.5, linestyle="--",
             label="Resistance (channel)")
    mid_y = (support_y + channel_y) / 2
    ax1.plot(x, mid_y, color="gray", linewidth=0.8, linestyle=":", alpha=0.5,
             label="Midline")
    ax1.fill_between(x, support_y, channel_y, alpha=0.05, color="#1a7f37")

    # Find approach-to-channel-top points
    profit_zones = []
    for i in range(10, n-5):
        if channel_y[i] - price[i] < 2 and all(price[i] >= price[j] for j in range(i-3, i)):
            if len(profit_zones) == 0 or i - profit_zones[-1] > 15:
                profit_zones.append(i)

    for idx, t in enumerate(profit_zones[:4]):
        # Profit-taking zone shading
        ax1.axvspan(t-3, t+3, alpha=0.12, color="#ff7f0e")
        ax1.scatter(t, price[t], color="#ff7f0e", s=120, zorder=5,
                    marker="*", edgecolors="black", linewidths=0.3)
        label = "TAKE PROFIT" if idx == 0 else ""
        ax1.annotate(
            f"TP #{idx+1}" if idx > 0 else "TAKE PROFIT\n(near channel top)",
            xy=(t, price[t]),
            xytext=(t+5 if idx % 2 == 0 else t-10,
                    price[t] + (4 if idx % 2 == 0 else -6)),
            fontsize=8, fontweight="bold", color="#ff7f0e",
            arrowprops=dict(arrowstyle="->", color="#ff7f0e", lw=1),
        )

    # Also show entry points near support
    entry_zones = []
    for i in range(10, n-5):
        if price[i] - support_y[i] < 2.5 and all(price[i] <= price[j] for j in range(i-3, i)):
            if len(entry_zones) == 0 or i - entry_zones[-1] > 15:
                entry_zones.append(i)

    for t in entry_zones[:3]:
        ax1.scatter(t, price[t], color="#1a7f37", s=80, zorder=5,
                    marker="^", edgecolors="black", linewidths=0.3)

    # The cycle annotation
    if len(entry_zones) >= 1 and len(profit_zones) >= 1:
        e = entry_zones[0]
        p = profit_zones[0]
        ax1.annotate("", xy=(p, channel_y[p]+2), xytext=(e, support_y[e]-2),
                     arrowprops=dict(arrowstyle="->", color="#0969da",
                                     connectionstyle="arc3,rad=0.3",
                                     lw=1.5, linestyle="--"))
        ax1.text((e+p)/2 - 8, (support_y[e] + channel_y[p])/2,
                 "Buy low →\nSell high\n(repeat)",
                 fontsize=9, color="#0969da", ha="center", fontweight="bold")

    ax1.legend(fontsize=9, loc="upper left")
    ax1.set_xlabel("Time →", fontsize=10)
    ax1.set_ylabel("Price", fontsize=10)

    # ── Right: Downtrend channel with cover-short at bottom ──
    np.random.seed(60)
    resistance_y = 130 - 0.2 * x
    channel_low_y = resistance_y - 16

    price2 = np.zeros(n)
    price2[0] = 125
    for i in range(1, n):
        dist_r = resistance_y[i] - price2[i-1]
        dist_c = price2[i-1] - channel_low_y[i]
        if dist_r < 2:
            drift = -0.5
        elif dist_c < 2:
            drift = 0.4
        else:
            drift = -0.08
        price2[i] = price2[i-1] + drift + np.random.normal(0, 0.7)
        price2[i] = min(price2[i], resistance_y[i] + 1.5)

    _style_ax(ax2, "Downtrend channel",
              "Cover shorts as price approaches the lower channel line")

    ax2.plot(x, price2, color="#333", linewidth=1, alpha=0.7)
    ax2.plot(x, resistance_y, color="#cf222e", linewidth=2.5,
             label="Resistance (base)")
    ax2.plot(x, channel_low_y, color="#0969da", linewidth=2.5,
             linestyle="--", label="Support (channel)")
    mid_y2 = (resistance_y + channel_low_y) / 2
    ax2.plot(x, mid_y2, color="gray", linewidth=0.8, linestyle=":",
             alpha=0.5, label="Midline")
    ax2.fill_between(x, channel_low_y, resistance_y, alpha=0.05, color="#cf222e")

    profit_zones2 = []
    for i in range(10, n-5):
        if price2[i] - channel_low_y[i] < 2.5 and all(price2[i] <= price2[j] for j in range(i-3, i)):
            if len(profit_zones2) == 0 or i - profit_zones2[-1] > 15:
                profit_zones2.append(i)

    for idx, t in enumerate(profit_zones2[:4]):
        ax2.axvspan(t-3, t+3, alpha=0.12, color="#0969da")
        ax2.scatter(t, price2[t], color="#0969da", s=120, zorder=5,
                    marker="*", edgecolors="black", linewidths=0.3)
        ax2.annotate(
            f"COVER #{idx+1}" if idx > 0 else "COVER SHORT\n(near channel bottom)",
            xy=(t, price2[t]),
            xytext=(t+5 if idx % 2 == 0 else t-10,
                    price2[t] - (5 if idx % 2 == 0 else -5)),
            fontsize=8, fontweight="bold", color="#0969da",
            arrowprops=dict(arrowstyle="->", color="#0969da", lw=1),
        )

    ax2.legend(fontsize=9, loc="lower left")
    ax2.set_xlabel("Time →", fontsize=10)
    ax2.set_ylabel("Price", fontsize=10)

    # Bottom explanation
    fig.text(0.5, 0.01,
             "KEY DISTINCTION: The channel line is a PROFIT-TAKING zone, not a reversal signal.\n"
             "It tells you 'the easy money in this swing is done' — not 'the trend is over.'\n"
             "Short-term traders exit here; longer-term holders may keep positions with a trailing stop.",
             ha="center", fontsize=10, style="italic", color="#555",
             bbox=dict(boxstyle="round,pad=0.5", fc="#f0f0f0", ec="#ccc"))

    plt.tight_layout(rect=[0, 0.07, 1, 0.95])
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    print(f"Saved: {save_path}")
    return fig


# =============================================================================
# BONUS: All three rules working together on one chart
# =============================================================================

def plot_all_rules_combined(save_path="rules_combined.png"):
    """One chart showing the full trading cycle using all three rules."""
    fig, ax = plt.subplots(figsize=(18, 9))

    np.random.seed(77)
    n = 200
    x = np.arange(n)
    support_y = 50 + 0.18 * x
    channel_y = support_y + 15

    price = np.zeros(n)
    price[0] = 55
    for i in range(1, n):
        dist_s = price[i-1] - support_y[i]
        dist_c = channel_y[i] - price[i-1]

        if i < 160:
            if dist_s < 2:
                drift = 0.45
            elif dist_c < 2:
                drift = -0.35
            else:
                drift = 0.06
        else:
            drift = -0.5  # breakdown

        price[i] = price[i-1] + drift + np.random.normal(0, 0.65)
        if i < 155:
            price[i] = max(price[i], support_y[i] - 1.5)

    _style_ax(ax, "The Complete Trading Cycle — All Three Rules in Action",
              "Rule 1 (green ▲) → Rule 3 (orange ★) → Rule 2 (red ▼)")

    ax.plot(x, price, color="#333", linewidth=1.2, alpha=0.7, zorder=2)
    ax.plot(x[:175], support_y[:175], color="#1a7f37", linewidth=2.5,
            label="Uptrend line (support)", zorder=3)
    ax.plot(x[:175], channel_y[:175], color="#ff7f0e", linewidth=2,
            linestyle="--", alpha=0.7, label="Channel line (resistance)")
    ax.fill_between(x[:175], support_y[:175], channel_y[:175],
                    alpha=0.04, color="#1a7f37")

    # Find entries (near support)
    entries = []
    for i in range(10, 155):
        if price[i] - support_y[i] < 2.5 and all(price[i] <= price[j] for j in range(i-3, i)):
            if len(entries) == 0 or i - entries[-1] > 20:
                entries.append(i)

    # Find exits (near channel)
    exits = []
    for i in range(10, 155):
        if channel_y[i] - price[i] < 2.5 and all(price[i] >= price[j] for j in range(i-3, i)):
            if len(exits) == 0 or i - exits[-1] > 20:
                exits.append(i)

    # Plot Rule 1 entries
    for idx, t in enumerate(entries[:5]):
        ax.scatter(t, price[t], color="#1a7f37", s=150, zorder=5,
                   marker="^", edgecolors="black", linewidths=0.5)
        ax.annotate(f"Rule 1: BUY",
                    xy=(t, price[t]), xytext=(t+3, price[t]-6),
                    fontsize=8, fontweight="bold", color="#1a7f37",
                    arrowprops=dict(arrowstyle="->", color="#1a7f37", lw=0.8))

    # Plot Rule 3 profit-taking
    for idx, t in enumerate(exits[:4]):
        ax.scatter(t, price[t], color="#ff7f0e", s=200, zorder=5,
                   marker="*", edgecolors="black", linewidths=0.3)
        ax.annotate(f"Rule 3: TAKE PROFIT",
                    xy=(t, price[t]), xytext=(t+3, price[t]+5),
                    fontsize=8, fontweight="bold", color="#ff7f0e",
                    arrowprops=dict(arrowstyle="->", color="#ff7f0e", lw=0.8))

    # Plot Rule 2 breakdown
    break_bar = 162
    ax.scatter(break_bar, price[break_bar], color="#cf222e", s=200, zorder=5,
               marker="v", edgecolors="black", linewidths=0.5)
    ax.annotate("Rule 2: SELL\n(trend line broken,\n3 closes below = confirmed)",
                xy=(break_bar, price[break_bar]),
                xytext=(break_bar+8, price[break_bar]+10),
                fontsize=10, fontweight="bold", color="#cf222e",
                arrowprops=dict(arrowstyle="->", color="#cf222e", lw=1.5),
                bbox=dict(boxstyle="round,pad=0.4", fc="white", ec="#cf222e"))

    # Shade breakdown zone
    ax.axvspan(160, 175, alpha=0.1, color="#cf222e")

    # Draw trade arcs between entries and exits
    pairs = list(zip(entries[:4], exits[:4]))
    for e, p in pairs:
        if e < p:
            mid = (e + p) / 2
            ax.annotate("", xy=(p, price[p]-1), xytext=(e, price[e]+1),
                         arrowprops=dict(arrowstyle="->", color="#0969da",
                                         connectionstyle="arc3,rad=-0.2",
                                         lw=1, linestyle="--", alpha=0.4))

    ax.legend(fontsize=10, loc="upper left")
    ax.set_xlabel("Time →", fontsize=11)
    ax.set_ylabel("Price", fontsize=11)

    # Summary text
    fig.text(0.5, 0.01,
             "THE CYCLE: Buy at support (Rule 1) → Take profit at channel top (Rule 3) → "
             "Repeat until the trend line breaks (Rule 2).\n"
             "Rule 2 ends the game. Everything before it is swing trading within an established trend.",
             ha="center", fontsize=10, style="italic", color="#555",
             bbox=dict(boxstyle="round,pad=0.5", fc="#f0f0f0", ec="#ccc"))

    plt.tight_layout(rect=[0, 0.06, 1, 0.97])
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    print(f"Saved: {save_path}")
    return fig


# =============================================================================
if __name__ == "__main__":
    plot_rule_1()
    plot_rule_2()
    plot_rule_3()
    plot_all_rules_combined()
    print("\nAll illustrations generated.")
