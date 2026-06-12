"""Nesting forest construction for multi-scale detections (B4 / FR-MS-3).

After the multi-scale sweep (B2) and cross-scale de-duplication (B3), a flat,
scale-tagged detection list still has no structure: a large formation traced by
the major swings and a small formation nested inside one of its legs sit side by
side as independent entries.  This module reconstructs the **nesting forest** —
parent → child links by date-range containment within a single leg.

Concept (SRS sub-module §MS.2 / FR-MS-3)
----------------------------------------
Detection *C* is a child of detection *P* iff ALL hold:

  1. *P* was found at a STRICTLY coarser scale than *C* (``P.scale > C.scale``).
  2. *C*'s ``[start_index, end_index]`` is contained within *P*'s range, with a
     small ``containment_tol`` slack in samples.
  3. *C* lies within a SINGLE LEG of *P* — between two consecutive defining
     pivots of *P*, NOT straddling one of them.  Containment alone is necessary
     but NOT sufficient (Trap MS-B2): a "child" that spans a defining pivot of
     the parent is an overlapping-window artifact, not a real nesting, and is
     rejected.

Each child is attached to its **tightest** (smallest-range) containing parent —
the immediate encloser.  Detections with no enclosing parent are roots.  Cycles
are impossible by construction: a parent is always strictly coarser-scale than
its child, so the scale strictly decreases along every parent→child edge.

This module is pure reconciliation over the existing ``Detection`` data model;
it never re-runs denoising, swing extraction, or detection.

Part B task map: B4 (this module).  B5 adds agreement/conflict annotation on top
of the forest; B6 measures the spurious-nesting null rate.
"""
from __future__ import annotations

from chart_decomp.domain.entities import Detection


def _is_contained(child: Detection, parent: Detection, tol: int) -> bool:
    """True iff ``child``'s index range sits inside ``parent``'s (± ``tol``)."""
    return (
        child.start_index >= parent.start_index - tol
        and child.end_index <= parent.end_index + tol
    )


def _within_single_leg(child: Detection, parent: Detection, tol: int) -> bool:
    """True iff ``child`` lies within ONE leg of ``parent`` (FR-MS-3 cond 3).

    A leg is the segment between two consecutive defining pivots of ``parent``.
    The child stays inside a single leg exactly when NO parent pivot is strictly
    interior to the child's range.  A pivot within ``tol`` samples of either
    child endpoint is treated as a shared leg boundary (the child abuts the
    pivot rather than crossing it), so it does not count as straddling.
    """
    lo = child.start_index + tol
    hi = child.end_index - tol
    for v in parent.pivots:
        if lo < v < hi:
            return False
    return True


def _assign_depths(detections: list[Detection], by_id: dict[int, Detection]) -> None:
    """Set ``nesting_depth`` = number of ancestors (0 for roots).

    Memoised over the parent chain.  Acyclic by construction (parents are
    strictly coarser), so the walk always terminates.
    """
    cache: dict[int, int] = {}

    def depth(d: Detection) -> int:
        if d.parent_id is None:
            return 0
        if d.detection_id in cache:
            return cache[d.detection_id]
        cache[d.detection_id] = 1 + depth(by_id[d.parent_id])
        return cache[d.detection_id]

    for d in detections:
        d.nesting_depth = depth(d)


def build_nesting_forest(
    detections: list[Detection],
    containment_tol: int = 2,
) -> list[Detection]:
    """Build the parent→child nesting forest in place (FR-MS-3).

    Sets ``parent_id``, ``children_ids`` and ``nesting_depth`` on every
    detection.  Detections with no enclosing parent are left as roots
    (``parent_id is None``).

    Parameters
    ----------
    detections      : flat, de-duplicated, scale-tagged detection list (from B3).
                      Each must carry a unique ``detection_id`` and a ``scale``;
                      entries missing a scale are treated as isolated (they can
                      neither parent nor be parented).
    containment_tol : sample slack for the containment and single-leg tests
                      (default 2, per SRS MS.6).  Larger values admit children
                      that poke slightly past a parent edge or leg boundary.

    Returns
    -------
    The same ``detections`` list (mutated), so callers can chain.  The roots are
    ``[d.detection_id for d in detections if d.parent_id is None]`` — the
    multi-scale pipeline copies these into ``MultiScaleResult.roots``.

    Notes
    -----
    - Each child attaches to its tightest (smallest-range) valid parent; ties on
      range break on the smaller ``detection_id`` for determinism.
    - The function is idempotent: nesting fields are reset on entry, so a rebuild
      on the same list reproduces the same forest.
    - O(n²) over detections; n is small (tens) in practice.
    """
    # Reset nesting fields so repeated calls are idempotent.
    for d in detections:
        d.parent_id = None
        d.children_ids = []
        d.nesting_depth = 0

    by_id = {d.detection_id: d for d in detections if d.detection_id is not None}

    for child in detections:
        if child.detection_id is None or child.scale is None:
            continue

        best: Detection | None = None
        best_width: int | None = None
        for parent in detections:
            if parent is child or parent.detection_id is None or parent.scale is None:
                continue
            if parent.scale <= child.scale:                 # cond 1: strictly coarser
                continue
            if not _is_contained(child, parent, containment_tol):   # cond 2
                continue
            if not _within_single_leg(child, parent, containment_tol):  # cond 3
                continue

            width = parent.end_index - parent.start_index
            if (
                best is None
                or width < best_width
                or (width == best_width and parent.detection_id < best.detection_id)
            ):
                best = parent
                best_width = width

        if best is not None:
            child.parent_id = best.detection_id

    # Populate children_ids (sorted for determinism) from the parent links.
    for child in detections:
        if child.parent_id is not None and child.parent_id in by_id:
            by_id[child.parent_id].children_ids.append(child.detection_id)
    for d in detections:
        d.children_ids.sort()

    _assign_depths(detections, by_id)
    return detections
