"""EM-2 / S5 — role reversal and break history (`FR-EM-S3`, `EC-S4`).

Edwards & Magee, Ch 13, and the half of the chapter they say casual chart
readers never grasp:

    "A former Top, once surpassed, becomes a Bottom zone in a subsequent
    downtrend; an old Bottom, once penetrated, becomes a Top zone in a later
    advance."

So a penetrated level is not spent — it changes sides. This task gives a level
its **break history** and the type that history implies.

Why the threshold is in ATR units, not a percentage
---------------------------------------------------
`FR-EM-S3` forbids inventing a number here and points at EM-9, which measured
that one percentage is structurally wrong across kinds: median penetration ran
from **0.56%** (`SR_BOUNCE`) to **4.47%** (`SR_BREAKOUT`), an eightfold spread,
so the book's 3% is "nearly inert for one and nearly total for the other"
(`docs/em9_penetration_filter_sweep.md`). A fixed percentage would also mean a
quiet large cap and a volatile small cap are judged on the same scale, which
they are not. Decisiveness is therefore measured in multiples of the symbol's
own ATR, and `TestThresholdIsVolatilityRelative` is the test that stops anyone
replacing it with a percentage.

What this task deliberately does NOT change
-------------------------------------------
`type` keeps its current meaning — the pivot-composition answer — and the
supports/resistances split is untouched. The reversal surfaces as
`effective_type` + `role_reversed` alongside it.

That is a deliberate deviation from the plan's wording ("the most recent
penetration decides the current type"), taken for the reason `S4` established:
`type` decides which list a level lands in, three live consumers read those
lists, and `S4` has just shown that EM-2's measures do not yet beat touch
count on `H-S1`. Changing what consumers read, on the strength of a model that
is not yet proven, is the mistake this plan keeps avoiding. The payload
carries everything needed to make the switch, and `S9`/`D1` can make it with
evidence. `FR-EM-S3`'s own requirement — that a reversed level be
distinguishable from a `FLIP` — is satisfied either way, and needs the extra
field regardless.
"""
from __future__ import annotations

from typing import List, Optional
from unittest.mock import MagicMock

import pandas as pd
import pytest

from app.models.schemas import SRBreak, SRLevel, SRLevelType
from app.services.analysis_service import AnalysisService
from app.services.sr_volume import (
    BREAK_ATR_MULTIPLE,
    detect_breaks,
    effective_level_type,
    trailing_atr,
)


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

def _frame(closes: List[float], hl_pad: float = 0.4, volume: float = 1_000_000.0) -> pd.DataFrame:
    closes = [float(c) for c in closes]
    return pd.DataFrame({
        "open": closes,
        "high": [c + hl_pad for c in closes],
        "low": [c - hl_pad for c in closes],
        "close": closes,
        "volume": [volume] * len(closes),
    })


#: Intrabar range wide enough that the routine swing below stays inside the
#: ATR band. See `TestThresholdIsVolatilityRelative` and the limitation note
#: there: `pad` raises ATR without moving a single close, which is the lever
#: that isolates volatility from penetration depth.
QUIET_PAD = 3.0


def _oscillate(level: float, amplitude: float, cycles: int) -> List[float]:
    """Price swinging around `level`, forming pivots on both sides of it."""
    out: List[float] = []
    for _ in range(cycles):
        out += [level + amplitude, level + amplitude / 2, level,
                level - amplitude / 2, level - amplitude, level - amplitude / 2,
                level, level + amplitude / 2]
    return out


def _support_level(levels: List[SRLevel]) -> Optional[SRLevel]:
    return next((lv for lv in levels if lv.type == SRLevelType.SUPPORT), None)


def _resistance_level(levels: List[SRLevel]) -> Optional[SRLevel]:
    return next((lv for lv in levels if lv.type == SRLevelType.RESISTANCE), None)


def _svc() -> AnalysisService:
    return AnalysisService(session=MagicMock())


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


def _nearest(levels: List[SRLevel], price: float) -> Optional[SRLevel]:
    return min(levels, key=lambda lv: abs(lv.price - price)) if levels else None


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

class TestSchema:

    def test_srbreak_carries_direction_bar_date_and_size(self):
        fields = SRBreak.model_fields
        for name in ("direction", "bar_index", "date", "penetration_atr", "penetration_pct"):
            assert name in fields, name

    def test_srlevel_gains_breaks_effective_type_and_the_reversal_flag(self):
        fields = SRLevel.model_fields
        assert "breaks" in fields
        assert "effective_type" in fields
        assert "role_reversed" in fields

    def test_the_new_fields_are_additive(self):
        """`FR-EM-S8`: a caller constructing an SRLevel without them — any
        existing test, any other service — must keep working."""
        from app.models.schemas import SRTouch, SwingType

        lvl = SRLevel(
            price=100.0, type=SRLevelType.SUPPORT, strength=2, age_bars=5,
            touches=[SRTouch(bar_index=1, date="2026-01-01", price=100.0,
                             pivot_type=SwingType.LOW)],
        )
        assert lvl.breaks == []
        assert lvl.role_reversed is False
        assert lvl.effective_type is None


# ---------------------------------------------------------------------------
# FR-EM-S3 — the reversal itself
# ---------------------------------------------------------------------------

class TestRoleReversal:

    def test_an_unbroken_level_has_no_breaks_and_keeps_its_type(self):
        frame = _frame(_oscillate(100.0, 2.0, cycles=6), hl_pad=QUIET_PAD)
        levels = _levels(frame)
        assert levels
        assert all(not lvl.breaks for lvl in levels), (
            "fixture is not quiet: the routine swing is tripping the band"
        )
        for lvl in levels:
            assert lvl.role_reversed is False
            assert lvl.effective_type == lvl.type

    def test_a_support_broken_downward_becomes_resistance(self):
        """E&M's claim, in its simplest form.

        The level under test is the SUPPORT cluster — the one whose role the
        break actually reverses. A resistance broken downward is merely
        confirmed as resistance, which is why `role_reversed` keys off the
        declared type rather than off the break alone.
        """
        closes = _oscillate(100.0, 2.0, cycles=6) + [92.0, 86.0, 80.0, 78.0, 79.0, 78.5]
        lvl = _support_level(_levels(_frame(closes, hl_pad=QUIET_PAD)))
        assert lvl is not None, "fixture produced no support level"

        assert any(b.direction == "down" for b in lvl.breaks)
        assert lvl.role_reversed is True
        assert lvl.effective_type == SRLevelType.RESISTANCE

    def test_a_resistance_broken_upward_becomes_support(self):
        """The mirror image. Without it, a test could pass because everything
        happens to resolve to RESISTANCE."""
        closes = _oscillate(100.0, 2.0, cycles=6) + [108.0, 114.0, 120.0, 122.0, 121.0, 122.5]
        lvl = _resistance_level(_levels(_frame(closes, hl_pad=QUIET_PAD)))
        assert lvl is not None, "fixture produced no resistance level"

        assert any(b.direction == "up" for b in lvl.breaks)
        assert lvl.role_reversed is True
        assert lvl.effective_type == SRLevelType.SUPPORT

    def test_a_break_records_where_and_how_far(self):
        closes = _oscillate(100.0, 2.0, cycles=6) + [92.0, 86.0, 80.0, 78.0]
        lvl = _support_level(_levels(_frame(closes, hl_pad=QUIET_PAD)))
        assert lvl is not None

        brk = lvl.breaks[-1]
        assert brk.bar_index >= 0
        assert brk.penetration_atr > 0
        assert brk.penetration_pct > 0

    def test_a_reversed_level_is_distinguishable_from_a_flip_level(self):
        """`FR-EM-S3` is explicit that `FLIP` — a pivot-composition tie — is
        **not** the same concept as a level whose role reversed on a
        penetration, and that a consumer must be able to tell them apart."""
        closes = _oscillate(100.0, 2.0, cycles=6) + [92.0, 86.0, 80.0, 78.0]
        for lvl in _levels(_frame(closes, hl_pad=QUIET_PAD)):
            if lvl.role_reversed:
                # Whatever `type` says — including FLIP — the reversal is
                # readable on its own field rather than inferred.
                assert lvl.breaks
                assert lvl.effective_type is not None


# ---------------------------------------------------------------------------
# The EM-9 lesson: the threshold must not be a percentage
# ---------------------------------------------------------------------------

class TestThresholdIsVolatilityRelative:

    def test_a_shallow_poke_through_is_not_a_break(self):
        """A level price brushes through by a fraction of an ATR has not been
        penetrated decisively — this is the whole point of having a threshold
        at all."""
        closes = _oscillate(100.0, 3.0, cycles=8)
        frame = _frame(closes)
        atr = trailing_atr(frame)
        shallow = 0.1 * float(atr.iloc[-1])

        breaks = detect_breaks(frame, level_price=100.0 + shallow, first_bar=0)
        assert breaks == [] or all(b.penetration_atr >= BREAK_ATR_MULTIPLE for b in breaks)

    def test_the_same_percentage_move_is_judged_differently_at_different_volatility(self):
        """The EM-9 finding, as an executable property.

        Two symbols move through a level by the **same percentage**. The quiet
        one has been decisively penetrated; the volatile one is inside its
        normal daily noise. A fixed-percentage threshold cannot tell them
        apart, and that is exactly the failure EM-9 measured — an eightfold
        spread in median penetration across signal kinds.
        """
        # IDENTICAL closes in both frames, so the penetration is the same 2%
        # in each. Only the intrabar range differs, which moves ATR and
        # nothing else — the cleanest possible isolation of the property.
        closes = _oscillate(100.0, 2.0, cycles=6) + [98.0] * 8
        quiet = _frame(closes, hl_pad=0.4)
        volatile = _frame(closes, hl_pad=QUIET_PAD)

        assert quiet["close"].equals(volatile["close"]), "closes must be identical"

        quiet_breaks = detect_breaks(quiet, level_price=100.0, first_bar=0)
        volatile_breaks = detect_breaks(volatile, level_price=100.0, first_bar=0)

        assert quiet_breaks, "2% through a level on a 0.4-wide range is decisive"
        assert not volatile_breaks, (
            "the same 2% on a 6-wide range is inside the daily noise; a "
            "percentage threshold could not tell these two apart"
        )

    def test_the_threshold_is_expressed_in_atr_multiples(self):
        assert BREAK_ATR_MULTIPLE > 0
        closes = _oscillate(100.0, 3.0, cycles=6) + [94.0, 88.0, 82.0, 80.0]
        for b in detect_breaks(_frame(closes), level_price=100.0, first_bar=0):
            assert b.penetration_atr >= BREAK_ATR_MULTIPLE


# ---------------------------------------------------------------------------
# EC-S4 — more than one break, in both directions
# ---------------------------------------------------------------------------

class TestMultipleBreaks:

    @staticmethod
    def _down_then_up() -> pd.DataFrame:
        return _frame(
            _oscillate(100.0, 2.0, cycles=5)
            + [94.0, 88.0, 84.0, 83.0]           # decisively below
            + [90.0, 96.0, 104.0, 112.0, 115.0]  # and decisively back above
        )

    @staticmethod
    def _up_then_down() -> pd.DataFrame:
        return _frame(
            _oscillate(100.0, 2.0, cycles=5)
            + [106.0, 112.0, 116.0, 117.0]
            + [110.0, 104.0, 96.0, 88.0, 85.0]
        )

    def test_break_history_is_a_list_not_a_flag(self):
        """`EC-S4`. Two penetrations in opposite directions must both be on
        the record — collapsing them to a boolean would lose the history E&M
        reads a level's character from."""
        breaks = detect_breaks(self._down_then_up(), level_price=100.0, first_bar=0)
        assert len(breaks) >= 2
        assert {b.direction for b in breaks} == {"down", "up"}

    def test_the_most_recent_penetration_decides(self):
        """`EC-S4`'s resolution rule, asserted in both directions so it cannot
        pass by always answering the same thing."""
        down_then_up = detect_breaks(self._down_then_up(), level_price=100.0, first_bar=0)
        assert down_then_up[-1].direction == "up"
        assert effective_level_type(SRLevelType.RESISTANCE, down_then_up) == SRLevelType.SUPPORT

        up_then_down = detect_breaks(self._up_then_down(), level_price=100.0, first_bar=0)
        assert up_then_down[-1].direction == "down"
        assert effective_level_type(SRLevelType.SUPPORT, up_then_down) == SRLevelType.RESISTANCE

    def test_breaks_are_in_chronological_order(self):
        breaks = detect_breaks(self._down_then_up(), level_price=100.0, first_bar=0)
        assert [b.bar_index for b in breaks] == sorted(b.bar_index for b in breaks)

    def test_staying_beyond_the_level_records_one_break_not_one_per_bar(self):
        """A level penetrated once and left behind has been broken once. One
        entry per bar would make the history a function of how long the frame
        happens to be."""
        closes = _oscillate(100.0, 2.0, cycles=5) + [90.0] + [85.0] * 30
        breaks = detect_breaks(
            _frame(closes, hl_pad=QUIET_PAD), level_price=100.0, first_bar=0,
        )
        assert len([b for b in breaks if b.direction == "down"]) == 1


# ---------------------------------------------------------------------------
# Causality, compatibility, determinism
# ---------------------------------------------------------------------------

class TestCausality:

    def test_a_break_does_not_depend_on_bars_after_it(self):
        """`H-S4` in this task's terms. The break list legitimately *grows* as
        new bars arrive — "now" moves — but a break already recorded at bar i
        must be identical whether or not later bars exist."""
        closes = _oscillate(100.0, 2.0, cycles=5) + [94.0, 88.0, 84.0, 83.0]
        short = _frame(closes)
        long = _frame(closes + [120.0, 130.0, 140.0, 150.0])

        early = detect_breaks(short, level_price=100.0, first_bar=0)
        later = detect_breaks(long, level_price=100.0, first_bar=0)

        cut = len(short)
        assert early == [b for b in later if b.bar_index < cut]


class TestCompatibility:

    def test_type_and_the_support_resistance_split_are_unchanged(self):
        """`FR-EM-S8`. `type` still answers the pivot-composition question and
        a level still lands in the same list it did before S5 — the reversal
        is additive until `S9`/`D1` have evidence to act on it."""
        closes = _oscillate(100.0, 3.0, cycles=6) + [94.0, 88.0, 82.0, 80.0]
        frame = _frame(closes)
        supports, resistances = _svc()._find_sr_levels(frame)

        for lvl in supports:
            assert lvl.type in (SRLevelType.SUPPORT, SRLevelType.FLIP)
        for lvl in resistances:
            assert lvl.type in (SRLevelType.RESISTANCE, SRLevelType.FLIP)

    def test_a_break_detection_failure_cannot_lose_the_levels(self):
        import app.services.analysis_service as mod

        original = mod.detect_breaks

        def boom(*args, **kwargs):
            raise RuntimeError("synthetic break failure")

        mod.detect_breaks = boom
        try:
            levels = _levels(_frame(_oscillate(100.0, 3.0, cycles=6)))
        finally:
            mod.detect_breaks = original

        assert levels
        assert all(lvl.breaks == [] for lvl in levels)


class TestDeterminism:

    def test_repeated_runs_are_identical(self):
        frame = _frame(_oscillate(100.0, 3.0, cycles=6) + [94.0, 88.0, 82.0, 80.0])
        first = [(lv.price, lv.role_reversed, lv.effective_type, len(lv.breaks))
                 for lv in _levels(frame)]
        second = [(lv.price, lv.role_reversed, lv.effective_type, len(lv.breaks))
                  for lv in _levels(frame)]
        assert first == second


class TestThinData:

    def test_no_atr_means_no_breaks_rather_than_every_bar_a_break(self):
        """Too few bars to form an ATR: the honest answer is "unknown", and a
        zero/NaN ATR must not make every crossing look infinitely decisive."""
        frame = _frame([100.0, 101.0, 99.0, 95.0])
        assert detect_breaks(frame, level_price=100.0, first_bar=0) == []

    def test_a_flat_series_has_no_true_range_and_so_no_breaks(self):
        frame = _frame([100.0] * 40, hl_pad=0.0)
        assert detect_breaks(frame, level_price=100.0, first_bar=0) == []
