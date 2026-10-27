"""Backlog #99 — the phase-independent EM-4 estimator and its bootstrap.

The study scripts in this directory are `__main__` programs and are not
asserted anywhere. That was tolerable while they only *described* data. It is
not tolerable for `block_bootstrap`, because that function is now the thing
standing between the workstream and a false positive: #99 measured that a
naive Welch t on the same all-observations sample reads +1.26 / +2.01 / +2.83
and would have reported E&M's claim CONFIRMED at two horizons, where the
bootstrap reads +0.46 / +0.55 / +0.79 and rejects it.

A deflation of 2.8-3.6x is the whole result, so the deflation itself needs
tests. These assert *properties* against known answers, never the study's
output numbers:

* against iid data, where the right answer is the textbook one;
* against clustered data, where a per-observation SE is knowably wrong;
* and that the fast `low_flags` matches the naive re-sort it replaced.
"""
from __future__ import annotations

import math
import random

from statistics import mean

from tests.em4_mei_study import (
    DECILE,
    WARMUP_POINTS,
    block_bootstrap,
    edge,
    forward_observations,
    low_flags,
    welch,
)


class _Point:
    """Minimal stand-in for MeiPoint: the estimator reads .day and .mei only."""

    def __init__(self, day, mei):
        self.day = day
        self.mei = mei


def _iid_with_shift(n=3000, low_rate=0.1, shift=0.0, seed=7):
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        is_low = rng.random() < low_rate
        out.append((is_low, rng.gauss(0.0, 1.0) + (shift if is_low else 0.0)))
    return out


# ---------------------------------------------------------------------------
# edge()
# ---------------------------------------------------------------------------

def test_edge_is_the_difference_in_arm_means():
    obs = [(True, 10.0), (True, 20.0), (False, 1.0), (False, 3.0)]
    assert edge(obs) == 15.0 - 2.0


def test_edge_is_none_when_an_arm_cannot_support_a_mean():
    assert edge([(True, 1.0), (False, 1.0), (False, 2.0)]) is None
    assert edge([(True, 1.0), (True, 2.0), (False, 1.0)]) is None


# ---------------------------------------------------------------------------
# block_bootstrap() against known answers
# ---------------------------------------------------------------------------

def test_iid_data_with_unit_blocks_recovers_the_textbook_standard_error():
    """The calibration test: where the analytic answer is right, match it.

    With block = 1 and independent observations the moving-block bootstrap
    degenerates to the ordinary bootstrap, so its SE must agree with the
    Welch SE of the difference in means. If this drifts, the machinery is
    wrong and every deflation it reports is meaningless.
    """
    obs = _iid_with_shift(n=4000, low_rate=0.1, shift=0.5, seed=11)
    low = [r for f, r in obs if f]
    other = [r for f, r in obs if not f]
    analytic = math.sqrt(
        (sum((x - mean(low)) ** 2 for x in low) / (len(low) - 1)) / len(low)
        + (sum((x - mean(other)) ** 2 for x in other) / (len(other) - 1)) / len(other)
    )
    se, _, discarded = block_bootstrap(obs, block=1, replicates=600, seed=3)
    assert discarded == 0
    assert abs(se - analytic) / analytic < 0.15, (se, analytic)


def test_clustered_data_makes_a_long_block_report_a_far_larger_error():
    """The load-bearing property, and the reason the function exists.

    Low-MEI days arrive in runs — a bear market, not scattered days — and
    inside a run the forward returns are nearly the same number. A
    per-observation SE counts each day as fresh evidence and shrinks by
    sqrt(n); a block that spans a run cannot, because the whole run enters or
    leaves a replicate together.
    """
    rng = random.Random(5)
    obs = []
    for run in range(40):
        is_low = run % 4 == 0
        level = rng.gauss(0.0, 3.0) + (2.0 if is_low else 0.0)
        for _ in range(100):                     # a run: one event, 100 rows
            obs.append((is_low, level + rng.gauss(0.0, 0.05)))

    naive, _, _ = block_bootstrap(obs, block=1, replicates=600, seed=3)
    blocked, _, _ = block_bootstrap(obs, block=200, replicates=600, seed=3)
    assert blocked > 2.0 * naive, (naive, blocked)


def test_a_long_block_does_not_inflate_the_error_on_iid_data():
    """The converse, so the previous test cannot pass by always inflating.

    Without clustering there is nothing for a block to preserve, so a long
    block must agree with the analytic SE too — a little noisier, not larger
    in expectation. This is what distinguishes 'prices dependence' from
    'penalises everything'.
    """
    obs = _iid_with_shift(n=4000, low_rate=0.1, shift=0.5, seed=11)
    unit, _, _ = block_bootstrap(obs, block=1, replicates=600, seed=3)
    long_block, _, _ = block_bootstrap(obs, block=120, replicates=600, seed=3)
    assert 0.7 < long_block / unit < 1.4, (unit, long_block)


def test_the_bootstrap_is_reproducible_from_its_seed():
    obs = _iid_with_shift(n=1500, seed=2)
    first = block_bootstrap(obs, block=40, replicates=200, seed=99)
    again = block_bootstrap(obs, block=40, replicates=200, seed=99)
    assert first == again
    assert block_bootstrap(obs, block=40, replicates=200, seed=100) != first


def test_replicates_without_a_low_arm_are_discarded_and_counted():
    """A replicate that drew no bear market cannot produce an edge.

    Reported rather than silently dropped: #99 pre-registered that a discard
    rate above 10% means the episodes are too few for the bootstrap to be
    interpreted at all.
    """
    obs = [(i in (0, 1), float(i % 7)) for i in range(400)]
    se, _, discarded = block_bootstrap(obs, block=100, replicates=200, seed=4)
    assert discarded > 0
    obs_plenty = _iid_with_shift(n=2000, low_rate=0.3, seed=6)
    _, _, none_discarded = block_bootstrap(obs_plenty, block=50,
                                           replicates=200, seed=4)
    assert none_discarded == 0


def test_too_few_observations_refuses_rather_than_inventing_an_error():
    se, pct, discarded = block_bootstrap([(True, 1.0), (False, 2.0)], block=2)
    assert se is None and pct is None and discarded > 0


def test_the_percentile_is_below_the_point_estimate():
    obs = _iid_with_shift(n=3000, low_rate=0.1, shift=0.4, seed=13)
    point = edge(obs)
    se, pct, _ = block_bootstrap(obs, block=20, replicates=600, seed=3)
    assert pct < point
    assert point - 3.0 * se < pct < point


# ---------------------------------------------------------------------------
# low_flags() — the shared classifier
# ---------------------------------------------------------------------------

def _naive_flags(series):
    """The implementation `low_flags` replaced: re-sort the whole history."""
    flags = []
    for i, p in enumerate(series):
        past = [q.mei for q in series[:i]]
        if i < WARMUP_POINTS or not past:
            flags.append(False)
            continue
        cutoff = sorted(past)[max(0, int(len(past) * DECILE / 100.0) - 1)]
        flags.append(p.mei <= cutoff)
    return flags


def test_low_flags_matches_the_naive_resort_it_replaced():
    """#99 pre-registered that classification is untouched; this enforces it."""
    rng = random.Random(17)
    series = [_Point(i, rng.uniform(0.0, 100.0)) for i in range(WARMUP_POINTS + 400)]
    assert low_flags(series) == _naive_flags(series)


def test_low_flags_matches_the_naive_resort_on_COARSE_values():
    """The same equality, on values shaped like the real thing.

    Written because the continuous fixture above is too smooth to be a test:
    a mutation that puts each reading inside its own trailing history — i.e.
    hindsight — survives it, because with 650 distinct uniform draws the
    decile rank almost never shifts onto a different value.

    Real MEI is coarse. In 2007-09 it is a percentage of a **10-11 symbol**
    universe (#87's caveat, worsened by #90), so it takes values like 0.0,
    9.1, 18.2 — ties everywhere, where the continuous fixture has none.

    Measured, not assumed: coarseness alone does **not** catch the hindsight
    mutation either. Only the constructed boundary case below does. This test
    is kept as a realistic-input guard on the fast/naive equivalence, and the
    docstring says so rather than claiming a kill it does not make.
    """
    rng = random.Random(29)
    levels = [round(100.0 * k / 11.0, 1) for k in range(12)]
    series = [_Point(i, rng.choice(levels)) for i in range(WARMUP_POINTS + 400)]
    assert low_flags(series) == _naive_flags(series)


def test_a_reading_is_NOT_part_of_its_own_trailing_decile():
    """Causality, asserted directly rather than via an oracle.

    Constructed to be the discriminating case. The history is 259 distinct
    ascending values, so the cutoff rank is int(259 * 0.10) - 1 = 24, which
    is the value 25.0; a reading of 26.0 is therefore NOT in the bottom
    decile. Admit the reading into its own history and the count becomes 260,
    the rank becomes int(26.0) - 1 = 25, and with 26.0 inserted that rank now
    *is* 26.0 — so the reading qualifies on the strength of its own presence.

    That is hindsight: a reading cannot be evidence about where it sits in
    the distribution it is being judged against.
    """
    series = [_Point(j, float(j + 1)) for j in range(259)]
    series.append(_Point(259, 26.0))
    flags = low_flags(series)
    assert flags[259] is False
    assert flags == _naive_flags(series)


def test_low_flags_ignores_the_warmup_and_uses_only_the_past():
    rng = random.Random(19)
    series = [_Point(i, rng.uniform(20.0, 100.0)) for i in range(WARMUP_POINTS + 50)]
    # A reading lower than everything before it is low; one at the top is not.
    series.append(_Point(9001, 0.0))
    series.append(_Point(9002, 100.0))
    flags = low_flags(series)
    assert not any(flags[:WARMUP_POINTS])
    assert flags[-2] is True
    assert flags[-1] is False


def test_a_later_collapse_cannot_reclassify_an_earlier_reading():
    """No hindsight: the threshold at i sees series[:i] and nothing after."""
    rng = random.Random(23)
    head = [_Point(i, rng.uniform(40.0, 60.0)) for i in range(WARMUP_POINTS + 100)]
    early = low_flags(head)
    extended = low_flags(head + [_Point(9000 + j, 0.0) for j in range(50)])
    assert extended[: len(head)] == early


# ---------------------------------------------------------------------------
# forward_observations() — every day, in time order
# ---------------------------------------------------------------------------

def test_every_eligible_day_is_used_and_order_is_preserved():
    """The phase fix itself: nothing is skipped, so no offset can reselect.

    The old sampler took the earliest qualifying day and jumped `horizon`
    forward, which is why #90 could move Welch t by a full point just by
    starting the series 40 readings earlier.
    """
    n = WARMUP_POINTS + 120
    series = [_Point(i, float(i % 101)) for i in range(n)]
    proxy = {i: 100.0 + i for i in range(n)}
    horizon = 10
    obs = forward_observations(series, proxy, horizon)
    assert len(obs) == n - WARMUP_POINTS - horizon
    expected_first = (100.0 + WARMUP_POINTS + horizon) / (100.0 + WARMUP_POINTS)
    assert abs(obs[0][1] - (expected_first - 1.0) * 100.0) < 1e-9


def test_days_missing_from_the_proxy_are_skipped_not_misaligned():
    n = WARMUP_POINTS + 60
    series = [_Point(i, float(i % 101)) for i in range(n)]
    proxy = {i: 100.0 + i for i in range(n) if i % 5}
    obs = forward_observations(series, proxy, 10)
    assert 0 < len(obs) < n - WARMUP_POINTS - 10


def test_a_nonpositive_proxy_level_cannot_produce_a_return():
    n = WARMUP_POINTS + 40
    series = [_Point(i, 50.0) for i in range(n)]
    proxy = {i: (0.0 if i == WARMUP_POINTS else 100.0 + i) for i in range(n)}
    obs = forward_observations(series, proxy, 10)
    assert len(obs) == n - WARMUP_POINTS - 10 - 1
