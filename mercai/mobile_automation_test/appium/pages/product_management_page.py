"""
Seller product list. The entry point to price insights.
"""
from __future__ import annotations

import logging

from selenium.webdriver.common.by import By

from base.base_page import BasePage

logger = logging.getLogger(__name__)


class ProductManagementPage(BasePage):
    DASHBOARD_TAB = (By.XPATH, '//*[@resource-id="tab-dashboard"]')

    @staticmethod
    def price_insights_button(product_id: int):
        """
        The chart-line control on a product row.

        Rendered only when `features.price_intel` is true for this seller, so
        its absence is a meaningful signal rather than a broken locator -- see
        ProductManagementScreen.jsx.
        """
        return (By.XPATH, f'//*[@resource-id="product-price-insights-{product_id}"]')

    def open_price_insights(self, product_id: int):
        locator = self.price_insights_button(product_id)
        assert self.is_visible(*locator, timeout=15), (
            f"No price-insights control on product {product_id}. Either the "
            "seller does not own it, or price_intel is disabled for them."
        )
        self.tap(*locator)
        return self
