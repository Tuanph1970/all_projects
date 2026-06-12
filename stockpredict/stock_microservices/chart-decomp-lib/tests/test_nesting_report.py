"""B7 — Nesting report builder (FR-MS-6 / FR-VIZ-2).

Turns a multi-scale detection list into ordered report rows that a table can
render directly: forest pre-order (each parent immediately followed by its
nested children), with per-row scale, nesting depth (for indentation), and a
reference to the parent (id + label).

Mandatory tests (from implementation_plan_fpr_multiscale.md §B7):
  ✓ Report renders parent/child indentation and the scale column.
  ✓ A nested child row references its parent's id/label.

Additional properties tested:
  - Forest pre-order: a parent row immediately precedes its child rows.
  - Roots have parent_id / parent_label = None and depth 0.
  - relation_to_parent, directional_bias, noteworthy are surfaced per row.
  - Integration with detect_multiscale output.
"""
from __future__ import annotations

import numpy as np
import pytest

from chart_decomp.application.multiscale_pipeline_usecase import detect_multiscale
from chart_decomp.application.nesting_report import (
    build_nesting_report,
    detection_label,
    order_forest,
)
from chart_decomp.application.nesting_usecase import (
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


def _nested_pair():
    """A large bearish H&S with a bullish bull-flag nested in its right shoulder."""
    parent = _det("Head & Shoulders", 0, 120, scale=3, did=0, pivots=HS_PIVOTS)
    child = _det("Bull Flag", 104, 116, scale=1, did=1)
    dets = build_nesting_forest([parent, child])
    annotate_relations(dets)
    return dets


def _row_by_id(rows):
    return {r["detection_id"]: r for r in rows}


# ── detection_label ───────────────────────────────────────────────────────────

class TestDetectionLabel:
    def test_label_includes_pattern_and_id(self):
        d = _det("Head & Shoulders", 0, 120, scale=3, did=7)
        assert detection_label(d) == "Head & Shoulders #7"

    def test_label_without_id(self):
        d = Detection(pattern="Bull Flag", start_index=0, end_index=10,
                      pivots=[0, 5, 10], score=0.5)
        assert detection_label(d) == "Bull Flag"


# ── order_forest ──────────────────────────────────────────────────────────────

class TestOrderForest:
    def test_parent_immediately_precedes_child(self):
        dets = _nested_pair()
        ordered = order_forest(dets)
        ids = [d.detection_id for d in ordered]
        assert ids.index(0) < ids.index(1)   # parent before child
        # child immediately follows its parent (pre-order)
        assert ids == [0, 1]

    def test_three_level_preorder(self):
        P = _det("Head & Shoulders", 0, 180, scale=3, did=0,
                 pivots=[0, 30, 60, 90, 120, 150, 180])
        M = _det("Ascending Triangle", 122, 148, scale=2, did=1,
                 pivots=[122, 130, 140, 148])
        C = _det("Bull Flag", 131, 139, scale=1, did=2, pivots=[131, 135, 139])
        other = _det("Double Top", 300, 360, scale=2, did=3)
        dets = build_nesting_forest([P, M, C, other])
        ordered = order_forest(dets)
        ids = [d.detection_id for d in ordered]
        # P, then its subtree M->C in pre-order, then the unrelated root.
        assert ids == [0, 1, 2, 3]

    def test_all_detections_present_once(self):
        dets = _nested_pair()
        ordered = order_forest(dets)
        assert sorted(d.detection_id for d in ordered) == [0, 1]


# ── build_nesting_report ──────────────────────────────────────────────────────

class TestBuildReport:
    def test_scale_column_present(self):
        """MANDATORY: every row exposes the scale."""
        rows = build_nesting_report(_nested_pair())
        assert all("scale" in r for r in rows)
        by = _row_by_id(rows)
        assert by[0]["scale"] == 3
        assert by[1]["scale"] == 1

    def test_indentation_depth_present(self):
        """MANDATORY: parent/child indentation via nesting_depth."""
        rows = build_nesting_report(_nested_pair())
        by = _row_by_id(rows)
        assert by[0]["nesting_depth"] == 0   # root, not indented
        assert by[1]["nesting_depth"] == 1   # child, indented one level

    def test_child_references_parent_id_and_label(self):
        """MANDATORY: a nested child row references its parent's id/label."""
        rows = build_nesting_report(_nested_pair())
        by = _row_by_id(rows)
        child = by[1]
        assert child["parent_id"] == 0
        assert child["parent_label"] == "Head & Shoulders #0"

    def test_root_has_no_parent(self):
        rows = build_nesting_report(_nested_pair())
        by = _row_by_id(rows)
        assert by[0]["parent_id"] is None
        assert by[0]["parent_label"] is None

    def test_rows_in_forest_preorder(self):
        rows = build_nesting_report(_nested_pair())
        assert [r["detection_id"] for r in rows] == [0, 1]

    def test_relation_and_bias_surfaced(self):
        rows = build_nesting_report(_nested_pair())
        by = _row_by_id(rows)
        # Bull flag (bullish) nested in H&S (bearish) → conflict.
        assert by[0]["directional_bias"] == "bearish"
        assert by[1]["directional_bias"] == "bullish"
        assert by[1]["relation_to_parent"] == "conflict"
        assert by[0]["relation_to_parent"] is None   # root

    def test_core_columns_present(self):
        rows = build_nesting_report(_nested_pair())
        required = {
            "detection_id", "pattern", "label", "scale", "start_index",
            "end_index", "score", "null_percentile", "noteworthy", "confirmed",
            "nesting_depth", "parent_id", "parent_label", "relation_to_parent",
            "directional_bias", "also_seen_at_scales",
        }
        for r in rows:
            assert required <= set(r), f"missing {required - set(r)}"

    def test_empty(self):
        assert build_nesting_report([]) == []


# ── Integration with detect_multiscale ────────────────────────────────────────

class TestReportIntegration:
    @pytest.fixture(scope="class")
    def result(self):
        rng = np.random.default_rng(0)
        x = 100.0 + np.cumsum(rng.normal(0, 0.012, 500))
        return detect_multiscale(x, scales=(1, 2, 3), compute_fpr=False)

    def test_report_covers_all_detections(self, result):
        rows = build_nesting_report(result.detections)
        assert len(rows) == len(result.detections)
        assert {r["detection_id"] for r in rows} == {
            d.detection_id for d in result.detections
        }

    def test_parents_precede_children(self, result):
        rows = build_nesting_report(result.detections)
        pos = {r["detection_id"]: i for i, r in enumerate(rows)}
        for r in rows:
            if r["parent_id"] is not None:
                assert pos[r["parent_id"]] < pos[r["detection_id"]]

    def test_depth_matches_detection(self, result):
        rows = build_nesting_report(result.detections)
        by_det = {d.detection_id: d for d in result.detections}
        for r in rows:
            assert r["nesting_depth"] == by_det[r["detection_id"]].nesting_depth
