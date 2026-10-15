"""EM-2 / S3 — `H-S2`, the volume-shuffle harness.

`H-S2` of `docs/SRS_edwards_magee_sr_levels.md` §5 is the cheapest statement
that a volume-weighted level reads what it claims to read. Permute the
``volume`` column against price and assert two things:

* the level **strength** changes measurably — the price-volume *relationship*
  is what carries the information, not volume's level or its distribution;
* the level **price** under the shipped arithmetic mean is **bit-identical** —
  proof the shuffle is doing nothing to the geometry, so any movement in
  strength is attributable to volume alone.

The fixture warning, which is the whole reason this task is separate
-------------------------------------------------------------------
A fixture whose volume column is **constant** is invariant under permutation.
Shuffle it and nothing moves, so the harness passes against an implementation
that ignores volume entirely — it is satisfiable by a decorative one. EM-1's
`H1` caught exactly that, twice, and the EM-2 plan carries the warning forward
into this task. `TestFixturesAreShuffleable` therefore asserts the property of
the *fixtures* before anything asserts a property of the code: if those guards
ever pass vacuously, every other test in this file is worthless.

What is testable now, and what waits for `S4`
--------------------------------------------
The `S1` primitives exist, so their response to a shuffle is asserted here for
real. ``SRLevel.volume_strength`` does not exist until `S4`, so the end-to-end
assertion is a strict xfail — red on purpose, and it flips to a hard failure
the moment `S4` lands without satisfying it.
"""
from __future__ import annotations

from typing import List, Optional, Tuple
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from app.models.schemas import SRLevel
from app.services.analysis_service import AnalysisService
from app.services.sr_volume import (
    SpanMode,
    congestion_span,
    relative_level_volume,
    volume_weighted_price,
)

SEED = 20261015
SHUFFLE_SEED = 99173


# ---------------------------------------------------------------------------
# Fixtures — scripted volume, by requirement
# ---------------------------------------------------------------------------

def scripted_volume(n: int, rng: np.random.Generator) -> np.ndarray:
    """Volume with real structure: a slow cycle, occasional bursts, noise.

    Deliberately **not** constant and deliberately **not** i.i.d. — a shuffle
    has to be able to destroy something, or `H-S2` proves nothing.
    """
    cycle = 1.0 + 0.4 * np.sin(np.arange(n) / 17.0)
    burst = 1.0 + 4.0 * (rng.random(n) > 0.95)
    noise = 1.0 + rng.normal(0.0, 0.18, n)
    vol = np.clip(np.round(900_000 * cycle * burst * noise), 1_000, None)
    return vol.astype(float)


def oscillating_frame(n: int = 300, floor: float = 100.0, ceil: float = 112.0) -> pd.DataFrame:
    """A range-bound series, so `_find_sr_levels` actually produces levels to
    measure, with volume scripted to be *heavy at the extremes* — the shape
    E&M describe, where turnover concentrates where the level formed."""
    rng = np.random.default_rng(SEED)
    span = ceil - floor
    close = floor + span * (0.5 + 0.5 * np.sin(np.arange(n) / 9.0))
    close = close + rng.normal(0.0, 0.25, n)

    # Heavy volume near the band edges, light in the middle.
    mid = (floor + ceil) / 2.0
    edge_weight = 1.0 + 2.5 * (np.abs(close - mid) / (span / 2.0))
    vol = scripted_volume(n, rng) * edge_weight

    return pd.DataFrame({
        "date": pd.date_range("2021-01-01", periods=n, freq="B"),
        "open": close,
        "high": close + 0.45,
        "low": close - 0.45,
        "close": close,
        "volume": np.round(vol),
    })


def shuffled(frame: pd.DataFrame, seed: int = SHUFFLE_SEED) -> pd.DataFrame:
    """The same frame with ``volume`` permuted and every price column intact."""
    out = frame.copy()
    rng = np.random.default_rng(seed)
    out["volume"] = rng.permutation(frame["volume"].to_numpy())
    return out


def _levels(frame: pd.DataFrame) -> List[SRLevel]:
    svc = AnalysisService(session=MagicMock())
    supports, resistances = svc._find_sr_levels(frame)
    seen = set()
    out: List[SRLevel] = []
    for lvl in list(supports) + list(resistances):
        key = (round(lvl.price, 9), lvl.type)
        if key not in seen:
            seen.add(key)
            out.append(lvl)
    return out


def _spans(frame: pd.DataFrame) -> List[Tuple[int, int]]:
    """Per-touch congestion spans — the shape `S1` measured as the correct one
    (a congestion is local to a visit, not to a whole cluster)."""
    spans: List[Tuple[int, int]] = []
    for lvl in _levels(frame):
        for touch in lvl.touches:
            span = congestion_span(
                frame, [touch.bar_index], mode=SpanMode.NEIGHBOURHOOD,
            )
            if span is not None:
                spans.append(span)
    return spans


# ---------------------------------------------------------------------------
# The fixture guards — these gate everything else in the file
# ---------------------------------------------------------------------------

class TestFixturesAreShuffleable:
    """EM-1's `H1` lesson, asserted rather than trusted."""

    def test_the_volume_column_is_not_constant(self):
        frame = oscillating_frame()
        vol = frame["volume"].to_numpy()
        assert vol.std() > 0, (
            "a constant volume column is invariant under permutation, which "
            "makes H-S2 satisfiable by an implementation that ignores volume"
        )
        assert vol.std() / vol.mean() > 0.1, "volume varies too little to shuffle"

    def test_the_shuffle_actually_moves_the_column(self):
        frame = oscillating_frame()
        before = frame["volume"].to_numpy()
        after = shuffled(frame)["volume"].to_numpy()
        assert not np.array_equal(before, after)

    def test_the_shuffle_preserves_the_multiset(self):
        """A permutation, not a resample: volume's marginal distribution is
        untouched, so only its alignment with price is destroyed."""
        frame = oscillating_frame()
        assert sorted(frame["volume"].tolist()) == sorted(shuffled(frame)["volume"].tolist())

    def test_the_shuffle_leaves_every_price_column_untouched(self):
        frame = oscillating_frame()
        after = shuffled(frame)
        for col in ("open", "high", "low", "close"):
            assert frame[col].equals(after[col])

    def test_the_fixture_produces_levels_to_measure(self):
        assert _levels(oscillating_frame()), "no levels: nothing for H-S2 to test"

    def test_volume_is_correlated_with_price_position_before_the_shuffle(self):
        """The fixture scripts heavy volume at the band edges. If that
        correlation were absent, a shuffle would have nothing to destroy and
        the harness would be vacuous even with a varying column."""
        frame = oscillating_frame()
        close = frame["close"].to_numpy()
        vol = frame["volume"].to_numpy()
        distance_from_mid = np.abs(close - close.mean())
        rho = np.corrcoef(distance_from_mid, vol)[0, 1]
        assert rho > 0.2, f"fixture volume is not tied to price position (rho={rho:.3f})"


# ---------------------------------------------------------------------------
# Invariance: the geometry must not move
# ---------------------------------------------------------------------------

class TestPriceIsBitIdenticalUnderShuffle:
    """`H-S2`'s second half. Without this, a change in strength could be a
    change in the clustering rather than in the volume reading."""

    def test_level_prices_are_bit_identical(self):
        before = _levels(oscillating_frame())
        after = _levels(shuffled(oscillating_frame()))

        assert len(before) == len(after)
        for a, b in zip(before, after):
            assert a.price == b.price, "level price moved under a volume shuffle"
            assert a.type == b.type
            assert a.strength == b.strength
            assert a.age_bars == b.age_bars

    def test_congestion_spans_are_bit_identical(self):
        """`congestion_span` reads only price, so a volume shuffle must not
        move a single span boundary."""
        assert _spans(oscillating_frame()) == _spans(shuffled(oscillating_frame()))


# ---------------------------------------------------------------------------
# Response: the volume readings must move
# ---------------------------------------------------------------------------

class TestPrimitivesRespondToTheShuffle:
    """The `S1` primitives exist, so their response is asserted for real here
    rather than deferred with the `S4` field."""

    def test_relative_level_volume_changes_on_at_least_most_spans(self):
        frame = oscillating_frame()
        mixed = shuffled(frame)
        spans = _spans(frame)
        assert spans, "no spans to measure"

        moved = 0
        compared = 0
        for start, end in spans:
            a = relative_level_volume(frame, start, end)
            b = relative_level_volume(mixed, start, end)
            if a.known and b.known:
                compared += 1
                if a.value != pytest.approx(b.value):
                    moved += 1

        assert compared > 0, "no comparable spans"
        assert moved / compared > 0.8, (
            f"only {moved}/{compared} spans moved under a volume shuffle — the "
            f"reading is not tracking the price-volume relationship"
        )

    def test_volume_weighted_price_changes_under_the_shuffle(self):
        """The centre of gravity is a volume-weighted close, so permuting the
        weights must move it."""
        frame = oscillating_frame()
        mixed = shuffled(frame)
        spans = _spans(frame)

        moved = 0
        compared = 0
        for start, end in spans:
            a = volume_weighted_price(frame, start, end)
            b = volume_weighted_price(mixed, start, end)
            if a is not None and b is not None:
                compared += 1
                if a != pytest.approx(b):
                    moved += 1

        assert compared > 0
        assert moved / compared > 0.8

    def test_the_arithmetic_mean_close_does_not_change(self):
        """The control for the test above: a plain mean of closes is blind to
        volume, so it must be identical. If this ever moved, the shuffle
        helper would be corrupting price."""
        frame = oscillating_frame()
        mixed = shuffled(frame)
        for start, end in _spans(frame):
            a = float(frame["close"].iloc[start:end + 1].mean())
            b = float(mixed["close"].iloc[start:end + 1].mean())
            assert a == pytest.approx(b)


# ---------------------------------------------------------------------------
# The end-to-end assertion — awaiting S4
# ---------------------------------------------------------------------------

def _volume_strengths(frame: pd.DataFrame) -> List[Optional[float]]:
    return [getattr(lvl, "volume_strength", None) for lvl in _levels(frame)]


class TestLevelStrengthUnderShuffle:

    def test_volume_strength_is_populated(self):
        """`S4` landed. Until then this test asserted the opposite and the
        assertion below was a strict xfail; the marker turned `XPASS(strict)`
        the moment the field appeared, which is what forced both to be
        updated rather than left stale."""
        strengths = _volume_strengths(oscillating_frame())
        assert strengths
        assert any(v is not None for v in strengths)

    def test_level_volume_strength_changes_measurably_under_the_shuffle(self):
        """`H-S2`: strength reads the price-volume relationship.

        Paired against `TestPriceIsBitIdenticalUnderShuffle`, which proves the
        geometry held still while this moved.
        """
        frame = oscillating_frame()
        before = _volume_strengths(frame)
        after = _volume_strengths(shuffled(frame))

        assert before and all(v is not None for v in before), "volume_strength absent"
        assert len(before) == len(after)

        moved = sum(
            1 for a, b in zip(before, after)
            if a is not None and b is not None and a != pytest.approx(b)
        )
        assert moved / len(before) > 0.8, (
            f"only {moved}/{len(before)} level strengths moved under a volume "
            f"shuffle — strength is not reading volume"
        )
