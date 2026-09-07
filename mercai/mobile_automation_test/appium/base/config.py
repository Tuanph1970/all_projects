"""
Mercai mobile E2E configuration.

Ported from mathematic-mobile's Appium harness, which is the pattern this
follows throughout. Differences are only the app under test and the backend:
mercai's API is published, so the default backend is the real tunnel rather
than a host-relative address.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


@dataclass
class AppConfig:
    """Android app under test."""
    app_package: str = os.getenv("APP_PACKAGE", "com.mercai.app")
    app_activity: str = os.getenv("APP_ACTIVITY", ".MainActivity")
    app_wait_activity: str = "*"

    # Expo runs a MANAGED workflow, so there is no android/ directory and no
    # APK until someone runs `npx expo prebuild -p android` and a gradle build.
    # Until then this is empty and the driver falls back to package/activity,
    # which only works if the app is already installed on the device.
    apk_path: str | None = os.getenv("APK_PATH")
    app_wait_duration: int = 30


@dataclass
class EmulatorConfig:
    platform_name: str = "Android"
    platform_version: str = os.getenv("PLATFORM_VERSION", "14")
    device_name: str = os.getenv("DEVICE_NAME", "Pixel_3a_API_36")
    udid: str = os.getenv("UDID", "emulator-5554")

    auto_launch: bool = True
    # Env-driven, because the right value differs by situation and the cost is
    # large: with no_reset=False Appium reinstalls the app for every test, and
    # this APK is 218MB. Leave it true once the app is installed; set it false
    # when a test genuinely needs virgin state.
    no_reset: bool = os.getenv("NO_RESET", "true").lower() == "true"
    full_reset: bool = os.getenv("FULL_RESET", "false").lower() == "true"


@dataclass
class ServerConfig:
    host: str = os.getenv("APPIUM_HOST", "127.0.0.1")
    port: int = int(os.getenv("APPIUM_PORT", "4723"))
    ssl: bool = False

    @property
    def remote_url(self) -> str:
        scheme = "https" if self.ssl else "http"
        # Selenium's RemoteConnection appends /wd/hub itself, and Appium 3.x
        # dropped /wd/hub from its root — so omitting it here is correct.
        return f"{scheme}://{self.host}:{self.port}"


@dataclass
class BackendConfig:
    """
    The API the app talks to.

    Defaults to the published tunnel rather than 10.0.2.2, because mercai's
    backend is reachable from anywhere and a device on mobile data cannot see
    the host loopback at all.
    """
    base_url: str = os.getenv("BACKEND_URL", "https://mercai.tuan1970.com")

    # Seeded seller from back_end/scripts/seed_catalogue.py. This account owns
    # products, which the price-intelligence tests need -- but it exists ONLY
    # where that seed has been run. It is NOT on the production deployment,
    # whose database is fresh. Point BACKEND_URL at a seeded local stack before
    # using this one.
    seller_username: str = os.getenv("SELLER_USERNAME", "gomthuha")
    seller_password: str = os.getenv("SELLER_PASSWORD", "MercaiTest@2026")

    # Accounts for the AUTH suite, created on production 2026-09-07. They hold
    # no products on purpose: authentication does not need a catalogue, and
    # keeping them bare means the auth tests do not silently depend on the
    # seed. Both exist on https://mercai.tuan1970.com.
    auth_customer_username: str = os.getenv("AUTH_CUSTOMER_USERNAME", "e2e_customer")
    auth_customer_password: str = os.getenv("AUTH_CUSTOMER_PASSWORD", "E2eTest@2026")
    auth_seller_username: str = os.getenv("AUTH_SELLER_USERNAME", "e2e_seller")
    auth_seller_password: str = os.getenv("AUTH_SELLER_PASSWORD", "E2eTest@2026")

    # Registration tests create real users and there is no delete-account path
    # in the suite, so every run leaves a row behind. The prefix makes them
    # greppable for later cleanup.
    throwaway_prefix: str = os.getenv("THROWAWAY_PREFIX", "e2e_tmp")


@dataclass
class TestConfig:
    app: AppConfig = field(default_factory=AppConfig)
    emulator: EmulatorConfig = field(default_factory=EmulatorConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    backend: BackendConfig = field(default_factory=BackendConfig)

    implicit_wait: int = 2
    explicit_wait: int = 10
    screenshot_on_failure: bool = True

    screenshot_dir: str = os.path.join(
        os.path.dirname(__file__), "..", "..", "screenshots", "appium"
    )
    report_dir: str = os.path.join(
        os.path.dirname(__file__), "..", "..", "reports"
    )


config = TestConfig()
