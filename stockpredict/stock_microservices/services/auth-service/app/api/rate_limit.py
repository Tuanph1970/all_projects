"""Per-IP rate limiting for the auth-service's sensitive endpoints.

Uses slowapi (a Starlette wrapper around `limits`), keyed by client IP, to shut
down the trivial single-IP brute-force / enumeration cases that drove
SECURITY_AUDIT.md MEDIUM #7. Best-effort: a botnet can still spread requests
across many addresses.

The limiter instance is shared across all routes so the budget is per IP rather
than per endpoint. To rate-limit a route, decorate it with
`@limiter.limit("N/minute")`; slowapi requires the route to take
`request: Request` so it can read the address.

WHERE THE CLIENT ADDRESS COMES FROM — and a correction (Backlog #24)
--------------------------------------------------------------------
This module previously claimed that `get_remote_address` "respects
X-Forwarded-For when present (Traefik sets this)". **That was false**, and the
rate limit was not per-IP at all. `slowapi.util.get_remote_address` reads
`request.client.host` and nothing else:

    if not request.client or not request.client.host:
        return "127.0.0.1"
    return request.client.host

`request.client` is the TCP peer unless uvicorn's `ProxyHeadersMiddleware`
rewrites it, and that middleware only trusts `X-Forwarded-For` when the peer
appears in `--forwarded-allow-ips` / `FORWARDED_ALLOW_IPS`, **which defaults to
`127.0.0.1`**. Behind Traefik the peer is a Docker bridge address, so the
header was ignored and every request through the gateway keyed to Traefik's
own IP. Measured, not inferred: a login through the gateway logged client
`172.18.0.5`, which is Traefik.

The effect was that all callers shared ONE bucket. At 5/minute that is a
self-inflicted denial of service — six people signing in inside a minute, or
one person mistyping a password five times, locks out everyone — and it made
the control trivially abusable as a DoS rather than a brute-force defence.

The fix is deployment configuration, so `check_proxy_trust()` below exists to
make its absence loud instead of silent.

DO NOT SET `FORWARDED_ALLOW_IPS=*`
----------------------------------
It is the usual advice and it is wrong here. uvicorn walks the forwarded chain
**in reverse** and returns the first *untrusted* hop, which is spoof-resistant;
but with `*` it takes `x_forwarded_for_hosts[0]` — the **leftmost** entry,
which the client controls. Verified against the installed uvicorn (0.52.4):

    trusted="172.18.0.0/16", chain "1.2.3.4, 203.0.113.9" -> 203.0.113.9  (spoof ignored)
    trusted="*",             same chain                   -> 1.2.3.4      (spoof wins)

So `*` would let any caller reset its own bucket by sending a header. Use the
proxy's network instead.
"""
import os
from typing import Optional

from slowapi import Limiter
from slowapi.util import get_remote_address


def _should_disable_for_tests() -> bool:
    """Disable rate limiting under pytest so the test suite can hit
    /login and /reset-password many times in quick succession without
    triggering 429s. Detected via PYTEST_CURRENT_TEST (set by pytest)
    or an explicit RATE_LIMIT_ENABLED=false override.
    """
    if os.environ.get("RATE_LIMIT_ENABLED", "").lower() == "false":
        return True
    if "PYTEST_CURRENT_TEST" in os.environ:
        return True
    return False


#: The deployment setting this module's correctness depends on. uvicorn reads
#: it from the environment and defaults it to "127.0.0.1", which never matches
#: a Docker bridge peer — see the module docstring.
DEFAULT_FORWARDED_ALLOW_IPS = "127.0.0.1"


def proxy_trust_setting() -> str:
    """Whatever uvicorn will use for `--forwarded-allow-ips`."""
    return os.environ.get("FORWARDED_ALLOW_IPS", DEFAULT_FORWARDED_ALLOW_IPS)


def check_proxy_trust() -> Optional[str]:
    """Return a warning if per-IP limiting cannot work, else None.

    Called at startup so a misconfiguration announces itself. Two bad states:

    * the setting is absent or still loopback-only — behind a proxy every
      request keys to the proxy and the budget is global;
    * the setting is `*` — the leftmost, client-controlled forwarded entry is
      trusted, so a caller can choose its own bucket.
    """
    value = proxy_trust_setting().strip()
    if value == "*":
        return ("FORWARDED_ALLOW_IPS='*' trusts the client-controlled leftmost "
                "X-Forwarded-For entry, so rate-limit buckets can be chosen by "
                "the caller. Set it to the proxy's network instead.")
    if value == DEFAULT_FORWARDED_ALLOW_IPS:
        return ("FORWARDED_ALLOW_IPS is not set, so uvicorn trusts only "
                "127.0.0.1 and X-Forwarded-For is ignored. Behind a reverse "
                "proxy every request keys to the proxy's address and the rate "
                "limit is GLOBAL, not per-IP. Set it to the proxy's network "
                "(e.g. 127.0.0.1,172.16.0.0/12).")
    return None


# `get_remote_address` reads `request.client.host`. That is the real client only
# when uvicorn has been told to trust the proxy — see `check_proxy_trust`.
limiter = Limiter(
    key_func=get_remote_address,
    enabled=not _should_disable_for_tests(),
)
