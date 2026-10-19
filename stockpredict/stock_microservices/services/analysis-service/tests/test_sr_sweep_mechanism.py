"""EM-2 / W1 — the sweep's override mechanism must actually override.

This file is the anti-trap guard, and it is the reason W1 can be believed.

The plan names the trap twice because the workstream has paid for it twice
(EM-1 `S2`'s `confirm_rvol`, Backlog `#78`'s `MAX_PATTERN_AGE_BARS`):

    A parameter read as a DEFAULT ARGUMENT is bound at function-definition
    time, so patching the module constant afterwards does nothing. The sweep
    comes back perfectly flat, and a flat sweep reads as "this parameter does
    not matter" when it means "the harness never varied it".

In `sr_volume` it is worse than uniform — it is **mixed**. `MAX_CONGESTION_BARS`
is read inside a function body, so patching the module attribute works; every
other threshold is a default argument on a function `_find_sr_levels` calls
without passing it, so patching the module attribute is a no-op. A naive sweep
would show one parameter responding and seven flat: the most misleading output
available.

So two things are asserted here, fast and on synthetic data:

1. **The trap is real**, parameter by parameter — patching the module constant
   alone does not change `_find_sr_levels`' output. If this ever starts
   failing, somebody has refactored the constants to body reads and the sweep
   machinery can be simplified; that is good news, but it must be a deliberate
   change rather than a silent one.
2. **The override works**, parameter by parameter — `sr_sweep.override` does
   change the output. A parameter that cannot be moved here will read as flat
   in the sweep, and this test says so in seconds instead of hours.
"""
from __future__ import annotations

from typing import Any, List
from unittest.mock import MagicMock

import pandas as pd
import pytest

import app.services.sr_volume as srv
from app.services.analysis_service import AnalysisService
from tests.sr_sweep import GRIDS, INERT_FOR_HS1, override


def _frame() -> pd.DataFrame:
    """A series with pivots, a congestion, an excursion and a return — enough
    structure that every threshold has something to bite on."""
    closes: List[float] = []
    for i in range(8):
        closes += [100.0, 101.8 + i * 0.05, 100.0, 98.2 - i * 0.05, 100.0]
    closes += [100.0 - 2.5 * k for k in range(1, 8)]          # excursion down
    closes += [82.0 + 1.3 * k for k in range(1, 18)]          # and back up
    for i in range(6):
        closes += [104.0, 105.6 + i * 0.05, 104.0, 102.4, 104.0]
    return pd.DataFrame({
        "open": closes,
        "high": [c + 0.5 for c in closes],
        "low": [c - 0.5 for c in closes],
        "close": closes,
        "volume": [
            900_000.0 * (3.0 if abs(c - 100.0) < 2.0 else 1.0) for c in closes
        ],
    })


def _fingerprint(frame: pd.DataFrame) -> tuple:
    """Everything a threshold could plausibly move, in one comparable value."""
    supports, resistances = AnalysisService(session=MagicMock())._find_sr_levels(frame)
    out = []
    for lvl in list(supports) + list(resistances):
        out.append((
            round(lvl.price, 6),
            lvl.volume_strength,
            lvl.price_cog,
            lvl.adjusted_strength,
            lvl.age_decay,
            lvl.excursion_pct,
            lvl.distance_suppressed,
            lvl.attacks,
            len(lvl.breaks),
            lvl.effective_type,
        ))
    return tuple(out)


#: The two settings per parameter that the mechanism test pushes between —
#: chosen as the extremes of each sweep grid, so if these do not move the
#: output nothing in the grid will.
EXTREMES = {name: (grid[0], grid[-1]) for name, grid in GRIDS.items()}


@pytest.mark.parametrize("name", sorted(EXTREMES))
def test_the_override_actually_changes_the_output(name: str):
    """Guard (2). A parameter that cannot be moved here will read as flat in
    the sweep, and a flat sweep is a harness smell rather than a finding."""
    frame = _frame()
    low, high = EXTREMES[name]

    with override(**{name: low}):
        a = _fingerprint(frame)
    with override(**{name: high}):
        b = _fingerprint(frame)

    assert a != b, (
        f"override({name}=...) did not change _find_sr_levels' output; the "
        f"sweep would report this parameter as flat and that would be a "
        f"harness bug, not a result"
    )


@pytest.mark.parametrize("name", sorted(EXTREMES))
def test_patching_the_module_constant_alone_is_not_enough(name: str):
    """Guard (1) — the trap, asserted so it cannot quietly stop being true.

    `MAX_CONGESTION_BARS` is the documented exception: it is read in a
    function body, so the module patch does reach it.
    """
    frame = _frame()
    low, high = EXTREMES[name]
    baseline = _fingerprint(frame)

    def _patched(value: Any) -> tuple:
        original = getattr(srv, name)
        setattr(srv, name, value)
        try:
            return _fingerprint(frame)
        finally:
            setattr(srv, name, original)

    moved = _patched(low) != baseline or _patched(high) != baseline

    if name == "MAX_CONGESTION_BARS":
        assert moved, (
            "MAX_CONGESTION_BARS is read in congestion_span's body, so a "
            "module patch should reach it"
        )
    else:
        assert not moved, (
            f"{name} now responds to a module patch, so it is no longer a "
            f"bound default argument. Good — but update sr_sweep's "
            f"_KEYWORD_TARGETS and this test deliberately rather than "
            f"leaving the machinery more complicated than it needs to be."
        )


def test_every_threshold_is_either_swept_or_documented_as_inert():
    """`FR-EM-S10` says *every* number is swept. A threshold may be left out
    of the grid only with a written reason, so a later addition cannot be
    quietly forgotten."""
    from tests.sr_sweep import _KEYWORD_TARGETS

    accounted = set(GRIDS) | set(INERT_FOR_HS1)
    assert accounted == set(_KEYWORD_TARGETS), (
        "a threshold is neither swept nor documented as inert: "
        f"{accounted ^ set(_KEYWORD_TARGETS)}"
    )
    for name, grid in GRIDS.items():
        assert len(grid) >= 3, f"{name}: a sweep needs at least three settings"
        assert len(set(map(str, grid))) == len(grid), f"{name}: duplicate settings"
    for name, reason in INERT_FOR_HS1.items():
        assert len(reason) > 80, f"{name}: 'inert' needs a real explanation"


def test_the_congestion_guard_still_works_even_though_it_is_inert():
    """`MAX_CONGESTION_BARS` cannot move `H-S1` because `S4` calls the
    primitives per touch, so spans are tiny. It is still the guard `S1` built,
    and this proves it has not quietly stopped guarding."""
    from app.services.sr_volume import congestion_span

    frame = _frame()
    mid = len(frame) // 2
    original = srv.MAX_CONGESTION_BARS
    try:
        srv.MAX_CONGESTION_BARS = 15
        assert congestion_span(frame, [mid], window=3) is not None, (
            "a per-touch span must still be measured"
        )
        assert congestion_span(frame, [mid], window=30) is None, (
            "a span far wider than the guard must still be refused"
        )
    finally:
        srv.MAX_CONGESTION_BARS = original


def test_attack_proximity_still_moves_the_attack_count():
    """`ATTACK_PROXIMITY_ATR` is inert for `H-S1` because nothing consumes
    `attacks`. It must still move `attacks` itself, or the field is broken
    rather than merely unused."""
    frame = _frame()
    with override(ATTACK_PROXIMITY_ATR=0.25):
        tight = [x[7] for x in _fingerprint(frame)]
    with override(ATTACK_PROXIMITY_ATR=3.0):
        loose = [x[7] for x in _fingerprint(frame)]
    assert tight != loose


def test_every_parameter_has_a_declared_arm_of_effect():
    """`is_flat` is the sweep's bug signal, and it only works if it is asked
    about the arm the parameter actually feeds. `BREAK_ATR_MULTIPLE` moves
    `em2_role` and leaves `em2_adjusted` identical, so checking the wrong arm
    would raise a false alarm and discredit the real ones."""
    from tests.sr_sweep import ARM_OF_EFFECT

    assert set(ARM_OF_EFFECT) == set(GRIDS), (
        f"arm-of-effect and grid disagree: {set(ARM_OF_EFFECT) ^ set(GRIDS)}"
    )


def test_the_constants_the_sweep_knows_about_are_the_ones_that_exist():
    """Catches a renamed or deleted constant before the sweep silently stops
    covering it."""
    for name in GRIDS:
        assert hasattr(srv, name), f"sr_volume has no {name}"


def test_the_neighbourhood_default_can_produce_a_legal_span():
    """The one defect `W1` found, pinned.

    A per-touch NEIGHBOURHOOD span is `window + 1` bars. At
    `DEFAULT_NEIGHBOURHOOD = 1` that is 2 bars, below
    `MIN_CONGESTION_BARS = 3`, so `congestion_span` refuses every touch and
    `volume_strength` / `price_cog` / `adjusted_strength` all come back None
    for every level — with no error raised anywhere. The EM-2 arms just vanish.

    `sr_volume` now asserts the relationship at import; this test states it in
    the suite so the reason survives.
    """
    assert srv.DEFAULT_NEIGHBOURHOOD + 1 >= srv.MIN_CONGESTION_BARS


def test_a_too_small_neighbourhood_disables_the_volume_path():
    """Demonstrates the failure the guard prevents, so the guard is not
    mistaken for superstition."""
    from app.services.sr_volume import congestion_span

    frame = _frame()
    mid = len(frame) // 2
    assert congestion_span(frame, [mid], window=1) is None
    assert congestion_span(frame, [mid], window=srv.DEFAULT_NEIGHBOURHOOD) is not None
