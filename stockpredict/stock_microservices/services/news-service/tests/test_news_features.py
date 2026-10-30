"""Backlog #106 — news as decayed PAST covariates: intensity and polarity.

Harnesses that must exist alongside the code (CLAUDE.md): a no-leakage causality
test, and a property test rather than an assertion on simulator magnitudes.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

import pytest

from app.features.news_features import (
    DEFAULT_HALFLIFE_DAYS,
    NewsFeatureRow,
    NewsItemPoint,
    daily_news_features,
    halflife_from_decay,
    is_trustworthy_score,
    session_date_for,
)


def _at(y, m, d, hh=2, mm=0, score=0.5, source="model") -> NewsItemPoint:
    return NewsItemPoint(
        ts_utc=datetime(y, m, d, hh, mm, tzinfo=timezone.utc),
        sentiment_score=score, score_source=source,
    )


# ---------------------------------------------------------------------------
# 3. publication-time discipline
# ---------------------------------------------------------------------------

def test_an_item_during_the_session_belongs_to_that_session():
    # 02:00 UTC = 09:00 ICT, the open.
    assert session_date_for(datetime(2026, 9, 14, 2, 0, tzinfo=timezone.utc)) == date(2026, 9, 14)


def test_an_item_after_the_close_belongs_to_the_next_session():
    """Leakage, not an off-by-one: a 16:00 ICT story cannot have moved the
    session that closed at 15:00."""
    # 08:00 UTC = 15:00 ICT exactly, the close -> already too late.
    assert session_date_for(datetime(2026, 9, 14, 8, 0, tzinfo=timezone.utc)) == date(2026, 9, 15)
    assert session_date_for(datetime(2026, 9, 14, 23, 30, tzinfo=timezone.utc)) == date(2026, 9, 15)


def test_a_naive_timestamp_is_read_as_utc_which_is_what_the_store_holds():
    assert session_date_for(datetime(2026, 9, 14, 9, 0)) == date(2026, 9, 15)


def test_a_non_utc_timestamp_is_converted_before_the_cutoff_is_applied():
    ict = timezone(timedelta(hours=7))
    # 16:00 ICT on the 14th is 09:00 UTC -> after the close -> next session.
    assert session_date_for(datetime(2026, 9, 14, 16, 0, tzinfo=ict)) == date(2026, 9, 15)


def test_the_cutoff_is_configurable():
    late = time(23, 59)
    assert session_date_for(datetime(2026, 9, 14, 9, 0, tzinfo=timezone.utc),
                            close_utc=late) == date(2026, 9, 14)


# ---------------------------------------------------------------------------
# 1. intensity and polarity are separate series
# ---------------------------------------------------------------------------

def test_no_news_and_neutral_news_are_distinguishable():
    """The defect the separation exists to prevent: a single signed field is 0
    for both 'nothing happened' and 'balanced coverage'. Intensity separates
    them."""
    quiet = daily_news_features([], start=date(2026, 9, 1), end=date(2026, 9, 1))
    noisy = daily_news_features(
        [_at(2026, 9, 1, score=0.4), _at(2026, 9, 1, score=-0.4)],
        start=date(2026, 9, 1), end=date(2026, 9, 1),
    )
    assert quiet[0].polarity == noisy[0].polarity == 0.0   # same polarity
    assert quiet[0].intensity == 0.0
    assert noisy[0].intensity == 2.0                       # different intensity


def test_polarity_is_scale_free_so_volume_does_not_inflate_it():
    """Polarity is a mean, not a sum: ten identical good stories are not ten
    times as positive as one. Volume is intensity's job."""
    one = daily_news_features([_at(2026, 9, 1, score=0.6)],
                              start=date(2026, 9, 1), end=date(2026, 9, 1))
    ten = daily_news_features([_at(2026, 9, 1, score=0.6) for _ in range(10)],
                              start=date(2026, 9, 1), end=date(2026, 9, 1))
    assert one[0].polarity == pytest.approx(0.6)
    assert ten[0].polarity == pytest.approx(0.6)
    assert ten[0].intensity == pytest.approx(10 * one[0].intensity)


# ---------------------------------------------------------------------------
# 2. the impulse decays
# ---------------------------------------------------------------------------

def test_one_story_decays_instead_of_vanishing_after_a_day():
    rows = daily_news_features([_at(2026, 9, 1)],
                               start=date(2026, 9, 1), end=date(2026, 9, 11),
                               halflife_days=5.0)
    series = [r.intensity for r in rows]
    assert series[0] == pytest.approx(1.0)
    assert all(series[i] > series[i + 1] for i in range(len(series) - 1)), "must be monotone decaying"
    # A property, not a simulator magnitude: one half-life halves it.
    assert series[5] == pytest.approx(0.5, abs=1e-9)
    assert series[10] == pytest.approx(0.25, abs=1e-9)
    assert series[-1] > 0.0, "an undecayed series of zeros is the defect this prevents"


def test_decay_runs_over_calendar_days_including_the_weekend():
    """News ages over a weekend. Fri -> Mon is three days of decay, not one."""
    fri, mon = date(2026, 9, 4), date(2026, 9, 7)
    rows = daily_news_features([_at(2026, 9, 4)], start=fri, end=mon, halflife_days=3.0)
    assert rows[0].date == fri and rows[-1].date == mon
    assert rows[-1].intensity == pytest.approx(1.0 * (0.5 ** (3 / 3.0)))


def test_a_shorter_halflife_forgets_faster():
    args = dict(start=date(2026, 9, 1), end=date(2026, 9, 6))
    fast = daily_news_features([_at(2026, 9, 1)], halflife_days=2.0, **args)
    slow = daily_news_features([_at(2026, 9, 1)], halflife_days=10.0, **args)
    assert fast[-1].intensity < slow[-1].intensity


def test_a_non_positive_halflife_is_refused_not_silently_defaulted():
    for bad in (0.0, -1.0):
        with pytest.raises(ValueError, match="halflife_days"):
            daily_news_features([], start=date(2026, 9, 1), end=date(2026, 9, 2),
                                halflife_days=bad)


def test_an_inverted_range_is_refused():
    with pytest.raises(ValueError, match="precedes"):
        daily_news_features([], start=date(2026, 9, 5), end=date(2026, 9, 1))


def test_halflife_round_trips_through_the_decay_factor():
    decay = 0.5 ** (1.0 / 7.0)
    assert halflife_from_decay(decay) == pytest.approx(7.0)


# ---------------------------------------------------------------------------
# 4. polarity only averages scores we can vouch for (#112 provenance)
# ---------------------------------------------------------------------------

def test_a_legacy_row_counts_as_coverage_but_not_as_tone():
    """score_source NULL means the row was scored by the pre-#112 ternary, where
    neutral was stored as +0.5. Averaging that in would feed a known-bad number
    to the model; ignoring the article entirely would understate coverage."""
    rows = daily_news_features([_at(2026, 9, 1, score=0.5, source=None)],
                               start=date(2026, 9, 1), end=date(2026, 9, 1))
    assert rows[0].article_count == 1
    assert rows[0].intensity == 1.0
    assert rows[0].scored_count == 0
    assert rows[0].polarity == 0.0


def test_a_template_row_counts_as_coverage_but_not_as_tone():
    """'template' means no model answered — the score is a constant, not a
    judgement."""
    rows = daily_news_features([_at(2026, 9, 1, score=0.0, source="template")],
                               start=date(2026, 9, 1), end=date(2026, 9, 1))
    assert rows[0].intensity == 1.0
    assert rows[0].polarity == 0.0
    assert rows[0].scored_count == 0


def test_an_unscored_row_counts_as_coverage_but_not_as_tone():
    rows = daily_news_features([_at(2026, 9, 1, score=None, source="model")],
                               start=date(2026, 9, 1), end=date(2026, 9, 1))
    assert rows[0].intensity == 1.0
    assert rows[0].scored_count == 0


def test_a_trustworthy_score_beside_an_untrusted_one_is_not_diluted():
    """The untrusted row must not drag the mean toward its stored constant."""
    rows = daily_news_features(
        [_at(2026, 9, 1, score=-0.6, source="model"),
         _at(2026, 9, 1, score=0.5, source=None)],
        start=date(2026, 9, 1), end=date(2026, 9, 1),
    )
    assert rows[0].intensity == 2.0
    assert rows[0].scored_count == 1
    assert rows[0].polarity == pytest.approx(-0.6)


@pytest.mark.parametrize("source,ok", [
    ("model", True), ("label_fallback", True), ("keyword_fallback", True),
    ("template", False), (None, False), ("", False),
])
def test_which_provenances_may_set_the_tone(source, ok):
    assert is_trustworthy_score(0.4, source) is ok


def test_a_missing_score_is_never_trustworthy_whatever_the_source_says():
    assert is_trustworthy_score(None, "model") is False


# ---------------------------------------------------------------------------
# causality — the mandatory no-leakage harness (CLAUDE.md C1, §I.5.3)
# ---------------------------------------------------------------------------

def test_future_news_cannot_change_a_past_feature_value():
    """The no-leakage test. Compute the series, then add a burst of news AFTER
    the cut and recompute: every value at or before the cut must be identical.
    A windowed or centred smoother would fail this; the recursion cannot."""
    base = [_at(2026, 9, 2, score=0.3), _at(2026, 9, 5, score=-0.2)]
    future = [_at(2026, 9, 20, score=0.9) for _ in range(25)]

    args = dict(start=date(2026, 9, 1), end=date(2026, 9, 30), halflife_days=5.0)
    before = daily_news_features(base, **args)
    after = daily_news_features(base + future, **args)

    cut = date(2026, 9, 19)
    a = [(r.date, r.intensity, r.polarity) for r in before if r.date <= cut]
    b = [(r.date, r.intensity, r.polarity) for r in after if r.date <= cut]
    assert a == b, "news published after the cut changed a value at or before it"
    # And the burst must actually show up afterwards, or the test proves nothing
    # by asserting on a series that never moved.
    assert [r.intensity for r in after if r.date == date(2026, 9, 20)][0] > 20


def test_each_value_depends_only_on_its_own_prefix():
    """Stronger form: truncating the input at date d must not change any value
    up to d, for every d in the range."""
    items = [_at(2026, 9, day, score=(0.1 * day)) for day in range(1, 16)]
    full = daily_news_features(items, start=date(2026, 9, 1), end=date(2026, 9, 15))
    for d in (date(2026, 9, 3), date(2026, 9, 8), date(2026, 9, 14)):
        prefix = [i for i in items if i.ts_utc.date() <= d]
        part = daily_news_features(prefix, start=date(2026, 9, 1), end=d)
        assert [(r.date, r.intensity, r.polarity) for r in part] \
            == [(r.date, r.intensity, r.polarity) for r in full if r.date <= d]


# ---------------------------------------------------------------------------
# warmup, range and shape
# ---------------------------------------------------------------------------

def test_warmup_carries_prior_news_into_the_first_returned_row():
    """Without warmup the first row restarts from zero and understates a story
    published days earlier — an artefact of where the request happens to begin."""
    item = [_at(2026, 9, 1)]
    cold = daily_news_features(item, start=date(2026, 9, 6), end=date(2026, 9, 6))
    warm = daily_news_features(item, start=date(2026, 9, 6), end=date(2026, 9, 6),
                               warmup_days=30)
    assert cold[0].intensity == 0.0
    assert warm[0].intensity == pytest.approx(0.5, abs=1e-9)   # one half-life


def test_items_outside_the_window_are_ignored():
    rows = daily_news_features(
        [_at(2026, 8, 1), _at(2026, 12, 1)],
        start=date(2026, 9, 1), end=date(2026, 9, 3),
    )
    assert all(r.article_count == 0 and r.intensity == 0.0 for r in rows)


def test_one_row_per_calendar_date_oldest_first():
    rows = daily_news_features([], start=date(2026, 9, 1), end=date(2026, 9, 10))
    assert len(rows) == 10
    assert [r.date for r in rows] == sorted(r.date for r in rows)
    assert isinstance(rows[0], NewsFeatureRow)


def test_polarity_stays_inside_the_unit_range():
    rows = daily_news_features(
        [_at(2026, 9, 1, score=1.0) for _ in range(50)],
        start=date(2026, 9, 1), end=date(2026, 9, 5),
    )
    assert all(-1.0 <= r.polarity <= 1.0 for r in rows)


def test_the_default_halflife_is_in_the_range_the_backlog_called_for():
    assert 3.0 <= DEFAULT_HALFLIFE_DAYS <= 10.0
