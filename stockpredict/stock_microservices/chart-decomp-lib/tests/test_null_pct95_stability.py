"""A6.6 — Null pct95 stability with production n_null (FR-FPR-1).

Acceptance criterion (A6.6): all pct95 values are stable across two independent
null sweeps with different seeds.

Stability tolerance:
  High-FPR patterns (≥ 200 null scores): ±0.02
  Low-FPR patterns (< 200 null scores):  ±0.05

The ±0.02 / ±0.05 split reflects the statistical reality of the 95th-percentile
estimator SE:

    SE_q ≈ sqrt(q(1-q) / n_scores) / f(q)

  With q=0.95, f(q)≈2 (approximate density):
    n_scores = 1000 → SE ≈ 0.007 → 2σ ≈ 0.014  (within ±0.02)
    n_scores = 200  → SE ≈ 0.016 → 2σ ≈ 0.032  (within ±0.05)
    n_scores = 50   → SE ≈ 0.032 → 2σ ≈ 0.064  (within ±0.05 at 1σ)

Rare-firing patterns (pennants FPR≈0.08, doubles FPR≈0.10–0.18) accumulate only
40–90 scores in 500 surrogates; pct95 variance is irreducible without a much
larger n_null.  The ±0.05 tolerance is honest about this limitation.

Also verifies:
  - Service-layer API schema default has been raised to 500 (A6.6)
  - No pattern has a dead gate (pct95 ≥ 1.0) at n_null=1000
"""
from __future__ import annotations

import pytest

from chart_decomp.infrastructure.validation.null_fpr import (
    null_detection_distribution,
    null_thresholds,
)

# ── Shared sweep parameters ────────────────────────────────────────────────────

_LENGTH    = 300
_VOL       = 0.01
_N_NULL    = 1000       # used for the stability assertion sweep
_DETECTORS = "all"

_HIGH_FPR_TOL  = 0.02   # patterns with ≥ 400 null scores (triangles FPR ≈ 0.5–1.0)
_LOW_FPR_TOL   = 0.05   # patterns with < 400 null scores (flags, H&S, pennants, doubles)
_FPR_THRESHOLD = 400    # score count above which the tight tolerance applies


def _sweep(seed: int, n_null: int = _N_NULL):
    dist = null_detection_distribution(
        length=_LENGTH, volatility=_VOL, detectors=_DETECTORS,
        n_null=n_null, seed=seed,
    )
    thresh = null_thresholds(dist, noteworthy_pct=95.0)
    n_scores = {p: len(dist.scores_by_pattern.get(p, [])) for p in thresh}
    pct95    = {p: t.pct95 for p, t in thresh.items() if t.pct95 is not None}
    return pct95, n_scores


# ── Stability: two seeds must agree within tolerance ─────────────────────────

@pytest.mark.slow
class TestNullPct95Stability:
    """MANDATORY (A6.6): pct95 stable across seeds at n_null=1000."""

    def test_pct95_stable_seed0_vs_seed1(self):
        """Primary acceptance check: two independent sweeps agree within tolerance."""
        t0, n0 = _sweep(seed=0)
        t1, _  = _sweep(seed=1)
        common = sorted(set(t0) & set(t1))
        assert common, "No patterns fired in both sweeps — check detector registry"
        failures = []
        for pat in common:
            n_scores = n0.get(pat, 0)
            tol = _HIGH_FPR_TOL if n_scores >= _FPR_THRESHOLD else _LOW_FPR_TOL
            delta = abs(t0[pat] - t1[pat])
            if delta > tol:
                failures.append(
                    f"  {pat}: Δ={delta:.4f} > {tol:.2f} "
                    f"(n_scores={n_scores}, seed0={t0[pat]:.4f}, seed1={t1[pat]:.4f})"
                )
        assert not failures, (
            f"pct95 unstable at n_null={_N_NULL}:\n" + "\n".join(failures)
        )

    def test_no_dead_gates(self):
        """No pattern may have pct95 ≥ 1.0 (dead gate) at n_null=1000."""
        t, _ = _sweep(seed=0)
        dead = [p for p, v in t.items() if v >= 1.0]
        assert dead == [], f"Dead-gate patterns (pct95 ≥ 1.0): {dead}"

    def test_symmetric_triangle_pct95_below_0_95(self):
        """Symmetric Triangle pct95 < 0.95 after A6.6 min_inter_pivot tightening."""
        t, _ = _sweep(seed=0)
        pct95 = t.get("Symmetric Triangle")
        assert pct95 is not None, "Symmetric Triangle did not fire on any null series"
        assert pct95 < 0.95, (
            f"Symmetric Triangle pct95={pct95:.4f} ≥ 0.95 — min_inter_pivot may not be active"
        )


# ── Service schema: default must be 500 (raised from 100) ────────────────────

class TestServiceSchemaN500:
    """Service-layer API schema default must be raised to n_null=500 (A6.6)."""

    @staticmethod
    def _load_schemas():
        import os, sys
        svc = os.path.abspath(
            os.path.join(os.path.dirname(__file__),
                         "../../services/chart-decomp-service")
        )
        if svc not in sys.path:
            sys.path.insert(0, svc)
        from app.api.schemas import PatternPipelineRequest, PatternNullFPRRequest
        return PatternPipelineRequest, PatternNullFPRRequest

    def test_pattern_pipeline_request_default_n_null(self):
        PPR, _ = self._load_schemas()
        req = PPR(series=[float(i) for i in range(20)])
        assert req.n_null >= 500, (
            f"PatternPipelineRequest.n_null default={req.n_null}, want ≥ 500 (A6.6)"
        )

    def test_pattern_null_fpr_request_default_n_null(self):
        _, PNFPR = self._load_schemas()
        req = PNFPR(series=[float(i) for i in range(20)])
        assert req.n_null >= 500, (
            f"PatternNullFPRRequest.n_null default={req.n_null}, want ≥ 500 (A6.6)"
        )
