# Backlog #85 — does EM-3's edge concentrate in trending markets?

**Date:** 2026-10-20
**Study:** `decision-helper-service/tests/em3_regime_gate_study.py`
**Verdict:** **No. Both pre-registered conditions fail. No gate is built.**

---

## Why it was asked

`#84` confirmed the basing-point stop's advantage out of sample **on
magnitude** (+37.82 gross per trade, clustered t = +3.39 across 32 symbols)
but **not on consistency** (54 % of windows, sign test never significant). The
rule loses about as often as it wins; its wins are bigger. So the edge sits in
a tail, and the question became *where the magnitude comes from*.

E&M's own mechanism predicted an answer. A basing point is built from a
**reaction low in an advance** — the procedure presupposes a trend to base
within. In a range there is no advance to protect, so a wider stop should buy
nothing and cost patience. If that were right, the advantage would concentrate
in trend regimes.

## The criterion, fixed before the run

> Both, or there is nothing to gate on:
> 1. the advantage is significantly positive **within trend regimes**
>    (TREND_UP and TREND_DOWN pooled); and
> 2. that advantage is **larger in trend than in range**.

Conditioned at **trade** granularity rather than #84's 192 windows, using
`TradeRecord.entry_regime` — which the replay already computes on every bar
through `compute_regime`, causally, reading only bars up to the entry.

---

## Result

Gross P&L per trade, by regime at entry, 32 symbols:

| regime at entry | n (ATR) | ATR | n (BP) | BP | advantage | Welch t |
|---|---|---|---|---|---|---|
| TREND_UP | 566 | +25.52 | 415 | +118.20 | **+92.68** | +1.60 ns |
| TREND_DOWN | 416 | −97.78 | 320 | −105.10 | **−7.32** | −0.13 ns |
| RANGE | 363 | +28.50 | 205 | +94.35 | **+65.86** | +1.08 ns |

| criterion | | |
|---|---|---|
| 1. significantly positive in trend | +47.69, t = +1.17 | **FAIL** |
| 2. larger in trend than in range | trend +47.69 **vs** range +65.86 | **FAIL** |

**Criterion 2 is the informative one, and it does not depend on
significance**: the point estimate in RANGE (+65.86) is *higher* than in trend
(+47.69). The directional claim — that the edge lives in trends — is simply
not supported, whatever the power.

So **there is nothing to gate on.** `#84`'s unconditional result is the whole
story, and a regime-gated basing-point stop would not be a stronger proposal
than the plain one.

### A power caveat that cuts the other way

Splitting one sample three ways costs power. `#84`'s pooled, clustered
estimate was significant at t = +3.39; here every individual bucket is `ns`
because each holds a third of the trades. So "FAIL" on criterion 1 partly
reflects thinner buckets rather than a missing effect.

That caveat does **not** rescue the hypothesis. Criterion 2 compares two point
estimates and range wins. Power would have to be wrong in a very specific
direction to reverse that, and more data would have to move trend *above*
range rather than merely make both significant.

---

## What the decomposition does show, offered as a hypothesis and not a finding

The three buckets do not split trend-versus-range. They split something else:

* **TREND_UP: +92.68** — the largest advantage anywhere.
* **RANGE: +65.86** — comparable, and not distinguishable from it.
* **TREND_DOWN: −7.32** — the only negative bucket, and essentially zero.

TREND_DOWN entries are predominantly shorts. So the pattern looks less like
*trend versus range* and more like **long versus short**, or up-market versus
down-market.

**That is explicitly a post-hoc observation, and it is not tested here.** I
have just refuted one pre-registered hypothesis; generating a second from the
same data and testing it on the same data is how a finding gets manufactured.
It is logged as **Backlog #86** so it can be stated in advance and tested
against evidence it did not come from.

There is also a plausible mechanism, which is a reason to take it seriously
rather than a reason to believe it: E&M's procedure is written for an
*advance* — "a high is made, prices recede" — and Bassetti's worked example is
a bull market. The mirrored short-side version is a translation we made, not
a rule the book validates.

---

## Standing of EM-3 after four tasks

| | |
|---|---|
| built, in-sample A/B | gross/trade −16.51 → +22.80, t = +2.02 — clears its own criterion |
| `#84` walk-forward | magnitude **confirmed** OOS (clustered t = +3.39); consistency **not** (sign test ns) |
| `#84` filter sweep | sign robust across 3–12 %; significance fragile, and 6 % is the peak |
| `#85` regime gate | **refuted** — the edge is not concentrated in trends |

So EM-3 has a **real but tail-driven unconditional edge** that cannot be shown
consistent and cannot be sharpened by regime. `trailing_stop_mode` stays
`ATR`; the implementation and the measurements stay as evidence.

This is a reasonable place to stop on EM-3 unless #86's long/short hypothesis
is worth testing — which it may be, since a long-only basing-point stop would
be both a cleaner claim and closer to what the book actually argues.
