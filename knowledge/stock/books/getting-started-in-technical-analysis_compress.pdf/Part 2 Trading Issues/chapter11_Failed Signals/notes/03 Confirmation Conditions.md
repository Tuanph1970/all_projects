# 03 Confirmation Conditions

**Parent:** [[00 Chapter 11 Index]] · **Master:** [[01 Failed Signals]]
**Tags:** #chapter11 #confirmation #risk-management

## Definition

A **confirmation condition** is a rule that turns a *suspected* failed signal into an *actionable* one. Without it, every wiggle would qualify as a failure and you'd be trading noise. Schwager describes three confirmation flavours that can be used independently or in combination:

| Type | Trigger (for a bull trap) | Speed vs reliability |
|---|---|---|
| **Initial price confirmation** | Price closes back inside the prior range | Earliest entry, more false calls |
| **Strong price confirmation** | Price closes beyond the *opposite* end of the range | Best entry-quality, but you give up some price |
| **Time confirmation** | A specified window (e.g., 4 weeks) elapses without a new high beyond the breakout | Catches slow-grinding failures the price rules miss |

There is also an **invalidation condition**: a return to the breakout extreme cancels the failed-signal interpretation. More aggressive traders use a partial-invalidation (e.g., bull-trap stops out only if price climbs back to the *upper* end of the range after a strong-confirmation entry).

## Illustration

![[03_confirmation_conditions.png]]

Compare with the book's **Figures 11.4–11.5** (June 1994 T-bond, July 1993 silver), which overlay all three confirmation lines on real charts.

## Common-life analogy

You hear a rumour at work that a colleague has resigned.
- **Initial price confirmation** = they don't show up to today's stand-up. (Suggestive but they could just be sick.)
- **Strong price confirmation** = HR sends a goodbye email. (Now you're certain.)
- **Time confirmation** = three weeks pass and they've never been seen again, no goodbye email or otherwise. (Slow, but you can act on it.)
- **Invalidation** = they show up Monday morning with a coffee. (Rumour was wrong.)

The three rules are about *how much evidence is enough* before you act, with a clear trade-off between speed and certainty.

## Numeric example

Range: **$95–$104**. Breakout day closes $104.80.

| Day | Close | Initial confirm? | Strong confirm? | Time confirm? |
|----|-------|---|---|---|
| 1 | 104.20 | no | no | — |
| 4 | 99.50 | **YES** ($104 line crossed back) | no | — |
| 9 | 94.30 | already | **YES** ($95 line crossed) | — |
| 20 (no new high) | 99.10 | already | already | **YES** at 4-week mark |

If you require *two* of the three (Schwager's preferred robustness), entry would not trigger until Day 9.

## Python sketch

```python
def confirm_failed_breakout(df, breakout_idx, range_high, range_low,
                             time_window=20):
    """Yield ('initial'|'strong'|'time', day_idx) tuples in order of arrival."""
    breakout_high = df["high"].iloc[breakout_idx]
    fired = set()
    for j in range(breakout_idx + 1, min(breakout_idx + time_window + 1, len(df))):
        if df["high"].iloc[j] > breakout_high:
            return                                # invalidated
        c = df["close"].iloc[j]
        if "initial" not in fired and c < range_high:
            fired.add("initial");   yield "initial", j
        if "strong"  not in fired and c < range_low:
            fired.add("strong");    yield "strong",  j
    if {"initial", "strong"} & fired == set():
        yield "time", breakout_idx + time_window  # no price confirmation,
                                                  # but time elapsed
```

## Relationships within the chapter

- Used by **every** other concept-note in the chapter:
  - [[02 Bull and Bear Traps]] — uses range boundaries.
  - [[04 False Trend Line Breakouts]] — uses N closes back across the trend line.
  - [[05 Filled Gaps]] — uses close beyond prior-day close.
  - [[06 Return to Spike Extremes]] — uses close beyond the spike extreme.
  - [[07 Return to Wide-Ranging Day Extremes]] — uses close beyond the WRD's opposite extreme.
  - [[08 Counter-to-Anticipated Flag Pennant Breakout]] / [[09 Opposite-Direction Breakout After Normal Breakout]] — uses close beyond the opposite end of the flag.
  - [[10 Penetration of Top and Bottom Formations]] — uses close beyond the recent shoulder.
- The *speed vs reliability* trade-off here recurs in [[12 Future Reliability of Failed Signals]] (faster signals work better when the pattern is less crowded).

## When each condition works best

| Use… | When… |
|---|---|
| **Initial price** | Volatile market with sharp reversals; you want the best entry and accept whipsaws. |
| **Strong price** | Quiet or trendy market where you want fewer false signals. |
| **Time** | Slow-grinding markets that fail without a clean snap-back day. |
| **Two of three** | Default when capital preservation matters more than perfect entry. |

## Relationships outside the chapter

- The *idea* of confirmation generalises beyond Chapter 11: see the glossary entry **Confirmation** in the book's appendix, and its appearance in the breakout-system filter rules of [[Chapter 14 - Technical Trading Systems]].
- Confirmation is the natural counterpart to **filters** (Chapter 14) — both reduce false signals, but a filter is applied at signal time, a confirmation after.
- Where to put your protective stop once a confirmation fires is the topic of [[Chapter 9 - Stop Loss Points]].
