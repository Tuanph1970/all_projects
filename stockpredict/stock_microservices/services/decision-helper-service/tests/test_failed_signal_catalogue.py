"""Backlog #89 — the verdict catalogue, counted honestly.

#89 was raised on a premise I got wrong. `#83` recorded three kinds as
"unmeasured, pending the two-phase cross-service scan `#79` used". They are
not unmeasured pending anything: they are **unreachable by construction**,
established by `#73` and `#78` and already asserted in
`TestDetectorsStillUnreachable`. No scan can reach them.

The same error produced a second one. `#82` and `#83` both described "ten
verdict kinds driving live recommendations", a figure reached by counting
detector functions. The real number is **nine reachable**, and all nine now
have outcome evidence.

So these tests pin the accounting rather than measuring anything new:

* the catalogue partitions into reachable and unreachable with nothing
  unaccounted for;
* every unreachable kind genuinely cannot fire, and says why;
* every reachable kind has been measured, and is recorded as such.

Why bother asserting arithmetic? Because the miscount was not careless — the
shape of this work invited it. Each study found "nothing here", and each time
the unmeasured remainder looked like the place the signal might be hiding. A
machine-readable count removes the invitation.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import List

import pytest

from app.services.signal.base import OHLCVBar
from app.services.signal.failed_signal import (
    ALL_KINDS,
    MEASURED_BY,
    UNREACHABLE,
    adapt_ai_insights_patterns,
    detect_failed_signals,
    reachable_kinds,
)


def _bars(n: int = 60) -> List[OHLCVBar]:
    out, price, day = [], 100.0, date(2023, 1, 2)
    for i in range(n):
        price *= 1.003 if (i // 7) % 2 == 0 else 0.997
        out.append(OHLCVBar(date=day, open=price, high=price * 1.01,
                            low=price * 0.99, close=price, volume=1_000_000))
        day += timedelta(days=1)
    return out


class TestTheCatalogueIsAccountedFor:

    def test_every_kind_is_either_reachable_or_explained(self):
        assert set(UNREACHABLE) | reachable_kinds() == ALL_KINDS
        assert set(UNREACHABLE) & reachable_kinds() == set()

    def test_the_counts_are_what_the_studies_actually_covered(self):
        """Nine reachable, not ten. #82 and #83 both said ten."""
        assert len(ALL_KINDS) == 12
        assert len(UNREACHABLE) == 3
        assert len(reachable_kinds()) == 9

    def test_every_unreachable_kind_states_its_upstream_reason(self):
        for kind, reason in UNREACHABLE.items():
            assert len(reason) > 60, f"{kind}: 'unreachable' needs a reason"
            assert "Backlog #" in reason, f"{kind}: cite where it was established"

    def test_every_reachable_kind_has_been_measured(self):
        """The conclusion worth stating plainly: the catalogue is FULLY
        measured, and the answer is uniform — none of it predicts anything.
        Seven at #83 per kind and per direction, two at #79 over 6,797 causal
        scans."""
        assert set(MEASURED_BY) == reachable_kinds()
        assert set(MEASURED_BY.values()) == {"#79", "#83"}


class TestTheUnreachableKindsReallyCannotFire:
    """Not a restatement of `TestDetectorsStillUnreachable`, which tests the
    adapter. This tests the claim the registry makes: run the detectors over
    real bars with a real adapted payload and assert none of the three
    appears."""

    def test_none_of_them_appears_with_a_full_pattern_payload(self):
        bars = _bars()
        payload = {
            "patterns": [{
                "pattern_name": "Flag", "pattern_type": "bullish",
                "found": True, "confidence": 0.8, "neckline": 101.0,
                "measured_move_target": 110.0, "key_bars": [50, 55, 58, 59],
                "volume_evidence": {},
            }],
            "lookback_bars": len(bars),
        }
        adapted = adapt_ai_insights_patterns(
            payload, last_close=bars[-1].close, bar_index=len(bars) - 1
        )
        results = detect_failed_signals(
            bars, bars[-1].date, patterns=adapted or payload
        )
        fired = {r.kind for r in results}
        assert fired & set(UNREACHABLE) == set(), (
            f"an unreachable kind fired: {fired & set(UNREACHABLE)} — the "
            f"registry is now wrong and #89's accounting with it"
        )

    def test_a_rounding_pattern_name_still_maps_to_nothing(self):
        for name in ("Rounding Top", "Rounding Bottom", "Saucer"):
            out = adapt_ai_insights_patterns({
                "patterns": [{"pattern_name": name, "pattern_type": "bullish",
                              "found": True, "confidence": 0.7,
                              "neckline": 100.0, "key_bars": [1]}],
                "lookback_bars": 60,
            })
            assert out is None or not out.get("patterns")

    def test_nothing_supplies_a_reliability_score(self):
        out = adapt_ai_insights_patterns({
            "patterns": [{"pattern_name": "Double Top", "pattern_type": "bearish",
                          "found": True, "confidence": 0.7, "neckline": 100.0,
                          "key_bars": [50, 55, 58]}],
            "lookback_bars": 60,
        })
        assert out is not None
        for p in out["patterns"]:
            assert "reliability_score" not in p


class TestRemovalIsADeliberateDecision:
    """The three are kept rather than deleted, and the reason is recorded.

    They are dead code today. But each documents a real upstream gap — no
    rounding detector, no reliability score, flags reported mid-formation —
    and deleting them would delete the only machine-checked record of those
    gaps. If ai-insights grows a rounding detector, `ROUNDING_BREAK` becomes
    live and its test starts failing, which is the signal to measure it.

    What the registry removes is the cost of keeping them: they can no longer
    inflate a count of what influences behaviour.
    """

    def test_they_are_still_defined_so_the_gap_stays_visible(self):
        assert set(UNREACHABLE) <= ALL_KINDS

    def test_they_are_excluded_from_any_count_of_live_behaviour(self):
        assert not (set(UNREACHABLE) & set(MEASURED_BY))
        assert not (set(UNREACHABLE) & reachable_kinds())
