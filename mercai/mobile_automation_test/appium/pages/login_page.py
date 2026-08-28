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
