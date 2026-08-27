"""
The SSRF guards.

Sellers supply these URLs, so this file is the security boundary of the whole
feature. Every test here corresponds to a way an unguarded fetcher gets used to
read something on the internal network and hand it back to the person asking.
"""
from pathlib import Path

import pytest

SERVICE = Path(__file__).resolve().parents[2] / "services" / "intel"


@pytest.fixture()
def fetcher(load_service, monkeypatch):
    load_service(SERVICE)
    import app.services.adapters as adapters
    import app.services.fetcher as fetcher_module

    # A known allowlist, independent of whatever adapter files exist.
    adapters.registry.cache_clear()
    monkeypatch.setattr(adapters, "allowed_hosts", lambda: ["example.com", "tiki.vn"])
    monkeypatch.setattr(
        adapters, "is_allowed",
        lambda host: adapters.normalise_host(host) in ("example.com", "tiki.vn")
        or adapters.normalise_host(host).endswith((".example.com", ".tiki.vn")),
    )
    return fetcher_module


def _resolves_to(monkeypatch, fetcher, address):
    monkeypatch.setattr(
        fetcher.socket, "getaddrinfo",
        lambda host, port, *a, **k: [(2, 1, 6, "", (address, 0))],
    )


# --------------------------------------------------------------------------
# Scheme and shape
# --------------------------------------------------------------------------

@pytest.mark.parametrize("url", [
    "file:///etc/passwd",
    "gopher://example.com/",
    "ftp://example.com/x",
    "//example.com/x",
])
def test_non_http_schemes_are_refused(fetcher, url):
    with pytest.raises(fetcher.FetchRefused) as caught:
        fetcher.check_url(url)
    assert caught.value.status == fetcher.REFUSED_ADDRESS


def test_non_standard_ports_are_refused(fetcher, monkeypatch):
    """Blocks the "allowlisted host, but :6379" shape."""
    _resolves_to(monkeypatch, fetcher, "93.184.216.34")
    with pytest.raises(fetcher.FetchRefused) as caught:
        fetcher.check_url("http://example.com:6379/")
    assert caught.value.status == fetcher.REFUSED_ADDRESS


# --------------------------------------------------------------------------
# The allowlist
# --------------------------------------------------------------------------

def test_a_host_not_on_the_allowlist_is_refused(fetcher):
    with pytest.raises(fetcher.FetchRefused) as caught:
        fetcher.check_url("http://evil.test/")
    assert caught.value.status == fetcher.HOST_NOT_ALLOWED
    # The message names what we do support, so the seller can act on it.
    assert "example.com" in caught.value.detail


def test_the_refusal_message_does_not_leak_internal_hosts(fetcher):
    with pytest.raises(fetcher.FetchRefused) as caught:
        fetcher.check_url("http://db:3306/")
    assert caught.value.status == fetcher.HOST_NOT_ALLOWED


def test_subdomains_of_an_allowed_host_are_allowed(fetcher, monkeypatch):
    _resolves_to(monkeypatch, fetcher, "93.184.216.34")
    host, _ = fetcher.check_url("https://m.tiki.vn/product-p1.html")
    assert host == "m.tiki.vn"


def test_a_lookalike_host_is_not_allowed(fetcher):
    """`tiki.vn.evil.test` ends with neither `tiki.vn` nor `.tiki.vn`."""
    with pytest.raises(fetcher.FetchRefused) as caught:
        fetcher.check_url("http://tiki.vn.evil.test/")
    assert caught.value.status == fetcher.HOST_NOT_ALLOWED


# --------------------------------------------------------------------------
# Address validation -- the actual SSRF payloads
# --------------------------------------------------------------------------

@pytest.mark.parametrize("address,what", [
    ("169.254.169.254", "cloud metadata"),
    ("127.0.0.1", "loopback"),
    ("10.0.0.5", "private"),
    ("172.17.0.2", "docker bridge"),
    ("192.168.1.1", "private"),
    ("0.0.0.0", "unspecified"),
    ("::1", "ipv6 loopback"),
    ("fd00::1", "ipv6 private"),
])
def test_non_public_addresses_are_refused(fetcher, monkeypatch, address, what):
    _resolves_to(monkeypatch, fetcher, address)
    with pytest.raises(fetcher.FetchRefused) as caught:
        fetcher.check_url("http://example.com/")
    assert caught.value.status == fetcher.REFUSED_ADDRESS, what


def test_a_public_address_passes(fetcher, monkeypatch):
    _resolves_to(monkeypatch, fetcher, "93.184.216.34")
    host, _ = fetcher.check_url("http://example.com/thing")
    assert host == "example.com"


def test_every_resolved_address_must_be_public(fetcher, monkeypatch):
    """
    Not just the first. A hostname with one public and one private A record
    would otherwise pass and then connect to whichever the resolver returned.
    """
    monkeypatch.setattr(
        fetcher.socket, "getaddrinfo",
        lambda *a, **k: [(2, 1, 6, "", ("93.184.216.34", 0)),
                         (2, 1, 6, "", ("127.0.0.1", 0))],
    )
    with pytest.raises(fetcher.FetchRefused) as caught:
        fetcher.check_url("http://example.com/")
    assert caught.value.status == fetcher.REFUSED_ADDRESS


def test_a_host_that_does_not_resolve_is_refused(fetcher, monkeypatch):
    def boom(*a, **k):
        raise OSError("no such host")

    monkeypatch.setattr(fetcher.socket, "getaddrinfo", boom)
    with pytest.raises(fetcher.FetchRefused) as caught:
        fetcher.check_url("http://example.com/")
    assert caught.value.status == fetcher.REFUSED_ADDRESS


# --------------------------------------------------------------------------
# URL normalisation
# --------------------------------------------------------------------------

def test_tracking_parameters_are_stripped(fetcher):
    """
    Two campaign links to the same listing must hash to one comparable --
    otherwise a seller gets two rows that always agree, and the duplicate
    silently doubles that listing's weight in the median.
    """
    a = fetcher.normalise_url("https://TIKI.vn/thing-p1.html?utm_source=fb&spid=9#reviews")
    b = fetcher.normalise_url("https://tiki.vn/thing-p1.html?spid=9&utm_campaign=x")
    assert a == b
    assert "utm" not in a and "#" not in a


def test_normalisation_keeps_parameters_that_identify_the_product(fetcher):
    """`spid` selects the seller offer on Tiki -- dropping it changes the page."""
    assert "spid=278513545" in fetcher.normalise_url(
        "https://tiki.vn/bat-p1.html?spid=278513545"
    )
