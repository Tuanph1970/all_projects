"""
Catalogue fixtures, seeded over the API rather than through the UI.

Why this exists: the production database is FRESH. Before this suite ran,
`GET /api/v1/products/` returned `[]` and there were no categories at all --
so every customer-side product test (browse, sort, filter, search) had nothing
to look at and would have failed for want of data, not because the app was
broken.

Seeding through the API rather than by driving the seller UI is deliberate:

  - A browse test that depends on an add-product test passing is not a browse
    test, it is a two-hour debugging session whenever either one breaks.
  - Prices and names are chosen so the ordering assertions are unambiguous
    (see PRODUCTS below) rather than whatever the catalogue happens to hold.
  - It is idempotent, so a rerun does not pile up duplicates.

This talks to config.backend.base_url. That is the URL the TEST PROCESS uses;
the APK's own backend is fixed at build time in
front_end/src/constants/config.js. If the two disagree, the suite seeds one
backend and the app reads another -- which looks exactly like "the seed did
not work". Keep them pointed at the same place.
"""
from __future__ import annotations

import logging
from typing import Any

import requests

from base.config import config

logger = logging.getLogger(__name__)

TIMEOUT = 30

# Prefix marks everything this module creates, so it is greppable and
# deletable. Nothing here is ever cleaned up automatically.
PREFIX = "E2E"

CATEGORIES = [
    {"name": "E2E Ceramics", "description": "appium suite fixture category"},
    {"name": "E2E Tableware", "description": "appium suite fixture category"},
]

# Deliberately spread so ordering assertions cannot be satisfied by accident:
# Alpha is unambiguously cheapest, Gamma unambiguously dearest, and the names
# sort in the same order as the prices so a price sort and a name sort are
# distinguishable.
PRODUCTS = [
    {
        "name": "E2E Alpha Vase",
        "description": "cheapest fixture product, used for price-ascending assertions",
        "price": 100000,
        "quantity_available": 5,
        "category": "E2E Ceramics",
    },
    {
        "name": "E2E Beta Bowl",
        "description": "mid-priced fixture product",
        "price": 250000,
        "quantity_available": 8,
        "category": "E2E Ceramics",
    },
    {
        "name": "E2E Gamma Teapot",
        "description": "dearest fixture product, used for price-descending assertions",
        "price": 500000,
        "quantity_available": 3,
        "category": "E2E Tableware",
    },
]


class CatalogueApi:
    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or config.backend.base_url).rstrip("/")
        self._token: str | None = None

    # ── auth ────────────────────────────────────────────────────────────────

    def login(self, username: str, password: str) -> str:
        r = requests.post(
            f"{self.base_url}/api/v1/auth/login",
            json={"username": username, "password": password},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        self._token = r.json()["access_token"]
        return self._token

    def try_login(self, username: str, password: str) -> str | None:
        """Login, or None if the credentials are refused. Other errors raise."""
        r = requests.post(
            f"{self.base_url}/api/v1/auth/login",
            json={"username": username, "password": password},
            timeout=TIMEOUT,
        )
        if r.status_code == 200:
            self._token = r.json()["access_token"]
            return self._token
        if r.status_code in (400, 401):
            return None
        r.raise_for_status()
        return None

    def register(
        self, username: str, password: str, email: str, full_name: str, role: str
    ) -> bool:
        """
        Create an account. True if created, False if it already existed.

        A 400 here is "email already registered" or "username already taken"
        (auth.py:157-171) -- both mean someone else won the race or the account
        predates us, and neither is a failure for our purposes.
        """
        r = requests.post(
            f"{self.base_url}/api/v1/auth/register",
            json={
                "email": email,
                "username": username,
                "full_name": full_name,
                "password": password,
                "role": role,
            },
            timeout=TIMEOUT,
        )
        if r.status_code == 200:
            return True
        if r.status_code == 400:
            logger.info("account %s already exists", username)
            return False
        r.raise_for_status()
        return False

    @property
    def _headers(self) -> dict[str, str]:
        if not self._token:
            raise RuntimeError("login() first")
        return {"Authorization": f"Bearer {self._token}"}

    # ── reads ───────────────────────────────────────────────────────────────

    def list_products(self, limit: int = 100) -> list[dict[str, Any]]:
        r = requests.get(
            f"{self.base_url}/api/v1/products/",
            params={"limit": limit},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        body = r.json()
        # The endpoint has returned a bare list historically; tolerate either
        # shape rather than exploding on a pagination change.
        return body if isinstance(body, list) else body.get("items", [])

    def list_categories(self) -> list[dict[str, Any]]:
        r = requests.get(
            f"{self.base_url}/api/v1/products/categories", timeout=TIMEOUT
        )
        r.raise_for_status()
        return r.json()

    # ── writes ──────────────────────────────────────────────────────────────

    def create_category(self, name: str, description: str) -> dict[str, Any]:
        r = requests.post(
            f"{self.base_url}/api/v1/products/categories",
            json={"name": name, "description": description},
            headers=self._headers,
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        return r.json()

    def create_product(self, **fields) -> dict[str, Any]:
        r = requests.post(
            f"{self.base_url}/api/v1/products/",
            json=fields,
            headers=self._headers,
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        return r.json()

    def delete_product(self, product_id: int) -> bool:
        r = requests.delete(
            f"{self.base_url}/api/v1/products/{product_id}",
            headers=self._headers,
            timeout=TIMEOUT,
        )
        return r.status_code < 300


# Email is DERIVED from the username rather than fixed, so overriding
# AUTH_SELLER_USERNAME in .env still works: a fixed address would collide with
# the existing account ("Email already registered", a 400 that this code reads
# as "someone else made it") and the subsequent login would fail for reasons
# that have nothing to do with the override.
ACCOUNT_EMAIL_DOMAIN = "mercai-test.com"

ACCOUNTS = [
    {
        "username_attr": "auth_customer_username",
        "password_attr": "auth_customer_password",
        "full_name": "E2E Customer",
        "role": "customer",
    },
    {
        "username_attr": "auth_seller_username",
        "password_attr": "auth_seller_password",
        "full_name": "E2E Seller",
        "role": "seller",
    },
]


def ensure_accounts() -> dict[str, str]:
    """
    Guarantee the suite's two test accounts exist and their passwords work.

    This is what makes the suite survive a database rebuild. The backend runs
    on a remote machine that has been rebuilt before, and a fresh database
    means these accounts are simply gone -- at which point every auth test
    fails with "credentials or backend are wrong", which reads like a broken
    app rather than an empty database.

    Login is attempted FIRST, so the normal path is one request and no writes.
    Registration only happens when login is refused.

    Returns {username: role}. Raises with a pointed message if an account
    exists but its password does not match, because that is the one case
    nothing here can repair automatically.
    """
    api = CatalogueApi()
    result: dict[str, str] = {}

    for spec in ACCOUNTS:
        username = getattr(config.backend, spec["username_attr"])
        password = getattr(config.backend, spec["password_attr"])

        if api.try_login(username, password):
            logger.info("account %s present", username)
            result[username] = spec["role"]
            continue

        logger.info("account %s missing, registering", username)
        created = api.register(
            username=username,
            password=password,
            email=f"{username}@{ACCOUNT_EMAIL_DOMAIN}",
            full_name=spec["full_name"],
            role=spec["role"],
        )

        if not api.try_login(username, password):
            raise AssertionError(
                f"cannot authenticate as {username!r} and cannot create it. "
                f"{'It was just registered, so this is a backend problem. ' if created else ''}"
                f"Most likely the account exists on {api.base_url} with a "
                f"different password -- set {spec['password_attr'].upper()} in "
                f"appium/.env to the real one, or delete the account."
            )
        result[username] = spec["role"]

    return result


def ensure_catalogue() -> dict[str, dict[str, Any]]:
    """
    Guarantee the fixture products exist. Idempotent.

    Returns the fixture products keyed by name, so a test can assert against
    a known price without hard-coding an id that changes per environment.

    IDEMPOTENCY IS DRIVEN OFF PRODUCTS, NOT CATEGORIES, and that is deliberate.
    `GET /api/v1/products/categories` is Redis-cached for an hour
    (CACHE_TTL_CATEGORIES=3600) and `POST /categories` never invalidates that
    key -- see products.py:86-92, which commits and returns without touching
    the cache, unlike every product write next to it. So a category created
    here stays invisible to the list endpoint for up to an hour, and a
    "create if not listed" loop happily creates it again on every single run.
    The first version of this function did exactly that and piled up
    duplicates.

    Products do not have that problem: create_product calls
    invalidate_all_products(), so the list reflects reality immediately.
    Categories are therefore created ONLY as a side effect of creating a
    product that needs one -- which, because products are idempotent, means
    they are created once and never again.
    """
    # The seller account has to exist before anything can be seeded as it.
    ensure_accounts()

    api = CatalogueApi()
    api.login(
        config.backend.auth_seller_username, config.backend.auth_seller_password
    )

    existing_products = {p["name"]: p for p in api.list_products()}
    missing = [s for s in PRODUCTS if s["name"] not in existing_products]

    seeded: dict[str, dict[str, Any]] = {
        s["name"]: existing_products[s["name"]]
        for s in PRODUCTS
        if s["name"] in existing_products
    }

    if not missing:
        logger.info("catalogue fixtures already present, nothing to seed")
        return seeded

    # Only now is a category lookup worth doing. Trust the list if it happens
    # to be warm, otherwise create -- a duplicate here is bounded by the fact
    # that we only get here when a product is genuinely missing.
    categories = {c["name"]: c for c in api.list_categories()}
    needed = {s["category"] for s in missing}
    for spec in CATEGORIES:
        if spec["name"] in needed and spec["name"] not in categories:
            logger.info("seeding category %s", spec["name"])
            categories[spec["name"]] = api.create_category(
                spec["name"], spec["description"]
            )

    for spec in missing:
        logger.info("seeding product %s", spec["name"])
        category = categories.get(spec["category"])
        seeded[spec["name"]] = api.create_product(
            name=spec["name"],
            description=spec["description"],
            price=spec["price"],
            quantity_available=spec["quantity_available"],
            category_id=category["id"] if category else None,
        )

    return seeded
