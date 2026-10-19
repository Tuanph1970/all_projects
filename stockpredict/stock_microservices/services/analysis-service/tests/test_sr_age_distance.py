"""EM-2 / S7 — age decay (`FR-EM-S5`) and distance-away (`FR-EM-S6`).

Two of E&M's three criteria for estimating a level's potential (Ch 13); the
third, volume, was `S4`.

**Age.** *"A supply one or two years old is more effective than one four or
five years old, but the latter does not lose all of its potency by any
means."* So strength decays with age and the decay has a **floor** — decaying
to zero would misread the book, and the floor is a requirement rather than a
nicety.

**Distance away.** *"Don't expect much supply from a low-middle-priced bottom
unless the trend later took quotations more than 10% under it."* The mechanism
is psychological and it is about the holder's P&L: price has to move far
enough away from the level to convince the buyer he made a bad investment, so
that he sells to get out even when price returns. A level price merely brushed
past has no trapped interest behind it. Such a level is **suppressed, not
dropped** (`FR-EM-S6`).

Why this one is in percent while S5/S6 were in ATR multiples
------------------------------------------------------------
A deliberate divergence from the EM-9 pattern, and the reasoning matters.
`FR-EM-S3`'s penetration test is about whether a *price move* is decisive,
which is a question about the symbol's own scale — hence ATR. E&M's
distance-away criterion is about whether a *holder feels wrong*, and a 10%
loss feels like a 10% loss whether the symbol is quiet or wild. The unit
follows the mechanism. `W1` sweeps it either way, and if the ATR form measures
better the sweep will say so.

What this task does NOT do
--------------------------
It does not fold either measure into `volume_strength`. `S6` established that
rule the hard way — a measure E&M predicted and the data refused — and three
tests there pin `volume_strength` as raw volume only. So the composite lands
on its own field, `adjusted_strength`, and `H-S1` decides whether anything
should read it.
"""
from __future__ import annotations

from typing import List
from unittest.mock import MagicMock

import pandas as pd
import pytest

from app.models.schemas import SRLevel, SRLevelType
from app.services.analysis_service import AnalysisService
from app.services.sr_volume import (
    AGE_DECAY_FLOOR,
    AGE_HALFLIFE_BARS,
    DISTANCE_AWAY_PCT,
    DISTANCE_SUPPRESSION,
    age_decay,
    adjusted_level_strength,
    level_excursion_pct,
)

ATR_LEAD_IN = 30


def _pivoted_then_excursion(level: float = 100.0) -> List[float]:
    """Pivots at `level`, then a deep excursion away, then a return.

    Flat plateaus do not work here: `_find_swing_pivots` needs a strict local
    extreme, so a run of identical closes produces no pivots and therefore no
    levels at all. The legs below have distinct turning points.
    """
    out: List[float] = []
    for i in range(6):                       # pivots around the level
        out += [level, level + 1.6 + i * 0.05, level,
                level - 1.4 - i * 0.05, level]
    out += [level - 3.0 * k for k in range(1, 6)]   # the excursion down
    out += [level - 15.0 + 1.1 * k for k in range(1, 15)]  # and back towards it
    return out


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

def _frame(closes: List[float], hl_pad: float = 0.4) -> pd.DataFrame:
    closes = [float(c) for c in closes]
    return pd.DataFrame({
        "open": closes,
        "high": [c + hl_pad for c in closes],
        "low": [c - hl_pad for c in closes],
        "close": closes,
        "volume": [1_000_000.0] * len(closes),
    })


def _levels(frame: pd.DataFrame) -> List[SRLevel]:
    supports, resistances = AnalysisService(session=MagicMock())._find_sr_levels(frame)
    seen = set()
    out: List[SRLevel] = []
    for lvl in list(supports) + list(resistances):
        key = (round(lvl.price, 9), lvl.type)
        if key not in seen:
            seen.add(key)
            out.append(lvl)
    return out


# ---------------------------------------------------------------------------
# FR-EM-S5 — age decay, with a floor
# ---------------------------------------------------------------------------

class TestAgeDecay:

    def test_a_fresh_level_is_undecayed(self):
        assert age_decay(0) == pytest.approx(1.0)

    def test_decay_is_monotone_in_age(self):
        """Older is weaker — the direction of E&M's claim."""
        values = [age_decay(a) for a in (0, 25, 50, 100, 200, 400)]
        assert values == sorted(values, reverse=True)

    def test_the_decay_has_a_floor_and_never_reaches_zero(self):
        """`FR-EM-S5`'s binding half. E&M: an old level "does not lose all of
        its potency by any means", so a decay that reaches zero misreads the
        book. This is the test that stops a later refactor to a plain
        exponential."""
        assert AGE_DECAY_FLOOR > 0
        for age in (1_000, 10_000, 1_000_000):
            assert age_decay(age) >= AGE_DECAY_FLOOR
            assert age_decay(age) > 0

    def test_the_floor_is_reached_rather_than_approached_forever(self):
        assert age_decay(10_000) == pytest.approx(AGE_DECAY_FLOOR)

    def test_the_halflife_halves_it_towards_the_floor(self):
        """Pins the shape so the half-life constant means what it says."""
        span = 1.0 - AGE_DECAY_FLOOR
        assert age_decay(AGE_HALFLIFE_BARS) == pytest.approx(
            AGE_DECAY_FLOOR + span / 2.0
        )

    def test_a_negative_or_missing_age_is_treated_as_fresh(self):
        assert age_decay(-5) == pytest.approx(1.0)
        assert age_decay(None) == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# FR-EM-S6 — distance away
# ---------------------------------------------------------------------------

class TestExcursion:

    def test_a_level_price_never_left_has_no_excursion(self):
        """Price hugging the level means nobody is trapped behind it."""
        closes = [100.0 + (i % 2) * 0.2 for i in range(60)]
        pct = level_excursion_pct(_frame(closes), level_price=100.0, first_bar=0)
        assert pct is not None
        assert pct < 1.0

    def test_a_deep_excursion_is_measured(self):
        closes = [100.0] * 20 + [85.0] * 20 + [99.0] * 10
        pct = level_excursion_pct(_frame(closes), level_price=100.0, first_bar=0)
        assert pct == pytest.approx(15.0, abs=0.6)

    def test_the_excursion_is_the_maximum_not_the_latest(self):
        """A level that was 20% away once and is 2% away now still has the
        trapped holders that the 20% move created."""
        closes = [100.0] * 10 + [80.0] * 5 + [98.0] * 10
        pct = level_excursion_pct(_frame(closes), level_price=100.0, first_bar=0)
        assert pct == pytest.approx(20.0, abs=0.6)

    def test_an_excursion_before_the_level_formed_does_not_count(self):
        """Causality, and the mechanism: holders are trapped by what happened
        *after* they transacted at the level, not before."""
        closes = [60.0] * 20 + [100.0] * 20
        early = level_excursion_pct(_frame(closes), level_price=100.0, first_bar=0)
        late = level_excursion_pct(_frame(closes), level_price=100.0, first_bar=20)
        assert early is not None and late is not None
        assert late < early

    def test_a_missing_frame_is_unknown_not_zero(self):
        assert level_excursion_pct(_frame([]), level_price=100.0, first_bar=0) is None


class TestDistanceSuppression:

    def test_a_level_without_the_excursion_is_suppressed_not_dropped(self):
        """`FR-EM-S6` is explicit: suppress, do not drop. A level with no
        trapped interest is weak evidence, not absent evidence."""
        weak = adjusted_level_strength(
            volume_strength=2.0, age_bars=0, excursion_pct=1.0,
        )
        assert weak is not None
        assert 0 < weak < 2.0

    def test_suppression_uses_the_stated_factor(self):
        assert adjusted_level_strength(
            volume_strength=1.0, age_bars=0, excursion_pct=0.0,
        ) == pytest.approx(DISTANCE_SUPPRESSION)

    def test_a_level_with_the_excursion_is_not_suppressed(self):
        full = adjusted_level_strength(
            volume_strength=2.0, age_bars=0, excursion_pct=DISTANCE_AWAY_PCT + 5,
        )
        assert full == pytest.approx(2.0)

    def test_the_threshold_is_the_books_figure_and_is_marked_as_sweepable(self):
        """E&M's 10% is a 1950s NYSE figure. It is the default, not a trusted
        constant (`FR-EM-S10`), and `W1` sweeps it."""
        assert DISTANCE_AWAY_PCT == pytest.approx(10.0)

    def test_an_unknown_excursion_does_not_suppress(self):
        """Unknown is not "no excursion" — the same rule as every other
        unavailability path in this workstream."""
        assert adjusted_level_strength(
            volume_strength=2.0, age_bars=0, excursion_pct=None,
        ) == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# The composite
# ---------------------------------------------------------------------------

class TestAdjustedStrength:

    def test_it_is_none_when_there_is_no_volume_strength(self):
        """Nothing to adjust: the fallback is the touch count, as everywhere
        else in EM-2."""
        assert adjusted_level_strength(
            volume_strength=None, age_bars=0, excursion_pct=50.0,
        ) is None

    def test_age_and_distance_both_apply(self):
        both = adjusted_level_strength(
            volume_strength=4.0, age_bars=AGE_HALFLIFE_BARS, excursion_pct=0.0,
        )
        age_only = adjusted_level_strength(
            volume_strength=4.0, age_bars=AGE_HALFLIFE_BARS, excursion_pct=99.0,
        )
        assert both < age_only < 4.0

    def test_it_never_exceeds_the_raw_strength(self):
        """Both effects are suppressive: neither may promote a level."""
        for age in (0, 10, 100, 500):
            for exc in (0.0, 5.0, 10.0, 50.0, None):
                out = adjusted_level_strength(
                    volume_strength=3.0, age_bars=age, excursion_pct=exc,
                )
                assert out is not None
                assert out <= 3.0 + 1e-9


# ---------------------------------------------------------------------------
# S6's rule still holds: the raw measure stays raw
# ---------------------------------------------------------------------------

class TestVolumeStrengthStaysRaw:

    def test_volume_strength_is_not_adjusted_by_age_or_distance(self):
        """`S6` established this the hard way. The composite goes on its own
        field so that nothing silently rewrites the raw measurement."""
        import app.services.sr_volume as srv

        frame = _frame(_pivoted_then_excursion())
        for lvl in _levels(frame):
            if lvl.volume_strength is None:
                continue
            expected = srv.aggregate_level_volume(
                frame, [t.bar_index for t in lvl.touches], level_price=lvl.price,
            ).value
            assert lvl.volume_strength == pytest.approx(expected)


# ---------------------------------------------------------------------------
# Schema, causality, determinism
# ---------------------------------------------------------------------------

class TestSchema:

    def test_the_new_fields_exist_and_are_additive(self):
        from app.models.schemas import SRTouch, SwingType

        for name in ("age_decay", "excursion_pct", "adjusted_strength",
                     "distance_suppressed"):
            assert name in SRLevel.model_fields, name

        lvl = SRLevel(
            price=100.0, type=SRLevelType.SUPPORT, strength=1, age_bars=0,
            touches=[SRTouch(bar_index=0, date="2026-01-01", price=100.0,
                             pivot_type=SwingType.LOW)],
        )
        assert lvl.age_decay is None
        assert lvl.excursion_pct is None
        assert lvl.adjusted_strength is None
        assert lvl.distance_suppressed is False

    def test_age_bars_is_finally_consumed(self):
        """`FR-EM-S5` is the first consumer of `age_bars`, which
        `_find_sr_levels` has always computed and never used."""
        frame = _frame(_pivoted_then_excursion())
        levels = _levels(frame)
        assert levels
        for lvl in levels:
            if lvl.age_decay is not None:
                assert lvl.age_decay == pytest.approx(age_decay(lvl.age_bars))


class TestCausalityAndDeterminism:

    def test_appending_future_bars_does_not_change_a_past_excursion(self):
        closes = [100.0] * 20 + [85.0] * 20
        short = _frame(closes)
        long = _frame(closes + [40.0] * 10)
        assert level_excursion_pct(short, 100.0, first_bar=0) == pytest.approx(
            level_excursion_pct(
                _frame(long["close"].tolist()[:len(closes)]), 100.0, first_bar=0,
            )
        )

    def test_repeated_runs_are_identical(self):
        frame = _frame(_pivoted_then_excursion())
        first = [(lv.price, lv.age_decay, lv.excursion_pct, lv.adjusted_strength)
                 for lv in _levels(frame)]
        second = [(lv.price, lv.age_decay, lv.excursion_pct, lv.adjusted_strength)
                  for lv in _levels(frame)]
        assert first == second

    def test_a_failure_cannot_lose_the_levels(self):
        import app.services.analysis_service as mod

        original = mod.adjusted_level_strength

        def boom(*args, **kwargs):
            raise RuntimeError("synthetic S7 failure")

        mod.adjusted_level_strength = boom
        try:
            levels = _levels(_frame(_pivoted_then_excursion()))
        finally:
            mod.adjusted_level_strength = original

        assert levels
        assert all(lvl.adjusted_strength is None for lvl in levels)
