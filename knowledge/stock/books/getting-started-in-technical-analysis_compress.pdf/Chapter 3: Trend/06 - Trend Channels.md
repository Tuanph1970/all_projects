# Trend Channels

## Description

A set of **parallel lines** enclosing a trend. The base line (primary trend line) defines the slope; the channel line runs parallel on the opposite side, passing through an anchor point. Schwager (p.34): "It is not uncommon for reactions against a major trend to begin near a line parallel to the trend line."

The channel creates a structured trading zone: the base line defines entry points ([[07 - Trend Line Rules|Rule 1]]) and the channel line defines profit-taking zones ([[07 - Trend Line Rules|Rule 3]]).

## Simple Analogy

Think of a river flowing downhill. The base line is one bank, the channel line is the other. The water (price) bounces between the banks as it flows in the overall direction. Kayakers (traders) enter when the water pushes toward one bank (entry at support), and exit when it reaches the other bank (profit at resistance). The river can only be navigated while it has two banks — when it floods beyond the channel, the rules break down.

## Construction

**Step 1:** Draw the base trend line (any method — conventional, internal, TD).

**Step 2:** Choose a channel anchor on the opposite side. Three strategies:

| Strategy | Anchor | Width | Best For |
|---|---|---|---|
| A: Farthest Extreme | Highest high (uptrend) or lowest low (downtrend) between base anchors | Widest | Contains all price action |
| B: Best-Fit | Optimal intercept minimizing distance to opposite swing points | Medium | Robust, not dominated by spikes |
| C: Specific Swing | Most prominent opposite RH (uptrend) or RL (downtrend) | Varies | Textbook standard |

**Step 3:** Draw parallel line: `y = slope × x + c₂` where `c₂ = anchor_price - slope × anchor_x`

**Math:** Both lines share the same slope. Channel width = `|c₂ - c₁|` (constant everywhere).

## Illustration

**Charts:**
- `assets/charts/trend_channels_comparison.png` — All 3 anchor strategies side by side
- `assets/charts/trend_channel_detail.png` — Single detailed channel with position indicator

**Book references:** Figures 3.8 (Eurodollar uptrend channel), 3.9 (Cocoa downtrend channel)

## Python Code

**File:** `assets/code/trend_channels.py`

Key functions:
- `build_base_line()` — Construct the primary trend line
- `channel_farthest_extreme()` — Strategy A
- `channel_best_fit()` — Strategy B
- `channel_specific_swing()` — Strategy C
- `build_trend_channel()` — End-to-end convenience function
- `TrendChannel.position_in_channel()` — Returns 0% (at base) to 100% (at channel line)

## Connections

- **Depends on:** [[03 - Conventional Trend Lines]] or [[05 - TD Lines (DeMark)]] (for the base line), [[01 - Relative Highs and Relative Lows]] (for anchor selection)
- **Used by:** [[07 - Trend Line Rules]] (Rule 1 entry, Rule 3 profit-taking)
- **Source:** Schwager pp.34-35, Glossary p.330

---
*Tags: #trend-channel #schwager-ch3 #codeable #trading-structure*
