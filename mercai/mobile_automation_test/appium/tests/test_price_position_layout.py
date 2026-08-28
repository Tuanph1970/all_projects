"""
Layout tests for the price intelligence screens.

WHAT THESE COVER THAT NOTHING ELSE DOES

  front_end jest (9 tests)  the right components render with the right text.
                            Cannot fail on layout: jest mocks React Native's
                            native layer, so nothing is measured or drawn.
  API tests (16)            the numbers are right.
  THESE                     the pixels are right.

Between the first two sits a class of bug a user hits on first launch and no
existing test can see: a scale overflowing its card, a button under the system
navigation bar, overlapping chips, a truncated product name.

REQUIREMENTS
  * a device or emulator, and an Appium server on 127.0.0.1:4723
  * the mercai app installed (see README -- Expo is managed, so an APK needs
    `npx expo prebuild -p android` first)
  * the seeded catalogue, and INTEL_PRICE_ENABLED=true

    pytest tests/test_price_position_layout.py -v
"""
from __future__ import annotations

import logging

import pytest
from appium.webdriver.webdriver import WebDriver

from base import layout
from base.config import config
from pages.login_page import LoginPage
from pages.price_position_page import PricePositionPage
from pages.product_management_page import ProductManagementPage

logger = logging.getLogger(__name__)

# Seeded by back_end/scripts/seed_catalogue.py as SEED-BAT-002, owned by
# gomthuha and priced 185,000d -- the listing with a real price history.
SEEDED_PRODUCT_ID = 2


@pytest.mark.layout
class TestPricePositionLayout:
    """Geometry of the price position screen on a real device."""

    @pytest.fixture(autouse=True)
    def setup(self, driver: WebDriver):
        self.driver = driver
        self.login = LoginPage(driver)
        self.products = ProductManagementPage(driver)
        self.screen = PricePositionPage(driver)

        if self.login.is_showing(timeout=8):
            self.login.login()

        self.products.open_price_insights(SEEDED_PRODUCT_ID)
        self.screen.wait_until_loaded()

    # ── The screen is in a valid state at all ───────────────────────────────

    def test_shows_exactly_one_of_position_or_no_market(self):
        """
        A blank screen is the failure this guards against, and it is the one
        most likely to appear only on a device -- both states render fine under
        jest.
        """
        has_position = self.screen.has_market_view()
        has_empty_state = self.screen.has_no_market_state()
        assert has_position != has_empty_state, (
            f"expected exactly one state, got position={has_position} "
            f"no_market={has_empty_state}"
        )

    # ── Geometry ────────────────────────────────────────────────────────────

    def test_the_position_label_is_fully_on_screen(self):
        if not self.screen.has_market_view():
            pytest.skip("no market view for this product on this deployment")
        label = self.screen.find(*PricePositionPage.POSITION_LABEL)
        layout.assert_within_screen(self.driver, label, "position chip")
        layout.assert_visible_area(label, "position chip")

    def test_every_price_is_fully_on_screen(self):
        """
        The stat row packs five figures across the width. On a narrow device
        the outer ones are the first thing to overflow, and an unreadable p75
        is worse than no p75.
        """
        prices = self.screen.prices_on_screen()
        assert prices, "no dong amount rendered anywhere on the screen"
        for index, element in enumerate(prices):
            layout.assert_within_screen(self.driver, element, f"price[{index}]")

    def test_no_price_is_truncated(self):
        for index, element in enumerate(self.screen.prices_on_screen()):
            layout.assert_text_not_truncated(element, f"price[{index}]")

    def test_reading_order_is_position_then_market_then_tracked(self):
        """Sections must appear in the order the copy assumes."""
        if not self.screen.has_market_view():
            pytest.skip("no market view for this product on this deployment")
        label = self.screen.find(*PricePositionPage.POSITION_LABEL)
        self.screen.scroll_to_text("Listings you")
        tracked = self.screen.find(*PricePositionPage.HEADING_TRACKED)
        layout.assert_above(label, tracked, "position chip", "tracked listings")

    # ── Interactive controls ────────────────────────────────────────────────

    def test_the_add_comparable_control_is_hittable(self):
        self.screen.scroll_to_text("Listings you")
        button = self.screen.find(*PricePositionPage.ADD_BUTTON)
        layout.assert_within_screen(self.driver, button, "add comparable button")
        layout.assert_tap_target(self.driver, button, "add comparable button")

    def test_the_url_field_and_its_button_do_not_overlap(self):
        self.screen.scroll_to_text("Listings you")
        field = self.screen.find(*PricePositionPage.URL_INPUT)
        button = self.screen.find(*PricePositionPage.ADD_BUTTON)
        layout.assert_no_overlap(field, button, "url field", "add button")
        layout.assert_above(field, button, "url field", "add button")

    def test_the_edit_button_clears_the_bottom_inset(self):
        """
        The screen ends with a button inside a safe-area padding calculation.
        Getting that wrong puts it under the system navigation bar, where it
        renders perfectly and cannot be tapped.
        """
        self.screen.scroll_to_text("Edit this listing")
        button = self.screen.find(*PricePositionPage.EDIT_BUTTON)
        layout.assert_within_screen(self.driver, button, "edit listing button")
        layout.assert_tap_target(self.driver, button, "edit listing button")

    # ── The benchmark block ─────────────────────────────────────────────────

    def test_the_benchmark_caveat_travels_with_its_numbers(self):
        """
        The Tiki benchmark's p75 is roughly three times the seller's own. The
        caveat explaining that is the only thing standing between those numbers
        and a bad pricing decision, so it must be on screen with them, not
        scrolled away or clipped.
        """
        if not self.screen.scroll_to_text("The wider market"):
            pytest.skip("no benchmark configured for this product's category")
        caveat = self.screen.find(*PricePositionPage.BENCHMARK_CAVEAT)
        layout.assert_within_screen(self.driver, caveat, "benchmark caveat")
        layout.assert_visible_area(caveat, "benchmark caveat")
        layout.assert_text_not_truncated(caveat, "benchmark caveat")

    # ── A record for a human ────────────────────────────────────────────────

    def test_capture_reference_screenshots(self):
        """Not an assertion -- a durable visual record next to the geometry."""
        self.screen.screenshot("price_position_top")
        self.screen.scroll_to_text("Listings you")
        self.screen.screenshot("price_position_tracked")
        logger.info("\n%s", layout.describe(self.driver, {
            "screen": self.screen.find(*PricePositionPage.SCREEN),
        }))
