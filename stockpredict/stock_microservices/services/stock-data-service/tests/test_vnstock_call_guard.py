"""Backlog #144 — every vnstock interaction goes through the quota guard.

The bug this file exists to prevent coming back: 11 data fetches called
`stock.listing.*` / `stock.finance.*` directly, and 18 sites built a
`StockComponents` per invocation, all outside `vnstock_call`. So they spent
upstream requests the guard could not pace, retry or even see — and they did it
synchronously on the event loop.

WHY CONSTRUCTION COUNTS AS A CALL, measured 2026-11-10 inside the service's own
container rather than assumed: `Vnstock().stock(...)` builds
`Finance(symbol, source)`, whose `__init__` runs `_handshake()` — a GET to
trading.vietcap.com.vn/priceboard whose session cookies it keeps. ~0.6s when
idle; back-to-back, the SIXTH construction read-times-out at 30s, and 20 of them
took 102s with three outright failures. That is the mechanism behind #134's
bursts and the reason #134's pacing fix did not stop them: the guard was pacing
DATA calls while the failures were in CONSTRUCTION.

`test_no_unguarded_vendor_calls` is the one that matters most here. The other
tests check the behaviour that was built; that one checks the behaviour cannot
quietly regress, in the manner of prediction-service's test_schema_sources.py.
"""
import ast
import asyncio
import pathlib
from unittest.mock import MagicMock, patch

import pytest

from app.config import get_settings
from app.services.stock_service import (
    COMPONENTS_CACHE_MAX,
    StockService,
    clear_components_cache,
    components_cache_state,
)

settings = get_settings()

SERVICE_SRC = pathlib.Path(__file__).resolve().parents[1] / "app" / "services" / "stock_service.py"

#: The vendor component attributes a call lands on. Reaching any of their
#: methods is an upstream request and must be guarded.
VENDOR_ATTRS = frozenset({"quote", "company", "finance", "listing", "trading"})


def _service() -> StockService:
    return StockService(repository=MagicMock())


def _distinct_vnstock() -> MagicMock:
    """A `Vnstock` whose .stock() returns a FRESH object each call.

    A bare MagicMock caches `return_value`, so `.stock()` hands back the same
    instance every time — which makes "are these two components distinct?"
    vacuously false and would have let a cache-key bug pass.
    """
    vn = MagicMock()
    vn.stock.side_effect = lambda *a, **kw: MagicMock()
    return vn


# ── the structural guard ───────────────────────────────────────────────────

def test_no_unguarded_vendor_calls():
    """No `stock.<component>.<method>(...)` outside `await vnstock_call(...)`.

    Walks the AST rather than grepping, so a reformatted or multi-line call
    cannot slip past. A new call site must either go through the guard or make
    the reason it does not explicit by changing this test.
    """
    tree = ast.parse(SERVICE_SRC.read_text())

    guarded: set[int] = set()
    for node in ast.walk(tree):
        # Collect everything lexically inside an `await vnstock_call(...)`.
        if isinstance(node, ast.Await) and isinstance(node.value, ast.Call):
            fn = node.value.func
            if isinstance(fn, ast.Name) and fn.id == "vnstock_call":
                for inner in ast.walk(node):
                    guarded.add(id(inner))

    offenders = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        # stock.finance.ratio(...) -> Attribute(attr='ratio', value=Attribute(attr='finance'))
        if not (isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Attribute)):
            continue
        if fn.value.attr not in VENDOR_ATTRS:
            continue
        if id(node) in guarded:
            continue
        offenders.append(f"line {node.lineno}: .{fn.value.attr}.{fn.attr}(...)")

    assert not offenders, (
        "vnstock calls bypassing the quota guard (Backlog #144):\n  "
        + "\n  ".join(offenders)
    )


def test_no_direct_component_construction():
    """`self.vnstock.stock(...)` is routed through `_components`, which guards it.

    Construction is an upstream request (see the module docstring), so a bare
    one is the same defect in a different shape — and it was the harder half to
    see, because one site had the construction INSIDE a `vnstock_call(...)`
    argument list, where it was evaluated eagerly on the event loop and only
    looked guarded.
    """
    tree = ast.parse(SERVICE_SRC.read_text())
    offenders = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        if (isinstance(fn, ast.Attribute) and fn.attr == "stock"
                and isinstance(fn.value, ast.Attribute) and fn.value.attr == "vnstock"):
            offenders.append(f"line {node.lineno}")
    assert not offenders, (
        "direct self.vnstock.stock(...) construction outside _components "
        f"(Backlog #144): {offenders}"
    )


# ── the behaviour ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_construction_goes_through_the_guard():
    clear_components_cache()
    svc = _service()
    with patch("app.services.stock_service.vnstock_call") as guard:
        async def _passthrough(fn, *a, **kw):
            return fn(*a, **kw)
        guard.side_effect = _passthrough
        with patch.object(StockService, "vnstock", new=MagicMock()):
            await svc._components("FPT")
    assert guard.call_count == 1, "construction must be built inside vnstock_call"


@pytest.mark.asyncio
async def test_a_component_is_built_once_and_reused():
    """The point of #144's fix: N call sites, one handshake."""
    clear_components_cache()
    svc = _service()
    vn = MagicMock()
    with patch.object(StockService, "vnstock", new=vn):
        first = await svc._components("FPT")
        for _ in range(9):
            again = await svc._components("FPT")
            assert again is first
    assert vn.stock.call_count == 1, "ten lookups must cost one construction"


@pytest.mark.asyncio
async def test_sources_do_not_share_a_component():
    """A KBS component must never be served for a VCI request — the KBS ratio
    path in get_company_financials depends on this."""
    clear_components_cache()
    svc = _service()
    with patch.object(StockService, "vnstock", new=_distinct_vnstock()):
        vci = await svc._components("FPT", "VCI")
        kbs = await svc._components("FPT", "KBS")
    assert vci is not kbs


@pytest.mark.asyncio
async def test_symbols_do_not_share_a_component():
    clear_components_cache()
    svc = _service()
    with patch.object(StockService, "vnstock", new=_distinct_vnstock()):
        assert await svc._components("FPT") is not await svc._components("VNM")


@pytest.mark.asyncio
async def test_the_symbol_is_normalised_so_case_is_not_a_cache_miss():
    clear_components_cache()
    svc = _service()
    vn = MagicMock()
    with patch.object(StockService, "vnstock", new=vn):
        a = await svc._components("fpt")
        b = await svc._components("FPT")
    assert a is b and vn.stock.call_count == 1


@pytest.mark.asyncio
async def test_an_expired_entry_is_rebuilt_not_served_stale():
    """The handshake stores session COOKIES, so an entry kept forever would
    eventually fail every financial read for that symbol until a restart."""
    clear_components_cache()
    svc = _service()
    vn = _distinct_vnstock()
    clock = [1000.0]
    # `_vnstock_last_call` is reset alongside the frozen clock, and it has to be.
    # The pacing in `vnstock_call` computes `_vnstock_last_call + interval - now`
    # from the same `time.monotonic`, so a frozen clock BELOW the real monotonic
    # baseline a previous test left behind yields a wait of ~500,000 seconds and
    # the test hangs instead of failing. This file hung exactly that way: both
    # TTL tests passed in isolation and timed out when run after the others.
    with patch.object(StockService, "vnstock", new=vn), \
         patch.object(settings, "VNSTOCK_COMPONENTS_TTL_SECONDS", 900.0), \
         patch("app.services.stock_service._vnstock_last_call", 0.0), \
         patch("app.services.stock_service.time.monotonic", lambda: clock[0]):
        first = await svc._components("FPT")
        clock[0] += 899.0
        assert await svc._components("FPT") is first, "still fresh"
        clock[0] += 2.0                               # now past the TTL
        assert await svc._components("FPT") is not first
    assert vn.stock.call_count == 2


@pytest.mark.asyncio
async def test_ttl_zero_disables_reuse_entirely():
    """An operator escape hatch that must actually opt out, not half-cache."""
    clear_components_cache()
    svc = _service()
    vn = _distinct_vnstock()
    with patch.object(StockService, "vnstock", new=vn), \
         patch.object(settings, "VNSTOCK_COMPONENTS_TTL_SECONDS", 0.0):
        a = await svc._components("FPT")
        b = await svc._components("FPT")
    assert a is not b
    assert vn.stock.call_count == 2
    assert components_cache_state()["size"] == 0, "nothing may be retained"


@pytest.mark.asyncio
async def test_the_cache_is_bounded():
    """~1,750 symbols and no expiry sweep, so the bound is the only thing
    stopping unbounded growth in a long-lived process."""
    clear_components_cache()
    svc = _service()
    with patch.object(StockService, "vnstock", new=_distinct_vnstock()):
        for i in range(COMPONENTS_CACHE_MAX + 25):
            await svc._components(f"S{i:04d}")
    assert components_cache_state()["size"] == COMPONENTS_CACHE_MAX


@pytest.mark.asyncio
async def test_eviction_is_least_recently_used():
    """The nightly sync walks the whole universe; a FIFO cache would evict the
    symbol an interactive request is actively using."""
    clear_components_cache()
    svc = _service()
    with patch.object(StockService, "vnstock", new=_distinct_vnstock()):
        first = await svc._components("AAA")
        for i in range(COMPONENTS_CACHE_MAX - 1):
            await svc._components(f"S{i:04d}")
        assert await svc._components("AAA") is first      # keeps it hot
        for i in range(10):
            await svc._components(f"T{i:04d}")
        assert await svc._components("AAA") is first, "recently used was evicted"
