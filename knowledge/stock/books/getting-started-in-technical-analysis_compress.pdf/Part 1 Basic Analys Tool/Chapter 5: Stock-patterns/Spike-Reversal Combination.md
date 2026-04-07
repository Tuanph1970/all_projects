---
tags: [technical-analysis, schwager, one-day-pattern, spike-reversal, high-conviction]
source: "Schwager - Getting Started in Technical Analysis, Chapter 5 p.81"
related: ["[[One-Day Patterns MOC]]", "[[Spikes]]", "[[Reversal Days]]"]
---

# Spike-Reversal Combination

## Definition

A day that satisfies **both** the [[Spikes|spike]] conditions and the [[Reversal Days|reversal day]] conditions simultaneously.

> Such days are far more significant than days that are only reversal days.
> — Schwager

## Analogy

Extend the basketball dunk analogy from [[Spikes]]: the player not only jumps highest (spike — protrusion above neighboring highs), but on the way down they crash through the floor of the previous day entirely (reversal — close below prior day's low). It's not just "went up and came back" — it's "went up, came back, and kept falling past where we started."

This double condition makes the signal rare but high-conviction. The market extended itself to a climax AND the close confirms the reversal in the strongest possible terms.

## Why It Works

Each pattern alone has weaknesses:
- **Spike alone**: Confirms protrusion but doesn't guarantee the close was weak *enough* relative to prior days
- **Reversal alone (even strict)**: Confirms close below prior low but doesn't require the dramatic protrusion that signals exhaustion

Together, they cover each other's blind spots. The spike confirms the climactic extension, and the reversal confirms the decisive rejection.

## Occurrence

Rare. Schwager notes that requiring both the strong reversal day condition AND the spike conditions produces very few signals. This is the trade-off: frequency is low, but conviction per signal is high.

## Detection Strategy

```python
def detect_spike_reversal_combos(df, k=0.75, atr_period=10,
                                  lookback_n=50, strict_reversal=True):
    """
    Find days that are BOTH a spike AND a reversal day.
    Uses set intersection on dates from each detector.
    """
    spikes = detect_spikes(df, k=k, atr_period=atr_period,
                           lookback_n=lookback_n)       # see [[Spikes]]
    reversals = detect_reversal_days(df,
                                     strict=strict_reversal)  # see [[Reversal Days]]

    if spikes.empty or reversals.empty:
        return pd.DataFrame()

    combo_dates = set(spikes['date']) & set(reversals['date'])

    combos = []
    for date in combo_dates:
        spike_row = spikes[spikes['date'] == date].iloc[0]
        rev_row = reversals[reversals['date'] == date].iloc[0]
        combos.append({
            'date': date,
            'spike_type': spike_row['type'],
            'reversal_type': rev_row['type'],
            'protrusion': spike_row['protrusion'],
            'severity': rev_row['severity'],
        })

    return pd.DataFrame(combos)
```

## Connection to Chapter 11

When a spike-reversal combination later gets violated (prices return past the spike extreme), the failure of this already-strong signal is itself a powerful signal in the opposite direction — the "failed failed signal" concept.
