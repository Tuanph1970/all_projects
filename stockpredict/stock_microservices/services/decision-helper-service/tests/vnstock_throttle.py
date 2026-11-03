"""Backlog #49 — how long to wait between two vnstock calls.

Two different vnstock installs are in play, and they do NOT share a quota
model. Both were read out of the installed packages rather than assumed:

**The container** — `stock-data-service`, vnstock 4.0.7. Its `vnai` is
tiered (`vnai/beam/auth.py`)::

    TIER_LIMITS = {"guest": {"min": 20, ...}, "free": {"min": 60, ...}, ...}

and `_detect_tier()` returns `"free"` on the mere **presence** of
`VNSTOCK_API_KEY` (no validation). So there the key is decisive: 20 req/min
without it, 60 with. Verified in the running container after the owner
installed one — tier `free`, limits `{'min': 60, 'hour': 3600}`.

**The host** — where these dump scripts actually run: vnstock **3.3.1**,
vnai 2.2.6, kept deliberately (owner decision 2026-10-28: no need for
vnstock 4 here). That vnai has **no tier system at all**
(`vnai/beam/quota.py`)::

    self.resource_limits["VCI"] = {"min": 60, "hour": 3000}

A flat 60 req/min for VCI, key or no key.

What that means, stated plainly because the backlog row implied otherwise
-------------------------------------------------------------------------
On the host the ceiling was **always 60/min**. The old hardcoded `3.2`
(≈18.75/min) was therefore about **three times more conservative than
necessary**, and an API key never had anything to do with it. So the speedup
these scripts get is real but it is NOT the key's doing — it is simply no
longer throttling against a limit that was never 20.

The key's real payoff is the container: the nightly VN30 sync and live profile
reads go from 3.1s to 1.05s spacing, which is the #49 benefit that actually
needed a key.

The hour cap is the one to watch
--------------------------------
The host allows 3,000/hour, i.e. **50/min sustained**, which is *below* the
57/min that 1.05s spacing implies. A 92-symbol pull is 93 calls in under two
minutes and nowhere near it — but a bulk job running longer than ~50 minutes
at this spacing would trip the hour limit, not the minute one. Pass
`VNSTOCK_MIN_INTERVAL_SECONDS=1.2` (50/min) for anything that long.

Why this module exists
----------------------
`deep_history_dump.py` and `index_history_dump.py` hardcoded `3.2`, and they
are the slowest thing in the EM-3 and EM-4 workstreams — #86, #90 and #101
each spent roughly an hour of wall-clock on pulls. `stock-data-service`
already derived its spacing (`Settings.vnstock_min_interval`); these two
ignored every setting there was.

Honesty note, for the tiered install: `vnai` 4.x flips the tier on the
presence of the variable without validating it, so *any* non-empty string
would raise that ceiling. That would be abusing the vendor's honour system.
Use a real key from https://vnstocks.com/login or stay a guest.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional

#: Just under 20 req/min, the guest ceiling.
GUEST_INTERVAL_SECONDS = 3.1
#: Just under 60 req/min, the free Community ceiling.
KEYED_INTERVAL_SECONDS = 1.05


#: Parsed once per process. These scripts are long-running batch jobs; re-reading
#: a file per call would be pointless I/O, and the key does not change mid-run.
_ENV_FILE: Optional[Dict[str, str]] = None

#: Only these names are ever read out of the .env file. A dev helper has no
#: business parsing a secrets file wholesale.
_ENV_FILE_KEYS = ("VNSTOCK_API_KEY", "VNSTOCK_MIN_INTERVAL_SECONDS")


def _repo_env_file() -> Optional[Path]:
    """The repo-root `.env`, identified by the compose file beside it."""
    for parent in Path(__file__).resolve().parents:
        if (parent / "docker-compose.full-stack.yml").exists():
            candidate = parent / ".env"
            return candidate if candidate.exists() else None
    return None


def env_file_values() -> Dict[str, str]:
    """`VNSTOCK_*` settings from the repo `.env`, for scripts run on the host.

    The key lives in `stockpredict/.env`, which **docker-compose** reads — the
    host shell does not. Without this fallback a dump script started by hand
    stays on the guest interval no matter what the owner configured, which is
    the #49 defect this module exists to fix, one layer up. Found by checking
    after the key was installed: the service reported tier `free` while
    `describe()` on the host still said GUEST.

    Only the two names in `_ENV_FILE_KEYS` are read and the value is never
    logged or printed. A real environment variable always wins, so a shell
    export can still override the file.
    """
    global _ENV_FILE
    if _ENV_FILE is not None:
        return _ENV_FILE
    values: Dict[str, str] = {}
    path = _repo_env_file()
    if path is not None:
        try:
            for line in path.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                name, _, value = line.partition("=")
                if name.strip() in _ENV_FILE_KEYS:
                    values[name.strip()] = value.strip()
        except OSError:
            # An unreadable .env is not an error worth failing a pull over;
            # the guest interval is always a safe answer.
            pass
    _ENV_FILE = values
    return values


def _resolve(name: str, env: Optional[dict]) -> Optional[str]:
    """A real env var first, then the repo `.env`.

    When a caller passes `env` explicitly the file is NOT consulted, so tests
    stay hermetic and cannot be turned green or red by whatever the machine
    happens to have configured.
    """
    if env is not None:
        return env.get(name)
    value = os.environ.get(name)
    if value and value.strip():
        return value
    return env_file_values().get(name)


def has_api_key(env: Optional[dict] = None) -> bool:
    """Is a vnstock key present? Mirrors `vnai`'s own env-var check.

    An empty or whitespace-only value counts as absent: docker-compose passes
    `${VNSTOCK_API_KEY:-}` through as `""`, and treating that as a key would
    silently triple the call rate for a guest — the same trap
    `stock-data-service`'s `_blank_env_is_unset` validator exists to close.
    """
    value = _resolve("VNSTOCK_API_KEY", env)
    return bool(value and value.strip())


def min_interval(env: Optional[dict] = None) -> float:
    """Seconds to wait between vnstock calls, from the tier.

    `VNSTOCK_MIN_INTERVAL_SECONDS` overrides, so a long batch pull can be made
    deliberately gentler (or faster on a paid tier) without editing code.
    """
    override = _resolve("VNSTOCK_MIN_INTERVAL_SECONDS", env)
    if override and override.strip():
        try:
            return float(override)
        except ValueError:
            pass
    return KEYED_INTERVAL_SECONDS if has_api_key(env) else GUEST_INTERVAL_SECONDS


#: vnai's rate-limit handler calls `sys.exit()`, not `raise`.
#:
#: `vnai/beam/quota.py` contains literally
#:     sys.exit(f"Rate limit exceeded. {str(exc_val)} Process terminated.")
#: so a quota breach does not raise something a caller can catch and retry — it
#: terminates the interpreter. stock-data-service has guarded this since #48 by
#: monkeypatching `CleanErrorContext.__exit__` in its `main.py`; these host-side
#: dump scripts never did, and they are the LONGEST-running vnstock consumers in
#: the project (#86/#90/#101 each spent about an hour of wall-clock pulling).
#: Losing an hour-long dump to a bare `sys.exit` is the worst version of this
#: failure, because the partial work is gone and the cause is a one-line message
#: with no traceback.
#:
#: Applied by `activate()`. Idempotent, and a no-op where vnai is absent or has
#: no such context manager (vnstock 5 ships no vnai at all).
def _disarm_vnai_process_kill() -> bool:
    """Turn vnai's `sys.exit()` on rate-limit back into a catchable exception.

    Returns True if the patch was applied or already in place.
    """
    try:
        import vnai.beam.quota as _quota
    except Exception:
        return False                      # no vnai (vnstock 5, or not installed)
    ctx = getattr(_quota, "CleanErrorContext", None)
    rate_limit = getattr(_quota, "RateLimitExceeded", None)
    if ctx is None or rate_limit is None:
        return False
    if getattr(ctx, "_stockpredict_disarmed", False):
        return True

    class _Catchable(ctx):                # type: ignore[misc,valid-type]
        _stockpredict_disarmed = True

        def __exit__(self, exc_type, exc_val, exc_tb):
            # Let RateLimitExceeded propagate to the caller instead of being
            # converted into process death.
            if exc_type is rate_limit:
                return False
            return super().__exit__(exc_type, exc_val, exc_tb)

    _quota.CleanErrorContext = _Catchable
    return True

def activate() -> float:
    """Export the key into the environment, then return the call spacing.

    Only matters where a **tiered** vnai is installed — vnstock 4.x, i.e. the
    container. There `vnai/beam/auth.py::_has_api_key` grants the tier by
    reading `os.getenv("VNSTOCK_API_KEY")` itself, so reading the repo `.env`
    for *spacing* alone would leave vnai seeing a GUEST at 20 req/min while we
    called every 1.05s (~57/min) — a quota breach ending in
    `RateLimitExceeded` partway through an hour-long pull.

    THE HOST IS NO LONGER ON 3.3.1. This docstring said "vnstock 3.3.1, kept by
    owner decision", and that stopped being true on 2026-11-03: running
    `scripts/ci-unit-tests.sh stock-data-service` on the host does
    `pip install --find-links=vendor/wheels -r requirements.txt`, which upgraded
    the host to the pinned 4.0.7 and vnai 2.2.6 -> 2.5.9 as a side effect. 3.3.1
    is withdrawn from PyPI and was in no local cache, so it cannot be restored
    from here. Measured after the change: has_api_key() True, spacing 1.05s,
    tier "free/Community key" — so the SPACING is unaffected, and the host now
    matches the container rather than diverging from it.

    It is kept because these scripts are also runnable inside the container,
    where omitting it would be exactly the breach described above.

    An existing environment variable is never overwritten, so a shell export
    still wins. Returns the interval so a caller can do both in one line.
    """
    # Disarm vnai's sys.exit() on rate-limit before any call is made.
    _disarm_vnai_process_kill()

    key = (env_file_values().get("VNSTOCK_API_KEY") or "").strip()
    if key and not (os.environ.get("VNSTOCK_API_KEY") or "").strip():
        os.environ["VNSTOCK_API_KEY"] = key
    return min_interval()


def describe(env: Optional[dict] = None) -> str:
    """One line for a script banner, so a slow run is never a mystery.

    It also names an override when one is in force. Without that, a run
    spacing calls at 0.5s as a guest would print the "set a key to go faster"
    hint while already exceeding the guest ceiling — a confusing and
    misleading banner on the one configuration that most needs explaining.
    """
    keyed = has_api_key(env)
    spacing = min_interval(env)
    tier = "free/Community key (60 req/min)" if keyed else "GUEST (20 req/min)"
    override = _resolve("VNSTOCK_MIN_INTERVAL_SECONDS", env)
    overridden = bool(override and override.strip())
    line = f"vnstock tier: {tier}; spacing {spacing:.2f}s between calls"
    if overridden:
        return line + "  [VNSTOCK_MIN_INTERVAL_SECONDS override in force]"
    if not keyed:
        return line + "  [set VNSTOCK_API_KEY to go ~3x faster — #49]"
    return line
