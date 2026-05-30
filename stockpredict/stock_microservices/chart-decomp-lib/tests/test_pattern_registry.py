"""CD-605 (A5) — Detector base helpers + registry/factory (FR-PAT-EXT).

Asserts:
- A registry maps name → detector, supports override, and lists names.
- detect() runs the selected detectors and aggregates (sorted by start_index).
- 'all' vs an explicit subset; unknown names raise (mirrors DecomposerFactory).
- An empty/short skeleton produces no detections and no exception.
- Module-level register_detector / detect_patterns delegate to a default registry.
- Shared geometry helpers on PatternDetectorBase behave.
"""
from __future__ import annotations

import numpy as np
import pytest

from chart_decomp.domain.entities import Detection, Swing, SwingSkeleton
from chart_decomp.factories import pattern_detector_factory as pf
from chart_decomp.factories.pattern_detector_factory import (
    PatternDetectorRegistry,
    default_registry,
    detect_patterns,
    register_detector,
)
from chart_decomp.infrastructure.patterns.base import PatternDetectorBase


class StubDetector(PatternDetectorBase):
    def __init__(self, name: str, fire_at: int | None = None):
        self.name = name
        self.fire_at = fire_at

    def detect(self, skeleton, x, params=None):
        if self.fire_at is None or len(skeleton) == 0:
            return []
        return [Detection(self.name, self.fire_at, self.fire_at + 5, [self.fire_at], 0.5)]


@pytest.fixture
def skeleton():
    return SwingSkeleton([Swing(0, 10.0, "L"), Swing(10, 20.0, "H"), Swing(20, 8.0, "L")])


@pytest.fixture
def x():
    return np.linspace(0, 1, 30)


@pytest.fixture
def clean_default():
    """Snapshot/restore the module-level default registry to avoid pollution."""
    saved = dict(default_registry._detectors)
    try:
        yield
    finally:
        default_registry._detectors = saved


class TestRegistry:
    def test_register_and_names(self):
        reg = PatternDetectorRegistry()
        reg.register(StubDetector("A"))
        reg.register(StubDetector("B"))
        assert set(reg.names()) == {"A", "B"}

    def test_override_replaces(self):
        reg = PatternDetectorRegistry()
        reg.register(StubDetector("A", fire_at=1))
        reg.register(StubDetector("A", fire_at=2))  # same name overrides
        assert reg.names() == ["A"]
        assert reg.get("A").fire_at == 2

    def test_unknown_get_raises(self):
        reg = PatternDetectorRegistry()
        with pytest.raises(ValueError):
            reg.get("nope")

    def test_detect_aggregates_sorted(self, skeleton, x):
        reg = PatternDetectorRegistry()
        reg.register(StubDetector("A", fire_at=10))
        reg.register(StubDetector("B", fire_at=3))
        dets = reg.detect(skeleton, x, detectors="all")
        assert [d.start_index for d in dets] == [3, 10]
        assert {d.pattern for d in dets} == {"A", "B"}

    def test_detect_subset(self, skeleton, x):
        reg = PatternDetectorRegistry()
        reg.register(StubDetector("A", fire_at=10))
        reg.register(StubDetector("B", fire_at=3))
        dets = reg.detect(skeleton, x, detectors=["A"])
        assert len(dets) == 1 and dets[0].pattern == "A"

    def test_detect_unknown_subset_raises(self, skeleton, x):
        reg = PatternDetectorRegistry()
        reg.register(StubDetector("A", fire_at=10))
        with pytest.raises(ValueError):
            reg.detect(skeleton, x, detectors=["X"])

    def test_empty_skeleton_no_detections(self, x):
        reg = PatternDetectorRegistry()
        reg.register(StubDetector("A", fire_at=10))
        assert reg.detect(SwingSkeleton([]), x, detectors="all") == []


class TestModuleLevel:
    def test_register_and_detect(self, skeleton, x, clean_default):
        register_detector(StubDetector("uniqueX", fire_at=4))
        assert "uniqueX" in default_registry.names()
        dets = detect_patterns(skeleton, x, detectors=["uniqueX"])
        assert len(dets) == 1 and dets[0].pattern == "uniqueX"


class TestBaseHelpers:
    def test_linfit_recovers_line(self):
        xs = np.array([0, 1, 2, 3], dtype=float)
        ys = 2.0 * xs + 3.0
        slope, intercept = PatternDetectorBase.linfit(xs, ys)
        assert slope == pytest.approx(2.0)
        assert intercept == pytest.approx(3.0)

    def test_line_at(self):
        assert PatternDetectorBase.line_at(0, 0.0, 10, 100.0, 5) == pytest.approx(50.0)

    def test_within_tol(self):
        assert PatternDetectorBase.within_tol(100.0, 103.0, 0.05) is True
        assert PatternDetectorBase.within_tol(100.0, 110.0, 0.03) is False

    def test_rel_diff(self):
        assert PatternDetectorBase.rel_diff(100.0, 100.0) == pytest.approx(0.0)
        assert PatternDetectorBase.rel_diff(90.0, 110.0) == pytest.approx(0.2)

    def test_series_range_and_clamp(self):
        assert PatternDetectorBase.series_range(np.array([3.0, 1.0, 8.0])) == pytest.approx(7.0)
        assert PatternDetectorBase.clamp01(1.5) == pytest.approx(1.0)
        assert PatternDetectorBase.clamp01(-0.2) == pytest.approx(0.0)
        assert PatternDetectorBase.clamp01(0.4) == pytest.approx(0.4)

    def test_base_detect_is_abstract(self):
        with pytest.raises(NotImplementedError):
            PatternDetectorBase().detect(SwingSkeleton([]), np.zeros(5))
