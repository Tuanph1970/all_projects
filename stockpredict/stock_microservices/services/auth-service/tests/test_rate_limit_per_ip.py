"""Backlog #24 — the rate limit is per-IP only if the proxy is trusted.

`test_rate_limit.py` proves the limiter FIRES (429 after the 5/minute budget).
It cannot prove the budget is **per IP**, because every request it makes
arrives from the same ASGI client address — so a limiter keyed on a single
shared value would pass it unchanged. That was the live bug: behind Traefik,
`get_remote_address` returned Traefik's own address for every caller, so all
users shared ONE bucket and six sign-ins in a minute locked out everyone.

These tests close that gap from both ends: the behaviour (distinct addresses
get distinct budgets) and the deployment setting the behaviour depends on.
"""
import ipaddress
import os
import re

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.dependencies import get_db
from app.api.rate_limit import (
    DEFAULT_FORWARDED_ALLOW_IPS,
    check_proxy_trust,
    limiter,
)
from app.main import app
from app.models.domain import Base

PREFIX = "/stock_helper/api/v2/auth"
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

#: What the compose files ship. Not "*" — see the module docstring in
#: app/api/rate_limit.py for why that would be exploitable.
SHIPPED_TRUST = "127.0.0.1,172.16.0.0/12"


@pytest_asyncio.fixture
async def client_factory():
    """Build clients that present different peer addresses to the app.

    `ASGITransport(client=...)` sets `scope["client"]`, which is what
    `get_remote_address` reads — so this exercises the real keying path
    rather than a stub.
    """
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = _get_db
    limiter.enabled = True
    limiter.reset()
    opened = []

    def make(ip: str) -> AsyncClient:
        c = AsyncClient(
            transport=ASGITransport(app=app, client=(ip, 0)),
            base_url="http://test",
        )
        opened.append(c)
        return c

    try:
        yield make
    finally:
        for c in opened:
            await c.aclose()
        limiter.enabled = False
        limiter.reset()
        app.dependency_overrides.clear()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()


async def _spend_budget(client: AsyncClient) -> list:
    payload = {"email": "ghost@example.com", "password": "Wrong1234"}
    return [(await client.post(f"{PREFIX}/login", json=payload)).status_code
            for _ in range(6)]


@pytest.mark.asyncio
async def test_one_address_exhausting_its_budget_does_not_lock_out_another(client_factory):
    """THE TEST THE OLD SUITE COULD NOT MAKE.

    With the limiter keyed on a single shared value — which is what happened
    behind Traefik — the second address starts already rate-limited. That is
    the self-inflicted denial of service: one person mistyping a password five
    times took the service down for everybody.
    """
    attacker = client_factory("203.0.113.9")
    bystander = client_factory("198.51.100.4")

    spent = await _spend_budget(attacker)
    assert spent[:5].count(401) == 5, spent
    assert spent[5] == 429, spent

    # The bystander has spent nothing. 401 = reached the handler; 429 = shared bucket.
    r = await bystander.post(f"{PREFIX}/login",
                             json={"email": "ghost@example.com", "password": "Wrong1234"})
    assert r.status_code == 401, (
        "a second client address was rate-limited without making a request — "
        "the budget is shared, not per-IP")


@pytest.mark.asyncio
async def test_each_address_gets_the_full_budget(client_factory):
    """Two addresses, two full budgets — not one split between them."""
    a = await _spend_budget(client_factory("203.0.113.9"))
    b = await _spend_budget(client_factory("198.51.100.4"))
    assert a[5] == 429 and b[5] == 429
    assert a[:5].count(401) == 5 and b[:5].count(401) == 5


# ---------------------------------------------------------------------------
# The library fact that made the bug invisible
# ---------------------------------------------------------------------------

def test_get_remote_address_does_NOT_read_x_forwarded_for():
    """Pinned because the module docstring asserted the opposite for months.

    If this ever starts passing XFF through, slowapi changed its contract and
    the reasoning in rate_limit.py needs revisiting — but it must never be
    *assumed* again.
    """
    class _Req:
        client = type("C", (), {"host": "172.18.0.5"})()
        headers = {"x-forwarded-for": "203.0.113.9"}

    assert get_remote_address(_Req()) == "172.18.0.5"


async def _client_seen_by_app(trusted: str, peer: str, xff: str):
    """Run one request through uvicorn's ProxyHeadersMiddleware and report the
    client the application ends up seeing.

    Deliberately exercised through the PUBLIC middleware rather than the
    private `_TrustedHosts` helper: that helper was renamed between the
    uvicorn on this host and the 0.52.4 in the container
    (`get_trusted_client_host` vs `get_trusted_client_address`), so a test
    bound to it checks the test environment rather than the deployment.
    """
    from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

    seen = {}

    async def app(scope, receive, send):
        seen["client"] = scope.get("client")
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = ProxyHeadersMiddleware(app, trusted_hosts=trusted)
    scope = {
        "type": "http",
        "client": (peer, 1234),
        "headers": [(b"x-forwarded-for", xff.encode()), (b"x-forwarded-proto", b"https")],
    }

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(_message):
        return None

    await middleware(scope, receive, send)
    return seen["client"][0] if seen.get("client") else None


@pytest.mark.asyncio
async def test_a_spoofed_forwarded_header_does_not_win_with_the_shipped_setting():
    """Why the shipped setting is a network and not `*`.

    A client can send its own X-Forwarded-For; the proxy APPENDS the address it
    actually saw. uvicorn walks the chain in reverse and takes the first
    untrusted hop, so the spoof is ignored.
    """
    pytest.importorskip("uvicorn")
    seen = await _client_seen_by_app(
        trusted=SHIPPED_TRUST, peer="172.18.0.5", xff="1.2.3.4, 203.0.113.9")
    assert seen == "203.0.113.9", f"the spoofed leftmost entry won: {seen}"


@pytest.mark.asyncio
async def test_star_would_let_a_caller_choose_its_own_bucket():
    """The reason check_proxy_trust() warns about `*` as loudly as about the
    default. With `*` uvicorn takes the leftmost entry, which the client sends."""
    pytest.importorskip("uvicorn")
    seen = await _client_seen_by_app(
        trusted="*", peer="172.18.0.5", xff="1.2.3.4, 203.0.113.9")
    assert seen == "1.2.3.4", (
        "'*' no longer trusts the leftmost entry; if uvicorn changed this, the "
        "warning in check_proxy_trust() should be revisited")


@pytest.mark.asyncio
async def test_the_default_setting_ignores_the_header_entirely():
    """The live bug, reproduced: with uvicorn's default the forwarded header is
    discarded and the app sees the proxy, so every caller shares one bucket."""
    pytest.importorskip("uvicorn")
    seen = await _client_seen_by_app(
        trusted=DEFAULT_FORWARDED_ALLOW_IPS, peer="172.18.0.5", xff="203.0.113.9")
    assert seen == "172.18.0.5", (
        "expected the proxy address, i.e. the shared-bucket failure mode")


@pytest.mark.asyncio
async def test_the_shipped_default_covers_a_docker_bridge_peer():
    """127.0.0.1 — uvicorn's default — never matches a Docker bridge address,
    which is the whole reason the limit was global. Asserted as behaviour."""
    pytest.importorskip("uvicorn")
    assert await _client_seen_by_app(
        trusted=SHIPPED_TRUST, peer="172.18.0.5", xff="203.0.113.9") == "203.0.113.9"


# ---------------------------------------------------------------------------
# The startup guard
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value,expect_warning", [
    (None, True),                      # unset -> uvicorn defaults to loopback
    ("127.0.0.1", True),               # explicit loopback -> same failure
    ("*", True),                       # trusts a client-controlled header
    (SHIPPED_TRUST, False),
    ("172.16.0.0/12", False),
])
def test_check_proxy_trust_flags_every_bad_state(monkeypatch, value, expect_warning):
    if value is None:
        monkeypatch.delenv("FORWARDED_ALLOW_IPS", raising=False)
    else:
        monkeypatch.setenv("FORWARDED_ALLOW_IPS", value)
    warning = check_proxy_trust()
    assert (warning is not None) is expect_warning, (value, warning)
    if expect_warning:
        assert "FORWARDED_ALLOW_IPS" in warning


def test_the_star_warning_explains_the_spoofing_risk(monkeypatch):
    """A warning that just says 'misconfigured' would get set to '*' next."""
    monkeypatch.setenv("FORWARDED_ALLOW_IPS", "*")
    warning = check_proxy_trust()
    assert "caller" in warning and "X-Forwarded-For" in warning


# ---------------------------------------------------------------------------
# The deployment setting itself
# ---------------------------------------------------------------------------

def _compose_auth_block(path: str) -> str:
    text = open(path).read()
    start = text.index("\n  auth-service:")
    rest = text[start + 1:]
    nxt = re.search(r"\n  [a-z][a-z0-9_-]*:\n", rest)
    return rest[: nxt.start()] if nxt else rest


@pytest.mark.parametrize("compose", [
    "../../../docker-compose.yml",                 # stock_microservices/
    "../../../../docker-compose.full-stack.yml",   # repo root
])
def test_compose_configures_proxy_trust_for_auth_service(compose):
    """The control is only correct if this ships. It is a deployment value with
    no runtime guard beyond a log line, and this project has been bitten six
    times by a default nobody asserted."""
    path = os.path.join(os.path.dirname(__file__), compose)
    if not os.path.exists(path):
        pytest.skip(f"{compose} not present")
    block = _compose_auth_block(path)
    assert "FORWARDED_ALLOW_IPS" in block, (
        "auth-service does not set FORWARDED_ALLOW_IPS, so uvicorn trusts only "
        "127.0.0.1 and the rate limit degrades to a global one")
    line = next(ln for ln in block.splitlines() if "FORWARDED_ALLOW_IPS" in ln)
    assert "*" not in line.split("=", 1)[1].replace("${", "").replace("}", ""), (
        f"FORWARDED_ALLOW_IPS must not be '*': {line.strip()}")
    # ...and the default must actually cover a Docker bridge peer.
    default = line.split(":-", 1)[1].rstrip("} \t") if ":-" in line else ""
    assert default, f"no inline default to fall back on: {line.strip()}"
    nets = [p for p in default.split(",") if "/" in p]
    assert any(ipaddress.ip_address("172.18.0.5") in ipaddress.ip_network(n)
               for n in nets), f"default does not cover a bridge peer: {default}"
