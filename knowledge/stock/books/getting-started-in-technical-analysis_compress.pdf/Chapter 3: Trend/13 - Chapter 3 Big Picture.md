# Chapter 3 Big Picture

## Description

Chapter 3 functions as the **API contract** for trend analysis. It delivers the first set of tools AND establishes their specifications — what each can do, what it can't, and where it breaks. Each limitation creates a precisely specified opening that a later chapter fills.

Schwager's Preface: "I am supplying the tools, but not the architectural design — that is left to the individual reader."

## The Architecture

### Foundation Layer
[[01 - Relative Highs and Relative Lows]] is the primitive that all other tools implement against. When Schwager mentions "relative lows" in Ch.9, Ch.8, or Ch.11, he's referencing this definition.

### The Subjectivity ↔ Objectivity ↔ Lag Spectrum

```
Most Subjective, Least Lag                    Most Objective, Most Lag
        ←──────────────────────────────────────────→
  Conventional    Internal    TD Lines    Moving Averages
  (eyeball)       (best-fit)  (N param)   (N-day smooth)
```

Each step toward objectivity adds lag. Each step toward responsiveness adds subjectivity. This is a fundamental constraint — like the uncertainty principle.

### The Failure Catalog → Forward References

| Ch.3 Limitation | Mechanism | Later Chapter Resolution |
|---|---|---|
| Subjectivity | Which lows to connect? | Ch.4: Prior highs/lows as objective reference |
| [[11 - False Penetrations]] | Trend line breaks that reverse | Ch.11: Failed signals (more reliable than originals) |
| Sideways failure | [[12 - Trending vs Sideways Markets]] | Ch.6: Oscillators (inverse profile) |
| Lag | MAs enter/exit late | Ch.5: Chart patterns (structural signals, no fixed lag) |
| All of above | Every tool has blind spots | Ch.9: Risk control (makes failures survivable) |

### Schwager's Hidden Design Principle

**Each tool in the book exists because another tool has a known failure mode.**

- Oscillators exist because trend tools fail in ranges
- Failed signals exist because all signals sometimes fail
- Confirmation conditions exist because raw signals are unreliable
- Stop-loss rules exist because trades can be wrong
- Diversification exists because any single market can stay in the wrong regime

No tool is presented as complete on its own. Every tool is one component where others compensate for its weaknesses.

## The "API Contract" Summary

```
Input:         OHLC price data over time
Output:        Trend direction + reference levels (support/resistance)
Precondition:  A trend must exist (if not, output is garbage)
Postcondition: Entry timing (Rule 1), exit timing (Rule 2/3), risk (stop)
Failure modes: False penetrations, whipsaws, redrawing, lag (all documented)
Error handling: See Ch.9 (risk), Ch.11 (failed signals), Ch.14 (confirmation)
Dependencies:  Regime must be trending — for detection see Ch.4, Ch.6, Ch.12
```

## What We Built in This Study

| Concept | Code | Simulation | Charts |
|---|---|---|---|
| RH/RL Detection | `detect_swing_points()` | `swing_points_detector.jsx` | — |
| 6 Trend Line Methods | `trend_lines.py` (all 6) | — | `trend_lines_comparison.png` |
| Trend Channels | `trend_channels.py` | — | `trend_channels_comparison.png` |
| Three Trading Rules | `trend_line_rules_illustrations.py` | — | `rule1/2/3.png`, `rules_combined.png` |
| Trend Line Redrawing | — | `trend_line_redrawing_stepper.jsx` | — |
| Amoco Redrawing | — | `amoco_uptrend_redrawing_stepper.jsx` | — |
| TD Lines Walkthrough | — | `td_lines_stepper.jsx` | — |
| MA Signal Mechanism | `moving_average_trend()` | `ma_signal_interactive.jsx` | — |

## Connections

- **This chapter feeds:** Every subsequent chapter in the book
- **Core philosophy:** Decision support with defined risk, not prediction
- **Source:** Schwager Ch.3, pp.33-50, synthesized across Ch.4-17

---
*Tags: #synthesis #schwager-ch3 #book-architecture #api-contract*
