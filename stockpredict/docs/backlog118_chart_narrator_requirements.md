# Backlog #118 — plain-text chart analyst: requirements vs. what we have

Owner requirements supplied 2026-11-03 (in Vietnamese), describing what
technical-analysis content on TikTok/Facebook actually covers. **Output is text
only — nothing renders or exports video.**

This document maps each requirement onto (a) what already exists in the
codebase and (b) **what this project has already measured about it**. (b) is the
part that shapes the design, because for several of these the measurement came
back negative — and a narrator that speaks confidently about a refuted signal is
worse than no narrator.

Legend: **ADOPTED** = passed its gate out-of-sample · **REAL** = exists and
beats a null, but no improvement demonstrated · **REFUTED** = measured, failed
· **ABSENT** = not implemented.

---

## 1. Xu hướng — trend (kênh giá, trendline, MA10/20/50/200)

| piece | state | evidence |
|---|---|---|
| Moving averages | **exists** | configurable `fast_ma`/`slow_ma`; indicators computed in analysis-service and the prediction feature builder |
| Regime (TREND_UP / TREND_DOWN / RANGE) | **exists** | `regime/classifier.py`, `compute_regime` |
| Trendline engine | **REFUTED** | EM-5 Gate A asked "does the SLOPE earn anything over a HORIZONTAL level through the same anchors?" — it did not. Engine kept as apparatus, feature Not Built |
| Price channel / return line | **ABSENT** | EM-5 Phase B, conditional on Gate A passing. It did not pass, so this was never built |

**Consequence.** MAs and regime are safe to narrate. A drawn trendline can be
*described* ("the last three lows rise") but must not be presented as carrying
predictive weight over a flat level — that is exactly the claim EM-5 tested and
lost. Channels would be new work.

## 2. Hỗ trợ / kháng cự — support & resistance, breakout / breakdown

| piece | state | evidence |
|---|---|---|
| S/R levels | **REAL** | EM-2 Done. Every method beats a matched-distance random null *significantly* — the levels are not imaginary |
| Volume-weighted strength | **REFUTED** | no EM-2 measure beat the shipped **touch count** at any threshold. Strength is still `len(cluster)` |
| E&M "third attack succeeds" | **REFUTED** | 42.3% against a predicted >50% |
| Breakout / breakdown detectors | **exists** | `SR_BREAKOUT`, `N_DAY_BREAKOUT`, `MA_CROSS`, `SR_BOUNCE` |
| Penetration filter (how far past a level counts) | **measured inert** | EM-9: across a *tenfold* threshold range hit rate moved 0.411 → 0.419. Decision was DO NOT CHANGE |
| Throwback / pullback entry at a broken boundary | **REFUTED** | EM-7, negative at gate 2 |

**Consequence.** Naming levels is well supported. Claiming a breakout is
*reliable* is not: the detectors fire, but nothing here has shown the resulting
signal predicts, and the filter that was supposed to separate real breaks from
noise does not change the hit rate.

## 3. Chỉ báo — RSI, MACD, Bollinger, Volume

| piece | state | evidence |
|---|---|---|
| RSI, MACD, Bollinger Bands | **exists** | computed in analysis-service; also in the prediction feature builder |
| Volume primitives | **ADOPTED** | EM-1 Done. `relative_volume()` = volume ÷ its own trailing **median** (median so one climax day cannot absorb into the baseline), per-symbol only, explicit unknown-reasons |
| RSI divergence | **ABSENT** | not implemented |
| Volume confirmation of a pattern | **exists** | `PatternVolumeRule`, `BreakoutRule`, `ClimaxFlag`, `VolumeVerdict` |

**Consequence.** Volume is the best-evidenced input in the whole system and
should carry the most narrative weight. Divergence is new work.

## 4. Mẫu hình giá — chart patterns & candlesticks

**Eleven chart-pattern detectors exist** (this is EM-1's "11 detectors"):
ascending / descending / symmetrical triangle, double top, double bottom,
head-and-shoulders, inverse head-and-shoulders, flag, pennant, gap,
wide-ranging day, plus a trap detector.

| piece | state | evidence |
|---|---|---|
| Classic chart patterns | **exists** | detectors above; confidence de-quantised under #70 so a gate can be placed |
| Volume validation of those patterns | **ADOPTED** | EM-1 Done |
| Nến Nhật — candlestick reversals (Doji, Hammer, Engulfing) | **ABSENT** | not implemented anywhere |
| Objective-completion ("a reversal must have something to reverse") | **exists** | EM-8, two fixes shipped |

**Consequence.** Candlestick patterns are a genuine gap against the
requirement — one of only three pieces of real new analysis work this document
identifies.

## 5. Chiến lược — entry, take profit, stop loss, tỷ trọng giải ngân

| piece | state | evidence |
|---|---|---|
| Stop loss | **ADOPTED** | EM-3 basing-point trail: 61 symbols no EM-3 study had seen, +16,383 net P&L/symbol, clustered t=+8.97, 54/61 positive, 76% of the advantage attributable to the rule. Became the `/backtest` default 2026-11-03 |
| Take profit / targets | **exists** | `target_module.py`; EM-8 calibrated objective completion |
| Entry signals | **weak** | #82 measured the ten failed-signal verdict kinds as **no better than nothing**; #79 found one significantly **BACKWARDS** |
| Per-position sizing | **exists** | `risk_per_trade_pct`, `sizing_module.py`, `pyramiding.py` |
| Portfolio-level exposure (tỷ trọng) | **REFUTED** | EM-4's Magee governor is unsupported at every phase, instrument and threshold (#87/#90/#99/#100). Measure built, governor deliberately not |

**Consequence, and this is the most important line in the document.** This
section is explicit investment advice about a real person's money, and the
evidence underneath it is uneven: the **stop** has a genuinely strong,
out-of-sample answer, while the **entry** rests on signals measured as no better
than nothing. A narrator that emits "mua ở X, chốt lời ở Y, cắt lỗ ở Z" in one
confident breath would present those as equally grounded. They are not.

---

## What this means for the build

**Three pieces of genuinely new analysis**, everything else is composition:
1. Candlestick reversal patterns (Doji, Hammer, Engulfing, …) — §4
2. RSI divergence — §3
3. Price channel / return line — §1 (note EM-5's slope result argues against expecting much)

**Binding narration rules**, carried over from the #118 row and now specific:
- Every claim travels with its measured standing. "Kháng cự tại 22,800 (3 lần
  kiểm định)" is supportable; "kháng cự mạnh" is not, because volume-weighted
  strength was refuted.
- Where the finding is *no measurable edge*, say so. That covers trendline
  slope, breakout filtering, the throwback entry, and portfolio exposure.
- The stop may be stated with confidence. The entry may not.
- Phase 1 is **template-based, no LLM** — a template cannot invent a claim, the
  same chart must yield the same text, and the existing `en.json`/`vi.json`
  gives exact control over Vietnamese financial wording. An LLM rewriter that
  is forbidden from altering any number or verdict stays available for phase 2.

**Still unanswered, and it drives length and structure more than anything
else:** where does the text appear — a UI panel, an API response, a
notification, or on demand per symbol?
