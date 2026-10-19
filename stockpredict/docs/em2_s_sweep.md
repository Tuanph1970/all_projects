# EM-2 / W1 — threshold sweep (`FR-EM-S10`)

**Date:** 2026-10-19
**Harness:** `analysis-service/tests/sr_sweep.py` (grid), `tests/sr_hitrate_harness.py` (`H-S1`)
**Sample:** 32 real VN symbols. Grid at step 10; the stacked-best configuration re-confirmed at step 5.
**Raw results:** `/tmp/em2_sweep.json` (regenerate with `PYTHONPATH=. python3 tests/sr_sweep.py <out.json>`)

---

## Why this sweep existed

`FR-EM-S10` and `CLAUDE.md` both require it: E&M's figures are 1940s–60s NYSE
rules, so every number in EM-2 is a default pending measurement. But `S7` gave
it a second job. Having found that **no EM-2 arm beats the shipped touch-count
model significantly**, the obvious objection was that a badly chosen threshold
might be understating EM-2 across the board. This sweep is that objection,
tested.

**Answer: no. The verdict stands.** Details below, then the one real defect the
sweep found.

---

## The trap, and why these numbers can be believed

The plan names it twice because the workstream has paid for it twice (EM-1
`S2`'s `confirm_rvol`, Backlog `#78`'s `MAX_PATTERN_AGE_BARS`): **a parameter
read as a default argument is bound at definition time**, so patching the
module constant does nothing, the sweep returns perfectly flat, and flat reads
as "this parameter does not matter" rather than "the harness never varied it".

In `sr_volume` the situation was *mixed*, which is worse than uniform:
`MAX_CONGESTION_BARS` is read in a function body (patchable), every other
threshold is a bound default on a function `_find_sr_levels` calls without
passing it (not patchable). A naive sweep would have shown one parameter
responding and the rest flat.

So `sr_sweep.override()` rebinds the *functions* in the namespace
`_find_sr_levels` actually calls, and `tests/test_sr_sweep_mechanism.py`
asserts, parameter by parameter and in seconds, both that the trap is real and
that the override defeats it. **All seven swept parameters vary.**

One further wrinkle, found while reading the first partial results: the
flatness check has to ask about the arm each parameter *feeds*.
`BREAK_ATR_MULTIPLE` moves `em2_role` and leaves `em2_adjusted` bit-identical
— correct behaviour — and the sweep's own first run duly flagged it
`FLAT - SUSPECT`. `ARM_OF_EFFECT` fixes that, and a test keeps the map
complete. A false flat alarm would have discredited the real ones.

---

## Results

Each parameter swept one-at-a-time, all others at their defaults. `z` is a
two-proportion test against `touch_count_matched`, the same-selectivity
control. **Defaults in bold.**

### Volume path — `em2_volume`

| `DEFAULT_NEIGHBOURHOOD` | rate | n | z vs matched |
|---|---|---|---|
| 1 | **no arm at all** | 0 | — |
| **3** | 54.65 % | 6,218 | −0.72 |
| 5 | 54.02 % | 6,212 | −1.43 |
| 10 | **55.24 %** | 6,142 | −0.06 |

| `DEFAULT_BASELINE_WINDOW` | rate | n | z vs matched |
|---|---|---|---|
| 50 | 54.10 % | 6,244 | −1.34 |
| **100** | **54.65 %** | 6,218 | −0.72 |
| 200 | 54.39 % | 6,268 | −1.02 |

### Penetration — `em2_role`

| `BREAK_ATR_MULTIPLE` | rate | n | z vs matched |
|---|---|---|---|
| 0.25 | 55.38 % | 10,851 | +0.11 |
| **0.5** | 55.62 % | 10,605 | +0.42 |
| 1.0 | 55.79 % | 10,128 | +0.63 |
| 2.0 | **55.83 %** | 9,438 | +0.67 |

The only parameter in the sweep with a **monotone gradient**: a stricter
penetration test gives a better role-coherence arm, consistently. Worth
noting that E&M's own filter was 3 % of price, which for a typical VN name is
nearer 2 ATR than 0.5.

### Age and distance — `em2_adjusted`

| `AGE_HALFLIFE_BARS` | rate | z | | `AGE_DECAY_FLOOR` | rate | z |
|---|---|---|---|---|---|---|
| 40 | 55.21 % | −0.09 | | 0.1 | 55.40 % | +0.13 |
| **120** | **55.41 %** | +0.13 | | **0.4** | **55.41 %** | +0.13 |
| 250 | 55.09 % | −0.22 | | 0.8 | 55.09 % | −0.22 |

| `DISTANCE_AWAY_PCT` | rate | z | | `DISTANCE_SUPPRESSION` | rate | z |
|---|---|---|---|---|---|---|
| 5 | 55.40 % | +0.12 | | 0.2 | **55.46 %** | +0.19 |
| **10** | **55.41 %** | +0.13 | | **0.5** | 55.41 % | +0.13 |
| 20 | 55.39 % | +0.11 | | 0.9 | 55.38 % | +0.10 |

All four are **effectively inert**: every setting lands inside 0.4 pp, which is
under one standard error. For age that is the limitation `S7` already
recorded — E&M's claim is about *years* and a 250-bar window spans about one,
so there is barely any age range to decay over. For distance it is a result in
its own right: **E&M's 10 % is as good as anything, and the effect is tiny.**

### Excluded, with reasons

| threshold | why it is not in the grid |
|---|---|
| `MAX_CONGESTION_BARS` | A **misuse guard, not a tuning knob**, and structurally inert. `S1` added it so a *cluster-wide* call fails loudly; `S4` complies by calling the primitives once per touch, so every real span is at most `DEFAULT_NEIGHBOURHOOD + 1` bars (4 at the default) and no setting from 15 upward ever bites. Verified still functional — a 41-bar span with `MAX=15` is refused — by a test, so it cannot quietly stop guarding. |
| `ATTACK_PROXIMITY_ATR` | Nothing consumes `attacks`. `S6` measured E&M's third-attack rule, found 42.3 % against a predicted >50 %, and the pre-registered consequence was that the weighting does not ship. The threshold moves the reported `attacks` field and can move nothing else. A test asserts it still moves *that*, so the field is unused rather than broken. |

Both are listed in `INERT_FOR_HS1` with their reasoning, and a test requires
every threshold to be either swept or documented as inert — so a later
addition cannot be silently forgotten.

---

## The decisive run: stacked best, full sample

Every parameter set to its point-estimate best simultaneously
(`DEFAULT_NEIGHBOURHOOD=10`, `BREAK_ATR_MULTIPLE=2.0`,
`DISTANCE_SUPPRESSION=0.2`, the rest already optimal), at 32 symbols / step 5:

| arm | rate | vs shipped | vs matched | vs null |
|---|---|---|---|---|
| `random_null` | 54.36 % | — | — | — |
| `touch_count` (shipped) | 55.46 % | — | — | — |
| `touch_count_matched` | 55.74 % | — | — | — |
| `em2_volume` | 55.80 % | z = +0.61 | z = +0.10 | z = +2.59 ✓ |
| `em2_role` | 55.84 % | z = +0.77 | z = +0.18 | z = +3.03 ✓ |
| `em2_adjusted` | **55.89 %** | z = +0.76 | z = +0.24 | z = +2.72 ✓ |

**The tuning genuinely helps EM-2 internally.** `em2_volume` rises from
54.90 % at the defaults to 55.80 % — +0.90 pp — so the default neighbourhood
*was* understating the volume arm, which is exactly the risk this sweep
existed to find.

**And it changes nothing about the conclusion.** Against the same-selectivity
control the best arm is +0.24 pp at z = +0.24. Every arm still clears the
random null significantly and none comes close to clearing the incumbent. The
highest `z` against `touch_count` anywhere in the entire sweep — 24 grid runs
plus the stacked run — is **+0.97**.

---

## Decisions

### Every default is retained

No change is justified. `CLAUDE.md`'s `C4` admits an improvement only on
out-of-sample significance, and the best point estimate in the sweep is under
1 σ. Adopting the point-estimate-best settings would be tuning to noise, which
is the behaviour this workstream has spent six tasks avoiding.

Five of the seven defaults are already the point-estimate best
(`DEFAULT_BASELINE_WINDOW=100`, `AGE_HALFLIFE_BARS=120`, `AGE_DECAY_FLOOR=0.4`,
`DISTANCE_AWAY_PCT=10.0`, and `DISTANCE_SUPPRESSION=0.5` within 0.05 pp of it),
which is the useful half of this answer: **the thresholds were not badly
chosen, and EM-2's parity with touch count is not a tuning artifact.**

### Two directional hints, recorded not acted on

* `DEFAULT_NEIGHBOURHOOD` 3 → 10 is worth +0.90 pp on the volume arm (≈1.5 σ),
  and 10 is independently the more faithful reading of a "congestion area" —
  11 bars is about two weeks, while the default's 4 bars is thin basis for the
  word. Two reasons pointing the same way. A future session with more power
  could justify it; the sweep alone cannot.
* `BREAK_ATR_MULTIPLE` has the sweep's only monotone gradient, favouring a
  *stricter* test. If any EM-2 measure is ever revisited, this is the one with
  a real signal behind it.

### One defect found and fixed

`DEFAULT_NEIGHBOURHOOD = 1` **silently disables the entire volume path.** A
1-bar neighbourhood yields a 2-bar span, which falls below
`MIN_CONGESTION_BARS = 3`, so `congestion_span` returns `None` for every
touch — and therefore `volume_strength`, `price_cog` and `adjusted_strength`
are all `None` for every level, with no error anywhere. The EM-2 arms simply
vanish from the study.

That is a footgun rather than a tuning result, so it is now guarded: the module
validates at import that its own neighbourhood default can produce a legal
span, and a test pins the relationship. Found only because the sweep's
small-sample flag marked the row.

---

## Standing of EM-2 after W1

`W1` was the last thing that could have overturned `S7`. It did not, so the
pre-registered conclusion is now final:

* E&M's Ch 13 levels are **real** — every EM-2 arm, at every threshold
  setting, beats a matched-distance random null significantly, and so does the
  shipped touch-count model (+1.10 pp, z = +2.35).
* Three of E&M's criteria reproduce **directionally** (role coherence, age,
  distance) and one quantitative claim is **refuted** (the third attack, at
  z = −26.4).
* **No EM-2 measure beats counting touches**, at any threshold, at full
  sample, stacked.

So `S9`'s consumer switch does not ship. Three live consumers read `strength`;
moving them onto a parity measure would spend behaviour-change risk for no
measured return. The new fields stay on the payload as evidence and as the
basis for any future candidate.

`W2` writes this up for the user guide. `S8` (round figures) was always gated
and is now moot — it would add levels carrying no volume strength to a ranking
nothing consumes. `D1`'s before/after has nothing to compare.

### What would change the answer

Stated so a future session knows where to look rather than re-running this:

1. **Multi-year windows.** E&M's age claim is about one-to-two versus
   four-to-five years, and a 250-bar window spans one. The age result here is a
   weak version of their effect, not a test of it.
2. **True volume-at-price.** `FR-EM-S2`'s centre of gravity is a
   volume-weighted *close* because daily bars carry no intraday distribution
   (`NFR-S2`). Intraday data would test what E&M actually described.
3. **A stricter penetration test**, per the gradient above, measured with more
   power than 24 runs at step 10 can provide.
