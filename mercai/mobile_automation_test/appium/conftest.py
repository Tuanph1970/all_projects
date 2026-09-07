"""
Pytest configuration for the mercai Appium suite.

Ported from mathematic-mobile's harness. The fixture-account pre-registration
it does at session start is dropped: mercai's test sellers come from
back_end/scripts/seed_catalogue.py, which also creates their products, so
registering a bare account here would produce a seller with nothing to look at.
"""
from __future__ import annotations

import logging
import subprocess
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
    config.addinivalue_line("markers", "auth: authentication tests")
    config.addinivalue_line("markers", "slow: marks tests as slow")


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)


@pytest.fixture(scope="session", autouse=True)
def test_accounts():
    """
    Guarantee the suite's accounts exist before any test drives the app.

    Autouse and session-scoped: two HTTP requests once per run, in exchange
    for the suite surviving a database rebuild. The backend lives on a remote
    machine that has been rebuilt before, and a fresh database silently
    removes these accounts -- after which every auth test fails inside the UI
    with "credentials or backend are wrong", which looks like an app bug.

    Failing here instead turns that into one honest error at session start,
    naming the backend it could not reach or authenticate against.
    """
    from helpers.catalogue import ensure_accounts

    try:
        return ensure_accounts()
    except Exception as exc:
        pytest.fail(
            f"could not prepare test accounts on {app_config.backend.base_url}: "
            f"{exc}",
            pytrace=False,
        )


@pytest.fixture(scope="session")
def catalogue(test_accounts):
    """
    Fixture products, seeded over the API. Idempotent.

    Not autouse -- the auth tests do not need a catalogue, and making them
    wait for one would couple them to data they never read.
    """
    from helpers.catalogue import ensure_catalogue

    return ensure_catalogue()


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


@pytest.fixture(scope="function")
def logged_out_driver(request) -> WebDriver:
    """
    A driver whose app starts signed out, every time.

    NO_RESET is true by default (the APK is ~120MB and reinstalling it per
    test is unaffordable), so the app otherwise starts wherever the previous
    test left it -- usually signed in, which makes every login test a no-op
    that passes without logging in.

    `adb shell pm clear` wipes the app's data in well under a second without
    touching the install, so it gets a virgin AsyncStorage (no persisted auth
    token) at a fraction of the cost of full_reset. It also resets the stored
    language back to the vi default, which the text locators assume.
    """
    subprocess.run(
        ["adb", "-s", app_config.emulator.udid, "shell", "pm", "clear",
         app_config.app.app_package],
        capture_output=True,
        timeout=30,
        check=False,
    )
    _driver = create_driver()
    yield _driver
    try:
        rep = getattr(request.node, "rep_call", None)
        if rep is not None and rep.failed:
            screenshot_on_failure(_driver, suffix=request.node.name)
    except Exception:
        pass
    _driver.quit()
