"""
Registration page object.

Locator strategy follows login_page.py: a React Native TextInput exposes its
`testID` as an Android resource-id, but plain Text and most composed
Pressables do not. Inputs are therefore addressed by resource-id and
everything else by visible text.

The role selector is the exception worth explaining. `register-role-customer`
and `register-role-seller` are testIDs on plain <View> wrappers around a
react-native-paper <RadioButton>. Tapping the wrapper does not reliably toggle
the radio, because the RadioButton owns its own press handler -- so these
locators are used to SCROLL to the control, and the tap goes to the radio's
visible label instead. The labels are Vietnamese because the app defaults to
LANGUAGES.VI (see front_end/src/i18n/LanguageContext.jsx:45).
"""
from __future__ import annotations

import logging
import time

from selenium.webdriver.common.by import By

from base.base_page import BasePage

logger = logging.getLogger(__name__)


class RegisterPage(BasePage):
    FIRSTNAME_INPUT = (By.XPATH, '//*[@resource-id="register-firstname-input"]')
    LASTNAME_INPUT = (By.XPATH, '//*[@resource-id="register-lastname-input"]')
    USERNAME_INPUT = (By.XPATH, '//*[@resource-id="register-username-input"]')
    EMAIL_INPUT = (By.XPATH, '//*[@resource-id="register-email-input"]')
    PASSWORD_INPUT = (By.XPATH, '//*[@resource-id="register-password-input"]')
    CONFIRM_PASSWORD_INPUT = (
        By.XPATH,
        '//*[@resource-id="register-confirm-password-input"]',
    )
    SUBMIT_BUTTON = (By.XPATH, '//*[@resource-id="register-submit-button"]')
    LOGIN_LINK = (By.XPATH, '//*[@resource-id="register-login-link"]')

    ROLE_CUSTOMER_ROW = (By.XPATH, '//*[@resource-id="register-role-customer"]')
    ROLE_SELLER_ROW = (By.XPATH, '//*[@resource-id="register-role-seller"]')

    # Visible radio labels, vi locale.
    ROLE_CUSTOMER_LABEL = (By.XPATH, '//*[@text="Khách hàng"]')
    ROLE_SELLER_LABEL = (By.XPATH, '//*[@text="Người bán"]')

    def is_showing(self, timeout: int = 5) -> bool:
        return self.is_visible(*self.USERNAME_INPUT, timeout=timeout)

    def select_role(self, role: str):
        """Pick customer or seller. Scrolls the control into view first."""
        if role not in ("customer", "seller"):
            raise ValueError(f"role must be 'customer' or 'seller', got {role!r}")

        row = self.ROLE_CUSTOMER_ROW if role == "customer" else self.ROLE_SELLER_ROW
        label = (
            self.ROLE_CUSTOMER_LABEL if role == "customer" else self.ROLE_SELLER_LABEL
        )

        self.log(f"selecting role {role}")
        self.scroll_until_present(*row)
        self.tap(*label)
        return self

    def fill(
        self,
        *,
        first_name: str,
        last_name: str,
        username: str,
        email: str,
        password: str,
        confirm_password: str | None = None,
    ):
        """Fill every field. Does not submit."""
        self.log(f"filling registration form for {username}")
        self.type_text(*self.FIRSTNAME_INPUT, first_name)
        self.type_text(*self.LASTNAME_INPUT, last_name)
        self.type_text(*self.USERNAME_INPUT, username)
        self.type_text(*self.EMAIL_INPUT, email)
        self.type_text(*self.PASSWORD_INPUT, password)
        self.type_text(
            *self.CONFIRM_PASSWORD_INPUT,
            confirm_password if confirm_password is not None else password,
        )
        self.hide_keyboard()
        return self

    def submit(self):
        self.scroll_until_present(*self.SUBMIT_BUTTON)
        self.tap(*self.SUBMIT_BUTTON)
        # Registration is a network round trip; the screen only changes after
        # it resolves.
        time.sleep(2)
        return self
