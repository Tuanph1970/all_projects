# 02 Bull and Bear Traps

**Parent:** [[00 Chapter 11 Index]] · **Master:** [[01 Failed Signals]]
**Tags:** #chapter11 #failed-signal #breakout

## Definition

A **bull trap** is a major upside breakout from a trading range or consolidation that is followed soon afterwards by a sharp, abrupt reversal back inside (or below) the range. A **bear trap** is the mirror image: a major downside breakout that quickly snaps back upward. Schwager calls counter-to-anticipated price action of this kind one of the **most reliable indicators of major tops and bottoms** in his experience.

The intuition: breakouts that "matter" should attract *more* buying (or selling) once they trigger. If instead the market reverses immediately, that's strong evidence the breakout uncovered no real demand — the move was thin, mostly stop-driven, and the dominant pressure is in the opposite direction.

## Illustration

![[02_bull_bear_traps.png]]

The book's **Figure 11.1** (Wal-Mart) and **Figures 11.2–11.5** (T-bonds, silver) show real-market examples of both traps with their confirmation overlays.

## Common-life analogy

A friend invites you to "the best new restaurant in town" and there's a line out the door, so you join it. After fifteen minutes the line suddenly clears: people walk away saying the kitchen is closed for a private event. If five minutes later the line *re-forms with twice as many people*, that's a continuation breakout — the restaurant really did just have a quick hiccup. But if the line stays empty and people start filing into the diner across the street, the original "great new restaurant" buzz was a bull trap; the real action is across the street.

## Numeric example

Stock XYZ has consolidated between **$95 and $104** for three months.

- **Day 0** — closes $104.50 (above the $104 range high → "upside breakout").
- **Day 1–3** — drifts to $103, $102, $101.
- **Day 4** — closes $99.20 → **Initial price confirmation** of bull trap (back inside the range).
- **Day 9** — closes $94.10 → **Strong price confirmation** (below the range low).

Trade plan: short on Day 4 at $99.20, stop above $104.50 (breakout high). Risk = $5.30. Mean post-trap extension in liquid stocks tends to be 1.5–3× the height of the failed range; here range height is $9, so a target near $90 implies $9.20 of reward — almost 2:1, before any discretionary trailing.

## Python sketch

```python
import pandas as pd

def detect_bull_traps(df: pd.DataFrame, lookback: int = 20,
                      time_confirm: int = 20) -> list[dict]:
    """Tag bull traps: breakout above lookback-day high then close back inside."""
    range_high = df["high"].rolling(lookback).max().shift(1)
    range_low  = df["low"].rolling(lookback).min().shift(1)
    out = []
    for i in range(lookback, len(df)):
        if df["high"].iloc[i] <= range_high.iloc[i]:
            continue
        breakout_high = df["high"].iloc[i]
        for j in range(i + 1, min(i + time_confirm + 1, len(df))):
            if df["high"].iloc[j] > breakout_high:           # invalidated
                break
            if df["close"].iloc[j] < range_high.iloc[i]:     # confirmed
                out.append({"breakout": df.index[i],
                            "confirmed": df.index[j],
                            "type": "bull_trap"})
                break
    return out
```

Full version (with bear traps + strong confirmation): `code/chapter11_detectors.py`.

## Relationships within the chapter

- Bull/bear traps are the **canonical illustration** of [[01 Failed Signals]]; the chapter opens with them.
- They use the protocol from [[03 Confirmation Conditions]] to determine *when* the trap is "official" (initial price, strong price, or time confirmation).
- Conceptually adjacent to [[04 False Trend Line Breakouts]], which apply the same idea to a slanted reference line instead of horizontal range boundaries.
- [[10 Penetration of Top and Bottom Formations]] generalises the trap idea to richer reversal patterns (double tops, head-and-shoulders).

## When the concept works best

- **Long, mature ranges.** The longer the consolidation, the more meaningful the failure of its breakout.
- **Round-number boundaries** (e.g., $50, $100). These attract dense stop orders, so a trap that triggers at a round number tends to be cleaner.
- **Heavy participation in the breakout day** (volume spike) followed by *thin* trade on the snap-back — the volume signature of a real trap.
- **Strong-confirmation traders** prefer waiting until price closes below the opposite range boundary; you give up a few dollars of entry but reduce false calls. See [[03 Confirmation Conditions]].

## Relationships outside the chapter

- Trading-range mechanics that produce traps are detailed in [[Chapter 4 - Trading Ranges and Support and Resistance]].
- Trap entries should sit just outside the trap extreme (per [[Chapter 9 - Stop Loss Points]]).
- Schwager lists "major upside breakout that fails quickly" as an explicit warning flag in [[Chapter 17 - Eighty-Two Trading Rules]] (rule cluster around 56–58).
- The market-psychology read on traps appears in [[Chapter 18 - Market Wizardom]].
