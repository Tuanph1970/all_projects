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

#: The local names a vendor component is bound to, now that gen-5 constructs
#: them individually (#142). Under gen-4 this test looked for
#: `stock.<kind>.<method>(...)`; the component is now the variable itself, so
#: the shape to catch is `<kind>.<method>(...)`.
#: Deliberately `vn_`-prefixed in the service. `listing` and `company` are
#: ordinary words that already named unrelated locals there — one function binds
#: `listing = item.get("listingInfo", {})` — so an unprefixed component variable
#: both risks shadowing and makes this guard match dictionaries it has no view
#: on. The prefix is what lets the check be exact instead of heuristic.
VENDOR_VARS = frozenset({"vn_quote", "vn_company", "vn_finance", "vn_listing",
                         "vn_trading", "vn_kbs_finance"})

#: The gen-5 classes. Constructing one is the other half of the bypass — a
#: `finance` construction runs the handshake (see the module docstring).
VENDOR_CLASSES = frozenset({"VnQuote", "VnCompany", "VnFinance", "VnListing",
                            "VnTrading"})


def _service() -> StockService:
    return StockService(repository=MagicMock())


def _distinct_class() -> MagicMock:
    """A gen-5 component class that returns a FRESH instance each call.

    A bare MagicMock caches `return_value`, so the class would hand back the
    same instance every time — which makes "are these two components distinct?"
    vacuously false and would have let a cache-key bug pass.
    """
    cls = MagicMock()
    cls.side_effect = lambda *a, **kw: MagicMock()
    return cls


# ── the structural guard ───────────────────────────────────────────────────

def test_no_unguarded_vendor_calls():
    """No `<component>.<method>(...)` outside `await vnstock_call(...)`.

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
        # finance.ratio(...) -> Attribute(attr='ratio', value=Name(id='finance'))
        if not (isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Name)):
            continue
        if fn.value.id not in VENDOR_VARS:
            continue
        if id(node) in guarded:
            continue
        offenders.append(f"line {node.lineno}: {fn.value.id}.{fn.attr}(...)")

    assert not offenders, (
        "vnstock calls bypassing the quota guard (Backlog #144):\n  "
        + "\n  ".join(offenders)
    )


def test_no_gen4_component_construction():
    """The gen-4 facade builds no components any more (#142).

    `Vnstock().stock(...)` constructed every component eagerly, so a caller that
    only wanted `listing.all_symbols()` still paid the Finance handshake.
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
    assert not offenders, f"gen-4 self.vnstock.stock(...) still in use: {offenders}"


def test_gen5_classes_are_only_constructed_inside_the_builder():
    """A bare `VnFinance(...)` anywhere else is the #144 bypass in gen-5 dress.

    The only legitimate construction sites are the lambdas in
    `_component`'s `builders` map, which `vnstock_call` then runs.
    """
    src = SERVICE_SRC.read_text()
    tree = ast.parse(src)

    builder_lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "_component":
            for inner in ast.walk(node):
                if hasattr(inner, "lineno"):
                    builder_lines.add(inner.lineno)

    offenders = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id in VENDOR_CLASSES
                and node.lineno not in builder_lines):
            offenders.append(f"line {node.lineno}: {node.func.id}(...)")
    assert not offenders, (
        f"gen-5 component constructed outside _component (Backlog #144): {offenders}"
    )


def test_the_listing_source_is_pinned_to_kbs():
    """gen-4 pinned `stock.listing` to KBS regardless of the configured source,
    and the row counts differ: KBS 1,517 symbols, VCI 1,757 (measured
    2026-11-10). The migration must not quietly re-point the universe."""
    from app.services.stock_service import LISTING_SOURCE
    assert LISTING_SOURCE == "KBS"


# ── the behaviour ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_construction_goes_through_the_guard():
    clear_components_cache()
    svc = _service()
    with patch("app.services.stock_service.vnstock_call") as guard:
        async def _passthrough(fn, *a, **kw):
            return fn(*a, **kw)
        guard.side_effect = _passthrough
        with patch("app.services.stock_service.VnCompany", new=_distinct_class()):
            await svc._company("FPT")
    assert guard.call_count == 1, "construction must be built inside vnstock_call"


@pytest.mark.asyncio
async def test_a_component_is_built_once_and_reused():
    """The point of #144's fix: N call sites, one handshake."""
    clear_components_cache()
    svc = _service()
    vn = _distinct_class()
    with patch("app.services.stock_service.VnCompany", new=vn):
        first = await svc._company("FPT")
        for _ in range(9):
            again = await svc._company("FPT")
            assert again is first
    assert vn.call_count == 1, "ten lookups must cost one construction"


@pytest.mark.asyncio
async def test_sources_do_not_share_a_component():
    """A KBS component must never be served for a VCI request — the KBS ratio
    path in get_company_financials depends on this."""
    clear_components_cache()
    svc = _service()
    with patch("app.services.stock_service.VnCompany", new=_distinct_class()):
        vci = await svc._company("FPT", "VCI")
        kbs = await svc._company("FPT", "KBS")
    assert vci is not kbs


@pytest.mark.asyncio
async def test_symbols_do_not_share_a_component():
    clear_components_cache()
    svc = _service()
    with patch("app.services.stock_service.VnCompany", new=_distinct_class()):
        assert await svc._company("FPT") is not await svc._company("VNM")


@pytest.mark.asyncio
async def test_the_symbol_is_normalised_so_case_is_not_a_cache_miss():
    clear_components_cache()
    svc = _service()
    vn = _distinct_class()
    with patch("app.services.stock_service.VnCompany", new=vn):
        a = await svc._company("fpt")
        b = await svc._company("FPT")
    assert a is b and vn.call_count == 1


@pytest.mark.asyncio
async def test_an_expired_entry_is_rebuilt_not_served_stale():
    """The handshake stores session COOKIES, so an entry kept forever would
    eventually fail every financial read for that symbol until a restart."""
    clear_components_cache()
    svc = _service()
    vn = _distinct_class()
    clock = [1000.0]
    # `_vnstock_last_call` is reset alongside the frozen clock, and it has to be.
    # The pacing in `vnstock_call` computes `_vnstock_last_call + interval - now`
    # from the same `time.monotonic`, so a frozen clock BELOW the real monotonic
    # baseline a previous test left behind yields a wait of ~500,000 seconds and
    # the test hangs instead of failing. This file hung exactly that way: both
    # TTL tests passed in isolation and timed out when run after the others.
    with patch("app.services.stock_service.VnCompany", new=vn), \
         patch.object(settings, "VNSTOCK_COMPONENTS_TTL_SECONDS", 900.0), \
         patch("app.services.stock_service._vnstock_last_call", 0.0), \
         patch("app.services.stock_service.time.monotonic", lambda: clock[0]):
        first = await svc._company("FPT")
        clock[0] += 899.0
        assert await svc._company("FPT") is first, "still fresh"
        clock[0] += 2.0                               # now past the TTL
        assert await svc._company("FPT") is not first
    assert vn.call_count == 2


@pytest.mark.asyncio
async def test_ttl_zero_disables_reuse_entirely():
    """An operator escape hatch that must actually opt out, not half-cache."""
    clear_components_cache()
    svc = _service()
    vn = _distinct_class()
    with patch("app.services.stock_service.VnCompany", new=vn), \
         patch.object(settings, "VNSTOCK_COMPONENTS_TTL_SECONDS", 0.0):
        a = await svc._company("FPT")
        b = await svc._company("FPT")
    assert a is not b
    assert vn.call_count == 2
    assert components_cache_state()["size"] == 0, "nothing may be retained"


@pytest.mark.asyncio
async def test_the_cache_is_bounded():
    """~1,750 symbols and no expiry sweep, so the bound is the only thing
    stopping unbounded growth in a long-lived process."""
    clear_components_cache()
    svc = _service()
    with patch("app.services.stock_service.VnCompany", new=_distinct_class()):
        for i in range(COMPONENTS_CACHE_MAX + 25):
            await svc._company(f"S{i:04d}")
    assert components_cache_state()["size"] == COMPONENTS_CACHE_MAX


@pytest.mark.asyncio
async def test_eviction_is_least_recently_used():
    """The nightly sync walks the whole universe; a FIFO cache would evict the
    symbol an interactive request is actively using."""
    clear_components_cache()
    svc = _service()
    with patch("app.services.stock_service.VnCompany", new=_distinct_class()):
        first = await svc._company("AAA")
        for i in range(COMPONENTS_CACHE_MAX - 1):
            await svc._company(f"S{i:04d}")
        assert await svc._company("AAA") is first      # keeps it hot
        for i in range(10):
            await svc._company(f"T{i:04d}")
        assert await svc._company("AAA") is first, "recently used was evicted"
