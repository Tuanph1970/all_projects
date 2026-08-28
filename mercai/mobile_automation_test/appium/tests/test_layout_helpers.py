"""
Unit tests for the layout assertions themselves.

These need no device: the helpers only read `.location`, `.size` and `.text`
off an element, so a stub is enough. Worth having, because an assertion helper
that is subtly wrong is worse than none -- it produces confident green on a
broken screen, and nobody re-reads a passing test.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from base import layout


class FakeElement:
    def __init__(self, x, y, w, h, text=""):
        self.location = {"x": x, "y": y}
        self.size = {"width": w, "height": h}
        self.text = text


class FakeDriver:
    def __init__(self, width=1080, height=2220, dpi=440):
        self._size = {"width": width, "height": height}
        self._dpi = dpi

    def get_window_size(self):
        return self._size

    def get_display_density(self):
        return self._dpi


@pytest.fixture()
def driver():
    return FakeDriver()


# ── within screen ───────────────────────────────────────────────────────────

def test_an_element_inside_the_viewport_passes(driver):
    layout.assert_within_screen(driver, FakeElement(40, 100, 500, 80), "x")


def test_overflowing_the_right_edge_fails(driver):
    """The narrow-device case: a stat row wider than the screen."""
    with pytest.raises(AssertionError, match="overflows the right edge"):
        layout.assert_within_screen(driver, FakeElement(700, 100, 500, 80), "stat row")


def test_a_negative_left_fails(driver):
    with pytest.raises(AssertionError, match="left edge"):
        layout.assert_within_screen(driver, FakeElement(-5, 100, 200, 80), "x")


def test_extending_below_the_screen_fails(driver):
    with pytest.raises(AssertionError, match="below the screen"):
        layout.assert_within_screen(driver, FakeElement(0, 2200, 200, 80), "x")


# ── ordering and overlap ────────────────────────────────────────────────────

def test_correct_reading_order_passes():
    layout.assert_above(FakeElement(0, 0, 100, 50), FakeElement(0, 60, 100, 50), "a", "b")


def test_reversed_order_fails():
    with pytest.raises(AssertionError, match="does not sit above"):
        layout.assert_above(FakeElement(0, 60, 100, 50), FakeElement(0, 0, 100, 50), "a", "b")


def test_touching_edges_counts_as_ordered():
    """bottom == top is adjacent, not overlapping."""
    layout.assert_above(FakeElement(0, 0, 100, 50), FakeElement(0, 50, 100, 50), "a", "b")


def test_side_by_side_elements_do_not_overlap():
    layout.assert_no_overlap(FakeElement(0, 0, 100, 50), FakeElement(120, 0, 100, 50), "a", "b")


def test_intersecting_elements_overlap():
    with pytest.raises(AssertionError, match="overlaps"):
        layout.assert_no_overlap(FakeElement(0, 0, 100, 50), FakeElement(50, 25, 100, 50), "a", "b")


# ── tap targets ─────────────────────────────────────────────────────────────

def test_a_48dp_target_passes_at_high_density(driver):
    # 440dpi -> density 2.75 -> 48dp is 132px
    layout.assert_tap_target(driver, FakeElement(0, 0, 140, 140), "button")


def test_a_small_target_fails(driver):
    with pytest.raises(AssertionError, match="minimum tap target"):
        layout.assert_tap_target(driver, FakeElement(0, 0, 40, 40), "button")


def test_density_is_read_from_the_device_not_assumed(driver):
    # The same 60px control passes on a low-density screen and fails on a high
    # one. Hard-coding 48 pixels would have silently passed both.
    layout.assert_tap_target(FakeDriver(dpi=160), FakeElement(0, 0, 60, 60), "b")
    with pytest.raises(AssertionError):
        layout.assert_tap_target(FakeDriver(dpi=440), FakeElement(0, 0, 60, 60), "b")


def test_unreadable_density_degrades_rather_than_erroring():
    class NoDensity(FakeDriver):
        def get_display_density(self):
            raise RuntimeError("not supported")

    assert layout.density(NoDensity()) == 1.0


# ── drawable area and truncation ────────────────────────────────────────────

def test_a_collapsed_element_has_no_drawable_area():
    with pytest.raises(AssertionError, match="no drawable area"):
        layout.assert_visible_area(FakeElement(10, 10, 0, 40), "chip")


def test_truncated_text_is_caught():
    with pytest.raises(AssertionError, match="truncated"):
        layout.assert_text_not_truncated(
            FakeElement(0, 0, 100, 20, "Bát tô gốm Bát Tràng men rạn thủ…"), "name")


def test_untruncated_text_passes():
    layout.assert_text_not_truncated(FakeElement(0, 0, 100, 20, "185.000₫"), "price")


def test_an_ascii_ellipsis_is_caught_too():
    with pytest.raises(AssertionError, match="truncated"):
        layout.assert_text_not_truncated(FakeElement(0, 0, 100, 20, "Bát tô..."), "name")


# ── clipping inside a container ─────────────────────────────────────────────

def test_content_inside_its_card_passes():
    layout.assert_not_clipped_horizontally(
        FakeElement(60, 100, 200, 40), FakeElement(40, 80, 400, 300), "bar", "card")


def test_content_escaping_its_card_fails():
    with pytest.raises(AssertionError, match="escapes"):
        layout.assert_not_clipped_horizontally(
            FakeElement(60, 100, 500, 40), FakeElement(40, 80, 400, 300), "bar", "card")
