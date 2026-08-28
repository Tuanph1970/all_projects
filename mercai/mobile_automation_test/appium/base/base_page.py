"""
Base Page Object -- common methods for all page objects.

Ported verbatim from mathematic-mobile's Appium harness so the two suites stay
recognisable to the same reader. Only `scroll_to_text` and the geometry helper
below are new, and both exist because the mercai price screen is long enough
that half its content starts below the fold.
"""
from __future__ import annotations

import time
import logging
from pathlib import Path
from typing import Optional, Tuple

from appium.webdriver.webdriver import WebDriver
from appium.webdriver.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from .config import config

logger = logging.getLogger(__name__)


class BasePage:
    """Base class for all page objects."""

    # Default wait timeout for explicit waits
    _wait_timeout: int = config.explicit_wait

    def __init__(self, driver: WebDriver):
        self.driver: WebDriver = driver
        self._wait = WebDriverWait(driver, self._wait_timeout)

    # ── Element Finding ───────────────────────────────────────────────────────

    def find(
        self,
        by: str,
        value: str,
        timeout: Optional[int] = None,
    ) -> WebElement:
        """Find element with explicit wait."""
        wait = WebDriverWait(self.driver, timeout or self._wait_timeout)
        try:
            return wait.until(EC.presence_of_element_located((by, value)))
        except TimeoutException:
            raise AssertionError(f"Element not found: {by}={value}")

    def find_clickable(
        self,
        by: str,
        value: str,
        timeout: Optional[int] = None,
    ) -> WebElement:
        """Find element that is clickable."""
        wait = WebDriverWait(self.driver, timeout or self._wait_timeout)
        try:
            return wait.until(EC.element_to_be_clickable((by, value)))
        except TimeoutException:
            raise AssertionError(f"Element not clickable: {by}={value}")

    def find_visible(
        self,
        by: str,
        value: str,
        timeout: Optional[int] = None,
    ) -> WebElement:
        """Find visible element."""
        wait = WebDriverWait(self.driver, timeout or self._wait_timeout)
        try:
            return wait.until(EC.visibility_of_element_located((by, value)))
        except TimeoutException:
            raise AssertionError(f"Element not visible: {by}={value}")

    def find_all(
        self,
        by: str,
        value: str,
    ) -> list[WebElement]:
        """Find all matching elements."""
        return self.driver.find_elements(by, value)

    def is_visible(
        self,
        by: str,
        value: str,
        timeout: int = 3,
    ) -> bool:
        """Check if element is visible within timeout."""
        try:
            self.find_visible(by, value, timeout=timeout)
            return True
        except Exception:
            return False

    def is_present(
        self,
        by: str,
        value: str,
        timeout: int = 3,
    ) -> bool:
        """Check if element is present in DOM within timeout."""
        try:
            self.find(by, value, timeout=timeout)
            return True
        except Exception:
            return False

    def wait_for(
        self,
        condition,
        timeout: Optional[int] = None,
    ):
        """Wait for a Selenium expected condition."""
        wait = WebDriverWait(self.driver, timeout or self._wait_timeout)
        return wait.until(condition)

    def wait_for_activity(
        self,
        activity: str,
        timeout: int = 30,
    ):
        """Wait for Android activity."""
        self.driver.wait_activity(activity, timeout)

    # ── Actions ─────────────────────────────────────────────────────────────

    def tap(self, by: str, value: str, timeout: Optional[int] = None):
        """Tap element."""
        el = self.find_clickable(by, value, timeout)
        el.click()
        time.sleep(0.3)

    def type_text(self, by: str, value: str, text: str, clear_first: bool = True):
        """Type text into element."""
        el = self.find_visible(by, value)
        if clear_first:
            el.clear()
        # Use Selenium's send_keys — works with React Native TextInput
        el.send_keys(text)
        time.sleep(0.2)

    def press_keycode(self, code: int):
        """Press Android keycode."""
        self.driver.press_keycode(code)

    def press_back(self):
        """Press back button."""
        self.driver.back()

    def hide_keyboard(self):
        """Hide keyboard if shown."""
        try:
            self.driver.hideKeyboard()
        except Exception:
            pass

    def swipe_down(self, duration: int = 500):
        """Swipe down."""
        size = self.driver.get_window_size()
        x = size["width"] // 2
        start_y = int(size["height"] * 0.8)
        end_y = int(size["height"] * 0.2)
        self.driver.swipe(x, start_y, x, end_y, duration)

    # ── Screenshots ─────────────────────────────────────────────────────────

    def screenshot(self, name: str, folder: Optional[str] = None) -> Path:
        """Take a screenshot."""
        folder = folder or config.screenshot_dir
        path = Path(folder) / f"{name}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        self.driver.save_screenshot(str(path))
        logger.info(f"Screenshot: {path}")
        return path

    # ── App Lifecycle ─────────────────────────────────────────────────────

    def reset_app(self):
        """Reset app (clear data)."""
        self.driver.reset()

    def close_app(self):
        """Close the app."""
        self.driver.close_app()

    def launch_app(self):
        """Launch the app."""
        self.driver.launch_app()

    # ── Helpers ────────────────────────────────────────────────────────────

    @property
    def page_source(self) -> str:
        """Get page source for debugging."""
        return self.driver.page_source

    def log(self, msg: str):
        """Log a message."""
        logger.info(f"[{self.__class__.__name__}] {msg}")

    # ── Scrolling to content ────────────────────────────────────────────────

    def scroll_to_text(self, text: str, max_swipes: int = 6) -> bool:
        """
        Swipe up until `text` appears.

        UiScrollable would be terser, but React Native's ScrollView is not
        always exposed as a scrollable container to UiAutomator, so it silently
        finds nothing. Manual swipes work regardless of how the tree is
        reported.
        """
        from selenium.webdriver.common.by import By

        locator = (By.XPATH, f'//*[contains(@text, "{text}")]')
        for _ in range(max_swipes):
            if self.is_visible(*locator, timeout=1):
                return True
            self.swipe_up()
        return self.is_visible(*locator, timeout=1)

    def scroll_until_present(self, by: str, value: str, max_swipes: int = 8) -> bool:
        """
        Swipe up until a specific element enters the tree.

        Distinct from scroll_to_text, and the difference matters: stopping when
        a section HEADING becomes visible leaves the controls under it still
        below the fold, and Android omits off-screen views from the
        accessibility tree entirely -- so they read as "element not found"
        rather than "not scrolled to yet".
        """
        for _ in range(max_swipes):
            if self.is_present(by, value, timeout=1):
                return True
            self.swipe_up()
        return self.is_present(by, value, timeout=2)

    def scroll_until_fully_visible(self, by: str, value: str,
                                   max_swipes: int = 8) -> bool:
        """
        Scroll until the element is entirely on screen, not merely present.

        This distinction is the difference between a real failure and a false
        one. Android reports an element's bounds CLIPPED to the viewport, so a
        control scrolled half into view measures as a fraction of its true
        height -- a 48dp button caught with only its top edge showing reports
        about 10dp and fails a tap-target assertion it should pass.
        """
        from base.layout import box_of

        if not self.scroll_until_present(by, value, max_swipes=max_swipes):
            return False

        screen = self.driver.get_window_size()
        for _ in range(4):
            box = box_of(self.find(by, value, timeout=2))
            if box.top >= 0 and box.bottom <= screen["height"]:
                return True
            self.swipe_up(duration=300)
        box = box_of(self.find(by, value, timeout=2))
        return box.top >= 0 and box.bottom <= screen["height"]

    def swipe_up(self, duration: int = 400):
        """Swipe content upward (reveals what is below the fold)."""
        size = self.driver.get_window_size()
        x = size["width"] // 2
        self.driver.swipe(x, int(size["height"] * 0.75),
                          x, int(size["height"] * 0.30), duration)
