"""B4 — Nesting forest construction (FR-MS-3).

Mandatory tests (from implementation_plan_fpr_multiscale.md §B4 / SRS FR-MS-TEST-1):
  ✓ Nested-plant: a small pattern inside the right-shoulder LEG of a large H&S
    gets parent_id → the large one; nesting_depth 0 (H&S) and 1 (child).
  ✓ Single-leg guard: a small detection that straddles a parent's defining
    pivot is NOT made a child (MS-B2 — containment is necessary but not
    sufficient; spanning a defining pivot is an overlapping-window artifact).
  ✓ No cycles; each non-root has exactly one parent.

Additional properties tested:
  - Tightest (smallest-range) containing parent wins when several enclose a child.
  - Three-level nesting yields depths 0 / 1 / 2.
  - A strictly coarser scale is required (equal-scale overlap → no link).
  - Containment is required (coarser but non-overlapping → no link).
  - containment_tol slack admits a child that pokes slightly past a parent edge.
  - children_ids are consistent with parent_id (the inverse relation holds).
  - Integration: detect_multiscale populates roots and a valid acyclic forest.
"""
from __future__ import annotations

import numpy as np
import pytest

from chart_decomp.application.multiscale_pipeline_usecase import detect_multiscale
from chart_decomp.application.nesting_usecase import build_nesting_forest
from chart_decomp.domain.entities import Detection


# ── Helpers ───────────────────────────────────────────────────────────────────

def _det(
    pattern: str,
    start: int,
    end: int,
    scale: int,
    did: int,
    pivots: list[int] | None = None,
    score: float = 0.8,
) -> Detection:
    """Build a scale/id-tagged Detection mirroring the B3 test helper.

    When ``pivots`` is not given a minimal 3-pivot skeleton spanning the
    interval is synthesised (start, midpoint, end).
    """
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


def _by_id(dets: list[Detection]) -> dict[int, Detection]:
    return {d.detection_id: d for d in dets}


# A large Head & Shoulders at the coarsest scale.  Seven defining pivots:
#   start, left-shoulder peak, left trough, head, right trough,
#   right-shoulder peak, end.  Legs are the segments between consecutive pivots.
HS_PIVOTS = [0, 20, 40, 60, 80, 100, 120]


def _large_hs(did: int = 0, scale: int = 3) -> Detection:
    return _det("Head & Shoulders", 0, 120, scale=scale, did=did, pivots=HS_PIVOTS)


# ── MANDATORY: nested-plant test ──────────────────────────────────────────────

class TestNestedPlant:
    """FR-MS-TEST-1: small pattern inside the right-shoulder leg of a large H&S."""

    def test_child_links_to_parent(self):
        parent = _large_hs(did=0)
        # Right-shoulder leg of the H&S is [100, 120]; plant a bull flag inside it.
        child = _det("Bull Flag", 104, 116, scale=1, did=1)
        out = build_nesting_forest([parent, child])
        by = _by_id(out)
        assert by[1].parent_id == 0
        assert 1 in by[0].children_ids

    def test_nesting_depths(self):
        parent = _large_hs(did=0)
        child = _det("Bull Flag", 104, 116, scale=1, did=1)
        out = build_nesting_forest([parent, child])
        by = _by_id(out)
        assert by[0].nesting_depth == 0   # large H&S is a root
        assert by[1].nesting_depth == 1   # nested flag is one level down

    def test_parent_is_root(self):
        parent = _large_hs(did=0)
        child = _det("Bull Flag", 104, 116, scale=1, did=1)
        build_nesting_forest([parent, child])
        assert parent.parent_id is None
        assert child.parent_id == 0

    def test_child_range_within_a_single_leg(self):
        """Sanity: the planted child sits strictly between two consecutive
        parent pivots (100 and 120) — no defining pivot is interior to it."""
        parent = _large_hs(did=0)
        child = _det("Bull Flag", 104, 116, scale=1, did=1)
        interior = [v for v in parent.pivots
                    if child.start_index < v < child.end_index]
        assert interior == []


# ── MANDATORY: single-leg guard ───────────────────────────────────────────────

class TestSingleLegGuard:
    """MS-B2: a 'child' that straddles a parent's defining pivot is rejected."""

    def test_straddling_pivot_not_made_child(self):
        parent = _large_hs(did=0)
        # [70, 110] is fully INSIDE the parent's [0, 120] range, but it crosses
        # the defining pivots at 80 and 100 — two legs, not one → artifact.
        straddler = _det("Bull Flag", 70, 110, scale=1, did=1)
        # Confirm the premise: it IS contained, so only the leg guard can reject it.
        assert straddler.start_index >= parent.start_index
        assert straddler.end_index <= parent.end_index
        crossed = [v for v in parent.pivots
                   if straddler.start_index < v < straddler.end_index]
        assert crossed, "test premise: straddler must cross >=1 defining pivot"

        build_nesting_forest([parent, straddler])
        assert straddler.parent_id is None      # rejected → it is a root
        assert straddler.detection_id not in parent.children_ids

    def test_straddler_becomes_root(self):
        parent = _large_hs(did=0)
        straddler = _det("Bull Flag", 70, 110, scale=1, did=1)
        out = build_nesting_forest([parent, straddler])
        roots = [d.detection_id for d in out if d.parent_id is None]
        assert 0 in roots and 1 in roots

    def test_legit_child_in_other_leg_still_links(self):
        """Guard is per-pivot, not blanket: a sibling that DOES sit in one leg
        still nests even when another candidate child straddles."""
        parent = _large_hs(did=0)
        straddler = _det("Bull Flag", 70, 110, scale=1, did=1)
        good = _det("Bull Flag", 22, 38, scale=1, did=2)   # leg [20, 40]
        build_nesting_forest([parent, straddler, good])
        assert straddler.parent_id is None
        assert good.parent_id == 0


# ── MANDATORY: structural invariants (no cycles, one parent each) ─────────────

class TestForestInvariants:
    def _forest(self) -> list[Detection]:
        # P (scale 3) ⊃ M (scale 2) ⊃ C (scale 1), plus an unrelated root.
        P = _det("Head & Shoulders", 0, 180, scale=3, did=0,
                 pivots=[0, 30, 60, 90, 120, 150, 180])
        M = _det("Ascending Triangle", 122, 148, scale=2, did=1,
                 pivots=[122, 130, 140, 148])
        C = _det("Bull Flag", 131, 139, scale=1, did=2,
                 pivots=[131, 135, 139])
        other = _det("Double Top", 300, 360, scale=2, did=3)
        return build_nesting_forest([P, M, C, other])

    def test_every_non_root_has_exactly_one_parent(self):
        out = self._forest()
        by = _by_id(out)
        for d in out:
            if d.parent_id is not None:
                assert d.parent_id in by                    # parent exists
                assert d.detection_id in by[d.parent_id].children_ids

    def test_no_cycles(self):
        out = self._forest()
        by = _by_id(out)
        for d in out:
            seen = set()
            cur = d
            while cur.parent_id is not None:
                assert cur.detection_id not in seen, "cycle detected"
                seen.add(cur.detection_id)
                cur = by[cur.parent_id]

    def test_three_level_depths(self):
        out = self._forest()
        by = _by_id(out)
        assert by[0].nesting_depth == 0
        assert by[1].nesting_depth == 1
        assert by[2].nesting_depth == 2
        assert by[3].nesting_depth == 0   # unrelated root

    def test_tightest_parent_wins(self):
        """C is enclosed by both M and P; it must attach to M (smaller range)."""
        out = self._forest()
        by = _by_id(out)
        assert by[2].parent_id == 1           # M, not P
        assert 2 not in by[0].children_ids    # P does not claim the grandchild

    def test_children_ids_match_parent_ids(self):
        out = self._forest()
        by = _by_id(out)
        for d in out:
            for cid in d.children_ids:
                assert by[cid].parent_id == d.detection_id


# ── Containment / scale preconditions ─────────────────────────────────────────

class TestContainmentPreconditions:
    def test_equal_scale_no_link(self):
        """A parent must be STRICTLY coarser (FR-MS-3 cond 1)."""
        a = _det("Bull Flag", 0, 100, scale=2, did=0)
        b = _det("Bull Flag", 40, 60, scale=2, did=1)   # inside a, same scale
        build_nesting_forest([a, b])
        assert b.parent_id is None

    def test_finer_does_not_parent_coarser(self):
        """Direction is fixed: the coarser one is always the parent."""
        coarse = _det("Head & Shoulders", 0, 120, scale=3, did=0, pivots=HS_PIVOTS)
        fine = _det("Bull Flag", 104, 116, scale=1, did=1)
        build_nesting_forest([coarse, fine])
        assert coarse.parent_id is None       # coarse never becomes a child
        assert fine.parent_id == 0

    def test_coarser_but_disjoint_no_link(self):
        big = _det("Head & Shoulders", 0, 120, scale=3, did=0, pivots=HS_PIVOTS)
        far = _det("Bull Flag", 300, 320, scale=1, did=1)   # outside big's range
        build_nesting_forest([big, far])
        assert far.parent_id is None

    def test_containment_tol_slack(self):
        """A child poking slightly past the parent edge (within tol) still nests."""
        parent = _large_hs(did=0)             # [0, 120]
        # Child in the right-shoulder leg but ending 2 samples past the edge.
        child = _det("Bull Flag", 104, 122, scale=1, did=1)
        build_nesting_forest([parent, child], containment_tol=2)
        assert child.parent_id == 0

    def test_containment_tol_strict_rejects(self):
        parent = _large_hs(did=0)
        child = _det("Bull Flag", 104, 122, scale=1, did=1)
        # tol=0 → the 2-sample overhang now violates containment.
        build_nesting_forest([parent, child], containment_tol=0)
        assert child.parent_id is None


# ── Edge cases ────────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_empty(self):
        assert build_nesting_forest([]) == []

    def test_single_detection_is_root(self):
        d = _large_hs(did=0)
        out = build_nesting_forest([d])
        assert out[0].parent_id is None
        assert out[0].children_ids == []
        assert out[0].nesting_depth == 0

    def test_idempotent_rebuild(self):
        """Re-running on the same list reproduces the same forest (fields reset)."""
        dets = [
            _large_hs(did=0),
            _det("Bull Flag", 104, 116, scale=1, did=1),
        ]
        build_nesting_forest(dets)
        first = [(d.detection_id, d.parent_id, sorted(d.children_ids), d.nesting_depth)
                 for d in dets]
        build_nesting_forest(dets)
        second = [(d.detection_id, d.parent_id, sorted(d.children_ids), d.nesting_depth)
                  for d in dets]
        assert first == second

    def test_missing_scale_is_skipped(self):
        """A detection without a scale tag cannot parent or be parented."""
        no_scale = _det("Head & Shoulders", 0, 120, scale=3, did=0, pivots=HS_PIVOTS)
        no_scale.scale = None
        child = _det("Bull Flag", 104, 116, scale=1, did=1)
        build_nesting_forest([no_scale, child])
        assert child.parent_id is None


# ── Integration with detect_multiscale ────────────────────────────────────────

class TestNestingIntegration:
    @pytest.fixture(scope="class")
    def ms_result(self):
        rng = np.random.default_rng(0)
        x = 100.0 + np.cumsum(rng.normal(0, 0.012, 500))
        return detect_multiscale(x, scales=(1, 2, 3), compute_fpr=False)

    def test_roots_populated(self, ms_result):
        expected = {d.detection_id for d in ms_result.detections
                    if d.parent_id is None}
        assert set(ms_result.roots) == expected

    def test_roots_are_valid_ids(self, ms_result):
        ids = {d.detection_id for d in ms_result.detections}
        assert all(r in ids for r in ms_result.roots)

    def test_forest_is_acyclic(self, ms_result):
        by = {d.detection_id: d for d in ms_result.detections}
        for d in ms_result.detections:
            seen = set()
            cur = d
            while cur.parent_id is not None:
                assert cur.detection_id not in seen
                seen.add(cur.detection_id)
                cur = by[cur.parent_id]

    def test_parent_strictly_coarser(self, ms_result):
        by = {d.detection_id: d for d in ms_result.detections}
        for d in ms_result.detections:
            if d.parent_id is not None:
                assert by[d.parent_id].scale > d.scale

    def test_child_parent_consistency(self, ms_result):
        by = {d.detection_id: d for d in ms_result.detections}
        for d in ms_result.detections:
            for cid in d.children_ids:
                assert by[cid].parent_id == d.detection_id
            if d.parent_id is not None:
                assert d.detection_id in by[d.parent_id].children_ids
