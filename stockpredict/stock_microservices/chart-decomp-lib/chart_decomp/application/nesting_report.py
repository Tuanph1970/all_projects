"""Nesting report builder for multi-scale detections (B7 / FR-MS-6 / FR-VIZ-2).

Turns the flat, scale-tagged, nesting-linked detection list (from B2–B6) into an
ordered list of report rows a table can render directly:

  * forest **pre-order** — each parent row is immediately followed by its nested
    children, so depth-based indentation reads as a tree;
  * one plain ``dict`` per detection carrying every field the detection report
    shows (FR-MS-6): scale, nesting depth, the parent's id and label, the
    agreement/conflict relation, directional bias, and the null-FPR fields.

This is a presentation helper over the existing ``Detection`` data model; it
computes nothing new about the patterns themselves.  The chart-decomp service
reuses :func:`order_forest` / :func:`build_nesting_report` to serialise a
``MultiScaleResult`` for the frontend.
"""
from __future__ import annotations

from chart_decomp.domain.entities import Detection


def detection_label(d: Detection) -> str:
    """Human-readable handle for a detection, e.g. ``'Head & Shoulders #3'``.

    Falls back to the bare pattern name when no ``detection_id`` is assigned.
    """
    if d.detection_id is None:
        return d.pattern
    return f"{d.pattern} #{d.detection_id}"


def order_forest(detections: list[Detection]) -> list[Detection]:
    """Return ``detections`` in nesting forest pre-order.

    Roots (parentless detections), sorted by start index, come first; each is
    immediately followed by its descendant subtree (also sorted by start index),
    recursively.  Children are derived from ``parent_id`` so the ordering is
    correct even if ``children_ids`` was not maintained.  Any detection not
    reachable from a root (defensive: malformed input) is appended at the end.
    """
    by_id = {d.detection_id: d for d in detections if d.detection_id is not None}

    children: dict[int, list[Detection]] = {}
    roots: list[Detection] = []
    for d in detections:
        if d.parent_id is not None and d.parent_id in by_id:
            children.setdefault(d.parent_id, []).append(d)
        else:
            roots.append(d)

    def _key(d: Detection):
        return (d.start_index, d.detection_id if d.detection_id is not None else 0)

    roots.sort(key=_key)
    for lst in children.values():
        lst.sort(key=_key)

    ordered: list[Detection] = []
    seen: set[int] = set()

    def _visit(d: Detection) -> None:
        if d.detection_id in seen:
            return
        seen.add(d.detection_id)
        ordered.append(d)
        for c in children.get(d.detection_id, []):
            _visit(c)

    for r in roots:
        _visit(r)

    # Defensive: surface any detection left unvisited (e.g. dangling parent_id).
    for d in detections:
        if d.detection_id not in seen:
            ordered.append(d)
            seen.add(d.detection_id)

    return ordered


def _row(d: Detection, by_id: dict[int, Detection]) -> dict:
    parent = by_id.get(d.parent_id) if d.parent_id is not None else None
    return {
        "detection_id": d.detection_id,
        "pattern": d.pattern,
        "label": detection_label(d),
        "scale": d.scale,
        "start_index": d.start_index,
        "end_index": d.end_index,
        "score": d.score,
        "null_percentile": d.null_percentile,
        "noteworthy": d.noteworthy,
        "confirmed": d.confirmed,
        "nesting_depth": d.nesting_depth,
        "parent_id": d.parent_id,
        "parent_label": detection_label(parent) if parent is not None else None,
        "relation_to_parent": d.relation_to_parent,
        "directional_bias": d.directional_bias,
        "also_seen_at_scales": list(d.also_seen_at_scales),
    }


def build_nesting_report(detections: list[Detection]) -> list[dict]:
    """Build forest-ordered report rows from a multi-scale detection list (FR-MS-6).

    Each row is a dict with the display fields (see :func:`_row`).  Rows are in
    forest pre-order so a table can indent by ``nesting_depth`` to show nesting.
    Pass ``MultiScaleResult.detections``; the report-level
    ``spurious_nesting_fpr`` lives on the result, not on individual rows.
    """
    by_id = {d.detection_id: d for d in detections if d.detection_id is not None}
    return [_row(d, by_id) for d in order_forest(detections)]
