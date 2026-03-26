---
tags: [technical-analysis, schwager, top-bottom-formation, confirmation]
source: "Schwager Ch.5 pp.96-98"
related: ["[[Double Tops and Bottoms]]", "[[Signal Frequency vs Reliability Trade-off]]"]
---

# Double Top/Bottom Completion (Reaction Low/High Breach)

## The Standard Rule
- Double top completed → close below the reaction low between peaks
- Double bottom completed → close above the reaction high between troughs

## The Deep-Reaction Problem
When the intervening pullback is deep (Fig 5.32, deutsche mark), waiting for the reaction low breach surrenders nearly half the advance. Confirmation arrives too late to be useful.

## Schwager's Resolution: Clue-Stacking
Use one-day patterns at the second peak/trough as early confirmation:
- **Spike** at peak 2 → buying/selling climax
- **Strict reversal day** → decisive rejection at the level
- **Wide-ranging day** against trend → momentum shift
- **Flag** after initial pullback from peak 2 → new direction establishing

## Shallow vs. Deep
- **Shallow reaction** (Fig 5.33): Pattern confirms close to actual peak → clean signal
- **Deep reaction** (Fig 5.32): Must anticipate using clues → [[Signal Frequency vs Reliability Trade-off]]

## For algorithmic detection
Track `reaction_depth_pct`. Below 10% → safe to wait for confirmation. Above 25% → confirmation is impractical, switch to clue-stacking mode.
