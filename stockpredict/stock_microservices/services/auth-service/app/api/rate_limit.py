"""Per-IP rate limiting for the auth-service's sensitive endpoints.

Uses slowapi (Starlette wrapper around limits library). Limits are keyed
by client IP (taken from X-Forwarded-For when behind Traefik, otherwise
the socket peer). This is best-effort: a determined attacker behind a
botnet can still spread requests across many IPs, but it shuts down the
trivial single-IP brute-force / enumeration cases that drove
SECURITY_AUDIT.md MEDIUM #7.

The limiter instance is shared across all routes so the rate budget is
global per IP, not per-endpoint. To rate-limit a route, decorate it with
@limiter.limit("N/minute"). The slowapi convention requires the route
to take `request: Request` as a parameter so the limiter can read the IP.
"""
import os

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


# get_remote_address respects X-Forwarded-For when present (Traefik sets
# this) and falls back to the direct peer otherwise.
limiter = Limiter(
    key_func=get_remote_address,
    enabled=not _should_disable_for_tests(),
)
