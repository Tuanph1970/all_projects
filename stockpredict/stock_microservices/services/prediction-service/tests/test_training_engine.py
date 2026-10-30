"""Backlog #109: which engine trains a solution when the caller does not say.

The default used to be 'tabular' and is now 'darts' (owner decision 2026-10-30).
These tests pin the three things that can go wrong with a default: it points at
the wrong engine, it overrides a caller who DID choose, or an unrecognised name
is quietly swallowed into the default so the operator trains something other
than what they asked for.
"""
import inspect

import pytest

from app.api import solution_routes as sr


# ---------------------------------------------------------------------------
# the decision itself
# ---------------------------------------------------------------------------

def test_the_default_engine_is_darts():
    """The engine named in the UI must be the engine that trains.

    On the tabular path DARTS_TO_ML_MAP resolves 'TFT' to LightGBM, so the
    model label is not the model. That mislabelling is the reason for the flip.
    """
    assert sr.DEFAULT_TRAINING_ENGINE == 'darts'


def test_the_default_engine_is_one_the_dispatcher_accepts():
    """A default outside the supported set would fail every unflagged request."""
    assert sr.DEFAULT_TRAINING_ENGINE in sr.SUPPORTED_TRAINING_ENGINES


def test_both_engines_remain_available():
    """The flip is a default, not a removal — tabular stays reachable so a
    regression is still one flag away from being undone."""
    assert set(sr.SUPPORTED_TRAINING_ENGINES) == {'tabular', 'darts'}


# ---------------------------------------------------------------------------
# resolve_training_engine
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('absent', [None, '', '   '])
def test_not_choosing_an_engine_yields_the_default(absent):
    """Absent, None and blank all mean 'the caller did not choose'."""
    assert sr.resolve_training_engine(absent) == sr.DEFAULT_TRAINING_ENGINE


def test_an_explicit_choice_is_honoured_not_overridden():
    """Kills the mutation 'just return the default': asking for tabular must
    still get tabular, or the flag that undoes a regression does nothing."""
    assert sr.resolve_training_engine('tabular') == 'tabular'


def test_an_explicit_darts_choice_is_honoured():
    assert sr.resolve_training_engine('darts') == 'darts'


@pytest.mark.parametrize('spelling', ['DARTS', ' darts ', 'Darts'])
def test_case_and_whitespace_are_normalised(spelling):
    assert sr.resolve_training_engine(spelling) == 'darts'


def test_an_unknown_engine_is_preserved_for_the_caller_to_reject():
    """Not replaced by the default: silently substituting an engine would train
    something other than what was asked for, which is the class of behaviour
    #104/#105/#109 exist to remove. The caller validates and reports."""
    assert sr.resolve_training_engine('nonsense') == 'nonsense'


# ---------------------------------------------------------------------------
# the two call sites actually use the constant
# ---------------------------------------------------------------------------

def test_train_endpoint_defaults_through_the_constant():
    """A literal 'tabular' left at this call site would override the flip while
    every test above still passed — the constant must be what the route reads."""
    src = inspect.getsource(sr.train_solution)
    assert 'DEFAULT_TRAINING_ENGINE' in src
    assert "or 'tabular'" not in src


def test_training_dispatch_resolves_through_the_helper():
    """_run_training must not re-implement the default with its own literal."""
    src = inspect.getsource(sr._run_training)
    assert 'resolve_training_engine' in src
    assert "or 'tabular'" not in src


# ---------------------------------------------------------------------------
# Backlog #106 — the news-covariate flag and its half-life
# ---------------------------------------------------------------------------

def test_news_covariates_are_opt_in():
    """Default ON would add two near-constant features to every existing
    solution and move its numbers for no gain."""
    assert sr.NEWS_FEATURES_DEFAULT is False


def test_the_default_halflife_is_in_the_range_the_backlog_called_for():
    assert 3.0 <= sr.NEWS_HALFLIFE_DEFAULT <= 10.0


@pytest.mark.parametrize('requested,expected', [
    (5.0, 5.0), (1, 1.0), ('7', 7.0), (0.5, 0.5), (90, 90.0),
])
def test_a_valid_halflife_is_used_as_given(requested, expected):
    assert sr.resolve_news_halflife(requested) == expected


@pytest.mark.parametrize('requested,expected', [
    (0, 0.5), (-3, 0.5), (1000, 90.0),
])
def test_an_out_of_range_halflife_is_clamped_not_rejected(requested, expected):
    """A smoothing knob, not a correctness switch: a slider at 0 must not fail
    a training run. But 0 itself can never reach the decay factor, which is
    undefined there — hence the clamp rather than a pass-through."""
    assert sr.resolve_news_halflife(requested) == expected


@pytest.mark.parametrize('junk', [None, 'abc', '', float('nan'), object()])
def test_an_unusable_halflife_falls_back_to_the_default(junk):
    assert sr.resolve_news_halflife(junk) == sr.NEWS_HALFLIFE_DEFAULT


def test_the_clamp_can_never_return_a_value_the_series_builder_refuses():
    """news_features raises on halflife <= 0; the clamp must make that
    unreachable from the API, for every input."""
    for junk in (0, -1, -1e9, 'x', None, float('nan'), 1e9):
        assert sr.resolve_news_halflife(junk) > 0


def test_train_endpoint_carries_both_news_fields():
    src = inspect.getsource(sr.train_solution)
    assert 'include_news' in src
    assert 'resolve_news_halflife' in src


def test_training_attaches_news_only_when_asked():
    """The attach must sit behind the flag and before the warm-up dropna — a
    NaN-filled column there would delete every bar outside the news window."""
    src = inspect.getsource(sr._run_training)
    assert 'include_news' in src
    assert 'attach_news_features' in src
    assert src.index('attach_news_features') < src.index('feature_df.dropna()')


def test_a_failed_news_fetch_fails_the_run_rather_than_training_without_it():
    """Training on all-zero news columns and reporting a news-aware model is
    the #109 mislabelling defect in another costume."""
    src = inspect.getsource(sr._run_training)
    assert 'NewsCovariateError' in src
    assert 'could not' in src
