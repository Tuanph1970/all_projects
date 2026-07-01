"""T1 — package scaffold: imports, stage subpackages, exceptions, DEFAULTS."""
from __future__ import annotations

import importlib

import pytest


def test_top_level_import():
    import event_reaction  # noqa: F401


@pytest.mark.parametrize(
    "sub",
    ["ingest", "align", "surprise", "returns", "jumps", "cross_section"],
)
def test_stage_subpackages_import(sub):
    importlib.import_module(f"event_reaction.{sub}")


def test_exception_hierarchy():
    from event_reaction.exceptions import (
        AlignmentError,
        EventReactionError,
        InsufficientDataError,
        LeakageError,
    )

    for exc in (InsufficientDataError, AlignmentError, LeakageError):
        assert issubclass(exc, EventReactionError)


def test_defaults_match_srs_appendix_a():
    from event_reaction import DEFAULTS

    assert DEFAULTS.L == 120
    assert DEFAULTS.g == 5
    assert DEFAULTS.k1 == 1
    assert DEFAULTS.k2 == 1
    assert DEFAULTS.jump_local_window == 21
    assert DEFAULTS.jump_level == 0.01
    assert DEFAULTS.n_surrogates == 1000
    assert DEFAULTS.seed == 0
