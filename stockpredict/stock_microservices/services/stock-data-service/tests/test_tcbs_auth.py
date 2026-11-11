"""Backlog #142 P0 — TCBS token custody.

The behaviours worth pinning are the ones that fail QUIETLY if got wrong: a
token used past its useful life, a token that does not survive a restart, a
credential reaching a log, and a prime that retries into an invisible budget.
"""
import base64
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import get_settings
from app.services.tcbs_auth import (
    KEY_EXPIRY_WARN_DAYS,
    TOKEN_SAFETY_MARGIN_SECONDS,
    TcbsAuth,
    TcbsAuthError,
    jwt_exp,
)

settings = get_settings()


def make_jwt(exp: datetime) -> str:
    """A JWT with a real `exp`. Unsigned — nothing here verifies signatures,
    and pretending otherwise would test the wrong thing."""
    def seg(d):
        return base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()
    return f"{seg({'alg': 'HS256'})}.{seg({'exp': exp.timestamp()})}.sig"


class FakeRedis:
    """Enough Redis to test custody, including that a TTL was actually set."""
    def __init__(self):
        self.store = {}
        self.ttls = {}

    async def get(self, k):
        return self.store.get(k)

    async def set(self, k, v, ex=None):
        self.store[k] = v
        self.ttls[k] = ex


def auth_with(redis=None) -> TcbsAuth:
    return TcbsAuth(redis_client=redis if redis is not None else FakeRedis())


# ── reading the clock ──────────────────────────────────────────────────────

def test_jwt_exp_reads_the_token_not_the_documentation():
    """The docs say 8 hours MAXIMUM; the token is the authority on its own
    lifetime and may well be shorter."""
    exp = datetime.now(timezone.utc) + timedelta(hours=3)
    got = jwt_exp(make_jwt(exp))
    assert got is not None and abs((got - exp).total_seconds()) < 2


def test_an_unreadable_token_yields_no_expiry_rather_than_a_guess():
    assert jwt_exp("not-a-jwt") is None
    assert jwt_exp("") is None


@pytest.mark.asyncio
async def test_no_token_means_needs_prime():
    state = await auth_with().token_state()
    assert state.present is False
    assert state.usable is False
    assert state.as_dict()["needs_prime"] is True


@pytest.mark.asyncio
async def test_a_healthy_token_is_usable_and_does_not_ask_for_a_prime():
    r = FakeRedis()
    r.store["tcbs:token"] = make_jwt(datetime.now(timezone.utc) + timedelta(hours=7))
    state = await auth_with(r).token_state()
    assert state.present and state.usable
    assert state.as_dict()["needs_prime"] is False
    assert state.seconds_left > 6 * 3600


@pytest.mark.asyncio
async def test_a_token_inside_the_safety_margin_is_already_unusable():
    """THE POINT OF THE MARGIN: a 93-symbol sweep takes minutes, so a token that
    is valid at the start and dead halfway through writes a PARTIAL run with no
    error naming the cause. Refusing to start is the loud, consistent failure."""
    r = FakeRedis()
    r.store["tcbs:token"] = make_jwt(
        datetime.now(timezone.utc) + timedelta(seconds=TOKEN_SAFETY_MARGIN_SECONDS - 60))
    state = await auth_with(r).token_state()
    assert state.present is True, "it has not expired..."
    assert state.usable is False, "...but it must not be started with"
    assert state.as_dict()["needs_prime"] is True


@pytest.mark.asyncio
async def test_bearer_returns_none_rather_than_an_expiring_token():
    r = FakeRedis()
    r.store["tcbs:token"] = make_jwt(datetime.now(timezone.utc) + timedelta(seconds=30))
    assert await auth_with(r).bearer() is None


@pytest.mark.asyncio
async def test_a_redis_outage_reports_no_token_instead_of_raising():
    """/health reads this. A health endpoint that 500s because Redis hiccuped is
    worse than one that says 'no token'."""
    broken = MagicMock()
    broken.get = AsyncMock(side_effect=ConnectionError("redis down"))
    state = await auth_with(broken).token_state()
    assert state.present is False and state.as_dict()["needs_prime"] is True


# ── priming ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_prime_stores_the_token_with_a_ttl_from_its_own_exp():
    """The TTL must come from the token, so Redis drops it exactly when it dies
    and a stale credential never lingers as a confusing half-state."""
    exp = datetime.now(timezone.utc) + timedelta(hours=8)
    r = FakeRedis()
    with patch.object(settings, "TCBS_API_KEY", "k" * 48):
        with patch("app.services.tcbs_auth.httpx.AsyncClient") as client:
            resp = MagicMock(status_code=200)
            resp.json.return_value = {"token": make_jwt(exp)}
            client.return_value.__aenter__.return_value.post = AsyncMock(return_value=resp)
            state = await auth_with(r).prime("123456")
    assert state.usable
    assert r.ttls["tcbs:token"] is not None
    assert 7.9 * 3600 < r.ttls["tcbs:token"] <= 8 * 3600


@pytest.mark.asyncio
async def test_prime_makes_exactly_one_attempt():
    """An unconfirmed report puts the exchange at 10/day and TCBS publishes no
    figure, so a retry loop could spend a budget nobody can see."""
    r = FakeRedis()
    with patch.object(settings, "TCBS_API_KEY", "k" * 48):
        with patch("app.services.tcbs_auth.httpx.AsyncClient") as client:
            post = AsyncMock(return_value=MagicMock(status_code=400, text="nope"))
            client.return_value.__aenter__.return_value.post = post
            with pytest.raises(TcbsAuthError):
                await auth_with(r).prime("123456")
    assert post.await_count == 1


@pytest.mark.asyncio
async def test_prime_without_an_otp_is_refused_before_any_request():
    """The vendor would reject it anyway; spending the round trip to learn that
    is how a daily budget evaporates."""
    with patch.object(settings, "TCBS_API_KEY", "k" * 48):
        with patch("app.services.tcbs_auth.httpx.AsyncClient") as client:
            with pytest.raises(TcbsAuthError, match="OTP"):
                await auth_with().prime("")
            client.assert_not_called()


@pytest.mark.asyncio
async def test_prime_without_a_configured_key_is_refused():
    with patch.object(settings, "TCBS_API_KEY", ""):
        with pytest.raises(TcbsAuthError, match="TCBS_API_KEY"):
            await auth_with().prime("123456")


@pytest.mark.asyncio
async def test_a_token_with_no_readable_expiry_is_refused_not_stored():
    """Storing a credential whose lifetime is unknown means never knowing when
    to re-prime — the silent-outage shape again."""
    r = FakeRedis()
    with patch.object(settings, "TCBS_API_KEY", "k" * 48):
        with patch("app.services.tcbs_auth.httpx.AsyncClient") as client:
            resp = MagicMock(status_code=200)
            resp.json.return_value = {"token": "opaque-not-a-jwt"}
            client.return_value.__aenter__.return_value.post = AsyncMock(return_value=resp)
            with pytest.raises(TcbsAuthError, match="lifetime"):
                await auth_with(r).prime("123456")
    assert "tcbs:token" not in r.store


@pytest.mark.asyncio
async def test_an_already_expired_token_is_refused():
    r = FakeRedis()
    with patch.object(settings, "TCBS_API_KEY", "k" * 48):
        with patch("app.services.tcbs_auth.httpx.AsyncClient") as client:
            resp = MagicMock(status_code=200)
            resp.json.return_value = {
                "token": make_jwt(datetime.now(timezone.utc) - timedelta(minutes=1))}
            client.return_value.__aenter__.return_value.post = AsyncMock(return_value=resp)
            with pytest.raises(TcbsAuthError, match="expired"):
                await auth_with(r).prime("123456")
    assert "tcbs:token" not in r.store


@pytest.mark.asyncio
async def test_the_otp_never_reaches_the_error_message():
    """Errors get pasted into issues and logs. The vendor's code is useful; the
    code a human read off their phone is not ours to repeat."""
    with patch.object(settings, "TCBS_API_KEY", "k" * 48):
        with patch("app.services.tcbs_auth.httpx.AsyncClient") as client:
            resp = MagicMock(status_code=400, text='{"code":"203002"}')
            client.return_value.__aenter__.return_value.post = AsyncMock(return_value=resp)
            with pytest.raises(TcbsAuthError) as err:
                await auth_with().prime("987654")
    assert "987654" not in str(err.value)
    assert "203002" in str(err.value), "the vendor's own code should survive"


# ── the other clock ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_api_key_status_flags_a_key_approaching_expiry():
    soon = datetime.now(timezone.utc) + timedelta(days=KEY_EXPIRY_WARN_DAYS - 5)
    with patch.object(settings, "TCBS_API_KEY", "k" * 48):
        with patch("app.services.tcbs_auth.httpx.AsyncClient") as client:
            resp = MagicMock(status_code=200)
            resp.json.return_value = {"expireDate": soon.isoformat()}
            client.return_value.__aenter__.return_value.post = AsyncMock(return_value=resp)
            out = await auth_with().api_key_status()
    assert out["api_key_renew_soon"] is True
    assert out["api_key_days_left"] < KEY_EXPIRY_WARN_DAYS


@pytest.mark.asyncio
async def test_a_year_out_key_is_not_flagged():
    far = datetime.now(timezone.utc) + timedelta(days=365)
    with patch.object(settings, "TCBS_API_KEY", "k" * 48):
        with patch("app.services.tcbs_auth.httpx.AsyncClient") as client:
            resp = MagicMock(status_code=200)
            resp.json.return_value = {"expireDate": far.isoformat()}
            client.return_value.__aenter__.return_value.post = AsyncMock(return_value=resp)
            out = await auth_with().api_key_status()
    assert out["api_key_renew_soon"] is False


@pytest.mark.asyncio
async def test_api_key_status_survives_the_vendor_being_down():
    with patch.object(settings, "TCBS_API_KEY", "k" * 48):
        with patch("app.services.tcbs_auth.httpx.AsyncClient") as client:
            client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=TimeoutError("slow"))
            out = await auth_with().api_key_status()
    assert out["api_key_expires"] is None
    assert out["api_key_error"] == "TimeoutError"
