# 12 Future Reliability of Failed Signals

**Parent:** [[00 Chapter 11 Index]] · **Master:** [[01 Failed Signals]]
**Tags:** #chapter11 #meta-principle #market-evolution

## Definition

This is Schwager's **meta-observation** about the failed-signal idea itself. He proposes a general principle: there is an **inverse relationship** between the popularity of a chart indicator and its efficiency. The more traders watch and act on a pattern, the worse the pattern's edge gets — because the crowd's stop orders cluster predictably and become exploitable. He uses this to explain why pre-1980s breakouts worked beautifully (few users) but modern breakouts are riddled with false signals (many users).

The corollary, and the key insight of the whole chapter, is that the **concept of failed signals can be made dynamic**: peg "what counts as a failed signal" to whatever the prevailing technical wisdom is. If a new pattern becomes popular in the future, *that* pattern's failure becomes the high-quality signal. In this sense, failed-signal trading is **timeless** even though specific failure rules are not.

There is also a self-defeating warning: if failed-signal trading itself became as popular as breakout trading, its edge would erode in turn. This is the meta-principle applied to itself.

## Illustration

![[12_future_reliability.png]]

The illustration plots the schematic shape of Schwager's claim: a steep decay in average reliability as the percentage of traders using an indicator grows.

## Common-life analogy

A small café in a sleepy neighbourhood serves the best coffee in town for a few years. Locals know the trick. When a travel blogger writes about it, lines snake around the block, the staff burn out, the beans aren't roasted as carefully, and the experience steadily decays. The café didn't change — *the relationship between the café and its clientele* changed. Once everyone knew the secret, the secret stopped being a secret.

The same dynamic governs trading patterns: as soon as everyone watches the same line, that line stops being where the action is — and the action moves to whatever line the watchers don't yet see.

## Numeric example

Suppose 500,000 traders use a 50-day breakout system on a given stock. On a typical breakout day, perhaps 20,000 of them place buy-stop orders just above the 50-day high. Those 20,000 buys execute on the breakout, but no follow-on order flow appears. Result: a 0.8% breakout pop, then a 3% reversal — the textbook bull trap. As more traders adopt the system, the breakout pop shrinks (because more pre-positioning) and the post-trap reversal grows (because more disappointed exits). A trader who reverses at the trap can systematically harvest this distortion.

If failed-signal trading then becomes ubiquitous in the same way, the reversal becomes pre-positioned too, and the next layer (failures of the failures) becomes profitable. Each new layer is more nuanced and harder to define, which is *why* it remains workable for longer.

## Python sketch

```python
def reliability_curve(popularity_pct, decay=35, baseline=5):
    """Toy model of Schwager's claim:
       reliability falls roughly exponentially with crowd size."""
    import numpy as np
    return 90 * np.exp(-popularity_pct / decay) + baseline

# Application: a system that is more reliable when fewer adopters use it
# might still be worth trading at lower size; very crowded systems
# require failure-of-pattern logic to stay profitable.
```

A more rigorous test would back-test breakout-system performance against an estimate of the system's *adoption share* over time and look for the predicted negative correlation.

## Relationships within the chapter

- This is the **closing note** of Chapter 11 and provides the philosophical underpinning of [[01 Failed Signals]] as a strategy. Without this principle, failed signals would just be one more pattern; with it, they are a *structural* feature of crowded markets.
- It also explains why traders should pay close attention to *which* patterns are popular at any given time — the menu of high-quality failures changes as fashion changes.
- It generalises the dynamic that already shows up in every other concept-note: the more textbook the original signal, the more meaningful its failure.

## When the principle works best (or matters most)

- **Across decades**, when comparing how well a given setup worked in the 1970s vs. now.
- **In rotation**: when an alternative method (cup-and-handle, harmonic patterns, supply-demand zones) becomes the trend-of-the-decade among retail traders, those new patterns become the new candidates for failure-trading.
- **Conservatively** — when in doubt about whether a new technical tool works, ask first: *how popular is it*? Very popular = expect noise. Obscure = expect quieter, longer-lived edge.

## Relationships outside the chapter

- The validity-of-charts question this principle helps answer is the entire subject of [[Chapter 7 - Is Chart Analysis Still Valid]]; failed signals are one of the five reasons Schwager argues charts remain valid.
- The arms-race dynamic between traders and patterns is also discussed implicitly in [[Chapter 14 - Technical Trading Systems]] (problem #1: too many similar systems → "trading with the crowd") and [[Chapter 15 - Testing and Optimizing Trading Systems]] (overfitting).
- The market-wisdom interviews in [[Chapter 18 - Market Wizardom]] return to this theme repeatedly: edges decay; staying profitable requires evolving with the crowd.
- The principle dovetails with **Random Walk Theory** (raised in the **Introduction**): if patterns have edge only when uncrowded, that's a partial concession to random-walk skeptics — but it also explains why charts can keep working for the disciplined minority.
