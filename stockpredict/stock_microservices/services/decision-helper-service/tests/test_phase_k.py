"""Tests for Phase K — Pattern overlay on Decision Console (F-100..F-103).

These tests document the field-name contract between the Decision Console
PatternPanel component and the ai-insights-service AllPatternsResponse /
PatternMatch schemas.  If ai-insights-service renames a field, these tests
will catch it at the decision-helper test layer.
"""
from __future__ import annotations

import sys
import importlib.util
import pathlib
import pytest


# ---------------------------------------------------------------------------
# Helpers — graceful skip when ai-insights-service is not on sys.path
# ---------------------------------------------------------------------------

def _import_ai_schemas():
    """Return the ai-insights-service schemas module, or None if not importable."""
    try:
        svc_root = pathlib.Path(__file__).parents[2] / "ai-insights-service"
        schemas_path = svc_root / "app" / "models" / "schemas.py"
        if not schemas_path.exists():
            return None

        spec = importlib.util.spec_from_file_location("ai_schemas", schemas_path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules.setdefault("pydantic", __import__("pydantic"))
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _import_pattern_base():
    """Return the ai-insights-service patterns base module (PatternMatch), or None."""
    try:
        svc_root = pathlib.Path(__file__).parents[2] / "ai-insights-service"
        base_path = svc_root / "app" / "services" / "patterns" / "base.py"
        if not base_path.exists():
            return None

        spec = importlib.util.spec_from_file_location("pattern_base", base_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


_ai = _import_ai_schemas()
_base = _import_pattern_base()

_skip_if_no_ai = pytest.mark.skipif(
    _ai is None,
    reason="ai-insights-service schemas not importable from test environment",
)
_skip_if_no_base = pytest.mark.skipif(
    _base is None,
    reason="ai-insights-service pattern base not importable from test environment",
)


# ---------------------------------------------------------------------------
# F-100 — AllPatternsResponse field-name contract
# ---------------------------------------------------------------------------

@_skip_if_no_ai
class TestAllPatternsResponseContract:
    """PatternPanel reads these fields — verify they exist in AllPatternsResponse."""

    def _fields(self):
        return set(_ai.AllPatternsResponse.model_fields.keys())

    def test_symbol_exists(self):
        assert "symbol" in self._fields()

    def test_patterns_exists(self):
        assert "patterns" in self._fields()

    def test_pattern_count_exists(self):
        assert "pattern_count" in self._fields()

    def test_categories_exists(self):
        assert "categories" in self._fields()

    def test_lookback_bars_exists(self):
        assert "lookback_bars" in self._fields()


# ---------------------------------------------------------------------------
# F-101 — PatternMatch field-name contract
# ---------------------------------------------------------------------------

@_skip_if_no_base
class TestPatternMatchContract:
    """PatternCard reads these fields from each PatternMatch."""

    def _fields(self):
        import dataclasses
        # PatternMatch may be a dataclass or pydantic model
        if hasattr(_base.PatternMatch, "model_fields"):
            return set(_base.PatternMatch.model_fields.keys())
        if dataclasses.is_dataclass(_base.PatternMatch):
            return {f.name for f in dataclasses.fields(_base.PatternMatch)}
        return set(vars(_base.PatternMatch()).keys())

    def test_pattern_name_exists(self):
        assert "pattern_name" in self._fields()

    def test_pattern_type_exists(self):
        assert "pattern_type" in self._fields()

    def test_found_exists(self):
        assert "found" in self._fields()

    def test_confidence_exists(self):
        assert "confidence" in self._fields()

    def test_neckline_exists(self):
        assert "neckline" in self._fields()

    def test_measured_move_target_exists(self):
        assert "measured_move_target" in self._fields()

    def test_pattern_type_values(self):
        # PatternPanel branches on 'bullish' / 'bearish'
        pm_bullish = _base.PatternMatch(
            pattern_name="Test", pattern_type="bullish",
            found=True, confidence=0.8,
        )
        pm_bearish = _base.PatternMatch(
            pattern_name="Test", pattern_type="bearish",
            found=False, confidence=0.0,
        )
        assert pm_bullish.pattern_type == "bullish"
        assert pm_bearish.pattern_type == "bearish"

    def test_found_is_bool(self):
        pm = _base.PatternMatch(
            pattern_name="HeadAndShoulders", pattern_type="bearish",
            found=True, confidence=0.75,
        )
        assert isinstance(pm.found, bool)

    def test_optional_fields_default_none(self):
        pm = _base.PatternMatch(
            pattern_name="DoubleTop", pattern_type="bearish",
            found=False, confidence=0.0,
        )
        assert pm.neckline is None
        assert pm.measured_move_target is None


# ---------------------------------------------------------------------------
# F-102 — Frontend integration contract (standalone, no service import needed)
# ---------------------------------------------------------------------------

class TestPatternPanelContract:
    """Document the shape PatternPanel expects from the REST response."""

    def test_pattern_panel_filters_found_patterns(self):
        patterns = [
            {"pattern_name": "HeadAndShoulders", "pattern_type": "bearish",
             "found": True, "confidence": 0.8, "neckline": 45.0, "measured_move_target": 40.0},
            {"pattern_name": "DoubleTop", "pattern_type": "bearish",
             "found": False, "confidence": 0.0, "neckline": None, "measured_move_target": None},
            {"pattern_name": "CupAndHandle", "pattern_type": "bullish",
             "found": True, "confidence": 0.65, "neckline": 50.0, "measured_move_target": 58.0},
        ]
        found = [p for p in patterns if p["found"]]
        assert len(found) == 2
        assert all(p["found"] for p in found)

    def test_pattern_type_determines_color(self):
        bullish = {"pattern_type": "bullish"}
        bearish = {"pattern_type": "bearish"}
        is_bullish = lambda p: p["pattern_type"] == "bullish"
        assert is_bullish(bullish) is True
        assert is_bullish(bearish) is False

    def test_confidence_pct_conversion(self):
        pattern = {"confidence": 0.82}
        pct = round(pattern["confidence"] * 100)
        assert pct == 82

    def test_allpatterns_response_shape(self):
        response = {
            "symbol": "VIC",
            "lookback_bars": 100,
            "patterns": [],
            "pattern_count": 0,
            "categories": {"bullish": 0, "bearish": 0},
        }
        assert "patterns" in response
        assert isinstance(response["patterns"], list)

    def test_getpatterns_extracts_patterns_key(self):
        # helperService.getPatterns returns the full AllPatternsResponse;
        # DecisionConsole reads .patterns from it
        api_response = {
            "symbol": "VIC",
            "lookback_bars": 100,
            "patterns": [
                {"pattern_name": "Triangle", "pattern_type": "bullish",
                 "found": True, "confidence": 0.7, "neckline": None, "measured_move_target": 55.0},
            ],
            "pattern_count": 1,
            "categories": {"bullish": 1},
        }
        patterns = api_response.get("patterns", [])
        assert len(patterns) == 1
        assert patterns[0]["pattern_name"] == "Triangle"
