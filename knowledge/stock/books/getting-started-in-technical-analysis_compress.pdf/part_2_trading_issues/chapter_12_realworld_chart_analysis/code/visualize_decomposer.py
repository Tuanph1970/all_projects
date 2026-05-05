"""
Visualize chart_decomposer output: overlay all detected patterns,
color-coded by direction, on a price chart with confluence shading.
"""
import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches

sys.path.insert(0, os.path.dirname(__file__))
from chart_decomposer import decompose_chart

OUT = "/home/claude/obsidian_chapter12/images"

# ------------------------------------------------------------------
# Build the same demo series as the decomposer's __main__
# ------------------------------------------------------------------
np.random.seed(7)
n = 250
dates = pd.date_range("2023-01-02", periods=n, freq="B")
drift = np.concatenate([
    np.linspace(0.05, 0.12, 80),
    np.linspace(0.12, 0.05, 60),
    np.array([0.40, 0.50, 0.30, -0.30, -0.50, -0.60]),
    np.linspace(-0.10, -0.15, n - 80 - 60 - 6),
])
noise = np.random.normal(0, 0.6, n)
closes = 100 + np.cumsum(drift + noise)
df = pd.DataFrame({
    "open":  closes + np.random.normal(0, 0.2, n),
    "high":  closes + np.abs(np.random.normal(0.4, 0.3, n)),
    "low":   closes - np.abs(np.random.normal(0.4, 0.3, n)),
    "close": closes,
}, index=dates)

findings, groups = decompose_chart(df, timeframes=("D", "W"))

# ------------------------------------------------------------------
# Plot
# ------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(13, 6.5))

# Price line
ax.plot(df.index, df["close"], color="black", linewidth=0.9, zorder=3)

# Color map per pattern type
palette = {
    "bull_trap":                       "#d62728",
    "bear_trap":                       "#2ca02c",
    "flag_pennant":                    "#1f77b4",
    "counter_to_anticipated_breakout": "#ff7f0e",
    "wide_ranging_day":                "#9467bd",
    "island_reversal":                 "#8c564b",
    "spike_high":                      "#e377c2",
}

# Highlight confluence groups in the background (alpha by conviction)
conviction_alpha = {"low": 0.05, "moderate": 0.10, "high": 0.18, "very_high": 0.25}
for g in groups:
    if len(g.findings) < 2:
        continue
    color = "red" if g.net_score < 0 else ("green" if g.net_score > 0 else "gray")
    ax.axvspan(g.span_start, g.span_end,
               color=color, alpha=conviction_alpha[g.conviction], zorder=1)

# Plot each finding as a marker / span
y_lo, y_hi = df["close"].min(), df["close"].max()
y_range = y_hi - y_lo
for f in findings:
    color = palette.get(f.pattern, "gray")
    if f.start_idx == f.end_idx:
        # single-bar event — marker
        y = float(df["close"].asof(f.start_idx))
        marker = "v" if f.direction == "bearish" else ("^" if f.direction == "bullish" else "o")
        offset = -y_range * 0.04 if f.direction == "bearish" else y_range * 0.04
        ax.scatter(f.start_idx, y + offset, marker=marker, color=color,
                   s=55, zorder=5, edgecolor="black", linewidth=0.4,
                   label=f.pattern if f.pattern not in ax.get_legend_handles_labels()[1] else "")
    else:
        # span — bracket
        try:
            seg = df.loc[f.start_idx:f.end_idx, "close"]
            if seg.empty:
                continue
            y_top = seg.max() + y_range * 0.02
            ax.plot([f.start_idx, f.end_idx], [y_top, y_top],
                    color=color, linewidth=2.0, alpha=0.7, zorder=4)
        except KeyError:
            continue

# Build a deduplicated legend
handles, labels = ax.get_legend_handles_labels()
by_label = dict(zip(labels, handles))
ax.legend(by_label.values(), by_label.keys(),
          loc="upper left", fontsize=8, ncol=2)

ax.set_title("Multi-Timeframe Pattern Decomposition with Confluence Shading",
             fontsize=11)
ax.set_xlabel("Date")
ax.set_ylabel("Close")
ax.grid(True, linestyle=":", alpha=0.4)

# Annotate the strongest confluence zone
strongest = max(groups, key=lambda g: (len(g.findings), abs(g.net_score)))
mid = strongest.span_start + (strongest.span_end - strongest.span_start) / 2
ax.annotate(
    f"Strongest confluence:\n{len(strongest.findings)} signals, "
    f"conviction={strongest.conviction}\n"
    f"bias={'BEAR' if strongest.net_score < 0 else 'BULL'} "
    f"(net={strongest.net_score:+.2f})",
    xy=(mid, df["close"].asof(mid)),
    xytext=(mid, df["close"].max() + y_range * 0.05),
    arrowprops=dict(arrowstyle="->", color="black"),
    fontsize=9,
    ha="center",
    bbox=dict(boxstyle="round,pad=0.4", facecolor="lightyellow", edgecolor="black"),
)

plt.tight_layout()
out_path = f"{OUT}/13_decomposer_overlay.png"
plt.savefig(out_path, dpi=140)
plt.close()
print(f"Wrote {out_path}")
