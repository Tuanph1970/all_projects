"""N3 — watched-symbol resolver (FR-NEWS-WATCH).

Unions the owned/watched tickers from portfolio-service + decision-helper over HTTP.
Resilient to one upstream being down (EC-N7); user-agnostic (EC-N10 — only tickers
cross the wire, never user identity).
"""
from __future__ import annotations

import httpx
import pytest

from app.ingest.watch_source import WatchSource

_PORT = "http://portfolio-service:8003"
_HELP = "http://decision-helper-service:8010"


def _source(handler) -> WatchSource:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return WatchSource(_PORT, _HELP, client=client)


def test_resolve_unions_uppercases_dedups_sorts():
    def handler(req: httpx.Request) -> httpx.Response:
        if "watched-symbols" in req.url.path:
            return httpx.Response(200, json=["fpt", "ACB"])
        if "watched-tickers" in req.url.path:
            return httpx.Response(200, json=["acb", "vnm"])  # ACB overlaps
        return httpx.Response(404)

    assert _source(handler).resolve() == ["ACB", "FPT", "VNM"]


def test_accepts_wrapped_payloads():
    def handler(req: httpx.Request) -> httpx.Response:
        if "watched-symbols" in req.url.path:
            return httpx.Response(200, json={"symbols": ["FPT"]})
        if "watched-tickers" in req.url.path:
            return httpx.Response(200, json={"tickers": ["HPG"]})
        return httpx.Response(404)

    assert _source(handler).resolve() == ["FPT", "HPG"]


def test_one_upstream_down_still_returns_the_other():
    def handler(req: httpx.Request) -> httpx.Response:
        if "watched-symbols" in req.url.path:
            return httpx.Response(503)  # portfolio down
        if "watched-tickers" in req.url.path:
            return httpx.Response(200, json=["FPT"])
        return httpx.Response(404)

    assert _source(handler).resolve() == ["FPT"]


def test_both_down_returns_empty_no_raise():
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    assert _source(handler).resolve() == []


def test_hits_the_two_documented_paths():
    seen = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(req.url.path)
        return httpx.Response(200, json=[])

    _source(handler).resolve()
    assert any(p.endswith("/portfolio/watched-symbols") for p in seen)
    assert any(p.endswith("/helper/watched-tickers") for p in seen)


def test_network_error_is_swallowed():
    def handler(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    assert _source(handler).resolve() == []
