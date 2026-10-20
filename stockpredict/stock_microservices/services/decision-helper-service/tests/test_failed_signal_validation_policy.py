"""Backlog #83 — the live path may not act on an unvalidated verdict.

Ten verdict kinds reach `decision/orchestrator.py` and shape what a user is
shown. `#79` measured the two pattern-based ones and found neither predicted
anything — one significantly backwards. `#82` measured the rest *as a group*
in the backtest and found them no better than nothing, but could not say which
kinds carried that.

`#83` measured every pattern-independent kind **per kind and per direction**,
on #79's method: causal scans, non-overlapping forward windows, against the
no-verdict baseline on the same bars, with the edge signed by each verdict's
own directional claim.

**Not one was validated**, and `OPPOSITE_BREAKOUT / LONG` was significantly
backwards at two horizons (t = −2.12 at 20 sessions, −2.06 at 60) — it implied
LONG and price then underperformed.

The policy that follows, and these tests pin it:

* the backwards one is **suppressed**, not capped — a visible verdict still
  tells a user something, and that one tells them something false;
* the rest are **capped below `OVERRIDE_THRESHOLD`**, so none can change a
  recommendation on its own. They are still returned, because "a recent
  formation failed" is a reason to look;
* the cap protects the **live path** and is bypassable for study, so the
  backtest's override flag does not become a silent no-op.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import List

import pytest

from app.services.signal.failed_signal import (
    OVERRIDE_THRESHOLD,
    SUPPRESSED,
    UNVALIDATED_SEVERITY_CAP,
    FailedSignalResult,
    _apply_validation_policy,
    detect_failed_signals,
    highest_severity,
)
from app.services.signal.base import OHLCVBar


def _verdict(kind: str, direction: str, severity: float) -> FailedSignalResult:
    return FailedSignalResult(kind=kind, direction=direction, severity=severity)


def _bars(n: int = 160) -> List[OHLCVBar]:
    """A series with enough shape that several detectors have something to
    fire on — the policy is what is under test, not the detectors."""
    out: List[OHLCVBar] = []
    price, day = 100.0, date(2023, 1, 2)
    for i in range(n):
        price *= 1.004 if (i // 12) % 2 == 0 else 0.996
        wobble = 1.0 + 0.004 * ((i % 5) - 2)
        close = price * wobble
        out.append(OHLCVBar(date=day, open=close, high=close * 1.012,
                            low=close * 0.988, close=close, volume=1_000_000))
        day += timedelta(days=1)
    return out


# ---------------------------------------------------------------------------
# The policy itself
# ---------------------------------------------------------------------------

class TestThePolicy:

    def test_the_cap_sits_below_the_override_threshold(self):
        """The whole point: no unvalidated verdict may override a confirmed
        signal's direction. This is #79's remedy extended to the rest rather
        than a new mechanism."""
        assert UNVALIDATED_SEVERITY_CAP < OVERRIDE_THRESHOLD

    def test_a_high_severity_verdict_is_capped(self):
        out = _apply_validation_policy([_verdict("BULL_TRAP", "SHORT", 0.95)])
        assert len(out) == 1
        assert out[0].severity == pytest.approx(UNVALIDATED_SEVERITY_CAP)

    def test_the_cap_is_recorded_on_the_evidence_not_silent(self):
        """A number that was changed should say so, or a reader of the payload
        cannot tell a measured severity from a policy one."""
        out = _apply_validation_policy([_verdict("FILLED_GAP", "LONG", 0.80)])
        assert out[0].evidence["severity_capped"] is True
        assert "83" in out[0].evidence["capped_reason"]

    def test_a_verdict_already_below_the_cap_is_untouched(self):
        original = _verdict("WRD_RETURN", "LONG", 0.20)
        out = _apply_validation_policy([original])
        assert out[0].severity == pytest.approx(0.20)
        assert "severity_capped" not in out[0].evidence

    def test_the_backwards_verdict_is_suppressed_entirely(self):
        """`OPPOSITE_BREAKOUT / LONG` measured significantly negative at two
        horizons. Capping would leave it visible, and a visible verdict still
        asserts something."""
        assert ("OPPOSITE_BREAKOUT", "LONG") in SUPPRESSED
        out = _apply_validation_policy([_verdict("OPPOSITE_BREAKOUT", "LONG", 0.9)])
        assert out == []

    def test_the_other_direction_of_the_same_kind_survives(self):
        """Only the measured direction is suppressed. `/SHORT` was merely
        unvalidated, and suppressing it too would be acting beyond the
        evidence."""
        out = _apply_validation_policy([_verdict("OPPOSITE_BREAKOUT", "SHORT", 0.9)])
        assert len(out) == 1

    def test_it_is_suppressed_not_inverted(self):
        """Inverting a signal because it measured backwards on one 32-symbol
        sample would be fitting to the sample. Suppression asserts only what
        the measurement supports: showing it is worse than showing nothing."""
        out = _apply_validation_policy([_verdict("OPPOSITE_BREAKOUT", "LONG", 0.9)])
        assert not [r for r in out if r.kind == "OPPOSITE_BREAKOUT"]


# ---------------------------------------------------------------------------
# What it means end to end
# ---------------------------------------------------------------------------

class TestNoVerdictCanOverride:

    def test_nothing_returned_by_the_live_path_can_override(self):
        """The user-visible consequence, asserted on the real detectors rather
        than on hand-built verdicts."""
        bars = _bars()
        for i in range(120, len(bars)):
            for r in detect_failed_signals(bars[: i + 1], bars[i].date):
                assert r.severity < OVERRIDE_THRESHOLD, f"{r.kind} can override"

    def test_the_highest_severity_verdict_still_cannot_override(self):
        bars = _bars()
        tops = [
            highest_severity(detect_failed_signals(bars[: i + 1], bars[i].date))
            for i in range(120, len(bars))
        ]
        assert any(t is not None for t in tops), "fixture produced no verdicts"
        for t in tops:
            if t is not None:
                assert t.severity < OVERRIDE_THRESHOLD

    def test_verdicts_are_still_returned_as_information(self):
        """The remedy is "stop acting on them", not "stop reporting them". A
        recent formation failing is a legitimate reason to look."""
        bars = _bars()
        seen = 0
        for i in range(120, len(bars)):
            seen += len(detect_failed_signals(bars[: i + 1], bars[i].date))
        assert seen > 0


class TestTheStudySeamIsNotASilentNoOp:

    def test_a_study_can_opt_out_of_the_policy(self):
        """The cap protects the live path. A measurement that wants the
        pre-#83 behaviour must be able to get it, or the backtest's override
        flag would silently do nothing — the trap this codebase has paid for
        in EM-1's sweep, #78 and #84's walk-forward."""
        bars = _bars()
        capped = uncapped = 0
        for i in range(120, len(bars)):
            capped += sum(
                1 for r in detect_failed_signals(bars[: i + 1], bars[i].date)
                if r.severity >= OVERRIDE_THRESHOLD
            )
            uncapped += sum(
                1 for r in detect_failed_signals(
                    bars[: i + 1], bars[i].date, apply_validation_policy=False
                )
                if r.severity >= OVERRIDE_THRESHOLD
            )
        assert capped == 0
        assert uncapped > 0, "the opt-out changed nothing — it is a no-op"

    def test_the_backtest_bypasses_the_cap_when_the_override_is_enabled(self):
        import inspect

        from app.services.backtest import harness

        src = inspect.getsource(harness.run_backtest_on_bars)
        assert "apply_validation_policy=False" in src
