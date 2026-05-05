# 07 Return to Wide-Ranging Day Extremes

**Parent:** [[00 Chapter 11 Index]] · **Master:** [[01 Failed Signals]]
**Tags:** #chapter11 #failed-signal #wide-ranging-day

## Definition

A **wide-ranging day (WRD)** is a bar whose true range is unusually large compared with recent days. Schwager's formal definition uses the **volatility ratio**: VR = today's true range ÷ average true range over the past N days. A day with VR > k (commonly k = 2.0) is a WRD. WRDs that close near one of their extremes are interpreted as strong directional signals — a WRD-up with a high close after a decline often kicks off an uptrend, and a WRD-down with a weak close after an advance often kicks off a downtrend.

A **return to a wide-ranging day extreme** is the failed-signal version: a later close *beyond the opposite end* of the WRD. A close above the high of a downside WRD, or below the low of an upside WRD, transforms the WRD itself into a failed signal and points to a continuation in the new direction.

## Illustration

![[07_wide_ranging_day_failed.png]]

In the book, **Figure 11.16** (DuPont) shows a pronounced downside WRD in late October that was later reversed when an upside WRD closed above its high — kicking off a multi-month rally.

## Common-life analogy

You decide on a Sunday — having stayed up too late, eaten too much, and slept badly — that *next week is the start of a serious lifestyle reset*. That Sunday is a wide-ranging emotional day; its message is "decisive change." If by Wednesday you're back to staying up late and eating leftover pizza for breakfast, you've closed beyond the opposite end of the WRD: the bold decision didn't stick, and you can confidently predict the old habits will dominate the rest of the week.

## Numeric example

Past 15-day average true range = **$1.20**.

| Day | High | Low | Close | True range | VR | Direction |
|-----|------|-----|-------|------------|----|-|
| 1 | 81.5 | 78.0 | 78.4 | 3.50 | 2.92 | down (close near low) |
| 5 | 80.4 | 79.6 | 80.1 | 0.80 | — | — |
| 9 | 82.5 | 80.8 | **82.3** | 1.70 | — | close > 81.5 → **WRD failed** |

The downside WRD had said "we're going lower." The Day-9 close above its $81.50 high reverses the message. Long entry at $82.30; stop near the WRD low ($78.00). Reward target: 2× the WRD size projected from breakout, i.e., target ~$89.

## Python sketch

```python
def wide_ranging_days(df, n=15, k=2.0):
    pc = df["close"].shift(1)
    tr = pd.concat([df["high"] - df["low"],
                    (df["high"] - pc).abs(),
                    (df["low"]  - pc).abs()], axis=1).max(axis=1)
    avg = tr.rolling(n).mean()
    vr  = tr / avg
    rng = df["high"] - df["low"]
    pos = (df["close"] - df["low"]) / rng
    rows = []
    for i in range(n, len(df)):
        if vr.iloc[i] > k:
            direction = "up" if pos.iloc[i] > 0.7 else "down" if pos.iloc[i] < 0.3 else "neutral"
            rows.append((df.index[i], direction,
                         df["high"].iloc[i], df["low"].iloc[i]))
    return rows

def wrd_failed(df, wrds):
    for date, direction, h, l in wrds:
        i = df.index.get_loc(date)
        for j in range(i + 1, len(df)):
            if direction == "down" and df["close"].iloc[j] > h:
                yield (date, df.index[j]); break
            if direction == "up" and df["close"].iloc[j] < l:
                yield (date, df.index[j]); break
```

Full implementation: `code/chapter11_detectors.py`.

## Relationships within the chapter

- WRD failures are the **bigger-cousin** of [[06 Return to Spike Extremes]]: both detect when a "this-is-decisive" single bar gets repudiated, but a spike is *defined by neighbouring bars* whereas a WRD is *defined by recent volatility*.
- Often **co-occurs with** [[05 Filled Gaps]] — Schwager observes that the day a gap is filled is itself frequently a WRD.
- The volatility ratio used here is the same statistic referenced as a building-block measure in [[Chapter 14 - Technical Trading Systems]] system design.

## When the concept works best

- **WRDs near multi-month extremes.** A WRD-down after a six-month rally that gets reversed is the textbook major top.
- **Low-volatility regimes** preceding the WRD. If the market has been calm for weeks, a sudden VR > 3 day stands out and its failure carries more weight.
- **Sequential WRDs** in the same direction (Schwager's chart of a stretch of four consecutive WRDs erasing four months of gains): when *that* gets reversed, it's an exceptionally strong failed signal.

## Relationships outside the chapter

- WRD definition, mathematical and visual: [[Chapter 5 - Chart Patterns]] and the **Appendix** entry for **volatility ratio**.
- Average true range (the denominator in VR) is one of the core volatility tools defined in the **Appendix**.
- Reversal-day and key reversal-day concepts in [[Chapter 5 - Chart Patterns]] are conceptually adjacent — they're all single-bar pattern signals whose failure can itself be traded.
