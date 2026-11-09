# S-5a — Method-correctness study: RESULTS (Part 2)

**Date:** 2026-11-09
**Pre-registration:** `docs/s5a_method_correctness_preregistration.md` (Part 1),
written before `tests/s5a_method_correctness.py` existed. No constant was changed
after seeing any of what follows.
**Reproduce:**
`PYTHONPATH=.:../../stock-common python3 tests/s5a_method_correctness.py <bars.tsv>`
(~1 minute, read-only, nothing in the pipeline touched.)

---

## 1. What was run

1,185 scan dates, 2021-03-15 → 2026-11-06, 93 symbols, production `ScanConfig()`
defaults. **320 episodes** across 218 dates (a symbol re-entering within 20 bars
counts once), against 94,681 ARM-LIQ observations and a seeded 320-name
ARM-RANDOM draw.

## 2. The results, against §9's pre-registered failure conditions

| Pre-registered failure condition | Result | Verdict |
|---|---|---|
| Breakout rate ≤ ARM-LIQ | 51.6% vs **40.2%** (ARM-RANDOM 46.6%) | **passes** |
| Mean excess 20-bar return ≤ 0 | **−0.59%** | **FAILS** |
| Returns flat across BROAD / NARROW | −0.47% vs −0.94% | passes |
| MA20 holders no better than losers | +7.99% vs −1.74% | passes (but see §4) |

### Primary — excess return vs the same-date liquid-universe mean

| horizon | candidates | ARM-RANDOM |
|---|---|---|
| +5 bars | −0.35% (median −0.81%) | +0.26% |
| +10 bars | −0.52% (median −1.12%) | +0.04% |
| +20 bars | −0.59% (median −1.57%) | −0.48% |

**Candidates did not outperform a random liquid Vietnamese stock.** They are
marginally *worse* at every horizon. That is a pre-registered failure condition
and it is reported as one.

### Secondary — breakout within 20 bars, on close

| arm | rate |
|---|---|
| candidates | **51.6%** |
| ARM-RANDOM | 46.6% |
| ARM-LIQ (all liquid names) | **40.2%** |
| candidates, against their own base pivot | 51.2% |

The one unambiguous positive: a candidate clears its own recent range
**half the time**, against 40% for a liquid name picked at random. The base and
squeeze geometry is selecting for something real.

## 3. THE PRIMARY METRIC TESTED THE WRONG THING, AND THAT IS MY ERROR

This is the most important sentence in the document. The pre-registration fixed
entry at **the close of the episode date** — the first day a symbol appears as a
candidate — on the reasoning that it was a price actually available. It is. But
it is **not where Qullamaggie buys.**

The source method is explicit (`Cẩm Nang`, Part 1 §2): *"Mua ngay khi giá vượt
qua đường kháng cự của vùng tích lũy… với một cây nến mạnh mẽ"*, with volume
above the base's average. The candidate date is when the stock goes **on the
watchlist** — still inside the base, before any breakout. Buying there is what
the method spends Part 2 building a watchlist in order to *avoid*.

So the primary result refutes **"buy every candidate at the close of the day it
appears"**, which nobody proposed, and says little about the method. The
secondary result is the one that bears on it: the breakout the method waits for
arrives about half the time, meaningfully more often than for a random liquid
name — and the other half is precisely what the entry trigger is there to skip.

The pre-registration is left as written. Fixing it retroactively would make
every number in it unfalsifiable, which is the whole thing pre-registration
exists to prevent.

## 4. The MA20 result is largely circular

+7.99% for holders against −1.74% for losers at +20 bars looks decisive and is
mostly an artefact of how it was measured: "stayed above its MA20 for 20 bars"
and "went up over 20 bars" are close to the same statement. It is not
look-ahead — nothing future-dated entered the entry decision — but as *evidence*
it cannot separate "the exit rule works" from "the exit rule is a proxy for the
outcome".

What it does say, and this part is clean: **only 38 of 320 candidates (12%) held
their MA20 for a full 20 bars.** Most candidates break down within a month. For a
method whose exit is *"chỉ bán hết khi giá đóng cửa nằm dưới đường MA này"*, that
is a high churn rate and a real cost the entry trigger has to earn back.

## 5. What this study establishes

- The scanner's **selection mechanism has content**: 51.6% vs 40.2% breakout rate
  is not noise-level, and it agrees with VT-4's 6.2× enrichment.
- **Regime matters in the direction the trend template implies** — BROAD beats
  NARROW at every horizon.
- **Buying the base is not a strategy.** Whatever edge the method has must come
  from the breakout trigger and the exits, not from candidate selection alone.
- Nothing here estimates edge, and §2's table is not a performance report.
  320 burst-correlated episodes over one bear-heavy cycle cannot carry one.

## 6. What should be measured next (Part 3, to be pre-registered separately)

The obvious successor, and it needs its own pre-registration before any code:

1. **Entry on the breakout, not on the candidacy** — first close above the pivot
   within N bars, with volume above the base's average, which is the method's
   actual trigger. Excess return measured from *there*.
2. **The 2–5% stop and the MA10/MA20 trail**, with VN reality applied: ±7%/±10%
   bands mean a breakout can lock at trần unfilled, and T+2.5 means the day-1
   stop is unreachable. Both belong in the arms, not in a footnote.
3. **A non-circular exit test** — compare *exiting* on the MA20 break against
   holding to +20 bars, on the same episodes.
4. Deeper history before any of it: `HISTORY_YEARS = 5` is our own setting and
   the vendor serves from ~2009, so three to four market cycles are available
   where this study had one.
