# Chapter 3 — Trends

> *"The trend is your friend except at the end when it bends."* — Ed Seykota

## Overview

Chapter 3 establishes the foundational tools for trend analysis. Every tool here shares the same fundamental limitation: it works well when a trend exists and fails when one doesn't. The chapter simultaneously delivers the tools AND documents their failure modes, creating the demand for tools in subsequent chapters.

## Core Concepts

### Foundation
- [[01 - Relative Highs and Relative Lows]] — The primitive that everything else builds on

### Trend Definition
- [[02 - Uptrend and Downtrend]] — Defined by the RH/RL sequence

### Trend Line Methods
- [[03 - Conventional Trend Lines]] — Connect extreme highs or lows (subjective)
- [[04 - Internal Trend Lines]] — Best-fit ignoring extremes (more subjective, more useful)
- [[05 - TD Lines (DeMark)]] — Objective two-point method (parametric)

### Trend Channels
- [[06 - Trend Channels]] — Parallel lines enclosing a trend

### Trading Rules
- [[07 - Trend Line Rules]] — Entry, penetration, and profit-taking rules

### Moving Averages
- [[08 - Moving Averages]] — Smoothed trend identification
- [[09 - Moving Average Signals]] — Direction-change signals with threshold

### Key Dynamics
- [[10 - Trend Line Redrawing]] — Why trend lines need constant adjustment
- [[11 - False Penetrations]] — Why trend line breaks often lie
- [[12 - Trending vs Sideways Markets]] — The core unsolvable trade-off

### Synthesis
- [[13 - Chapter 3 Big Picture]] — How it all connects to the rest of the book

## Relationships to Later Chapters

| Ch.3 Limitation | Resolved By |
|---|---|
| Subjectivity | Ch.4 Support/Resistance |
| False signals | Ch.11 Failed Signals |
| Sideways failure | Ch.6 Oscillators |
| Lag | Ch.5 Chart Patterns |
| All of the above | Ch.9 Risk Control |

## Assets
- `assets/code/trend_lines.py` — All 6 trend line methods
- `assets/code/trend_channels.py` — Channel construction with 3 anchor strategies
- `assets/code/trend_line_rules_illustrations.py` — Rule 1/2/3 chart generator
- `assets/simulations/` — Interactive JSX steppers

---
*Source: Schwager, "Getting Started in Technical Analysis", Ch.3, pp.33-50*
