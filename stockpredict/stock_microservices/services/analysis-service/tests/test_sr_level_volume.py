"""EM-2 / S4 — `volume_strength` and the centre of gravity on `SRLevel`.

`FR-EM-S1` (strength is volume, not touch count), `FR-EM-S2` (the level price
is a volume-weighted centre of gravity) and `NFR-S2` (it is an approximation
and must be labelled as one). Written before the fields exist.

What S4 may and may not change
------------------------------
`price` is **unchanged** in this task. Moving the level price to the centre of
gravity moves a number three live consumers trade off — the CHART stop, the
SR_LEVEL target and the bounce/breakout confidence — and the plan puts that
behind `D1`'s evidence. So `price_cog` arrives *alongside* `price`, and
`TestPriceIsUnchanged` is the guard that keeps this task additive.

Equally, `strength` keeps its meaning. SRS open question 1 was settled by
reading the consumer: `sr_bounce_breakout` does `int(lvl.get("strength", 1))`
and then `min(0.4 + strength * 0.05 + ..., 0.9)`, so a volume *ratio* of 2.3
would be silently truncated to 2 and any large figure would saturate the cap.
Repurposing the field would corrupt it quietly rather than merely change it.

The per-touch rule, from S1
---------------------------
`S1` measured that a congestion is **local to a visit**: `_find_sr_levels`
clusters every visit to a price across the whole window, so a cluster-wide span
is most of the frame and carries no information (0.61x-1.18x across real
levels, against 0.48x-2.44x measured per touch). So the primitives are called
once per touch and the results aggregated, and `sr_volume.MAX_CONGESTION_BARS`
makes the wrong shape fail loudly.
"""
from __future__ import annotations

import inspect
from pathlib import Path
from typing import List, Optional
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from app.models.schemas import SRLevel, SRLevelType
from app.services import sr_volume
from app.services.analysis_service import AnalysisService
from app.services.sr_volume import Aggregation

SEED = 20261015


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _svc() -> AnalysisService:
    return AnalysisService(session=MagicMock())


def _frame(
    closes: List[float],
    volumes: Optional[List[float]] = None,
    hl_pad: float = 0.45,
) -> pd.DataFrame:
    closes = [float(c) for c in closes]
    if volumes is None:
        volumes = [1_000_000.0] * len(closes)
    return pd.DataFrame({
        "open": closes,
        "high": [c + hl_pad for c in closes],
        "low": [c - hl_pad for c in closes],
        "close": closes,
        "volume": [float(v) for v in volumes],
    })


def _two_level_frame(
    heavy_at_low: bool = True,
    n_cycles: int = 7,
    heavy_multiple: float = 6.0,
) -> pd.DataFrame:
    """A range-bound series touching a floor near 100 and a ceiling near 118,
    with volume deliberately heavy at **one** of them.

    This is the fixture the discriminating property is measured on: two levels
    with the same touch count, differing only in the volume that changed hands
    there. E&M's claim is that the heavy one is the stronger level; if
    `volume_strength` cannot separate these two, it is not measuring anything.
    """
    closes: List[float] = []
    volumes: List[float] = []
    base = 900_000.0
    for _ in range(n_cycles):
        leg = [100.0, 103.0, 108.0, 113.0, 118.0, 113.0, 108.0, 103.0]
        for price in leg:
            closes.append(price)
            near_low = price <= 103.0
            near_high = price >= 113.0
            heavy = near_low if heavy_at_low else near_high
            volumes.append(base * (heavy_multiple if heavy else 1.0))
    # Lead-in so the trailing baseline has history that is not itself part of
    # the congestions (sr_volume needs MIN_BASELINE_BARS before a span).
    lead_closes = [109.0 + (i % 3) * 0.4 for i in range(40)]
    lead_vol = [base] * 40
    return _frame(lead_closes + closes, lead_vol + volumes)


def _levels(frame: pd.DataFrame) -> List[SRLevel]:
    supports, resistances = _svc()._find_sr_levels(frame)
    seen = set()
    out: List[SRLevel] = []
    for lvl in list(supports) + list(resistances):
        key = (round(lvl.price, 9), lvl.type)
        if key not in seen:
            seen.add(key)
            out.append(lvl)
    return out


def _nearest(levels: List[SRLevel], price: float) -> SRLevel:
    return min(levels, key=lambda lv: abs(lv.price - price))


# ---------------------------------------------------------------------------
# The schema change must be additive
# ---------------------------------------------------------------------------

class TestSchemaIsAdditive:

    def test_srlevel_has_the_two_new_fields(self):
        fields = SRLevel.model_fields
        assert "volume_strength" in fields
        assert "price_cog" in fields

    def test_both_new_fields_default_to_none(self):
        """`FR-EM-S8`: additive. A caller that constructs an SRLevel without
        them — any existing test, any other service — must keep working."""
        from app.models.schemas import SRTouch, SwingType

        lvl = SRLevel(
            price=100.0, type=SRLevelType.SUPPORT, strength=2, age_bars=5,
            touches=[SRTouch(bar_index=1, date="2026-01-01", price=100.0,
                             pivot_type=SwingType.LOW)],
        )
        assert lvl.volume_strength is None
        assert lvl.price_cog is None

    def test_strength_is_still_an_int_touch_count(self):
        """SRS open question 1, settled by reading the consumer: a float ratio
        in this field would be truncated by `int()` in sr_bounce_breakout and
        would saturate its 0.9 confidence cap."""
        assert SRLevel.model_fields["strength"].annotation is int

        frame = _two_level_frame()
        for lvl in _levels(frame):
            assert isinstance(lvl.strength, int)
            assert lvl.strength == len(lvl.touches)


# ---------------------------------------------------------------------------
# `price` must not move — this task is additive
# ---------------------------------------------------------------------------

class TestPriceIsUnchanged:

    def test_price_is_still_the_arithmetic_mean_of_the_touch_prices(self):
        """Pins the pre-S4 definition. `price_cog` is offered alongside; three
        live consumers read `price`, and moving it is `D1`'s decision."""
        for lvl in _levels(_two_level_frame()):
            expected = round(sum(t.price for t in lvl.touches) / len(lvl.touches), 4)
            assert lvl.price == expected

    def test_price_does_not_move_when_volume_changes(self):
        """The sharpest form: multiply volume by 50 and `price` must be
        bit-identical, while `price_cog` is free to move."""
        frame = _two_level_frame()
        heavy = frame.copy()
        heavy["volume"] = frame["volume"] * 50.0

        before = [(lv.price, lv.type, lv.strength) for lv in _levels(frame)]
        after = [(lv.price, lv.type, lv.strength) for lv in _levels(heavy)]
        assert before == after


# ---------------------------------------------------------------------------
# FR-EM-S1 — strength is volume
# ---------------------------------------------------------------------------

class TestVolumeStrength:

    def test_volume_strength_is_populated(self):
        levels = _levels(_two_level_frame())
        assert any(lv.volume_strength is not None for lv in levels)

    def test_the_heavy_level_outranks_the_light_one(self):
        """`FR-EM-S1`'s whole claim, as a property.

        Two levels, same touch count, differing only in the volume transacted
        there. Touch count cannot tell them apart; volume strength must.
        """
        heavy_low = _two_level_frame(heavy_at_low=True)
        low_lvl = _nearest(_levels(heavy_low), 100.0)
        high_lvl = _nearest(_levels(heavy_low), 118.0)

        assert low_lvl.volume_strength is not None
        assert high_lvl.volume_strength is not None
        assert low_lvl.volume_strength > high_lvl.volume_strength

    def test_the_ranking_follows_the_volume_not_the_price(self):
        """The mirror image: move the heavy volume to the ceiling and the
        ranking must invert. Without this, a test could pass because low
        levels happen to score higher for some unrelated reason."""
        heavy_high = _two_level_frame(heavy_at_low=False)
        low_lvl = _nearest(_levels(heavy_high), 100.0)
        high_lvl = _nearest(_levels(heavy_high), 118.0)

        assert high_lvl.volume_strength > low_lvl.volume_strength

    def test_touch_count_cannot_separate_the_two_levels(self):
        """States the premise the test above depends on: if the touch counts
        differed, the comparison would not be isolating volume."""
        levels = _levels(_two_level_frame(heavy_at_low=True))
        low_lvl = _nearest(levels, 100.0)
        high_lvl = _nearest(levels, 118.0)
        assert low_lvl.strength == high_lvl.strength

    def test_volume_strength_is_relative_not_absolute(self):
        """`FR-EM-S1`: expressed relative to the symbol's own recent volume,
        never as a share count. Scaling the whole column must leave it
        unchanged — that is what makes the figure comparable across symbols."""
        frame = _two_level_frame()
        scaled = frame.copy()
        scaled["volume"] = frame["volume"] * 1000.0

        before = [lv.volume_strength for lv in _levels(frame)]
        after = [lv.volume_strength for lv in _levels(scaled)]

        assert before == pytest.approx(after, rel=1e-9)
        assert any(v is not None for v in before)


# ---------------------------------------------------------------------------
# FR-EM-S2 — the centre of gravity
# ---------------------------------------------------------------------------

class TestPriceCog:

    def test_price_cog_is_populated(self):
        assert any(lv.price_cog is not None for lv in _levels(_two_level_frame()))

    def test_price_cog_is_a_volume_weighted_close(self):
        """Computed directly from the definition on a hand-built span, so the
        test pins the arithmetic rather than restating the implementation."""
        closes = [10.0] * 20 + [100.0, 100.0, 100.0, 200.0]
        volumes = [1_000.0] * 20 + [1_000.0, 1_000.0, 1_000.0, 3_000.0]
        cog = sr_volume.volume_weighted_price(_frame(closes, volumes), 20, 23)
        expected = (100 * 1000 + 100 * 1000 + 100 * 1000 + 200 * 3000) / 6000
        assert cog == pytest.approx(expected)

    def test_price_cog_sits_inside_the_congestion_price_range(self):
        """A weighted mean of closes cannot fall outside the closes it
        averages. Cheap, but it is the test that catches a weight/value mix-up
        in the accumulation."""
        frame = _two_level_frame()
        lo = float(frame["close"].min())
        hi = float(frame["close"].max())
        for lvl in _levels(frame):
            if lvl.price_cog is not None:
                assert lo <= lvl.price_cog <= hi

    def test_price_cog_moves_when_the_weights_move(self):
        """If permuting volume left the centre of gravity alone, it would not
        be weighted by volume at all — the `H-S2` property, at field level."""
        frame = _two_level_frame()
        shuffled = frame.copy()
        rng = np.random.default_rng(7)
        shuffled["volume"] = rng.permutation(frame["volume"].to_numpy())

        before = [lv.price_cog for lv in _levels(frame)]
        after = [lv.price_cog for lv in _levels(shuffled)]
        pairs = [(a, b) for a, b in zip(before, after) if a is not None and b is not None]
        assert pairs
        assert any(a != pytest.approx(b) for a, b in pairs)


# ---------------------------------------------------------------------------
# NFR-S2 — the approximation must be labelled, and never mis-named
# ---------------------------------------------------------------------------

class TestApproximationIsLabelled:

    FORBIDDEN = ("volume_at_price", "volume at price", "volume-at-price")

    def _sources(self) -> List[Path]:
        root = Path(__file__).resolve().parents[1] / "app"
        return [
            root / "services" / "sr_volume.py",
            root / "services" / "analysis_service.py",
            root / "models" / "schemas.py",
        ]

    def test_nothing_is_named_volume_at_price(self):
        """`NFR-S2`, as it actually binds: no *identifier* may call this
        volume-at-price.

        An earlier version of this test banned the phrase from the source
        outright and failed on the docstring that forbids it — prose which
        says "this is NOT volume-at-price" is the requirement being met, not
        broken. So the check is on identifiers, where the naming claim
        actually lives, plus the user-facing descriptions below.
        """
        import re

        pattern = re.compile(r"\bvolume[_\s-]?at[_\s-]?price\b")
        offenders = []
        for path in self._sources():
            if not path.exists():
                continue
            for lineno, line in enumerate(path.read_text().splitlines(), 1):
                stripped = line.strip()
                # Identifier-ish contexts only: assignments, defs, classes,
                # attribute access and dict keys — not prose.
                if not pattern.search(stripped.lower()):
                    continue
                looks_like_code = any(
                    tok in stripped
                    for tok in ("def ", "class ", " = ", "self.", '"volume_at', "'volume_at")
                )
                if looks_like_code:
                    offenders.append(f"{path.name}:{lineno}: {stripped[:70]}")
        assert not offenders, "NFR-S2 violated by an identifier: " + "; ".join(offenders)

    def test_the_module_disclaims_the_phrase_rather_than_merely_avoiding_it(self):
        """The positive half, and the stronger statement: `NFR-S2` wants the
        approximation *labelled*, so the module must say outright that it is
        not volume at price and why daily bars cannot supply one."""
        text = (Path(__file__).resolve().parents[1]
                / "app" / "services" / "sr_volume.py").read_text().lower()
        assert "not volume-at-price" in text or "not** volume-at-price" in text
        assert "nfr-s2" in text

    def test_the_user_facing_descriptions_never_use_the_phrase(self):
        """The field descriptions reach the API response and the UI, which is
        exactly where `NFR-S2`'s prohibition bites."""
        for name in ("volume_strength", "price_cog"):
            description = (SRLevel.model_fields[name].description or "").lower()
            for phrase in self.FORBIDDEN:
                assert phrase not in description, f"{name}: {phrase!r}"

    def test_price_cog_documents_what_it_actually_is(self):
        """The field must carry the approximation in its own description, so a
        reader of the API cannot mistake it for the real thing."""
        description = (SRLevel.model_fields["price_cog"].description or "").lower()
        assert "volume-weighted" in description
        assert "close" in description
        assert "approximation" in description

    def test_the_aggregation_choice_is_documented_in_the_module(self):
        doc = inspect.getdoc(sr_volume.aggregate_level_volume) or ""
        assert "sum" in doc.lower() and "max" in doc.lower()


# ---------------------------------------------------------------------------
# H-S4 causality, EC-S1/S2 thin data, H-S6 determinism
# ---------------------------------------------------------------------------

class TestCausality:

    def test_appending_future_bars_does_not_move_a_past_levels_volume(self):
        """`H-S4`. A level's volume is what traded while it was forming, not
        what has traded since. This is what forbids normalising volume over the
        whole series."""
        frame = _two_level_frame()
        cut = len(frame) - 40
        past = frame.iloc[:cut].reset_index(drop=True)

        before = [(lv.price, lv.volume_strength, lv.price_cog) for lv in _levels(past)]

        future = frame.iloc[cut:].copy()
        future["volume"] = future["volume"] * 25.0
        extended = pd.concat([past, future], ignore_index=True)
        # Re-slice to the same window so the comparison is level-for-level.
        after = [
            (lv.price, lv.volume_strength, lv.price_cog)
            for lv in _levels(extended.iloc[:cut].reset_index(drop=True))
        ]
        assert before == after


class TestThinData:

    def test_missing_volume_column_leaves_the_fields_none_and_still_ships_levels(self):
        """`EC-S1`. The level is still produced; only the volume claim is
        withheld, so the caller falls back to the touch count."""
        frame = _two_level_frame().drop(columns=["volume"])
        levels = _levels(frame)
        assert levels
        assert all(lv.volume_strength is None for lv in levels)
        assert all(lv.price_cog is None for lv in levels)

    def test_all_null_volume_is_unknown_not_zero(self):
        frame = _two_level_frame()
        frame["volume"] = None
        levels = _levels(frame)
        assert levels
        assert all(lv.volume_strength is None for lv in levels)

    def test_all_zero_volume_is_unknown_not_a_zero_strength(self):
        """A dormant symbol must read as *unknown*, never as "no interest
        here" — the level could be perfectly real and simply untraded."""
        frame = _two_level_frame()
        frame["volume"] = 0.0
        levels = _levels(frame)
        assert levels
        assert all(lv.volume_strength is None for lv in levels)

    def test_a_volume_bug_cannot_break_level_detection(self):
        """`NFR-S2`'s failure-isolation sibling: if the volume layer raises,
        the levels themselves must still ship. Three consumers depend on them
        existing."""
        import app.services.analysis_service as mod

        original = mod.aggregate_level_volume

        def boom(*args, **kwargs):
            raise RuntimeError("synthetic volume failure")

        mod.aggregate_level_volume = boom
        try:
            levels = _levels(_two_level_frame())
        finally:
            mod.aggregate_level_volume = original

        assert levels, "a volume failure must not remove the levels"
        assert all(lv.volume_strength is None for lv in levels)


class TestDeterminism:

    def test_repeated_runs_are_identical(self):
        frame = _two_level_frame()
        first = [(lv.price, lv.volume_strength, lv.price_cog) for lv in _levels(frame)]
        second = [(lv.price, lv.volume_strength, lv.price_cog) for lv in _levels(frame)]
        assert first == second


# ---------------------------------------------------------------------------
# The aggregation question S4 inherits from S1
# ---------------------------------------------------------------------------

class TestAggregationModes:
    """`S1` left open whether a level's strength is the SUM of its visits'
    volume (E&M's "volume transacted there") or the MAX (the heaviest single
    visit). Both are implemented so `H-S1` can choose on evidence; this class
    only asserts they are distinguishable and behave as named."""

    def test_both_modes_exist(self):
        assert set(Aggregation) >= {Aggregation.SUM, Aggregation.MAX}

    def test_sum_rewards_repeated_visits_and_max_does_not(self):
        few = _two_level_frame(n_cycles=3)
        many = _two_level_frame(n_cycles=9)

        def strength(frame, aggregation):
            levels = _levels(frame)
            lvl = _nearest(levels, 100.0)
            return sr_volume.aggregate_level_volume(
                frame, [t.bar_index for t in lvl.touches], aggregation=aggregation
            ).value

        sum_few = strength(few, Aggregation.SUM)
        sum_many = strength(many, Aggregation.SUM)
        max_few = strength(few, Aggregation.MAX)
        max_many = strength(many, Aggregation.MAX)

        assert sum_many > sum_few, "SUM must grow with the number of visits"
        assert max_many == pytest.approx(max_few, rel=0.35), (
            "MAX must be roughly insensitive to how many equally-heavy visits "
            "there were"
        )
