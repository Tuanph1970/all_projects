# 13 Traders Diary

**Step 6 of the [[00 Chapter 16 Index|Planned Trading Approach]]**

![[11_traders_diary.svg]]

## Definition

The **trader's diary** is the qualitative companion to the [[12 Traders Notebook]]. Where the notebook records *what* happened in numbers, the diary records *why* — in the trader's own words. Each trade gets a card with three sections:

1. **Reasons for the trade** — written **at entry**, before outcome is known. The chart pattern, the system signal, the macro thesis, the volatility setup. This timestamp matters: post-hoc rationalisation is impossible if the section is locked in before the trade resolves.
2. **How it turned out** — written at exit. The clean factual record of fill prices, max favourable excursion, max adverse excursion, what the chart looked like when exited.
3. **Lessons** — what the trade taught. By convention, the most important lessons are written **in CAPITAL LETTERS** to make them visually unmissable on later review.

The diary is reviewed periodically — weekly at minimum, monthly is typical. Patterns emerge across many entries that no single trade reveals.

## Easy Analogy

A surgeon's morbidity-and-mortality conference. After every difficult case, the surgeon writes notes on what they intended, what happened, and what they would do differently. No surgeon expects perfection; they expect *learning per case*. The crucial detail: the intent is recorded before the outcome, so the lesson cannot be rewritten by hindsight.

## Numeric / Concrete Example

**Trade #57 — short COPPER, March contract**

> **Reasons for trade (entered Apr 12):** Triple top failure on the daily chart at $4.85. RSI divergence at the third peak. Trend system flipped to short. Targeting prior swing low at $4.55. Stop at $4.92 — $700/contract risk, 1.4% of equity.

> **How it turned out (exited Apr 19):** Stopped out at $4.93 on a 2-day ramp through resistance. Loss: $720/contract including slippage. The triple top resolved into a flag continuation pattern; my "third peak" turned out to be the breakout.

> **Lessons:**
> - Pattern was visually compelling but **VOLUME WAS RISING ON EACH PEAK** — opposite of textbook triple top.
> - I IGNORED THE ROLLOVER WEEK; lower liquidity widened normal noise band, my stop was inside it.
> - SAW THE PATTERN I WANTED TO SEE. Pre-mortem question for next similar setup: "What would convince me this is a continuation, not a top?"

A quarterly review across 90 such entries reveals: 60% of CAPS lessons concern stop placement during low-liquidity windows. **That** is the actionable insight that changes the next 90 trades.

## Python Code

A diary card is mostly free-form text, but a tiny structure helps with later review and search:

```python
from dataclasses import dataclass, field
from datetime import date
from typing import List

@dataclass
class DiaryEntry:
    trade_id: int
    market: str
    entry_date: date
    reasons: str                    # written at entry, locked
    outcome: str = ''               # filled at exit
    lessons: List[str] = field(default_factory=list)
    
    def add_lesson(self, lesson: str, *, important: bool = False):
        # Convention: important lessons in CAPS so they pop on review
        self.lessons.append(lesson.upper() if important else lesson)
    
    def search(self, keyword: str) -> bool:
        haystack = ' '.join([self.reasons, self.outcome] + self.lessons).lower()
        return keyword.lower() in haystack
```

A quarterly review just iterates: `[e for e in entries if e.search('stop placement')]` and reads the matches end-to-end.

## Relationships

### Within Chapter 16
- The qualitative twin of [[12 Traders Notebook]] — both written nightly during [[11 Planning Time Routine]].
- Feeds directly into [[15 Segmented Trade Analysis]]: the segmenting often produces a number ("trades during rollover week have -0.4 expectancy"), and the diary explains *why*.
- The diary is where lessons surface that eventually rewrite [[01 Trading Philosophy]] — that's the feedback loop closing.

### Outside Chapter 16
- **Chapter 17 — Rules** — many of the 82 rules are diary lessons that one trader after another, across history, has had to write down before learning.
- **Chapter 18 — Rule #11 (Discipline)** — the diary is the audit trail that lets a trader catch themselves drifting from their own rules. Without it, the drift is invisible.

## When This Concept Works Well
- When the **Reasons** section is locked at entry — ideally in a system that timestamps it. A diary that can be edited after the outcome is known is a story, not a record.
- When the trader writes diary entries on **winning** trades with the same care as on losers. Skipping winners hides the "right reasons, lucky outcome" trade — the kind that builds false confidence.

## When It Fails
- When entries become formulaic ("good setup, took the trade, hit stop, lesson: be more careful") — empty calories.
- When CAPS are overused — if every lesson is shouting, none of them are. Reserve them for the lessons the trader expects to need to re-read.
- When the diary is never reviewed — writing without reading is just journaling. The value is in the periodic re-reading, where patterns appear that single entries can't show.
