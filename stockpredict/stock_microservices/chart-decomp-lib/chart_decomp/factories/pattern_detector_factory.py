"""Registry/factory for chart-pattern detectors (FR-PAT-EXT).

Mirrors ``decomposer_factory.py``'s name→implementation registry style, adapted
to the open/closed extensibility the SRS requires: new detectors (including a
future ML detector, FR-ML-1) are added by registering them, with no change to
``detect()`` or its callers.

A module-level ``default_registry`` holds the built-in detector set; the
``register_detector`` / ``detect_patterns`` functions operate on it and back the
public facade (added in A12). Callers that need isolation can instantiate their
own ``PatternDetectorRegistry``.
"""
from __future__ import annotations

from typing import Iterable, Optional, Union

import numpy as np

from chart_decomp.domain.entities import Detection, SwingSkeleton


class PatternDetectorRegistry:
    """Name → detector registry that runs and aggregates detectors.

    Design patterns:
        Registry — name→detector mapping for open/closed extensibility.
        Composite — ``detect`` runs all selected detectors as one operation.
    """

    def __init__(self) -> None:
        self._detectors: dict[str, object] = {}

    def register(self, detector, name: Optional[str] = None) -> None:
        """Register (or override) a detector under ``name`` (default detector.name)."""
        key = name or getattr(detector, "name", None)
        if not key:
            raise ValueError("detector must have a non-empty 'name' (or pass name=)")
        self._detectors[key] = detector

    def get(self, name: str):
        if name not in self._detectors:
            raise ValueError(
                f"Unknown detector '{name}'; registered: {self.names()}"
            )
        return self._detectors[name]

    def names(self) -> list[str]:
        return list(self._detectors.keys())

    def detect(
        self,
        skeleton: SwingSkeleton,
        x: np.ndarray,
        detectors: Union[str, Iterable[str]] = "all",
        params: Optional[dict] = None,
    ) -> list[Detection]:
        """Run the selected detectors and return their aggregated detections.

        Parameters
        ----------
        detectors : "all" or an iterable of registered names.
        params    : optional dict {detector_name: params_object}; a detector
                    receives its own params (or None → its default).

        Detections are returned sorted by ``start_index``.
        """
        names = self._resolve(detectors)
        params = params or {}
        out: list[Detection] = []
        for nm in names:
            out.extend(self._detectors[nm].detect(skeleton, x, params.get(nm)))
        out.sort(key=lambda d: d.start_index)
        return out

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _resolve(self, detectors: Union[str, Iterable[str]]) -> list[str]:
        if detectors == "all":
            return self.names()
        requested = list(detectors)
        unknown = [n for n in requested if n not in self._detectors]
        if unknown:
            raise ValueError(
                f"Unknown detector(s) {unknown}; registered: {self.names()}"
            )
        return requested


# ── Module-level default registry + convenience functions ────────────────────

default_registry = PatternDetectorRegistry()


def register_detector(detector, name: Optional[str] = None) -> None:
    """Register a detector on the default registry (FR-PAT-EXT)."""
    default_registry.register(detector, name)


def detect_patterns(
    skeleton: SwingSkeleton,
    x: np.ndarray,
    detectors: Union[str, Iterable[str]] = "all",
    params: Optional[dict] = None,
) -> list[Detection]:
    """Run the default registry's detectors over a swing skeleton."""
    return default_registry.detect(skeleton, x, detectors, params)
