# 03 — Stop Placement Quality

## Definition

The quality of a stop is determined by **whether it sits beyond a meaningful structural level** — a level whose break would actually change the technical picture. A stop placed *closer* than the closest meaningful level is "too tight": it will be triggered by routine noise (one-day spikes, intraday wiggles, evolving consolidation shape) without the trade idea being violated. The result is **premature liquidation** of trades that would otherwise have worked.

Schwager states the rule plainly in Figure 12.3 and Figure 12.16: stops belong at the closest *meaningful* point — typically the midpoint of the prior trading range, the opposite boundary of a flag, or beyond a swing high/low — *not* at the closest *price* that "feels safe."

A useful compromise rule: **don't bring the stop tighter than break-even for the first two weeks of the trade.**

## Illustration

![[03_stop_too_close.png]]

Figure 12.11 (March 1995 copper) and Figure 12.16 (December 1993 wheat) both show stops triggered by one-day spikes that did not violate the actual flag pattern, after which the trade resumed in the original anticipated direction.

## Analogy

A sleeping smoke alarm should go off when there's a fire, not when you make toast. If you set the sensitivity so high that burnt toast triggers it, you'll spend your evenings on a stepladder pulling the battery and eventually disable it altogether. The right sensitivity is "real fire, not bread." A stop should be similarly calibrated: it triggers on real damage to the trade idea, not on the price equivalent of toast smoke.

## Numeric Example

Long entered at 106.00, flag pattern with floor at 105.00, ATR ≈ 1.50.

| Stop placement | Distance | Triggered by? | Outcome |
|---|---|---|---|
| **Too tight** — 105.50 | 0.50 (0.33 ATR) | One-day spike to 105.20 | Stop triggered → −0.50; price then runs to 114 → **−0.50 realized, missed +8** |
| **Meaningful** — 104.30 (just below flag low) | 1.70 (1.13 ATR) | Genuine breakdown | Trade survives spike → captures +8 to 114 |
| **Too loose** — 100.00 | 6.00 (4.0 ATR) | Almost nothing | Captures the +8 but a real failure costs −6 |

## Python

```python
from chapter12_concepts import (
    closest_meaningful_level, stop_was_too_tight, true_range
)
import pandas as pd

df = pd.DataFrame({
    "open":  [105.5, 106.0, 105.8, 105.6, 105.4, 105.7, 106.1],
    "high":  [106.2, 106.5, 106.3, 106.1, 105.9, 106.3, 106.7],
    "low":   [105.1, 105.5, 105.4, 105.2, 105.0, 105.3, 105.7],
    "close": [105.9, 106.1, 105.7, 105.5, 105.3, 106.0, 106.4],
})

entry = 106.00
flag_low = closest_meaningful_level(df, lookback=7, side="below")  # 105.00
atr = true_range(df).rolling(5).mean().iloc[-1]                    # ~0.93

print(f"Flag low (meaningful): {flag_low:.2f}, ATR ≈ {atr:.2f}")

# Compare two candidate stops
for stop in (105.50, 104.30):
    too_tight = stop_was_too_tight(entry, stop, atr, k=1.0)
    label = "TOO TIGHT" if too_tight else "ok"
    print(f"Stop @ {stop} — distance {entry - stop:.2f} ({(entry-stop)/atr:.2f} ATR) → {label}")
```

## Relationships

### Within Chapter 12

- **[[01_Primary_Premise_Violation]]** — the stop encodes the premise. If the premise is "above flag low," the stop must sit below the flag low *with margin for noise*.
- **[[07_Flag_and_Pennant_Continuation]]** — flags evolve in shape and tolerate spikes; stops on flag trades must allow for that.
- **[[10_Trailing_Stop]]** — trailing stops face the same too-tight risk; the chapter's compromise rule (no tighter than break-even for two weeks) directly addresses it.

### When does it work best?

Stop discipline matters most for **continuation patterns** (flags, pennants, triangles), where a noisy boundary is normal. It matters less for **trap trades**, where the invalidation is itself a defined level (return to the breakout extreme).

### Outside the chapter

- **Chapter 9 — Choosing Stop-Loss Points.** This concept *is* Chapter 9 applied to real trades. Schwager's prescriptions there — trend-line stops, prior-high/low stops, volatility-based stops — all express "closest meaningful level."
- **Chapter 14 — Trading Systems.** The "confirmation rule" (require N% penetration before signal validation) is the systematic version of the same idea applied to entries.
- **Appendix — True Range / ATR.** ATR provides a quantitative basis for "how much margin beyond the boundary" — typically 1× to 1.5× ATR.

## Source

- Schwager, *Getting Started in Technical Analysis*, Ch. 12, Figures 12.3, 12.11, 12.16
- Code: [`chapter12_concepts.py → closest_meaningful_level(), stop_was_too_tight()`](code/chapter12_concepts.py)
- Image: [`03_stop_too_close.png`](images/03_stop_too_close.png)
