"""
Outbound fetch for seller-supplied URLs.

SELLERS SUPPLY THE URLS, WHICH MAKES THIS AN SSRF SURFACE, and that is the most
serious security consideration in this feature. An unguarded fetcher will
happily retrieve http://169.254.169.254/latest/meta-data/, http://db:3306, or
the Traefik dashboard on the internal network -- and hand the response back to
the person who asked for it.

Enforced in order (docs/ai-features/05-price-intelligence.md section 6):

  1. scheme is http or https
  2. host is on the allowlist (adapters + INTEL_ALLOWED_HOSTS)
  3. every resolved address is public
  4. redirects capped, and 2-3 RE-RUN ON EVERY HOP -- skipping that is the
     classic bypass, because the allowlisted host can 302 to anywhere
  5. robots.txt permits the path for our user agent
  6. we identify ourselves and give a contact URL
  7. connect/read timeouts and a streamed body cap
  8. per-host token bucket, shared across all sellers

On the residual DNS-rebinding window: addresses are validated and then httpx
resolves again when it connects, so in principle an attacker controlling DNS
for an allowlisted host could return a public address to us and a private one
to the connection. The allowlist is what makes this uninteresting -- the attack
requires control of a host we deliberately chose to trust, which is a different
and much larger problem than a seller pasting a link. Connecting to the
validated IP directly would close it, at the cost of hand-rolling TLS SNI and
Host headers through a custom transport; that trade is not worth it while the
allowlist holds.
"""
import ipaddress
import logging
import socket
import time
import urllib.robotparser
from dataclasses import dataclass
from typing import Optional, Tuple
from urllib.parse import urlparse, urlunparse

import httpx

from shared.cache import cache
from shared.config import settings

from app.services import adapters

logger = logging.getLogger(__name__)

USER_AGENT = (
    "MercaiPriceBot/1.0 (+https://mercai.tuan1970.com/bot; "
    "price comparison for our own sellers)"
)

CONNECT_TIMEOUT = 5.0
READ_TIMEOUT = 10.0
MAX_BYTES = 2 * 1024 * 1024
MAX_REDIRECTS = 3
ROBOTS_TTL = 86_400

# Statuses are part of the contract: each maps to one plain-language message
# for the seller (section 6.1). Never invent a new one at a call site.
OK = "ok"
HOST_NOT_ALLOWED = "host_not_allowed"
BLOCKED_ROBOTS = "blocked_robots"
JS_REQUIRED = "js_required"
NO_PRICE_FOUND = "no_price_found"
HTTP_ERROR = "http_error"
TIMEOUT = "timeout"
IMPLAUSIBLE = "implausible"
REFUSED_ADDRESS = "refused_address"
RATE_LIMITED = "rate_limited"

MESSAGES = {
    OK: "Price read successfully.",
    HOST_NOT_ALLOWED: "We don't support this site yet.",
    BLOCKED_ROBOTS: "This site asks us not to read its pages.",
    JS_REQUIRED: "This page builds its price in the browser, so we can't read it.",
    NO_PRICE_FOUND: "We couldn't find a price on this page.",
    HTTP_ERROR: "That page didn't respond.",
    TIMEOUT: "That page took too long to respond.",
    IMPLAUSIBLE: "We read a price that doesn't look right, so we're ignoring it.",
    REFUSED_ADDRESS: "That address isn't one we're able to fetch.",
    RATE_LIMITED: "We've checked this site very recently. Try again shortly.",
}


class FetchRefused(Exception):
    """Refused before any request left the process."""

    def __init__(self, status: str, detail: str = ""):
        super().__init__(detail or status)
        self.status = status
        self.detail = detail


@dataclass
class FetchResult:
    status: str
    url: str
    final_url: str
    http_status: Optional[int] = None
    body: str = ""
    elapsed_ms: int = 0
    detail: str = ""


# ---------------------------------------------------------------------------
# URL hygiene
# ---------------------------------------------------------------------------

TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "gclid", "fbclid", "msclkid", "ref", "referrer", "src", "source",
}


def normalise_url(raw: str) -> str:
    """
    Canonical form for storage and de-duplication.

    Lowercases the host, drops the fragment and strips tracking parameters, so
    the same listing pasted twice from two different campaign links is one row
    rather than two comparables that will always agree.
    """
    parsed = urlparse((raw or "").strip())
    query = "&".join(
        part for part in (parsed.query or "").split("&")
        if part and part.split("=")[0].lower() not in TRACKING_PARAMS
    )
    return urlunparse((
        parsed.scheme.lower(), parsed.netloc.lower(), parsed.path or "/",
        parsed.params, query, "",
    ))


# ---------------------------------------------------------------------------
# Address validation
# ---------------------------------------------------------------------------

def _is_public(address: str) -> bool:
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return False
    return not (
        ip.is_private or ip.is_loopback or ip.is_link_local
        or ip.is_multicast or ip.is_reserved or ip.is_unspecified
    )


def resolve_and_validate(host: str) -> Tuple[bool, str]:
    """
    Every address the host resolves to must be public.

    ALL of them, not the first: a hostname with one public and one private A
    record would otherwise pass the check and then connect to the private one
    depending on resolver order.
    """
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError as exc:
        return False, f"{host} did not resolve ({exc})"

    addresses = {info[4][0] for info in infos}
    if not addresses:
        return False, f"{host} resolved to nothing"
    bad = [a for a in addresses if not _is_public(a)]
    if bad:
        return False, f"{host} resolves to a non-public address ({', '.join(sorted(bad))})"
    return True, ""


def check_url(raw_url: str) -> Tuple[str, str]:
    """Everything checkable before a packet leaves. (host, detail) or raises."""
    parsed = urlparse((raw_url or "").strip())

    if parsed.scheme not in ("http", "https"):
        raise FetchRefused(REFUSED_ADDRESS, "Only http and https URLs are supported")
    if not parsed.hostname:
        raise FetchRefused(REFUSED_ADDRESS, "That URL has no host")

    # The allowlist runs BEFORE the port check on purpose. Both refuse
    # `http://db:3306`, but "we don't support db" is the useful sentence and
    # "only standard web ports" is a confusing one -- the seller's mistake was
    # the host, not the port.
    host = parsed.hostname.lower()
    if not adapters.is_allowed(host):
        supported = ", ".join(adapters.allowed_hosts()) or "none yet"
        raise FetchRefused(
            HOST_NOT_ALLOWED,
            f"We don't support {host} yet. Supported: {supported}",
        )

    if parsed.port and parsed.port not in (80, 443):
        raise FetchRefused(REFUSED_ADDRESS, "Only the standard web ports are supported")

    ok, detail = resolve_and_validate(host)
    if not ok:
        raise FetchRefused(REFUSED_ADDRESS, detail)
    return host, ""


# ---------------------------------------------------------------------------
# robots.txt
# ---------------------------------------------------------------------------

def robots_allows(scheme: str, host: str, path: str) -> bool:
    """
    Honour robots.txt, cached for a day.

    Cheap, and it materially improves where we stand: fetching a page a seller
    already opened in their own browser, from a host we chose, at a rate the
    operator asked for. A parse failure is treated as permission, because a
    malformed robots.txt is not a refusal.
    """
    key = f"mercai:intel:robots:{host}"
    body = cache.get(key)
    if body is None:
        try:
            response = httpx.get(
                f"{scheme}://{host}/robots.txt",
                headers={"User-Agent": USER_AGENT},
                timeout=CONNECT_TIMEOUT,
                follow_redirects=True,
            )
            body = response.text if response.status_code == 200 else ""
        except Exception:
            body = ""
        cache.set(key, body, ttl=ROBOTS_TTL)

    if not body:
        return True
    parser = urllib.robotparser.RobotFileParser()
    try:
        parser.parse(body.splitlines())
        return parser.can_fetch(USER_AGENT, path or "/")
    except Exception:
        return True


# ---------------------------------------------------------------------------
# Per-host politeness budget
# ---------------------------------------------------------------------------

def host_budget_available(host: str, consume: bool = True) -> bool:
    """
    One request per INTEL_HOST_INTERVAL_SECONDS per host, plus a daily cap.

    Shared across every seller, so no amount of refresh-tapping can make us
    hammer a site. Fails OPEN when Redis is down -- the timeouts and the
    redirect cap still bound the damage, and blocking sellers because a cache
    is unavailable trades a real feature for a theoretical courtesy.
    """
    client = cache.client
    if client is None:
        return True
    try:
        gate = f"mercai:intel:hostgate:{host}"
        daily = f"mercai:intel:hostday:{host}"
        if not consume:
            return not client.exists(gate)
        if client.exists(gate):
            return False
        if int(client.get(daily) or 0) >= settings.INTEL_HOST_DAILY_CAP:
            return False
        client.setex(gate, settings.INTEL_HOST_INTERVAL_SECONDS, "1")
        if client.incr(daily) == 1:
            client.expire(daily, 86_400)
        return True
    except Exception:
        logger.warning("Host budget check failed; allowing", exc_info=True)
        return True


# ---------------------------------------------------------------------------
# The fetch
# ---------------------------------------------------------------------------

def fetch(raw_url: str, *, respect_budget: bool = True) -> FetchResult:
    """
    Retrieve a page, or return a FetchResult saying honestly why not.

    Redirects are followed MANUALLY so that the allowlist and address checks
    run again on every hop. `follow_redirects=True` would let an allowlisted
    host bounce us anywhere it liked, which is the whole attack.
    """
    url = normalise_url(raw_url)
    host, _ = check_url(url)

    if respect_budget and not host_budget_available(host):
        raise FetchRefused(RATE_LIMITED, f"Recently fetched from {host}")

    parsed = urlparse(url)
    if not robots_allows(parsed.scheme, host, parsed.path):
        raise FetchRefused(BLOCKED_ROBOTS, f"{host}/robots.txt disallows {parsed.path}")

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
    }
    timeout = httpx.Timeout(READ_TIMEOUT, connect=CONNECT_TIMEOUT)
    started = time.monotonic()
    current = url

    try:
        with httpx.Client(follow_redirects=False, timeout=timeout) as client:
            for _ in range(MAX_REDIRECTS + 1):
                with client.stream("GET", current, headers=headers) as response:
                    if response.is_redirect:
                        location = response.headers.get("location")
                        if not location:
                            break
                        current = str(response.url.join(location))
                        # Re-validate the new target. This is the line that
                        # makes the manual redirect loop worth writing.
                        check_url(current)
                        continue

                    chunks, size = [], 0
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > MAX_BYTES:
                            break
                        chunks.append(chunk)
                    body = b"".join(chunks).decode(
                        response.encoding or "utf-8", errors="replace"
                    )
                    elapsed = int((time.monotonic() - started) * 1000)

                    if response.status_code != 200:
                        return FetchResult(
                            status=HTTP_ERROR, url=url, final_url=current,
                            http_status=response.status_code, elapsed_ms=elapsed,
                            detail=f"HTTP {response.status_code}",
                        )
                    return FetchResult(
                        status=OK, url=url, final_url=current,
                        http_status=200, body=body, elapsed_ms=elapsed,
                    )
        raise FetchRefused(HTTP_ERROR, "Too many redirects")
    except httpx.TimeoutException:
        return FetchResult(
            status=TIMEOUT, url=url, final_url=current,
            elapsed_ms=int((time.monotonic() - started) * 1000),
            detail="The page did not respond in time",
        )
    except httpx.HTTPError as exc:
        return FetchResult(
            status=HTTP_ERROR, url=url, final_url=current,
            elapsed_ms=int((time.monotonic() - started) * 1000),
            detail=str(exc)[:200],
        )
