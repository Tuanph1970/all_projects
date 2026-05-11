"""Direct tests for AuthService — covers the pure utilities + the
business-logic methods that aren't routinely hit by the route tests.
"""
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import jwt
import pytest

from app.config import get_settings
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService


settings = get_settings()


async def _seed_user(test_db, email="alice@example.com", username="alice",
                     password="Password123!", active=True):
    repo = UserRepository(test_db)
    user = await repo.create_user(
        email=email,
        username=username,
        hashed_password=AuthService.hash_password(password),
        full_name="Alice Liddell",
    )
    if not active:
        user.is_active = False
        await test_db.commit()
        await test_db.refresh(user)
    return user, repo


# ---------------------------------------------------------------------------
# Password utilities
# ---------------------------------------------------------------------------

def test_hash_password_returns_bcrypt_string():
    hashed = AuthService.hash_password("secret")
    # bcrypt hashes start with $2b$
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")
    assert hashed != "secret"


def test_verify_password_round_trip():
    h = AuthService.hash_password("plaintext")
    assert AuthService.verify_password("plaintext", h) is True
    assert AuthService.verify_password("wrong", h) is False


# ---------------------------------------------------------------------------
# Token utilities
# ---------------------------------------------------------------------------

def test_create_access_token_decodes_back_with_expected_claims():
    token = AuthService.create_access_token(user_id=7, email="alice@example.com", role="user")
    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    assert payload["sub"] == "7"
    assert payload["email"] == "alice@example.com"
    assert payload["type"] == "access"


def test_create_refresh_token_returns_64char_url_safe_and_future_expiry():
    token, exp = AuthService.create_refresh_token()
    assert isinstance(token, str)
    assert len(token) >= 64
    assert exp > datetime.utcnow()


def test_decode_token_returns_none_on_invalid_token():
    assert AuthService.decode_token("not.a.jwt") is None


def test_decode_token_returns_none_on_expired_token():
    expired = jwt.encode(
        {
            "sub": "1",
            "exp": datetime.utcnow() - timedelta(minutes=1),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    assert AuthService.decode_token(expired) is None


def test_decode_token_returns_payload_on_valid_token():
    valid = AuthService.create_access_token(1, "x@y.com", "user")
    payload = AuthService.decode_token(valid)
    assert payload["sub"] == "1"


# ---------------------------------------------------------------------------
# verify_token
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_verify_token_returns_valid_for_good_token():
    svc = AuthService(repository=None)
    token = AuthService.create_access_token(7, "alice@example.com", "user")
    out = await svc.verify_token(token)
    assert out.valid is True
    assert out.user_id == 7
    assert out.email == "alice@example.com"


@pytest.mark.asyncio
async def test_verify_token_returns_invalid_for_bad_token():
    svc = AuthService(repository=None)
    out = await svc.verify_token("not.a.jwt")
    assert out.valid is False


# ---------------------------------------------------------------------------
# register / login / refresh / logout
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_register_duplicate_email_raises(test_db):
    user, _ = await _seed_user(test_db)
    svc = AuthService(UserRepository(test_db))

    from app.models.schemas import UserCreate
    with pytest.raises(ValueError, match="Email"):
        await svc.register(UserCreate(
            email=user.email, username="other", password="Password123!", full_name="x",
        ))


@pytest.mark.asyncio
async def test_register_duplicate_username_raises(test_db):
    user, _ = await _seed_user(test_db)
    svc = AuthService(UserRepository(test_db))

    from app.models.schemas import UserCreate
    with pytest.raises(ValueError, match="Username"):
        await svc.register(UserCreate(
            email="other@example.com", username=user.username,
            password="Password123!", full_name="x",
        ))


@pytest.mark.asyncio
async def test_login_invalid_email_raises(test_db):
    svc = AuthService(UserRepository(test_db))
    from app.models.schemas import UserLogin
    with pytest.raises(ValueError, match="Invalid"):
        await svc.login(UserLogin(email="nobody@example.com", password="x"))


@pytest.mark.asyncio
async def test_login_wrong_password_raises(test_db):
    await _seed_user(test_db)
    svc = AuthService(UserRepository(test_db))
    from app.models.schemas import UserLogin
    with pytest.raises(ValueError, match="Invalid"):
        await svc.login(UserLogin(email="alice@example.com", password="wrong"))


@pytest.mark.asyncio
async def test_login_inactive_user_raises(test_db):
    await _seed_user(test_db, active=False)
    svc = AuthService(UserRepository(test_db))
    from app.models.schemas import UserLogin
    with pytest.raises(ValueError, match="deactivated"):
        await svc.login(UserLogin(email="alice@example.com", password="Password123!"))


@pytest.mark.asyncio
async def test_refresh_tokens_with_unknown_token_raises(test_db):
    svc = AuthService(UserRepository(test_db))
    with pytest.raises(ValueError, match="Invalid refresh token"):
        await svc.refresh_tokens("never-issued")


@pytest.mark.asyncio
async def test_refresh_tokens_with_revoked_token_raises(test_db):
    user, repo = await _seed_user(test_db)
    svc = AuthService(repo)
    expires = datetime.utcnow() + timedelta(days=1)
    await repo.create_refresh_token(user.id, "tok", expires)
    await repo.revoke_refresh_token("tok")
    with pytest.raises(ValueError, match="expired or revoked"):
        await svc.refresh_tokens("tok")


@pytest.mark.asyncio
async def test_refresh_tokens_with_inactive_user_raises(test_db):
    user, repo = await _seed_user(test_db, active=False)
    svc = AuthService(repo)
    expires = datetime.utcnow() + timedelta(days=1)
    await repo.create_refresh_token(user.id, "tok", expires)
    with pytest.raises(ValueError, match="not found or inactive"):
        await svc.refresh_tokens("tok")


@pytest.mark.asyncio
async def test_refresh_tokens_happy_path_revokes_old_and_issues_new(test_db):
    user, repo = await _seed_user(test_db)
    svc = AuthService(repo)
    expires = datetime.utcnow() + timedelta(days=1)
    await repo.create_refresh_token(user.id, "old-tok", expires)

    out = await svc.refresh_tokens("old-tok")
    assert out.access_token  # JWT
    assert out.refresh_token != "old-tok"
    # The old token is now revoked.
    old = await repo.get_refresh_token("old-tok")
    assert old.is_revoked is True


@pytest.mark.asyncio
async def test_logout_revokes_the_refresh_token(test_db):
    user, repo = await _seed_user(test_db)
    svc = AuthService(repo)
    expires = datetime.utcnow() + timedelta(days=1)
    await repo.create_refresh_token(user.id, "tok", expires)
    ok = await svc.logout("tok")
    assert ok is True
    assert (await repo.get_refresh_token("tok")).is_revoked is True


@pytest.mark.asyncio
async def test_logout_all_returns_revoke_count(test_db):
    user, repo = await _seed_user(test_db)
    svc = AuthService(repo)
    expires = datetime.utcnow() + timedelta(days=1)
    await repo.create_refresh_token(user.id, "t1", expires)
    await repo.create_refresh_token(user.id, "t2", expires)
    assert await svc.logout_all(user.id) == 2


# ---------------------------------------------------------------------------
# change_password
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_change_password_with_wrong_current_password_raises(test_db):
    user, repo = await _seed_user(test_db)
    svc = AuthService(repo)
    with pytest.raises(ValueError, match="incorrect"):
        await svc.change_password(user.id, "wrong", "NewPass123!")


@pytest.mark.asyncio
async def test_change_password_with_missing_user_raises(test_db):
    svc = AuthService(UserRepository(test_db))
    with pytest.raises(ValueError, match="not found"):
        await svc.change_password(999_999, "Password123!", "NewPass123!")


@pytest.mark.asyncio
async def test_change_password_happy_path_revokes_all_tokens(test_db):
    user, repo = await _seed_user(test_db)
    svc = AuthService(repo)
    expires = datetime.utcnow() + timedelta(days=1)
    await repo.create_refresh_token(user.id, "t1", expires)
    await repo.create_refresh_token(user.id, "t2", expires)

    ok = await svc.change_password(user.id, "Password123!", "NewPass123!")
    assert ok is True
    # All previous refresh tokens revoked.
    assert (await repo.get_refresh_token("t1")).is_revoked is True
    assert (await repo.get_refresh_token("t2")).is_revoked is True
    # New password verifies.
    refreshed = await repo.get_user_by_id(user.id)
    assert AuthService.verify_password("NewPass123!", refreshed.hashed_password)


# ---------------------------------------------------------------------------
# get_current_user
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_current_user_returns_user(test_db):
    user, repo = await _seed_user(test_db)
    svc = AuthService(repo)
    out = await svc.get_current_user(user.id)
    assert out is not None
    assert out.id == user.id


@pytest.mark.asyncio
async def test_get_current_user_returns_none_when_missing(test_db):
    svc = AuthService(UserRepository(test_db))
    assert (await svc.get_current_user(999_999)) is None


# ---------------------------------------------------------------------------
# Password reset — confirm flow
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_password_reset_token_carries_pwreset_v1_kid_header():
    token = AuthService.create_password_reset_token(7, "alice@example.com")
    header = jwt.get_unverified_header(token)
    assert header.get("kid") == "pwreset-v1"


@pytest.mark.asyncio
async def test_confirm_password_reset_invalid_token_raises(test_db):
    svc = AuthService(UserRepository(test_db))
    with pytest.raises(ValueError, match="Invalid reset token"):
        await svc.confirm_password_reset("not.a.jwt", "NewPass123!")


@pytest.mark.asyncio
async def test_confirm_password_reset_expired_token_raises(test_db):
    """A token that's already expired raises the dedicated message."""
    svc = AuthService(UserRepository(test_db))
    expired = jwt.encode(
        {
            "sub": "1",
            "email": "x@y.com",
            "type": "password_reset",
            "iat": datetime.utcnow() - timedelta(minutes=10),
            "exp": datetime.utcnow() - timedelta(minutes=1),
        },
        AuthService._password_reset_signing_key(),
        algorithm=settings.JWT_ALGORITHM,
    )
    with pytest.raises(ValueError, match="expired"):
        await svc.confirm_password_reset(expired, "NewPass123!")


@pytest.mark.asyncio
async def test_confirm_password_reset_wrong_token_type_raises(test_db):
    """A correctly-signed token with the wrong `type` claim must be
    rejected — prevents an access-token-shaped token from being reused
    as a reset token if signing keys ever collided."""
    svc = AuthService(UserRepository(test_db))
    wrong_type = jwt.encode(
        {
            "sub": "1",
            "email": "x@y.com",
            "type": "access",  # wrong type
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(minutes=5),
        },
        AuthService._password_reset_signing_key(),
        algorithm=settings.JWT_ALGORITHM,
    )
    with pytest.raises(ValueError, match="Invalid reset token"):
        await svc.confirm_password_reset(wrong_type, "NewPass123!")


@pytest.mark.asyncio
async def test_confirm_password_reset_missing_user_raises(test_db):
    svc = AuthService(UserRepository(test_db))
    token = AuthService.create_password_reset_token(999_999, "ghost@example.com")
    with pytest.raises(ValueError, match="Invalid reset token"):
        await svc.confirm_password_reset(token, "NewPass123!")


@pytest.mark.asyncio
async def test_confirm_password_reset_inactive_user_raises(test_db):
    user, _ = await _seed_user(test_db, active=False)
    svc = AuthService(UserRepository(test_db))
    token = AuthService.create_password_reset_token(user.id, user.email)
    with pytest.raises(ValueError, match="Invalid reset token"):
        await svc.confirm_password_reset(token, "NewPass123!")


@pytest.mark.asyncio
async def test_confirm_password_reset_happy_path_revokes_existing_tokens(test_db):
    user, repo = await _seed_user(test_db)
    svc = AuthService(repo)
    expires = datetime.utcnow() + timedelta(days=1)
    await repo.create_refresh_token(user.id, "session-1", expires)

    token = AuthService.create_password_reset_token(user.id, user.email)
    ok = await svc.confirm_password_reset(token, "NewPass456!")
    assert ok is True
    # Old session revoked.
    sess = await repo.get_refresh_token("session-1")
    assert sess.is_revoked is True
    # Password actually changed.
    refreshed = await repo.get_user_by_id(user.id)
    assert AuthService.verify_password("NewPass456!", refreshed.hashed_password)


# ---------------------------------------------------------------------------
# request_password_reset — generic-message paths
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_request_password_reset_generic_for_unknown_email(test_db):
    """Unknown emails get the same response as known ones — anti-enumeration."""
    svc = AuthService(UserRepository(test_db))
    msg = await svc.request_password_reset("nobody@example.com")
    assert "exists" in msg.lower()


@pytest.mark.asyncio
async def test_request_password_reset_generic_for_inactive_user(test_db):
    """Inactive accounts also get the generic message."""
    await _seed_user(test_db, active=False)
    svc = AuthService(UserRepository(test_db))
    msg = await svc.request_password_reset("alice@example.com")
    assert "exists" in msg.lower()


@pytest.mark.asyncio
async def test_request_password_reset_swallows_email_send_failure(test_db):
    """SMTP failure must NOT change the response — anti-enumeration."""
    user, _ = await _seed_user(test_db)
    svc = AuthService(UserRepository(test_db))
    with patch("app.services.auth_service.send_password_reset_email",
               AsyncMock(side_effect=RuntimeError("smtp down"))):
        msg = await svc.request_password_reset(user.email)
    assert "exists" in msg.lower()


# ---------------------------------------------------------------------------
# HKDF-derived signing key is stable + distinct from JWT secret
# ---------------------------------------------------------------------------

def test_password_reset_signing_key_is_stable():
    """Two calls return the same bytes — needed for reset links to
    survive a process restart."""
    k1 = AuthService._password_reset_signing_key()
    k2 = AuthService._password_reset_signing_key()
    assert k1 == k2
    assert isinstance(k1, bytes)
    assert len(k1) == 32  # SHA-256 output


def test_password_reset_signing_key_differs_from_jwt_secret():
    """The whole point of HKDF here is to avoid sharing the key with
    access-token signing."""
    k = AuthService._password_reset_signing_key()
    assert k != settings.JWT_SECRET_KEY.encode()
