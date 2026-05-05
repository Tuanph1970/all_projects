# 06 — Bear Trap

## Definition

A **bear trap** is the mirror of a bull trap: a downside breakout below a prior trading range or chart pattern that **fails almost immediately**, with prices snapping back into and eventually above the range. The breakdown triggers stop-loss orders below the range and tempts new shorts in, but **uncovers no additional selling pressure** — strong evidence of underlying buying support. Schwager treats confirmed bear traps as among the most reliable major-bottom signals.

Same three confirmation conditions as bull traps: initial (median), strong (opposite boundary), and time (failure to revisit the breakout low within the window).

## Illustration

![[06_bear_trap.png]]

Figure 12.13 (crude oil continuous futures) is the cleanest bear-trap demonstration in Chapter 12: the *previous* trade (Figure 12.12) had been a *short* on a pennant near the trading-range low. When that breakdown failed and prices rebounded into the range, the failure of the short trade was *itself* the entry signal for a long — and that long captured a large gain. **The same failure that stops one trade is the premise for the opposite trade.**

## Analogy

A frozen pond looks weakest near the edge where it meets the bank. Someone steps off the bank onto the ice, expecting to crash through the thin part — and the ice holds. Not just holds: it doesn't even crack. That single confirmation, that the part everyone *expected* to fail didn't, is stronger evidence of the pond's solidity than any amount of standing in the middle would have provided. The market's failure to break where it "should have" is a similarly powerful tell.

## Numeric Example

July 1993 silver (Figure 11.3 / culmination of 6-year downtrend):

| Event | Price | Read |
|---|---|---|
| 3-month narrow range | $3.55 – $3.75 | Tight base |
| 6-month broader range | $3.45 – $3.95 | Macro structure |
| February 2-day plunge | **$3.40** | Below both ranges |
| Within 1 week | back to $3.55 | Inside narrow range — **initial confirmation** |
| Within 4 weeks | $3.85 | Inside broader range — **strong confirmation** |
| 6 months later | $5.40 | +60% rally |

A long entered on strong confirmation at $3.85 with a stop below $3.40 risks $0.45 to make $1.55 — a 1:3.4 reward.

## Python

```python
from chapter12_concepts import detect_bear_trap
import pandas as pd

# Market breaks below 3.50 then immediately rebounds back through median 3.65.
df = pd.DataFrame({
    "open":  [3.55, 3.50, 3.45, 3.42, 3.50, 3.60, 3.70, 3.80],
    "high":  [3.58, 3.52, 3.48, 3.50, 3.62, 3.72, 3.82, 3.88],
    "low":   [3.50, 3.45, 3.40, 3.41, 3.48, 3.58, 3.68, 3.76],
    "close": [3.52, 3.48, 3.42, 3.48, 3.60, 3.70, 3.80, 3.85],
})

traps = detect_bear_trap(df, range_high=3.75, range_low=3.50, lookforward=6)
print(traps.tolist())
# Bars where close < 3.50 followed by close >= median 3.625 within 6 bars are flagged.
```

## Relationships

### Within Chapter 12

- **[[05_Bull_Trap]]** — exact mirror image; everything inverts.
- **[[01_Primary_Premise_Violation]]** — a bear trap *is* a premise violation viewed from the short side, and the same event becomes a long-entry premise.
- **[[08_Counter_to_Anticipated_Breakout]]** — bear traps and counter-to-anticipated upside breaks of bear flags are the same family of failure-becomes-signal patterns.
- **[[09_Wide_Ranging_Day]]** — Figure 12.13 specifically pairs the bear-trap low with a wide-ranging *up* day for confluence.
- **The crude-oil sequence (12.12 → 12.13)** is Schwager's most powerful demonstration that the willingness to *reverse* an existing position when the bear trap appears is the difference between a small loss and a large gain.

### When does it work best?

Most reliable at:
- **The end of extended downtrends** (the silver example was a 6-year downtrend).
- **After very tight pre-breakdown ranges** (low volatility means the breakdown should have momentum if real).
- When the breakdown happens on a single dramatic 1–2 day plunge that **fails to follow through**.

### Outside the chapter

- **Chapter 11 — The Most Important Rule.** Bear traps are detailed there with their confirmation rules.
- **Chapter 4 — Trading Ranges and Support/Resistance.** A bear trap is the failure mode of a standard support break.
- **Chapter 17 — Trading Rules** (rule 50): "Play the breakout from an extended, narrow range with a stop against the other side of the range" is a discipline that automatically converts every breakdown into either a winner or a tight bear-trap loser.

## Source

- Schwager, *Getting Started in Technical Analysis*, Ch. 12, Figure 12.13 (and 12.12)
- Background: Ch. 11 — Bull and Bear Traps (Figure 11.3)
- Code: [`chapter12_concepts.py → detect_bear_trap()`](code/chapter12_concepts.py)
- Image: [`06_bear_trap.png`](images/06_bear_trap.png)
