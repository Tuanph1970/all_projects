"""Coverage for password reset, change-password, and logout-all flows.

The base test_auth.py covers register/login/refresh/me. This file targets
the gaps surfaced by `pytest --cov`: the reset-token round-trip we wired
in Sprint A, change_password's session-revocation behavior, and logout_all.
"""
import pytest
from httpx import AsyncClient

from app.services.auth_service import AuthService


PREFIX = "/stock_helper/api/v2/auth"


async def _register_and_login(client: AsyncClient, user_data: dict) -> dict:
    """Helper: register a fresh user, log in, return the tokens."""
    reg = await client.post(f"{PREFIX}/register", json=user_data)
    assert reg.status_code == 201, reg.text
    login = await client.post(
        f"{PREFIX}/login",
        json={"email": user_data["email"], "password": user_data["password"]},
    )
    assert login.status_code == 200, login.text
    return login.json()


# ---------------------------------------------------------------------------
# Reset-password request endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reset_password_returns_generic_message_for_unknown_email(
    client: AsyncClient,
):
    """Anti-enumeration: response is identical for known + unknown emails."""
    r = await client.post(
        f"{PREFIX}/reset-password",
        json={"email": "no-such-user@example.com"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "If the email exists" in body["message"]


@pytest.mark.asyncio
async def test_reset_password_returns_generic_message_for_existing_user(
    client: AsyncClient, test_user_data: dict,
):
    await _register_and_login(client, test_user_data)
    r = await client.post(
        f"{PREFIX}/reset-password",
        json={"email": test_user_data["email"]},
    )
    assert r.status_code == 200
    assert "If the email exists" in r.json()["message"]


# ---------------------------------------------------------------------------
# Reset-password confirm — round-trip the JWT we just issued
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reset_password_confirm_with_valid_token(
    client: AsyncClient, test_user_data: dict,
):
    """End-to-end: register → mint reset token via the service → confirm."""
    reg = await client.post(f"{PREFIX}/register", json=test_user_data)
    assert reg.status_code == 201
    user_id = reg.json()["id"]

    token = AuthService.create_password_reset_token(
        user_id=user_id,
        email=test_user_data["email"],
    )

    r = await client.post(
        f"{PREFIX}/reset-password/confirm",
        json={"token": token, "new_password": "BrandNew123"},
    )
    assert r.status_code == 200, r.text
    assert "successfully" in r.json()["message"].lower()

    # Old password must no longer work
    bad = await client.post(
        f"{PREFIX}/login",
        json={"email": test_user_data["email"], "password": test_user_data["password"]},
    )
    assert bad.status_code == 400 or bad.status_code == 401

    # New password works
    good = await client.post(
        f"{PREFIX}/login",
        json={"email": test_user_data["email"], "password": "BrandNew123"},
    )
    assert good.status_code == 200


@pytest.mark.asyncio
async def test_reset_password_confirm_rejects_garbage_token(client: AsyncClient):
    r = await client.post(
        f"{PREFIX}/reset-password/confirm",
        json={"token": "not-a-jwt", "new_password": "Whatever123"},
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_reset_password_confirm_rejects_wrong_signing_key(
    client: AsyncClient, test_user_data: dict,
):
    """A JWT signed with the access-token key (not the derived reset key)
    must be rejected — this guards the key-separation we shipped in Backlog #33.
    """
    import jwt
    from datetime import datetime, timedelta
    from app.config import get_settings
    settings = get_settings()
    reg = await client.post(f"{PREFIX}/register", json=test_user_data)
    user_id = reg.json()["id"]

    forged = jwt.encode(
        {
            "sub": str(user_id),
            "email": test_user_data["email"],
            "type": "password_reset",
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(minutes=5),
        },
        settings.JWT_SECRET_KEY,  # WRONG: should be the derived reset key
        algorithm=settings.JWT_ALGORITHM,
    )

    r = await client.post(
        f"{PREFIX}/reset-password/confirm",
        json={"token": forged, "new_password": "Whatever123"},
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_reset_password_confirm_rejects_wrong_token_type(
    client: AsyncClient, test_user_data: dict,
):
    """A token with the right signing key but wrong `type` claim is rejected."""
    import jwt
    from datetime import datetime, timedelta
    from app.config import get_settings
    settings = get_settings()
    reg = await client.post(f"{PREFIX}/register", json=test_user_data)
    user_id = reg.json()["id"]

    wrong_type = jwt.encode(
        {
            "sub": str(user_id),
            "email": test_user_data["email"],
            "type": "access",  # WRONG: confirm endpoint requires password_reset
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(minutes=5),
        },
        AuthService._password_reset_signing_key(),
        algorithm=settings.JWT_ALGORITHM,
    )

    r = await client.post(
        f"{PREFIX}/reset-password/confirm",
        json={"token": wrong_type, "new_password": "Whatever123"},
    )
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# Change-password — verifies the session-revocation side effect
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_change_password_revokes_existing_refresh_tokens(
    client: AsyncClient, test_user_data: dict,
):
    tokens = await _register_and_login(client, test_user_data)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    r = await client.post(
        f"{PREFIX}/change-password",
        json={
            "current_password": test_user_data["password"],
            "new_password": "RotatedPass123",
        },
        headers=headers,
    )
    assert r.status_code == 200, r.text

    # Old refresh token must be revoked.
    refresh = await client.post(
        f"{PREFIX}/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refresh.status_code == 401


@pytest.mark.asyncio
async def test_change_password_rejects_wrong_current_password(
    client: AsyncClient, test_user_data: dict,
):
    tokens = await _register_and_login(client, test_user_data)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    r = await client.post(
        f"{PREFIX}/change-password",
        json={
            "current_password": "NotTheActualOne",
            "new_password": "RotatedPass123",
        },
        headers=headers,
    )
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# logout-all — revokes every refresh token for the user
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_logout_all_revokes_every_refresh_token(
    client: AsyncClient, test_user_data: dict,
):
    """Issue two sessions (login twice), call /logout-all, verify both
    refresh tokens are dead.
    """
    tokens_a = await _register_and_login(client, test_user_data)
    second_login = await client.post(
        f"{PREFIX}/login",
        json={"email": test_user_data["email"], "password": test_user_data["password"]},
    )
    tokens_b = second_login.json()

    headers = {"Authorization": f"Bearer {tokens_a['access_token']}"}
    r = await client.post(f"{PREFIX}/logout-all", headers=headers)
    assert r.status_code == 200

    for refresh in (tokens_a["refresh_token"], tokens_b["refresh_token"]):
        attempt = await client.post(
            f"{PREFIX}/refresh", json={"refresh_token": refresh}
        )
        assert attempt.status_code == 401


# ---------------------------------------------------------------------------
# Email service — verify the dev-mode (no SMTP) path doesn't blow up
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_email_service_returns_false_when_smtp_unconfigured():
    """SMTP_HOST is intentionally unset in tests; send_email should
    return False rather than raise. This is the documented dev-mode
    behavior (logs the link instead of sending).
    """
    from app.services.email_service import send_email
    sent = await send_email(
        to_email="someone@example.com",
        subject="test",
        text_body="hello",
    )
    assert sent is False
