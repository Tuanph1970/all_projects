"""
Redirect handling.

`follow_redirects=True` would be one word shorter and would defeat the entire
allowlist: an allowlisted host can 302 to anywhere it likes, including
169.254.169.254. These tests exist because that is the bypass everyone forgets.
"""
from pathlib import Path

import httpx
import pytest

SERVICE = Path(__file__).resolve().parents[2] / "services" / "intel"


@pytest.fixture()
def fetcher(load_service, monkeypatch):
    load_service(SERVICE)
    import app.services.adapters as adapters
    import app.services.fetcher as fetcher_module

    adapters.registry.cache_clear()
    monkeypatch.setattr(adapters, "allowed_hosts", lambda: ["good.example"])
    monkeypatch.setattr(
        adapters, "is_allowed",
        lambda host: adapters.normalise_host(host) == "good.example",
    )
    monkeypatch.setattr(
        fetcher_module.socket, "getaddrinfo",
        lambda *a, **k: [(2, 1, 6, "", ("93.184.216.34", 0))],
    )
    # Robots and the host budget are covered elsewhere; keep them out of the way.
    monkeypatch.setattr(fetcher_module, "robots_allows", lambda *a, **k: True)
    monkeypatch.setattr(fetcher_module, "host_budget_available", lambda *a, **k: True)
    return fetcher_module


def install_transport(monkeypatch, fetcher, handler):
    real_client = httpx.Client

    def client_factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(fetcher.httpx, "Client", client_factory)


def test_a_redirect_to_a_disallowed_host_is_refused(fetcher, monkeypatch):
    def handler(request):
        if request.url.host == "good.example":
            return httpx.Response(302, headers={"location": "http://evil.test/x"})
        return httpx.Response(200, text="<html>should never be reached</html>")

    install_transport(monkeypatch, fetcher, handler)
    with pytest.raises(fetcher.FetchRefused) as caught:
        fetcher.fetch("http://good.example/start")
    assert caught.value.status == fetcher.HOST_NOT_ALLOWED


def test_a_redirect_to_cloud_metadata_is_refused(fetcher, monkeypatch):
    """The payload this whole file exists for."""
    def handler(request):
        if request.url.host == "good.example":
            return httpx.Response(
                302, headers={"location": "http://169.254.169.254/latest/meta-data/"}
            )
        return httpx.Response(200, text="SECRET")

    install_transport(monkeypatch, fetcher, handler)
    with pytest.raises(fetcher.FetchRefused):
        fetcher.fetch("http://good.example/start")


def test_a_redirect_within_the_allowlist_is_followed(fetcher, monkeypatch):
    def handler(request):
        if request.url.path == "/start":
            return httpx.Response(302, headers={"location": "/final"})
        return httpx.Response(200, text="<html>arrived</html>")

    install_transport(monkeypatch, fetcher, handler)
    result = fetcher.fetch("http://good.example/start")
    assert result.status == fetcher.OK
    assert "arrived" in result.body
    assert result.final_url.endswith("/final")


def test_a_redirect_loop_terminates(fetcher, monkeypatch):
    def handler(request):
        return httpx.Response(302, headers={"location": "http://good.example/loop"})

    install_transport(monkeypatch, fetcher, handler)
    with pytest.raises(fetcher.FetchRefused) as caught:
        fetcher.fetch("http://good.example/loop")
    assert caught.value.status == fetcher.HTTP_ERROR


def test_a_non_200_is_reported_not_raised(fetcher, monkeypatch):
    """A competitor's 404 is a fact about the market, not an error in our system."""
    install_transport(monkeypatch, fetcher, lambda r: httpx.Response(404, text="gone"))
    result = fetcher.fetch("http://good.example/missing")
    assert result.status == fetcher.HTTP_ERROR
    assert result.http_status == 404


def test_an_oversized_body_is_truncated_not_streamed_forever(fetcher, monkeypatch):
    big = "x" * (fetcher.MAX_BYTES + 50_000)
    install_transport(monkeypatch, fetcher, lambda r: httpx.Response(200, text=big))
    result = fetcher.fetch("http://good.example/huge")
    assert result.status == fetcher.OK
    assert len(result.body) <= fetcher.MAX_BYTES


def test_a_timeout_is_its_own_status(fetcher, monkeypatch):
    def handler(request):
        raise httpx.ConnectTimeout("too slow")

    install_transport(monkeypatch, fetcher, handler)
    result = fetcher.fetch("http://good.example/slow")
    assert result.status == fetcher.TIMEOUT
    assert fetcher.MESSAGES[result.status]
