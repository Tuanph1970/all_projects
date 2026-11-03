"""The shared primitive must stay identical to EM-1's original (Backlog #117).

stock-data-service needs relative volume to publish an unusual-volume reading
with each price event. The original lives here, in a 1,680-line EM-1 module with
heavy validated coverage, where the primitive's constants, dataclass and helpers
are woven through the file — extracting it would risk EM-1's measured work to
start a feature that does not need that risk.

So the algorithm is reproduced in stock_common.analytics.volume, and this file
is the price of that duplication: it drives BOTH implementations over randomised
and adversarial inputs and asserts they agree exactly. Divergence becomes a test
failure here rather than two services quietly disagreeing about what "4x normal
volume" means — the same device that ties the secrets guard to docker-compose
and the event-routing pattern to its publisher.

If this file ever fails, the two have drifted: fix the copy, do not relax the
test.
"""
from __future__ import annotations

import random

import pytest

from app.services.patterns.volume import relative_volume as em1_relative_volume
from stock_common.analytics.volume import relative_volume as shared_relative_volume


def _compare(volume, index, **kw):
    a = em1_relative_volume(volume, index, **kw)
    b = shared_relative_volume(volume, index, **kw)
    assert (a.value is None) == (b.value is None), (index, a, b)
    if a.value is not None:
        assert a.value == pytest.approx(b.value, rel=1e-12), (index, a.value, b.value)
    assert a.reason == b.reason, (index, a.reason, b.reason)
    assert a.bars_used == b.bars_used, (index, a.bars_used, b.bars_used)
    if a.baseline is None or b.baseline is None:
        assert a.baseline == b.baseline, (index, a.baseline, b.baseline)
    else:
        assert a.baseline == pytest.approx(b.baseline, rel=1e-12)


@pytest.mark.parametrize("seed", range(12))
def test_the_two_implementations_agree_on_random_series(seed):
    rng = random.Random(seed)
    n = rng.randint(1, 240)
    series = [rng.choice([
        rng.randint(0, 5_000_000),          # ordinary volume, zeros included
        0,                                   # a halt
        None,                                # a missing cell
        float("nan"),                        # an unusable cell
    ]) for _ in range(n)]
    for index in range(-2, n + 2):
        _compare(series, index)


@pytest.mark.parametrize("window", [12, 30, 100, 400])
def test_they_agree_for_any_baseline_window(window):
    rng = random.Random(window)
    series = [rng.randint(0, 100_000) for _ in range(200)]
    for index in (0, 11, 50, 150, 199):
        _compare(series, index, baseline_window=window)


@pytest.mark.parametrize("min_bars", [1, 10, 40])
def test_they_agree_for_any_min_bars(min_bars):
    series = [100 + (i % 9) for i in range(120)]
    for index in (5, 15, 60, 119):
        _compare(series, index, min_bars=min_bars)


@pytest.mark.parametrize("series,index", [
    ([], 0),                                        # empty
    ([42], 0),                                      # single bar, no history
    ([0] * 50 + [900], 50),                         # fully dormant window
    ([300] * 12 + [0] * 120 + [900], 132),          # dormancy needing the widen
    ([300] * 12 + [0] * 500 + [900], 512),          # dormancy beyond the widen
    ([None] * 30 + [500], 30),                      # all-missing window
    ([0] * 9 + [700], 9),                           # below the baseline floor
    ([5] * 60 + [0], 60),                           # a zero AT the judged bar
])
def test_they_agree_on_the_adversarial_cases(series, index):
    """The edges where two faithful-looking copies usually part company:
    dormancy, the widening boundary, all-missing windows, and a zero on the bar
    being judged rather than in its history."""
    _compare(series, index)


def test_the_constants_match():
    from app.services.patterns import volume as em1
    from stock_common.analytics import volume as shared

    assert em1.DEFAULT_BASELINE_WINDOW == shared.DEFAULT_BASELINE_WINDOW
    assert em1.MIN_BASELINE_BARS == shared.MIN_BASELINE_BARS
    assert em1.MAX_WIDEN_FACTOR == shared.MAX_WIDEN_FACTOR
