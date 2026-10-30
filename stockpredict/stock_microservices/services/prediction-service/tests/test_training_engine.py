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
