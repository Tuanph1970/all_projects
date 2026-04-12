---
title: "Flag and Pennant Stops"
chapter: 9
concept_number: 4
tags:
  - technical-analysis
  - stop-loss
  - flags
  - pennants
  - continuation-patterns
  - schwager
  - chapter-9
related:
  - "[[Stop-Loss Principle]]"
  - "[[Trading Range Stops]]"
  - "[[Wide-Ranging Day Stops]]"
  - "[[Trailing Stops]]"
  - "[[Failed Signals]]"
  - "[[Confirmation Conditions]]"
created: 2026-04-08
---

# Flag and Pennant Stops

## Definition

After a breakout from a flag or pennant formation (a narrow, short-duration consolidation within a trend), the **return to the opposite boundary** signals a price reversal and serves as the stop placement point.

- **Flag**: parallel boundaries, slight counter-trend slope
- **Pennant**: converging boundaries (like a tiny triangle)
- Both are **pauses in a major trend**, typically lasting 1–3 weeks

The opposite boundary works as the full stop (unlike [[Trading Range Stops]] where you use the midpoint-to-far zone) because **flags and pennants are narrow enough** that the full width implies reasonable risk.

## Key Quotes (Schwager)

> "After a breakout in one direction of a flag or pennant formation, the return to the opposite end (or some point beyond) can be used as a signal of a price reversal, and by implication a point for placing stops."

From Chapter 5 (definition):

> "Flags and pennants are narrow-band, short-duration (e.g., one to three weeks) congestion phases within trends."

## Analogy: Feature Flag Rollback on Metric Regression

Like a **feature flag canary** in a running deployment:

| Feature flag canary | Flag/pennant stop |
|---|---|
| System running well (stable metrics) | Prior trend established |
| Feature flag enabled to 5% (test) | Price enters narrow consolidation |
| Metrics hold → roll to 100% | Price breaks out, trend resumes |
| Key metric drops to pre-flag level | Price returns to opposite boundary |
| Rollback immediately | Stop triggered — exit the position |

The rollback threshold is tight because the "range" of uncertainty was narrow to begin with.

## How This Differs from Trading Range Stops

| Dimension | Trading range | Flag/pennant |
|-----------|--------------|--------------|
| Duration | Weeks to months | 1–3 weeks |
| Width | Wide (10–20%+) | Narrow (3–8%) |
| Context | No clear prior trend | Within an existing trend |
| Stop zone | Midpoint to far boundary | Full opposite boundary |
| Risk per trade | Moderate to high | Typically small |

The narrowness is the key advantage: you get a **well-defined stop at low risk** precisely because the consolidation is compact.

## When It Works Best

- **Within a strong, established trend** — flags/pennants are continuation patterns, so they need a prior trend to pause
- When you want **tight risk** — the narrow width means the stop is close to entry
- After a sharp, impulsive move — the "pole" of the flag should be a strong prior swing
- Combined with [[Confirmation Conditions]] to validate the breakout before entry

## When It Fails

- **Misidentified patterns** — what looks like a flag might actually be the start of a trend reversal (see [[Failed Signals]])
- Flags that are **too wide** (>8% width) — these are closer to trading ranges and should be treated as such
- Flags that are **too long** (>3 weeks) — extended consolidation increases the probability that the trend has changed character, not just paused
- Low-volume breakouts from the flag — less conviction behind the resumption

## Backtest Results

500 simulated flag breakout scenarios (65% trend continuation probability):

| Flag width | Risk/trade | Avg P&L | Worst | False stop rate |
|-----------|-----------|---------|-------|-----------------|
| 2.0% | 2.0% | +3.4% | -5.2% | 36.5% |
| **4.0%** | **4.0%** | **+3.7%** | **-6.8%** | **10.2%** |
| 6.0% | 6.0% | +3.5% | -8.6% | 1.7% |
| 8.0% | 8.0% | +3.2% | -11.2% | 0.0% |

**Flag (4%) vs trading range (12%) comparison:**

| Metric | Flag stop | Range stop |
|--------|----------|------------|
| Risk per trade | 4.0% | 12.0% |
| Average P&L | +3.7% | +3.1% |
| False stop rate | 10.2% | 0.0% |
| **Risk reduction** | **66.7%** | — |

Key insight: flag-based entries give 67% less risk with better average returns, at the cost of a modest false stop rate.

## Cross-References

- **[[Stop-Loss Principle]]** (Ch. 9, Concept 1) — Flags implement Rule 2: exit where the technical picture changes (opposite boundary)
- **[[Trading Range Stops]]** (Ch. 9, Concept 3) — Flags are mini trading ranges; same logic but narrower width allows using the full opposite boundary
- **[[Wide-Ranging Day Stops]]** (Ch. 9, Concept 5) — Similar logic: after a breakout from a one-bar pattern, return to the opposite end = reversal
- **[[Trailing Stops]]** (Ch. 9, Concept 8) — A flag breakout entry combined with trailing stops allows riding the trend beyond the flag
- **[[Failed Signals]]** (Ch. 7) — A failed breakout from a flag is a high-reliability reversal signal
- **[[Confirmation Conditions]]** (Ch. 7) — Time delay or minimum penetration to filter false flag breakouts

## Python Implementation

See `flag_pennant_stops.py`:

- `FlagPattern` — dataclass with `stop_price`, `breakout_price`, `risk_pct`, convergence detection
- `detect_flag()` — finds flag-like consolidation after a trend move
- `evaluate_flag_stop()` — backtests flag stops at different widths
- `compare_flag_vs_range_stops()` — quantifies the risk advantage of flag entries

## Summary

Flag and pennant stops are the **tightest chart-based stops** in Schwager's toolkit. Because these patterns are narrow by definition (1–3 weeks, 3–8% width), you can use the full opposite boundary as the stop and still have reasonable risk per trade. The tradeoff: the narrower the flag, the more likely normal noise triggers a false stop. A 4% flag width sits at the sweet spot — low enough risk for good reward/risk ratios, wide enough to survive most noise. The fundamental logic is identical to [[Trading Range Stops]]: return to the opposite end means the breakout failed. The only difference is scale.
