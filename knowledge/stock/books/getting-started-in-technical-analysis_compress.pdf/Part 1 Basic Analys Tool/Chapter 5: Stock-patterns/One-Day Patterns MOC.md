---
tags: [technical-analysis, schwager, chart-patterns, MOC]
source: "Schwager - Getting Started in Technical Analysis, Chapter 5 & Appendix"
---

# One-Day Patterns

> *"Never confuse brilliance with a bull market."* — Paul Rubin

One-day patterns are single-bar (or near-single-bar) signals that suggest different kinds of price behavior depending on their market context. They are the smallest building blocks of chart analysis.

## Pattern Catalog

| Pattern | Frequency | Reliability | Real-Time? |
|---------|-----------|-------------|------------|
| [[Gaps]] | Moderate | Depends on type | ✅ |
| [[Spikes]] | Low-Moderate | Moderate-High | ⚠️ Needs t+1 |
| [[Reversal Days]] | High (standard) / Low (strict) | Low (standard) / Moderate (strict) | ✅ |
| [[Spike-Reversal Combination]] | Rare | High | ⚠️ Needs t+1 |
| [[Thrust Days]] | Very High | Low (single) / High (aggregate) | ✅ |
| [[Run Days]] | Low | High | ❌ Needs N future bars |
| [[Wide-Ranging Days]] | Low-Moderate | Moderate-High (with context) | ✅ |

## Relationships

```
                THRUST DAY (common, count them)
                     │
               "more powerful"
                     │
                 RUN DAY (requires hindsight)


   SPIKE ◄──── overlap ────► REVERSAL DAY
     │            = "far more          │
     │            significant"         │
     └──────────┬──────────────────────┘
                │
      SPIKE-REVERSAL COMBINATION (rare, high value)


        GAP                    WIDE-RANGING DAY
   (type depends              (meaning depends
    on context)                on close position)
```

## Cross-Cutting Principles

- **Signal frequency vs. reliability** is a constant trade-off — see [[Signal Frequency vs Reliability Trade-off]]
- Every pattern derives meaning from **context** — same pattern can mean different things at different locations
- These patterns are for **decision support with defined risk**, not prediction
- Pattern combinations compound significance — see [[Spike-Reversal Combination]]

## Shared Building Blocks

- [[True Range and ADTR]] — used by Spikes, Run Days, and Wide-Ranging Days
- [[Close Position Within Range]] — used by Spikes and Wide-Ranging Days

## Connections to Other Chapters

- Failed signals (Chapter 11) — when these patterns fail, the failure itself is a signal: [[Filled Gaps]], [[Return to Spike Extremes]], [[Return to Wide-Ranging Day Extremes]]
- Stop placement (Chapter 9) — pattern extremes often define natural stop-loss points
- Continuation patterns (Chapter 5) — [[Flags and Pennants]], [[Triangles]]
