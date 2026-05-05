---
chapter: 3
concept: Trend Line Rules
tags: [technical-analysis, trends, chapter-3, trading-rules]
source: "Schwager, Getting Started in Technical Analysis, Ch. 3, pp. 34-35, 39"
---

# Trend Line Rules

## Definition

Three trading rules customarily applied to trend lines and channels:

1. **Pullback entry rule.** Declines that approach an uptrend line, or rallies that approach a downtrend line, are good opportunities to enter positions in the direction of the prevailing trend.
2. **Penetration reversal rule.** A close beyond the trend line is a counter-trend signal — sell on penetration of an uptrend line, buy on penetration of a downtrend line. To filter false breaks, the rule is usually qualified: require either a minimum percentage move or a minimum number of consecutive closes through the line.
3. **Channel exit rule.** The opposite end of the channel (the lower end of a downtrend channel, the upper end of an uptrend channel) is a profit-taking zone for short-term traders.

A practical caveat from the chapter: trend-line penetrations are more often *redraws* than reversals. Trend lines tend to look much better in hindsight than in real time.

## Illustration

![[06_trend_line_rules.png]]

The green ▲ marks a Rule 1 entry — price pulls back to touch the uptrend line and turns upward. The red ▼ marks a Rule 2 sell signal where price closes decisively below the line.

## Analogy

Think of a fence at the edge of your back yard. While the dog runs around inside (price moving with the trend), brushing against the fence (the trend line) is normal — that's where you call him back when he wanders too far. But if the dog actually jumps the fence and stays on the other side for a full minute (the closing-confirmation requirement), now he's escaped — you have to go retrieve him because he's no longer obeying the boundary. A single paw resting briefly on the fence is not the same thing as a true escape.

## Numeric Example

Setup: an uptrend line `y = 60 + 0.15 × x`. Confirmation = 2 consecutive closes below the line.

| Bar | Close | Line value | Below line? | Action |
|----:|------:|-----------:|:------------|:-------|
| 50  | 67.65 | 67.50      | No (touch)   | **Buy (Rule 1)** |
| 78  | 71.20 | 71.70      | Yes          | Wait — only 1 close |
| 79  | 70.80 | 71.85      | Yes          | **Sell (Rule 2 confirmed)** |
| 110 | 76.20 | 76.50      | Yes          | Already short — no new signal |

Rule 3 example: in an uptrend channel where the parallel return line at bar 50 sits at 71.50, a long entered at 67.65 (Rule 1) might take partial profits when price approaches 71.50.

## Python Implementation

See [[02_trend_lines.py]]:

```python
from trend_lines import fit_uptrend_line, near_trend_line, trend_line_signal

line = fit_uptrend_line(closes, pivot_lows_idx=[12, 38])

# Rule 1: pullback entry
if near_trend_line(line, closes[bar], bar, tolerance_pct=0.005):
    enter_long()

# Rule 2: confirmed penetration
sig = trend_line_signal(line, closes, current_bar=bar,
                       confirm_closes=2, pct_threshold=0.01)
if sig == "sell":
    exit_long_and_consider_short()
```

## Relationships

**Within Chapter 3:**
- Operationalizes the [[03_Uptrend_Line]] and [[04_Downtrend_Line]] — the rules transform a line on a chart into a tradeable strategy.
- Rule 3 explicitly references the [[05_Trend_Channel]].
- Conventional rules contrast with [[06_TD_Line]]'s built-in objective penetration definitions.
- [[08_Moving_Average]] reversal signals are a parallel rule system — same trend-following spirit, different smoothing tool.

**Outside Chapter 3:**
- Rule 1 is the philosophical basis for buying near **support** and selling near **resistance** (Ch. 4).
- Rule 2's confirmation requirement (% move or N closes) is a classic answer to the **false signals** problem (Ch. 11).
- Rule 1 is one variant of a **midtrend entry** technique (Ch. 8).
- The penetration price itself is a natural **stop-loss point** for trades opened with Rule 1 (Ch. 9).
- Rule 3 directly drives **objective-setting** strategies (Ch. 10).

## When does each rule work well?

| Rule | Best in | Worst in |
|------|---------|----------|
| 1 — Pullback entry | Mature, well-defined trends | Choppy markets (line keeps shifting) |
| 2 — Penetration reversal | Real trend changes | Persistent strong trends (more often a redraw) |
| 3 — Channel exit | Steady, oscillating trend | Accelerating trends (price overshoots return line) |

## Source

Schwager, *Getting Started in Technical Analysis*, Ch. 3, pp. 34-35 ("the following rules are usually applied to trend lines and channels"), and the discussion of false signals on p. 39.
