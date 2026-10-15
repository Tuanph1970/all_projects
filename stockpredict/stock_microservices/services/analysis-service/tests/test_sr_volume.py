"""EM-2 / S1 — level volume primitives.

`FR-EM-S1` groundwork, `FR-EM-S2`'s span question, and `EC-S1`–`EC-S3`. These
tests are written before `app/services/sr_volume.py` exists.

Why these primitives, and why here
----------------------------------
`_find_sr_levels` scores a level by `len(cluster)` — a touch count. Edwards &
Magee spend Ch 13 arguing that is the wrong measure: a level's power is the
**volume that changed hands there**, so a level touched twice on heavy trade
outranks one touched five times on thin trade. S1 builds the measurement; no
detector or level reads it yet (that is `S4`).

Deliberately mirroring EM-1
---------------------------
`ai-insights/app/services/patterns/volume.py` already solved the
relative-volume problem — a causal trailing median baseline, `MIN_BASELINE_BARS`
below which there is no usable baseline, and `_usable` treating NULL as missing
while keeping zero as data. That module lives in a different service and cannot
be imported, so this one mirrors its **shape, edge cases and naming on
purpose**. Divergences are noted where they exist rather than left for a reader
to discover.

Causality (C1) is binding
-------------------------
A level's volume is measured as of **its own formation** — the span never
extends past the level's last pivot. Reading later bars would score a level with
hindsight it did not have, and `H-S4` below appends future bars and asserts no
past reading moves, so a later "vectorise the whole column" refactor fails
loudly rather than leaking quietly.
"""
from __future__ import annotations



import pandas as pd
import pytest

from app.services.sr_volume import (
    DEFAULT_BASELINE_WINDOW,
    MAX_CONGESTION_BARS,
    MIN_BASELINE_BARS,
    MIN_CONGESTION_BARS,
    SpanMode,
    congestion_span,
    relative_level_volume,
    volume_weighted_price,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _frame(closes, volumes=None, hl_pad: float = 0.5) -> pd.DataFrame:
    closes = [float(c) for c in closes]
    if volumes is None:
        volumes = [1_000_000.0] * len(closes)
    return pd.DataFrame({
        "open": closes,
        "high": [c + hl_pad for c in closes],
        "low": [c - hl_pad for c in closes],
        "close": closes,
        "volume": list(volumes),
    })


def _flat(n: int, price: float = 100.0, volume: float = 1_000_000.0) -> pd.DataFrame:
    return _frame([price] * n, [volume] * n)


# ---------------------------------------------------------------------------
# congestion_span — FR-EM-S2's open question 2
# ---------------------------------------------------------------------------

class TestCongestionSpan:
    """Two candidate definitions, both implemented so `H-S1` can pick between
    them at `S4` rather than the choice being guessed here (open question 2)."""

    def test_neighbourhood_mode_is_the_pivots_plus_a_window(self):
        df = _flat(200)
        span = congestion_span(df, [100, 110], mode=SpanMode.NEIGHBOURHOOD, window=3)
        assert span == (97, 110)

    def test_contiguous_mode_follows_the_run_that_stayed_in_the_cluster(self):
        """It walks BACK through the plateau, and stops forward at the pivot.

        Price sits at ~100 from bar 90 to 110; the pivots are 95 and 105. The
        span is (90, 105), not (90, 110), and the asymmetry is the C1 rule the
        plan sets: *read only bars at or before the level's own last pivot*.

        Bars 106-110 really are part of the same congestion in hindsight. But
        including them would make a level's strength depend on bars that had
        not happened when the level formed, so the same level would score
        differently depending on when it was asked about. Backwards is history;
        forwards is hindsight.
        """
        closes = [80.0] * 90 + [100.0] * 21 + [130.0] * 89
        df = _frame(closes)
        start, end = congestion_span(df, [95, 105], mode=SpanMode.CONTIGUOUS,
                                     level_price=100.0, tolerance_pct=2.0)
        assert start == 90          # walked back to where the plateau begins
        assert end == 105           # stopped at the last pivot, not bar 110

    def test_the_span_never_extends_past_the_last_pivot(self):
        """C1. A level is scored as of its own formation, not with hindsight."""
        df = _flat(300)
        # Pivots close enough together to BE a congestion — [100, 150] would
        # now be refused by MAX_CONGESTION_BARS, which is a different rule.
        for mode in (SpanMode.NEIGHBOURHOOD, SpanMode.CONTIGUOUS):
            span = congestion_span(df, [100, 110], mode=mode,
                                   level_price=100.0, window=5)
            assert span is not None
            assert span[1] <= 110, f"{mode} read past the last pivot"

    def test_span_is_clipped_to_the_frame(self):
        """A pivot near bar 0 must not produce a negative start index."""
        df = _flat(20)
        span = congestion_span(df, [4], mode=SpanMode.NEIGHBOURHOOD, window=10)
        assert span == (0, 4)

    def test_a_pivot_too_close_to_the_start_yields_no_span(self):
        """`EC-S3` again: clipping cannot manufacture enough bars. Pivot 1 with
        any window gives at most bars 0-1, which is below MIN_CONGESTION_BARS."""
        assert congestion_span(_flat(20), [1], mode=SpanMode.NEIGHBOURHOOD,
                               window=10) is None

    def test_no_pivots_is_no_span(self):
        assert congestion_span(_flat(50), [], mode=SpanMode.NEIGHBOURHOOD) is None

    def test_a_long_sideways_run_is_truncated_not_refused(self):
        """The distinction that matters.

        A scattered pivot spread means the caller passed a cluster — refused.
        But a long contiguous run is a different thing: a wide sideways area is
        a STRONG level in E&M's terms (Ch 13), so refusing to measure it would
        discard the information. The walk is bounded instead.
        """
        df = _flat(300)                     # flat forever: the run never ends
        span = congestion_span(df, [100, 110], mode=SpanMode.CONTIGUOUS,
                               level_price=100.0)
        assert span is not None, "a long congestion must still be measurable"
        start, end = span
        assert end == 110                              # still clipped at the pivot
        assert (end - start + 1) <= MAX_CONGESTION_BARS  # and bounded

    def test_a_scattered_cluster_is_refused_not_averaged(self):
        """The measured answer to SRS open question 2.

        `_find_sr_levels` clusters every visit to a price across the whole
        window, so a cluster's touches are scattered — on real data FPT's
        strongest level spanned bars 114-220 and TCB's spanned 21-243, 226 of
        250. "The congestion is most of the year" is not a congestion, and the
        strength that falls out of it carries no information: those levels gave
        relative-volume readings of only 0.61x-1.18x, against 0.48x-2.44x when
        measured per touch.

        So the primitive refuses. `S4` must call it once per touch and
        aggregate, and a cluster-wide call fails loudly instead of returning a
        meaningless number.
        """
        df = _flat(300)
        scattered = [20, 120, 243]          # a real cluster's touch spread
        assert congestion_span(df, scattered, mode=SpanMode.NEIGHBOURHOOD) is None
        assert congestion_span(df, scattered, mode=SpanMode.CONTIGUOUS,
                               level_price=100.0) is None
        # Each touch on its own is a perfectly good congestion.
        for bar in scattered:
            assert congestion_span(df, [bar], mode=SpanMode.NEIGHBOURHOOD) is not None

    def test_the_congestion_bounds_bracket_a_plausible_area(self):
        """A congestion is weeks, not a year (Ch 13). Swept at W1."""
        assert MIN_CONGESTION_BARS < MAX_CONGESTION_BARS
        assert MAX_CONGESTION_BARS <= 60

    def test_a_span_shorter_than_the_minimum_is_rejected(self):
        """`EC-S3`: below a stated minimum there is nothing to average over."""
        df = _flat(50)
        span = congestion_span(df, [10], mode=SpanMode.NEIGHBOURHOOD, window=0)
        assert span is None or (span[1] - span[0] + 1) >= MIN_CONGESTION_BARS


# ---------------------------------------------------------------------------
# volume_weighted_price — FR-EM-S2, and NFR-S2's honesty requirement
# ---------------------------------------------------------------------------

class TestVolumeWeightedPrice:
    def test_it_is_the_volume_weighted_mean_of_closes(self):
        # Two bars: 100 on 1 share, 200 on 3 shares -> (100 + 600) / 4 = 175.
        df = _frame([100.0, 200.0], [1.0, 3.0])
        assert volume_weighted_price(df, 0, 1) == pytest.approx(175.0)

    def test_equal_volume_degenerates_to_the_arithmetic_mean(self):
        """The sanity check that it is a weighted mean and not something else:
        with flat volume it must agree with what `_find_sr_levels` does today."""
        df = _frame([100.0, 110.0, 120.0], [500.0] * 3)
        assert volume_weighted_price(df, 0, 2) == pytest.approx(110.0)

    def test_a_heavy_bar_pulls_the_level_towards_itself(self):
        """E&M's 'centre of gravity' — the whole point of the measure."""
        light = _frame([100.0, 110.0], [1_000.0, 1_000.0])
        heavy = _frame([100.0, 110.0], [1_000.0, 9_000.0])
        assert volume_weighted_price(heavy, 0, 1) > volume_weighted_price(light, 0, 1)

    def test_zero_total_volume_is_unknown_not_zero(self):
        """`EC-S1`: a dormant span has no centre of gravity. Returning 0.0
        would place the level at zero, which is worse than admitting ignorance."""
        assert volume_weighted_price(_frame([100.0, 110.0], [0.0, 0.0]), 0, 1) is None

    def test_null_volume_bars_are_skipped_not_imputed(self):
        """`EC-S1`: NULL is missing, so it drops out of BOTH sums — it is never
        treated as zero volume, which would silently reweight the average.

        Skipping the middle bar leaves (100x1 + 300x3) / (1+3) = 250. Imputing
        zero for it would give the same numerator over the same denominator, so
        the discriminating check is the one below: a bar imputed as zero-volume
        would still contribute its PRICE to a mean, and 250 proves it did not.
        """
        df = _frame([100.0, 200.0, 300.0], [1.0, None, 3.0])
        assert volume_weighted_price(df, 0, 2) == pytest.approx(250.0)
        # The 200 close is absent from the result entirely.
        assert volume_weighted_price(df, 0, 2) != pytest.approx(200.0)

    def test_an_empty_or_inverted_span_is_unknown(self):
        df = _flat(10)
        assert volume_weighted_price(df, 5, 4) is None
        assert volume_weighted_price(df, 50, 60) is None


# ---------------------------------------------------------------------------
# relative_level_volume — FR-EM-S1
# ---------------------------------------------------------------------------

class TestRelativeLevelVolume:
    """Strength relative to the symbol's own history, never an absolute share
    count — `FR-EM-S1`, mirroring `FR-EM-V1`'s reasoning that "high" means high
    for that stock in that period."""

    def test_a_flat_series_reads_as_one(self):
        df = _flat(200)
        lv = relative_level_volume(df, 150, 160)
        assert lv.known
        assert lv.value == pytest.approx(1.0)

    def test_heavy_congestion_reads_above_one(self):
        vols = [1_000_000.0] * 200
        for i in range(150, 161):
            vols[i] = 3_000_000.0
        lv = relative_level_volume(_frame([100.0] * 200, vols), 150, 160)
        assert lv.value == pytest.approx(3.0, rel=0.05)

    def test_quiet_congestion_reads_below_one(self):
        vols = [1_000_000.0] * 200
        for i in range(150, 161):
            vols[i] = 250_000.0
        lv = relative_level_volume(_frame([100.0] * 200, vols), 150, 160)
        assert lv.value == pytest.approx(0.25, rel=0.05)

    def test_the_baseline_is_a_median_not_a_mean(self):
        """Mirrors `FR-EM-V1`. One climax bar in the baseline window would
        inflate a mean and make every later level look quiet by comparison;
        the median does not move."""
        vols = [1_000_000.0] * 200
        vols[40] = 500_000_000.0            # one absurd vendor print
        lv = relative_level_volume(_frame([100.0] * 200, vols), 150, 160)
        assert lv.value == pytest.approx(1.0, rel=0.05)

    def test_too_little_history_is_unknown(self):
        """`EC-S3` / the `MIN_BASELINE_BARS` precedent."""
        lv = relative_level_volume(_flat(MIN_BASELINE_BARS + 2), 5, 8)
        assert not lv.known
        assert lv.reason

    def test_all_null_volume_is_volume_unavailable(self):
        """`EC-S1`: the caller must be able to fall back to the touch count,
        and must be told why — the reason string is the contract."""
        df = _frame([100.0] * 200, [None] * 200)
        lv = relative_level_volume(df, 150, 160)
        assert not lv.known
        assert lv.reason == "volume_unavailable"

    def test_a_dormant_span_is_flagged_thin_not_scored_zero(self):
        """`EC-S2`: zero is data — a halt or a genuinely dormant ticker — but
        it must not read as 'no interest at this level'."""
        vols = [1_000_000.0] * 200
        for i in range(150, 161):
            vols[i] = 0.0
        lv = relative_level_volume(_frame([100.0] * 200, vols), 150, 160)
        assert lv.value is None or lv.value == 0.0
        assert lv.thin_volume

    def test_a_thin_ticker_is_marked(self):
        """`EC-S2`. A lumpy, barely-traded symbol gets a marker so a consumer
        can say WHY there is no verdict rather than showing a bare blank."""
        vols = [0.0 if i % 3 else 1_000.0 for i in range(200)]
        lv = relative_level_volume(_frame([100.0] * 200, vols), 150, 160)
        assert lv.thin_volume


# ---------------------------------------------------------------------------
# H-S4 — causality
# ---------------------------------------------------------------------------

class TestHS4Causality:
    """C1, and the test that makes a future refactor fail loudly.

    Everything here reads only bars at or before the span's end. Appending
    later bars must not move a single reading — if someone replaces these
    helpers with a whole-column vectorised form that normalises against the
    full series, this is what catches it.
    """

    def test_appending_future_bars_changes_no_reading(self):
        base = _frame([100.0] * 200, [1_000_000.0] * 200)
        extended = _frame(
            [100.0] * 200 + [500.0] * 50,
            [1_000_000.0] * 200 + [900_000_000.0] * 50,
        )
        for start, end in ((150, 160), (120, 130), (60, 70)):
            assert (volume_weighted_price(base, start, end)
                    == volume_weighted_price(extended, start, end))
            a = relative_level_volume(base, start, end)
            b = relative_level_volume(extended, start, end)
            assert a == b, f"span ({start},{end}) moved when future bars were appended"

    def test_the_baseline_reads_only_bars_before_the_span(self):
        """A heavy bar INSIDE the span must not also inflate the baseline it is
        being compared against — that would mask the very thing being measured."""
        vols = [1_000_000.0] * 200
        for i in range(150, 161):
            vols[i] = 5_000_000.0
        lv = relative_level_volume(_frame([100.0] * 200, vols), 150, 160)
        assert lv.value == pytest.approx(5.0, rel=0.05)
        assert lv.baseline == pytest.approx(1_000_000.0, rel=0.05)

    def test_congestion_span_never_looks_forward(self):
        df = _flat(300)
        span = congestion_span(df, [100], mode=SpanMode.NEIGHBOURHOOD, window=5)
        assert span[1] <= 100


# ---------------------------------------------------------------------------
# H-S6 — determinism
# ---------------------------------------------------------------------------

class TestHS6Determinism:
    def test_repeated_calls_are_identical(self):
        df = _frame([100.0 + i % 7 for i in range(200)],
                    [1_000_000.0 + (i * 37) % 500_000 for i in range(200)])
        assert relative_level_volume(df, 150, 160) == relative_level_volume(df, 150, 160)
        assert volume_weighted_price(df, 150, 160) == volume_weighted_price(df, 150, 160)
        assert (congestion_span(df, [150], mode=SpanMode.NEIGHBOURHOOD)
                == congestion_span(df, [150], mode=SpanMode.NEIGHBOURHOOD))


# ---------------------------------------------------------------------------
# The vocabulary is mirrored from EM-1 on purpose
# ---------------------------------------------------------------------------

class TestMirrorsEM1Deliberately:
    """`S1`'s "reuse, do not reinvent" requirement, asserted rather than
    trusted to review. EM-1 settled these numbers with a measured sweep
    (docs/em1_s2_parameter_sweep.md); re-deriving different ones here would
    mean two vocabularies for one idea."""

    def test_the_baseline_window_matches_em1s_swept_value(self):
        assert DEFAULT_BASELINE_WINDOW == 100

    def test_the_minimum_baseline_matches_em1(self):
        assert MIN_BASELINE_BARS == 10

    def test_a_congestion_needs_fewer_bars_than_a_baseline(self):
        """A congestion is a handful of bars; a baseline is months. If these
        ever cross, something has been copied without thinking."""
        assert MIN_CONGESTION_BARS < MIN_BASELINE_BARS
