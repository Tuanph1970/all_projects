"""
Price position screen -- the subject of the layout tests.

Locators lean on testIDs where React Native exposes them, and on visible text
for the section headings, which are plain Text nodes.
"""
from __future__ import annotations

import logging

from selenium.webdriver.common.by import By

from base.base_page import BasePage

logger = logging.getLogger(__name__)


class PricePositionPage(BasePage):
    SCREEN = (By.XPATH, '//*[@resource-id="price-position-screen"]')
    LOADING = (By.XPATH, '//*[@resource-id="price-position-loading"]')
    ERROR = (By.XPATH, '//*[@resource-id="price-position-error"]')

    POSITION_LABEL = (By.XPATH, '//*[@resource-id="price-position-label"]')
    NO_MARKET = (By.XPATH, '//*[@resource-id="price-position-no-market"]')

    BENCHMARK_CAVEAT = (By.XPATH, '//*[@resource-id="benchmark-caveat"]')
    URL_INPUT = (By.XPATH, '//*[@resource-id="comparable-url-input"]')
    ADD_BUTTON = (By.XPATH, '//*[@resource-id="comparable-add-button"]')
    EDIT_BUTTON = (By.XPATH, '//*[@resource-id="price-position-edit-button"]')

    HEADING_MARKET = (By.XPATH, '//*[@text="The market"]')
    HEADING_WIDER = (By.XPATH, '//*[@text="The wider market"]')
    HEADING_TRACKED = (By.XPATH, '//*[contains(@text, "Listings you")]')

    # A Vietnamese dong amount, e.g. "185.000₫".
    ANY_PRICE = (By.XPATH, '//*[contains(@text, "₫")]')

    def wait_until_loaded(self, timeout: int = 25):
        assert self.is_visible(*self.SCREEN, timeout=timeout), \
            "Price position screen never appeared"
        assert not self.is_visible(*self.ERROR, timeout=1), \
            "Price position screen rendered its error state"
        return self

    def has_market_view(self) -> bool:
        return self.is_visible(*self.POSITION_LABEL, timeout=3)

    def has_no_market_state(self) -> bool:
        return self.is_visible(*self.NO_MARKET, timeout=3)

    def prices_on_screen(self):
        return self.find_all(*self.ANY_PRICE)

    def add_comparable(self, url: str):
        self.scroll_to_text("Listings you")
        self.type_text(*self.URL_INPUT, url)
        self.hide_keyboard()
        self.tap(*self.ADD_BUTTON)
        return self
