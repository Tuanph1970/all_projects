---
tags: [technical-analysis, schwager, principle, meta]
source: "Schwager - Getting Started in Technical Analysis, Chapter 5"
related: ["[[One-Day Patterns MOC]]", "[[Reversal Days]]", "[[Spikes]]"]
---

# Signal Frequency vs Reliability Trade-off

## The Core Tension

Across all one-day patterns, Schwager returns to the same structural tension:

> **Looser definitions → more signals → more false positives**
> **Tighter definitions → fewer signals → fewer false positives, but more missed valid signals**

There is no free lunch. Every time you tighten a definition to reduce noise, you also filter out some genuine signals.

## The Reversal Day Case Study

This trade-off is most explicit in [[Reversal Days]]:

| Definition | Frequency | False Positive Rate | Valid Signals Caught |
|-----------|-----------|--------------------|--------------------|
| Standard (close < prior close) | Very high | Very high | Most |
| Strict (close < prior low) | Low | Low | Some |
| Ultra-strict (close < low of prior 2 days) | Very low | Very low | Few |

Schwager's verdict: the standard definition is "worthless" — the noise overwhelms the signal. He recommends the strict definition as the better trade-off, accepting missed signals as the price of usable reliability.

## How Schwager Resolves It

Rather than just tightening one definition, Schwager uses **pattern combinations** to filter:

1. **Spike + Reversal Day** → see [[Spike-Reversal Combination]]. Two independent conditions must be met simultaneously, dramatically reducing false positives while keeping the signals that do fire meaningful.

2. **Context requirements** → Spikes require a "substantive preceding advance," not just local conditions. This filters out noise in choppy markets.

3. **Aggregate counting** → [[Thrust Days]] are individually meaningless but powerful in aggregate. Instead of trading each one, count the balance over a rolling window.

## Implication for Automated Detection

When building detectors, this trade-off maps directly to **precision vs. recall**:

- Loose parameters → high recall, low precision
- Tight parameters → low recall, high precision
- The right setting depends on the cost of false positives vs. missed signals in your specific use case

For risk management (stop placement), you may prefer **high recall** — you'd rather get alerted to something that might be nothing than miss a real reversal.

For trade entry, you likely prefer **high precision** — you'd rather miss some entries than take many bad ones.
