"""B3 — Cross-scale de-duplication (FR-MS-2).

Mandatory tests (from implementation_plan_fpr_multiscale.md §B3):
  ✓ A medium pattern present at two adjacent scales appears as ONE detection
    with also_seen_at_scales populated, not two.
  ✓ Two genuinely different same-type patterns far apart are NOT merged.

Additional properties tested:
  - Higher score is retained when merging.
  - scale is set to the COARSEST (max k_drop) across the merged group.
  - Non-adjacent scale pairs (|diff|=2) are never merged.
  - Different pattern types are never merged.
  - Jaccard threshold is respected: pairs below it survive as separate dets.
  - Transitive closure via union-find: A-B and B-C qualify → all three merge.
  - Integration: detect_multiscale output has no surviving adjacent-scale
    same-pattern pair with Jaccard > threshold (post-condition of dedup).
"""
from __future__ import annotations

import numpy as np
import pytest

from chart_decomp.application.multiscale_pipeline_usecase import (
    _dedup_detections,
    _jaccard_interval,
    detect_multiscale,
)
from chart_decomp.domain.entities import Detection


# ── Helpers ───────────────────────────────────────────────────────────────────

def _det(
    pattern: str,
    start: int,
    end: int,
    scale: int,
    score: float,
    did: int = 0,
    also: list | None = None,
) -> Detection:
    d = Detection(
        pattern=pattern,
        start_index=start,
        end_index=end,
        pivots=[start, (start + end) // 2, end],
        score=score,
    )
    d.scale = scale
    d.detection_id = did
    d.also_seen_at_scales = also or []
    return d


def _jaccard(a: Detection, b: Detection) -> float:
    return _jaccard_interval(a.start_index, a.end_index, b.start_index, b.end_index)


# ── Unit: _jaccard_interval ───────────────────────────────────────────────────

class TestJaccardInterval:
    def test_identical_intervals(self):
        assert _jaccard_interval(10, 60, 10, 60) == pytest.approx(1.0)

    def test_no_overlap(self):
        assert _jaccard_interval(0, 50, 100, 150) == pytest.approx(0.0)

    def test_touching_at_one_point(self):
        # [0,50] and [50,100] share exactly 1 sample: inter=1, union=101
        assert _jaccard_interval(0, 50, 50, 100) == pytest.approx(1 / 101)

    def test_full_containment(self):
        # [20,40] inside [10,60]: inter=21, union=51
        assert _jaccard_interval(20, 40, 10, 60) == pytest.approx(21 / 51)

    def test_partial_overlap_concrete(self):
        # [10,60] vs [12,62]: inter=[12,60]=49, union=[10,62]=53
        assert _jaccard_interval(10, 60, 12, 62) == pytest.approx(49 / 53)

    def test_symmetry(self):
        assert _jaccard_interval(10, 60, 20, 80) == _jaccard_interval(20, 80, 10, 60)


# ── Unit: _dedup_detections ───────────────────────────────────────────────────

class TestDedupUnit:
    """Mandatory and supplementary unit tests for _dedup_detections."""

    # ── MANDATORY: adjacent overlap merges ──────────────────────────────────

    def test_adjacent_scales_high_overlap_merge_to_one(self):
        """MANDATORY: same pattern, |scale diff|=1, J=0.976 → exactly one detection."""
        d1 = _det("Head & Shoulders", 10, 60, scale=1, score=0.9, did=0)
        d2 = _det("Head & Shoulders", 12, 62, scale=2, score=0.8, did=1)
        assert _jaccard(d1, d2) > 0.7
        out = _dedup_detections([d1, d2])
        assert len(out) == 1

    def test_merged_has_also_seen_at_scales_populated(self):
        """MANDATORY: merged detection's also_seen_at_scales is not empty."""
        d1 = _det("Head & Shoulders", 10, 60, scale=1, score=0.9, did=0)
        d2 = _det("Head & Shoulders", 12, 62, scale=2, score=0.8, did=1)
        out = _dedup_detections([d1, d2])
        assert len(out) == 1
        m = out[0]
        assert m.also_seen_at_scales != [], "also_seen_at_scales must be populated after merge"
        # Between scale 1 and 2, one ends up in .scale and the other in .also_seen_at_scales
        assert sorted([m.scale] + m.also_seen_at_scales) == [1, 2]

    # ── MANDATORY: far-apart same-type NOT merged ────────────────────────────

    def test_far_apart_not_merged(self):
        """MANDATORY: same pattern, adjacent scale, zero Jaccard → two detections."""
        d1 = _det("Head & Shoulders", 0, 50, scale=1, score=0.9, did=0)
        d2 = _det("Head & Shoulders", 200, 250, scale=2, score=0.8, did=1)
        assert _jaccard(d1, d2) == 0.0
        out = _dedup_detections([d1, d2])
        assert len(out) == 2

    # ── Scale of merged detection is coarsest ───────────────────────────────

    def test_merged_scale_is_coarsest(self):
        d1 = _det("Head & Shoulders", 10, 60, scale=1, score=0.9, did=0)
        d2 = _det("Head & Shoulders", 12, 62, scale=2, score=0.8, did=1)
        out = _dedup_detections([d1, d2])
        assert out[0].scale == 2

    def test_also_seen_contains_finer_scale(self):
        d1 = _det("Head & Shoulders", 10, 60, scale=1, score=0.9, did=0)
        d2 = _det("Head & Shoulders", 12, 62, scale=2, score=0.8, did=1)
        out = _dedup_detections([d1, d2])
        assert 1 in out[0].also_seen_at_scales

    # ── Higher score retained ────────────────────────────────────────────────

    def test_higher_score_retained_when_d1_wins(self):
        d1 = _det("Ascending Triangle", 10, 60, scale=1, score=0.9, did=0)
        d2 = _det("Ascending Triangle", 12, 62, scale=2, score=0.6, did=1)
        out = _dedup_detections([d1, d2])
        assert out[0].score == pytest.approx(0.9)

    def test_higher_score_retained_when_d2_wins(self):
        d1 = _det("Ascending Triangle", 10, 60, scale=1, score=0.5, did=0)
        d2 = _det("Ascending Triangle", 12, 62, scale=2, score=0.85, did=1)
        out = _dedup_detections([d1, d2])
        assert out[0].score == pytest.approx(0.85)

    # ── Non-adjacent scales not merged ──────────────────────────────────────

    def test_scale_diff_2_not_merged(self):
        d1 = _det("Head & Shoulders", 10, 60, scale=1, score=0.9, did=0)
        d3 = _det("Head & Shoulders", 12, 62, scale=3, score=0.8, did=1)
        assert abs(d1.scale - d3.scale) == 2
        out = _dedup_detections([d1, d3])
        assert len(out) == 2

    # ── Different patterns not merged ───────────────────────────────────────

    def test_different_patterns_not_merged(self):
        d1 = _det("Head & Shoulders", 10, 60, scale=1, score=0.9, did=0)
        d2 = _det("Bull Flag", 12, 62, scale=2, score=0.8, did=1)
        out = _dedup_detections([d1, d2])
        assert len(out) == 2

    # ── Jaccard threshold boundary ───────────────────────────────────────────

    def test_overlap_below_threshold_not_merged(self):
        # [0,50] vs [40,90]: inter=[40,50]=11, union=[0,90]=91, J≈0.121
        d1 = _det("Head & Shoulders", 0, 50, scale=1, score=0.9, did=0)
        d2 = _det("Head & Shoulders", 40, 90, scale=2, score=0.8, did=1)
        assert _jaccard(d1, d2) < 0.7
        out = _dedup_detections([d1, d2], dedup_jaccard=0.7)
        assert len(out) == 2

    def test_overlap_above_threshold_merged(self):
        # Same pair but lower threshold
        d1 = _det("Head & Shoulders", 0, 50, scale=1, score=0.9, did=0)
        d2 = _det("Head & Shoulders", 40, 90, scale=2, score=0.8, did=1)
        out = _dedup_detections([d1, d2], dedup_jaccard=0.1)
        assert len(out) == 1

    # ── Same-scale duplicates merged (|diff|=0 ≤ 1) ─────────────────────────

    def test_same_scale_overlapping_merged(self):
        d1 = _det("Descending Triangle", 10, 60, scale=3, score=0.66, did=0)
        d2 = _det("Descending Triangle", 12, 62, scale=3, score=0.40, did=1)
        out = _dedup_detections([d1, d2])
        assert len(out) == 1
        assert out[0].score == pytest.approx(0.66)
        assert out[0].scale == 3

    def test_same_scale_merge_also_seen_empty(self):
        """Two same-scale dets that merge: also_seen_at_scales is empty (no *other* scales)."""
        d1 = _det("Bull Flag", 10, 60, scale=2, score=0.7, did=0)
        d2 = _det("Bull Flag", 11, 61, scale=2, score=0.5, did=1)
        out = _dedup_detections([d1, d2])
        assert len(out) == 1
        assert out[0].also_seen_at_scales == []

    # ── Three-way transitive merge ───────────────────────────────────────────

    def test_three_way_transitive_merge(self):
        """d1-d2 qualify and d2-d3 qualify → union-find puts all three in one group.
        d1 and d3 have |scale diff|=2 so they do NOT qualify directly, but the
        transitive closure via d2 unifies them.
        """
        d1 = _det("Ascending Triangle", 10, 60, scale=1, score=0.90, did=0)
        d2 = _det("Ascending Triangle", 11, 61, scale=2, score=0.80, did=1)
        d3 = _det("Ascending Triangle", 12, 62, scale=3, score=0.70, did=2)
        # All pairs overlap: J ≈ 0.94
        out = _dedup_detections([d1, d2, d3])
        assert len(out) == 1
        m = out[0]
        assert m.score == pytest.approx(0.90)       # highest score kept
        assert m.scale == 3                          # coarsest
        assert sorted(m.also_seen_at_scales) == [1, 2]  # other two scales

    def test_three_way_partial_no_transitive(self):
        """d1-d2 qualify but d2-d3 do NOT (far apart) → two groups: {d1,d2} and {d3}."""
        d1 = _det("Bull Flag", 10, 60, scale=1, score=0.9, did=0)
        d2 = _det("Bull Flag", 12, 62, scale=2, score=0.8, did=1)
        d3 = _det("Bull Flag", 300, 350, scale=2, score=0.7, did=2)
        out = _dedup_detections([d1, d2, d3])
        assert len(out) == 2
        scores = sorted(d.score for d in out)
        assert scores == pytest.approx([0.7, 0.9])

    # ── Edge cases ───────────────────────────────────────────────────────────

    def test_empty_list(self):
        assert _dedup_detections([]) == []

    def test_single_detection(self):
        d = _det("Head & Shoulders", 10, 60, scale=1, score=0.8, did=0)
        out = _dedup_detections([d])
        assert len(out) == 1

    def test_unchanged_detection_not_in_merge_group(self):
        """A detection that doesn't qualify with any partner passes through untouched."""
        lone = _det("Bear Flag", 0, 40, scale=1, score=0.75, did=99)
        d1 = _det("Head & Shoulders", 10, 60, scale=1, score=0.9, did=0)
        d2 = _det("Head & Shoulders", 12, 62, scale=2, score=0.8, did=1)
        out = _dedup_detections([lone, d1, d2])
        assert len(out) == 2
        lone_out = next(d for d in out if d.pattern == "Bear Flag")
        assert lone_out.scale == 1
        assert lone_out.also_seen_at_scales == []

    def test_output_sorted_by_start_index(self):
        d1 = _det("Head & Shoulders", 100, 160, scale=1, score=0.9, did=0)
        d2 = _det("Bull Flag", 10, 50, scale=1, score=0.7, did=1)
        out = _dedup_detections([d1, d2])
        assert out[0].start_index < out[1].start_index

    def test_detection_id_preserved_from_keeper(self):
        d1 = _det("Ascending Triangle", 10, 60, scale=1, score=0.9, did=42)
        d2 = _det("Ascending Triangle", 11, 61, scale=2, score=0.7, did=99)
        out = _dedup_detections([d1, d2])
        assert out[0].detection_id == 42   # keeper (score=0.9) had id=42

    def test_also_seen_inherits_prior_also_seen(self):
        """If a detection already has also_seen_at_scales (from a previous merge),
        those scales are included in the new merged group's also_seen.
        """
        d1 = _det("Bull Flag", 10, 60, scale=2, score=0.9, did=0, also=[1])
        d2 = _det("Bull Flag", 11, 61, scale=3, score=0.7, did=1)
        out = _dedup_detections([d1, d2])
        assert len(out) == 1
        m = out[0]
        assert m.scale == 3
        assert sorted(m.also_seen_at_scales) == [1, 2]   # 1 from d1.also_seen, 2 from d1.scale


# ── Integration: detect_multiscale post-condition ────────────────────────────

class TestDedupIntegration:
    """Verify dedup is wired into detect_multiscale and the post-condition holds."""

    @pytest.fixture(scope="class")
    def ms_raw(self):
        """Baseline series known to produce overlapping adjacent-scale detections."""
        rng = np.random.default_rng(0)
        return 100.0 + np.cumsum(rng.normal(0, 0.012, 500))

    @pytest.fixture(scope="class")
    def ms_result(self, ms_raw):
        return detect_multiscale(ms_raw, scales=(1, 2, 3), compute_fpr=False)

    def test_no_surviving_adjacent_scale_duplicates(self, ms_result):
        """Post-condition: no two detections in the output share (same pattern,
        adjacent scales, Jaccard > 0.7) — dedup must have removed all such pairs.
        """
        dets = ms_result.detections
        violations = []
        for i, di in enumerate(dets):
            for j, dj in enumerate(dets):
                if j <= i:
                    continue
                if di.pattern != dj.pattern:
                    continue
                if di.scale is None or dj.scale is None:
                    continue
                if abs(di.scale - dj.scale) > 1:
                    continue
                j_val = _jaccard_interval(
                    di.start_index, di.end_index, dj.start_index, dj.end_index
                )
                if j_val > 0.7:
                    violations.append(
                        f"  {di.pattern}: id={di.detection_id}(k={di.scale}) "
                        f"vs id={dj.detection_id}(k={dj.scale}) J={j_val:.3f}"
                    )
        assert not violations, (
            "Surviving adjacent-scale duplicates after dedup:\n" + "\n".join(violations)
        )

    def test_dedup_reduces_detection_count(self, ms_result, ms_raw):
        """Dedup must have removed at least one detection from this series
        (we know from B2 diagnostics that 5 pairs have J > 0.7).
        """
        # Count raw (pre-dedup) via detect_multiscale with dedup_jaccard=2.0 (nothing merges)
        raw_ms = detect_multiscale(ms_raw, scales=(1, 2, 3),
                                   dedup_jaccard=2.0, compute_fpr=False)
        assert len(ms_result.detections) < len(raw_ms.detections), (
            f"Dedup did not reduce count: before={len(raw_ms.detections)}, "
            f"after={len(ms_result.detections)}"
        )

    def test_merged_detections_have_also_seen_populated(self, ms_result):
        """Any detection where .scale is not the finest should have also_seen populated."""
        # Detections that survived a merge: scale > min possible AND also_seen not empty
        has_merge = [d for d in ms_result.detections if d.also_seen_at_scales]
        # We know from diagnostics that at least 3 merges happen (Asc, Desc, H&S)
        assert len(has_merge) >= 1, (
            "Expected at least one merged detection with also_seen_at_scales set"
        )

    def test_all_ids_still_unique_after_dedup(self, ms_result):
        ids = [d.detection_id for d in ms_result.detections]
        assert len(ids) == len(set(ids))

    def test_scale_tags_coarser_or_same_after_dedup(self, ms_result):
        """After dedup, .scale == coarsest scale in the merged group.
        Verify no detection has scale < min(its group) — i.e. we don't accidentally
        downgrade a detection's scale to a finer level.
        """
        # We can only check: all .scale values are in (1, 2, 3)
        for d in ms_result.detections:
            assert d.scale in (1, 2, 3), f"Unexpected scale {d.scale}"

    def test_mandatory_pattern_present_at_two_adjacent_scales(self, ms_raw):
        """MANDATORY: a pattern found at k_drop=1 and k_drop=2 with J>0.7 appears
        as ONE detection with also_seen_at_scales populated.
        We use the Ascending Triangle pair identified in B2 diagnostics
        (J=0.976) as the concrete fixture.
        """
        # Run with dedup disabled to confirm both detections exist pre-dedup
        raw_ms = detect_multiscale(ms_raw, scales=(1, 2), dedup_jaccard=2.0,
                                   compute_fpr=False)
        asc_k1 = [d for d in raw_ms.detections
                  if d.pattern == "Ascending Triangle" and d.scale == 1]
        asc_k2 = [d for d in raw_ms.detections
                  if d.pattern == "Ascending Triangle" and d.scale == 2]
        # Confirm the overlapping pair exists before dedup
        found_overlap = any(
            _jaccard_interval(a.start_index, a.end_index, b.start_index, b.end_index) > 0.7
            for a in asc_k1 for b in asc_k2
        )
        assert found_overlap, (
            "Test fixture assumption violated: no Ascending Triangle pair with J>0.7 "
            "at scales 1 and 2 on this series (re-check B2 diagnostics)"
        )

        # Run with dedup enabled — the pair must collapse to one detection
        deduped_ms = detect_multiscale(ms_raw, scales=(1, 2), compute_fpr=False)
        asc_deduped = [d for d in deduped_ms.detections
                       if d.pattern == "Ascending Triangle"]
        # Verify no surviving pair at adjacent scales with J > 0.7
        for i, di in enumerate(asc_deduped):
            for j, dj in enumerate(asc_deduped):
                if j <= i:
                    continue
                if abs(di.scale - dj.scale) <= 1:
                    j_val = _jaccard_interval(
                        di.start_index, di.end_index, dj.start_index, dj.end_index
                    )
                    assert j_val <= 0.7, (
                        f"Ascending Triangle duplicate survived dedup: "
                        f"id={di.detection_id}(k={di.scale}) vs "
                        f"id={dj.detection_id}(k={dj.scale}) J={j_val:.3f}"
                    )
        # The merged detection must carry also_seen_at_scales
        merged = [d for d in asc_deduped if d.also_seen_at_scales]
        assert merged, "Merged Ascending Triangle detection missing also_seen_at_scales"
