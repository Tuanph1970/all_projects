---
title: Change of Market Opinion
chapter: 10
concept_number: 7
tags:
  - exit-strategy
  - discretionary-trading
  - market-opinion
  - conviction
  - position-management
  - trading-psychology
related:
  - "[[Trailing Stops]]"
  - "[[Failed Signals]]"
  - "[[Overbought Oversold Indicators as Exit Signals]]"
  - "[[Contrary Opinion]]"
  - "[[Planned Trading Approach]]"
  - "[[Risk Control and Win Rate vs Profitability]]"
schwager_quote: "The trader sets no predetermined objectives at all, but rather maintains the position until market opinion changes to at least neutral."
---

# Change of Market Opinion

## Definition

The trader sets **no predetermined price objectives** and instead maintains the position until their informed market opinion shifts to **at least neutral**. When you no longer believe in the trade's thesis — even if you're not yet bearish — you exit.

> "This is another approach with very little flash, but lots of common sense."
> — Schwager, Chapter 10

## Core Principle

This is the **anti-formula** exit. No thresholds, no pattern geometry, no oscillator readings. Just continuous reassessment of a single question: *"Do I still believe in this trade?"*

The critical insight: you don't need to be *bearish* to exit a long. **Neutral is enough.** The burden of proof is on the trade to justify its continued existence. The moment that justification weakens to indifference, the trade has lost its reason to live.

## Simple Analogy

**Driving on a road trip with a plan.** You started heading north because you believed the destination was north. Road signs start contradicting your map — closed road, detour, unexpected terrain. At first you keep going (strong conviction). Then doubt builds. Eventually you realize you're no longer confident the destination is north — so you pull over. You don't need to be sure it's *south*. Just losing confidence in *north* is reason enough to stop driving north. And if the signs now clearly point south? The skilled driver turns around immediately.

## Schwager's Conviction Spectrum

| Conviction Level | Opinion | Action |
|---|---|---|
| 80-100% | Strongly bullish/bearish | Hold — thesis fully intact |
| 60-80% | Bullish/bearish | Hold — monitor for erosion |
| 50-60% | Moderately leaning | Tighten stops — conviction weakening |
| 40-50% | **Neutral** | **EXIT** — Schwager's trigger |
| 20-40% | Opposite direction | Exit or **REVERSE** |
| 0-20% | Strongly opposite | **REVERSE** (Ch. 11's 180° turn) |

## The 180° Turn (Chapter 11 Extension)

Schwager extends this concept beyond mere exit in Chapter 11:

> "The truly skilled trader will be able to do a 180-degree turn, reversing a position at a loss if market behavior points to such a course of action."

And in Chapter 12, his real-world deutsche mark trade demonstrates this:

> "This trade provides a perfect example of the desirability of quickly reversing a trade opinion if market conditions change. Only two days before implementation of a long position, I had been bearish and short."

The progression: strong conviction → weakening conviction → neutral → exit → and for the truly skilled: new conviction in the opposite direction → reverse.

## The Rationalization Trap (Chapter 18)

Schwager shares a deeply personal example about predicting the dollar would rise "for years." When the chart picture changed:

> "The discomfort and embarrassment I felt about these previous forecasts told me it was time to change my opinion."

> "In my earlier years in the business, I invariably tried to rationalize my original market opinion. I was burned enough times that I eventually learned a lesson."

The key behavioral warning: when you find yourself *rationalizing* — "it's just a pullback," "weak hands are being shaken out" — that rationalization itself is the signal that your opinion has changed but your ego hasn't accepted it yet.

## Chapter 16: Formal Place in the Trading Plan

In the trade planning worksheet (Chapter 16), Schwager positions change of opinion as a legitimate alternative to mechanical exits:

> "Some traders may prefer to forgo the use of objectives, allowing the timing of liquidation to be determined by either a trailing stop or a change of opinion."

This establishes a formal two-track exit framework:
1. **Mechanical track**: trailing stop (always running as a safety net)
2. **Discretionary track**: change of market opinion (continuous reassessment)

Whichever fires first triggers the exit.

## When It Works Best

- **For experienced, disciplined traders** who can honestly assess their own conviction without ego interference
- **In combination with a trailing stop** — the trailing stop provides mechanical protection while opinion assessment adds informed judgment
- **When the chart picture has changed qualitatively** — not a single indicator crossing a threshold, but a broader shift in the technical landscape
- **For longer-duration trades** where the original thesis may evolve significantly
- **When multiple weak signals accumulate** — no single factor triggers an exit, but together they erode conviction below the neutral threshold

## When It Fails

- **For traders prone to emotional decision-making** — fear and hope distort opinion assessment
- **When the trader is publicly committed to a view** — ego prevents honest reassessment (Schwager's "don't talk about your position" rule)
- **Without a mechanical backstop** — opinion-only exits have no defined worst case; always pair with [[Trailing Stops]]
- **When rationalization masquerades as analysis** — the trader convinces themselves the trade is still valid when it isn't
- **For systematic/algorithmic traders** — this is inherently discretionary and cannot be fully automated

## The Conviction Checklist Framework

To make the subjective process more disciplined, score each factor from the original trade thesis:

| Factor | Weight | Status Options |
|---|---|---|
| Trend direction (Ch. 3) | 2.0× | Supporting / Neutral / Opposing |
| Chart pattern structure (Ch. 5/10) | 1.5× | Supporting / Neutral / Opposing |
| S/R context (Ch. 4/10) | 1.0× | Supporting / Neutral / Opposing |
| Momentum/oscillators (Ch. 6/10) | 1.0× | Supporting / Neutral / Opposing |
| Sentiment (Ch. 10) | 0.5× | Supporting / Neutral / Opposing |
| Volume confirmation | 0.5× | Supporting / Neutral / Opposing |
| Failed signal risk (Ch. 11) | 2.0× | Supporting / Neutral / Opposing |
| Higher timeframe alignment (Ch. 7) | 1.5× | Supporting / Neutral / Opposing |

Weighted sum determines conviction percentage. When it drops below ~45% → opinion is neutral → exit.

## Cross-References

### Within Chapter 10
- [[Trailing Stops]] — The mechanical complement. Schwager pairs these in Ch. 16: trailing stop + opinion change = complete exit system
- [[Overbought Oversold Indicators as Exit Signals]] — OB/OS readings feed into opinion assessment (one factor among many)
- [[Contrary Opinion]] — Extreme sentiment is one input to overall market opinion
- [[Support and Resistance as Objectives]] — Price reaching key S/R shifts the technical picture and may affect opinion
- [[Measured Move]] — MM target hit may trigger opinion reassessment
- [[Chart-Based Objectives]] — Pattern targets influence the "is the thesis still valid?" question

### Within the Book
- [[Failed Signals]] (Chapter 11) — A failed signal is the most powerful single opinion-changer. If a breakout fails, opinion should shift immediately
- [[Planned Trading Approach]] (Chapter 16) — Opinion change formalized as a legitimate exit track in the trading plan
- [[Trends]] (Chapter 3) — Trend breaks are a primary trigger for opinion change
- [[Multi-Timeframe Analysis]] (Chapter 7) — Higher timeframe opinion shift overrides lower timeframe conviction
- [[Risk Control and Win Rate vs Profitability]] (Chapter 7) — Opinion-based exits can preserve the reward side of R:R by holding through noise that would trigger mechanical exits

## Python Implementation

See `change_of_market_opinion.py` for:
- `ConvictionAssessment` — Weighted checklist scoring system
- `build_default_checklist()` — Pre-built factors from all Ch. 10 methods
- `synthesize_exit_decision()` — Combines ALL Ch. 10 exit methods into a unified decision with priority hierarchy
- `MarketOpinion` enum — Schwager's opinion spectrum from strongly bullish to strongly bearish

### The Synthesis Function (Capstone)
```python
# Combine ALL Chapter 10 methods
decision = synthesize_exit_decision(
    method_signals={
        'Chart objective': 'exit',    # Target hit
        'Measured move': 'exit',      # MM reached
        'S/R objective': 'caution',   # Near resistance
        'OB/OS': 'exit',             # RSI overbought
        'Contrary opinion': 'caution', # Sentiment high
        'Trailing stop': 'hold',      # Not yet triggered
    },
    conviction=assessment,  # Current conviction score
    trailing_stop_hit=False,
)
# → "PARTIAL_EXIT: 3 methods triggered (confluence).
#    Take partial profits, trail the remainder."
```

### Decision Hierarchy
1. **Trailing stop hit** → full exit (mechanical override)
2. **Conviction at neutral/opposing** → full exit or reverse
3. **Multiple methods signaling exit** → partial exit (confluence)
4. **Single method signaling** → caution, tighten stops
5. **All methods holding** → hold position

## Key Takeaway

Change of Market Opinion is the **capstone concept** of Chapter 10. It's the least technical but most important exit method because it's the one that integrates everything else. Each of the six preceding methods produces a signal — but it's the trader's *informed judgment* that synthesizes those signals into a decision. Schwager deliberately places it last and keeps it brief because the concept is simple: **keep asking yourself if you still believe in the trade, and have the honesty to answer truthfully.** The trailing stop is your mechanical safety net. Your opinion is your informed override. Together, they form a complete exit framework.
