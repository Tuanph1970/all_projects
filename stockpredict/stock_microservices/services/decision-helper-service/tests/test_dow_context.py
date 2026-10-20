"""EM-6 D2 — adopting the primary trend only when a witness confirms it.

The composition the Phase-2 plan settled (§1), after the SRS left `FR-EM-D4`
(confirm a *turn*) and `FR-EM-D5` (check a *state*) unrelated:

> The witness governs how a lead turn is **adopted**; the gate then checks a
> signal against the adopted trend. A lead turn is adopted only once a witness
> confirms it, within `k` bars — and if none does, **the turn is not adopted
> and the previous trend stands**, which is tenet 12 rather than a special
> case invented for the code.

Two layers, tested separately on purpose: `adopt_turns` is the subtle part and
is exercised with literal trend sequences so the intent is visible, while
`market_context_series` is tested for calendar alignment, availability and
code validation.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, List, Optional, Sequence

import pytest

from app.services.market_context import dow_context
from app.services.market_context.dow import TREND_DOWN, TREND_UP, UNDEFINED, swing_trend_series
from app.services.market_context.dow_context import (
    DEFAULT_LAG_BARS,
    DEFAULT_MAX_STALE_DAYS,
    EXCLUDED_INDICES,
    LEAD_INDEX,
    WITNESS_INDICES,
    ExcludedWitnessError,
    adopt_turns,
    market_context_series,
)
from app.services.signal.base import OHLCVBar

U, D, X = TREND_UP, TREND_DOWN, UNDEFINED


def _w(*series: Sequence[Optional[str]]) -> Dict[str, List[Optional[str]]]:
    return {f"W{i}": list(s) for i, s in enumerate(series)}


# ---------------------------------------------------------------------------
# adopt_turns — the confirmation rule
# ---------------------------------------------------------------------------

class TestConfirmation:

    def test_a_turn_a_witness_already_agrees_with_is_adopted_at_once(self):
        assert adopt_turns([X, X, U, U], _w([D, D, U, U]), k=0) == [X, X, U, U]

    def test_a_turn_no_witness_confirms_on_the_day_is_not_adopted_when_k_is_zero(self):
        assert adopt_turns([X, U, U, U], _w([D, D, D, U]), k=0) == [X, X, X, X]

    def test_the_same_turn_is_adopted_late_when_the_window_allows_it(self):
        """E&M: the averages *need not confirm on the same day*."""
        assert adopt_turns([X, U, U, U], _w([D, D, D, U]), k=5) == [X, X, X, U]

    def test_adoption_happens_at_the_confirming_bar_not_the_turn_bar(self):
        out = adopt_turns([X, U, U, U, U], _w([D, D, D, U, U]), k=5)
        assert out[1] == X and out[2] == X, "not before the witness agrees"
        assert out[3] == U, "at the bar the witness agreed"


class TestTenet12:

    def test_an_unconfirmed_turn_leaves_the_previous_trend_standing(self):
        """The heart of D2, and the reason `UNDEFINED` is wrong here.

        The lead turns UP at bar 2 and no witness ever agrees. The adopted
        trend must remain DOWN — the state established earlier — rather than
        flipping to UP or being cleared.
        """
        lead = [D, D, U, U, U, U]
        out = adopt_turns(lead, _w([D, D, D, D, D, D]), k=1)
        assert out == [D, D, D, D, D, D]

    def test_an_expired_turn_is_not_resurrected_by_a_later_agreement(self):
        """A deliberate consequence of bounding the window, pinned here.

        E&M set no limit on how late an average may confirm, but the witness
        study measured that HNX eventually confirms 98% of VNINDEX turns — so
        an unbounded window would make the gate nearly inert. `k` is that
        bound, and once it lapses the signal is stale: the witness turning UP
        at bar 4 is not a confirmation of the turn that happened at bar 1.
        """
        out = adopt_turns([X, U, U, U, U, U], _w([D, D, D, D, U, U]), k=1)
        assert out == [X] * 6


class TestHowManyWitnessesMustAgree:

    def test_one_witness_is_enough_by_default(self):
        out = adopt_turns([X, U, U], _w([D, U, U], [D, D, D]), k=5, required=1)
        assert out == [X, U, U]

    def test_unanimity_waits_for_the_slower_witness(self):
        out = adopt_turns([X, U, U, U], _w([D, U, U, U], [D, D, U, U]),
                          k=5, required=2)
        assert out == [X, X, U, U]


class TestAvailability:

    def test_with_no_witness_available_the_lead_is_adopted_unchanged(self):
        """EC-D1 fail-open, at the logic layer.

        A data outage must never look like a quiet market. Asserted as
        equality with the lead, not as "roughly the same".
        """
        lead = [X, U, U, D, D]
        assert adopt_turns(lead, _w([None] * 5), k=0) == lead

    def test_with_no_witnesses_configured_at_all_the_lead_is_adopted_unchanged(self):
        lead = [X, U, U, D, D]
        assert adopt_turns(lead, {}, k=0) == lead

    def test_unanimity_asks_only_the_witnesses_that_are_available(self):
        """Requiring two of two when only one is reporting would suppress on
        an outage, which is EC-D1's failure mode wearing a different hat."""
        out = adopt_turns([X, U, U], _w([D, U, U], [None, None, None]),
                          k=5, required=2)
        assert out == [X, U, U]


class TestTheLagWindow:

    def test_k_is_read_at_call_time_not_frozen_at_import(self, monkeypatch):
        """H-D5 again. Sixth instance of this trap in the project."""
        lead, wit = [X, U, U, U], _w([D, D, D, U])
        assert adopt_turns(lead, wit)[-1] == U          # default k = 5 confirms

        monkeypatch.setattr(dow_context, "DEFAULT_LAG_BARS", 0)
        assert adopt_turns(lead, wit)[-1] == X, (
            "DEFAULT_LAG_BARS is not being read at call time"
        )

    def test_a_wider_window_never_adopts_less(self):
        lead, wit = [X, U, U, U, U, U], _w([D, D, D, D, U, U])
        narrow = adopt_turns(lead, wit, k=0)
        wide = adopt_turns(lead, wit, k=10)
        assert sum(s != X for s in wide) >= sum(s != X for s in narrow)

    def test_every_bar_gets_exactly_one_reading(self):
        assert len(adopt_turns([X, U, U], _w([D, U, U]), k=1)) == 3


class TestStrictnessIsStickiness:
    """A stricter gate does not mean a more bearish one — it means a more
    PERSISTENT one, and that is the hazard this class guards.

    Adoption blocks *turns*, so rejecting a DOWN turn leaves the previous UP
    standing. On 20 years of real VN indices, `UNANIMOUS_3` with k <= 5 adopts
    only 5 turns and holds one state for 3,911 bars — about 15 years. That is
    not a strict market context, it is a constant one, and a constant is as
    useless as an inert gate. `D6` therefore sweeps k over {0, 10, 20, 60} and
    carries a degeneracy criterion alongside the vacuity guard.
    """

    def _turns(self, series):
        return sum(1 for a, b in zip(series, series[1:]) if a != b)

    def test_requiring_more_witnesses_never_adopts_more_turns(self):
        lead = [X, U, U, D, D, U, U, D, D, U, U]
        wit = _w([X, U, D, D, U, U, D, D, U, U, U],
                 [X, D, D, D, D, U, U, U, D, D, U])
        loose = adopt_turns(lead, wit, k=3, required=1)
        strict = adopt_turns(lead, wit, k=3, required=2)
        assert self._turns(strict) <= self._turns(loose)

    def test_a_rejected_down_turn_leaves_the_market_reading_up(self):
        """Stated as a test because it reads as a bug the first time it is
        seen in a backtest: a stricter gate produced MORE long exposure."""
        lead = [U, U, D, D, D]
        out = adopt_turns(lead, _w([U, U, U, U, U]), k=1)
        assert out == [U, U, U, U, U]


# ---------------------------------------------------------------------------
# market_context_series — calendars, availability, validation
# ---------------------------------------------------------------------------

def _legs(points: Sequence[float], bars_per_leg: int = 10,
          start: date = date(2020, 1, 1), step: int = 1) -> List[OHLCVBar]:
    closes = [float(points[0])]
    for a, b in zip(points, points[1:]):
        for j in range(1, bars_per_leg + 1):
            closes.append(a + (b - a) * j / bars_per_leg)
    day = start
    bars = []
    for c in closes:
        bars.append(OHLCVBar(date=day, open=c, high=c * 1.2, low=c * 0.8,
                             close=c, volume=1_000_000))
        day += timedelta(days=step)
    return bars


UP_POINTS = [100, 120, 105, 130, 112, 140]
DOWN_POINTS = [100, 80, 88, 70, 76]


class TestFailOpen:

    def test_no_witnesses_reproduces_the_lead_exactly(self):
        """EC-D1 at the integration layer, and the strongest form of it:
        byte-for-byte equality with the ungated trend."""
        lead = _legs(UP_POINTS)
        ctx = market_context_series(lead, {})
        assert [c.adopted_trend for c in ctx] == swing_trend_series(lead)
        assert all(c.status == "SKIP_NO_WITNESS" for c in ctx)

    def test_a_witness_that_has_not_listed_yet_does_not_block_the_lead(self):
        """HNX starts in 2005 and UPCOM in 2009 while VNINDEX starts in 2004,
        so this is the real history, not a hypothetical."""
        lead = _legs(UP_POINTS)
        late = _legs(DOWN_POINTS, start=lead[40].date)
        ctx = market_context_series(lead, {"HNXINDEX": late})
        early = [c for c in ctx if c.date < late[0].date]
        assert early and all(c.status == "SKIP_NO_WITNESS" for c in early)
        assert [c.adopted_trend for c in early] == swing_trend_series(lead)[:len(early)]


class TestStaleness:

    def test_a_missing_day_carries_the_last_witness_reading(self):
        lead = _legs(UP_POINTS)
        witness = [b for i, b in enumerate(_legs(UP_POINTS)) if i % 2 == 0]
        ctx = market_context_series(lead, {"HNXINDEX": witness})
        assert all(c.status == "OK" for c in ctx[2:])

    def test_a_witness_that_stops_reporting_becomes_unavailable(self):
        """EC-D2. Beyond the staleness bound it is treated as absent, which
        routes it into EC-D1 rather than letting a months-old reading vote."""
        lead = _legs(UP_POINTS)
        witness = _legs(DOWN_POINTS)[:5]
        ctx = market_context_series(lead, {"HNXINDEX": witness},
                                    max_stale_days=3)
        assert ctx[-1].status == "SKIP_NO_WITNESS"
        assert [c.adopted_trend for c in ctx] == swing_trend_series(lead)

    def test_the_staleness_bound_is_read_at_call_time(self, monkeypatch):
        lead = _legs(UP_POINTS)
        witness = _legs(DOWN_POINTS)[:5]
        monkeypatch.setattr(dow_context, "DEFAULT_MAX_STALE_DAYS", 3)
        assert market_context_series(lead, {"HNXINDEX": witness})[-1].status == "SKIP_NO_WITNESS"


class TestWitnessCodes:

    def test_vn30_is_rejected_and_the_message_says_why(self):
        """EC-D5 + FR-EM-D3. VN30 is 0.965-correlated with VNINDEX and
        confirms with a median lag of 0 bars — a witness that agrees with
        everything. The exclusion is a measurement, so the error carries it."""
        lead = _legs(UP_POINTS)
        with pytest.raises(ExcludedWitnessError) as exc:
            market_context_series(lead, {"VN30": _legs(UP_POINTS)})
        assert "0.965" in str(exc.value)

    def test_an_excluded_witness_can_still_be_measured_deliberately(self):
        lead = _legs(UP_POINTS)
        ctx = market_context_series(lead, {"VN30": _legs(UP_POINTS)},
                                    allow_excluded=True)
        assert len(ctx) == len(lead)

    def test_the_allow_list_matches_what_the_study_established(self):
        assert LEAD_INDEX == "VNINDEX"
        assert set(WITNESS_INDICES) == {"HNXINDEX", "UPCOMINDEX"}
        assert set(EXCLUDED_INDICES) == {"VN30", "HNX30"}

    def test_an_unknown_code_is_rejected_rather_than_guessed(self):
        lead = _legs(UP_POINTS)
        with pytest.raises(ExcludedWitnessError):
            market_context_series(lead, {"NOT_AN_INDEX": _legs(UP_POINTS)})


class TestAgreementReporting:

    def test_disagreeing_witnesses_are_named(self):
        """FR-EM-D6 needs them by name: the penalty mode must say which
        indices dissented, not merely that something did."""
        lead = _legs(UP_POINTS)
        ctx = market_context_series(lead, {"HNXINDEX": _legs(DOWN_POINTS)})
        last = ctx[-1]
        assert last.lead_trend == TREND_UP
        assert "HNXINDEX" in last.disagreeing
        assert "HNXINDEX" not in last.agreeing


class TestCausalityAndDeterminism:

    def test_appending_future_bars_changes_no_past_reading(self):
        lead, wit = _legs(UP_POINTS), _legs(UP_POINTS)
        before = market_context_series(lead, {"HNXINDEX": wit})

        more_lead = lead + _legs([140, 90, 95], start=lead[-1].date + timedelta(days=1))
        more_wit = wit + _legs([140, 90, 95], start=wit[-1].date + timedelta(days=1))
        after = market_context_series(more_lead, {"HNXINDEX": more_wit})

        assert ([c.adopted_trend for c in after[:len(before)]]
                == [c.adopted_trend for c in before])

    def test_repeated_runs_are_identical(self):
        lead, wit = _legs(UP_POINTS), _legs(DOWN_POINTS)
        a = market_context_series(lead, {"HNXINDEX": wit})
        b = market_context_series(lead, {"HNXINDEX": wit})
        assert [c.adopted_trend for c in a] == [c.adopted_trend for c in b]

    def test_an_empty_lead_is_inert(self):
        assert market_context_series([], {"HNXINDEX": _legs(UP_POINTS)}) == []


class TestDefaults:

    def test_the_shipped_defaults_are_the_registered_ones(self):
        assert DEFAULT_LAG_BARS == 5
        assert DEFAULT_MAX_STALE_DAYS == 10
