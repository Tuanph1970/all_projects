"""B7 — Multi-scale pattern endpoint surfaces nesting in the service response.

Mirrors test_report_fpr_column.py: reaches into the chart-decomp-service layer
and asserts the multi-scale response carries scale + nesting fields and that the
detection list is in forest pre-order with parent references (FR-MS-6).
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

_SVC_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../services/chart-decomp-service")
)
if _SVC_ROOT not in sys.path:
    sys.path.insert(0, _SVC_ROOT)

from app.api.schemas import (  # noqa: E402
    DetectionInfo,
    MultiScalePatternResponse,
    PatternMultiScaleRequest,
)
from app.services.decomp_service import run_pattern_multiscale  # noqa: E402


def _zigzag(control, n):
    idxs = [c[0] for c in control]
    prices = [c[1] for c in control]
    return np.interp(np.arange(n), idxs, prices).tolist()


# Planted H&S on a 300-pt series (same construction as the A5 report test).
_HS_CTRL = [
    (0, 80), (80, 130), (120, 100), (160, 160), (200, 102), (230, 132), (260, 90),
    (299, 90),
]


@pytest.fixture(scope="module")
def resp() -> MultiScalePatternResponse:
    req = PatternMultiScaleRequest(
        series=_zigzag(_HS_CTRL, 300),
        scales=[1, 2, 3],
        compute_fpr=False,
    )
    return run_pattern_multiscale(req)


class TestSchema:
    def test_detectioninfo_has_multiscale_fields(self):
        info = DetectionInfo(pattern="Head & Shoulders", start_index=0,
                             end_index=10, pivots=[0, 5, 10], score=0.8)
        # defaults are single-scale-safe
        assert info.scale is None
        assert info.nesting_depth == 0
        assert info.parent_id is None
        assert info.also_seen_at_scales == []

    def test_response_round_trips(self, resp):
        dumped = resp.model_dump()
        assert "detections" in dumped
        assert "roots" in dumped
        assert "denoised_by_scale" in dumped
        assert "spurious_nesting_fpr" in dumped


class TestMultiScaleResponse:
    def test_denoised_by_scale_has_all_scales(self, resp):
        assert set(resp.denoised_by_scale.keys()) == {1, 2, 3}

    def test_every_detection_scale_tagged(self, resp):
        assert all(d.scale in (1, 2, 3) for d in resp.detections)

    def test_detection_ids_unique(self, resp):
        ids = [d.detection_id for d in resp.detections]
        assert len(ids) == len(set(ids))

    def test_roots_match_parentless(self, resp):
        parentless = {d.detection_id for d in resp.detections if d.parent_id is None}
        assert set(resp.roots) == parentless

    def test_detections_in_forest_preorder(self, resp):
        """Parents must appear before their children (FR-VIZ-2 indentation)."""
        pos = {d.detection_id: i for i, d in enumerate(resp.detections)}
        for d in resp.detections:
            if d.parent_id is not None:
                assert pos[d.parent_id] < pos[d.detection_id]

    def test_child_rows_reference_parent_label(self, resp):
        by = {d.detection_id: d for d in resp.detections}
        for d in resp.detections:
            if d.parent_id is not None:
                assert d.parent_label is not None
                assert f"#{d.parent_id}" in d.parent_label
                assert by[d.parent_id].pattern in d.parent_label

    def test_bias_populated(self, resp):
        assert all(d.directional_bias in ("bullish", "bearish", "neutral")
                   for d in resp.detections)

    def test_spurious_nesting_fpr_zero_without_compute(self, resp):
        assert resp.spurious_nesting_fpr == 0.0
