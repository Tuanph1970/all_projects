"""
Pytest configuration for the mercai Appium suite.

Ported from mathematic-mobile's harness. The fixture-account pre-registration
it does at session start is dropped: mercai's test sellers come from
back_end/scripts/seed_catalogue.py, which also creates their products, so
registering a bare account here would produce a seller with nothing to look at.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import pytest
from appium.webdriver.webdriver import WebDriver

sys.path.insert(0, str(Path(__file__).parent))

from base.config import config as app_config
from base.driver_factory import create_driver, screenshot_on_failure


def pytest_configure(config):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("selenium").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    Path(app_config.screenshot_dir).mkdir(parents=True, exist_ok=True)
    Path(app_config.report_dir).mkdir(parents=True, exist_ok=True)

    config.addinivalue_line("markers", "layout: screen layout and geometry tests")
    config.addinivalue_line("markers", "e2e: end-to-end tests")
    config.addinivalue_line("markers", "slow: marks tests as slow")


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)


@pytest.fixture(scope="function")
def driver(request) -> WebDriver:
    """A fresh Appium driver per test, with a screenshot on failure."""
    _driver = create_driver()
    yield _driver
    try:
        rep = getattr(request.node, "rep_call", None)
        if rep is not None and rep.failed:
            screenshot_on_failure(_driver, suffix=request.node.name)
    except Exception:
        pass
    _driver.quit()
