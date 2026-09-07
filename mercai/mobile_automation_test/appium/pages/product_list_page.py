"""
Customer-facing product list, plus the product detail screen it opens.

Locator strategy matches the rest of the suite: inputs and testID'd controls by
resource-id, everything else by visible text. Product rows carry per-id testIDs
(`product-card-{id}`, `product-name-{id}`, `product-price-{id}`) which is why
these assertions can be specific rather than "something appeared".
"""
from __future__ import annotations

import logging
import re
import time

from selenium.webdriver.common.by import By

from base.base_page import BasePage

logger = logging.getLogger(__name__)

HOME_VIEW_ALL = (By.XPATH, '//*[@resource-id="home-view-all-products-button"]')


class ProductListPage(BasePage):
    SCREEN = (By.XPATH, '//*[@resource-id="product-list-screen"]')
    LIST = (By.XPATH, '//*[@resource-id="product-list"]')
    SEARCH_BAR = (By.XPATH, '//*[@resource-id="product-list-search-bar"]')
    SORT_BUTTON = (By.XPATH, '//*[@resource-id="product-sort-button"]')
    RESULTS_COUNT = (By.XPATH, '//*[@resource-id="results-count"]')
    SORT_INFO = (By.XPATH, '//*[@resource-id="sort-info"]')
    CATEGORY_ALL = (By.XPATH, '//*[@resource-id="category-all"]')

    SORT_PRICE_LOW_HIGH = (By.XPATH, '//*[@resource-id="sort-price-low-high"]')
    SORT_PRICE_HIGH_LOW = (By.XPATH, '//*[@resource-id="sort-price-high-low"]')
    SORT_NEWEST = (By.XPATH, '//*[@resource-id="sort-newest"]')

    def open_from_home(self):
        """Home -> "view all products" -> the list screen."""
        self.scroll_until_present(*HOME_VIEW_ALL)
        self.tap(*HOME_VIEW_ALL)
        time.sleep(1.5)
        return self

    def is_showing(self, timeout: int = 20) -> bool:
        return self.is_visible(*self.SCREEN, timeout=timeout)

    # ── reading what is on screen ───────────────────────────────────────────

    def results_count(self) -> int:
        """The "N products" label, as an int."""
        text = self.find_visible(*self.RESULTS_COUNT).text
        match = re.search(r"(\d+)", text)
        if not match:
            raise AssertionError(f"could not read a count from {text!r}")
        return int(match.group(1))

    def sort_label(self) -> str:
        return self.find_visible(*self.SORT_INFO).text

    def card(self, product_id: int):
        return (By.XPATH, f'//*[@resource-id="product-card-{product_id}"]')

    def name_of(self, product_id: int):
        return (By.XPATH, f'//*[@resource-id="product-name-{product_id}"]')

    def shows_product(self, product_id: int, timeout: int = 10) -> bool:
        return self.is_visible(*self.card(product_id), timeout=timeout)

    def visible_product_names(self) -> list[str]:
        """
        Names currently in the accessibility tree, in tree order.

        Android omits off-screen views entirely, so this is what is on screen
        -- not the whole list. Ordering assertions must therefore compare
        positions of items that are BOTH visible, which is why the fixture
        catalogue is small enough to fit on one screen.
        """
        nodes = self.find_all(
            By.XPATH, '//*[contains(@resource-id,"product-name-")]'
        )
        return [n.text for n in nodes if n.text]

    # ── actions ─────────────────────────────────────────────────────────────

    def sort_by(self, order: str):
        """order: 'price_asc' | 'price_desc' | 'newest'"""
        locator = {
            "price_asc": self.SORT_PRICE_LOW_HIGH,
            "price_desc": self.SORT_PRICE_HIGH_LOW,
            "newest": self.SORT_NEWEST,
        }[order]

        self.log(f"sorting by {order}")
        self.tap(*self.SORT_BUTTON)
        time.sleep(0.8)
        self.tap(*locator)
        # The list re-queries the backend, so give it the round trip.
        time.sleep(2.5)
        return self

    def search(self, query: str):
        self.log(f"searching the list for {query!r}")
        self.type_text(*self.SEARCH_BAR, query)
        self.hide_keyboard()
        time.sleep(2.5)
        return self

    def open_product(self, product_id: int):
        self.scroll_until_present(*self.card(product_id))
        self.tap(*self.card(product_id))
        time.sleep(1.5)
        return self


class ProductDetailsPage(BasePage):
    SCREEN = (By.XPATH, '//*[@resource-id="product-details-screen"]')
    ADD_TO_CART = (By.XPATH, '//*[@resource-id="product-add-to-cart-button"]')
    BUY_NOW = (By.XPATH, '//*[@resource-id="product-buy-now-button"]')
    QUANTITY_TEXT = (By.XPATH, '//*[@resource-id="product-quantity-text"]')
    QUANTITY_PLUS = (By.XPATH, '//*[@resource-id="product-quantity-plus"]')
    QUANTITY_MINUS = (By.XPATH, '//*[@resource-id="product-quantity-minus"]')
    BACK_BUTTON = (By.XPATH, '//*[@resource-id="product-details-back-button"]')

    def is_showing(self, timeout: int = 20) -> bool:
        return self.is_visible(*self.SCREEN, timeout=timeout)

    def quantity(self) -> int:
        return int(self.find_visible(*self.QUANTITY_TEXT).text.strip())

    def increment_quantity(self):
        self.tap(*self.QUANTITY_PLUS)
        time.sleep(0.5)
        return self

    def shows_text(self, text: str, timeout: int = 8) -> bool:
        return self.is_visible(By.XPATH, f'//*[@text="{text}"]', timeout=timeout)
