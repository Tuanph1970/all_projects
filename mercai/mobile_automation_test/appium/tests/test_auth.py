"""
Authentication E2E suite -- Appium port of the Maestro auth scripts.

MIGRATED FROM (maestro/scripts/, kept for reference until this suite is
trusted):

    AUTH-001  fast-customer-login-test.sh              -> test_auth_001_*
    AUTH-002  fast-seller-login-test.sh                -> test_auth_002_*
    AUTH-003  fast-auth-invalid-password-test.sh       -> test_auth_003_*
    AUTH-004  fast-auth-nonexistent-user-test.sh       -> test_auth_004_*
    AUTH-005  fast-auth-empty-fields-test.sh           -> test_auth_005_* (x3)
    AUTH-006  fast-auth-customer-registration-test.sh  -> test_auth_006_*
    AUTH-007  fast-auth-seller-registration-test.sh    -> test_auth_007_*
    AUTH-009  fast-auth-logout-test.sh                 -> test_auth_009_* (x2)

AUTH-008 has never existed -- the old numbering skips it. Not an omission
here.

Four things the Maestro scripts got wrong, corrected in this port:

1. They asserted logout via `logout-button` for BOTH roles. Only the seller's
   SellerProfileScreen uses that testID; the customer's ProfileScreen uses
   `profile-logout-button`. See shell_page.py.
2. They matched error text with English regexes (`.*[Ii]nvalid.*`). The app
   defaults to Vietnamese, so those could never have matched. Rejected logins
   are asserted by staying on the login screen instead.
3. They referenced `register-phone-input` and `register-shop-name-input`.
   Neither field exists on RegisterScreen -- registration posts
   phone_number: null and has no shop name at all.
4. They relied on Metro running (`ensure-metro.sh`). This suite drives the
   release APK, which embeds its own JS bundle, so Metro is irrelevant.

The APK's backend is fixed at BUILD time by front_end/src/constants/config.js.
Pointing these tests at a different backend means rebuilding the APK, not just
changing BACKEND_URL -- that env var only affects direct API calls made from
the test process.
"""
from __future__ import annotations

import logging
import time

import pytest

from base.config import config
from pages.login_page import LoginPage
from pages.register_page import RegisterPage
from pages.shell_page import ShellPage

logger = logging.getLogger(__name__)

pytestmark = [pytest.mark.e2e, pytest.mark.auth]


def _unique(kind: str) -> str:
    """A username/email stem unique per run."""
    return f"{config.backend.throwaway_prefix}_{kind}_{int(time.time())}"


# ── AUTH-001 / AUTH-002: successful login, per role ──────────────────────────


def test_auth_001_customer_login_succeeds(logged_out_driver):
    """A valid customer reaches the customer shell (Home tab)."""
    login = LoginPage(logged_out_driver)
    assert login.is_showing(timeout=30), "app did not start on the login screen"

    login.login(
        config.backend.auth_customer_username,
        config.backend.auth_customer_password,
    )

    shell = ShellPage(logged_out_driver)
    assert shell.landed_as_customer(), (
        "customer login did not reach the Home tab; "
        "still on login screen means the credentials or backend are wrong"
    )


def test_auth_002_seller_login_succeeds(logged_out_driver):
    """A valid seller reaches the seller shell (Dashboard tab), not Home."""
    login = LoginPage(logged_out_driver)
    assert login.is_showing(timeout=30), "app did not start on the login screen"

    login.login(
        config.backend.auth_seller_username,
        config.backend.auth_seller_password,
    )

    shell = ShellPage(logged_out_driver)
    assert shell.landed_as_seller(), (
        "seller login did not reach the Dashboard tab -- "
        "a seller landing on Home would mean the role was not applied"
    )


# ── AUTH-003 / AUTH-004: rejected logins ─────────────────────────────────────


def test_auth_003_invalid_password_is_rejected(logged_out_driver):
    """Valid username, wrong password: stays on login."""
    login = LoginPage(logged_out_driver)
    assert login.is_showing(timeout=30)

    login.submit_credentials(
        config.backend.auth_customer_username, "WrongPassword@123"
    )

    assert login.still_showing_after_attempt(), (
        "app left the login screen after a wrong password -- "
        "that would mean the credentials were accepted"
    )
    shell = ShellPage(logged_out_driver)
    assert not shell.is_signed_in(timeout=3), "wrong password reached the app shell"


def test_auth_004_nonexistent_user_is_rejected(logged_out_driver):
    """A username that does not exist: stays on login."""
    login = LoginPage(logged_out_driver)
    assert login.is_showing(timeout=30)

    login.submit_credentials(_unique("ghost"), "SomePassword@123")

    assert login.still_showing_after_attempt()
    shell = ShellPage(logged_out_driver)
    assert not shell.is_signed_in(timeout=3), "unknown user reached the app shell"


# ── AUTH-005: empty-field validation, all three combinations ─────────────────


@pytest.mark.parametrize(
    "username,password,scenario",
    [
        ("", "", "both fields empty"),
        (config.backend.auth_customer_username, "", "password empty"),
        ("", "E2eTest@2026", "username empty"),
    ],
    ids=["both-empty", "password-empty", "username-empty"],
)
def test_auth_005_empty_fields_blocked(
    logged_out_driver, username, password, scenario
):
    """Submitting with a blank field never signs in."""
    login = LoginPage(logged_out_driver)
    assert login.is_showing(timeout=30)

    login.submit_credentials(username, password)

    assert login.still_showing_after_attempt(), f"left login screen with {scenario}"
    shell = ShellPage(logged_out_driver)
    assert not shell.is_signed_in(timeout=3), f"signed in with {scenario}"


# ── AUTH-006 / AUTH-007: registration, per role ──────────────────────────────


@pytest.mark.parametrize("role", ["customer", "seller"], ids=["customer", "seller"])
def test_auth_006_007_registration_returns_to_login(logged_out_driver, role):
    """
    A complete registration form is accepted and returns to the login screen.

    RegisterScreen.jsx:93 navigates to Login on success, so being back on the
    login screen IS the success signal. The success Toast is not asserted --
    it is transient and would make the test flaky.

    NOTE: this creates a real user on whatever backend the APK points at, and
    nothing deletes it. Usernames are prefixed (see throwaway_prefix) so they
    can be cleaned up later.
    """
    login = LoginPage(logged_out_driver)
    assert login.is_showing(timeout=30)
    login.open_register()

    register = RegisterPage(logged_out_driver)
    assert register.is_showing(timeout=15), "register link did not open the form"

    stem = _unique(role)
    register.fill(
        first_name="E2E",
        last_name=role.capitalize(),
        username=stem,
        email=f"{stem}@mercai-test.com",
        password="E2eTest@2026",
    )
    register.select_role(role)
    register.submit()

    assert login.is_showing(timeout=20), (
        f"{role} registration did not return to the login screen -- "
        "either it failed (duplicate user, weak password, validation) or the "
        "navigation changed"
    )


# ── AUTH-009: logout, per role ───────────────────────────────────────────────


@pytest.mark.parametrize(
    "role,username_attr,password_attr",
    [
        ("customer", "auth_customer_username", "auth_customer_password"),
        ("seller", "auth_seller_username", "auth_seller_password"),
    ],
    ids=["customer", "seller"],
)
def test_auth_009_logout_returns_to_login(
    logged_out_driver, role, username_attr, password_attr
):
    """Sign in, log out via that role's own button, land back on login."""
    login = LoginPage(logged_out_driver)
    assert login.is_showing(timeout=30)

    login.login(
        getattr(config.backend, username_attr),
        getattr(config.backend, password_attr),
    )

    shell = ShellPage(logged_out_driver)
    assert shell.is_signed_in(), f"{role} did not sign in, so logout is untestable"

    shell.logout(role)

    assert login.is_showing(timeout=20), (
        f"{role} logout did not return to the login screen"
    )
