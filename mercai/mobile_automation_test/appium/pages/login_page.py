"""
Login page object.

Locator strategy is inherited from the mathematic-mobile harness, and the
reason is worth repeating because it is not obvious: React Native exposes a
TextInput's `testID` as an Android `resource-id`, but plain Text and most
composed Pressables do NOT reliably do so. Inputs are therefore addressed by
resource-id and everything else by text.
"""
from __future__ import annotations

import logging

from appium.webdriver.webdriver import WebDriver
from selenium.webdriver.common.by import By

from base.base_page import BasePage
from base.config import config

logger = logging.getLogger(__name__)


class LoginPage(BasePage):
    USERNAME_INPUT = (By.XPATH, '//*[@resource-id="login-username-input"]')
    PASSWORD_INPUT = (By.XPATH, '//*[@resource-id="login-password-input"]')
    SUBMIT_BUTTON = (By.XPATH, '//*[@resource-id="login-submit-button"]')
    REGISTER_LINK = (By.XPATH, '//*[@resource-id="login-register-link"]')
    FORGOT_PASSWORD_LINK = (
        By.XPATH,
        '//*[@resource-id="login-forgot-password-link"]',
    )

    def is_showing(self, timeout: int = 5) -> bool:
        return self.is_visible(*self.USERNAME_INPUT, timeout=timeout)

    def login(self, username: str | None = None, password: str | None = None):
        username = username or config.backend.seller_username
        password = password or config.backend.seller_password

        self.log(f"logging in as {username}")
        self.type_text(*self.USERNAME_INPUT, username)
        self.type_text(*self.PASSWORD_INPUT, password)
        self.hide_keyboard()
        self.tap(*self.SUBMIT_BUTTON)
        return self

    def submit_credentials(self, username: str, password: str):
        """
        Type whatever is given -- including empty strings -- and submit.

        Separate from login() because that one falls back to the configured
        seller when an argument is falsy, which would silently turn the
        empty-field test into a valid login.
        """
        self.log(f"submitting username={username!r} password={'*' * len(password)}")
        if username:
            self.type_text(*self.USERNAME_INPUT, username)
        else:
            self.find_visible(*self.USERNAME_INPUT).clear()
        if password:
            self.type_text(*self.PASSWORD_INPUT, password)
        else:
            self.find_visible(*self.PASSWORD_INPUT).clear()
        self.hide_keyboard()
        self.tap(*self.SUBMIT_BUTTON)
        return self

    def open_register(self):
        self.tap(*self.REGISTER_LINK)
        return self

    def still_showing_after_attempt(self, timeout: int = 8) -> bool:
        """
        The assertion for every rejected login.

        A failed login surfaces as a react-native-toast-message Toast, which
        is transient and unreliable to catch -- by the time Appium walks the
        tree it may already be gone. Staying on the login screen is the
        durable, observable consequence, so that is what is asserted.
        """
        return self.is_visible(*self.USERNAME_INPUT, timeout=timeout)
