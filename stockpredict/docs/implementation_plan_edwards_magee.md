# Implementation Plan — Edwards & Magee Validation Layer

**Phase 0 artifact** (candidate register — no design, no plan, no code).
**Date:** 2026-10-10
**Inputs:** `docs/edwards-magee-technical-analysis-of-stock-trends-9th-edition.md`
(reading notes for *Technical Analysis of Stock Trends*, 9th ed., Edwards · Magee · Bassetti),
read against the shipped code.
**Status:** every candidate below is **Candidate — not started**. Nothing here is committed work.

---

## Why this document exists

The repo's pattern and tactics code is a **Schwager** implementation. Schwager and Edwards &
Magee agree closely on the *shapes* (head-and-shoulders, triangles, flags, double tops) and on
the *tactics* (breakout entries, trailing stops, fixed-fractional sizing) — and those are
already built. Where they diverge is the **evidence layer**: E&M treat volume, support/resistance
provenance, and basing-point geometry as the conditions that separate a real formation from a
drawing. Almost none of that layer exists here.

This file is the register of what the book offers that the code does not, with the evidence for
each gap, so the next session can pick one or two and enter the design phase with the audit
already done.

### Workflow position

```
Phase 0  this document          — candidate register           ← you are here
Phase 1  docs/SRS_<topic>.md    — design / requirements (FR-EM-*)
Phase 2  implementation plan    — one PR-sized task per session
Phase 3  implement              — one task at a time, tests first, then STOP
Phase 4  document               — user guide + workbook update
```

Per `CLAUDE.md`, requirement IDs are how features get referenced. The ID prefix reserved for
this workstream is **`FR-EM-*`**, and the candidate IDs below (`EM-1` … `EM-9`) are placeholders
that the Phase-1 SRS will replace with real requirement IDs.

---

## The audit: what is already covered

Recorded so the gap list can be trusted, and so no candidate accidentally rebuilds shipped work.

| E&M method | Already implemented at |
|---|---|
| Head-and-Shoulders + inverse ("Kilroy") | `ai-insights/app/services/patterns/reversal.py:371` · `chart-decomp-lib/.../patterns/head_shoulders.py` |
| Double Top / Bottom | same two registries |
| Flag · Pennant · Symmetrical / Ascending / Descending Triangle | `ai-insights/.../patterns/continuation.py:773` · `chart-decomp-lib/.../patterns/{flag_pennant,triangle}.py` |
| Gap classification · Wide-Ranging Day | `continuation.py` (`GapDetector`, `WideRangingDayDetector`) |
| Bull trap / Bear trap · the false-signal reversal rule | `ai-insights/.../patterns/trap.py:203` · `decision-helper/.../signal/failed_signal.py` |
| S/R as clustered swing pivots, typed support/resistance/flip, with touch count and age | `analysis-service/app/services/analysis_service.py:203` `_find_sr_levels` |
| Donchian / n-day high-low breakout (Turtle entry) | `decision-helper/.../signal/trend/n_day_breakout.py` |
| Moving average as "automated trendline" + crossover | `decision-helper/.../signal/trend/ma_cross.py` |
| Entry on a 33/50/67 % correction (Magee's 40–45 % rule, approximately) | `decision-helper/.../signal/trend/midtrend.py` (`RETRACEMENT_LEVELS`) |
| Protective stop, never widened; chart > swing > ATR > money hierarchy | `decision-helper/.../risk/stop_module.py` |
| Measuring objective as a target; S/R target; fixed R:R fallback | `decision-helper/.../risk/target_module.py` |
| Position sizing from stop distance (the Scott procedure) + position cap | `decision-helper/.../risk/sizing_module.py` |
| Pyramiding with a cap and tightened stops | `decision-helper/.../risk/pyramiding.py` |
| Breakout penetration filter + time-delay confirmation | `decision-helper/.../confirmation/layer.py` |
| Portfolio risk aggregation (stop-based worst case) + correlation | `decision-helper/app/api/routes.py:1477`, `:1566` |
| Random-walk null benchmark for detections (E&M has no equivalent — stricter than the book) | `chart-decomp-lib/chart_decomp/infrastructure/validation/null_fpr.py` |

### The finding that dominates the register

**No pattern detector in this repository reads volume.** `grep -rn volume` over both pattern
packages (`ai-insights/app/services/patterns/`, `chart-decomp-lib/chart_decomp/infrastructure/patterns/`)
returns nothing.

- `patterns/base.py:115` `_validate_ohlc` requires only `{high, low, close}`.
- Yet `insights_service.py:691` `_fetch_historical_prices` builds its frame straight from the
  stock-data-service history payload, which **includes `volume`**, and that same frame is handed
  to all eleven detectors at `insights_service.py:1988-1990`.

So the column is already in memory at the detector boundary and is discarded. For E&M this is
not a detail: volume is the confirming condition on the majority of their patterns (Ch 6, 7, 11,
12, 28), and tenet 9 — *"volume goes with the trend"* — is one of the twelve. Candidates
**EM-1, EM-2, EM-7 and EM-8** all descend from this one fact.

By contrast `chart-decomp-service` accepts a bare close series
(`services/chart-decomp-service/app/services/decomp_service.py:84`, `np.asarray(req.series)`),
so extending any volume work into *that* package additionally requires a request-schema change.
`ai-insights` needs no new plumbing at all.

---

## Binding constraints on everything in this register

From `CLAUDE.md` (the chart-system standing rules), which bind this workstream too:

1. **C1 strict causality.** A volume gate, an S/R level, a basing point and a breadth reading are
   all computed from `data_up_to_t` only. No full-series pass then sliced.
2. **C4 mandatory benchmark.** Each candidate names the benchmark it must beat below. "Improves"
   means out-of-sample and significant, never "looks better on one chart".
3. **No magic numbers as assertions.** E&M's figures (3 %, 40 %, 10 %, 9:1 odds, "third attack")
   are the book's *rules*, so they are legitimate defaults — but they are 1940s–1960s NYSE rules.
   Each must be re-measured on VN data before being trusted, and tests assert properties, not the
   book's numbers.
4. **Reuse before building.** Several candidates are edits to shipped modules, not new modules.
   The audit table above is the check against duplication.

---

## Candidates

### EM-1 — Volume validation on the existing detectors  ★ recommended

- **E&M:** Ch 6 (H&S volume sequence), Ch 7 (rounding bottom's volume trough; the H&S *bottom*
  where the volume pattern is **not** the inverse of the top), Ch 11 (flag/pennant volume must
  dry up), Ch 12 (breakaway gap — *"false moves are seldom attended by gaps"*), Ch 10
  (broadening formation: volume high and irregular throughout), Ch 28 (climactic-volume
  cancellation; the three expected volume peaks of a minor move).
- **The book's requirement:** volume is a *condition of validity*, not a decoration. A
  head-and-shoulders top needs a heavy left shoulder, a decidedly lighter right shoulder, and
  (for the bottom) a conspicuous burst on the neckline break. A flag is only a flag if volume
  diminishes continuously and it resolves inside ~4 weeks. Volume is judged **relative** to that
  stock in that period, never as an absolute share count.
- **Now:** no detector reads the column (see above). `confidence` is pure geometry.
- **Gap:** every detection currently scores identically whether it formed on expanding or
  collapsing turnover.
- **Where it lands:** a `volume_profile` evaluation in `ai-insights/app/services/patterns/`,
  consumed as a per-detector multiplier or gate on `confidence`; `PatternMatch` grows the
  volume evidence fields. Optional second step: the same gate in `chart-decomp-lib`, which needs
  the `decomp_service.py` schema change first.
- **Mandatory benchmark (C4):** the existing null-FPR harness
  (`chart-decomp-lib/.../validation/null_fpr.py`) and the planted-pattern tests. The gate earns
  its place only if it **lowers the false-positive rate on random-walk surrogates without
  lowering planted-pattern recall**. That is a clean pass/fail, and it is the reason this
  candidate is cheap to evaluate.
- **Effort:** S–M. No new data plumbing for `ai-insights`.
- **Risk:** VN tickers include thin names where volume is lumpy or zero for days — E&M's own
  "Dormant Bottom" (Ch 7). The gate must degrade to neutral on thin data, never to "reject".

### EM-2 — Volume-weighted S/R with role reversal and attack count  ★ recommended

- **E&M:** Ch 13 (the whole chapter), Ch 30.
- **The book's requirement:**
  - A level's strength comes from the **volume that changed hands there**, not from how many
    times price visited it.
  - The precise level is the **volume-weighted average of the old congestion's closes** — its
    "centre of gravity".
  - **Role reversal:** *"a former Top, once surpassed, becomes a Bottom zone; an old Bottom,
    once penetrated, becomes a Top zone."*
  - **Distance-away:** expect little real supply from a 20–35 priced bottom unless price later
    fell **more than 10 % under it**.
  - **Time decay:** a one-to-two-year-old level beats a four-to-five-year-old one, *"but the
    latter does not lose all of its potency by any means."*
  - **The third-attack rule:** each repelled attack consumes some of a level's power, and *"it
    is an odds-on assumption that a third attack at a Resistance Level will succeed in
    penetrating it."*
  - **Round figures** (20, 30, 50, 100) create levels with no vested interest behind them,
    especially in new high ground.
  - And the correction that bites: boardroom usage calls the last reaction low the support; E&M
    name the **previous top**. *"It is much easier for prices to push up through a former Top
    level than through the Resistance set up at a previous volume Bottom."*
- **Now:** `analysis_service.py:203` clusters swing pivots within 2 %, types each cluster by
  whether highs or lows dominate, and sets `strength = len(cluster)` — a touch count. No volume,
  no break history, no decay, no attack count, and `_find_support_resistance` (`:265`) then
  splits purely on which side of spot a level sits.
- **Why it has the highest leverage in this register:** four shipped consumers read that level
  set — the CHART stop (`stop_module.py`), the SR_LEVEL target (`target_module.py`), the
  bounce/breakout signals (`signal/range/sr_bounce_breakout.py`) and the trap detector
  (`patterns/trap.py`). One improvement propagates to all four.
- **Where it lands:** `analysis-service/app/services/analysis_service.py` `_find_sr_levels`, with
  the `SRLevel` schema growing volume, attack-count, break-history and decay fields.
- **Mandatory benchmark (C4):** forward hit-rate of levels — does price actually reverse at
  volume-weighted levels more often than at the current touch-count levels, and does the
  third-attack rule beat a coin flip on VN data? Benchmark = the present implementation, plus a
  random-level null. Reuse the forward-return machinery already written for
  `news-service/app/services/call_scorer.py`.
- **Effort:** M.
- **Risk:** needs volume-at-price, which the current OHLCV rows support only approximately
  (daily bars, no intraday distribution). The "centre of gravity" must be defined honestly as a
  volume-weighted close average and documented as the approximation it is.

### EM-3 — Basing-point stop engine (Three-Days-Away + the 3 % new-high rule)

- **E&M:** Ch 28 and Bassetti's Ch 28.1, which Bassetti calls *"of absolutely basic importance"*.
- **The book's requirement**, as the four numbered rules of Ch 28.1:
  1. A high is made, recognised by no higher prices for the moment.
  2. Prices recede to a candidate low; watch each later day whose range lies **completely
     outside** the candidate's range.
  3. When **three such days** occur before a new low, the candidate becomes a **basing point** —
     raise the stop to **x % under the low of that basing-point day** (the book uses 6 %).
  4. When a new high exceeds the previous high by **3 %**, a new basing point is set at **the low
     of that new-high day**.
  Stops are **never** lowered, even when a later low undercuts an old one — the filter is what
  keeps the position. The rationale is Kovner's, quoted by Bassetti: put stops *"where they're
  hard to get to"*, because locals hunt the obvious prior low.
- **Now:** `stop_module.py` offers CHART / SWING / ATR / MONEY with an ATR trailing stop. The
  swing stop uses the nearest confirmed pivot — which is exactly the obvious prior low E&M warn is
  hunted — and nothing implements the three-days-away confirmation or the new-high advance.
- **Where it lands:** a `BASING_POINT` stop kind in `decision-helper/app/services/risk/stop_module.py`,
  plus the advance rule in the trailing path; `position_states.current_stop` already persists it.
- **Mandatory benchmark (C4):** A/B against the shipped ATR trailing stop in the existing
  backtest harness (`decision-helper/app/services/backtest/`), on the same signals, reporting
  stop-out frequency, average adverse excursion before exit, and expectancy. This is the one
  candidate that produces a single comparable number.
- **Effort:** S–M. Fully mechanical, self-contained, no new data.
- **Risk:** E&M's own caveat — advancing stops on new highs too (rule 4) can force a premature
  exit on a mid-trend blow-off. Ship rule 4 behind a flag and measure it separately from rules
  1–3, as Bassetti's "simplified teaching version" does.

### EM-4 — Magee Evaluative Index as a breadth-driven exposure governor

- **E&M:** Ch 38 (the MEI, one of the book's genuinely original tools), applied in Ch 42.
- **The book's requirement:** mark each chart in a universe `+` or `−` weekly by its *major*
  trend and total them — *"if 75 are plus, the market looks 75 % Bullish to you."* Then **scale
  total commitments to the reading**: larger long exposure at 80 % than at 53 %, so the account
  is *"almost automatically withdrawn from a deteriorating market… without the need for torturing
  decisions."* Magee's second use proportions capital between long and short around the 50 %
  line (Bassetti's "Natural Hedge"). E&M also report it as an overbought/oversold gauge: *"for
  over 20 years, all major stock market Bottoms have corresponded with extremely low MEI
  readings"* — ≤ 5–9 % Strong.
  The chapter's premise is the statistical demolition: of ~700 stocks around 1929, *"only 27 % of
  the stocks acted the way everybody knows all stocks acted."* The index is an abstraction;
  breadth is the reality.
- **Now:** no breadth measure anywhere, and no portfolio-level exposure scaling. Risk is
  per-position (`sizing_module.py`) and reported after the fact (`routes.py:1477` risk-overview);
  nothing caps *aggregate* exposure by market condition. The nearest thing is the per-symbol
  regime classifier (`decision-helper/app/services/regime/classifier.py`), which already returns
  TREND_UP / TREND_DOWN / RANGE — i.e. the `+`/`−` mark E&M ask for, computed objectively.
- **Where it lands:** a breadth series built by sweeping `classify_regime` across a universe
  (VN30, or the user's watchlist), stored as a daily time series; consumed as a risk cap in
  `sizing_module.py` / the discipline rules engine, and surfaced on the risk dashboard.
- **Mandatory benchmark (C4):** against constant exposure. Does MEI-scaled sizing improve
  risk-adjusted return (or cut max drawdown) out-of-sample versus a fixed risk-per-trade, on the
  same signal stream? Separately: do low MEI percentiles actually precede VN-Index bottoms?
- **Effort:** M. Also the only portfolio-level candidate here — everything else is per-ticker.
- **Risk:** VN30 is thirty names in a market where breadth is dominated by a few large caps;
  E&M's 100-chart universe assumption needs restating for VN. Also note Bassetti's own 9th-edition
  revision — he stopped trusting a single index and demanded agreement across three (see EM-6).

### EM-5 — Trendline engine with authority scoring and the Three-Fan Principle

- **E&M:** Ch 14, Ch 15, applied in Ch 29.
- **The book's requirement:**
  - Up trendline across the minor-reaction **bottoms**, down across the minor-rally **tops** —
    never bottom-to-top, never through the price track.
  - **Three tests of authority**, weighted in this order: number of contacts ≫ length/duration >
    angle (flatter is more significant).
  - **Three tests of valid penetration:** a close beyond by **3 %** (2 % in averages), volume, and
    the feeble volume-less pullback that fails to regain the line.
  - **Return line and channel**, whose best use is *negative* — a rally that fails to reach the
    return line signals deterioration — with the symmetry rule that the margin of the miss tends
    to equal the margin of the next break.
  - **The Three-Fan Principle:** three successively flatter lines from one origin, and *"when the
    third is broken the correction's extreme has been seen"* — a bottom-identifying signal with
    no analogue anywhere in this codebase.
  - Origin rules: draw major bull lines from the **second** intermediate bottom, intermediate
    lines from the **right shoulder**, not the head.
- **Now:** lines are fitted only *inside* detectors (`continuation.py:306` `_triangle_trendlines`,
  `chart-decomp-lib/.../patterns/triangle.py`). There is no standalone trendline object, no
  authority score, no channel, no fan logic, and no trendline overlay on the frontend charts.
- **Where it lands:** ~~new module — most naturally in `analysis-service` beside the S/R work~~ —
  **corrected at Phase 1: in-process in `decision-helper`.** The harness makes no per-bar HTTP
  calls, so anything facing a C4 benchmark needs an in-process path (the lesson EM-7's Phase 1 and
  EM-8's `M3` both taught). An `analysis-service` home and the chart overlay belonged to Phase B,
  which was not built.
- **CLOSED 2026-10-23 — `docs/em5_trendlines.md`.** Scoped to **Phase A** (engine + harnesses +
  one gate) because full scope was 12–16 sessions and the frontend was only worth building if the
  engine earned it. **Gate A FAILED: 0 of 3 horizons at all three penetration settings**, and not
  as a null — the **horizontal through the same anchors is significantly better**: at 3% and
  h=10, trendline +0.965% against horizontal +1.437% (t = **−7.18**, the trendline winning on 17
  of 92 symbols). Consistent in 9 of 9 grid cells on 45,117 trendline events. **Slope does not
  fail to help; it subtracts.** Trendlines break nearly **twice as often** as the horizontals
  through their own anchors, suggesting the mechanism — a horizontal sits at a *remembered price*,
  a sloping line at an *extrapolation* that drifts from anywhere anyone transacted — which squares
  with EM-2's finding that **touches** carry the information. Logged as a hypothesis, not tested
  on the data that suggested it. Phase B (Three-Fan Principle, return line/channel, authority
  scoring, frontend) **not built**; the engine ships as apparatus with 46 tests, consumed by
  nothing.
- **Mandatory benchmark (C4):** the fan rule as a bottom-caller against a lag-returns benchmark
  and a random-walk null-FPR; trendline breaks against the shipped n-day breakout signal.
- **Effort:** M–L — the largest candidate here, and the only one that needs frontend drawing work.
- **Risk:** trendline drawing is notoriously subjective; E&M themselves prescribe *"draw every
  line the action permits, lightly; erase the useless"*. A deterministic rule set is required or
  the determinism harness (II.5.4) will fail.

### EM-6 — Dow-Theory multi-index confirmation gate

- **E&M:** Ch 3 tenets 2, 3, 8 and 11; Ch 4; Bassetti's Ch 5.1 and 15.1.
- **The book's requirement:** the primary trend is read from successively higher tops *and*
  bottoms (or lower ones), **confirmed by a second average** — *"no valid trend-change signal from
  one average alone"*, though they need not confirm on the same day. **Closing prices only**; any
  penetration, however small, counts. Bassetti's 9th-edition revision is the directly applicable
  part: thirty stocks can no longer represent an economy, so he reads the broad trend from the
  **Industrials + S&P 500 + NASDAQ together**, requires "harmonic convergence" among the three,
  and treats **disagreement among them as itself a signal to hedge**.
- **Now:** index data exists (`stock-data-service` serves VNINDEX / VN30 / HNX,
  `routes.py:460`) and is used for benchmark-relative scoring in
  `news-service/app/services/call_scorer.py:141` — but **no market-level trend context reaches any
  signal**. The confirmation layer (`confirmation/layer.py`) tests penetration, time delay and
  oscillator position; all three are per-ticker.
- **Where it lands:** a market-context provider feeding `confirmation/layer.py` as a penalty or
  veto, and the regime classifier as a prior.
- **Mandatory benchmark (C4):** signals with the gate versus without, on the same universe — does
  requiring index confirmation improve hit rate enough to pay for the signals it suppresses?
- **Effort:** M.
- **Risk:** the VN analogue of "Industrials vs Transports" is not obvious. VNINDEX and VN30 share
  most of their weight, so they may confirm trivially; HNX / UPCOM or a breadth measure (EM-4) may
  be the real second witness. That question belongs in the Phase-1 SRS, not here.

### EM-7 — Pullback / throwback entry at a broken boundary

- **E&M:** Ch 6 (the pullback to a broken neckline is *"the short-seller's second chance and his
  stop-placement reference"*), Ch 13 (pattern resistance — a broken neckline reverses role and
  stops the pullback; no 10 %-away rule needed, a conclusive breakout suffices), Ch 14 (the
  throwback to a trendline is *"more frequent and more exact"* than pattern pullbacks — *"for
  reasons the authors admit no one knows"* — while return lines do **not** act as support after an
  upside break).
- **Now:** `midtrend.py` has PCT_RETRACEMENT (33/50/67 % of the swing) and LONG_MA_REACTION, but
  nothing anchored to a **broken pattern boundary or broken trendline**. A breakout that is missed
  is missed; there is no second-chance entry, and `failed_signal.py` handles the opposite case
  (the breakout that fails).
- **Where it lands:** a new detector in `decision-helper/app/services/signal/trend/`, reading the
  boundary from ~~the pattern evidence that detectors already emit (`neckline`,
  `measured_move_target`)~~ — **corrected at Phase 1: from a broken S/R level instead.**
  Pattern evidence cannot reach the backtest (no per-bar HTTP), which is the dead-path trap
  EM-8's `M3` found in `MEASURED_MOVE`; and Ch 13 says *"pattern resistance — the mechanism
  explains the patterns"*, so the level is the cause and the pattern a label on it.
- **CLOSED 2026-10-22 — `docs/em7_throwback.md`.** Gate 1 **PASS**: both of E&M's claims hold,
  the pullback is +10.0pp more frequent than a distance-matched null (t = +22.67) and stops
  0.23 ATR more exactly (t = −8.29), 9/9 grid cells. Gate 2 **FAIL**: −0.375pp per
  opportunity against simply taking the break (t = −2.86, 30/92 symbols, sign p = 0.001),
  despite a **2.81% better entry price** on 82% of opportunities. The mechanism is
  **adverse selection** — the BREAK return on declined opportunities exceeds filled ones by
  **+14.17pp** (t = +19.09), so the 17.7% that never come back are the ones that ran.
  *The second chance is offered precisely when the first was not worth taking.* Detector
  ships `OFF`. **E&M's 40% rule is untested, not refuted**, and the **trendline** throwback —
  the half E&M rate highest — was never in scope and needs EM-5.
- **Mandatory benchmark (C4):** entry quality versus taking the breakout itself — better average
  entry price must not be paid for with a materially lower fill rate.
- **Effort:** S. Depends on nothing; benefits from EM-5 if trendline throwbacks are included.

### EM-8 — Objective-completion calibration and the "something to reverse" cap

- **E&M:** Ch 32, and the collected measuring rules (master list items 117–129).
- **The book's requirement:** every pattern carries a **minimum** objective — H&S: head-to-neckline
  projected from the break; rectangle: its height; flag/pennant: *"the Flag flies at half mast"*;
  runaway gap: the halfway point; diamond: greatest width; double top: peak-to-valley below the
  valley. Rounding turns and H&S consolidations have **no usable formula** and must not be given
  one. And the qualification the code lacks: *"a Reversal Pattern has to have something to
  reverse"* — take the **smaller** of the measured objective and the extent of the preceding move.
- **Now:** `target_module.py` consumes `measured_move_target` when a detector supplies one, but
  only some detectors do, the `min(measured, preceding move)` cap is absent, and nothing records
  whether objectives were *actually reached* on VN tickers.
- **Where it lands:** the cap in `target_module.py`; the calibration as a report reusing
  `news-service/app/services/call_scorer.py`'s forward-return machinery at fixed session horizons.
- **Mandatory benchmark (C4):** the calibration *is* the benchmark — it answers "on VN30, what
  fraction of H&S objectives were reached within N sessions, versus a random-entry null?" That
  number then either justifies or retires the measured-move target path.
- **Effort:** S. Highest information-per-hour of anything in this register, because it measures
  machinery that is already shipped and in use.

### EM-9 — Re-calibrate the breakout penetration filter

- **E&M:** Ch 6 (the 3 % neckline rule), Ch 14 (three tests of valid penetration), master list
  item 128: **3 % of price for a stock, 2 % for the averages**.
- **Now:** `confirmation/layer.py:40` sets `MIN_PENETRATION` to **0.3 %–0.5 %** by signal kind —
  roughly an order of magnitude looser than the book's filter. Both numbers are defensible (E&M
  charted daily bars by hand on 1950s NYSE issues; this is a VN daily close series), but the
  divergence is undocumented and unmeasured.
- **Where it lands:** `decision-helper/app/services/confirmation/layer.py` — a constant, plus a
  sweep.
- **Mandatory benchmark (C4):** a penetration-threshold sweep on VN data, reporting hit rate and
  signal count at each level, so the chosen filter is an empirical result rather than an
  inherited default.
- **Effort:** S (a sweep and a documented decision, possibly no behaviour change).
- **Note:** cheap enough to fold into whichever candidate is chosen rather than run alone.

---

## Summary

| ID | Candidate | E&M Ch | Lands in | Benchmark | Effort |
|---|---|---|---|---|---|
| EM-1 ★ | Volume validation on existing detectors | 6, 7, 11, 12, 28 | `ai-insights/.../patterns/` | null-FPR ↓ with recall held | S–M |
| EM-2 ★ | Volume-weighted S/R, role reversal, attack count | 13, 30 | `analysis-service` `_find_sr_levels` | forward hit-rate vs touch-count levels | M |
| EM-3 | Basing-point stops (3-days-away + 3 % new high) | 28, 28.1 | `decision-helper/.../risk/stop_module.py` | A/B vs ATR trail in the backtest harness | S–M |
| EM-4 | Magee Evaluative Index exposure governor | 38, 42 | `decision-helper` regime × universe | vs constant exposure | M |
| EM-5 | Trendline engine + Three-Fan Principle | 14, 15, 29 | new module + chart overlay | lag-returns + null-FPR | M–L |
| EM-6 | Dow multi-index confirmation gate | 3, 5.1, 15.1 | `confirmation/layer.py` | gate on vs off | M |
| EM-7 | Pullback / throwback entry | 6, 13, 14 | `signal/trend/` | vs taking the breakout | S — **CLOSED, negative** |
| EM-8 | Objective-completion calibration + reversal cap | 32 | `target_module.py` + report | the calibration itself | S |
| EM-9 | Re-calibrate the 3 % penetration filter | 6, 14 | `confirmation/layer.py` | threshold sweep | S |

### Recommendation for the Phase-1 design session

**EM-1 + EM-2 together**, as one piece of work: "make the shipped detectors and levels obey E&M's
evidence rules." They share a cause (volume is on hand and ignored), they modify existing modules
rather than adding surface area, EM-1 has an unusually clean pass/fail via the null-FPR harness
that already exists, and EM-2 improves four shipped consumers from one change.

**Alternative, if a small self-contained result is preferred:** **EM-3** alone — a mechanical stop
rule that the existing backtest harness can A/B against the current ATR trail, producing one
comparable number per run.

**EM-8 or EM-9** can ride along with either choice; both are measurement tasks on shipped code.

---

## Deliberately excluded

Methods from the book that were considered and left out, with the reason, so they are not
re-proposed:

- **Dow Theory's twelve tenets as a trading system**, the bull/bear three-phase models — narrative
  judgment, not mechanisable without exactly the hindsight C1 forbids.
- **Point-and-figure, candlesticks** — named in Ch 2 as separate schools and not taught in the book.
- **Normal Range-for-Price, Sensitivity Index, Composite Leverage** (Ch 22, 24, 41, App A/B) —
  Magee's hand-computed proxies for volatility and beta. ATR and the correlation engine already
  cover the same ground with better estimators; only the *"negative composite leverage"* idea
  (counter-trend positions genuinely subtracting portfolio risk, App B) is not covered, and it is
  subsumed by EM-4's long/short extension.
- **The Turtle system** (App E) — its entries (Donchian), its stop unit (ATR/"N") and its sizing
  are already implemented; what remains is the pyramiding/position-limit table, largely covered by
  `pyramiding.py`.
- **TEKNIPLAT chart paper, staggered chart dating, the fixed daily charting routine** (Ch 19,
  App B) — artifacts of hand charting.
- **Options and futures tactics** (Ch 17.2, 20.1, 25, 27's implied-volatility stop) — out of scope
  for a VN cash-equity platform; revisit only if derivatives data arrives.
- **MPT, VAR, Sharpe** (Ch 42, 17.2) — the book itself judges MPT *"not very"* important for the
  general investor and deflates VAR via Mandelbrot; the risk dashboard's stop-based worst case is
  closer to E&M's own thinking.

---

*Phase 0 artifact — candidate register only. Next: pick one or two, then Phase 1 writes
`docs/SRS_edwards_magee.md` with real `FR-EM-*` requirement IDs.*

---

## The register is closed — 2026-10-23

All nine candidates have been measured to a conclusion.

| | outcome |
|---|---|
| **EM-1** volume validation | **shipped** |
| EM-9 penetration filter | recommended unchanged |
| EM-2 volume-weighted S/R | negative — levels real, no elaboration beat counting touches |
| EM-3 basing-point stops | real but tail-driven; default stayed `ATR` |
| EM-4 Magee Evaluative Index | measure ships; headline overturned by more data (`#87`) |
| EM-6 Dow multi-index gate | negative — confirmation *removed* what the raw regime had |
| EM-7 throwback entry | both claims confirmed, **tactic refuted** (adverse selection) |
| EM-8 measuring implications | two bug fixes, no feature; `MEASURED_MOVE` found dead |
| **EM-5** trendline engine | negative — **slope is worse than no slope** |

**One of nine shipped a feature**, and that is not the whole return.

EM-2, EM-7 and EM-5 agree on something worth stating as a finding in its own
right: **the structure E&M describe is real on this market, and almost nothing
built on top of it pays.** Levels beat a matched-distance null; no elaboration
of them beat counting touches. The throwback to a level is real and more exact
than chance; waiting for it loses money to adverse selection. A sloping level
is *worse* than the level.

And the measurement found defects the features never would have: `#92`,
`#93`, `#94`, `#80`, `#82`, `#70`, `#52`, `MEASURED_MOVE` as dead code, and —
while chasing a dashboard of N/A — `#95`. **Measuring the book's claims was
worth more for the bugs it exposed than for the claims it confirmed.**

Open and pre-registered, neither a feature: `#86` (EM-3's long/short
hypothesis, to be tested on evidence it did not come from) and `#90` (EM-4's
history starting four years late).
