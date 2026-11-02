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


# ---------------------------------------------------------------------------
# Backlog #109 — naming honesty on the TABULAR path.
#
# The darts engine (now the default) builds the architecture a solution names.
# The tabular engine cannot: it resolves 'TFT' through DARTS_TO_ML_MAP to
# LightGBM. Its result payload used to report neither the engine nor the model,
# so a stored result was indistinguishable from a real TFT. Two fixes: CatBoost
# becomes genuine (the package is installed, so that substitution is obsolete
# rather than necessary), and every remaining substitution is DISCLOSED.
# ---------------------------------------------------------------------------

def test_catboost_is_no_longer_substituted_by_xgboost():
    """catboost has shipped in the image since #109; mapping it to xgboost was
    the single substitution that had stopped being necessary."""
    assert sr.DARTS_TO_ML_MAP['CatBoost'] == 'catboost'


@pytest.mark.parametrize('name,backend', [
    ('XGBoost', 'xgboost'),
    ('LightGBM', 'lightgbm'),
    ('RandomForest', 'random_forest'),
    ('CatBoost', 'catboost'),
    ('LinearRegression', 'linear_regression'),
])
def test_a_genuine_tabular_model_is_not_reported_as_substituted(name, backend):
    d = sr.describe_tabular_backend(name)
    assert d['actual_backend'] == backend
    assert d['backend_substituted'] is False
    assert d['model_type'] == name


@pytest.mark.parametrize('name', [
    'BlockRNN', 'RNN', 'TCN', 'Transformer', 'TFT',
    'NBeats', 'NHits', 'DLinear', 'NLinear', 'TiDE',
])
def test_every_torch_architecture_is_reported_as_substituted(name):
    """These have no tabular equivalent, so disclosure is the honest option —
    renaming the catalogue would be wrong now that the darts engine builds the
    real thing under the same name."""
    d = sr.describe_tabular_backend(name)
    assert d['backend_substituted'] is True
    assert d['model_type'] == name
    assert d['actual_backend'] in ('xgboost', 'lightgbm', 'random_forest')
    assert d['actual_backend'] != name.lower()


def test_the_disclosure_names_both_the_asked_for_and_the_actual_model():
    d = sr.describe_tabular_backend('TFT')
    assert d['actual_backend'] == 'lightgbm'
    assert 'TFT' in d['note'] and 'lightgbm' in d['note']
    assert 'darts' in d['note'].lower(), "the note must say how to get the real model"


def test_a_genuine_model_carries_no_note_to_explain_away():
    assert sr.describe_tabular_backend('LightGBM').get('note') in (None, '')


def test_an_unknown_model_type_is_substituted_not_silently_accepted():
    """DARTS_TO_ML_MAP falls back to xgboost for anything unrecognised, which is
    still a substitution and must be reported as one."""
    d = sr.describe_tabular_backend('SomeFutureModel')
    assert d['backend_substituted'] is True
    assert d['actual_backend'] == 'xgboost'


def test_the_disclosure_states_which_engine_produced_it():
    assert sr.describe_tabular_backend('TFT')['engine'] == 'tabular'


def test_every_catalogue_name_resolves_to_a_backend_the_factory_can_build():
    """A name in the catalogue that maps to a backend _create_ml_model has no
    branch for would fall through to its final else — the #110/#111 defect."""
    from app.api.routes import MODEL_TYPE_MAP
    buildable = {'xgboost', 'lightgbm', 'random_forest', 'catboost', 'linear_regression'}
    for name in MODEL_TYPE_MAP.values():
        d = sr.describe_tabular_backend(name)
        assert d['actual_backend'] in buildable, f"{name} -> {d['actual_backend']}"


def _tabular_blocks():
    """The two places the disclosure has to appear, isolated.

    An earlier version of these tests asserted only that
    `describe_tabular_backend` appeared ANYWHERE in _run_training. Because it is
    called twice, deleting the call from the result payload left the string
    present via the metrics block and the test stayed green — a mutation proved
    it. Third instance of this shape in a week (#104/#105, #112), so the blocks
    are now separated and asserted independently.
    """
    src = inspect.getsource(sr._run_training)
    m_at = src.index('metrics_json = json.dumps(')
    r_at = src.index('"result": {')
    assert m_at < r_at, "block order changed; this test needs rewriting"
    return src[m_at:r_at], src[r_at:]


def test_the_tabular_result_payload_discloses_the_backend():
    """What the UI reads. Without this, a stored tabular result is
    indistinguishable from a real TFT."""
    _metrics, result = _tabular_blocks()
    assert 'describe_tabular_backend' in result


def test_the_persisted_metrics_also_carry_the_disclosure():
    """model_instances.training_metrics_json outlives the in-memory status, so
    the disclosure has to survive there too — otherwise reopening an old
    solution shows numbers with no indication of what produced them."""
    metrics, _result = _tabular_blocks()
    assert 'describe_tabular_backend' in metrics


# ---------------------------------------------------------------------------
# Backlog #116 — the coverage report must describe the split the trainer uses
# ---------------------------------------------------------------------------

def test_news_coverage_is_computed_after_the_warmup_drop():
    """The split is int(len(frame) * train_ratio) on the POST-dropna frame, so a
    report built before the drop would describe a boundary nothing uses — and
    the point of the report is which side of that boundary the coverage is on."""
    src = inspect.getsource(sr._run_training)
    assert src.index('feature_df.dropna()') < src.index('news_coverage(feature_df'), \
        "news_coverage must be computed after the warm-up drop"


def test_news_coverage_is_given_the_train_ratio():
    """Without it the report cannot split train from validation, which is the
    whole of #116."""
    src = inspect.getsource(sr._run_training)
    assert 'news_coverage(feature_df, train_ratio=' in src
