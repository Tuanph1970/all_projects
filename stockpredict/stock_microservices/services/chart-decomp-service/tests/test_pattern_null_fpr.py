"""POST /patterns/null-fpr — regression for a missing import.

run_pattern_null_fpr called null_fpr() without importing it, so every
request died with NameError (a 500) and nothing noticed: this service had
no tests. Found by ruff F821 while wiring CI.
"""
import numpy as np

from app.api.schemas import PatternNullFPRRequest
from app.services import decomp_service as svc


def _walk(n=120, seed=0):
    return (100 + np.cumsum(np.random.default_rng(seed).normal(0, 1, n))).tolist()


def test_null_fpr_runs_and_reports_the_requested_surrogate_count():
    req = PatternNullFPRRequest(series=_walk(), n_null=10, seed=1)
    out = svc.run_pattern_null_fpr(req)
    assert out.n_null == 10
    assert all(f >= 0 for f in out.fpr_by_pattern.values())


def test_null_fpr_is_reproducible_under_a_seed():
    req = PatternNullFPRRequest(series=_walk(), n_null=10, seed=7)
    assert svc.run_pattern_null_fpr(req) == svc.run_pattern_null_fpr(req)
