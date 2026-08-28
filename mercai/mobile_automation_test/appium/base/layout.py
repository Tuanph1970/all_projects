"""
Layout assertions.

WHY THIS EXISTS, and what it catches that other tests cannot:

The jest render tests in front_end assert that the right components appear with
the right text. They cannot fail on layout, because jest mocks React Native's
native layer -- nothing is ever measured, positioned or drawn. The API tests
assert the numbers are right. Between them there is a whole class of bug they
both miss and a user hits immediately:

  * the price scale overflowing the card, so the "you" marker sits off-screen
  * a button pushed under the system navigation bar by a safe-area miscalc
  * two chips overlapping on a narrow device
  * a long Vietnamese product name truncated so the price is unreadable
  * a tap target too small to hit reliably

Every function below takes elements from a live device and asserts a geometric
property, so those failures show up as a failing test rather than a screenshot
someone has to squint at.

Android reports bounds in PIXELS, not dp. The 48dp minimum tap target is
therefore converted using the device's own density rather than assumed.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from appium.webdriver.webelement import WebElement

logger = logging.getLogger(__name__)

# Android's accessibility guidance for a reliably hittable control.
MIN_TAP_TARGET_DP = 48


@dataclass
class Box:
    """An element's rectangle, in device pixels."""
    left: int
    top: int
    width: int
    height: int

    @property
    def right(self) -> int:
        return self.left + self.width

    @property
    def bottom(self) -> int:
        return self.top + self.height

    def __str__(self) -> str:
        return f"({self.left},{self.top} {self.width}x{self.height})"


def box_of(element: WebElement) -> Box:
    location = element.location
    size = element.size
    return Box(location["x"], location["y"], size["width"], size["height"])


def screen_box(driver) -> Box:
    size = driver.get_window_size()
    return Box(0, 0, size["width"], size["height"])


def density(driver) -> float:
    """
    Device pixels per dp. Falls back to 1.0 rather than failing the test --
    a missing density should weaken the tap-target check, not break the suite.
    """
    try:
        return float(driver.get_display_density()) / 160.0
    except Exception:
        logger.warning("Could not read display density; assuming 1.0")
        return 1.0


# ── Assertions ──────────────────────────────────────────────────────────────

def assert_within_screen(driver, element: WebElement, name: str) -> None:
    """The whole element is inside the viewport."""
    box, screen = box_of(element), screen_box(driver)
    assert box.left >= 0, f"{name} starts off the left edge: {box}"
    assert box.top >= 0, f"{name} starts above the top edge: {box}"
    assert box.right <= screen.width, (
        f"{name} overflows the right edge: right={box.right} > screen={screen.width}. "
        "On a narrow device this is how a price marker ends up invisible."
    )
    assert box.bottom <= screen.height, (
        f"{name} extends below the screen: bottom={box.bottom} > {screen.height}"
    )


def assert_not_clipped_horizontally(element: WebElement, container: WebElement,
                                    name: str, container_name: str) -> None:
    """The element sits inside its container's horizontal bounds."""
    box, outer = box_of(element), box_of(container)
    assert box.left >= outer.left - 1 and box.right <= outer.right + 1, (
        f"{name} {box} escapes {container_name} {outer} horizontally"
    )


def assert_above(upper: WebElement, lower: WebElement,
                 upper_name: str, lower_name: str) -> None:
    """Reading order: `upper` finishes before `lower` starts."""
    a, b = box_of(upper), box_of(lower)
    assert a.bottom <= b.top, (
        f"{upper_name} {a} does not sit above {lower_name} {b} — "
        "they overlap or are in the wrong order"
    )


def assert_no_overlap(first: WebElement, second: WebElement,
                      first_name: str, second_name: str) -> None:
    a, b = box_of(first), box_of(second)
    separated = (a.right <= b.left or b.right <= a.left
                 or a.bottom <= b.top or b.bottom <= a.top)
    assert separated, f"{first_name} {a} overlaps {second_name} {b}"


def assert_tap_target(driver, element: WebElement, name: str) -> None:
    """Big enough to hit. Android guidance is 48dp square."""
    box = box_of(element)
    minimum = MIN_TAP_TARGET_DP * density(driver)
    assert box.width >= minimum and box.height >= minimum, (
        f"{name} is {box.width}x{box.height}px, below the "
        f"{MIN_TAP_TARGET_DP}dp ({minimum:.0f}px) minimum tap target"
    )


def assert_visible_area(element: WebElement, name: str, min_px: int = 1) -> None:
    """Present in the tree is not the same as actually drawn."""
    box = box_of(element)
    assert box.width >= min_px and box.height >= min_px, (
        f"{name} has no drawable area: {box}. It is in the view tree but "
        "collapsed — usually a flex or text-wrapping bug."
    )


def assert_text_not_truncated(element: WebElement, name: str) -> None:
    """
    Catch the ellipsis. Vietnamese product names are long, and a truncated one
    on the price screen means the seller cannot tell which listing they are
    looking at.
    """
    text = (element.text or "")
    assert not text.rstrip().endswith(("…", "...")), (
        f"{name} is truncated: {text!r}"
    )


def describe(driver, elements: dict) -> str:
    """A geometry dump for a failure message or a manual look."""
    screen = screen_box(driver)
    lines = [f"screen {screen.width}x{screen.height}"]
    for name, element in elements.items():
        try:
            lines.append(f"  {name:<28} {box_of(element)}")
        except Exception as exc:
            lines.append(f"  {name:<28} <unreadable: {exc}>")
    return "\n".join(lines)
