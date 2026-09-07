"""
The signed-in app shell: tab bar and logout.

Two facts here were found the hard way and are the reason this file exists
rather than the assertions living inline in the tests.

1. The tab bar differs by role. MainNavigator.jsx:189 switches on user.role,
   so a customer lands on a bar containing `tab-home` and a seller on one
   containing `tab-dashboard`. "Did login succeed?" therefore has a different
   answer for each role, and asserting the wrong one reads as a login failure.

2. Logout is NOT one control. The customer's ProfileScreen uses
   `profile-logout-button` and the seller's SellerProfileScreen uses
   `logout-button`. The old Maestro scripts assumed `logout-button` for both,
   which cannot have worked for a customer.

Logout then raises a native Android confirm dialog, whose buttons are real
Android views (android:id/button1 = positive), not React Native ones.
"""
from __future__ import annotations

import logging
import time

from selenium.webdriver.common.by import By

from base.base_page import BasePage

logger = logging.getLogger(__name__)

# tabBarTestID is `tab-${route.name.toLowerCase()}` (MainNavigator.jsx:82).
TAB_HOME = (By.XPATH, '//*[@resource-id="tab-home"]')
TAB_DASHBOARD = (By.XPATH, '//*[@resource-id="tab-dashboard"]')
TAB_PROFILE = (By.XPATH, '//*[@resource-id="tab-profile"]')


class ShellPage(BasePage):
    CUSTOMER_LOGOUT = (By.XPATH, '//*[@resource-id="profile-logout-button"]')
    SELLER_LOGOUT = (By.XPATH, '//*[@resource-id="logout-button"]')

    # Native dialog. button1 is the positive action.
    DIALOG_CONFIRM = (By.ID, "android:id/button1")
    DIALOG_CONFIRM_BY_TEXT = (By.XPATH, '//*[@text="Đăng xuất"]')

    def landed_as_customer(self, timeout: int = 20) -> bool:
        return self.is_visible(*TAB_HOME, timeout=timeout)

    def landed_as_seller(self, timeout: int = 20) -> bool:
        return self.is_visible(*TAB_DASHBOARD, timeout=timeout)

    def is_signed_in(self, timeout: int = 20) -> bool:
        """True if either role's shell is showing."""
        return self.landed_as_customer(timeout=timeout) or self.landed_as_seller(
            timeout=3
        )

    def open_profile_tab(self):
        self.tap(*TAB_PROFILE)
        time.sleep(1)
        return self

    def logout(self, role: str):
        """Open the profile tab, hit that role's logout, confirm the dialog."""
        if role not in ("customer", "seller"):
            raise ValueError(f"role must be 'customer' or 'seller', got {role!r}")

        self.open_profile_tab()
        button = self.CUSTOMER_LOGOUT if role == "customer" else self.SELLER_LOGOUT

        # Both profile screens are longer than the viewport, and Android omits
        # off-screen views from the accessibility tree -- an un-scrolled logout
        # button reads as "not found" rather than "below the fold".
        self.scroll_until_present(*button)
        self.tap(*button)
        time.sleep(1)

        self.log("confirming logout dialog")
        if self.is_present(*self.DIALOG_CONFIRM, timeout=5):
            self.tap(*self.DIALOG_CONFIRM)
        else:
            self.tap(*self.DIALOG_CONFIRM_BY_TEXT)
        time.sleep(2)
        return self
