# Trend Line Redrawing

## Description

Schwager's major practical warning: trend lines frequently need to be redrawn as a trend extends. "The simple fact is that trend lines tend to be penetrated, sometimes repeatedly, during their evolution" (p.39). This means trend lines "work much better in hindsight than in real time."

The root cause is **trend deceleration** — trends don't maintain constant slope. An uptrend that starts steep gradually flattens; a downtrend that starts with panic selling becomes a grind. Each deceleration breaks the old trend line without breaking the trend itself. The slope changes; the direction doesn't.

## Simple Analogy

Imagine driving on a highway and checking your speedometer every mile. At first you're going 80mph, so you draw a line predicting where you'll be at that rate. Then traffic slows you to 60mph — you've "broken" your prediction line, but you're still heading the same direction. You redraw for 60mph. Then traffic slows to 45mph — broken again, redraw again. An observer watching your old predictions would think you'd "reversed course" three times, when you were going the same direction all along, just slowing down.

## The Two Key Examples

### Figure 3.10 — Amoco (Uptrend, 3 redraws)

Line 1 (steep) → broken in mid-June → false sell signal
Line 2 (moderate) → broken in late July → another false sell signal  
Line 3 (shallow) → captures the mature phase

A mechanical trader would have sold twice and taken two losses while the stock kept climbing.

### Figure 3.11 — Matif Bond (Downtrend, redraw)

Steep downtrend line → broken to the upside in Feb 1994 → false buy signal
Redrawn shallower line → correctly captures the continuing downtrend

The "correct" line was invisible until after the false signal had already triggered.

## The Temporal Asymmetry

The fundamental issue: the information needed to draw the "correct" trend line only becomes available *after* the false signal has already occurred. At the moment of maximum ambiguity (the penetration), the only line you have is the one that's about to be proven wrong.

## Illustration

**Interactive simulation:** `assets/simulations/trend_line_redrawing_stepper.jsx`
- 6-step walkthrough of the Matif bond scenario (Figure 3.11 analog)
- Shows what you see in real time vs what hindsight reveals

**Interactive simulation:** `assets/simulations/amoco_uptrend_redrawing_stepper.jsx`
- 7-step walkthrough of the Amoco scenario (Figure 3.10 analog)
- Three lines progressively shallower, two false sell signals

## Connections

- **Depends on:** [[03 - Conventional Trend Lines]]
- **Produces:** [[11 - False Penetrations]]
- **Resolved by:** [[05 - TD Lines (DeMark)]] (auto-redrawing built in), Ch.11 Failed Signals (turns false breaks into opportunities)
- **Also mitigated by:** [[04 - Internal Trend Lines]] (handles slope changes more gracefully)
- **Source:** Schwager pp.35-39, Figures 3.10, 3.11, 3.12

---
*Tags: #practical-warning #schwager-ch3 #hindsight-bias #trend-deceleration*
