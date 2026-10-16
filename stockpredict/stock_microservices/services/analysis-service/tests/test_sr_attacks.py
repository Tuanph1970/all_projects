"""EM-2 / S6 — attack count (`FR-EM-S4`), and the third-attack prediction.

Edwards & Magee, Ch 13: each repelled attack consumes some of a level's
power, and

    "it is an odds-on assumption that a third attack at a Resistance Level
    will succeed in penetrating it."

Two separate things, and the plan is emphatic that they must not be
conflated:

1. **The count** — how many approaches were repelled without breaking
   through. That is a measurement, and it ships either way as evidence.
2. **The weighting** — whether strength should *decrease* with that count.
   That rests on E&M's prediction being true of VN data, which `H-S3`
   measures against a coin flip. **If the third attack is not odds-on, the
   weighting does not ship.** A negative result is the result.

This file covers (1). The study for (2) lives in `tests/sr_attack_study.py`
and its verdict is recorded in the plan.

Vocabulary, shared with S5 and the hit-rate harness
---------------------------------------------------
An **approach** is a close coming within `ATTACK_PROXIMITY_ATR` x ATR of the
level, from the side the level is defending. It resolves as whichever comes
first: a **penetration** (a close beyond the level by `BREAK_ATR_MULTIPLE` x
ATR in the direction that counts) or a **repulsion** (a close back on the
defending side by at least the proximity distance). Those two regions are
disjoint by construction, so no approach is ever both.

Everything is in ATR multiples rather than percentages, for the reason EM-9
established and `S5` already encodes — a fixed percentage judges a quiet large
cap and a volatile small cap on the same scale, and they do not live on one.
"""
from __future__ import annotations

from typing import List
from unittest.mock import MagicMock

import pandas as pd
import pytest

from app.models.schemas import SRLevel, SRLevelType
from app.services.analysis_service import AnalysisService
from app.services.sr_volume import (
    ATTACK_PROXIMITY_ATR,
    LevelAttack,
    detect_attacks,
)

QUIET_PAD = 3.0


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


#: Bars of lead-in before any approach. Wilder's ATR has `min_periods=14`, so
#: a fixture shorter than that leaves the band undefined on nearly every bar
#: and the detector correctly reports nothing. The lead-in oscillates with a
#: similar amplitude to the approach legs — a flat one would warm the ATR to
#: near zero and make the proximity band meaninglessly tight — and stays far
#: enough from the level that it never registers as an approach itself.
ATR_LEAD_IN = 30


def _approach_and_retreat(level: float, times: int, depth: float = 0.3,
                          retreat: float = 6.0) -> List[float]:
    """`times` approaches from below that get turned away each time."""
    out: List[float] = []
    for i in range(ATR_LEAD_IN):
        out.append(level - retreat - (3.0 if i % 2 else 0.0))
    for _ in range(times):
        out += [level - retreat, level - retreat / 2, level - depth,
                level - retreat / 2, level - retreat]
    return out


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
# Schema
# ---------------------------------------------------------------------------

class TestSchema:

    def test_srlevel_carries_an_attack_count(self):
        assert "attacks" in SRLevel.model_fields

    def test_attacks_defaults_to_zero_and_is_additive(self):
        from app.models.schemas import SRTouch, SwingType

        lvl = SRLevel(
            price=100.0, type=SRLevelType.SUPPORT, strength=1, age_bars=0,
            touches=[SRTouch(bar_index=0, date="2026-01-01", price=100.0,
                             pivot_type=SwingType.LOW)],
        )
        assert lvl.attacks == 0

    def test_levels_report_a_non_negative_count(self):
        frame = _frame(_approach_and_retreat(100.0, times=3), hl_pad=0.4)
        for lvl in _levels(frame):
            assert lvl.attacks >= 0


# ---------------------------------------------------------------------------
# FR-EM-S4 — counting approaches that were turned away
# ---------------------------------------------------------------------------

class TestAttackCount:

    def test_three_approaches_that_are_turned_away_count_as_three(self):
        frame = _frame(_approach_and_retreat(100.0, times=3))
        attacks = detect_attacks(
            frame, level_price=100.0, first_bar=0,
            declared_type=SRLevelType.RESISTANCE,
        )
        assert len([a for a in attacks if not a.penetrated]) == 3

    def test_an_approach_that_breaks_through_is_not_an_attack(self):
        """E&M's attack is a *repelled* approach. One that succeeds is a
        penetration and belongs to the break history, not the attack count —
        otherwise the two measures would double-count the same event."""
        closes = _approach_and_retreat(100.0, times=2) + [100.5, 104.0, 108.0, 110.0]
        attacks = detect_attacks(
            _frame(closes), level_price=100.0, first_bar=0,
            declared_type=SRLevelType.RESISTANCE,
        )
        assert len([a for a in attacks if not a.penetrated]) == 2
        assert any(a.penetrated for a in attacks)

    def test_an_approach_is_counted_once_not_once_per_bar(self):
        """A level price loiters near for twenty bars has been attacked once.
        One entry per bar would make the count a function of how long price
        happened to dawdle."""
        closes = [94.0] + [99.7] * 20 + [94.0, 92.0]
        attacks = detect_attacks(
            _frame(closes), level_price=100.0, first_bar=0,
            declared_type=SRLevelType.RESISTANCE,
        )
        assert len(attacks) == 1

    def test_price_that_never_comes_close_is_not_an_attack(self):
        closes = [80.0, 82.0, 81.0, 79.0] * 10
        assert detect_attacks(
            _frame(closes), level_price=100.0, first_bar=0,
            declared_type=SRLevelType.RESISTANCE,
        ) == []

    def test_attacks_are_in_chronological_order(self):
        frame = _frame(_approach_and_retreat(100.0, times=4))
        attacks = detect_attacks(
            frame, level_price=100.0, first_bar=0,
            declared_type=SRLevelType.RESISTANCE,
        )
        assert [a.bar_index for a in attacks] == sorted(a.bar_index for a in attacks)

    def test_the_proximity_threshold_is_in_atr_multiples(self):
        """The EM-9 lesson again, and the S5 precedent: identical closes, a
        different intrabar range, and the verdict must be allowed to differ.
        A percentage could not express this."""
        assert ATTACK_PROXIMITY_ATR > 0
        closes = _approach_and_retreat(100.0, times=3, depth=2.0)
        tight = detect_attacks(
            _frame(closes, hl_pad=0.4), level_price=100.0, first_bar=0,
            declared_type=SRLevelType.RESISTANCE,
        )
        wide = detect_attacks(
            _frame(closes, hl_pad=QUIET_PAD), level_price=100.0, first_bar=0,
            declared_type=SRLevelType.RESISTANCE,
        )
        assert len(tight) != len(wide)


# ---------------------------------------------------------------------------
# Causality, thin data, determinism
# ---------------------------------------------------------------------------

class TestCausality:

    def test_an_attack_does_not_depend_on_bars_after_it(self):
        """`H-S4`. The list legitimately grows as bars arrive, but an entry
        already recorded must not change."""
        closes = _approach_and_retreat(100.0, times=3)
        short = _frame(closes)
        long = _frame(closes + [100.5, 106.0, 112.0, 120.0])

        early = detect_attacks(short, level_price=100.0, first_bar=0,
                               declared_type=SRLevelType.RESISTANCE)
        later = detect_attacks(long, level_price=100.0, first_bar=0,
                               declared_type=SRLevelType.RESISTANCE)
        cut = len(short)
        assert early == [a for a in later if a.bar_index < cut]


class TestThinData:

    def test_too_few_bars_for_an_atr_yields_no_attacks(self):
        assert detect_attacks(
            _frame([99.8, 100.1, 99.9]), level_price=100.0, first_bar=0,
            declared_type=SRLevelType.RESISTANCE,
        ) == []

    def test_a_flat_series_has_no_true_range_and_so_no_attacks(self):
        assert detect_attacks(
            _frame([100.0] * 40, hl_pad=0.0), level_price=100.0, first_bar=0,
            declared_type=SRLevelType.RESISTANCE,
        ) == []

    def test_an_attack_failure_cannot_lose_the_levels(self):
        import app.services.analysis_service as mod

        original = mod.detect_attacks

        def boom(*args, **kwargs):
            raise RuntimeError("synthetic attack failure")

        mod.detect_attacks = boom
        try:
            levels = _levels(_frame(_approach_and_retreat(100.0, times=3)))
        finally:
            mod.detect_attacks = original

        assert levels
        assert all(lvl.attacks == 0 for lvl in levels)


class TestDeterminism:

    def test_repeated_runs_are_identical(self):
        frame = _frame(_approach_and_retreat(100.0, times=3))
        a = detect_attacks(frame, level_price=100.0, first_bar=0,
                           declared_type=SRLevelType.RESISTANCE)
        b = detect_attacks(frame, level_price=100.0, first_bar=0,
                           declared_type=SRLevelType.RESISTANCE)
        assert a == b
        assert all(isinstance(x, LevelAttack) for x in a)


# ---------------------------------------------------------------------------
# H-S3's verdict, pinned
# ---------------------------------------------------------------------------

class TestTheWeightingDidNotShip:
    """`H-S3` measured E&M's third-attack claim and it does not hold.

    On 43,316 levels / 262k approaches of real VN daily bars
    (`tests/sr_attack_study.py`):

        1st approach     26.4% penetrated   z = -93.1
        2nd              40.2%              z = -35.7
        3rd              42.3%              z = -26.4
        4th or later     39.5%              z = -84.1

    E&M predict the third attack is *odds-on* — above 50%. It is 42.3%,
    significantly below a coin flip. `FR-EM-S4` and the plan both
    pre-registered the consequence: **if the third attack is not odds-on, the
    weighting does not ship and the count stays as evidence.**

    These tests pin that decision. They exist because the tempting move, on
    seeing the strongly monotone 26.4 -> 40.2 -> 42.3 gradient, is to decide
    after the fact that the *direction* was the real claim and ship a
    weighting anyway. That is choosing the criterion after seeing the data,
    which is the thing the pre-registration existed to prevent.
    """

    def test_strength_is_not_reduced_by_the_attack_count(self):
        """`strength` stays the touch count. No attack-derived discount."""
        frame = _frame(_approach_and_retreat(100.0, times=4))
        for lvl in _levels(frame):
            assert lvl.strength == len(lvl.touches)

    def test_volume_strength_is_not_reduced_by_the_attack_count(self):
        """The same for the EM-2 measure: whatever `attacks` says, it must
        not have been folded into `volume_strength`."""
        import app.services.sr_volume as srv

        frame = _frame(_approach_and_retreat(100.0, times=4))
        for lvl in _levels(frame):
            if lvl.volume_strength is None:
                continue
            expected = srv.aggregate_level_volume(
                frame, [t.bar_index for t in lvl.touches], level_price=lvl.price,
            ).value
            assert lvl.volume_strength == pytest.approx(expected), (
                "volume_strength has been adjusted by something other than "
                "volume — H-S3 did not license an attack weighting"
            )

    def test_no_attack_weighting_helper_is_exported(self):
        """A belt-and-braces guard: if a later session adds the weighting, it
        has to delete this test deliberately and say why in the commit."""
        import app.services.sr_volume as srv

        for name in dir(srv):
            assert "attack_weight" not in name.lower(), (
                f"{name} looks like the weighting H-S3 refused to license"
            )
