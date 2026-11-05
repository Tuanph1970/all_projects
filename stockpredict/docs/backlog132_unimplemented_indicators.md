# Backlog #132 — the thirteen indicators that are seeded but not implemented

**Status: hidden from the catalogue for the v0.9 release (owner decision, 2026-11-05). Not deleted.**

These thirteen entries exist in the `technical_indicators` table — seeded by
`prediction-service/app/main.py` `SEED_DATA_SQL` — and have **no branch** in
`_calculate_indicator` (`prediction-service/app/api/solution_routes.py`). They
are therefore advertised by the catalogue but cannot be computed.

They are listed here so the work is not rediscovered from scratch. This file is
the handoff; the enforcement is `UNAVAILABLE_INDICATORS` in
`app/api/solution_routes.py`.

## How they were found

Backlog #130. `_calculate_indicator` used to answer anything it could not
compute — an unknown code, or any exception from the `ta` library — with the
raw **close price** under a `value` key, plus a log line. A model then trained
on a column of closing prices labelled as the indicator the operator had
chosen, and nothing in the metrics, the payload or the UI said so.

Measured on 2026-11-05 against 880 bars of FPT: **14 of 54** catalogue
indicators resolved to the close price. One was a genuine bug — `AROON` passed
`close` where the library wanted `high` and `low`, so it raised on every call;
that is fixed. The other thirteen are these, and they had never been written.

The measurement also showed the substitution was **inflating reported
accuracy**, not merely mislabelling it: a duplicated close column sits near the
naive predictor on a price-level target, so it reads as a strong feature while
teaching the model nothing. With the seed fixed and only `AROON` changing, one
cell moved from rmse 2.336 to 2.683 — about 15% worse, and honest.

## What is hidden, and what each one is

All three affected groups are unimplemented **in their entirety**, which is why
hiding them removes three dropdowns rather than leaving gap-toothed ones.

### `support_resistance` (3)

| Name | What it is | Notes for implementing |
|---|---|---|
| `PIVOT` | Classic floor-trader pivots: P = (H+L+C)/3, with R1-R3 / S1-S3 derived from it. | Straightforward and self-contained. Emits ~7 columns per bar; decide whether all of them become features or only P. Usually computed from the **previous** period's bar, so mind the shift — using the current bar's own H/L/C is look-ahead. |
| `FIB_RET` | Fibonacci retracement levels (23.6 / 38.2 / 50 / 61.8 / 78.6%) between a swing high and swing low. | Needs a **swing definition** before it needs arithmetic — which high and which low. That choice is the whole indicator, and the project already has swing/pivot detection in `analysis-service` (`sr_volume.py`) and `ai-insights-service` pattern code worth reusing rather than reinventing. |
| `FIB_EXT` | The same levels projected beyond the swing (127.2 / 161.8 / 200 / 261.8%). | Same dependency as `FIB_RET`. |

### `price_transform` (5)

| Name | What it is | Notes for implementing |
|---|---|---|
| `TP` | Typical price, (H+L+C)/3. | Trivial, one column. |
| `MP` | Median price, (H+L)/2. | Trivial, one column. |
| `WC` | Weighted close, (H+L+2C)/4. | Trivial, one column. |
| `HEIKIN_ASHI` | Candles smoothed from the previous HA bar: HA-close = (O+H+L+C)/4, HA-open = mean of the previous HA open/close. | **Does not fit the current feature shape.** It re-bars the series — it produces a new OHLC per bar, not a value to append as a column. Either expose only `ha_close` as a feature, or treat it as a chart overlay rather than a covariate. |
| `RENKO` | Bricks of a fixed price size; a new brick only when price moves by the brick amount. | **Does not fit at all.** Renko discards the time axis: bars appear only when price moves enough, so there is no one-value-per-date mapping, and `_prepare_indicator_features` assumes exactly that. Needs a design decision before any code — probably "forward-fill the current brick level per date", which is a choice to make deliberately and document, not to improvise. |

### `bill_williams` (5)

| Name | What it is | Notes for implementing |
|---|---|---|
| `ALLIGATOR` | Three smoothed moving averages (13/8/5) displaced forward by 8/5/3 bars. | **The displacement is forward**, i.e. into the future relative to the bar it is plotted on. As a chart overlay that is fine; as a model feature it would be look-ahead and must not be fed with the displacement applied (CLAUDE.md C1). Implement undisplaced for features, displaced for display only, and say which is which. |
| `GATOR` | The absolute gaps between the Alligator lines. | Inherits `ALLIGATOR`'s displacement problem. |
| `AC` | Accelerator Oscillator: AO minus a 5-bar SMA of AO. | Easy — `AO` already exists and works, so this is a few lines on top of it. |
| `FRACTALS` | Bars whose high is the highest of five consecutive bars (and the mirror for lows). | Confirmation needs the **two bars after** the candidate, so a fractal is only known two bars later. Emit it on the bar where it becomes known, not on the bar it describes, or it is look-ahead. |
| `MFI_BW` | Bill Williams' Market Facilitation Index, (H-L)/volume. | Easy. Note the name collides with the existing, working `MFI` (Money Flow Index) — hence the `_BW` suffix. Keep them distinct. |

## Where the removal is enforced

| Place | Behaviour |
|---|---|
| `UNAVAILABLE_INDICATORS` in `app/api/solution_routes.py` | The single list. **Re-enabling one is deleting a name from this set.** |
| `GET /predict/indicators` | Filters them out, and drops a group left with nothing rather than returning it empty. |
| `GET /predict/indicators/type/{type}` | Filters them out. |
| `POST /solutions/{id}/indicators/set` | **422** naming them — refused at the write boundary, so a stale page or a direct API call is told while the operator is choosing rather than three minutes into a training run. |
| `_calculate_indicator` | Raises `IndicatorError` naming the indicator and the reason (#130). Never substitutes. |

The detail endpoint `GET /predict/indicators/{id}` is deliberately **not**
filtered: it is a lookup of a known id, and 404-ing it could break the display
of a legacy solution that still has one of these attached.

The table rows are **not deleted**. Ids stay stable, `solution_indicators` keeps
any legacy reference, and the catalogue metadata (description, default
parameters) is still there for whoever implements them.

## The test that keeps this honest

`test_the_unavailable_list_is_exactly_what_cannot_be_computed` computes every
catalogue indicator and asserts the set that raises is **exactly**
`UNAVAILABLE_INDICATORS`. So:

- implement one and forget to remove it from the list → the test fails, rather
  than the catalogue quietly hiding a working indicator;
- add a catalogue entry with no implementation and forget to list it → the test
  fails, rather than the GUI offering a control that breaks after training.

## Closing this properly

Two ways, and they are not exclusive:

1. **Implement them.** `TP`, `MP`, `WC`, `AC` and `MFI_BW` are each a few
   lines. `PIVOT` is self-contained. The Fibonacci pair needs a swing
   definition, and `HEIKIN_ASHI` / `RENKO` / `ALLIGATOR` / `GATOR` /
   `FRACTALS` each need a documented decision about shape or causality before
   any code — the table above says which.
2. **Stop seeding what will not be implemented.** If any of these are not
   wanted, removing them from `SEED_DATA_SQL` is the honest end state, and the
   test above then wants them out of `UNAVAILABLE_INDICATORS` too.

Whichever way: the thing not to do is restore a fallback that answers with a
different series than the one that was asked for.
