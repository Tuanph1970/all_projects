# Backlog #79 — do the pattern failed-signal verdicts predict anything?

**Answer: no. And one of them is significantly backwards.**

Backlog #73 made two pattern-failure detectors reachable; #78 stopped them
firing on every symbol. Neither established that they *work*. This does, and
the result is negative enough to change their behaviour.

Date: 2026-10-14. Evidence: 6,797 causal scans over 32 VN symbols.

## Method

The thing that makes this a benchmark rather than an anecdote is causality.

For each symbol and every 5th bar `t`, the frame `bars[t-249 .. t]` was sliced
**first** and the full ai-insights detector catalogue run on it — so each scan
sees only what was knowable on its own date. Never scan the whole series and
index into it; that is the `C1` violation EM-1's no-leakage test exists to
catch, and it would quietly inflate every number here.

Each scan then went through the live path — `adapt_ai_insights_patterns`
(recency guard and located-break rule from #78) and the two reachable
detectors. Forward return is close-to-close from `t` to `t+h`. The comparison
is against the **no-verdict baseline**: the same bars, same symbols, scans
where neither detector fired.

Significance is Welch's t (unequal variances, which these have).

## Result — overlapping samples, every 5th bar

| verdict | n | h | mean fwd | baseline | diff | t |
|---|---|---|---|---|---|---|
| DOUBLE_TOP_BREAK / SHORT | 1085 | 10 | +0.387% | +0.624% | −0.237 | −1.11 |
| DOUBLE_TOP_BREAK / SHORT | 1085 | 20 | +0.654% | +1.226% | −0.572 | −1.85 |
| DOUBLE_TOP_BREAK / LONG | 1071 | 10 | +0.603% | +0.624% | −0.021 | −0.09 |
| **HS_TARGET_FAILURE / SHORT** | 197 | 10 | **+1.935%** | +0.624% | **+1.311** | **+2.91** |
| HS_TARGET_FAILURE / LONG | 183 | 10 | −0.152% | +0.624% | −0.776 | −1.83 |

Sampling every 5 bars with 10- and 20-bar horizons means the windows overlap,
which inflates significance. So the whole thing was re-run on
**non-overlapping** samples — one observation per symbol per horizon length.

## Result — non-overlapping, which is the one to believe

**Horizon 10 bars** (baseline n=2234, mean +0.546%):

| verdict | n | symbols | mean | diff | t |
|---|---|---|---|---|---|
| DOUBLE_TOP_BREAK / LONG | 538 | 32 | +0.741% | +0.195 | +0.65 |
| DOUBLE_TOP_BREAK / SHORT | 537 | 32 | +0.297% | −0.250 | −0.81 |
| **HS_TARGET_FAILURE / SHORT** | 104 | 30 | **+1.961%** | **+1.415** | **+2.34** |
| HS_TARGET_FAILURE / LONG | 88 | 30 | −0.053% | −0.599 | −1.08 |

**Horizon 20 bars** (baseline n=1117, mean +0.933%): nothing reaches |t| > 1.96;
`HS_TARGET_FAILURE / SHORT` keeps its sign at +1.970, t = +1.62.

## Reading it honestly

**`DOUBLE_TOP_BREAK` is noise.** |t| < 1 in both directions once windows stop
overlapping. The weak-looking −1.85 in the overlapping run was the overlap. Its
severity of 0.60 was unearned.

**`HS_TARGET_FAILURE / SHORT` is backwards, and that is the finding.** It
implies SHORT, and the stock then **outperforms** the baseline by 1.4% over ten
bars — t = +2.34, spread across **30 of 32 symbols**, so not one ticker's
quirk. It is also the same sign and a larger effect in the overlapping run
(+1.31, t = +2.91) and at 20 bars (+1.97). A consistent wrong answer.

Mechanically this is unsurprising. The verdict means "an inverse H&S failed to
reach its target and price is below the neckline" — i.e. the stock has just
been beaten down. Mean reversion then does the rest. The detector is reading a
dip and calling it a short.

**`HS_TARGET_FAILURE / LONG` is noise** (t = −1.08), leaning the wrong way too.

Caveat stated plainly: eight tests were run here, so one |t| > 1.96 is expected
about 0.4 times by chance. A single 2.34 is therefore suggestive, not proof.
What raises it above a fluke is that the sign is consistent across both
sampling schemes and both horizons, and spread over 30 symbols.

## What changed as a result

`PATTERN_FAILURE_SEVERITY = 0.35`, below `OVERRIDE_THRESHOLD = 0.5`.

Both detectors sat at 0.60/0.65, so they cleared the threshold at which a
failed signal **overrides the confirmed signal's direction** — which is what
produced the REVERSE recommendations seen after #73. Nothing in this study
earns that authority, and one detector would have been actively flipping
positions the wrong way.

This is the same rule EM-1 holds its own rules to (`C4`): a method improves only
if it beats the benchmark out-of-sample with significance. Neither does. So
they keep firing and stay in `failed_results` as evidence, and they no longer
decide anything.

Live effect, same `bar_date=2026-10-06`:

| symbol | after #78 | after #79 |
|---|---|---|
| VHM | HS_TARGET_FAILURE · **REVERSE** | BEAR_TRAP · HOLD |
| TCB | DOUBLE_TOP_BREAK · **REVERSE** | None · HOLD |
| VNM | DOUBLE_TOP_BREAK · WAIT | FILLED_GAP · WAIT |

Both REVERSE recommendations are gone, and the S/R-based detectors — which were
never part of this study and keep their authority — report as before.

## What would make them useful

Not more calibration of the same rule. The signal is being swamped by mean
reversion after a drawdown, so the detector needs to distinguish "the pattern
failed" from "the stock is simply down":

* condition on the *breakout* having happened and then reversed, rather than on
  price merely sitting the wrong side of a neckline;
* normalise the forward return against the symbol's own recent drawdown, or
  benchmark against a dip-matched control rather than all bars;
* and run this study again, since a rule derived from this data needs
  out-of-sample confirmation before it gets its severity back.

Until then: a pattern-failure verdict is evidence that a recent formation did
not work out. It is not a reason to reverse a position.
