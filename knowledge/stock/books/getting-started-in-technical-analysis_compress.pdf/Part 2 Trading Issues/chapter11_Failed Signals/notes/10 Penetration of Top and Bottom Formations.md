# 10 Penetration of Top and Bottom Formations

**Parent:** [[00 Chapter 11 Index]] · **Master:** [[01 Failed Signals]]
**Tags:** #chapter11 #failed-signal #double-top #head-and-shoulders

## Definition

This concept covers failed-signal interpretations of **major reversal patterns**: double tops, double bottoms, triple tops/bottoms, and head-and-shoulders. When a market puts in one of these patterns it is broadcasting a high-confidence trend-reversal message; when price later **penetrates** the pattern's defining boundary, that strong message is repudiated and a powerful continuation in the *opposite direction of the pattern* often follows.

**Confirmation rules vary by pattern:**

| Pattern | Failure trigger |
|---|---|
| Double top | Close above the higher of the two tops |
| Double bottom | Close below the lower of the two bottoms |
| Head-and-shoulders **top** | Close above the **right shoulder high** |
| Head-and-shoulders **bottom** | Close below the **right shoulder low** |

Schwager notes that head-and-shoulders failures are **more common** than double-top/double-bottom failures (which are quite rare) and tend to make excellent trades. He also observes that after the failure trigger, prices often **pull back briefly** before the real continuation move begins — patient traders can wait for the pullback rather than entering at the trigger.

## Illustration

![[10_failed_head_shoulders.png]]

The book's **Figures 11.27–11.30** show real examples: penetrations of double tops in coffee (May/July 1994), a failed H&S top on IBM (Fig 11.29), and a failed H&S bottom in soybean oil (Fig 11.30).

## Common-life analogy

A teenager has run out of patience with their hometown. They've made two big "I'm leaving" announcements over six months — packed bags, made a scene, called grandma to ask if they can stay (the **double top** of leaving energy). Each time the family talked them out of it. Now imagine a year later they suddenly buy season tickets to the local theatre and start making weekend brunch plans with friends in town. They've **closed above the highest leaving-announcement peak**: the original "I'm leaving" message is fully repudiated, and you can confidently predict they're staying for a while.

## Numeric example — failed head-and-shoulders top

Stock prints:
- **Left shoulder high:** $58 (March)
- **Head high:** $64 (May)
- **Right shoulder high:** $59 (July)
- **Neckline:** ~$50

The market then drops through the neckline to $48 — the textbook H&S top has played out. But instead of continuing down, it bases at $48 and rallies.

- **Day** — closes $59.30 → above the right-shoulder high of $59 → **failed H&S top**.

Long entry at $59.30, stop just below the most recent reaction low (say $52.50). Risk = $6.80. The failure of an H&S top of size $14 (head minus neckline) often projects 1× pattern height above the trigger, so target ~$73.

If the trader prefers Schwager's "wait for pullback" approach, they wait for a retracement to ~$54–55 before entering, accepting that they'll miss the trade entirely if no pullback comes.

## Python sketch

```python
from dataclasses import dataclass

@dataclass
class HeadShoulders:
    left_shoulder: int
    head: int
    right_shoulder: int
    pattern: str = "top"        # "top" or "bottom"

def hs_failure(df, hs: HeadShoulders, lookahead=60):
    rs_idx = hs.right_shoulder
    if hs.pattern == "top":
        rs_level = df["high"].iloc[rs_idx]
        for j in range(rs_idx + 1, min(rs_idx + lookahead + 1, len(df))):
            if df["close"].iloc[j] > rs_level:
                return j
    else:
        rs_level = df["low"].iloc[rs_idx]
        for j in range(rs_idx + 1, min(rs_idx + lookahead + 1, len(df))):
            if df["close"].iloc[j] < rs_level:
                return j
    return None
```

Full version handling double tops/bottoms too: `code/chapter11_detectors.py`.

## Relationships within the chapter

- One of the **structural-pattern failures** alongside [[11 Breaking of Curvature]] (which handles rounding tops/bottoms in the same way).
- Uses [[03 Confirmation Conditions]] — specifically the "close beyond a reference level" form, with the reference being the right shoulder or the higher top.
- The **patience-for-pullback** advice here echoes the speed-vs-reliability theme in [[03 Confirmation Conditions]].

## When the concept works best

- **After well-formed patterns.** A textbook H&S with proportional shoulders, clear neckline, and obvious volume profile is more meaningful than a sloppy three-bumps pattern, both for the original signal and its failure.
- **For head-and-shoulders specifically.** Schwager calls these failures "common and excellent" — a useful asymmetry, since the original H&S pattern is also famous, so its failures are often crowded entry triggers.
- **When the pullback approach is available.** Best risk-adjusted entries come from waiting for the post-trigger retest.

## Relationships outside the chapter

- Top-and-bottom pattern anatomy (double, triple, H&S, V tops): [[Chapter 5 - Chart Patterns]].
- The **neckline** definition and behaviour are detailed in the book's glossary entry for **Neckline** and in [[Chapter 5 - Chart Patterns]].
- Stop-placement off the right shoulder or pattern extreme: [[Chapter 9 - Stop Loss Points]].
- This is the failed-signal pattern that Schwager calls out specifically in [[Chapter 7 - Is Chart Analysis Still Valid]] when he argues failed H&S patterns help keep chart analysis useful even after the patterns themselves have become widely known.
