"""
Appium Driver Factory
Handles driver lifecycle: start, stop, screenshot on failure.
"""
from __future__ import annotations

import os
import time
import logging
from pathlib import Path

import pytest
from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.webdriver import WebDriver

from .config import config, ServerConfig, EmulatorConfig, AppConfig

logger = logging.getLogger(__name__)


def _build_caps(
    app_config: AppConfig,
    emulator_config: EmulatorConfig,
) -> UiAutomator2Options:
    """Build Appium capabilities for Android."""
    options = UiAutomator2Options()

    # App installation
    if app_config.apk_path and os.path.exists(app_config.apk_path):
        options.app = app_config.apk_path
    else:
        options.app_package = app_config.app_package
        options.app_activity = app_config.app_activity

    # Device
    options.platform_name = emulator_config.platform_name
    options.platform_version = emulator_config.platform_version
    options.device_name = emulator_config.device_name
    options.udid = emulator_config.udid

    # Stability & performance
    options.no_reset = emulator_config.no_reset
    options.auto_launch = emulator_config.auto_launch
    options.disable_window_animation = True
    options.skip_unlock = True

    # App wait
    options.app_wait_activity = app_config.app_wait_activity
    options.app_wait_duration = app_config.app_wait_duration * 1000  # ms

    # Chrome driver (for web views)
    options.chromedriver_executable_dir = None  # auto-detect

    # Logging
    options.show_devtools_log = True

    return options


def _setup_adb_reverse(metro_port: int):
    """
    Forward emulator's localhost:PORT -> host:PORT so the app can reach Metro.

    Only needed for a debug build talking to a Metro dev server. mercai's
    backend is on a public hostname, so unlike the mathematic-mobile original
    nothing here forwards the API port.
    """
    import subprocess

    try:
        # Remove any existing reverse for this port
        subprocess.run(["adb", "reverse", "--remove", f"tcp:{metro_port}"],
                       stderr=subprocess.DEVNULL, timeout=5)
    except Exception:
        pass

    result = subprocess.run(
        ["adb", "reverse", f"tcp:{metro_port}", f"tcp:{metro_port}"],
        capture_output=True, text=True, timeout=10
    )
    if result.returncode == 0:
        logger.info(f"adb reverse setup: localhost:{metro_port} → host:{metro_port}")
    else:
        logger.warning(f"adb reverse failed: {result.stderr.strip()}")


def create_driver(
    server: ServerConfig = None,
    emulator: EmulatorConfig = None,
    app: AppConfig = None,
) -> WebDriver:
    """
    Create and return an Appium WebDriver.

    Usage:
        driver = create_driver()
        try:
            # tests here
        finally:
            driver.quit()
    """
    server = server or config.server
    emulator = emulator or config.emulator
    app = app or config.app

    # Ensure Metro is reachable from the emulator
    metro_port = int(os.environ.get("METRO_PORT", 8081))
    _setup_adb_reverse(metro_port)

    logger.info(f"Connecting to Appium at {server.remote_url}")
    logger.info(f"Target app: {app.app_package}")

    options = _build_caps(app, emulator)
    driver = webdriver.Remote(server.remote_url, options=options)

    # Set timeouts
    driver.implicitly_wait(config.implicit_wait)

    logger.info("Driver created successfully")
    return driver


def screenshot_on_failure(driver: WebDriver, suffix: str = ""):
    """Take screenshot on test failure."""
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    name = f"FAIL_{suffix}_{timestamp}" if suffix else f"FAIL_{timestamp}"
    filename = f"{name}.png"

    screenshot_dir = Path(config.screenshot_dir)
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    filepath = screenshot_dir / filename

    try:
        driver.save_screenshot(str(filepath))
        logger.warning(f"Screenshot saved: {filepath}")
    except Exception as e:
        logger.error(f"Failed to take screenshot: {e}")

    return filepath


@pytest.fixture(scope="session")
def appium_server():
    """Start Appium server if not already running."""
    import subprocess

    server_url = f"http://{config.server.host}:{config.server.port}"
    logger.info(f"Checking Appium server at {server_url}")

    # Check if server is already running
    import requests
    try:
        r = requests.get(f"{server_url}/status", timeout=3)
        if r.status_code == 200:
            logger.info("Appium server already running")
            yield server_url
            return
    except Exception:
        pass

    # Start server
    logger.info("Starting Appium server...")
    proc = subprocess.Popen(
        ["appium", "--address", config.server.host, "--port", str(config.server.port), "-G", "/dev/null"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for server to be ready
    for i in range(30):
        try:
            r = requests.get(f"{server_url}/status", timeout=2)
            if r.status_code == 200:
                logger.info("Appium server started")
                break
        except Exception:
            time.sleep(1)
    else:
        proc.kill()
        raise RuntimeError("Appium server failed to start")

    yield server_url

    proc.terminate()
    proc.wait(timeout=5)
    logger.info("Appium server stopped")


@pytest.fixture(scope="function")
def driver(appium_server):
    """
    Create a driver for each test, quit after.
    Takes screenshot on failure automatically.
    """
    _driver = create_driver()

    yield _driver

    # Screenshot on failure
    failed = hasattr(pytest, "failed") and pytest.failed
    if failed or (hasattr(_driver, '_last_was_failure') and _driver._last_was_failure):
        screenshot_on_failure(_driver)

    _driver.quit()
