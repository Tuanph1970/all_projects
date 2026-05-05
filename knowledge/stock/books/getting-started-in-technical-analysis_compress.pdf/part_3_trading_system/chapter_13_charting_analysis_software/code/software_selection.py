"""
Chapter 13 - Concept 4: Software Selection Framework
Schwager - Getting Started in Technical Analysis

Visualises the decision matrix for selecting charting/analysis software
based on: Time Frame, Analytical Goals, and Computer Skills.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# ── Software tier definitions from the book ────────────────────────────────
tiers = {
    "Entry-Level\n(<$100)": {
        "features": ["Bar charts", "Handful of indicators",
                     "Basic drawing tools", "Manual data entry"],
        "data_type": "Historical only",
        "user": "Beginner / Occasional trader",
        "color": "#AED6F1"
    },
    "Mid-Level\n($100-$500)": {
        "features": ["Bar/Candlestick/P&F charts", "EOD price download",
                     "Customizable indicators", "Simple system testing",
                     "Multiple timeframes"],
        "data_type": "Historical + EOD",
        "user": "Active trader / Swing trader",
        "color": "#85C1E9"
    },
    "Advanced\n($500-$3000+)": {
        "features": ["Real-time data support", "Advanced statistical analysis",
                     "Portfolio-level testing", "Full custom programming",
                     "Fundamental + technical data", "Options analysis"],
        "data_type": "Real-time + EOD + Historical",
        "user": "Professional / Full-time trader",
        "color": "#2E86C1"
    }
}

# ── Decision matrix ───────────────────────────────────────────────────────
criteria = ["Time Frame\n(Intraday?)", "Analytical\nGoals",
            "Computer\nSkills", "Budget"]
levels   = ["Entry-Level", "Mid-Level", "Advanced"]

# Score matrix: rows=levels, cols=criteria  (1=basic, 2=medium, 3=advanced)
scores = np.array([
    [1, 1, 1, 1],   # Entry
    [1, 2, 2, 2],   # Mid
    [3, 3, 3, 3],   # Advanced
])

# ── Visualisation ─────────────────────────────────────────────────────────
fig = plt.figure(figsize=(15, 10))
fig.suptitle("Software Selection Framework (Ch.13: Charting and Analysis Software)\n"
             "Schwager's Key Considerations Before Buying", fontsize=13, fontweight='bold')

# Left: Tier breakdown
ax1 = fig.add_subplot(1, 2, 1)
ax1.set_xlim(0, 3); ax1.set_ylim(0, 10)
ax1.axis('off')
ax1.set_title("Software Tier Breakdown", fontsize=11, fontweight='bold', pad=10)

y = 9.5
for tier_name, info in tiers.items():
    ax1.add_patch(mpatches.FancyBboxPatch(
        (0.1, y - 2.8), 2.8, 2.7,
        boxstyle="round,pad=0.1", facecolor=info['color'],
        edgecolor='white', linewidth=2))
    ax1.text(1.5, y - 0.3, tier_name, ha='center', va='top',
             fontsize=10, fontweight='bold', color='white')
    ax1.text(1.5, y - 0.75, f"User: {info['user']}", ha='center',
             fontsize=8, color='white', style='italic')
    ax1.text(1.5, y - 1.1, f"Data: {info['data_type']}", ha='center',
             fontsize=8, color='white')
    features_text = "\n".join([f"  • {f}" for f in info['features'][:3]])
    ax1.text(0.2, y - 1.4, features_text, ha='left', va='top',
             fontsize=7.5, color='white')
    y -= 3.1

# Right: Decision heatmap
ax2 = fig.add_subplot(1, 2, 2)
im = ax2.imshow(scores, cmap='Blues', aspect='auto', vmin=0, vmax=3)

ax2.set_xticks(range(len(criteria))); ax2.set_xticklabels(criteria, fontsize=10)
ax2.set_yticks(range(len(levels)));   ax2.set_yticklabels(levels, fontsize=10)

cell_labels = [
    ["Daily only", "Simple charts", "No coding", "$50-$100"],
    ["Daily/Weekly", "Indicators + Testing", "Basic logic", "$200-$500"],
    ["Intraday RT", "Advanced models", "Programming", "$500-$3000+"]
]
for i in range(len(levels)):
    for j in range(len(criteria)):
        ax2.text(j, i, cell_labels[i][j], ha='center', va='center',
                 fontsize=8.5, color='white' if scores[i, j] > 1.5 else 'black',
                 fontweight='bold')

ax2.set_title("Decision Matrix: Which Software Level Fits You?",
              fontsize=11, fontweight='bold', pad=10)
ax2.set_xlabel("Consideration Factors", fontsize=10)
ax2.set_ylabel("Software Tier", fontsize=10)

# Numeric example callout
ax2.text(3.7, 2, "Numeric Example:\nFull-time trader:\n• RT data: ~$400/mo\n• Software: ~$2,000\n• Total yr 1: ~$6,800",
         fontsize=8, ha='left', va='center',
         bbox=dict(boxstyle='round', facecolor='lightyellow', edgecolor='orange', alpha=0.9))

plt.tight_layout()
plt.savefig("/home/claude/obsidian_ch13/charts/software_selection.png",
            dpi=150, bbox_inches='tight')
plt.close()
print("Software selection chart saved.")
