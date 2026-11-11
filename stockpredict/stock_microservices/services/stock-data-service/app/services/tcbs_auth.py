"""Backlog #142 — TCBS OpenAPI token lifecycle (P0).

Design: `docs/backlog142_adapter_design.md`. Probe: `tests/tcbs_auth_probe.py`.

WHAT THIS IS FOR. The JWT that authorises every TCBS data call is valid for at
most 8 hours and, so far as the probe could establish without spending an OTP,
can only be minted with a Smart OTP a human reads off the TCInvest app. So the
service cannot mint one for itself: a person primes a token, and this module
keeps it alive and visible for as long as it lasts.

NOTHING HERE FETCHES MARKET DATA. P0 is auth only — no call site changes, no
behaviour changes. The vnstock path keeps running untouched.

THE TOKEN LIVES IN REDIS, NOT IN MEMORY, and that is the whole point of this
module rather than a module-level variable. An in-memory token dies with the
container, so a 03:00 restart would silently drop ingestion until somebody
noticed — which is exactly Backlog #143's shape, four days of a service saying
nothing while being wrong. Redis also expires the entry on its own, so a dead
token cannot linger as a confusing half-state.

SECRETS ARE NEVER LOGGED. The key, the OTP and the token appear in logs and in
`/health` as lengths and expiry timestamps, never as values.
"""
from __future__ import annotations

import base64
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

TOKEN_PATH = "/gaia/v1/oauth2/openapi/token"
#: Quoted from the per-endpoint doc pages, not inferred from the index — the
#: probe's first version guessed these and got a 404 that read like "the key
#: cannot query its own expiry", which would have been a bad thing to believe.
APIKEY_INFO_PATH = "/gaia/v1/oauth2/openapi/apikey/info"
APIKEY_EXTEND_PATH = "/gaia/v1/oauth2/openapi/apikey/extend"

REDIS_TOKEN_KEY = "tcbs:token"

#: Treat a token as dead this long before its real `exp`.
#:
#: A 93-symbol sweep takes minutes, so a token that passes the check at the
#: start and expires halfway through produces a PARTIAL run — some symbols
#: written, some not, and no error that names the cause. Refusing to start is
#: the better failure: it is loud, and it leaves the stored data consistent.
TOKEN_SAFETY_MARGIN_SECONDS = 600

#: Warn this far ahead of the API KEY's own expiry (a separate, yearly clock).
#: Renewal needs an OTP and cannot be automated — see `api_key_status`.
KEY_EXPIRY_WARN_DAYS = 30

HTTP_TIMEOUT = 30.0


class TcbsAuthError(RuntimeError):
    """Raised for a failed prime. Carries no credential material."""


@dataclass(frozen=True)
class TokenState:
    present: bool
    expires_at: Optional[datetime]
    seconds_left: Optional[float]

    @property
    def usable(self) -> bool:
        """Usable means 'will still be valid when the work finishes', not
        'has not expired yet' — see TOKEN_SAFETY_MARGIN_SECONDS."""
        if not self.present or self.seconds_left is None:
            return False
        return self.seconds_left > TOKEN_SAFETY_MARGIN_SECONDS

    def as_dict(self) -> Dict[str, Any]:
        return {
            "token_present": self.present,
            "token_expires": self.expires_at.isoformat() if self.expires_at else None,
            "token_seconds_left": (round(self.seconds_left)
                                   if self.seconds_left is not None else None),
            # The alert. Whatever watches /health should shout on this BEFORE
            # ingestion misses a run, not after.
            "needs_prime": not self.usable,
        }


def jwt_exp(token: str) -> Optional[datetime]:
    """Read `exp` from a JWT without verifying it.

    Verification needs TCBS's public key and answers a different question. What
    matters here is when this token stops being accepted, and the token itself
    is the authority on that — more so than the documented 8 hours, which is a
    maximum rather than a promise.
    """
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload))
        exp = claims.get("exp")
        return datetime.fromtimestamp(float(exp), timezone.utc) if exp else None
    except Exception:                                          # noqa: BLE001
        return None


class TcbsAuth:
    """Token custody. One instance per process; the state lives in Redis."""

    def __init__(self, redis_client=None):
        self._redis = redis_client

    async def _client(self):
        if self._redis is None:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(
                settings.redis_url, decode_responses=True)
        return self._redis

    # ── reading ──────────────────────────────────────────────────────────
    async def token_state(self) -> TokenState:
        """Current token, or an empty state. Never raises: this is read by
        /health, and a health endpoint that fails because Redis hiccuped is
        worse than one that reports 'no token'."""
        try:
            r = await self._client()
            token = await r.get(REDIS_TOKEN_KEY)
        except Exception as exc:                               # noqa: BLE001
            logger.warning("tcbs: token lookup failed: %s", exc)
            return TokenState(False, None, None)
        if not token:
            return TokenState(False, None, None)
        exp = jwt_exp(token)
        if exp is None:
            # Stored but unreadable: treat as absent rather than guess a TTL.
            return TokenState(True, None, None)
        left = (exp - datetime.now(timezone.utc)).total_seconds()
        return TokenState(True, exp, left)

    async def bearer(self) -> Optional[str]:
        """The token to send, or None when the adapter must fall back.

        Returns None for an unusable token rather than an expiring one, so a
        caller cannot accidentally start work it has no time to finish.
        """
        state = await self.token_state()
        if not state.usable:
            return None
        try:
            return await (await self._client()).get(REDIS_TOKEN_KEY)
        except Exception:                                      # noqa: BLE001
            return None

    # ── priming ──────────────────────────────────────────────────────────
    async def prime(self, otp: str) -> TokenState:
        """Exchange the API key + a human-supplied OTP for a JWT and store it.

        ONE ATTEMPT, NO RETRY. An unconfirmed report puts the token endpoint at
        10 exchanges/day and TCBS publishes no figure, so a retry loop could
        spend a budget nobody can see. A failed prime is reported to the
        operator, who still holds the app and can read a fresh code.
        """
        if not settings.TCBS_API_KEY:
            raise TcbsAuthError("TCBS_API_KEY is not configured")
        if not otp:
            raise TcbsAuthError("an OTP from the TCInvest app is required")

        url = settings.TCBS_BASE_URL.rstrip("/") + TOKEN_PATH
        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                resp = await client.post(
                    url,
                    json={"apiKey": settings.TCBS_API_KEY, "otp": otp},
                    headers={"Content-Type": "application/json"},
                )
        except Exception as exc:                               # noqa: BLE001
            raise TcbsAuthError(f"token request failed: {type(exc).__name__}") from exc

        if resp.status_code != 200:
            # The vendor's code/message is useful and carries no secret; the OTP
            # is never echoed back.
            raise TcbsAuthError(
                f"token exchange rejected (HTTP {resp.status_code}): "
                f"{resp.text[:200]}")

        token = (resp.json() or {}).get("token")
        if not token:
            raise TcbsAuthError("token exchange returned no token field")

        exp = jwt_exp(token)
        if exp is None:
            raise TcbsAuthError("token is not a readable JWT; refusing to store "
                                "a credential with an unknown lifetime")

        ttl = int((exp - datetime.now(timezone.utc)).total_seconds())
        if ttl <= 0:
            raise TcbsAuthError("token is already expired on arrival")

        r = await self._client()
        # Redis expires it on its own, so a dead token never lingers as a
        # confusing half-state that something might try to use.
        await r.set(REDIS_TOKEN_KEY, token, ex=ttl)
        logger.info(
            "tcbs: token primed, %d chars, expires %s (%.2f h)",
            len(token), exp.isoformat(), ttl / 3600)
        return await self.token_state()

    # ── the other clock ──────────────────────────────────────────────────
    async def api_key_status(self) -> Dict[str, Any]:
        """The API KEY's own expiry — a yearly clock, not the token's 8 hours.

        Readable with the key alone: no OTP, no bearer (verified 2026-11-10).
        That is what makes unattended monitoring possible at all.

        NOT auto-renewed, deliberately. `apikey/extend` needs an OTP, and the
        new term runs from the moment of extension rather than adding to the
        remainder ("không cộng dồn vào thời hạn cũ") — so a scheduled renewal
        would throw away whatever time was left. An EXPIRED key cannot be
        extended at all; it has to be recreated in TCInvest. Hence: warn early,
        let a human choose when.
        """
        if not settings.TCBS_API_KEY:
            return {"api_key_configured": False}
        url = settings.TCBS_BASE_URL.rstrip("/") + APIKEY_INFO_PATH
        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                resp = await client.post(
                    url, json={"apiKey": settings.TCBS_API_KEY},
                    headers={"Content-Type": "application/json"})
            if resp.status_code != 200:
                return {"api_key_configured": True,
                        "api_key_expires": None,
                        "api_key_error": f"HTTP {resp.status_code}"}
            expire_date = (resp.json() or {}).get("expireDate")
        except Exception as exc:                               # noqa: BLE001
            return {"api_key_configured": True, "api_key_expires": None,
                    "api_key_error": type(exc).__name__}

        out: Dict[str, Any] = {"api_key_configured": True,
                               "api_key_expires": expire_date}
        try:
            exp = datetime.fromisoformat(expire_date)
            days = (exp - datetime.now(exp.tzinfo)).total_seconds() / 86400
            out["api_key_days_left"] = round(days, 1)
            out["api_key_renew_soon"] = days < KEY_EXPIRY_WARN_DAYS
        except (TypeError, ValueError):
            pass
        return out


#: Process-wide instance. The custody is Redis; this is just the handle.
_auth: Optional[TcbsAuth] = None


def get_tcbs_auth() -> TcbsAuth:
    global _auth
    if _auth is None:
        _auth = TcbsAuth()
    return _auth


def reset_tcbs_auth() -> None:
    """Tests only."""
    global _auth
    _auth = None
