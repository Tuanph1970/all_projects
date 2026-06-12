"""B5 — Agreement/conflict annotation (FR-MS-4).

Directional bias is DESCRIPTIVE metadata only; it carries no predictive claim
(Trap MS-B4 / Part II constraint L3).  These tests assert the bookkeeping is
correct, not that any bias predicts anything.

Mandatory tests (from implementation_plan_fpr_multiscale.md §B5):
  ✓ Bullish child inside bearish parent → relation_to_parent == 'conflict'.
  ✓ Bearish child inside bearish parent → 'agreement'.
  ✓ Neutral-bias pattern → 'neutral'.

Additional properties tested:
  - The default bias table maps every detector's pattern name correctly.
  - Either side neutral → relation is neutral (no agreement/conflict claimed).
  - Roots (no parent) get relation_to_parent == None.
  - A custom bias_table overrides the default.
  - Unknown pattern names fall back to neutral bias.
  - Integration: detect_multiscale annotates bias on all detections and a valid
    relation on every non-root.
"""
from __future__ import annotations

import numpy as np
import pytest

from chart_decomp.application.multiscale_pipeline_usecase import detect_multiscale
from chart_decomp.application.nesting_usecase import (
    DEFAULT_BIAS_TABLE,
    annotate_relations,
    build_nesting_forest,
)
from chart_decomp.domain.entities import Detection


# ── Helpers ───────────────────────────────────────────────────────────────────

HS_PIVOTS = [0, 20, 40, 60, 80, 100, 120]


def _det(pattern, start, end, scale, did, pivots=None, score=0.8) -> Detection:
    d = Detection(
        pattern=pattern,
        start_index=start,
        end_index=end,
        pivots=pivots if pivots is not None else [start, (start + end) // 2, end],
        score=score,
    )
    d.scale = scale
    d.detection_id = did
    return d


def _parent_child(parent_pattern, child_pattern):
    """Large coarse parent with a child planted in its right-shoulder leg."""
    parent = _det(parent_pattern, 0, 120, scale=3, did=0, pivots=HS_PIVOTS)
    child = _det(child_pattern, 104, 116, scale=1, did=1)
    dets = build_nesting_forest([parent, child])
    annotate_relations(dets)
    assert child.parent_id == 0, "fixture: child must nest under parent"
    return parent, child


# ── Bias table ────────────────────────────────────────────────────────────────

class TestBiasTable:
    @pytest.mark.parametrize("pattern,bias", [
        ("Head & Shoulders", "bearish"),
        ("Inverse Head & Shoulders", "bullish"),
        ("Bull Flag", "bullish"),
        ("Bull Pennant", "bullish"),
        ("Bear Flag", "bearish"),
        ("Bear Pennant", "bearish"),
        ("Double Top", "bearish"),
        ("Double Bottom", "bullish"),
        ("Ascending Triangle", "bullish"),
        ("Descending Triangle", "bearish"),
        ("Symmetric Triangle", "neutral"),
    ])
    def test_default_table_maps_pattern(self, pattern, bias):
        assert DEFAULT_BIAS_TABLE[pattern] == bias

    def test_annotate_sets_directional_bias(self):
        dets = [
            _det("Head & Shoulders", 0, 120, scale=1, did=0),
            _det("Bull Flag", 10, 30, scale=1, did=1),
            _det("Symmetric Triangle", 200, 260, scale=1, did=2),
        ]
        annotate_relations(dets)
        assert dets[0].directional_bias == "bearish"
        assert dets[1].directional_bias == "bullish"
        assert dets[2].directional_bias == "neutral"

    def test_unknown_pattern_defaults_neutral(self):
        d = _det("Rounding Bottom", 0, 50, scale=1, did=0)
        annotate_relations([d])
        assert d.directional_bias == "neutral"


# ── MANDATORY relation cases ──────────────────────────────────────────────────

class TestRelationToParent:
    def test_bullish_child_in_bearish_parent_conflict(self):
        """MANDATORY: bull flag nested in a (bearish) H&S → conflict."""
        parent, child = _parent_child("Head & Shoulders", "Bull Flag")
        assert parent.directional_bias == "bearish"
        assert child.directional_bias == "bullish"
        assert child.relation_to_parent == "conflict"

    def test_bearish_child_in_bearish_parent_agreement(self):
        """MANDATORY: bear flag nested in a (bearish) H&S → agreement."""
        parent, child = _parent_child("Head & Shoulders", "Bear Flag")
        assert child.relation_to_parent == "agreement"

    def test_bullish_child_in_bullish_parent_agreement(self):
        parent, child = _parent_child("Inverse Head & Shoulders", "Bull Flag")
        assert child.relation_to_parent == "agreement"

    def test_neutral_child_is_neutral_relation(self):
        """MANDATORY (neutral): a neutral-bias child → neutral relation."""
        parent, child = _parent_child("Head & Shoulders", "Symmetric Triangle")
        assert child.directional_bias == "neutral"
        assert child.relation_to_parent == "neutral"

    def test_neutral_parent_is_neutral_relation(self):
        parent, child = _parent_child("Symmetric Triangle", "Bull Flag")
        assert parent.directional_bias == "neutral"
        assert child.relation_to_parent == "neutral"

    def test_root_has_no_relation(self):
        parent, child = _parent_child("Head & Shoulders", "Bull Flag")
        assert parent.parent_id is None
        assert parent.relation_to_parent is None


# ── Custom table / robustness ─────────────────────────────────────────────────

class TestCustomTable:
    def test_custom_bias_table_overrides(self):
        custom = {"Bull Flag": "bearish", "Head & Shoulders": "bearish"}
        parent = _det("Head & Shoulders", 0, 120, scale=3, did=0, pivots=HS_PIVOTS)
        child = _det("Bull Flag", 104, 116, scale=1, did=1)
        dets = build_nesting_forest([parent, child])
        annotate_relations(dets, bias_table=custom)
        # Under the custom table both are bearish → agreement (vs conflict default)
        assert child.directional_bias == "bearish"
        assert child.relation_to_parent == "agreement"

    def test_idempotent_reannotate(self):
        parent = _det("Head & Shoulders", 0, 120, scale=3, did=0, pivots=HS_PIVOTS)
        child = _det("Bull Flag", 104, 116, scale=1, did=1)
        dets = build_nesting_forest([parent, child])
        annotate_relations(dets)
        first = [(d.directional_bias, d.relation_to_parent) for d in dets]
        annotate_relations(dets)
        second = [(d.directional_bias, d.relation_to_parent) for d in dets]
        assert first == second

    def test_empty(self):
        annotate_relations([])   # must not raise


# ── Integration with detect_multiscale ────────────────────────────────────────

class TestAnnotationIntegration:
    @pytest.fixture(scope="class")
    def ms_result(self):
        rng = np.random.default_rng(0)
        x = 100.0 + np.cumsum(rng.normal(0, 0.012, 500))
        return detect_multiscale(x, scales=(1, 2, 3), compute_fpr=False)

    def test_all_detections_have_bias(self, ms_result):
        assert all(d.directional_bias in ("bullish", "bearish", "neutral")
                   for d in ms_result.detections)

    def test_non_roots_have_relation(self, ms_result):
        for d in ms_result.detections:
            if d.parent_id is not None:
                assert d.relation_to_parent in ("agreement", "conflict", "neutral")

    def test_roots_have_no_relation(self, ms_result):
        for d in ms_result.detections:
            if d.parent_id is None:
                assert d.relation_to_parent is None

    def test_relation_consistent_with_biases(self, ms_result):
        by = {d.detection_id: d for d in ms_result.detections}
        for d in ms_result.detections:
            if d.parent_id is None:
                continue
            pb = by[d.parent_id].directional_bias
            cb = d.directional_bias
            if cb == "neutral" or pb == "neutral":
                assert d.relation_to_parent == "neutral"
            elif cb == pb:
                assert d.relation_to_parent == "agreement"
            else:
                assert d.relation_to_parent == "conflict"
